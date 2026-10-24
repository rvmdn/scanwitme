"""JSON file-based implementation of SettingsRepository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanwitme.domain.interfaces import SettingsRepository
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
            default_source_language=self.get("default_source_language", "auto"),
            default_target_language=self.get("default_target_language", "id"),
            default_translation_provider=self.get("default_translation_provider", "free_direct"),
            hotkey=self.get("hotkey", "<ctrl>+<shift>+s"),
            cache_enabled=self.get("cache_enabled", True),
            cache_db_path=self.get("cache_db_path", ""),
            log_level=self.get("log_level", "INFO"),
        )
