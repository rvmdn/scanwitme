"""Theme stylesheet provider for ScanWitMe.

Supports Dark, Light, Midnight AMOLED, and System themes.
Designed to be easily extended with additional custom themes.
"""

from __future__ import annotations

DARK_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
}

QWidget#centralWidget {
    background-color: #0f172a;
}

QLabel#appTitle {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 700;
}

QLabel#badge {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusText {
    color: #94a3b8;
    font-size: 12px;
}

QGroupBox {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPushButton#scanButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    padding: 12px 20px;
    border: 1px solid #60a5fa;
}

QPushButton#scanButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}

QPushButton#scanButton:pressed {
    background: #1e40af;
}

QPushButton#secondaryButton {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}

QPushButton#secondaryButton:hover {
    background-color: #334155;
    color: #f8fafc;
}

QComboBox {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #2563eb;
    border: 1px solid #334155;
}
"""

LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #f8fafc;
}

QWidget#centralWidget {
    background-color: #f8fafc;
}

QLabel#appTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 700;
}

QLabel#badge {
    background-color: #e2e8f0;
    color: #0284c7;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusText {
    color: #64748b;
    font-size: 12px;
}

QGroupBox {
    color: #334155;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPushButton#scanButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    padding: 12px 20px;
    border: 1px solid #0284c7;
}

QPushButton#scanButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
}

QPushButton#scanButton:pressed {
    background: #075985;
}

QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}

QPushButton#secondaryButton:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QComboBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 1px solid #cbd5e1;
}
"""

AMOLED_STYLESHEET = """
QMainWindow {
    background-color: #000000;
}

QWidget#centralWidget {
    background-color: #000000;
}

QLabel#appTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}

QLabel#badge {
    background-color: #09090b;
    color: #38bdf8;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusText {
    color: #a1a1aa;
    font-size: 12px;
}

QGroupBox {
    color: #e4e4e7;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #27272a;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPushButton#scanButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    padding: 12px 20px;
    border: 1px solid #818cf8;
}

QPushButton#scanButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
}

QPushButton#scanButton:pressed {
    background: #3730a3;
}

QPushButton#secondaryButton {
    background-color: #09090b;
    color: #d4d4d8;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}

QPushButton#secondaryButton:hover {
    background-color: #18181b;
    color: #ffffff;
}

QComboBox {
    background-color: #09090b;
    color: #fafafa;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QComboBox QAbstractItemView {
    background-color: #09090b;
    color: #fafafa;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
    border: 1px solid #27272a;
}
"""


def get_theme_stylesheet(theme_id: str) -> str:
    """Return Qt stylesheet for given theme id."""
    if theme_id == "light":
        return LIGHT_STYLESHEET
    elif theme_id == "amoled":
        return AMOLED_STYLESHEET
    # Default and "system" fall back to Dark
    return DARK_STYLESHEET
