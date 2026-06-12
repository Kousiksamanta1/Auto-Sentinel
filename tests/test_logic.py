"""Tests for passive audit backend behavior."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.logic import BackendError, WirelessAuditService
from core.models import RuntimeEnvironment

MOCK_ENVIRONMENT = RuntimeEnvironment(
    platform_name="Test",
    mock_mode=True,
    supported=True,
)

HARDWARE_ENVIRONMENT = RuntimeEnvironment(
    platform_name="Linux",
    mock_mode=False,
    supported=True,
)


class FakeProcess:
    """Small subprocess stand-in for hardware lifecycle tests."""

    def __init__(self, return_code: int | None = None) -> None:
        self.return_code = return_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True
        self.return_code = 0

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9

    def wait(self, timeout: int | None = None) -> int:
        if self.return_code is None:
            raise subprocess.TimeoutExpired("fake", timeout or 0)
        return self.return_code


class LogicTests(unittest.TestCase):
    """Covers mock workflows and hardware preflight contracts."""

    def test_mock_scan_persists_loadable_capture_and_report(self) -> None:
        service = WirelessAuditService(environment=MOCK_ENVIRONMENT)
        with TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "captures"
            preflight = service.run_preflight("wlan0", output_root, False)
            self.assertTrue(preflight.ready)

            session = service.start_target_scan("wlan0", output_root)
            self.assertTrue(service.scan_active)
            self.assertTrue(session.csv_path.exists())

            records = service.read_live_records()
            self.assertEqual(len(records), 6)
            loaded = service.load_capture(session.csv_path)
            self.assertEqual(len(loaded), 6)
            self.assertIn("Networks discovered: 6", service.analyze_results(loaded))

            report_path = service.export_report(loaded, Path(tmp) / "report")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["networks"]), 6)
            self.assertEqual(payload["application"], "Auto-Sentinel")

            self.assertTrue(service.stop_target_scan())
            self.assertFalse(service.scan_active)

    def test_duplicate_scan_is_rejected(self) -> None:
        service = WirelessAuditService(environment=MOCK_ENVIRONMENT)
        with TemporaryDirectory() as tmp:
            service.start_target_scan("wlan0", Path(tmp))
            with self.assertRaisesRegex(BackendError, "already active"):
                service.start_target_scan("wlan0", Path(tmp))

    def test_validation_rejects_unsafe_values(self) -> None:
        service = WirelessAuditService(environment=MOCK_ENVIRONMENT)
        with TemporaryDirectory() as tmp:
            report = service.run_preflight("wlan0;rm", Path(tmp), False)
        self.assertFalse(report.ready)
        self.assertIn("Interface name", report.as_text())

    @patch("core.logic.os.geteuid", return_value=0)
    @patch("core.logic.shutil.which", side_effect=lambda tool: f"/usr/bin/{tool}")
    def test_hardware_preflight_passes_with_tools_and_interface(
        self,
        _mock_which: object,
        _mock_geteuid: object,
    ) -> None:
        service = WirelessAuditService(environment=HARDWARE_ENVIRONMENT)
        with (
            TemporaryDirectory() as tmp,
            patch.object(service, "discover_interfaces", return_value=["wlan0"]),
        ):
            report = service.run_preflight("wlan0", Path(tmp), True)
        self.assertTrue(report.ready, report.as_text())

    def test_monitor_interface_parser_handles_airmon_output(self) -> None:
        service = WirelessAuditService(environment=HARDWARE_ENVIRONMENT)
        result = service._extract_monitor_interface(  # pylint: disable=protected-access
            ["monitor mode vif enabled for [phy0]wlan0 on [phy0]wlan0mon"],
            "wlan0",
        )
        self.assertEqual(result, "wlan0mon")

    @patch("core.logic.shutil.which", return_value="/usr/sbin/iw")
    def test_interface_discovery_parses_iw_output(self, _mock_which: object) -> None:
        service = WirelessAuditService(environment=HARDWARE_ENVIRONMENT)
        iw_output = "phy#0\n\tInterface wlan2\n\t\ttype managed\n"
        with patch.object(service, "_run_quiet_command", return_value=iw_output):
            self.assertEqual(service.discover_interfaces(), ["wlan2"])

    def test_hardware_scan_lifecycle_and_managed_mode_restore(self) -> None:
        service = WirelessAuditService(environment=HARDWARE_ENVIRONMENT)
        fake_process = FakeProcess()
        commands: list[list[str]] = []

        def run_command(command: object, on_output: object = None) -> list[str]:
            del on_output
            normalized = list(command)
            commands.append(normalized)
            if normalized[:2] == ["airmon-ng", "start"]:
                return ["monitor mode enabled on wlan0mon"]
            return []

        with (
            TemporaryDirectory() as tmp,
            patch.object(service, "_require_tool"),
            patch.object(service, "_run_blocking_command", side_effect=run_command),
            patch.object(
                service,
                "_start_streaming_subprocess",
                return_value=fake_process,
            ),
            patch("core.logic.shutil.which", return_value="/usr/bin/tool"),
        ):
            monitor = service.start_monitor_mode("wlan0")
            session = service.start_target_scan(monitor, Path(tmp))
            self.assertEqual(session.monitor_interface, "wlan0mon")
            self.assertTrue(service.scan_active)
            self.assertTrue(service.stop_target_scan())
            service.restore_managed_mode()

        self.assertTrue(fake_process.terminated)
        self.assertIn(["airmon-ng", "stop", "wlan0mon"], commands)
        self.assertIn(["ip", "link", "set", "wlan0", "up"], commands)

    def test_unexpected_scanner_exit_is_reported(self) -> None:
        service = WirelessAuditService(environment=HARDWARE_ENVIRONMENT)
        with (
            TemporaryDirectory() as tmp,
            patch.object(service, "_require_tool"),
            patch.object(
                service,
                "_start_streaming_subprocess",
                return_value=FakeProcess(return_code=2),
            ),
        ):
            service.start_target_scan("wlan0mon", Path(tmp))
            with self.assertRaisesRegex(BackendError, "exited unexpectedly"):
                service.read_live_records()

    def test_empty_report_and_invalid_capture_are_rejected(self) -> None:
        service = WirelessAuditService(environment=MOCK_ENVIRONMENT)
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(BackendError, "no scan results"):
                service.export_report([], Path(tmp) / "report.json")
            invalid = Path(tmp) / "capture.txt"
            invalid.write_text("not a capture", encoding="utf-8")
            with self.assertRaisesRegex(BackendError, "existing .csv"):
                service.load_capture(invalid)


if __name__ == "__main__":
    unittest.main()
