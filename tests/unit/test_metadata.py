"""Unit tests for parameterized metadata registries and helpers."""

import pytest

from scanwitme.domain.metadata import (
    APP_THEMES,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_HOTKEY,
    DEFAULT_OCR_ENGINE,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_TEXT_DIRECTION,
    DEFAULT_THEME,
    DEFAULT_TRANSLATION_PROVIDER,
    DISPLAY_MODES,
    OCR_ENGINES,
    READING_DIRECTIONS,
    SOURCE_LANGUAGES,
    TARGET_LANGUAGES,
    TRANSLATION_PROVIDERS,
    get_app_themes,
    get_display_modes,
    get_language_to_ocr_mapping,
    get_ocr_engines,
    get_provider_by_id,
    get_reading_directions,
    get_source_language_by_code,
    get_source_languages,
    get_target_languages,
    get_theme_by_id,
    get_translation_providers,
    get_valid_display_modes,
    get_valid_ocr_engines,
    get_valid_provider_ids,
    get_valid_reading_directions,
    get_valid_source_codes,
    get_valid_target_codes,
    get_valid_theme_ids,
)


@pytest.mark.unit
def test_metadata_registries_non_empty() -> None:
    assert len(SOURCE_LANGUAGES) >= 5
    assert len(TARGET_LANGUAGES) >= 1
    assert len(TRANSLATION_PROVIDERS) >= 3
    assert len(DISPLAY_MODES) >= 3
    assert len(READING_DIRECTIONS) >= 3
    assert len(OCR_ENGINES) >= 2
    assert len(APP_THEMES) >= 3


@pytest.mark.unit
def test_metadata_getter_functions() -> None:
    assert get_source_languages() == SOURCE_LANGUAGES
    assert get_target_languages() == TARGET_LANGUAGES
    assert get_translation_providers() == TRANSLATION_PROVIDERS
    assert get_display_modes() == DISPLAY_MODES
    assert get_reading_directions() == READING_DIRECTIONS
    assert get_ocr_engines() == OCR_ENGINES
    assert get_app_themes() == APP_THEMES


@pytest.mark.unit
def test_metadata_validation_sets() -> None:
    valid_sources = get_valid_source_codes()
    assert "auto" in valid_sources
    assert "ko" in valid_sources
    assert "zh-CN" in valid_sources
    assert "ja" in valid_sources
    assert "en" in valid_sources

    valid_targets = get_valid_target_codes()
    assert "id" in valid_targets

    valid_providers = get_valid_provider_ids()
    assert "free_direct" in valid_providers
    assert "web_launcher" in valid_providers
    assert "cloud_v2" in valid_providers

    valid_modes = get_valid_display_modes()
    assert "bubble" in valid_modes
    assert "card" in valid_modes
    assert "both" in valid_modes

    valid_directions = get_valid_reading_directions()
    assert "auto" in valid_directions
    assert "vertical" in valid_directions
    assert "horizontal" in valid_directions

    valid_engines = get_valid_ocr_engines()
    assert "paddle" in valid_engines
    assert "manga_ocr" in valid_engines

    valid_themes = get_valid_theme_ids()
    assert "dark" in valid_themes
    assert "light" in valid_themes
    assert "amoled" in valid_themes
    assert "system" in valid_themes


@pytest.mark.unit
def test_metadata_defaults_are_valid() -> None:
    assert DEFAULT_SOURCE_LANGUAGE in get_valid_source_codes()
    assert DEFAULT_TARGET_LANGUAGE in get_valid_target_codes()
    assert DEFAULT_TRANSLATION_PROVIDER in get_valid_provider_ids()
    assert DEFAULT_DISPLAY_MODE in get_valid_display_modes()
    assert DEFAULT_TEXT_DIRECTION in get_valid_reading_directions()
    assert DEFAULT_OCR_ENGINE in get_valid_ocr_engines()
    assert DEFAULT_THEME in get_valid_theme_ids()
    assert DEFAULT_HOTKEY == "<ctrl>+<shift>+s"


@pytest.mark.unit
def test_theme_metadata_helpers() -> None:
    dark = get_theme_by_id("dark")
    assert dark is not None
    assert dark.get_name("id") == "Gelap"
    assert dark.get_name("en") == "Dark"
    assert "🌙" in dark.get_label("id")
    assert "🌙" in dark.get_label("en")
    assert get_theme_by_id("non_existent") is None


@pytest.mark.unit
def test_get_language_to_ocr_mapping() -> None:
    mapping = get_language_to_ocr_mapping()
    assert mapping["ko"] == "korean"
    assert mapping["korean"] == "korean"
    assert mapping["zh-CN"] == "ch"
    assert mapping["ja"] == "japan"
    assert mapping["japanese"] == "japan"
    assert mapping["en"] == "en"


@pytest.mark.unit
def test_get_source_language_by_code() -> None:
    ko = get_source_language_by_code("ko")
    assert ko is not None
    assert ko.name == "Korea"
    assert ko.ocr_model == "korean"

    hangul = get_source_language_by_code("hangul")
    assert hangul is not None
    assert hangul.code == "ko"

    unknown = get_source_language_by_code("nonexistent")
    assert unknown is None


@pytest.mark.unit
def test_get_provider_by_id() -> None:
    free = get_provider_by_id("free_direct")
    assert free is not None
    assert free.requires_api_key is False

    cloud = get_provider_by_id("cloud_v2")
    assert cloud is not None
    assert cloud.requires_api_key is True

    unknown = get_provider_by_id("nonexistent")
    assert unknown is None
