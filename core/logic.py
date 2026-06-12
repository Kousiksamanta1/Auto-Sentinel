"""Backend services and platform integrations for Auto-Sentinel."""

from __future__ import annotations

import csv
import json
import os
import random
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread

from core.environment import detect_environment
from core.logging_config import get_logger
from core.models import (
    NetworkRecord,
    PreflightCheck,
    PreflightReport,
    RuntimeEnvironment,
    ScanSession,
)
from core.parsers import AirodumpCsvParser

OutputCallback = Callable[[str], None]
INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")


class BackendError(RuntimeError):
    """Raised when a backend operation cannot be completed safely."""


class MockWifiDataSource:
    """Generates realistic synthetic Wi-Fi data for GUI testing."""

    def __init__(self) -> None:
        self._random = random.Random(1337)
        self._templates: list[dict[str, str | int]] = [
            {
                "ssid": "ACME-Guest",
                "bssid": "AA:10:4F:21:00:11",
                "channel": "1",
                "signal_dbm": -44,
                "encryption": "WPA2 / CCMP / PSK",
            },
            {
                "ssid": "BlueTeam-Lab",
                "bssid": "AA:10:4F:21:00:12",
                "channel": "6",
                "signal_dbm": -59,
                "encryption": "WPA2 / CCMP / PSK",
            },
            {
                "ssid": "SOC-WiFi",
                "bssid": "AA:10:4F:21:00:13",
                "channel": "11",
                "signal_dbm": -50,
                "encryption": "WPA3 / SAE",
            },
            {
                "ssid": "Legacy-IoT",
                "bssid": "AA:10:4F:21:00:14",
                "channel": "3",
                "signal_dbm": -74,
                "encryption": "WPA / TKIP / PSK",
            },
            {
                "ssid": "Visitor-Network",
                "bssid": "AA:10:4F:21:00:15",
                "channel": "9",
                "signal_dbm": -67,
                "encryption": "Open",
            },
            {
                "ssid": "<hidden>",
                "bssid": "AA:10:4F:21:00:16",
                "channel": "44",
                "signal_dbm": -64,
                "encryption": "WPA2 / CCMP / Enterprise",
            },
        ]

    def snapshot(self) -> list[NetworkRecord]:
        """Returns a fluctuating mock snapshot of nearby networks."""

        records: list[NetworkRecord] = []
        for template in self._templates:
            swing = self._random.randint(-4, 4)
            signal_dbm = max(-92, min(-32, int(template["signal_dbm"]) + swing))
            records.append(
                NetworkRecord(
                    ssid=str(template["ssid"]),
                    bssid=str(template["bssid"]),
                    channel=str(template["channel"]),
                    signal_dbm=signal_dbm,
                    encryption=str(template["encryption"]),
                )
            )

        return sorted(records, key=lambda record: record.signal_dbm, reverse=True)


class WirelessAuditService:
    """Coordinates passive wireless auditing operations."""

    def __init__(
        self,
        environment: RuntimeEnvironment | None = None,
        parser: AirodumpCsvParser | None = None,
    ) -> None:
        self.environment = environment or detect_environment()
        self._parser = parser or AirodumpCsvParser()
        self._logger = get_logger("logic")
        self._mock_data = MockWifiDataSource()
        self._process_lock = Lock()
        self._scan_process: subprocess.Popen[str] | None = None
        self._scan_session: ScanSession | None = None
        self._mock_scan_active = False
        self._base_interface = ""
        self._monitor_interface = ""
        self._monitor_started_by_app = False
        self._expected_scan_stop = False

    @property
    def scan_active(self) -> bool:
        """Returns whether a passive scan is active."""

        if self.environment.mock_mode:
            return self._mock_scan_active
        return self._scan_process is not None and self._scan_process.poll() is None

    def discover_interfaces(self) -> list[str]:
        """Discovers wireless interfaces available to the current runtime."""

        if self.environment.mock_mode:
            return ["wlan0", "wlan1"]

        discovered: set[str] = set()
        if shutil.which("iw"):
            result = self._run_quiet_command(["iw", "dev"])
            for line in result.splitlines():
                match = re.match(r"\s*Interface\s+(\S+)", line)
                if match:
                    discovered.add(match.group(1))

        sys_class_net = Path("/sys/class/net")
        if sys_class_net.is_dir():
            for candidate in sys_class_net.iterdir():
                if (candidate / "wireless").exists():
                    discovered.add(candidate.name)

        if not discovered and shutil.which("airmon-ng"):
            result = self._run_quiet_command(["airmon-ng"])
            for line in result.splitlines():
                fields = line.split()
                if len(fields) >= 2 and fields[0].lower() != "phy":
                    candidate = fields[1]
                    if INTERFACE_PATTERN.fullmatch(candidate):
                        discovered.add(candidate)

        return sorted(discovered)

    def run_preflight(
        self,
        interface: str,
        output_root: Path,
        request_monitor_mode: bool,
    ) -> PreflightReport:
        """Checks whether the requested passive scan can start."""

        checks: list[PreflightCheck] = []
        try:
            normalized_interface = self._validated_interface(interface)
            checks.append(PreflightCheck("Interface name", True, normalized_interface))
        except BackendError as exc:
            checks.append(PreflightCheck("Interface name", False, str(exc)))
            normalized_interface = ""

        try:
            resolved_output = self._prepare_output_root(output_root)
            checks.append(PreflightCheck("Capture directory", True, str(resolved_output)))
        except BackendError as exc:
            checks.append(PreflightCheck("Capture directory", False, str(exc)))

        if self.environment.mock_mode:
            checks.append(
                PreflightCheck(
                    "Runtime mode",
                    True,
                    "Mock mode uses synthetic data and does not access wireless hardware.",
                )
            )
            return PreflightReport(tuple(checks))

        for tool in ("airodump-ng", "airmon-ng", "ip"):
            path = shutil.which(tool)
            checks.append(
                PreflightCheck(
                    f"Tool: {tool}",
                    path is not None,
                    path or "Not found in PATH",
                )
            )

        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
        checks.append(
            PreflightCheck(
                "Privileges",
                is_root,
                "Running as root" if is_root else "Start with sudo for monitor-mode operations",
            )
        )

        interfaces = self.discover_interfaces()
        interface_present = bool(normalized_interface and normalized_interface in interfaces)
        checks.append(
            PreflightCheck(
                "Wireless interface",
                interface_present,
                (
                    f"{normalized_interface} detected"
                    if interface_present
                    else f"Detected interfaces: {', '.join(interfaces) or 'none'}"
                ),
            )
        )

        if not request_monitor_mode and normalized_interface:
            checks.append(
                PreflightCheck(
                    "Monitor mode",
                    normalized_interface.endswith("mon"),
                    (
                        "Existing monitor interface selected"
                        if normalized_interface.endswith("mon")
                        else "Select Monitor mode unless this interface is already in monitor mode"
                    ),
                    required=False,
                )
            )

        return PreflightReport(tuple(checks))

    def start_monitor_mode(
        self,
        interface: str,
        on_output: OutputCallback | None = None,
    ) -> str:
        """Enables monitor mode on a wireless interface."""

        normalized_interface = self._validated_interface(interface)
        if normalized_interface.endswith("mon"):
            self._base_interface = normalized_interface
            self._monitor_interface = normalized_interface
            self._monitor_started_by_app = False
            self._emit(on_output, f"Using existing monitor interface {normalized_interface}.")
            return normalized_interface

        if self.environment.mock_mode:
            self._base_interface = normalized_interface
            self._monitor_interface = f"{normalized_interface}_mockmon"
            self._monitor_started_by_app = True
            self._emit(on_output, "Mock mode enabled: no hardware changes were made.")
            return self._monitor_interface

        self._require_tool("airmon-ng")
        self._emit(on_output, f"Starting monitor mode on {normalized_interface}...")
        output_lines = self._run_blocking_command(
            ["airmon-ng", "start", normalized_interface],
            on_output=on_output,
        )

        self._base_interface = normalized_interface
        self._monitor_interface = self._extract_monitor_interface(
            output_lines,
            normalized_interface,
        )
        self._monitor_started_by_app = True
        self._emit(on_output, f"Monitor mode active on {self._monitor_interface}.")
        return self._monitor_interface

    def start_target_scan(
        self,
        interface: str,
        output_root: Path,
        on_output: OutputCallback | None = None,
    ) -> ScanSession:
        """Starts a passive network scan using ``airodump-ng``."""

        normalized_interface = self._validated_interface(interface)
        if self.scan_active:
            raise BackendError("A passive scan is already active.")

        resolved_output = self._prepare_output_root(output_root)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        session_dir = resolved_output / f"scan_{timestamp}"
        try:
            session_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise BackendError(f"Unable to create scan directory: {exc}") from exc

        output_prefix = session_dir / "autosentinel"
        csv_path = session_dir / "autosentinel-01.csv"
        self._base_interface = self._base_interface or normalized_interface
        self._monitor_interface = normalized_interface
        self._scan_session = ScanSession(
            monitor_interface=normalized_interface,
            csv_path=csv_path,
        )
        self._expected_scan_stop = False

        if self.environment.mock_mode:
            self._mock_scan_active = True
            self._write_mock_csv(self._mock_data.snapshot(), csv_path)
            self._emit(on_output, "Mock scan started. Synthetic results are saved as CSV.")
            return self._scan_session

        self._require_tool("airodump-ng")
        command = [
            "airodump-ng",
            "--write-interval",
            "1",
            "--output-format",
            "csv",
            "-w",
            str(output_prefix),
            normalized_interface,
        ]
        self._emit(on_output, f"Launching passive scan on {normalized_interface}...")
        with self._process_lock:
            self._scan_process = self._start_streaming_subprocess(command, on_output)

        return self._scan_session

    def stop_target_scan(self, on_output: OutputCallback | None = None) -> bool:
        """Stops an active passive scan, if one exists."""

        if self.environment.mock_mode:
            was_active = self._mock_scan_active
            self._mock_scan_active = False
            if was_active:
                self._emit(on_output, "Mock scan stopped.")
            return was_active

        self._expected_scan_stop = True
        with self._process_lock:
            process = self._scan_process
            self._scan_process = None

        if process is None:
            return False

        if process.poll() is None:
            self._emit(on_output, "Stopping passive scan...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._emit(on_output, "Scan process did not exit; forcing termination.")
                process.kill()
                process.wait(timeout=3)
        return True

    def restore_managed_mode(self, on_output: OutputCallback | None = None) -> None:
        """Restores an interface changed to monitor mode by this application."""

        if self.environment.mock_mode:
            self._monitor_interface = ""
            self._monitor_started_by_app = False
            return

        if not self._monitor_interface or not self._monitor_started_by_app:
            return

        self._emit(on_output, f"Restoring managed mode from {self._monitor_interface}...")
        try:
            self._best_effort_command(["airmon-ng", "stop", self._monitor_interface], on_output)
            if self._base_interface:
                self._best_effort_command(
                    ["ip", "link", "set", self._base_interface, "up"],
                    on_output,
                )
                if shutil.which("iwconfig"):
                    self._best_effort_command(
                        ["iwconfig", self._base_interface, "mode", "managed"],
                        on_output,
                    )
        finally:
            self._monitor_interface = ""
            self._monitor_started_by_app = False
            self._emit(on_output, "Managed mode restoration completed.")

    def read_live_records(self) -> list[NetworkRecord]:
        """Returns the latest available scan records."""

        if not self._scan_session:
            return []

        if self.environment.mock_mode:
            if not self._mock_scan_active:
                return self._parser.parse_access_points(self._scan_session.csv_path)
            records = self._mock_data.snapshot()
            self._write_mock_csv(records, self._scan_session.csv_path)
            return records

        process = self._scan_process
        if process is not None:
            return_code = process.poll()
            if return_code is not None and not self._expected_scan_stop:
                raise BackendError(
                    f"airodump-ng exited unexpectedly with status {return_code}."
                )

        return self._parser.parse_access_points(self._scan_session.csv_path)

    def load_capture(self, csv_path: Path) -> list[NetworkRecord]:
        """Loads access-point records from an airodump-ng CSV capture."""

        resolved_path = csv_path.expanduser().resolve()
        if not self._parser.supports(resolved_path):
            raise BackendError("Select an existing .csv capture file.")

        records = self._parser.parse_access_points(resolved_path)
        if not records:
            raise BackendError(
                "No access-point records were found. Ensure this is an airodump-ng CSV file."
            )
        return records

    def analyze_results(self, records: Sequence[NetworkRecord]) -> str:
        """Produces a concise analytical summary of discovered networks."""

        if not records:
            return "No scan results are available yet."

        strongest = max(records, key=lambda record: record.signal_dbm)
        busy_channels = Counter(str(record.channel) for record in records).most_common(3)
        security_mix = Counter(
            record.encryption or "Unknown" for record in records
        ).most_common(4)
        open_count = sum(
            (record.encryption or "Unknown").lower() == "open" for record in records
        )

        lines = [
            f"Networks discovered: {len(records)}",
            f"Open networks: {open_count}",
            (
                "Strongest signal: "
                f"{strongest.ssid} ({strongest.bssid}) on channel "
                f"{strongest.channel} at {strongest.signal_dbm} dBm"
            ),
            "Busiest channels: "
            + ", ".join(
                f"ch {channel} ({count})"
                for channel, count in busy_channels
            ),
            "Security mix: "
            + ", ".join(
                f"{encryption} ({count})"
                for encryption, count in security_mix
            ),
        ]
        return "\n".join(lines)

    def export_report(
        self,
        records: Sequence[NetworkRecord],
        destination: Path,
    ) -> Path:
        """Exports the current passive analysis as a JSON report."""

        if not records:
            raise BackendError("There are no scan results to export.")

        resolved = destination.expanduser().resolve()
        if resolved.suffix.lower() != ".json":
            resolved = resolved.with_suffix(".json")
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "application": "Auto-Sentinel",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": self.analyze_results(records),
                "networks": [asdict(record) for record in records],
            }
            resolved.write_text(
                json.dumps(payload, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise BackendError(f"Unable to write report: {exc}") from exc
        return resolved

    def _validated_interface(self, interface: str) -> str:
        """Normalizes and validates a wireless interface name."""

        normalized = interface.strip()
        if not normalized:
            raise BackendError("A wireless interface name is required.")
        if not INTERFACE_PATTERN.fullmatch(normalized):
            raise BackendError(
                "Interface names may contain letters, numbers, dots, colons, dashes, "
                "and underscores only."
            )
        return normalized

    def _prepare_output_root(self, output_root: Path) -> Path:
        """Creates and verifies a writable capture directory."""

        try:
            resolved = output_root.expanduser().resolve()
            resolved.mkdir(parents=True, exist_ok=True)
            probe = resolved / ".autosentinel-write-test"
            probe.write_text("ok", encoding="ascii")
            probe.unlink()
            return resolved
        except OSError as exc:
            raise BackendError(f"Capture directory is not writable: {exc}") from exc

    def _require_tool(self, tool_name: str) -> None:
        """Ensures a required command-line dependency exists."""

        if shutil.which(tool_name):
            return
        raise BackendError(
            f"Required tool '{tool_name}' was not found in PATH. "
            "Install aircrack-ng tooling first."
        )

    def _run_quiet_command(self, command: Sequence[str]) -> str:
        """Runs a short discovery command without raising on failure."""

        try:
            result = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stdout

    def _run_blocking_command(
        self,
        command: Sequence[str],
        on_output: OutputCallback | None = None,
    ) -> list[str]:
        """Runs a bounded command and forwards its combined output."""

        self._logger.info("Executing command: %s", " ".join(command))
        try:
            result = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendError(f"Command timed out: {' '.join(command)}") from exc
        except OSError as exc:
            raise BackendError(f"Unable to launch command {' '.join(command)}: {exc}") from exc

        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        output_lines = [line.strip() for line in combined.splitlines() if line.strip()]
        for line in output_lines:
            self._emit(on_output, line)

        if result.returncode != 0:
            raise BackendError(
                f"Command failed with exit code {result.returncode}: {' '.join(command)}"
            )
        return output_lines

    def _start_streaming_subprocess(
        self,
        command: Sequence[str],
        on_output: OutputCallback | None = None,
    ) -> subprocess.Popen[str]:
        """Starts a long-running subprocess and forwards output asynchronously."""

        self._logger.info("Starting streaming command: %s", " ".join(command))
        try:
            process = subprocess.Popen(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise BackendError(f"Unable to launch command {' '.join(command)}: {exc}") from exc

        output_thread = Thread(
            target=self._consume_process_output,
            args=(process, on_output),
            daemon=True,
        )
        output_thread.start()
        return process

    def _consume_process_output(
        self,
        process: subprocess.Popen[str],
        on_output: OutputCallback | None = None,
    ) -> None:
        """Consumes subprocess output without blocking the GUI."""

        if process.stdout is None:
            return
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            if line:
                self._emit(on_output, line)

    def _extract_monitor_interface(
        self,
        output_lines: Sequence[str],
        fallback: str,
    ) -> str:
        """Best-effort parser for monitor-mode interface names."""

        patterns = [
            re.compile(r"on\s+\[[^\]]+\](\S+)$", re.IGNORECASE),
            re.compile(r"monitor mode .* on (\S+)$", re.IGNORECASE),
            re.compile(r"enabled on (\S+)$", re.IGNORECASE),
        ]
        for line in output_lines:
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    return match.group(1).rstrip(")")
        return fallback if fallback.endswith("mon") else f"{fallback}mon"

    def _best_effort_command(
        self,
        command: Sequence[str],
        on_output: OutputCallback | None = None,
    ) -> None:
        """Executes a cleanup command and suppresses non-fatal failures."""

        try:
            self._run_blocking_command(command, on_output)
        except BackendError as exc:
            self._logger.warning("Cleanup command failed: %s", exc)
            self._emit(on_output, f"Cleanup warning: {exc}")

    def _write_mock_csv(
        self,
        records: Sequence[NetworkRecord],
        csv_path: Path,
    ) -> None:
        """Writes mock records in the airodump-ng CSV shape."""

        header = [
            "BSSID",
            "First time seen",
            "Last time seen",
            "channel",
            "Speed",
            "Privacy",
            "Cipher",
            "Authentication",
            "Power",
            "# beacons",
            "# IV",
            "LAN IP",
            "ID-length",
            "ESSID",
            "Key",
        ]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                for record in records:
                    privacy, cipher, authentication = self._encryption_parts(record)
                    writer.writerow(
                        [
                            record.bssid,
                            now,
                            now,
                            record.channel,
                            "54",
                            privacy,
                            cipher,
                            authentication,
                            record.signal_dbm,
                            "1",
                            "0",
                            "0.0.0.0",
                            len(record.ssid),
                            "" if record.ssid == "<hidden>" else record.ssid,
                            "",
                        ]
                    )
                writer.writerow([])
                writer.writerow(
                    [
                        "Station MAC",
                        "First time seen",
                        "Last time seen",
                        "Power",
                        "# packets",
                        "BSSID",
                        "Probed ESSIDs",
                    ]
                )
        except OSError as exc:
            raise BackendError(f"Unable to write mock capture: {exc}") from exc

    def _encryption_parts(self, record: NetworkRecord) -> tuple[str, str, str]:
        """Returns airodump-style security columns for a mock record."""

        if record.encryption.lower() == "open":
            return ("OPN", "", "")
        parts = [part.strip() for part in record.encryption.split("/")]
        padded = parts + ["", "", ""]
        return (padded[0], padded[1], padded[2])

    def _emit(self, on_output: OutputCallback | None, message: str) -> None:
        """Emits output to the callback and application log."""

        self._logger.info(message)
        if on_output:
            on_output(message)
