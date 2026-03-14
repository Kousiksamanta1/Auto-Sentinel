"""Primary Qt view for the Auto-Sentinel dashboard."""

from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCloseEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
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
        self.resize(1480, 920)
        self._build_ui()

    @property
    def app(self) -> QApplication:
        """Returns the active QApplication instance."""

        app = QApplication.instance()
        assert app is not None
        return app

    def current_interface(self) -> str:
        """Returns the selected interface string."""

        return self.interface_input.text().strip()

    def current_output_dir(self) -> str:
        """Returns the configured output directory."""

        return self.output_dir_input.text().strip()

    def selected_bssid(self) -> str | None:
        """Returns the selected BSSID from the dashboard, if any."""

        row = self.network_table.currentRow()
        if row < 0:
            return None
        item = self.network_table.item(row, 1)
        return item.text() if item else None

    def set_environment(self, description: str) -> None:
        """Updates the environment chip."""

        self.environment_value.setText(description)

    def set_runtime_status(self, description: str) -> None:
        """Updates the runtime status chip."""

        self.status_value.setText(description)

    def set_last_analysis(self, summary: str) -> None:
        """Updates the analysis panel text."""

        self.analysis_text.setPlainText(summary)

    def append_console(self, message: str) -> None:
        """Appends a line of text to the embedded console."""

        if not message.strip():
            return
        self.console_output.appendPlainText(message)
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_monitor_button_busy(self, busy: bool) -> None:
        """Applies a busy state to the monitor button."""

        self.monitor_button.setDisabled(busy)
        self.monitor_button.setText("Starting..." if busy else "Start Monitor Mode")

    def set_scan_button_state(self, running: bool, busy: bool = False) -> None:
        """Updates the scan button text and enabled state."""

        if busy:
            self.scan_button.setText("Working...")
            self.scan_button.setDisabled(True)
            return

        self.scan_button.setDisabled(False)
        self.scan_button.setText("Stop Target Scan" if running else "Target Scan")

    def update_scan_results(self, records: Sequence[NetworkRecord]) -> None:
        """Renders live scan results into the dashboard table."""

        self.network_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            for column_index, cell_value in enumerate(record.as_table_row()):
                item = QTableWidgetItem(cell_value)
                if column_index == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(self._signal_color(record.signal_dbm))
                if column_index == 4:
                    item.setForeground(self._encryption_color(record.encryption))
                self.network_table.setItem(row_index, column_index, item)

        if records:
            self.network_table.resizeRowsToContents()

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
        main_layout.setSpacing(20)

        main_layout.addWidget(self._build_header())
        main_layout.addWidget(self._build_body(), stretch=1)

    def _build_header(self) -> QWidget:
        """Builds the top title and status area."""

        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title_column = QVBoxLayout()
        title_label = QLabel("Auto-Sentinel")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("Passive WPA2 wireless auditing dashboard for Kali Linux and mock macOS testing.")
        subtitle_label.setObjectName("SubtitleLabel")
        title_column.addWidget(title_label)
        title_column.addWidget(subtitle_label)

        chips_column = QHBoxLayout()
        chips_column.setSpacing(10)
        self.environment_value = QLabel("Detecting environment")
        self.environment_value.setObjectName("ChipLabel")
        self.status_value = QLabel("Idle")
        self.status_value.setObjectName("ChipLabel")
        chips_column.addStretch(1)
        chips_column.addWidget(self.environment_value)
        chips_column.addWidget(self.status_value)

        layout.addLayout(title_column, stretch=2)
        layout.addLayout(chips_column, stretch=1)
        return header

    def _build_body(self) -> QWidget:
        """Builds the main action, dashboard, and console area."""

        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        layout.addWidget(self._build_left_panel(), stretch=0)
        layout.addWidget(self._build_right_panel(), stretch=1)
        return body

    def _build_left_panel(self) -> QWidget:
        """Builds the left-side control column."""

        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        panel.setMinimumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        controls_box = QGroupBox("Action Panel")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setSpacing(12)

        self.interface_input = QLineEdit("wlan0")
        self.interface_input.setPlaceholderText("Wireless interface, e.g. wlan0")
        self.output_dir_input = QLineEdit("captures")
        self.output_dir_input.setPlaceholderText("Output directory")

        interface_label = QLabel("Wireless Interface")
        interface_label.setObjectName("MutedLabel")
        output_label = QLabel("Capture Output Directory")
        output_label.setObjectName("MutedLabel")

        self.monitor_button = QPushButton("Start Monitor Mode")
        self.monitor_button.setObjectName("AccentButton")
        self.scan_button = QPushButton("Target Scan")
        self.attack_button = QPushButton("Deauth/Capture Handshake")
        self.attack_button.setObjectName("DangerButton")
        self.analyze_button = QPushButton("Analyze Results")

        controls_layout.addWidget(interface_label)
        controls_layout.addWidget(self.interface_input)
        controls_layout.addWidget(output_label)
        controls_layout.addWidget(self.output_dir_input)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self.monitor_button)
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.attack_button)
        controls_layout.addWidget(self.analyze_button)
        controls_layout.addStretch(1)

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
        summary_layout.addWidget(QLabel("UI Mode"), 0, 0)
        summary_layout.addWidget(QLabel("Threaded / Responsive"), 0, 1)
        summary_layout.addWidget(QLabel("Console"), 1, 0)
        summary_layout.addWidget(QLabel("Live subprocess output"), 1, 1)
        summary_layout.addWidget(QLabel("Cleanup"), 2, 0)
        summary_layout.addWidget(QLabel("Managed mode restore on exit"), 2, 1)

        layout.addWidget(controls_box)
        layout.addWidget(analysis_box)
        layout.addWidget(summary_card)
        return panel

    def _build_right_panel(self) -> QWidget:
        """Builds the dashboard and embedded console column."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_dashboard_box())
        splitter.addWidget(self._build_console_box())
        splitter.setSizes([540, 260])

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

    def _signal_color(self, signal_dbm: int) -> QColor:
        """Returns a signal-strength color."""

        if signal_dbm >= -50:
            return QColor("#7fffd4")
        if signal_dbm >= -67:
            return QColor("#ffe082")
        return QColor("#ff9f80")

    def _encryption_color(self, encryption: str) -> QColor:
        """Returns an encryption-aware color."""

        if "Open" in encryption:
            return QColor("#ffb07c")
        if "WPA3" in encryption:
            return QColor("#87e8ff")
        return QColor("#a6f9c5")
