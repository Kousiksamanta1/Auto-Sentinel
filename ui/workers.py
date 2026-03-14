"""Background worker objects used by the Qt controller."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class CallableWorker(QObject):
    """Runs a blocking callable inside a `QThread`."""

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self._task = task

    @pyqtSlot()
    def run(self) -> None:
        """Executes the configured task."""

        try:
            result = self._task()
        except Exception as exc:  # pylint: disable=broad-except
            self.failed.emit(str(exc))
            return

        self.finished.emit(result)


class PollingWorker(QObject):
    """Polls a callable at a fixed interval and emits snapshots."""

    snapshot = pyqtSignal(list)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, poller: Callable[[], list[object]], interval_ms: int = 1200) -> None:
        super().__init__()
        self._poller = poller
        self._interval_ms = interval_ms
        self._running = True

    @pyqtSlot()
    def run(self) -> None:
        """Starts the polling loop."""

        while self._running:
            try:
                self.snapshot.emit(self._poller())
            except Exception as exc:  # pylint: disable=broad-except
                self.failed.emit(str(exc))
                break
            QThread.msleep(self._interval_ms)

        self.finished.emit()

    def stop(self) -> None:
        """Stops the polling loop."""

        self._running = False
