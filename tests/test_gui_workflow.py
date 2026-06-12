"""Offscreen integration test for the mock GUI workflow."""

from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import main  # noqa: E402

main._prepare_macos_qt_runtime()  # pylint: disable=protected-access

from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.controller import AppController  # noqa: E402
from core.logic import WirelessAuditService  # noqa: E402
from core.models import RuntimeEnvironment  # noqa: E402
from ui.main_window import AutoSentinelWindow  # noqa: E402


class GuiWorkflowTests(unittest.TestCase):
    """Exercises the user-visible mock scan path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def wait_until(self, condition: object, timeout_ms: int = 4000) -> None:
        """Processes Qt events until a condition becomes true."""

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            self.app.processEvents()
            if condition():
                return
            QTest.qWait(25)
        self.fail("Timed out waiting for GUI state.")

    def test_scan_analyze_and_stop(self) -> None:
        environment = RuntimeEnvironment("Test", True, True)
        with TemporaryDirectory() as tmp:
            view = AutoSentinelWindow()
            view.output_dir_input.setText(str(Path(tmp) / "captures"))
            controller = AppController(
                view,
                WirelessAuditService(environment=environment),
            )

            self.wait_until(lambda: controller._active_tasks == 0)
            controller.handle_toggle_scan()
            self.wait_until(lambda: view.network_table.rowCount() == 6)
            self.assertEqual(view.start_scan_button.text(), "Stop Network Scan")

            controller.handle_analyze_results()
            self.wait_until(
                lambda: "Networks discovered: 6" in view.analysis_text.toPlainText()
            )

            controller.handle_toggle_scan()
            self.wait_until(lambda: view.start_scan_button.text() == "Start Network Scan")
            controller.shutdown()
            view.close()


if __name__ == "__main__":
    unittest.main()
