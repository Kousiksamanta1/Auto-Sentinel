"""Tests for airodump-ng CSV parsing."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.parsers import AirodumpCsvParser

SAMPLE_CSV = """BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
AA:BB:CC:DD:EE:FF, 2026-01-01, 2026-01-01, 6, 54, WPA2, CCMP, PSK, -42, 1, 0, 0.0.0.0, 4, Test,
11:22:33:44:55:66, 2026-01-01, 2026-01-01, 11, 54, OPN, , , -70, 1, 0, 0.0.0.0, 0, ,

Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
"""


class ParserTests(unittest.TestCase):
    """Covers valid, absent, and unsupported capture inputs."""

    def test_parses_and_sorts_access_points(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            path.write_text(SAMPLE_CSV, encoding="utf-8")

            records = AirodumpCsvParser().parse_access_points(path)

        self.assertEqual([record.bssid for record in records], [
            "AA:BB:CC:DD:EE:FF",
            "11:22:33:44:55:66",
        ])
        self.assertEqual(records[0].ssid, "Test")
        self.assertEqual(records[0].signal_dbm, -42)
        self.assertEqual(records[1].ssid, "<hidden>")
        self.assertEqual(records[1].encryption, "Open")

    def test_missing_file_returns_empty_result(self) -> None:
        records = AirodumpCsvParser().parse_access_points(Path("/missing/capture.csv"))
        self.assertEqual(records, [])

    def test_supports_only_existing_csv_files(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "capture.csv"
            text_path = Path(tmp) / "capture.txt"
            csv_path.touch()
            text_path.touch()
            parser = AirodumpCsvParser()
            self.assertTrue(parser.supports(csv_path))
            self.assertFalse(parser.supports(text_path))


if __name__ == "__main__":
    unittest.main()
