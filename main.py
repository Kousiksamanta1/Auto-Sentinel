"""Auto-Sentinel entry point."""

from __future__ import annotations

import atexit
import signal
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from core.controller import AppController
from core.logging_config import configure_logging
from core.logic import WirelessAuditService
from ui.main_window import AutoSentinelWindow
from ui.styles import DARK_THEME_QSS


def main() -> int:
    """Bootstraps the Auto-Sentinel application."""

    logger = configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Sentinel")
    app.setStyleSheet(DARK_THEME_QSS)

    view = AutoSentinelWindow()
    service = WirelessAuditService()
    controller = AppController(view=view, service=service)

    def handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received signal %s. Initiating cleanup.", signum)
        controller.shutdown()
        app.quit()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    atexit.register(controller.shutdown)
    app.aboutToQuit.connect(controller.shutdown)

    signal_pump = QTimer()
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start(250)

    view.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
