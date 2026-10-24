"""Unit tests for configuration and settings."""

from pathlib import Path

import pytest

from scanwitme.infrastructure.settings.config import AppSettings
from scanwitme.infrastructure.settings.json_settings import JsonSettingsRepository


@pytest.mark.unit
def test_app_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.default_source_language in {"ko", "zh-CN", "zh-TW", "auto"}
    assert settings.default_target_language == "id"
    assert settings.default_translation_provider in {"free_direct", "cloud_v2", "web_launcher"}
    assert settings.hotkey == "<ctrl>+<shift>+s"
    assert settings.cache_enabled is True
    assert "scanwitme_cache.db" in settings.cache_db_path


@pytest.mark.unit
def test_app_settings_validation_fallback() -> None:
    settings = AppSettings(
        default_source_language="invalid_lang",
        default_target_language="invalid_target",
        default_translation_provider="invalid_provider",
    )
    # Should fall back to safe defaults
    assert settings.default_source_language == "auto"
    assert settings.default_target_language == "id"
    assert settings.default_translation_provider == "free_direct"


@pytest.mark.unit
def test_json_settings_repository(tmp_path: Path) -> None:
    config_file = tmp_path / "test_settings.json"
    repo = JsonSettingsRepository(file_path=config_file)

    assert repo.get("default_source_language") is None
    repo.set("default_source_language", "zh-CN")
    repo.set("hotkey", "<ctrl>+<shift>+x")
    repo.save()

    assert config_file.exists()

    # Reload from disk
    new_repo = JsonSettingsRepository(file_path=config_file)
    assert new_repo.get("default_source_language") == "zh-CN"
    assert new_repo.get("hotkey") == "<ctrl>+<shift>+x"

    app_settings = new_repo.to_app_settings()
    assert app_settings.default_source_language == "zh-CN"
    assert app_settings.hotkey == "<ctrl>+<shift>+x"
