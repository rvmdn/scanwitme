"""Cache service providing text normalization and deterministic key generation."""

from __future__ import annotations

import hashlib
import re

from scanwitme.domain.interfaces import CacheRepository
from scanwitme.domain.models import TranslationResult

_WHITESPACE_REGEX = re.compile(r"\s+")


class CacheService:
    """Manages translation caching with normalized hashing."""

    def __init__(
        self, repository: CacheRepository, default_ttl_seconds: int | None = 86400 * 30
    ) -> None:
        self._repo = repository
        self._default_ttl = default_ttl_seconds

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize whitespace and trim surrounding space."""
        if not text:
            return ""
        # Collapse multiple spaces/newlines into a single space and strip
        return _WHITESPACE_REGEX.sub(" ", text).strip()

    @classmethod
    def compute_key(
        cls,
        text: str,
        source_lang: str,
        target_lang: str,
        provider: str,
    ) -> str:
        """Generate deterministic SHA-256 cache key from normalized parameters."""
        normalized = cls.normalize_text(text)
        payload = f"{normalized}|{source_lang.lower().strip()}|{target_lang.lower().strip()}|{provider.lower().strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        provider: str,
    ) -> TranslationResult | None:
        """Look up translation in cache."""
        key = self.compute_key(text, source_lang, target_lang, provider)
        return self._repo.get(key)

    def set(
        self,
        text: str,
        result: TranslationResult,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store translation in cache."""
        key = self.compute_key(
            text,
            result.source_language,
            result.target_language,
            result.provider,
        )
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._repo.set(key, result, ttl_seconds=ttl)

    def clear(self) -> None:
        """Flush cache."""
        self._repo.clear()
