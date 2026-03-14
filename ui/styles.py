"""Qt style sheet definitions for Auto-Sentinel."""

DARK_THEME_QSS = """
QWidget {
    background-color: #0f151c;
    color: #d5e9fb;
    font-family: "Rajdhani", "IBM Plex Sans", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0a1017;
}

#AppRoot {
    background: qradialgradient(
        cx: 0.8, cy: 0.05, radius: 1.05,
        fx: 0.8, fy: 0.05,
        stop: 0 #132433,
        stop: 0.45 #101821,
        stop: 1 #090f16
    );
}

QFrame#HeaderPanel {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #101c28,
        stop: 1 #0f2430
    );
    border: 1px solid #274055;
    border-radius: 16px;
}

QLabel#IdentityBadge {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #143346,
        stop: 1 #1a6044
    );
    border: 1px solid #4eb6e2;
    border-radius: 12px;
    color: #d9faff;
    font-size: 22px;
    font-weight: 700;
}

QLabel#TitleLabel {
    color: #89ffd7;
    font-size: 27px;
    font-weight: 700;
    letter-spacing: 0.8px;
}

QLabel#SubtitleLabel {
    color: #90a5ba;
    font-size: 13px;
    font-weight: 500;
}

QLabel#LegalBanner {
    background-color: #122634;
    border: 1px solid #2f5c76;
    border-radius: 8px;
    color: #59daff;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
}

QLabel#ChipLabel {
    background-color: #12202c;
    border: 1px solid #2a536e;
    border-radius: 10px;
    color: #a9e6ff;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 6px 10px;
}

QLabel#ThreatChip {
    background-color: #202715;
    border: 1px solid #80be53;
    border-radius: 10px;
    color: #cbffc1;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 10px;
}

QLabel#StatusDot {
    background-color: #2f4558;
    border: 1px solid #4d6174;
    border-radius: 5px;
}

QLabel#StatusDot[active="true"] {
    background-color: #84ffbb;
    border: 1px solid #b3ffcd;
}

QFrame#MetricCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #131f2a,
        stop: 1 #112632
    );
    border: 1px solid #244051;
    border-radius: 14px;
}

QLabel#MetricTitle {
    color: #89a5bb;
    font-size: 12px;
    font-weight: 600;
}

QLabel#MetricValue {
    color: #8cffca;
    font-size: 24px;
    font-weight: 700;
}

QLabel#MetricHint {
    color: #68839a;
    font-size: 11px;
    font-weight: 500;
}

QFrame#StatusCard,
QGroupBox {
    background-color: rgba(18, 29, 40, 0.96);
    border: 1px solid #23394b;
    border-radius: 14px;
}

QGroupBox {
    margin-top: 16px;
    padding: 18px 15px 14px 15px;
    font-size: 14px;
    font-weight: 700;
    color: #83deff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #6ce3ff;
}

QLabel#MutedLabel {
    color: #8da4b8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#CardValue {
    color: #d7eaf8;
    font-size: 12px;
    font-weight: 600;
}

QGroupBox#ActionPanel {
    border-color: #3f7896;
    background-color: rgba(14, 29, 42, 0.98);
}

QFrame#InsetCard,
QFrame#ConfigCard,
QFrame#DeauthCard {
    background-color: rgba(11, 23, 34, 0.98);
    border: 1px solid #2a5268;
    border-radius: 11px;
}

QFrame#OperationsCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 rgba(16, 35, 47, 0.98),
        stop: 1 rgba(16, 47, 41, 0.98)
    );
    border: 1px solid #3a7e95;
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
    color: #a5e7ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 0 2px;
}

QLabel#ActionHint {
    color: #95b8cf;
    font-size: 12px;
    font-weight: 600;
}

QLineEdit,
QComboBox,
QPlainTextEdit,
QTableWidget {
    background-color: #0f1923;
    border: 1px solid #233a4c;
    border-radius: 11px;
    selection-background-color: #18455c;
    selection-color: #dbf8ff;
}

QLineEdit {
    color: #dbf2ff;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 12px;
}

QLineEdit:focus,
QComboBox:focus {
    border: 1px solid #47b6dc;
}

QComboBox {
    color: #dbf2ff;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 10px;
    min-height: 22px;
}

QComboBox::drop-down {
    border: none;
    border-left: 1px solid #2f4f62;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #0f1d28;
    border: 1px solid #2a4f64;
    color: #d8f3ff;
    selection-background-color: #1b4f67;
    selection-color: #e9fcff;
}

QPushButton {
    min-height: 42px;
    border-radius: 11px;
    border: 1px solid #33586f;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #1b3a4f,
        stop: 1 #183042
    );
    color: #dff6ff;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
    padding: 0 12px;
}

QPushButton:hover {
    border-color: #4d86a7;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #1f4660,
        stop: 1 #1a3a50
    );
}

QPushButton:pressed {
    background-color: #142b3b;
}

QPushButton:disabled {
    background: #172633;
    border-color: #2a3f4f;
    color: #648094;
}

QPushButton#AccentButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #184630,
        stop: 1 #1f5c44
    );
    border-color: #58d591;
    color: #cbffe3;
}

QPushButton#AccentButton:hover {
    border-color: #7de9ad;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #1c593d,
        stop: 1 #246c50
    );
}

QPushButton#AccentBlueButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #113a56,
        stop: 1 #185075
    );
    border-color: #63c2ea;
    color: #cef2ff;
}

QPushButton#AccentBlueButton:hover {
    border-color: #7fd6fb;
}

QPushButton#DangerButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4a2c1c,
        stop: 1 #58311f
    );
    border-color: #f59666;
    color: #ffd9c8;
}

QPushButton#DangerButton:hover {
    border-color: #ffb28d;
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
        stop: 0 #1a3d61,
        stop: 1 #1f527f
    );
    border-color: #6fc6ff;
    color: #e3f6ff;
}

QPushButton#PrimaryButton:hover {
    border-color: #95d8ff;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #204a74,
        stop: 1 #286095
    );
}

QPushButton#CaptureButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #18533d,
        stop: 1 #1e6a4f
    );
    border-color: #63dca4;
    color: #d9ffe9;
}

QPushButton#CaptureButton:hover {
    border-color: #8cf3be;
}

QHeaderView::section {
    background-color: #102331;
    color: #9cdaef;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
    border: 0;
    border-bottom: 1px solid #2b5066;
    padding: 8px;
}

QTableWidget {
    alternate-background-color: #101d28;
    gridline-color: transparent;
}

QTableWidget::item {
    border-bottom: 1px solid #1a3242;
    padding: 8px 6px;
}

QTableWidget::item:selected {
    background-color: #18455c;
}

QPlainTextEdit {
    color: #a8f0ff;
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
    background: #2d5d77;
    border-radius: 6px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #3f85ab;
}

QSplitter::handle {
    background-color: #132432;
}
"""
