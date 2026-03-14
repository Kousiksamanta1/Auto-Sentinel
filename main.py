"""Auto-Sentinel entry point."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys

from core.logging_config import configure_logging


def _discover_qt_plugin_source() -> Path | None:
    """Discovers the PyQt6 plugin directory from the current Python environment."""

    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path(sys.prefix) / "lib" / py_version / "site-packages" / "PyQt6" / "Qt6" / "plugins",
        Path(sys.base_prefix) / "lib" / py_version / "site-packages" / "PyQt6" / "Qt6" / "plugins",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _prepare_macos_qt_runtime() -> None:
    """Mitigates Qt plugin loading issues for macOS/iCloud-hosted project paths."""

    if platform.system() != "Darwin":
        return

    plugin_source = _discover_qt_plugin_source()
    if plugin_source is None:
        return

    plugin_cache = Path("/tmp") / f"autosentinel_qt_plugins_{os.getpid()}"
    try:
        if plugin_cache.exists():
            shutil.rmtree(plugin_cache)
        plugin_cache.mkdir(parents=True, exist_ok=True)
        sync = subprocess.run(
            ["rsync", "-a", "--delete", f"{plugin_source}/", f"{plugin_cache}/"],
            check=False,
            capture_output=True,
            text=True,
        )
        if sync.returncode != 0:
            raise OSError(sync.stderr.strip() or "rsync plugin sync failed")
    except OSError as exc:
        print(f"[Auto-Sentinel] Warning: could not prepare macOS Qt plugin cache: {exc}", file=sys.stderr)
        return

    os.environ["QT_PLUGIN_PATH"] = str(plugin_cache)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_cache / "platforms")
    atexit.register(lambda: shutil.rmtree(plugin_cache, ignore_errors=True))


def main() -> int:
    """Bootstraps the Auto-Sentinel application."""

    _prepare_macos_qt_runtime()

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from core.controller import AppController
    from core.logic import WirelessAuditService
    from ui.main_window import AutoSentinelWindow
    from ui.styles import DARK_THEME_QSS

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
