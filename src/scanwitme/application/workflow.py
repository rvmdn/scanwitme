"""Translation workflow coordinating OCR text assembly, cache lookup, and provider dispatch."""

from __future__ import annotations

import logging
import time

from scanwitme.application.cache_service import CacheService
from scanwitme.domain.errors import InvalidRequestError
from scanwitme.domain.interfaces import TranslationProvider
from scanwitme.domain.models import OCRBlock, TranslationResult

logger = logging.getLogger("scanwitme.application.workflow")


class TranslationWorkflow:
    """Orchestrates text assembly, cache queries, and translation provider calls."""

    def __init__(
        self,
        translation_provider: TranslationProvider,
        cache_service: CacheService | None = None,
    ) -> None:
        self._provider = translation_provider
        self._cache = cache_service

    def set_provider(self, provider: TranslationProvider) -> None:
        self._provider = provider

    def execute(
        self,
        ocr_blocks: list[OCRBlock],
        source_language: str,
        target_language: str = "id",
    ) -> TranslationResult:
        """Combine dialogue blocks, check cache, invoke translation, and update cache."""
        if not ocr_blocks:
            raise InvalidRequestError("No OCR blocks provided for translation.")

        # Reconstruct natural dialogue string from sorted blocks
        # Join with space while respecting reading order
        combined_text = " ".join(b.text.strip() for b in ocr_blocks if b.text.strip())
        if not combined_text:
            raise InvalidRequestError("Recognized OCR blocks contain only empty whitespace.")

        # Check translation cache first
        if self._cache:
            cached_result = self._cache.get(
                text=combined_text,
                source_lang=source_language,
                target_lang=target_language,
                provider=self._provider.provider_id,
            )
            if cached_result:
                logger.info("Translation cache hit for text of length %d", len(combined_text))
                return cached_result

        # Perform translation via provider
        start_time = time.perf_counter()
        result = self._provider.translate(
            text=combined_text,
            source_language=source_language,
            target_language=target_language,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        result.latency_ms = latency_ms

        # Store in cache
        if self._cache:
            self._cache.set(text=combined_text, result=result)

        return result
