"""Unit tests for TranslationWorkflow."""

from unittest.mock import MagicMock

import pytest

from scanwitme.application.cache_service import CacheService
from scanwitme.application.workflow import TranslationWorkflow
from scanwitme.domain.errors import InvalidRequestError
from scanwitme.domain.models import OCRBlock, TranslationResult
from scanwitme.infrastructure.cache.sqlite_cache import SQLiteCacheRepository


@pytest.mark.unit
def test_workflow_empty_ocr_blocks() -> None:
    mock_provider = MagicMock()
    workflow = TranslationWorkflow(translation_provider=mock_provider)

    with pytest.raises(InvalidRequestError, match="No OCR blocks"):
        workflow.execute([], source_language="ko")


@pytest.mark.unit
def test_workflow_whitespace_only_blocks() -> None:
    mock_provider = MagicMock()
    workflow = TranslationWorkflow(translation_provider=mock_provider)

    blocks = [OCRBlock(text="   \n\t ", box=[[0, 0], [1, 0], [1, 1], [0, 1]], confidence=0.5)]
    with pytest.raises(InvalidRequestError, match="empty whitespace"):
        workflow.execute(blocks, source_language="ko")


@pytest.mark.unit
def test_workflow_execution_and_caching() -> None:
    mock_provider = MagicMock()
    mock_provider.provider_id = "cloud_v2"
    mock_provider.translate.return_value = TranslationResult(
        source_text="안녕하세요 세상",
        translated_text="Halo dunia",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
    )

    repo = SQLiteCacheRepository(db_path=":memory:")
    cache_service = CacheService(repository=repo)
    workflow = TranslationWorkflow(translation_provider=mock_provider, cache_service=cache_service)

    blocks = [
        OCRBlock(
            text="안녕하세요",
            box=[[0, 0], [50, 0], [50, 20], [0, 20]],
            confidence=0.98,
            reading_order=1,
        ),
        OCRBlock(
            text="세상",
            box=[[60, 0], [100, 0], [100, 20], [60, 20]],
            confidence=0.97,
            reading_order=2,
        ),
    ]

    # First call: cache miss, calls provider
    res1 = workflow.execute(blocks, source_language="ko", target_language="id")
    assert res1.translated_text == "Halo dunia"
    assert mock_provider.translate.call_count == 1

    # Second call with same blocks: cache hit, skips provider!
    res2 = workflow.execute(blocks, source_language="ko", target_language="id")
    assert res2.translated_text == "Halo dunia"
    assert res2.cached is True
    assert mock_provider.translate.call_count == 1  # Provider NOT called again!


@pytest.mark.unit
def test_workflow_applies_glossary() -> None:
    mock_provider = MagicMock()
    mock_provider.provider_id = "free_direct"
    mock_provider.translate.return_value = TranslationResult(
        source_text="안녕하세요 선배",
        translated_text="Halo senior",
        source_language="ko",
        target_language="id",
        provider="free_direct",
    )

    mock_glossary = MagicMock()
    mock_glossary.apply_glossary.return_value = "Halo Sunbae"

    workflow = TranslationWorkflow(
        translation_provider=mock_provider,
        glossary_service=mock_glossary,
    )

    blocks = [
        OCRBlock(text="안녕하세요 선배", box=[[0, 0], [10, 0], [10, 10], [0, 10]], confidence=0.9)
    ]
    res = workflow.execute(blocks, source_language="ko", target_language="id")

    assert res.translated_text == "Halo Sunbae"
    mock_glossary.apply_glossary.assert_called_once_with("Halo senior", language="ko")
