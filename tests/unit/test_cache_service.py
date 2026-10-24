"""Unit tests for SQLiteCacheRepository and CacheService."""

import time

import pytest

from scanwitme.application.cache_service import CacheService
from scanwitme.domain.models import TranslationResult
from scanwitme.infrastructure.cache.sqlite_cache import SQLiteCacheRepository


@pytest.mark.unit
def test_cache_text_normalization() -> None:
    raw = "  안녕하세요 \n\t 세상   !  "
    norm = CacheService.normalize_text(raw)
    assert norm == "안녕하세요 세상 !"


@pytest.mark.unit
def test_cache_service_hit_and_miss() -> None:
    repo = SQLiteCacheRepository(db_path=":memory:")
    service = CacheService(repository=repo)

    text = "만화 번역"
    # Miss
    assert service.get(text, "ko", "id", "cloud_v2") is None

    result = TranslationResult(
        source_text=text,
        translated_text="Terjemahan manga",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
    )
    service.set(text, result)

    # Hit
    cached = service.get("  만화   번역  ", "ko", "id", "cloud_v2")
    assert cached is not None
    assert cached.translated_text == "Terjemahan manga"
    assert cached.cached is True


@pytest.mark.unit
def test_cache_ttl_expiration() -> None:
    repo = SQLiteCacheRepository(db_path=":memory:")
    service = CacheService(repository=repo)

    text = "빠른 만료"
    result = TranslationResult(
        source_text=text,
        translated_text="Kedaluwarsa cepat",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
    )
    # 0.1 second TTL
    service.set(text, result, ttl_seconds=0.1)

    # Immediately available
    cached = service.get(text, "ko", "id", "cloud_v2")
    assert cached is not None

    time.sleep(0.15)

    # Should now be expired and return None
    assert service.get(text, "ko", "id", "cloud_v2") is None


@pytest.mark.unit
def test_cache_clear() -> None:
    repo = SQLiteCacheRepository(db_path=":memory:")
    service = CacheService(repository=repo)

    service.set(
        "테스트",
        TranslationResult(
            source_text="테스트",
            translated_text="Tes",
            source_language="ko",
            target_language="id",
            provider="cloud_v2",
        ),
    )
    assert service.get("테스트", "ko", "id", "cloud_v2") is not None

    service.clear()
    assert service.get("테스트", "ko", "id", "cloud_v2") is None
