"""Unit tests for domain models."""

import pytest

from scanwitme.domain.models import (
    OCRBlock,
    Rect,
    ScanSession,
    ScanState,
    TranslationResult,
)


@pytest.mark.unit
def test_rect_valid_and_properties() -> None:
    rect = Rect(x=100, y=200, width=300, height=150)
    assert rect.x == 100
    assert rect.y == 200
    assert rect.width == 300
    assert rect.height == 150
    assert rect.right == 400
    assert rect.bottom == 350


@pytest.mark.unit
def test_rect_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="Rectangle dimensions must be positive"):
        Rect(x=0, y=0, width=0, height=100)

    with pytest.raises(ValueError, match="Rectangle dimensions must be positive"):
        Rect(x=0, y=0, width=100, height=-5)


@pytest.mark.unit
def test_ocr_block_bounding_box_properties() -> None:
    box = [[10, 20], [100, 20], [100, 50], [10, 50]]
    block = OCRBlock(text="안녕하세요", box=box, confidence=0.98, reading_order=1)
    assert block.text == "안녕하세요"
    assert block.min_x == 10
    assert block.max_x == 100
    assert block.min_y == 20
    assert block.max_y == 50
    assert block.reading_order == 1


@pytest.mark.unit
def test_scan_session_lifecycle() -> None:
    session = ScanSession(session_id="test-session-1")
    assert session.status == ScanState.IDLE
    assert session.combined_source_text == ""

    # Add blocks
    block1 = OCRBlock(
        text="Hello", box=[[0, 0], [50, 0], [50, 20], [0, 20]], confidence=0.95, reading_order=1
    )
    block2 = OCRBlock(
        text="World", box=[[0, 30], [60, 30], [60, 50], [0, 50]], confidence=0.96, reading_order=2
    )
    session.ocr_blocks = [block1, block2]

    assert session.combined_source_text == "Hello World"


@pytest.mark.unit
def test_translation_result() -> None:
    result = TranslationResult(
        source_text="안녕하세요",
        translated_text="Halo",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
        latency_ms=120.5,
    )
    assert result.source_text == "안녕하세요"
    assert result.translated_text == "Halo"
    assert result.target_language == "id"
    assert result.latency_ms == 120.5
    assert not result.cached
