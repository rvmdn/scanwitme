"""JSON file-based implementation of SettingsRepository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanwitme.domain.interfaces import SettingsRepository
from scanwitme.domain.metadata import (
    DEFAULT_CACHE_ENABLED,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_HOTKEY,
    DEFAULT_LOG_LEVEL,
    DEFAULT_OCR_ENGINE,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_TEXT_DIRECTION,
    DEFAULT_THEME,
    DEFAULT_TRANSLATION_PROVIDER,
    DEFAULT_UI_LANGUAGE,
)
from scanwitme.infrastructure.settings.config import AppSettings, get_default_config_dir


class JsonSettingsRepository(SettingsRepository):
    """Persists user configuration as a JSON file in AppData."""

    def __init__(self, file_path: Path | None = None) -> None:
        if file_path is None:
            self._file_path = get_default_config_dir() / "settings.json"
        else:
            self._file_path = file_path
        self._data: dict[str, Any] = {}
        self.load()

    @property
    def file_path(self) -> Path:
        return self._file_path

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        """Persist dictionary to disk with pretty formatting."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid saving null/empty api keys if already saved
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def load(self) -> dict[str, Any]:
        """Load settings from JSON file if present."""
        if self._file_path.exists():
            try:
                with open(self._file_path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}
        return self._data

    def to_app_settings(self) -> AppSettings:
        """Instantiate strongly typed AppSettings from stored values."""
        return AppSettings(
            google_translate_api_key=self.get("google_translate_api_key"),
            default_source_language=self.get("default_source_language", DEFAULT_SOURCE_LANGUAGE),
            default_target_language=self.get("default_target_language", DEFAULT_TARGET_LANGUAGE),
            default_ui_language=self.get("default_ui_language", DEFAULT_UI_LANGUAGE),
            default_theme=self.get("default_theme", DEFAULT_THEME),
            default_translation_provider=self.get(
                "default_translation_provider", DEFAULT_TRANSLATION_PROVIDER
            ),
            display_mode=self.get("display_mode", DEFAULT_DISPLAY_MODE),
            text_direction=self.get("text_direction", DEFAULT_TEXT_DIRECTION),
            ocr_engine=self.get("ocr_engine", DEFAULT_OCR_ENGINE),
            hotkey=self.get("hotkey", DEFAULT_HOTKEY),
            cache_enabled=self.get("cache_enabled", DEFAULT_CACHE_ENABLED),
            cache_db_path=self.get("cache_db_path", ""),
            log_level=self.get("log_level", DEFAULT_LOG_LEVEL),
        )
