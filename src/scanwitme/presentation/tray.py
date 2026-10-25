"""Windows System Tray integration for ScanWitMe."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

logger = logging.getLogger("scanwitme.tray")


def create_default_tray_icon() -> QIcon:
    """Create a crisp programmatic icon for the system tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Blue rounded badge
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(QColor(255, 255, 255))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    # Letter 'S'
    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(14)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0004 | 0x0080, "S")  # AlignCenter
    painter.end()

    return QIcon(pixmap)


class TrayManager(QObject):
    """Manages the Windows system tray icon and context menu."""

    scan_requested = Signal()
    show_main_requested = Signal()
    history_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent_widget: QWidget | None = None) -> None:
        super().__init__(parent_widget)
        self._tray_icon = QSystemTrayIcon(parent_widget)
        self._tray_icon.setIcon(create_default_tray_icon())
        self._tray_icon.setToolTip("ScanWitMe — Screen Translator")

        self._build_menu()
        self._tray_icon.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()

        self._scan_action = QAction("⚡ Scan Region (Ctrl+Shift+S)", menu)
        self._scan_action.triggered.connect(self.scan_requested.emit)
        menu.addAction(self._scan_action)

        menu.addSeparator()

        self._show_action = QAction("Buka ScanWitMe", menu)
        self._show_action.triggered.connect(self.show_main_requested.emit)
        menu.addAction(self._show_action)

        self._history_action = QAction("📚 Riwayat Dialog...", menu)
        self._history_action.triggered.connect(self.history_requested.emit)
        menu.addAction(self._history_action)

        self._settings_action = QAction("Pengaturan...", menu)
        self._settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        self._exit_action = QAction("Keluar", menu)
        self._exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(self._exit_action)

        self._tray_icon.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.scan_requested.emit()

    def show(self) -> None:
        self._tray_icon.show()

    def hide(self) -> None:
        self._tray_icon.hide()

    def show_message(self, title: str, message: str) -> None:
        self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
