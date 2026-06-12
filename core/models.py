"""Typed data models used across the Auto-Sentinel application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeEnvironment:
    """Represents the runtime operating environment.

    Attributes:
        platform_name: Human readable platform identifier.
        mock_mode: Whether hardware operations should be simulated.
        supported: Whether the platform is fully supported for hardware access.
    """

    platform_name: str
    mock_mode: bool
    supported: bool


@dataclass(slots=True)
class NetworkRecord:
    """Represents a discovered wireless network."""

    ssid: str
    bssid: str
    channel: str
    signal_dbm: int
    encryption: str
    privacy: str = ""
    cipher: str = ""
    authentication: str = ""
    first_seen: str = ""
    last_seen: str = ""

    def as_table_row(self) -> tuple[str, str, str, str, str]:
        """Returns a tuple formatted for the dashboard table."""
        return (
            self.ssid or "<hidden>",
            self.bssid,
            self.channel,
            str(self.signal_dbm),
            self.encryption,
        )


@dataclass(slots=True)
class ScanSession:
    """Tracks metadata for an active or recent scan session."""

    monitor_interface: str
    csv_path: Path


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    """Represents one runtime readiness check."""

    name: str
    passed: bool
    detail: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Aggregates runtime readiness checks for a scan request."""

    checks: tuple[PreflightCheck, ...]

    @property
    def ready(self) -> bool:
        """Returns whether all required checks passed."""

        return all(check.passed or not check.required for check in self.checks)

    def as_text(self) -> str:
        """Formats the report for console and GUI display."""

        heading = "Preflight ready" if self.ready else "Preflight blocked"
        lines = [heading]
        for check in self.checks:
            marker = "PASS" if check.passed else ("WARN" if not check.required else "FAIL")
            lines.append(f"[{marker}] {check.name}: {check.detail}")
        return "\n".join(lines)
