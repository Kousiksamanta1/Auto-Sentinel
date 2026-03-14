"""Backend services and platform integrations for Auto-Sentinel."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import random
import re
import shutil
import subprocess
from pathlib import Path
from threading import Lock, Thread
from typing import Callable, Sequence

import pandas as pd

from core.environment import detect_environment
from core.logging_config import get_logger
from core.models import NetworkRecord, RuntimeEnvironment, ScanSession
from core.parsers import AirodumpCsvParser


OutputCallback = Callable[[str], None]


class BackendError(RuntimeError):
    """Raised when a backend operation cannot be completed safely."""


class MockWifiDataSource:
    """Generates realistic synthetic Wi-Fi data for GUI testing."""

    def __init__(self) -> None:
        self._logger = get_logger("mock")
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

        self._random.shuffle(records)
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
        self._base_interface = ""
        self._monitor_interface = ""

    @property
    def scan_active(self) -> bool:
        """Returns whether a passive scan subprocess is active."""

        return self._scan_process is not None and self._scan_process.poll() is None

    @property
    def monitor_interface(self) -> str:
        """Returns the active monitor interface if known."""

        return self._monitor_interface

    @property
    def current_session(self) -> ScanSession | None:
        """Returns the active or most recent scan session."""

        return self._scan_session

    def start_monitor_mode(self, interface: str, on_output: OutputCallback | None = None) -> str:
        """Enables monitor mode on a wireless interface.

        Args:
            interface: Wireless interface name, such as `wlan0`.
            on_output: Optional callback for streaming output messages.

        Returns:
            str: The resulting monitor-mode interface.

        Raises:
            BackendError: If the operation cannot be completed.
        """

        normalized_interface = self._validated_interface(interface)

        if self.environment.mock_mode:
            self._base_interface = normalized_interface
            self._monitor_interface = f"{normalized_interface}_mockmon"
            self._emit(on_output, "Mock mode enabled: no hardware changes were made.")
            self._emit(
                on_output,
                f"Synthetic monitor interface ready on {self._monitor_interface}.",
            )
            return self._monitor_interface

        self._require_tool("airmon-ng")
        self._emit(on_output, f"Starting monitor mode on {normalized_interface}...")
        output_lines = self._run_blocking_command(
            ["airmon-ng", "start", normalized_interface],
            on_output=on_output,
        )

        self._base_interface = normalized_interface
        self._monitor_interface = self._extract_monitor_interface(output_lines, normalized_interface)
        self._emit(on_output, f"Monitor mode active on {self._monitor_interface}.")
        return self._monitor_interface

    def start_target_scan(
        self,
        interface: str,
        output_root: Path,
        on_output: OutputCallback | None = None,
    ) -> ScanSession:
        """Starts a passive target scan using `airodump-ng`.

        Args:
            interface: Monitor-mode interface to use for scanning.
            output_root: Directory where capture output should be stored.
            on_output: Optional callback for streaming console output.

        Returns:
            ScanSession: Metadata describing the created scan session.

        Raises:
            BackendError: If the scan cannot be started.
        """

        normalized_interface = self._validated_interface(interface)
        if not self.environment.mock_mode and self.scan_active:
            raise BackendError("A target scan is already active.")

        output_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_dir = output_root / f"scan_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        output_prefix = session_dir / "autosentinel"
        csv_path = session_dir / "autosentinel-01.csv"

        self._base_interface = self._base_interface or normalized_interface
        self._monitor_interface = normalized_interface
        self._scan_session = ScanSession(
            base_interface=self._base_interface,
            monitor_interface=normalized_interface,
            output_prefix=output_prefix,
            csv_path=csv_path,
            started_at=datetime.now(timezone.utc),
        )

        if self.environment.mock_mode:
            self._emit(on_output, "Mock scan started. Streaming synthetic wireless inventory.")
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
        """Stops an active passive scan, if one exists.

        Args:
            on_output: Optional callback for streaming console output.

        Returns:
            bool: True when a running scan was stopped.
        """

        if self.environment.mock_mode:
            self._emit(on_output, "Mock scan stopped.")
            return False

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
                self._emit(on_output, "Scan process did not exit cleanly; forcing termination.")
                process.kill()
                process.wait(timeout=3)

        return True

    def restore_managed_mode(self, on_output: OutputCallback | None = None) -> None:
        """Restores the interface to managed mode on exit."""

        if self.environment.mock_mode:
            self._emit(on_output, "Cleanup complete in mock mode.")
            return

        if not self._monitor_interface:
            return

        self._emit(on_output, f"Restoring managed mode from {self._monitor_interface}...")
        try:
            self._best_effort_command(["airmon-ng", "stop", self._monitor_interface], on_output)
            if self._base_interface:
                self._best_effort_command(["ip", "link", "set", self._base_interface, "up"], on_output)
                if shutil.which("iwconfig"):
                    self._best_effort_command(
                        ["iwconfig", self._base_interface, "mode", "managed"],
                        on_output,
                    )
        finally:
            self._monitor_interface = ""
            self._emit(on_output, "Managed mode cleanup completed.")

    def read_live_records(self) -> list[NetworkRecord]:
        """Returns the latest available scan records."""

        if self.environment.mock_mode:
            return self._mock_data.snapshot()

        if not self._scan_session:
            return []

        return self._parser.parse_access_points(self._scan_session.csv_path)

    def analyze_results(self, records: Sequence[NetworkRecord]) -> str:
        """Produces a concise analytical summary of discovered networks.

        Args:
            records: Collected network records.

        Returns:
            str: Human-readable analysis text.
        """

        if not records:
            return "No scan results are available yet."

        frame = pd.DataFrame([asdict(record) for record in records])
        frame["channel"] = frame["channel"].astype(str)
        frame["encryption"] = frame["encryption"].replace("", "Unknown")

        strongest_index = frame["signal_dbm"].astype(int).idxmax()
        strongest = frame.loc[strongest_index]
        busy_channels = frame["channel"].value_counts().head(3)
        security_mix = frame["encryption"].value_counts().head(4)

        lines = [
            f"Networks discovered: {len(frame)}",
            (
                "Strongest signal: "
                f"{strongest['ssid']} ({strongest['bssid']}) on channel {strongest['channel']} "
                f"at {strongest['signal_dbm']} dBm"
            ),
            "Busiest channels: " + ", ".join(
                f"ch {channel} ({count})" for channel, count in busy_channels.items()
            ),
            "Security mix: " + ", ".join(
                f"{encryption} ({count})" for encryption, count in security_mix.items()
            ),
        ]
        return "\n".join(lines)

    def capture_handshake(
        self,
        interface: str,
        target_bssid: str | None = None,
        on_output: OutputCallback | None = None,
    ) -> str:
        """Runs a safe, threaded handshake-capture flow.

        In mock mode this emits simulated success text. In hardware mode this
        intentionally stays non-automated and returns a guarded notice.
        """

        normalized_interface = self._validated_interface(interface)
        target = target_bssid.strip().upper() if target_bssid else "unspecified target"

        if self.environment.mock_mode:
            message = (
                "Mock mode: simulated handshake capture started on "
                f"{normalized_interface} for {target}."
            )
            self._emit(on_output, message)
            return message

        message = (
            "Handshake capture automation is intentionally guarded in this build. "
            f"Requested interface={normalized_interface}, target={target}."
        )
        self._logger.warning(message)
        self._emit(on_output, message)
        return message

    def authorize_deauthentication(
        self,
        interface: str,
        target_bssid: str | None,
        packet_count: int,
        on_output: OutputCallback | None = None,
    ) -> str:
        """Runs a safe deauth-authorization workflow with validation."""

        normalized_interface = self._validated_interface(interface)
        if not target_bssid:
            raise BackendError("Target BSSID is required before authorizing deauthentication.")
        if packet_count <= 0:
            raise BackendError("Deauth packet count must be a positive integer.")

        target = target_bssid.strip().upper()
        if self.environment.mock_mode:
            message = (
                "Mock mode: deauthentication authorization simulated for "
                f"{target} on {normalized_interface} with {packet_count} packets."
            )
            self._emit(on_output, message)
            return message

        message = (
            "Deauthentication execution is intentionally non-automated in this build. "
            f"Authorization request logged for target={target}, packets={packet_count}, "
            f"interface={normalized_interface}."
        )
        self._logger.warning(message)
        self._emit(on_output, message)
        return message

    def deauth_capture_handshake(self, target_bssid: str | None = None) -> str:
        """Returns a guardrail message for intentionally omitted active attack flows."""

        target_clause = f" for {target_bssid}" if target_bssid else ""
        message = (
            "Active deauthentication or handshake-capture automation"
            f"{target_clause} is intentionally not implemented in this build. "
            "Passive discovery, analysis, logging, threading, and mock mode remain available."
        )
        self._logger.warning(message)
        return message

    def _validated_interface(self, interface: str) -> str:
        """Normalizes and validates a wireless interface name."""

        normalized = interface.strip()
        if not normalized:
            raise BackendError("A wireless interface name is required.")
        return normalized

    def _require_tool(self, tool_name: str) -> None:
        """Ensures a required command-line dependency exists."""

        if shutil.which(tool_name):
            return
        raise BackendError(
            f"Required tool '{tool_name}' was not found in PATH. Install aircrack-ng tooling first."
        )

    def _run_blocking_command(
        self,
        command: Sequence[str],
        on_output: OutputCallback | None = None,
    ) -> list[str]:
        """Runs a blocking command and streams combined stdout/stderr."""

        self._logger.info("Executing command: %s", " ".join(command))
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

        output_lines: list[str] = []
        if process.stdout is None:
            raise BackendError(f"Command produced no stdout stream: {' '.join(command)}")

        for raw_line in process.stdout:
            line = raw_line.rstrip()
            if not line:
                continue
            output_lines.append(line)
            self._emit(on_output, line)
            self._logger.info(line)

        return_code = process.wait()
        if return_code != 0:
            raise BackendError(f"Command failed with exit code {return_code}: {' '.join(command)}")

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
            if not line:
                continue
            self._emit(on_output, line)
            self._logger.info(line)

    def _extract_monitor_interface(self, output_lines: Sequence[str], fallback: str) -> str:
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
                    return match.group(1)

        if fallback.endswith("mon"):
            return fallback
        return f"{fallback}mon"

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

    def _emit(self, on_output: OutputCallback | None, message: str) -> None:
        """Safely emits output to both the callback and logger."""

        if on_output:
            on_output(message)
