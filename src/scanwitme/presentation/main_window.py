"""Main application window for ScanWitMe."""

from __future__ import annotations

import logging
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.i18n import tr
from scanwitme.domain.interfaces import SettingsRepository
from scanwitme.domain.metadata import (
    APP_THEMES,
    APP_UI_LANGUAGES,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_HOTKEY,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_TEXT_DIRECTION,
    DEFAULT_THEME,
    DEFAULT_TRANSLATION_PROVIDER,
    DEFAULT_UI_LANGUAGE,
    DISPLAY_MODES,
    READING_DIRECTIONS,
    SOURCE_LANGUAGES,
    TARGET_LANGUAGES,
    TRANSLATION_PROVIDERS,
)
from scanwitme.presentation.theme import get_theme_stylesheet
from scanwitme.presentation.tray import create_default_tray_icon

logger = logging.getLogger("scanwitme.ui.main")

MAIN_STYLESHEET = get_theme_stylesheet("dark")


class MainWindow(QMainWindow):
    """Primary control window for ScanWitMe."""

    scan_requested = Signal()
    toggle_frame_requested = Signal()
    auto_scan_toggled = Signal(bool)
    settings_requested = Signal()
    history_requested = Signal()
    glossary_requested = Signal()
    source_language_changed = Signal(str)
    target_language_changed = Signal(str)
    ui_language_changed = Signal(str)
    theme_changed = Signal(str)
    provider_changed = Signal(str)
    display_mode_changed = Signal(str)
    text_direction_changed = Signal(str)

    def __init__(self, settings_repo: SettingsRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._auto_active = False
        self.setWindowTitle("ScanWitMe PC — Screen Translator")
        self.setWindowIcon(create_default_tray_icon())
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setFixedSize(540, 560)

        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralWidget")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header bar
        header_layout = QHBoxLayout()
        title_label = QLabel("ScanWitMe", central)
        title_label.setObjectName("appTitle")
        self._badge_label = QLabel(tr("badge", DEFAULT_UI_LANGUAGE), central)
        self._badge_label.setObjectName("badge")
        header_layout.addWidget(title_label)
        header_layout.addWidget(self._badge_label)
        header_layout.addStretch()

        self._theme_toggle_btn = QPushButton("🌙", central)
        self._theme_toggle_btn.setObjectName("secondaryButton")
        self._theme_toggle_btn.setToolTip("Ganti Tema Cepat (Dark / AMOLED / Light)")
        self._theme_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_toggle_btn.setFixedWidth(36)
        self._theme_toggle_btn.clicked.connect(self._cycle_theme)
        header_layout.addWidget(self._theme_toggle_btn)

        self._glossary_btn = QPushButton("📖 Kamus", central)
        self._glossary_btn.setObjectName("secondaryButton")
        self._glossary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._glossary_btn.clicked.connect(self.glossary_requested.emit)
        header_layout.addWidget(self._glossary_btn)

        self._history_btn = QPushButton("📚 Riwayat", central)
        self._history_btn.setObjectName("secondaryButton")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.clicked.connect(self.history_requested.emit)
        header_layout.addWidget(self._history_btn)

        self._settings_btn = QPushButton("⚙ Pengaturan", central)
        self._settings_btn.setObjectName("secondaryButton")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        header_layout.addWidget(self._settings_btn)

        layout.addLayout(header_layout)

        # Hero Radar Card (Status Visualizer adapted from Android edition)
        self._hero_card = QFrame(central)
        self._hero_card.setObjectName("heroCard")
        self._hero_card.setStyleSheet(
            """
            QFrame#heroCard {
                background-color: #1e293b;
                border: 1.5px solid #334155;
                border-radius: 12px;
            }
            """
        )
        hero_layout = QHBoxLayout(self._hero_card)
        hero_layout.setContentsMargins(14, 8, 14, 8)

        self._radar_status_label = QLabel("⚡ RADAR SIAP • STANDBY", self._hero_card)
        self._radar_status_label.setStyleSheet(
            "color: #818cf8; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;"
        )
        hero_layout.addWidget(self._radar_status_label)
        hero_layout.addStretch()

        self._config_badge_label = QLabel("AUTO ➔ ID • Manga RTL", self._hero_card)
        self._config_badge_label.setStyleSheet(
            """
            background-color: #312e81;
            color: #c7d2fe;
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
            """
        )
        hero_layout.addWidget(self._config_badge_label)
        layout.addWidget(self._hero_card)

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

        # Quick Comic Readers Row (adapted from Mobile edition)
        readers_row = QHBoxLayout()
        readers_row.setSpacing(6)
        readers_lbl = QLabel("Komik Web:", central)
        readers_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        readers_row.addWidget(readers_lbl)

        for name, url in [
            ("Webtoon", "https://www.webtoons.com/id/"),
            ("MangaDex", "https://mangadex.org/"),
            ("Asura", "https://asuracomic.net/"),
        ]:
            btn = QPushButton(name, central)
            btn.setObjectName("secondaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
            btn.clicked.connect(
                lambda checked=False, target_url=url, title=name: self._open_reader(title, target_url)
            )
            readers_row.addWidget(btn)

        readers_row.addStretch()
        layout.addLayout(readers_row)

        # Quick Settings Group
        group = QGroupBox("Konfigurasi Cepat", central)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        # Language row
        lang_row = QHBoxLayout()
        src_label = QLabel("Bahasa Asli:", group)
        src_label.setStyleSheet("color: #94a3b8;")
        self._src_combo = QComboBox(group)
        for opt in SOURCE_LANGUAGES:
            self._src_combo.addItem(opt.label, opt.code)
        self._src_combo.currentIndexChanged.connect(self._on_source_lang_changed)

        arrow_label = QLabel("➔", group)
        arrow_label.setStyleSheet("color: #38bdf8; font-weight: bold;")

        self._tgt_combo = QComboBox(group)
        for opt in TARGET_LANGUAGES:
            self._tgt_combo.addItem(opt.label, opt.code)
        self._tgt_combo.currentIndexChanged.connect(self._on_target_lang_changed)

        lang_row.addWidget(src_label)
        lang_row.addWidget(self._src_combo)
        lang_row.addWidget(arrow_label)
        lang_row.addWidget(self._tgt_combo)
        lang_row.addStretch()
        group_layout.addLayout(lang_row)

        # Provider row
        provider_row = QHBoxLayout()
        prov_label = QLabel("Provider:", group)
        prov_label.setStyleSheet("color: #94a3b8;")
        self._prov_combo = QComboBox(group)
        for opt in TRANSLATION_PROVIDERS:
            self._prov_combo.addItem(opt.label, opt.id)
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
        for opt in DISPLAY_MODES:
            self._mode_combo.addItem(opt.label, opt.id)
        self._mode_combo.currentIndexChanged.connect(self._on_display_mode_changed)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        group_layout.addLayout(mode_row)

        # Direction row (Auto Smart Detect vs Vertical Manga vs Horizontal)
        dir_row = QHBoxLayout()
        dir_label = QLabel("Arah Baca:", group)
        dir_label.setStyleSheet("color: #94a3b8;")
        self._dir_combo = QComboBox(group)
        for opt in READING_DIRECTIONS:
            self._dir_combo.addItem(opt.label, opt.id)
        self._dir_combo.currentIndexChanged.connect(self._on_direction_changed)

        dir_row.addWidget(dir_label)
        dir_row.addWidget(self._dir_combo)
        dir_row.addStretch()
        group_layout.addLayout(dir_row)

        # UI Language & Theme row
        pref_row = QHBoxLayout()
        self._ui_label = QLabel("Bahasa UI:", group)
        self._ui_label.setStyleSheet("color: #94a3b8;")
        self._ui_combo = QComboBox(group)
        for opt in APP_UI_LANGUAGES:
            self._ui_combo.addItem(opt.label, opt.code)
        self._ui_combo.currentIndexChanged.connect(self._on_ui_lang_changed)

        self._theme_label = QLabel("Tema:", group)
        self._theme_label.setStyleSheet("color: #94a3b8;")
        self._theme_combo = QComboBox(group)
        for opt in APP_THEMES:
            self._theme_combo.addItem(opt.label, opt.id)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        pref_row.addWidget(self._ui_label)
        pref_row.addWidget(self._ui_combo)
        pref_row.addSpacing(10)
        pref_row.addWidget(self._theme_label)
        pref_row.addWidget(self._theme_combo)
        pref_row.addStretch()
        group_layout.addLayout(pref_row)

        self._group_box = group
        self._src_label = src_label
        self._prov_label = prov_label
        self._mode_label = mode_label
        self._dir_label = dir_label

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
        src_lang = self._settings_repo.get("default_source_language", DEFAULT_SOURCE_LANGUAGE)
        idx = self._src_combo.findData(src_lang)
        if idx >= 0:
            self._src_combo.setCurrentIndex(idx)

        tgt_lang = self._settings_repo.get("default_target_language", DEFAULT_TARGET_LANGUAGE)
        idx_t = self._tgt_combo.findData(tgt_lang)
        if idx_t >= 0:
            self._tgt_combo.setCurrentIndex(idx_t)

        provider = self._settings_repo.get(
            "default_translation_provider", DEFAULT_TRANSLATION_PROVIDER
        )
        idx_p = self._prov_combo.findData(provider)
        if idx_p >= 0:
            self._prov_combo.setCurrentIndex(idx_p)

        display_mode = self._settings_repo.get("display_mode", DEFAULT_DISPLAY_MODE)
        idx_m = self._mode_combo.findData(display_mode)
        if idx_m >= 0:
            self._mode_combo.setCurrentIndex(idx_m)

        text_dir = self._settings_repo.get("text_direction", DEFAULT_TEXT_DIRECTION)
        idx_d = self._dir_combo.findData(text_dir)
        if idx_d >= 0:
            self._dir_combo.setCurrentIndex(idx_d)

        ui_lang = self._settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        idx_u = self._ui_combo.findData(ui_lang)
        if idx_u >= 0:
            self._ui_combo.setCurrentIndex(idx_u)

        theme = self._settings_repo.get("default_theme", DEFAULT_THEME)
        idx_th = self._theme_combo.findData(theme)
        if idx_th >= 0:
            self._theme_combo.setCurrentIndex(idx_th)
        self.apply_theme(theme)
        if hasattr(self, "_theme_toggle_btn"):
            self._theme_toggle_btn.setText("☀️" if theme == "light" else ("⚫" if theme == "amoled" else "🌙"))
        self._update_config_badge()

        self.retranslate_ui()

        hotkey = self._settings_repo.get("hotkey", DEFAULT_HOTKEY)
        # Format for display: replace <ctrl> with Ctrl, etc.
        disp = (
            hotkey.replace("<ctrl>", "Ctrl")
            .replace("<shift>", "Shift")
            .replace("<alt>", "Alt")
            .replace("+", "+")
        )
        self._hotkey_label.setText(f"Hotkey: {disp}")

    def _open_reader(self, name: str, url: str) -> None:
        """Launch popular comic reading URL in default web browser."""
        webbrowser.open(url)
        self.set_status(f"Membuka {name} di browser...")

    def _cycle_theme(self) -> None:
        """Quick 1-click theme rotator (Dark -> AMOLED -> Light)."""
        current = self._theme_combo.currentData()
        themes = ["dark", "amoled", "light"]
        next_idx = (themes.index(current) + 1) % len(themes) if current in themes else 0
        next_theme = themes[next_idx]

        idx = self._theme_combo.findData(next_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

    def _update_config_badge(self) -> None:
        """Update live config pill inside the hero radar card."""
        if not hasattr(self, "_config_badge_label"):
            return
        src = self._src_combo.currentData() or "AUTO"
        tgt = self._tgt_combo.currentData() or "ID"
        dir_code = self._dir_combo.currentData() or "auto"
        dir_text = (
            "Manga RTL"
            if dir_code in ("vertical", "rtl")
            else ("Webtoon LTR" if dir_code in ("horizontal", "ltr") else "Auto")
        )
        self._config_badge_label.setText(f"{src.upper()} ➔ {tgt.upper()} • {dir_text}")

    def update_from_settings(self) -> None:
        """Refresh UI state when settings change."""
        self._load_settings()

    def apply_theme(self, theme_id: str) -> None:
        """Apply Qt stylesheet corresponding to theme."""
        self.setStyleSheet(get_theme_stylesheet(theme_id))

    def _on_theme_changed(self) -> None:
        theme = self._theme_combo.currentData()
        self._settings_repo.set("default_theme", theme)
        self._settings_repo.save()
        self.apply_theme(theme)
        if hasattr(self, "_theme_toggle_btn"):
            self._theme_toggle_btn.setText("☀️" if theme == "light" else ("⚫" if theme == "amoled" else "🌙"))
        self.theme_changed.emit(theme)

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
            if hasattr(self, "_hero_card"):
                self._hero_card.setStyleSheet("""
                    QFrame#heroCard {
                        background-color: #064e3b;
                        border: 1.5px solid #10b981;
                        border-radius: 12px;
                    }
                """)
                self._radar_status_label.setText("🟢 RADAR AKTIF • MEMANTAU KOMIK")
                self._radar_status_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self._auto_btn.setStyleSheet("")
            self._auto_btn.setText("🔄 Live Auto")
            if hasattr(self, "_hero_card"):
                self._hero_card.setStyleSheet("""
                    QFrame#heroCard {
                        background-color: #1e293b;
                        border: 1.5px solid #334155;
                        border-radius: 12px;
                    }
                """)
                self._radar_status_label.setText("⚡ RADAR SIAP • STANDBY")
                self._radar_status_label.setStyleSheet("color: #818cf8; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;")

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
        self._update_config_badge()
        self.source_language_changed.emit(lang)

    def _on_target_lang_changed(self) -> None:
        lang = self._tgt_combo.currentData()
        self._settings_repo.set("default_target_language", lang)
        self._settings_repo.save()
        self._update_config_badge()
        self.target_language_changed.emit(lang)

    def _on_ui_lang_changed(self) -> None:
        lang = self._ui_combo.currentData()
        self._settings_repo.set("default_ui_language", lang)
        self._settings_repo.save()
        self.retranslate_ui()
        self.ui_language_changed.emit(lang)

    def retranslate_ui(self) -> None:
        """Update all UI text according to currently configured UI language."""
        lang = self._settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        self.setWindowTitle(tr("app_title", lang))
        if hasattr(self, "_badge_label"):
            self._badge_label.setText(tr("badge", lang))
        if hasattr(self, "_glossary_btn"):
            self._glossary_btn.setText(tr("btn_glossary", lang))
        if hasattr(self, "_history_btn"):
            self._history_btn.setText(tr("btn_history", lang))
        self._settings_btn.setText(tr("btn_settings", lang))
        self._scan_btn.setText(f"{tr('btn_scan', lang)} (Ctrl+Shift+S)")
        self._frame_btn.setText(tr("btn_sniper", lang))
        if not getattr(self, "_auto_active", False):
            self._auto_btn.setText(tr("btn_live", lang))
        if hasattr(self, "_group_box"):
            self._group_box.setTitle(tr("quick_settings", lang))
        if hasattr(self, "_src_label"):
            self._src_label.setText(tr("label_source_lang", lang))
        if hasattr(self, "_prov_label"):
            self._prov_label.setText(tr("label_provider", lang))
        if hasattr(self, "_mode_label"):
            self._mode_label.setText(tr("label_display_mode", lang))
        if hasattr(self, "_dir_label"):
            self._dir_label.setText(tr("label_direction", lang))
        if hasattr(self, "_ui_label"):
            self._ui_label.setText(tr("label_ui_lang", lang))
        if hasattr(self, "_theme_label"):
            self._theme_label.setText(tr("label_theme", lang))

        # Update metadata combo box item labels dynamically
        if hasattr(self, "_src_combo"):
            for i, opt in enumerate(SOURCE_LANGUAGES):
                self._src_combo.setItemText(i, opt.get_label(lang))
        if hasattr(self, "_tgt_combo"):
            for i, opt in enumerate(TARGET_LANGUAGES):
                self._tgt_combo.setItemText(i, opt.get_label(lang))
        if hasattr(self, "_prov_combo"):
            for i, opt in enumerate(TRANSLATION_PROVIDERS):
                self._prov_combo.setItemText(i, opt.get_label(lang))
        if hasattr(self, "_mode_combo"):
            for i, opt in enumerate(DISPLAY_MODES):
                self._mode_combo.setItemText(i, opt.get_label(lang))
        if hasattr(self, "_dir_combo"):
            for i, opt in enumerate(READING_DIRECTIONS):
                self._dir_combo.setItemText(i, opt.get_label(lang))
        if hasattr(self, "_theme_combo"):
            for i, opt in enumerate(APP_THEMES):
                self._theme_combo.setItemText(i, opt.get_label(lang))

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

    def _on_direction_changed(self) -> None:
        direction = self._dir_combo.currentData()
        self._settings_repo.set("text_direction", direction)
        self._settings_repo.save()
        self._update_config_badge()
        self.text_direction_changed.emit(direction)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray instead of quitting."""
        self.hide()
        event.ignore()
