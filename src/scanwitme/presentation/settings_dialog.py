"""Settings dialog for ScanWitMe."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.interfaces import CacheRepository, SettingsRepository
from scanwitme.domain.metadata import (
    DEFAULT_DISPLAY_MODE,
    DEFAULT_HOTKEY,
    DEFAULT_OCR_ENGINE,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TEXT_DIRECTION,
    DEFAULT_TRANSLATION_PROVIDER,
    DISPLAY_MODES,
    OCR_ENGINES,
    READING_DIRECTIONS,
    SOURCE_LANGUAGES,
    TRANSLATION_PROVIDERS,
)


class SettingsDialog(QDialog):
    """Configuration modal for API keys, language defaults, and hotkeys."""

    settings_saved = Signal()

    def __init__(
        self,
        settings_repo: SettingsRepository,
        cache_repo: CacheRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._cache_repo = cache_repo
        self.setWindowTitle("Pengaturan — ScanWitMe")
        self.setFixedWidth(440)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        # API Key
        self._api_key_edit = QLineEdit(self)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("Masukkan Google Cloud Translation API Key")
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(self._api_key_edit)
        self._toggle_key_btn = QPushButton("👁", self)
        self._toggle_key_btn.setFixedWidth(32)
        self._toggle_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self._toggle_key_btn)
        form.addRow("API Key:", api_key_layout)

        # Source Language
        self._source_lang_combo = QComboBox(self)
        for opt in SOURCE_LANGUAGES:
            self._source_lang_combo.addItem(opt.label, opt.code)
        form.addRow("Bahasa Asli:", self._source_lang_combo)

        # Target Language
        self._target_lang_label = QLabel("Indonesia (id)", self)
        form.addRow("Bahasa Target:", self._target_lang_label)

        # Provider
        self._provider_combo = QComboBox(self)
        for opt in TRANSLATION_PROVIDERS:
            self._provider_combo.addItem(opt.label, opt.id)
        form.addRow("Provider:", self._provider_combo)

        # Display Mode
        self._mode_combo = QComboBox(self)
        for opt in DISPLAY_MODES:
            self._mode_combo.addItem(opt.label, opt.id)
        form.addRow("Mode Tampilan:", self._mode_combo)

        # Text Direction
        self._dir_combo = QComboBox(self)
        for opt in READING_DIRECTIONS:
            self._dir_combo.addItem(opt.label, opt.id)
        form.addRow("Arah Baca:", self._dir_combo)

        # OCR Engine
        self._engine_combo = QComboBox(self)
        for opt in OCR_ENGINES:
            self._engine_combo.addItem(opt.label, opt.id)
        form.addRow("Mesin OCR:", self._engine_combo)

        # Hotkey
        self._hotkey_edit = QLineEdit(self)
        self._hotkey_edit.setPlaceholderText("<ctrl>+<shift>+s")
        form.addRow("Hotkey:", self._hotkey_edit)

        layout.addLayout(form)

        # Cache management
        if self._cache_repo is not None:
            cache_layout = QHBoxLayout()
            cache_label = QLabel("Cache Terjemahan:")
            self._clear_cache_btn = QPushButton("Bersihkan Cache")
            self._clear_cache_btn.clicked.connect(self._on_clear_cache)
            cache_layout.addWidget(cache_label)
            cache_layout.addWidget(self._clear_cache_btn)
            layout.addLayout(cache_layout)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Batal", self)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("Simpan", self)
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def _toggle_api_key_visibility(self) -> None:
        if self._api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _load_values(self) -> None:
        api_key = self._settings_repo.get("google_translate_api_key", "")
        self._api_key_edit.setText(api_key or "")

        src_lang = self._settings_repo.get("default_source_language", DEFAULT_SOURCE_LANGUAGE)
        idx = self._source_lang_combo.findData(src_lang)
        if idx >= 0:
            self._source_lang_combo.setCurrentIndex(idx)

        provider = self._settings_repo.get("default_translation_provider", DEFAULT_TRANSLATION_PROVIDER)
        idx_p = self._provider_combo.findData(provider)
        if idx_p >= 0:
            self._provider_combo.setCurrentIndex(idx_p)

        mode = self._settings_repo.get("display_mode", DEFAULT_DISPLAY_MODE)
        idx_m = self._mode_combo.findData(mode)
        if idx_m >= 0:
            self._mode_combo.setCurrentIndex(idx_m)

        direction = self._settings_repo.get("text_direction", DEFAULT_TEXT_DIRECTION)
        idx_d = self._dir_combo.findData(direction)
        if idx_d >= 0:
            self._dir_combo.setCurrentIndex(idx_d)

        engine = self._settings_repo.get("ocr_engine", DEFAULT_OCR_ENGINE)
        idx_e = self._engine_combo.findData(engine)
        if idx_e >= 0:
            self._engine_combo.setCurrentIndex(idx_e)

        hotkey = self._settings_repo.get("hotkey", DEFAULT_HOTKEY)
        self._hotkey_edit.setText(hotkey)

    def _on_clear_cache(self) -> None:
        if self._cache_repo:
            self._cache_repo.clear()
            QMessageBox.information(
                self, "Cache Dibersihkan", "Semua riwayat cache terjemahan telah dihapus."
            )

    def _on_save(self) -> None:
        api_key = self._api_key_edit.text().strip()
        src_lang = self._source_lang_combo.currentData()
        provider = self._provider_combo.currentData()
        mode = self._mode_combo.currentData()
        direction = self._dir_combo.currentData()
        engine = self._engine_combo.currentData()
        hotkey = self._hotkey_edit.text().strip() or "<ctrl>+<shift>+s"

        self._settings_repo.set("google_translate_api_key", api_key if api_key else None)
        self._settings_repo.set("default_source_language", src_lang)
        self._settings_repo.set("default_translation_provider", provider)
        self._settings_repo.set("display_mode", mode)
        self._settings_repo.set("text_direction", direction)
        self._settings_repo.set("ocr_engine", engine)
        self._settings_repo.set("hotkey", hotkey)
        self._settings_repo.save()

        self.settings_saved.emit()
        self.accept()
