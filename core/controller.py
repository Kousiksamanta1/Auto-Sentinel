"""Qt controller connecting the GUI to backend logic."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from core.logging_config import get_logger
from core.logic import BackendError, WirelessAuditService
from core.models import NetworkRecord, PreflightReport, ScanSession
from ui.main_window import AutoSentinelWindow
from ui.workers import CallableWorker, PollingWorker


class AppController(QObject):
    """Mediates between the Qt view and backend service layer."""

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
        self._active_tasks = 0
        self._shutting_down = False

        self.console_message.connect(self._view.append_console)
        self._wire_signals()
        self._prime_view()

    def handle_refresh_interfaces(self) -> None:
        """Discovers wireless interfaces without blocking the GUI."""

        self._emit_telemetry("Refreshing wireless interface inventory.")
        self._run_background_task(
            task=self._service.discover_interfaces,
            on_success=self._on_interfaces_discovered,
            on_error=self._show_error,
        )

    def handle_preflight(self) -> None:
        """Runs readiness checks for the current scan configuration."""

        interface = self._view.current_interface()
        output_dir = Path(self._view.current_output_dir() or "captures")
        request_monitor = self._view.current_monitor_mode().lower() == "monitor"
        self._emit_telemetry(f"Running passive-scan preflight for {interface or 'no interface'}.")

        self._run_background_task(
            task=lambda: self._service.run_preflight(
                interface,
                output_dir,
                request_monitor,
            ),
            on_success=self._on_preflight_completed,
            on_error=self._show_error,
        )

    def handle_toggle_scan(self) -> None:
        """Starts or stops live passive scanning."""

        if self._service.scan_active or self._poll_thread is not None:
            self._emit_telemetry("Stopping the active passive scan.")

            def stop_task() -> object:
                stopped = self._service.stop_target_scan(self._forward_backend_output)
                self._service.restore_managed_mode(self._forward_backend_output)
                return stopped

            self._run_background_task(
                task=stop_task,
                on_success=self._on_scan_stopped,
                on_error=self._show_error,
                scan_transition=True,
            )
            return

        interface = self._view.current_interface()
        request_monitor = self._view.current_monitor_mode().lower() == "monitor"
        output_dir = Path(self._view.current_output_dir() or "captures")
        self._emit_telemetry(f"Preparing passive scan on interface {interface or 'unspecified'}.")

        def start_task() -> object:
            preflight = self._service.run_preflight(
                interface,
                output_dir,
                request_monitor,
            )
            self._forward_backend_output(preflight.as_text())
            if not preflight.ready:
                raise BackendError("Preflight checks failed. Review the console for details.")

            scan_interface = interface
            try:
                if request_monitor:
                    scan_interface = self._service.start_monitor_mode(
                        interface,
                        self._forward_backend_output,
                    )
                return self._service.start_target_scan(
                    scan_interface,
                    output_dir,
                    self._forward_backend_output,
                )
            except Exception:
                self._service.restore_managed_mode(self._forward_backend_output)
                raise

        self._run_background_task(
            task=start_task,
            on_success=self._on_scan_started,
            on_error=self._show_error,
            scan_transition=True,
        )

    def handle_browse_output(self) -> None:
        """Lets the user select the capture output directory."""

        self._view.choose_output_directory()

    def handle_load_capture(self) -> None:
        """Loads an existing airodump-ng CSV capture."""

        selected = self._view.selected_capture_path()
        if not selected:
            selected = self._view.choose_capture_file() or ""
        if not selected:
            return

        capture_path = Path(selected)
        self._emit_telemetry(f"Loading capture file {capture_path}.")
        self._run_background_task(
            task=lambda: self._service.load_capture(capture_path),
            on_success=lambda result: self._on_capture_loaded(result, capture_path),
            on_error=self._show_error,
        )

    def handle_analyze_results(self) -> None:
        """Analyzes the currently displayed network records."""

        snapshot = list(self._latest_records)
        self._emit_telemetry("Analyzing current passive scan results.")
        self._run_background_task(
            task=lambda: self._service.analyze_results(snapshot),
            on_success=self._on_analysis_completed,
            on_error=self._show_error,
        )

    def handle_export_report(self) -> None:
        """Exports displayed network records to a JSON report."""

        destination = self._view.choose_report_destination()
        if not destination:
            return

        snapshot = list(self._latest_records)
        self._emit_telemetry(f"Exporting report to {destination}.")
        self._run_background_task(
            task=lambda: self._service.export_report(snapshot, Path(destination)),
            on_success=self._on_report_exported,
            on_error=self._show_error,
        )

    def handle_open_output_directory(self) -> None:
        """Opens the configured output directory."""

        output_dir = Path(self._view.current_output_dir() or "captures").expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error(f"Unable to open capture directory: {exc}")
            return

        if not self._view.open_output_directory():
            self._show_error(f"The system could not open {output_dir.resolve()}.")

    def shutdown(self) -> None:
        """Stops background work and restores managed mode."""

        if self._shutting_down:
            return

        self._shutting_down = True
        self._emit_telemetry("Shutdown requested. Cleaning up scan resources.")
        self._stop_polling()

        try:
            self._service.stop_target_scan(self._forward_backend_output)
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning("Failed to stop scan during shutdown: %s", exc)

        try:
            self._service.restore_managed_mode(self._forward_backend_output)
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning("Failed to restore managed mode during shutdown: %s", exc)

        for thread in list(self._threads):
            thread.requestInterruption()
            thread.quit()
            if not thread.wait(16000):
                self._logger.warning("A worker thread did not stop before shutdown.")

    def _wire_signals(self) -> None:
        """Connects view actions to controller slots."""

        self._view.refresh_interfaces_button.clicked.connect(self.handle_refresh_interfaces)
        self._view.preflight_button.clicked.connect(self.handle_preflight)
        self._view.start_scan_button.clicked.connect(self.handle_toggle_scan)
        self._view.browse_output_button.clicked.connect(self.handle_browse_output)
        self._view.load_capture_button.clicked.connect(self.handle_load_capture)
        self._view.analyze_results_button.clicked.connect(self.handle_analyze_results)
        self._view.export_report_button.clicked.connect(self.handle_export_report)
        self._view.open_output_button.clicked.connect(self.handle_open_output_directory)
        self._view.closing.connect(self.shutdown)

    def _prime_view(self) -> None:
        """Initializes the view with runtime environment data."""

        environment = self._service.environment
        mode_label = "Mock Mode" if environment.mock_mode else "Hardware Mode"
        suffix = "" if environment.supported else " (best-effort)"
        self._view.set_environment(f"{environment.platform_name}{suffix}")
        self._view.set_runtime_status(mode_label)
        self._view.set_last_analysis(
            "Run a passive scan or load an airodump-ng CSV file to begin analysis."
        )
        self._refresh_control_state()

        if environment.mock_mode:
            self._emit_telemetry(
                "Mock mode is active. Synthetic data will be saved as valid CSV captures."
            )
        else:
            self._emit_telemetry(
                "Linux hardware mode detected. Run preflight before starting a scan."
            )
        QTimer.singleShot(0, self.handle_refresh_interfaces)

    def _run_background_task(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[str], None],
        scan_transition: bool = False,
    ) -> None:
        """Runs a blocking operation on a worker thread."""

        if self._shutting_down:
            return

        thread = QThread(self)
        worker = CallableWorker(task)
        worker.moveToThread(thread)
        self._threads.add(thread)
        self._workers.add(worker)
        self._active_tasks += 1

        if scan_transition:
            self._view.set_scan_button_state(
                running=self._service.scan_active or self._poll_thread is not None,
                busy=True,
            )
        self._refresh_control_state()

        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.failed.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(lambda: self._workers.discard(worker))
        thread.finished.connect(self._on_task_finished)
        thread.start()

    def _start_polling(self) -> None:
        """Starts the live result polling worker."""

        self._stop_polling()
        thread = QThread(self)
        worker = PollingWorker(self._service.read_live_records, interval_ms=1000)
        worker.moveToThread(thread)

        self._poll_thread = thread
        self._poll_worker = worker
        self._threads.add(thread)
        self._workers.add(worker)

        thread.started.connect(worker.run)
        worker.snapshot.connect(self._on_records_updated)
        worker.failed.connect(self._on_polling_failed)
        worker.failed.connect(worker.stop)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
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
            self._poll_thread.requestInterruption()
            self._poll_thread.quit()
            self._poll_thread.wait(2500)
            self._clear_polling_refs()

    def _clear_polling_refs(self) -> None:
        """Clears polling worker references after shutdown."""

        self._poll_thread = None
        self._poll_worker = None
        self._refresh_control_state()

    def _on_task_finished(self) -> None:
        """Updates global busy state after a worker exits."""

        self._active_tasks = max(0, self._active_tasks - 1)
        self._refresh_control_state()
        self._view.set_scan_button_state(
            running=self._service.scan_active or self._poll_thread is not None,
            busy=False,
        )

    def _on_interfaces_discovered(self, result: object) -> None:
        """Populates the interface selector."""

        interfaces = [str(item) for item in result] if isinstance(result, list) else []
        if not interfaces:
            self._forward_backend_output(
                "No wireless interfaces were detected. You may enter one manually."
            )
            return
        self._view.set_interfaces(interfaces)
        self._emit_telemetry(f"Detected interfaces: {', '.join(interfaces)}")

    def _on_preflight_completed(self, result: object) -> None:
        """Displays a structured preflight report."""

        if not isinstance(result, PreflightReport):
            raise BackendError("Unexpected preflight result.")
        text = result.as_text()
        self._view.set_last_analysis(text)
        self._emit_telemetry(text)
        self._view.set_runtime_status("Ready" if result.ready else "Preflight Failed")

    def _on_scan_started(self, result: object) -> None:
        """Handles a successful scan start."""

        if not isinstance(result, ScanSession):
            raise BackendError("Unexpected scan session result.")

        self._view.set_capture_path(str(result.csv_path))
        self._start_polling()
        self._view.set_runtime_status(f"Scanning: {result.monitor_interface}")
        self._view.set_scan_button_state(running=True, busy=False)
        self._emit_telemetry(f"Scan output: {result.csv_path}")
        self._refresh_control_state()

    def _on_scan_stopped(self, _: object) -> None:
        """Handles scan stop completion."""

        self._stop_polling()
        self._view.set_runtime_status("Idle")
        self._view.set_scan_button_state(running=False, busy=False)
        self._emit_telemetry("Passive scan stopped and interface cleanup completed.")

    def _on_records_updated(self, records: list[object]) -> None:
        """Pushes live results into the dashboard."""

        typed_records = [record for record in records if isinstance(record, NetworkRecord)]
        self._latest_records = typed_records
        self._view.update_scan_results(typed_records)

    def _on_capture_loaded(self, result: object, capture_path: Path) -> None:
        """Displays records loaded from a CSV capture."""

        if not isinstance(result, list):
            raise BackendError("Unexpected capture parser result.")
        records = [record for record in result if isinstance(record, NetworkRecord)]
        self._latest_records = records
        self._view.update_scan_results(records)
        self._view.set_capture_path(str(capture_path))
        summary = self._service.analyze_results(records)
        self._view.set_last_analysis(summary)
        self._view.set_runtime_status("Capture Loaded")
        self._emit_telemetry(f"Loaded {len(records)} networks from {capture_path}.")

    def _on_analysis_completed(self, result: object) -> None:
        """Updates the analysis panel."""

        summary = str(result)
        self._view.set_last_analysis(summary)
        self._emit_telemetry(summary)

    def _on_report_exported(self, result: object) -> None:
        """Reports the completed export path."""

        self._emit_telemetry(f"Report exported to {result}.")

    def _on_polling_failed(self, message: str) -> None:
        """Stops a failed scan and displays the backend error."""

        self._stop_polling()

        def cleanup_task() -> object:
            self._service.stop_target_scan(self._forward_backend_output)
            self._service.restore_managed_mode(self._forward_backend_output)
            return None

        self._run_background_task(
            task=cleanup_task,
            on_success=lambda _result: self._show_error(message),
            on_error=lambda cleanup_error: self._show_error(
                f"{message}\nCleanup also failed: {cleanup_error}"
            ),
        )

    def _refresh_control_state(self) -> None:
        """Synchronizes GUI controls with worker and scan state."""

        scanning = self._service.scan_active or self._poll_thread is not None
        self._view.set_controls_state(scanning=scanning, busy=self._active_tasks > 0)

    def _forward_backend_output(self, message: str) -> None:
        """Forwards backend output without logging it a second time."""

        self.console_message.emit(message)

    def _emit_telemetry(self, message: str) -> None:
        """Writes an informational message to logs and the console."""

        self._logger.info(message)
        self.console_message.emit(message)

    def _show_error(self, message: str) -> None:
        """Displays an error consistently in the UI and console."""

        self._logger.error("Error: %s", message)
        self.console_message.emit(f"Error: {message}")
        self._view.set_runtime_status("Error")
        if not self._shutting_down:
            QMessageBox.critical(self._view, "Auto-Sentinel Error", message)
