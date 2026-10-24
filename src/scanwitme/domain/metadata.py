"""Parameterized application metadata and configuration options.

Central source of truth for all languages, translation providers,
display modes, reading directions, and OCR engines supported by ScanWitMe.
Adding a new language or provider requires only defining a metadata entry here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageOption:
    """Metadata for a source or target language."""

    code: str  # Standard language code: "auto", "ko", "zh-CN", "ja", "en", etc.
    name: str  # Human readable name in Indonesian, e.g. "Korea", "Jepang"
    label: str  # UI combo box label, e.g. "Korea (ko)", "🔍 Deteksi Otomatis (auto)"
    ocr_model: str = "ch"  # Underlying PaddleOCR model family ("ch", "korean", "japan", "en")
    is_auto: bool = False
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderOption:
    """Metadata for a translation provider."""

    id: str  # Unique identifier: "free_direct", "web_launcher", "cloud_v2"
    name: str  # Short name
    label: str  # UI display label
    description: str  # Detailed description / tooltip
    requires_api_key: bool = False


@dataclass(frozen=True)
class DisplayModeOption:
    """Metadata for an overlay presentation mode."""

    id: str  # "bubble", "card", "both"
    name: str
    label: str
    description: str


@dataclass(frozen=True)
class ReadingDirectionOption:
    """Metadata for text layout and reading direction."""

    id: str  # "auto", "vertical", "horizontal"
    name: str
    label: str
    description: str


@dataclass(frozen=True)
class OCREngineOption:
    """Metadata for an OCR inference engine."""

    id: str  # "paddle", "manga_ocr"
    name: str
    label: str
    description: str


# ============================================================================
# Central Metadata Registries
# ============================================================================

# 1. Source Languages
SOURCE_LANGUAGES: tuple[LanguageOption, ...] = (
    LanguageOption(
        code="auto",
        name="Deteksi Otomatis",
        label="🔍 Deteksi Otomatis (auto)",
        ocr_model="ch",
        is_auto=True,
        aliases=["automatic", "detect"],
    ),
    LanguageOption(
        code="ko",
        name="Korea",
        label="Korea (ko)",
        ocr_model="korean",
        aliases=["korean", "hangul"],
    ),
    LanguageOption(
        code="zh-CN",
        name="Mandarin Sederhana",
        label="Mandarin Sederhana (zh-CN)",
        ocr_model="ch",
        aliases=["chinese", "mandarin", "zh"],
    ),
    LanguageOption(
        code="zh-TW",
        name="Mandarin Tradisional",
        label="Mandarin Tradisional (zh-TW)",
        ocr_model="ch",
        aliases=["traditional_chinese"],
    ),
    LanguageOption(
        code="ja",
        name="Jepang",
        label="Jepang (ja)",
        ocr_model="japan",
        aliases=["japanese", "nihongo"],
    ),
    LanguageOption(
        code="en",
        name="Inggris",
        label="Inggris (en)",
        ocr_model="en",
        aliases=["english"],
    ),
)

# 2. Target Languages
TARGET_LANGUAGES: tuple[LanguageOption, ...] = (
    LanguageOption(
        code="id",
        name="Indonesia",
        label="Indonesia (id)",
        aliases=["indonesian", "bahasa"],
    ),
)

# 3. Translation Providers
TRANSLATION_PROVIDERS: tuple[ProviderOption, ...] = (
    ProviderOption(
        id="free_direct",
        name="Terjemah Langsung (Gratis)",
        label="⚡ Terjemah Langsung (Gratis / In-App)",
        description="Terjemahan instan langsung di aplikasi tanpa perlu mendaftar atau API key.",
        requires_api_key=False,
    ),
    ProviderOption(
        id="web_launcher",
        name="Google Translate Web",
        label="🌐 Google Translate Web (Browser)",
        description="Membuka hasil teks di tab browser Google Translate resmi.",
        requires_api_key=False,
    ),
    ProviderOption(
        id="cloud_v2",
        name="Google Cloud Translation v2",
        label="🔑 Google Cloud API v2 (Perlu API Key)",
        description="Menggunakan Google Cloud Translation API resmi berbayar / kuota pribadi.",
        requires_api_key=True,
    ),
)

# 4. Display Modes
DISPLAY_MODES: tuple[DisplayModeOption, ...] = (
    DisplayModeOption(
        id="bubble",
        name="Balon Komik",
        label="💬 Balon Komik (Direct Bubble)",
        description="Menempelkan teks terjemahan langsung di atas balon komik asli.",
    ),
    DisplayModeOption(
        id="card",
        name="Kartu Pop-up",
        label="📋 Kartu Pop-up (Floating Card)",
        description="Menampilkan kotak kartu terjemahan melayang di bawah area pemindaian.",
    ),
    DisplayModeOption(
        id="both",
        name="Keduanya",
        label="🔀 Keduanya (Bubble + Card)",
        description="Menampilkan balon komik langsung dan kartu pop-up sekaligus.",
    ),
)

# 5. Reading Directions
READING_DIRECTIONS: tuple[ReadingDirectionOption, ...] = (
    ReadingDirectionOption(
        id="auto",
        name="Otomatis",
        label="🔄 Otomatis (Smart Detect)",
        description="Mendeteksi orientasi vertikal vs horizontal secara cerdas berdasarkan rasio teks.",
    ),
    ReadingDirectionOption(
        id="vertical",
        name="Vertikal Manga Jepang",
        label="⛩️ Vertikal Manga Jepang (縦書き)",
        description="Membaca teks tegak lurus tradisional (Right-to-Left, Top-to-Bottom).",
    ),
    ReadingDirectionOption(
        id="horizontal",
        name="Horizontal Standar",
        label="➡️ Horizontal Standar (LTR)",
        description="Membaca teks mendatar standar barat/manhwa modern (Left-to-Right, Top-to-Bottom).",
    ),
)

# 6. OCR Engines
OCR_ENGINES: tuple[OCREngineOption, ...] = (
    OCREngineOption(
        id="paddle",
        name="PaddleOCR",
        label="PaddleOCR (Bawaan — Multi-Bahasa & Vertikal)",
        description="Mesin OCR lokal bawaan berkecepatan tinggi dengan dukungan multi-bahasa dan orientasi.",
    ),
    OCREngineOption(
        id="manga_ocr",
        name="Manga-OCR",
        label="Manga-OCR (Khusus Manga Jepang)",
        description="Model vision transformer khusus manga Jepang (kha-white/manga-ocr).",
    ),
)


# ============================================================================
# Default Value Constants
# ============================================================================

DEFAULT_SOURCE_LANGUAGE: str = "auto"
DEFAULT_TARGET_LANGUAGE: str = "id"
DEFAULT_TRANSLATION_PROVIDER: str = "free_direct"
DEFAULT_DISPLAY_MODE: str = "both"
DEFAULT_TEXT_DIRECTION: str = "auto"
DEFAULT_OCR_ENGINE: str = "paddle"
DEFAULT_HOTKEY: str = "<ctrl>+<shift>+s"
DEFAULT_CACHE_ENABLED: bool = True
DEFAULT_LOG_LEVEL: str = "INFO"


# ============================================================================
# Lookup and Validation Helpers
# ============================================================================

def get_source_languages() -> tuple[LanguageOption, ...]:
    """Return all configured source languages."""
    return SOURCE_LANGUAGES


def get_target_languages() -> tuple[LanguageOption, ...]:
    """Return all configured target languages."""
    return TARGET_LANGUAGES


def get_translation_providers() -> tuple[ProviderOption, ...]:
    """Return all configured translation providers."""
    return TRANSLATION_PROVIDERS


def get_display_modes() -> tuple[DisplayModeOption, ...]:
    """Return all configured display modes."""
    return DISPLAY_MODES


def get_reading_directions() -> tuple[ReadingDirectionOption, ...]:
    """Return all configured reading directions."""
    return READING_DIRECTIONS


def get_ocr_engines() -> tuple[OCREngineOption, ...]:
    """Return all configured OCR engines."""
    return OCR_ENGINES


def get_valid_source_codes() -> set[str]:
    """Return valid source language code set."""
    return {lang.code for lang in SOURCE_LANGUAGES}


def get_valid_target_codes() -> set[str]:
    """Return valid target language code set."""
    return {lang.code for lang in TARGET_LANGUAGES}


def get_valid_provider_ids() -> set[str]:
    """Return valid translation provider id set."""
    return {prov.id for prov in TRANSLATION_PROVIDERS}


def get_valid_display_modes() -> set[str]:
    """Return valid display mode id set."""
    return {mode.id for mode in DISPLAY_MODES}


def get_valid_reading_directions() -> set[str]:
    """Return valid reading direction id set."""
    return {d.id for d in READING_DIRECTIONS}


def get_valid_ocr_engines() -> set[str]:
    """Return valid OCR engine id set."""
    return {eng.id for eng in OCR_ENGINES}


def get_language_to_ocr_mapping() -> dict[str, str]:
    """Return dictionary mapping language codes and aliases to PaddleOCR model names."""
    mapping: dict[str, str] = {}
    for lang in SOURCE_LANGUAGES:
        if lang.code != "auto":
            mapping[lang.code] = lang.ocr_model
            for alias in lang.aliases:
                mapping[alias] = lang.ocr_model
    return mapping


def get_source_language_by_code(code: str) -> LanguageOption | None:
    """Find source language option by code or alias."""
    for lang in SOURCE_LANGUAGES:
        if lang.code == code or code in lang.aliases:
            return lang
    return None


def get_provider_by_id(provider_id: str) -> ProviderOption | None:
    """Find provider option by id."""
    for prov in TRANSLATION_PROVIDERS:
        if prov.id == provider_id:
            return prov
    return None
