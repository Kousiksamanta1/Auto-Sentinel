"""Primary Qt view for the Auto-Sentinel dashboard."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import NetworkRecord


class AutoSentinelWindow(QMainWindow):
    """Main application window for wireless scan operations."""

    closing = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Auto-Sentinel")
        self.resize(1520, 940)
        self.setMinimumSize(1260, 760)
        self._pulse_active = False
        self._entry_animation: QPropertyAnimation | None = None
        self._status_pulse_timer = QTimer(self)
        self._metrics: dict[str, QLabel] = {}
        self._has_results = False
        self._busy = False
        self._build_ui()
        self._setup_status_pulse()
        self._setup_entry_animation()

    def current_interface(self) -> str:
        """Returns the selected interface string."""

        return self.interface_combo.currentText().strip()

    def current_monitor_mode(self) -> str:
        """Returns the selected monitor-mode state."""

        return self.monitor_mode_combo.currentText().strip()

    def current_output_dir(self) -> str:
        """Returns the configured output directory."""

        return self.output_dir_input.text().strip()

    def selected_capture_path(self) -> str:
        """Returns the selected CSV capture path."""

        return self.capture_path_input.text().strip()

    def choose_output_directory(self) -> str | None:
        """Prompts for and stores a capture output directory."""

        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Capture Directory",
            self.current_output_dir() or "captures",
        )
        if not selected:
            return None
        self.output_dir_input.setText(selected)
        return selected

    def choose_capture_file(self) -> str | None:
        """Prompts for and stores an airodump-ng CSV capture."""

        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Load Airodump CSV",
            self.current_output_dir() or "captures",
            "CSV captures (*.csv);;All files (*)",
        )
        if not selected:
            return None
        self.capture_path_input.setText(selected)
        return selected

    def choose_report_destination(self) -> str | None:
        """Prompts for a JSON report destination."""

        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Report",
            "auto-sentinel-report.json",
            "JSON reports (*.json)",
        )
        return selected or None

    def open_output_directory(self) -> bool:
        """Opens the configured capture directory in the system file manager."""

        output_dir = Path(self.current_output_dir() or "captures").expanduser().resolve()
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))

    def set_interfaces(self, interfaces: Sequence[str]) -> None:
        """Replaces interface choices while preserving the current value."""

        current = self.current_interface()
        self.interface_combo.clear()
        self.interface_combo.addItems(list(interfaces))
        if current in interfaces:
            self.interface_combo.setCurrentText(current)

    def set_capture_path(self, path: str) -> None:
        """Updates the displayed capture source."""

        self.capture_path_input.setText(path)

    def set_environment(self, description: str) -> None:
        """Updates the environment chip."""

        self.environment_value.setText(f"ENVIRONMENT: {description}")

    def set_runtime_status(self, description: str) -> None:
        """Updates the runtime status chip."""

        self.status_value.setText(f"RUNTIME: {description}")
        self.mission_value.setText(self._runtime_to_mission_state(description))

    def set_last_analysis(self, summary: str) -> None:
        """Updates the analysis panel text."""

        self.analysis_text.setPlainText(summary)

    def append_console(self, message: str) -> None:
        """Appends a line of text to the embedded console."""

        if not message.strip():
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_output.appendPlainText(f"[{timestamp}] {message}")
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_scan_button_state(self, running: bool, busy: bool = False) -> None:
        """Updates the scan button text and enabled state."""

        if busy:
            self.start_scan_button.setText("Working...")
            self.start_scan_button.setDisabled(True)
            return

        self.start_scan_button.setDisabled(False)
        self.start_scan_button.setText("Stop Network Scan" if running else "Start Network Scan")

    def set_controls_state(self, scanning: bool, busy: bool) -> None:
        """Coordinates controls that should not overlap with scan operations."""

        self._busy = busy
        configuration_enabled = not scanning and not busy
        for widget in (
            self.interface_combo,
            self.monitor_mode_combo,
            self.output_dir_input,
            self.refresh_interfaces_button,
            self.preflight_button,
            self.browse_output_button,
        ):
            widget.setEnabled(configuration_enabled)

        import_enabled = not scanning and not busy
        for widget in (
            self.capture_path_input,
            self.load_capture_button,
            self.open_output_button,
        ):
            widget.setEnabled(import_enabled)

        self.open_output_button.setEnabled(not busy)
        self.analyze_results_button.setEnabled(not busy and self._has_results)
        self.export_report_button.setEnabled(not busy and self._has_results)

    def update_scan_results(self, records: Sequence[NetworkRecord]) -> None:
        """Renders live scan results into the dashboard table."""

        self._has_results = bool(records)
        self.network_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            for column_index, cell_value in enumerate(record.as_table_row()):
                item = QTableWidgetItem(cell_value)
                if column_index == 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column_index == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(self._signal_color(record.signal_dbm))
                if column_index == 4:
                    item.setForeground(self._encryption_color(record.encryption))
                self.network_table.setItem(row_index, column_index, item)

        if records:
            self.network_table.resizeRowsToContents()
        self._update_metrics(records)
        self.analyze_results_button.setEnabled(self._has_results and not self._busy)
        self.export_report_button.setEnabled(self._has_results and not self._busy)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Emits a closing signal before the window exits."""

        self.closing.emit()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        """Builds the widget hierarchy."""

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        main_layout.addWidget(self._build_header())
        main_layout.addWidget(self._build_metrics_strip())
        main_layout.addWidget(self._build_body(), stretch=1)

    def _build_header(self) -> QWidget:
        """Builds the top identity and status area."""

        header = QFrame()
        header.setObjectName("HeaderPanel")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        identity = QLabel("AS")
        identity.setObjectName("IdentityBadge")
        identity.setFixedSize(54, 54)
        identity.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title_label = QLabel("Auto-Sentinel // Wireless Audit Command")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("Passive WPA2/WPA3 reconnaissance dashboard for authorized security assessments.")
        subtitle_label.setObjectName("SubtitleLabel")
        legal_banner = QLabel("AUTHORIZED TESTING ONLY")
        legal_banner.setObjectName("LegalBanner")
        title_column.addWidget(title_label)
        title_column.addWidget(subtitle_label)
        title_column.addWidget(legal_banner)

        chips_column = QVBoxLayout()
        chips_column.setSpacing(8)
        chips_column.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.environment_value = QLabel("ENVIRONMENT: Detecting")
        self.environment_value.setObjectName("ChipLabel")
        self.status_value = QLabel("RUNTIME: Idle")
        self.status_value.setObjectName("ChipLabel")
        self.mission_value = QLabel("MISSION: Standby")
        self.mission_value.setObjectName("ThreatChip")

        status_line = QHBoxLayout()
        status_line.setSpacing(8)
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(11, 11)
        status_line.addWidget(self.status_dot)
        status_line.addWidget(self.status_value)
        status_line.setAlignment(Qt.AlignmentFlag.AlignRight)

        chips_column.addWidget(self.environment_value, alignment=Qt.AlignmentFlag.AlignRight)
        chips_column.addLayout(status_line)
        chips_column.addWidget(self.mission_value, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(identity)
        layout.addLayout(title_column, stretch=1)
        layout.addLayout(chips_column)
        return header

    def _build_metrics_strip(self) -> QWidget:
        """Builds high-level telemetry cards shown above the body."""

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._metrics["networks"] = self._add_metric_card(
            layout=layout,
            title="Detected Networks",
            value="0",
            hint="Live BSSID inventory",
        )
        self._metrics["security_mix"] = self._add_metric_card(
            layout=layout,
            title="Security Profile",
            value="N/A",
            hint="Secured : Open",
        )
        self._metrics["strongest"] = self._add_metric_card(
            layout=layout,
            title="Strongest Signal",
            value="N/A",
            hint="Top RSSI",
        )
        self._metrics["channels"] = self._add_metric_card(
            layout=layout,
            title="Channel Spread",
            value="0",
            hint="Unique channels",
        )

        return strip

    def _build_body(self) -> QWidget:
        """Builds the main action, dashboard, and console area."""

        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        layout.addWidget(self._build_left_panel(), stretch=0)
        layout.addWidget(self._build_right_panel(), stretch=1)
        return body

    def _build_left_panel(self) -> QWidget:
        """Builds the left-side control column."""

        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        panel.setMinimumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        scroll = QScrollArea()
        scroll.setObjectName("LeftPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_body = QWidget()
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)

        controls_box = QGroupBox("Action Panel")
        controls_box.setObjectName("ActionPanel")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setContentsMargins(14, 16, 14, 14)
        controls_layout.setSpacing(11)

        intro = QLabel("Configure a sensor and run passive, authorized audit workflows.")
        intro.setObjectName("ActionHint")

        config_label = QLabel("Interface Configuration")
        config_label.setObjectName("SectionLabel")
        interface_label = QLabel("Wireless Interface")
        interface_label.setObjectName("MutedLabel")
        mode_label = QLabel("Monitor Mode State")
        mode_label.setObjectName("MutedLabel")
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["wlan0", "wlan1"])
        self.interface_combo.setEditable(True)
        self.monitor_mode_combo = QComboBox()
        self.monitor_mode_combo.addItems(["Monitor", "Managed"])
        self.monitor_mode_combo.setEditable(False)
        self.refresh_interfaces_button = QPushButton("Refresh Interfaces")
        self.refresh_interfaces_button.setObjectName("SecondaryButton")

        output_label = QLabel("Capture Directory")
        output_label.setObjectName("MutedLabel")
        self.output_dir_input = QLineEdit("captures")
        self.output_dir_input.setPlaceholderText("captures")
        self.browse_output_button = QPushButton("Browse Capture Directory")
        self.browse_output_button.setObjectName("SecondaryButton")

        config_card = QFrame()
        config_card.setObjectName("ConfigCard")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(10, 10, 10, 10)
        config_layout.setSpacing(8)
        config_layout.addWidget(interface_label)
        config_layout.addWidget(self.interface_combo)
        config_layout.addWidget(mode_label)
        config_layout.addWidget(self.monitor_mode_combo)
        config_layout.addWidget(self.refresh_interfaces_button)
        config_layout.addWidget(output_label)
        config_layout.addWidget(self.output_dir_input)
        config_layout.addWidget(self.browse_output_button)

        ops_label = QLabel("Operations")
        ops_label.setObjectName("SectionLabel")
        self.preflight_button = QPushButton("Run Preflight Checks")
        self.preflight_button.setObjectName("SecondaryButton")
        self.start_scan_button = QPushButton("Start Network Scan")
        self.start_scan_button.setObjectName("PrimaryButton")
        self.analyze_results_button = QPushButton("Analyze Current Results")
        self.analyze_results_button.setObjectName("AccentBlueButton")
        self.export_report_button = QPushButton("Export JSON Report")
        self.export_report_button.setObjectName("ExportButton")

        ops_card = QFrame()
        ops_card.setObjectName("OperationsCard")
        ops_layout = QVBoxLayout(ops_card)
        ops_layout.setContentsMargins(10, 10, 10, 10)
        ops_layout.setSpacing(9)
        for button in (
            self.preflight_button,
            self.start_scan_button,
            self.analyze_results_button,
            self.export_report_button,
        ):
            button.setMinimumHeight(48)
            ops_layout.addWidget(button)

        import_label = QLabel("Capture Analysis")
        import_label.setObjectName("SectionLabel")
        capture_path_label = QLabel("Airodump CSV File")
        capture_path_label.setObjectName("MutedLabel")
        self.capture_path_input = QLineEdit()
        self.capture_path_input.setPlaceholderText("Select an existing airodump-ng CSV")
        self.capture_path_input.setClearButtonEnabled(True)
        self.load_capture_button = QPushButton("Load Capture CSV")
        self.load_capture_button.setObjectName("SecondaryButton")
        self.open_output_button = QPushButton("Open Capture Directory")
        self.open_output_button.setObjectName("SecondaryButton")

        import_card = QFrame()
        import_card.setObjectName("ImportCard")
        import_layout = QVBoxLayout(import_card)
        import_layout.setContentsMargins(10, 10, 10, 10)
        import_layout.setSpacing(8)
        import_layout.addWidget(capture_path_label)
        import_layout.addWidget(self.capture_path_input)
        import_layout.addWidget(self.load_capture_button)
        import_layout.addWidget(self.open_output_button)

        guardrail_note = QLabel(
            "Passive scope only. Deauthentication and automated handshake attacks "
            "are not provided."
        )
        guardrail_note.setWordWrap(True)
        guardrail_note.setObjectName("ActionHint")

        controls_layout.addWidget(intro)
        controls_layout.addWidget(config_label)
        controls_layout.addWidget(config_card)
        controls_layout.addWidget(ops_label)
        controls_layout.addWidget(ops_card)
        controls_layout.addWidget(import_label)
        controls_layout.addWidget(import_card)
        controls_layout.addWidget(guardrail_note)

        analysis_box = QGroupBox("Analysis Snapshot")
        analysis_layout = QVBoxLayout(analysis_box)
        self.analysis_text = QPlainTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlainText("Analysis output will appear here once scan data is available.")
        analysis_layout.addWidget(self.analysis_text)

        summary_card = QFrame()
        summary_card.setObjectName("StatusCard")
        summary_layout = QGridLayout(summary_card)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        summary_layout.setHorizontalSpacing(12)
        summary_layout.setVerticalSpacing(10)
        summary_layout.addWidget(self._status_label("Execution Model"), 0, 0)
        summary_layout.addWidget(self._status_value("Threaded (QThread workers)"), 0, 1)
        summary_layout.addWidget(self._status_label("Telemetry Stream"), 1, 0)
        summary_layout.addWidget(self._status_value("Realtime subprocess console"), 1, 1)
        summary_layout.addWidget(self._status_label("Exit Safety"), 2, 0)
        summary_layout.addWidget(self._status_value("Managed mode restoration"), 2, 1)

        scroll_layout.addWidget(controls_box)
        scroll_layout.addWidget(analysis_box)
        scroll_layout.addWidget(summary_card)
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_body)
        layout.addWidget(scroll)
        return panel

    def _build_right_panel(self) -> QWidget:
        """Builds the dashboard and embedded console column."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_dashboard_box())
        splitter.addWidget(self._build_console_box())
        splitter.setSizes([560, 250])
        layout.addWidget(splitter)
        return panel

    def _build_dashboard_box(self) -> QWidget:
        """Builds the live dashboard group."""

        dashboard_box = QGroupBox("Live Dashboard")
        layout = QVBoxLayout(dashboard_box)

        self.network_table = QTableWidget(0, 5)
        self.network_table.setHorizontalHeaderLabels(
            ["SSID", "BSSID", "Channel", "Signal dBm", "Encryption"]
        )
        self.network_table.setAlternatingRowColors(True)
        self.network_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.network_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.network_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.network_table.verticalHeader().setVisible(False)
        self.network_table.horizontalHeader().setStretchLastSection(True)
        self.network_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.network_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.network_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.network_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.network_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.network_table.setShowGrid(False)

        layout.addWidget(self.network_table)
        return dashboard_box

    def _build_console_box(self) -> QWidget:
        """Builds the console group."""

        console_box = QGroupBox("Embedded Console")
        layout = QVBoxLayout(console_box)

        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlainText("Runtime output from backend tools will stream here.")
        self.console_output.document().setMaximumBlockCount(1200)
        layout.addWidget(self.console_output)
        return console_box

    def _add_metric_card(self, layout: QHBoxLayout, title: str, value: str, hint: str) -> QLabel:
        """Creates a compact telemetry card and returns its dynamic value label."""

        card = QFrame()
        card.setObjectName("MetricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("MetricTitle")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        hint_label = QLabel(hint)
        hint_label.setObjectName("MetricHint")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(hint_label)
        layout.addWidget(card)
        return value_label

    def _status_label(self, text: str) -> QLabel:
        """Builds a label used in the left-side status card."""

        label = QLabel(text)
        label.setObjectName("MutedLabel")
        return label

    def _status_value(self, text: str) -> QLabel:
        """Builds a value used in the left-side status card."""

        value = QLabel(text)
        value.setObjectName("CardValue")
        return value

    def _update_metrics(self, records: Sequence[NetworkRecord]) -> None:
        """Updates telemetry cards from current scan results."""

        count = len(records)
        if count == 0:
            self._metrics["networks"].setText("0")
            self._metrics["security_mix"].setText("N/A")
            self._metrics["strongest"].setText("N/A")
            self._metrics["channels"].setText("0")
            return

        open_networks = sum("open" in network.encryption.lower() for network in records)
        secured_networks = count - open_networks
        strongest = max(records, key=lambda network: network.signal_dbm)
        channels = len({network.channel for network in records})

        self._metrics["networks"].setText(str(count))
        self._metrics["security_mix"].setText(f"{secured_networks}:{open_networks}")
        self._metrics["strongest"].setText(f"{strongest.signal_dbm} dBm")
        self._metrics["channels"].setText(str(channels))

    def _runtime_to_mission_state(self, runtime_status: str) -> str:
        """Translates runtime status text into a mission-state label."""

        lowered = runtime_status.lower()
        if "error" in lowered or "failed" in lowered:
            return "MISSION: Fault State"
        if "scan" in lowered:
            return "MISSION: Active Monitoring"
        if "monitor" in lowered:
            return "MISSION: Sensor Armed"
        return "MISSION: Standby"

    def _setup_status_pulse(self) -> None:
        """Creates a lightweight pulse animation for the runtime indicator."""

        self._status_pulse_timer.setInterval(900)
        self._status_pulse_timer.timeout.connect(self._toggle_status_dot)
        self._status_pulse_timer.start()

    def _toggle_status_dot(self) -> None:
        """Toggles status indicator style for subtle activity feedback."""

        self._pulse_active = not self._pulse_active
        self.status_dot.setProperty("active", self._pulse_active)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def _setup_entry_animation(self) -> None:
        """Applies a smooth startup fade-in to the full dashboard."""

        root = self.centralWidget()
        if root is None:
            return

        effect = QGraphicsOpacityEffect(root)
        root.setGraphicsEffect(effect)

        self._entry_animation = QPropertyAnimation(effect, b"opacity", self)
        self._entry_animation.setDuration(420)
        self._entry_animation.setStartValue(0.0)
        self._entry_animation.setEndValue(1.0)
        self._entry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(60, self._entry_animation.start)

    def _signal_color(self, signal_dbm: int) -> QColor:
        """Returns a signal-strength color."""

        if signal_dbm >= -50:
            return QColor("#087f5b")
        if signal_dbm >= -67:
            return QColor("#9a5b00")
        return QColor("#bd3d35")

    def _encryption_color(self, encryption: str) -> QColor:
        """Returns an encryption-aware color."""

        if "Open" in encryption:
            return QColor("#b93831")
        if "WPA3" in encryption:
            return QColor("#176b82")
        return QColor("#087f5b")
