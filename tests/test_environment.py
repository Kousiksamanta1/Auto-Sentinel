"""Tests for runtime environment detection."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.environment import detect_environment


class EnvironmentTests(unittest.TestCase):
    """Validates platform-to-runtime mapping."""

    @patch("core.environment.platform.system", return_value="Linux")
    def test_linux_uses_hardware_mode(self, _mock_system: object) -> None:
        environment = detect_environment()
        self.assertFalse(environment.mock_mode)
        self.assertTrue(environment.supported)

    @patch("core.environment.platform.system", return_value="Darwin")
    def test_macos_uses_mock_mode(self, _mock_system: object) -> None:
        environment = detect_environment()
        self.assertTrue(environment.mock_mode)
        self.assertTrue(environment.supported)

    @patch("core.environment.platform.system", return_value="Windows")
    def test_other_platforms_use_best_effort_mock_mode(self, _mock_system: object) -> None:
        environment = detect_environment()
        self.assertEqual(environment.platform_name, "Windows")
        self.assertTrue(environment.mock_mode)
        self.assertFalse(environment.supported)


if __name__ == "__main__":
    unittest.main()
