"""Qt controller connecting the GUI to backend logic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from core.logic import BackendError, WirelessAuditService
from core.logging_config import get_logger
from core.models import NetworkRecord, ScanSession
from ui.main_window import AutoSentinelWindow
from ui.workers import CallableWorker, PollingWorker


class AppController(QObject):
    """Mediates between the Qt view and backend model/service layer."""

    console_message = pyqtSignal(str)

    def __init__(self, view: AutoSentinelWindow, service: WirelessAuditService) -> None:
        super().__init__()
        self._view = view
        self._service = service
        self._logger = get_logger("controller")
        self._threads: set[QThread] = set()
        self._workers: set[QObject] = set()
        self._poll_thread: QThread | None = None
        self._poll_worker: PollingWorker | None = None
        self._latest_records: list[NetworkRecord] = []
        self._shutting_down = False

        self.console_message.connect(self._view.append_console)
        self._wire_signals()
        self._prime_view()

    def handle_toggle_scan(self) -> None:
        """Starts or stops live passive scanning."""

        if self._service.scan_active or self._poll_thread is not None:
            self._emit_telemetry("Initiating threaded network scan stop sequence.")
            self._view.set_scan_button_state(running=True, busy=True)

            def stop_task() -> object:
                return self._service.stop_target_scan(self._emit_telemetry)

            self._run_background_task(
                task=stop_task,
                on_success=self._on_scan_stopped,
                on_error=self._show_error,
                on_finished=lambda: self._view.set_scan_button_state(running=False, busy=False),
            )
            return

        requested_interface = self._view.current_interface()
        requested_mode = self._view.current_monitor_mode().lower()
        output_dir = Path(self._view.current_output_dir() or "captures")
        self._view.set_scan_button_state(running=False, busy=True)
        self._emit_telemetry(
            f"Initiating threaded network scan on interface {requested_interface}..."
        )

        def start_task() -> object:
            scan_interface = requested_interface
            if requested_mode == "monitor":
                self._emit_telemetry(f"Monitor mode requested for {requested_interface}.")
                scan_interface = self._service.start_monitor_mode(
                    requested_interface,
                    self._emit_telemetry,
                )
            return self._service.start_target_scan(scan_interface, output_dir, self._emit_telemetry)

        self._run_background_task(
            task=start_task,
            on_success=self._on_scan_started,
            on_error=self._show_error,
            on_finished=lambda: self._view.set_scan_button_state(
                running=self._poll_thread is not None,
                busy=False,
            ),
        )

    def handle_capture_handshake(self) -> None:
        """Triggers threaded handshake capture workflow."""

        interface = self._view.current_interface()
        target = self._view.target_bssid_input_value() or self._view.selected_bssid()
        self._emit_telemetry(
            f"Initiating threaded handshake capture on interface {interface}..."
        )

        def task() -> object:
            return self._service.capture_handshake(
                interface=interface,
                target_bssid=target,
                on_output=self._emit_telemetry,
            )

        self._run_background_task(
            task=task,
            on_success=self._on_text_result,
            on_error=self._show_error,
        )

    def handle_parse_capture(self) -> None:
        """Parses capture data in a worker thread and updates analysis output."""

        self._emit_telemetry("Initiating threaded capture parsing.")

        def task() -> object:
            return self._service.analyze_results(self._latest_records)

        self._run_background_task(
            task=task,
            on_success=self._on_parse_completed,
            on_error=self._show_error,
        )

    def handle_authorize_deauthentication(self) -> None:
        """Runs deauth authorization flow in a worker thread."""

        interface = self._view.current_interface()
        target = self._view.target_bssid_input_value() or self._view.selected_bssid()
        packet_count = self._view.deauth_packet_count()
        self._emit_telemetry(
            f"Initiating threaded deauthentication authorization on interface {interface}..."
        )

        def task() -> object:
            return self._service.authorize_deauthentication(
                interface=interface,
                target_bssid=target,
                packet_count=packet_count,
                on_output=self._emit_telemetry,
            )

        self._run_background_task(
            task=task,
            on_success=self._on_text_result,
            on_error=self._show_error,
        )

    def shutdown(self) -> None:
        """Stops background work and restores managed mode."""

        if self._shutting_down:
            return

        self._shutting_down = True
        self._emit_telemetry("Shutdown requested. Stopping scan threads and restoring interface state.")
        self._stop_polling()

        try:
            self._service.stop_target_scan(self._emit_telemetry)
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning("Failed to stop scan during shutdown: %s", exc)

        try:
            self._service.restore_managed_mode(self._emit_telemetry)
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning("Failed to restore managed mode during shutdown: %s", exc)

        for thread in list(self._threads):
            thread.quit()
            thread.wait(1500)
        self._threads.clear()
        self._workers.clear()

    def _wire_signals(self) -> None:
        """Connects view actions to controller slots."""

        self._view.start_scan_button.clicked.connect(self.handle_toggle_scan)
        self._view.capture_handshake_button.clicked.connect(self.handle_capture_handshake)
        self._view.parse_capture_button.clicked.connect(self.handle_parse_capture)
        self._view.authorize_deauth_button.clicked.connect(self.handle_authorize_deauthentication)
        self._view.closing.connect(self.shutdown)

    def _prime_view(self) -> None:
        """Initializes the view with runtime environment data."""

        environment = self._service.environment
        mode_label = "Mock Mode" if environment.mock_mode else "Hardware Mode"
        suffix = "" if environment.supported else " (best-effort)"
        self._view.set_environment(f"{environment.platform_name}{suffix}")
        self._view.set_runtime_status(mode_label)
        self._view.set_last_analysis("Analysis output will appear here once scan data is available.")

        if environment.mock_mode:
            self._emit_telemetry(
                "Mock mode is active. Synthetic Wi-Fi data will be used instead of hardware tools."
            )
        else:
            self._emit_telemetry(
                "Linux hardware mode detected. Run the app with the privileges required by aircrack-ng tooling."
            )

    def _run_background_task(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[str], None],
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Runs a blocking operation on a worker thread."""

        thread = QThread(self)
        worker = CallableWorker(task)
        worker.moveToThread(thread)

        self._threads.add(thread)
        self._workers.add(worker)

        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.failed.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(lambda: self._workers.discard(worker))
        if on_finished is not None:
            thread.finished.connect(on_finished)

        thread.start()

    def _start_polling(self) -> None:
        """Starts the live result polling worker."""

        self._stop_polling()

        thread = QThread(self)
        worker = PollingWorker(self._service.read_live_records, interval_ms=1200)
        worker.moveToThread(thread)

        self._poll_thread = thread
        self._poll_worker = worker
        self._threads.add(thread)
        self._workers.add(worker)

        thread.started.connect(worker.run)
        worker.snapshot.connect(self._on_records_updated)
        worker.failed.connect(self._show_error)
        worker.failed.connect(worker.stop)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(lambda: self._workers.discard(worker))
        thread.finished.connect(self._clear_polling_refs)
        thread.start()

    def _stop_polling(self) -> None:
        """Stops the live result polling worker."""

        if self._poll_worker is not None:
            self._poll_worker.stop()

        if self._poll_thread is not None:
            self._poll_thread.quit()
            self._poll_thread.wait(1500)
            self._clear_polling_refs()

    def _clear_polling_refs(self) -> None:
        """Clears polling worker references after shutdown."""

        self._poll_thread = None
        self._poll_worker = None

    def _on_scan_started(self, result: object) -> None:
        """Handles a successful scan start."""

        session = result
        if not isinstance(session, ScanSession):
            raise BackendError("Unexpected scan session result.")

        self._start_polling()
        self._view.set_runtime_status(f"Scanning: {session.monitor_interface}")
        self._view.set_scan_button_state(running=True, busy=False)
        self._emit_telemetry(f"Scan session output: {session.csv_path}")

    def _on_scan_stopped(self, _: object) -> None:
        """Handles scan stop completion."""

        self._stop_polling()
        self._view.set_runtime_status("Idle")
        self._view.set_scan_button_state(running=False, busy=False)
        self._emit_telemetry("Target scan stopped.")

    def _on_records_updated(self, records: list[object]) -> None:
        """Pushes live results into the dashboard."""

        typed_records = [record for record in records if isinstance(record, NetworkRecord)]
        self._latest_records = typed_records
        self._view.update_scan_results(typed_records)

    def _on_parse_completed(self, result: object) -> None:
        """Updates analysis panel after threaded parse completion."""

        summary = str(result)
        self._view.set_last_analysis(summary)
        self._emit_telemetry(summary)

    def _on_text_result(self, result: object) -> None:
        """Emits text results returned by threaded tasks."""

        self._emit_telemetry(str(result))

    def _emit_telemetry(self, message: str) -> None:
        """Writes an informational message to both logs and the console stream."""

        self._logger.info(message)
        self.console_message.emit(message)

    def _show_error(self, message: str) -> None:
        """Displays an error consistently in the UI and console."""

        self._logger.error("Error: %s", message)
        self.console_message.emit(f"Error: {message}")
        QMessageBox.critical(self._view, "Auto-Sentinel Error", message)
