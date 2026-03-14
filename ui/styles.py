"""Qt style sheet definitions for Auto-Sentinel."""

DARK_THEME_QSS = """
QWidget {
    background-color: #0f141b;
    color: #d7e8f7;
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0a0f15;
}

#AppRoot {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #0c1117,
        stop: 0.55 #101821,
        stop: 1 #09111a
    );
}

QFrame#StatusCard,
QGroupBox {
    background-color: rgba(19, 28, 37, 0.96);
    border: 1px solid #1f3342;
    border-radius: 16px;
}

QGroupBox {
    margin-top: 16px;
    padding: 18px 16px 16px 16px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #54d7ff;
}

QLabel#TitleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #7fffd4;
}

QLabel#SubtitleLabel {
    color: #8ea4b8;
    font-size: 13px;
}

QLabel#ChipLabel {
    background-color: #12212d;
    border: 1px solid #21465e;
    border-radius: 10px;
    padding: 6px 10px;
    color: #54d7ff;
    font-weight: 600;
}

QLabel#MutedLabel {
    color: #8ea4b8;
}

QLineEdit,
QPlainTextEdit,
QTableWidget {
    background-color: #111922;
    border: 1px solid #203241;
    border-radius: 12px;
    selection-background-color: #11394a;
    selection-color: #dff9ff;
}

QLineEdit {
    padding: 10px 12px;
}

QPushButton {
    min-height: 42px;
    border-radius: 12px;
    border: 1px solid #29516a;
    background-color: #173043;
    color: #dff9ff;
    font-weight: 600;
    padding: 0 14px;
}

QPushButton:hover {
    background-color: #1b4158;
    border-color: #3c7697;
}

QPushButton:pressed {
    background-color: #112a39;
}

QPushButton:disabled {
    background-color: #17232d;
    color: #6f8798;
    border-color: #243644;
}

QPushButton#AccentButton {
    background-color: #12361f;
    border-color: #35b86d;
    color: #aaffd2;
}

QPushButton#AccentButton:hover {
    background-color: #174a2a;
}

QPushButton#DangerButton {
    background-color: #302019;
    border-color: #ff8c5a;
    color: #ffd2bf;
}

QHeaderView::section {
    background-color: #12202d;
    color: #a8d8f0;
    padding: 8px;
    border: 0;
    border-bottom: 1px solid #224051;
    font-weight: 600;
}

QTableWidget {
    gridline-color: #1a2935;
    alternate-background-color: #0f171f;
}

QTableWidget::item {
    padding: 8px;
}

QPlainTextEdit {
    padding: 10px;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 12px;
    color: #9ee8ff;
}

QScrollBar:vertical {
    width: 12px;
    background: transparent;
}

QScrollBar::handle:vertical {
    background: #21465e;
    border-radius: 6px;
    min-height: 24px;
}

QSplitter::handle {
    background-color: #13212c;
}
"""
