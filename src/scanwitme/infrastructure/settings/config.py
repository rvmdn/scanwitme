"""Configuration management and AppSettings for ScanWitMe."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    default_source_language: str = "auto"
    default_target_language: str = "id"
    default_translation_provider: str = "free_direct"  # "free_direct", "web_launcher", or "cloud_v2"
    display_mode: str = "both"  # "bubble" (manga inpainting), "card" (floating popup), or "both"
    text_direction: str = "auto"  # "auto" (smart detect), "vertical" (Japanese manga), or "horizontal"
    ocr_engine: str = "paddle"  # "paddle" (built-in multi-lang & vertical) or "manga_ocr"
    hotkey: str = "<ctrl>+<shift>+s"
    cache_enabled: bool = True
    cache_db_path: str = ""
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        # Load from environment variables if not explicitly provided
        if not self.google_translate_api_key:
            self.google_translate_api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")

        if not self.cache_db_path:
            self.cache_db_path = str(get_default_config_dir() / "scanwitme_cache.db")

        # Validate language codes
        valid_sources = {"ko", "zh-CN", "zh-TW", "ja", "en", "auto"}
        if self.default_source_language not in valid_sources:
            self.default_source_language = "auto"

        if self.default_target_language != "id":
            # MVP target is Indonesian
            self.default_target_language = "id"

        valid_providers = {"free_direct", "web_launcher", "cloud_v2"}
        if self.default_translation_provider not in valid_providers:
            self.default_translation_provider = "free_direct"

        valid_directions = {"auto", "vertical", "horizontal"}
        if self.text_direction not in valid_directions:
            self.text_direction = "auto"

        valid_engines = {"paddle", "manga_ocr"}
        if self.ocr_engine not in valid_engines:
            self.ocr_engine = "paddle"

        valid_display_modes = {"bubble", "card", "both"}
        if self.display_mode not in valid_display_modes:
            self.display_mode = "bubble"
