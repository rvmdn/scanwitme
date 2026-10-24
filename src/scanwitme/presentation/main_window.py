"""Main application window for ScanWitMe."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.interfaces import SettingsRepository
from scanwitme.presentation.tray import create_default_tray_icon

logger = logging.getLogger("scanwitme.ui.main")

MAIN_STYLESHEET = """
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


class MainWindow(QMainWindow):
    """Primary control window for ScanWitMe."""

    scan_requested = Signal()
    toggle_frame_requested = Signal()
    auto_scan_toggled = Signal(bool)
    settings_requested = Signal()
    source_language_changed = Signal(str)
    provider_changed = Signal(str)
    display_mode_changed = Signal(str)

    def __init__(self, settings_repo: SettingsRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._auto_active = False
        self.setWindowTitle("ScanWitMe PC — Screen Translator")
        self.setWindowIcon(create_default_tray_icon())
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setFixedSize(500, 400)

        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralWidget")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header bar
        header_layout = QHBoxLayout()
        title_label = QLabel("ScanWitMe", central)
        title_label.setObjectName("appTitle")
        badge_label = QLabel("PC MVP", central)
        badge_label.setObjectName("badge")
        header_layout.addWidget(title_label)
        header_layout.addWidget(badge_label)
        header_layout.addStretch()

        self._settings_btn = QPushButton("⚙ Pengaturan", central)
        self._settings_btn.setObjectName("secondaryButton")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        header_layout.addWidget(self._settings_btn)

        layout.addLayout(header_layout)

        # Scan Buttons Row (Big Scan + Sniper Frame Mode + Live Auto)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._scan_btn = QPushButton("⚡ Scan Layar (Ctrl+Shift+S)", central)
        self._scan_btn.setObjectName("scanButton")
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.clicked.connect(self.scan_requested.emit)
        btn_row.addWidget(self._scan_btn, stretch=3)

        self._frame_btn = QPushButton("🎯 Bingkai", central)
        self._frame_btn.setObjectName("secondaryButton")
        self._frame_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._frame_btn.setToolTip(
            "Tampilkan bingkai tetap di layar untuk memindai area tertentu berulang kali."
        )
        self._frame_btn.clicked.connect(self.toggle_frame_requested.emit)
        btn_row.addWidget(self._frame_btn, stretch=1)

        self._auto_btn = QPushButton("🔄 Live Auto", central)
        self._auto_btn.setObjectName("secondaryButton")
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_btn.setToolTip("Mode Live: Otomatis memindai saat panel komik di-scroll.")
        self._auto_btn.clicked.connect(self._on_auto_clicked)
        btn_row.addWidget(self._auto_btn, stretch=1)

        layout.addLayout(btn_row)

        # Quick Settings Group
        group = QGroupBox("Konfigurasi Cepat", central)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        # Language row
        lang_row = QHBoxLayout()
        src_label = QLabel("Bahasa Asli:", group)
        src_label.setStyleSheet("color: #94a3b8;")
        self._src_combo = QComboBox(group)
        self._src_combo.addItem("🔍 Deteksi Otomatis (auto)", "auto")
        self._src_combo.addItem("Korea (ko)", "ko")
        self._src_combo.addItem("Mandarin Sederhana (zh-CN)", "zh-CN")
        self._src_combo.addItem("Mandarin Tradisional (zh-TW)", "zh-TW")
        self._src_combo.addItem("Jepang (ja)", "ja")
        self._src_combo.addItem("Inggris (en)", "en")
        self._src_combo.currentIndexChanged.connect(self._on_source_lang_changed)

        arrow_label = QLabel("➔", group)
        arrow_label.setStyleSheet("color: #38bdf8; font-weight: bold;")

        tgt_label = QLabel("Indonesia (id)", group)
        tgt_label.setStyleSheet("color: #f8fafc; font-weight: 600;")

        lang_row.addWidget(src_label)
        lang_row.addWidget(self._src_combo)
        lang_row.addWidget(arrow_label)
        lang_row.addWidget(tgt_label)
        lang_row.addStretch()
        group_layout.addLayout(lang_row)

        # Provider row
        provider_row = QHBoxLayout()
        prov_label = QLabel("Provider:", group)
        prov_label.setStyleSheet("color: #94a3b8;")
        self._prov_combo = QComboBox(group)
        self._prov_combo.addItem("⚡ Terjemah Langsung (Gratis / In-App)", "free_direct")
        self._prov_combo.addItem("🌐 Google Translate Web (Browser)", "web_launcher")
        self._prov_combo.addItem("🔑 Google Cloud API v2 (Perlu API Key)", "cloud_v2")
        self._prov_combo.currentIndexChanged.connect(self._on_provider_changed)

        provider_row.addWidget(prov_label)
        provider_row.addWidget(self._prov_combo)
        provider_row.addStretch()
        group_layout.addLayout(provider_row)

        # Mode row (Direct Bubble vs Pop-up Card vs Both)
        mode_row = QHBoxLayout()
        mode_label = QLabel("Tampilan:", group)
        mode_label.setStyleSheet("color: #94a3b8;")
        self._mode_combo = QComboBox(group)
        self._mode_combo.addItem("💬 Balon Komik (Direct Bubble)", "bubble")
        self._mode_combo.addItem("📋 Kartu Pop-up (Floating Card)", "card")
        self._mode_combo.addItem("🔀 Keduanya (Bubble + Card)", "both")
        self._mode_combo.currentIndexChanged.connect(self._on_display_mode_changed)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        group_layout.addLayout(mode_row)

        layout.addWidget(group)

        # Status and hotkey indicator footer
        footer_layout = QHBoxLayout()
        self._status_label = QLabel("Siap untuk memindai.", central)
        self._status_label.setObjectName("statusText")
        footer_layout.addWidget(self._status_label)
        footer_layout.addStretch()

        self._hotkey_label = QLabel("Hotkey: Ctrl+Shift+S", central)
        self._hotkey_label.setStyleSheet("color: #64748b; font-size: 11px;")
        footer_layout.addWidget(self._hotkey_label)

        layout.addLayout(footer_layout)
        self.setCentralWidget(central)

    def _load_settings(self) -> None:
        src_lang = self._settings_repo.get("default_source_language", "auto")
        idx = self._src_combo.findData(src_lang)
        if idx >= 0:
            self._src_combo.setCurrentIndex(idx)

        provider = self._settings_repo.get("default_translation_provider", "free_direct")
        idx_p = self._prov_combo.findData(provider)
        if idx_p >= 0:
            self._prov_combo.setCurrentIndex(idx_p)

        display_mode = self._settings_repo.get("display_mode", "bubble")
        idx_m = self._mode_combo.findData(display_mode)
        if idx_m >= 0:
            self._mode_combo.setCurrentIndex(idx_m)

        hotkey = self._settings_repo.get("hotkey", "<ctrl>+<shift>+s")
        # Format for display: replace <ctrl> with Ctrl, etc.
        disp = (
            hotkey.replace("<ctrl>", "Ctrl")
            .replace("<shift>", "Shift")
            .replace("<alt>", "Alt")
            .replace("+", "+")
        )
        self._hotkey_label.setText(f"Hotkey: {disp}")

    def update_from_settings(self) -> None:
        """Refresh UI state when settings change."""
        self._load_settings()

    def set_auto_scan_active(self, active: bool) -> None:
        """Update Live Auto-Scan button text and visual state."""
        self._auto_active = active
        if active:
            self._auto_btn.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #34d399;
            """)
            self._auto_btn.setText("🟢 Live: ON")
        else:
            self._auto_btn.setStyleSheet("")
            self._auto_btn.setText("🔄 Live Auto")

    def _on_auto_clicked(self) -> None:
        new_state = not getattr(self, "_auto_active", False)
        self.set_auto_scan_active(new_state)
        self.auto_scan_toggled.emit(new_state)

    def set_status(self, message: str) -> None:
        """Update footer status bar text."""
        self._status_label.setText(message)

    def _on_source_lang_changed(self) -> None:
        lang = self._src_combo.currentData()
        self._settings_repo.set("default_source_language", lang)
        self._settings_repo.save()
        self.source_language_changed.emit(lang)

    def _on_provider_changed(self) -> None:
        provider = self._prov_combo.currentData()
        self._settings_repo.set("default_translation_provider", provider)
        self._settings_repo.save()
        self.provider_changed.emit(provider)

    def _on_display_mode_changed(self) -> None:
        mode = self._mode_combo.currentData()
        self._settings_repo.set("display_mode", mode)
        self._settings_repo.save()
        self.display_mode_changed.emit(mode)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray instead of quitting."""
        self.hide()
        event.ignore()
