"""Abstract interfaces defining domain boundaries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from scanwitme.domain.models import (
    CaptureResult,
    GlossaryEntry,
    HistoryItem,
    OCRBlock,
    Rect,
    TranslationResult,
)


class CaptureProvider(ABC):
    """Abstract interface for screen capture."""

    @abstractmethod
    def capture_region(self, rect: Rect) -> CaptureResult:
        """Capture the screen region defined by rect.

        Raises:
            CaptureError: If the capture operation fails.
            CaptureCancelled: If the user cancels the selection.
        """
        pass


class OCRProvider(ABC):
    """Abstract interface for local optical character recognition."""

    @abstractmethod
    def recognize(
        self,
        image_data: bytes,
        language: str = "ko",
        direction: str = "auto",
    ) -> list[OCRBlock]:
        """Perform text detection and recognition on raw image bytes.

        Args:
            image_data: Encoded image bytes (PNG/JPEG) or raw bitmap.
            language: Target source language code (e.g. 'ko', 'zh', 'ja').
            direction: Text reading direction ('auto', 'vertical', 'horizontal').

        Returns:
            A list of recognized OCRBlocks sorted in natural reading order.

        Raises:
            OCRError: If model inference fails.
            OCRNoTextFound: If no text was detected.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if models and dependencies are loaded and ready."""
        pass


class TranslationProvider(ABC):
    """Abstract interface for text translation."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider (e.g. 'cloud_v2', 'web_launcher')."""
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "id",
    ) -> TranslationResult:
        """Translate given source text into target language.

        Raises:
            AuthenticationError: On credential errors.
            QuotaExceededError: When quota is exhausted.
            NetworkError: On connection/timeout failures.
            InvalidRequestError: On invalid input or unsupported languages.
        """
        pass


class CacheRepository(ABC):
    """Abstract interface for translation caching."""

    @abstractmethod
    def get(self, key: str) -> TranslationResult | None:
        """Retrieve cached translation by deterministic key, or None."""
        pass

    @abstractmethod
    def set(self, key: str, result: TranslationResult, ttl_seconds: int | None = None) -> None:
        """Store translation result associated with key."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Purge all entries from the cache."""
        pass


class SettingsRepository(ABC):
    """Abstract interface for persistent configuration settings."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve setting value."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Update setting value."""
        pass

    @abstractmethod
    def save(self) -> None:
        """Persist settings to storage."""
        pass

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Load all settings from storage."""
        pass


class HistoryRepository(ABC):
    """Abstract interface for comic dialogue scan history."""

    @abstractmethod
    def add_item(self, item: HistoryItem) -> None:
        """Add or update a history item."""
        pass

    @abstractmethod
    def get_items(self, filter_type: str = "ALL", query: str = "") -> list[HistoryItem]:
        """Retrieve history items with optional filter and search query."""
        pass

    @abstractmethod
    def toggle_favorite(self, item_id: str) -> bool:
        """Toggle favorite bookmark status, returning new state."""
        pass

    @abstractmethod
    def delete_item(self, item_id: str) -> None:
        """Delete a single history entry."""
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Purge all history entries."""
        pass

    @abstractmethod
    def export_formatted(self, filter_type: str = "ALL") -> str:
        """Export history entries to formatted plain text."""
        pass


class GlossaryRepository(ABC):
    """Abstract interface for comic term dictionary and glossary replacements."""

    @abstractmethod
    def add_entry(self, entry: GlossaryEntry) -> None:
        """Add or update a glossary entry."""
        pass

    @abstractmethod
    def update_entry(self, entry: GlossaryEntry) -> None:
        """Update an existing glossary entry."""
        pass

    @abstractmethod
    def delete_entry(self, entry_id: str) -> None:
        """Delete a glossary entry by id."""
        pass

    @abstractmethod
    def get_entries(
        self, language: str = "ALL", enabled_only: bool = False, query: str = ""
    ) -> list[GlossaryEntry]:
        """Retrieve glossary entries with optional language, status, and search filters."""
        pass

    @abstractmethod
    def toggle_enabled(self, entry_id: str) -> bool:
        """Toggle active state of a glossary entry."""
        pass

    @abstractmethod
    def apply_glossary(self, text: str, language: str = "ALL") -> str:
        """Apply enabled glossary replacements to the given text."""
        pass

    @abstractmethod
    def load_presets(self, overwrite: bool = False) -> int:
        """Load built-in popular manga/manhwa/wuxia presets, returning count added."""
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Remove all glossary entries."""
        pass
