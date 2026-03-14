"""Primary Qt view for the Auto-Sentinel dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCloseEvent, QIntValidator
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
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
        self._build_ui()
        self._setup_status_pulse()
        self._setup_entry_animation()

    @property
    def app(self) -> QApplication:
        """Returns the active QApplication instance."""

        app = QApplication.instance()
        assert app is not None
        return app

    def current_interface(self) -> str:
        """Returns the selected interface string."""

        return self.interface_combo.currentText().strip()

    def current_monitor_mode(self) -> str:
        """Returns the selected monitor-mode state."""

        return self.monitor_mode_combo.currentText().strip()

    def current_output_dir(self) -> str:
        """Returns the configured output directory."""

        return "captures"

    def target_bssid_input_value(self) -> str | None:
        """Returns the target BSSID entered by the user, if any."""

        value = self.target_bssid_input.text().strip()
        return value or None

    def deauth_packet_count(self) -> int:
        """Returns a validated deauth packet count from the input."""

        raw_value = self.deauth_count_input.text().strip()
        try:
            parsed = int(raw_value)
        except ValueError:
            return 0
        return max(parsed, 0)

    def selected_bssid(self) -> str | None:
        """Returns the selected BSSID from the dashboard, if any."""

        row = self.network_table.currentRow()
        if row < 0:
            return None
        item = self.network_table.item(row, 1)
        return item.text() if item else None

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

    def update_scan_results(self, records: Sequence[NetworkRecord]) -> None:
        """Renders live scan results into the dashboard table."""

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

        intro = QLabel("Configure interface and run authorized audit workflows.")
        intro.setObjectName("ActionHint")

        config_label = QLabel("Interface Configuration")
        config_label.setObjectName("SectionLabel")
        interface_label = QLabel("Wireless Interface")
        interface_label.setObjectName("MutedLabel")
        mode_label = QLabel("Monitor Mode State")
        mode_label.setObjectName("MutedLabel")
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["wlan0", "wlan1", "wlan0mon"])
        self.interface_combo.setEditable(False)
        self.monitor_mode_combo = QComboBox()
        self.monitor_mode_combo.addItems(["Managed", "Monitor"])
        self.monitor_mode_combo.setEditable(False)

        config_card = QFrame()
        config_card.setObjectName("ConfigCard")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(10, 10, 10, 10)
        config_layout.setSpacing(8)
        config_layout.addWidget(interface_label)
        config_layout.addWidget(self.interface_combo)
        config_layout.addWidget(mode_label)
        config_layout.addWidget(self.monitor_mode_combo)

        ops_label = QLabel("Operations")
        ops_label.setObjectName("SectionLabel")
        self.start_scan_button = QPushButton("Start Network Scan")
        self.start_scan_button.setObjectName("PrimaryButton")
        self.capture_handshake_button = QPushButton("Capture Handshake")
        self.capture_handshake_button.setObjectName("CaptureButton")
        self.parse_capture_button = QPushButton("Parse Capture")
        self.parse_capture_button.setObjectName("AccentBlueButton")

        ops_card = QFrame()
        ops_card.setObjectName("OperationsCard")
        ops_layout = QVBoxLayout(ops_card)
        ops_layout.setContentsMargins(10, 10, 10, 10)
        ops_layout.setSpacing(9)
        for button in (
            self.start_scan_button,
            self.capture_handshake_button,
            self.parse_capture_button,
        ):
            button.setMinimumHeight(48)
            ops_layout.addWidget(button)

        deauth_label = QLabel("Deauthentication Authorization")
        deauth_label.setObjectName("SectionLabel")
        bssid_label = QLabel("Target BSSID")
        bssid_label.setObjectName("MutedLabel")
        packet_label = QLabel("Deauth Packets (count)")
        packet_label.setObjectName("MutedLabel")
        self.target_bssid_input = QLineEdit()
        self.target_bssid_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.target_bssid_input.setClearButtonEnabled(True)
        self.deauth_count_input = QLineEdit("10")
        self.deauth_count_input.setPlaceholderText("10")
        self.deauth_count_input.setValidator(QIntValidator(1, 99999, self))
        self.deauth_count_input.setMaxLength(5)
        self.authorize_deauth_button = QPushButton("Authorize Deauthentication")
        self.authorize_deauth_button.setObjectName("DangerButton")
        self.authorize_deauth_button.setMinimumHeight(48)

        deauth_card = QFrame()
        deauth_card.setObjectName("DeauthCard")
        deauth_layout = QVBoxLayout(deauth_card)
        deauth_layout.setContentsMargins(10, 10, 10, 10)
        deauth_layout.setSpacing(8)
        deauth_layout.addWidget(bssid_label)
        deauth_layout.addWidget(self.target_bssid_input)
        deauth_layout.addWidget(packet_label)
        deauth_layout.addWidget(self.deauth_count_input)
        deauth_layout.addWidget(self.authorize_deauth_button)

        guardrail_note = QLabel("Deauth workflow is guarded and intentionally non-automated.")
        guardrail_note.setObjectName("ActionHint")

        controls_layout.addWidget(intro)
        controls_layout.addWidget(config_label)
        controls_layout.addWidget(config_card)
        controls_layout.addWidget(ops_label)
        controls_layout.addWidget(ops_card)
        controls_layout.addWidget(deauth_label)
        controls_layout.addWidget(deauth_card)
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
        if "error" in lowered:
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
            return QColor("#7dffbf")
        if signal_dbm >= -67:
            return QColor("#ffe492")
        return QColor("#ffae8f")

    def _encryption_color(self, encryption: str) -> QColor:
        """Returns an encryption-aware color."""

        if "Open" in encryption:
            return QColor("#ff9f7d")
        if "WPA3" in encryption:
            return QColor("#82f0ff")
        return QColor("#9ef3c2")
