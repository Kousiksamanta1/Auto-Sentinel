"""Typed data models used across the Auto-Sentinel application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class RuntimeEnvironment:
    """Represents the runtime operating environment.

    Attributes:
        platform_name: Human readable platform identifier.
        is_linux: Whether the runtime is Linux.
        is_macos: Whether the runtime is macOS.
        mock_mode: Whether hardware operations should be simulated.
        supported: Whether the platform is fully supported for hardware access.
    """

    platform_name: str
    is_linux: bool
    is_macos: bool
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

    base_interface: str
    monitor_interface: str
    output_prefix: Path
    csv_path: Path
    started_at: datetime
