"""CSV parsers for passive wireless scan output."""

from __future__ import annotations

import csv
from pathlib import Path

from core.logging_config import get_logger
from core.models import NetworkRecord


class AirodumpCsvParser:
    """Parses `airodump-ng` CSV snapshots into typed records."""

    def __init__(self) -> None:
        self._logger = get_logger("parser")

    def parse_access_points(self, csv_path: Path) -> list[NetworkRecord]:
        """Parses the access point section of an airodump CSV file.

        Args:
            csv_path: Path to the CSV file written by `airodump-ng`.

        Returns:
            list[NetworkRecord]: Parsed access point rows sorted by signal.
        """

        if not csv_path.exists():
            return []

        discovered: dict[str, NetworkRecord] = {}
        in_ap_section = False

        try:
            with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.reader(handle)
                for raw_row in reader:
                    row = [cell.strip() for cell in raw_row]
                    if not any(row):
                        if in_ap_section and discovered:
                            break
                        continue

                    first_cell = row[0] if row else ""
                    if first_cell == "BSSID":
                        in_ap_section = True
                        continue

                    if first_cell.startswith("Station MAC"):
                        break

                    if not in_ap_section or len(row) < 14:
                        continue

                    record = self._row_to_record(row)
                    if record:
                        discovered[record.bssid] = record
        except OSError as exc:
            self._logger.warning("Unable to parse %s: %s", csv_path, exc)
            return []
        except csv.Error as exc:
            self._logger.warning("Malformed CSV encountered in %s: %s", csv_path, exc)
            return []

        return sorted(discovered.values(), key=lambda item: item.signal_dbm, reverse=True)

    def _row_to_record(self, row: list[str]) -> NetworkRecord | None:
        """Converts a raw CSV row into a typed record."""

        bssid = row[0].upper()
        if len(bssid.split(":")) != 6:
            return None

        privacy = row[5] if len(row) > 5 else ""
        cipher = row[6] if len(row) > 6 else ""
        authentication = row[7] if len(row) > 7 else ""
        ssid = row[13] if len(row) > 13 else ""

        return NetworkRecord(
            ssid=ssid or "<hidden>",
            bssid=bssid,
            channel=row[3] if len(row) > 3 else "?",
            signal_dbm=self._safe_int(row[8] if len(row) > 8 else "-100", default=-100),
            encryption=self._compose_encryption(privacy, cipher, authentication),
            privacy=privacy,
            cipher=cipher,
            authentication=authentication,
            first_seen=row[1] if len(row) > 1 else "",
            last_seen=row[2] if len(row) > 2 else "",
        )

    def _compose_encryption(
        self,
        privacy: str,
        cipher: str,
        authentication: str,
    ) -> str:
        """Creates a user-friendly encryption label."""

        normalized_privacy = privacy.strip().upper()
        if normalized_privacy in {"OPN", "OPEN"}:
            return "Open"

        parts: list[str] = []
        for value in (privacy, cipher, authentication):
            cleaned = value.strip()
            if cleaned and cleaned not in parts:
                parts.append(cleaned)

        return " / ".join(parts) if parts else "Unknown"

    def _safe_int(self, value: str, default: int = 0) -> int:
        """Safely converts a string to an integer."""

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
