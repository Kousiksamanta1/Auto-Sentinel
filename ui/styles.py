"""Qt style sheet definitions for Auto-Sentinel."""

LIGHT_THEME_QSS = """
QWidget {
    background-color: #f4f7fb;
    color: #172033;
    font-family: "Rajdhani", "IBM Plex Sans", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #edf2f7;
}

#AppRoot {
    background: qradialgradient(
        cx: 0.82, cy: 0.04, radius: 1.08,
        fx: 0.82, fy: 0.04,
        stop: 0 #e7f6f5,
        stop: 0.48 #f5f8fc,
        stop: 1 #eaf0f6
    );
}

QFrame#HeaderPanel {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #ffffff,
        stop: 1 #eef8f7
    );
    border: 1px solid #cbd8e5;
    border-radius: 16px;
}

QLabel#IdentityBadge {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #174a72,
        stop: 1 #087f67
    );
    border: 1px solid #0d6f75;
    border-radius: 12px;
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
}

QLabel#TitleLabel {
    color: #123653;
    font-size: 27px;
    font-weight: 700;
    letter-spacing: 0.8px;
}

QLabel#SubtitleLabel {
    color: #5b6b7c;
    font-size: 13px;
    font-weight: 500;
}

QLabel#LegalBanner {
    background-color: #fff6dc;
    border: 1px solid #e6b959;
    border-radius: 8px;
    color: #805500;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
}

QLabel#ChipLabel {
    background-color: #edf6ff;
    border: 1px solid #9dc4e3;
    border-radius: 10px;
    color: #205577;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 6px 10px;
}

QLabel#ThreatChip {
    background-color: #e9f8f0;
    border: 1px solid #7fc8a5;
    border-radius: 10px;
    color: #176447;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 10px;
}

QLabel#StatusDot {
    background-color: #a8b6c4;
    border: 1px solid #8293a3;
    border-radius: 5px;
}

QLabel#StatusDot[active="true"] {
    background-color: #1fa774;
    border: 1px solid #087f5b;
}

QFrame#MetricCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #ffffff,
        stop: 1 #edf7f7
    );
    border: 1px solid #cbd9e5;
    border-radius: 14px;
}

QLabel#MetricTitle {
    color: #607286;
    font-size: 12px;
    font-weight: 600;
}

QLabel#MetricValue {
    color: #087f67;
    font-size: 24px;
    font-weight: 700;
}

QLabel#MetricHint {
    color: #7a8a9a;
    font-size: 11px;
    font-weight: 500;
}

QFrame#StatusCard,
QGroupBox {
    background-color: rgba(255, 255, 255, 0.98);
    border: 1px solid #cbd8e5;
    border-radius: 14px;
}

QGroupBox {
    margin-top: 16px;
    padding: 18px 15px 14px 15px;
    font-size: 14px;
    font-weight: 700;
    color: #245b7a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #176b82;
}

QLabel#MutedLabel {
    color: #617286;
    font-size: 12px;
    font-weight: 600;
}

QLabel#CardValue {
    color: #24364a;
    font-size: 12px;
    font-weight: 600;
}

QGroupBox#ActionPanel {
    border-color: #9dbdd1;
    background-color: rgba(248, 252, 255, 0.99);
}

QFrame#ConfigCard,
QFrame#ImportCard {
    background-color: #f7fafc;
    border: 1px solid #c8d7e3;
    border-radius: 11px;
}

QFrame#OperationsCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #eef7ff,
        stop: 1 #edf9f4
    );
    border: 1px solid #a8cad5;
    border-radius: 11px;
}

QScrollArea#LeftPanelScroll {
    background: transparent;
    border: none;
}

QScrollArea#LeftPanelScroll > QWidget > QWidget {
    background: transparent;
}

QLabel#SectionLabel {
    color: #23667d;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 0 2px;
}

QLabel#ActionHint {
    color: #66798b;
    font-size: 12px;
    font-weight: 600;
}

QLineEdit,
QComboBox,
QPlainTextEdit,
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #c5d2de;
    border-radius: 11px;
    selection-background-color: #d7ebf8;
    selection-color: #153f59;
}

QLineEdit {
    color: #1d3044;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 12px;
}

QLineEdit:focus,
QComboBox:focus {
    border: 1px solid #2585ad;
}

QComboBox {
    color: #1d3044;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 10px;
    min-height: 22px;
}

QComboBox::drop-down {
    border: none;
    border-left: 1px solid #cad6e0;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #b8c9d6;
    color: #1d3044;
    selection-background-color: #d7ebf8;
    selection-color: #153f59;
}

QPushButton {
    min-height: 42px;
    border-radius: 11px;
    border: 1px solid #9fb2c2;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #ffffff,
        stop: 1 #e8eef4
    );
    color: #284258;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
    padding: 0 12px;
}

QPushButton:hover {
    border-color: #5f91ae;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #f8fcff,
        stop: 1 #dbeaf3
    );
}

QPushButton:pressed {
    background-color: #d5e2eb;
}

QPushButton:disabled {
    background: #edf1f5;
    border-color: #d2dbe3;
    color: #98a6b3;
}

QPushButton#AccentBlueButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #246d9b,
        stop: 1 #3688b6
    );
    border-color: #1b628f;
    color: #ffffff;
}

QPushButton#AccentBlueButton:hover {
    border-color: #164f73;
    background-color: #1f6f9e;
}

QGroupBox#ActionPanel QPushButton {
    font-size: 15px;
    font-weight: 700;
    border-width: 2px;
    border-radius: 12px;
    min-height: 48px;
    margin-top: 2px;
    margin-bottom: 2px;
    padding-left: 10px;
    padding-right: 10px;
}

QPushButton#PrimaryButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #1d6594,
        stop: 1 #287ead
    );
    border-color: #15577f;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    border-color: #104664;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #18577f,
        stop: 1 #216d97
    );
}

QPushButton#ExportButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #16815f,
        stop: 1 #209a72
    );
    border-color: #087f5b;
    color: #ffffff;
}

QPushButton#ExportButton:hover {
    border-color: #086b4e;
    background-color: #117052;
}

QHeaderView::section {
    background-color: #e8f0f6;
    color: #31566e;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
    border: 0;
    border-bottom: 1px solid #b9cad7;
    padding: 8px;
}

QTableWidget {
    alternate-background-color: #f6f9fc;
    gridline-color: transparent;
}

QTableWidget::item {
    border-bottom: 1px solid #e0e7ee;
    padding: 8px 6px;
}

QTableWidget::item:selected {
    background-color: #d7ebf8;
    color: #153f59;
}

QPlainTextEdit {
    color: #23566e;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.35;
    padding: 10px;
}

QScrollBar:vertical {
    width: 12px;
    background: transparent;
    margin: 3px;
}

QScrollBar::handle:vertical {
    background: #adc0ce;
    border-radius: 6px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #779bb0;
}

QSplitter::handle {
    background-color: #d4e0e8;
}
"""
