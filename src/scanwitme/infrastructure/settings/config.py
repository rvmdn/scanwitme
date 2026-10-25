"""Configuration management and AppSettings for ScanWitMe."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
    get_valid_display_modes,
    get_valid_ocr_engines,
    get_valid_provider_ids,
    get_valid_reading_directions,
    get_valid_source_codes,
    get_valid_target_codes,
    get_valid_theme_ids,
    get_valid_ui_language_codes,
)


def get_default_config_dir() -> Path:
    """Return platform-standard directory for storing ScanWitMe settings."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / ".config"
    config_dir = base / "ScanWitMe"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@dataclass
class AppSettings:
    """Strongly typed application settings."""

    google_translate_api_key: str | None = None
    default_source_language: str = DEFAULT_SOURCE_LANGUAGE
    default_target_language: str = DEFAULT_TARGET_LANGUAGE
    default_ui_language: str = DEFAULT_UI_LANGUAGE
    default_theme: str = DEFAULT_THEME
    default_translation_provider: str = DEFAULT_TRANSLATION_PROVIDER
    display_mode: str = DEFAULT_DISPLAY_MODE
    text_direction: str = DEFAULT_TEXT_DIRECTION
    ocr_engine: str = DEFAULT_OCR_ENGINE
    hotkey: str = DEFAULT_HOTKEY
    cache_enabled: bool = DEFAULT_CACHE_ENABLED
    cache_db_path: str = ""
    history_db_path: str = ""
    glossary_db_path: str = ""
    log_level: str = DEFAULT_LOG_LEVEL

    def __post_init__(self) -> None:
        # Load from environment variables if not explicitly provided
        if not self.google_translate_api_key:
            self.google_translate_api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")

        if not self.cache_db_path:
            self.cache_db_path = str(get_default_config_dir() / "scanwitme_cache.db")

        if not self.history_db_path:
            self.history_db_path = str(get_default_config_dir() / "scanwitme_history.db")

        if not self.glossary_db_path:
            self.glossary_db_path = str(get_default_config_dir() / "scanwitme_glossary.db")

        # Validate against parameterized metadata
        if self.default_source_language not in get_valid_source_codes():
            self.default_source_language = DEFAULT_SOURCE_LANGUAGE

        if self.default_target_language not in get_valid_target_codes():
            self.default_target_language = DEFAULT_TARGET_LANGUAGE

        if self.default_ui_language not in get_valid_ui_language_codes():
            self.default_ui_language = DEFAULT_UI_LANGUAGE

        if self.default_theme not in get_valid_theme_ids():
            self.default_theme = DEFAULT_THEME

        if self.default_translation_provider not in get_valid_provider_ids():
            self.default_translation_provider = DEFAULT_TRANSLATION_PROVIDER

        if self.text_direction not in get_valid_reading_directions():
            self.text_direction = DEFAULT_TEXT_DIRECTION

        if self.ocr_engine not in get_valid_ocr_engines():
            self.ocr_engine = DEFAULT_OCR_ENGINE

        if self.display_mode not in get_valid_display_modes():
            self.display_mode = DEFAULT_DISPLAY_MODE
