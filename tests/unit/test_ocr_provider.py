"""Unit tests for PaddleOCRProvider."""

from unittest.mock import MagicMock

import pytest

from scanwitme.domain.errors import OCRError, OCRNoTextFound
from scanwitme.domain.models import OCRBlock
from scanwitme.infrastructure.ocr.paddle_ocr import PaddleOCRProvider
from tests.fixtures.synthetic_images import create_blank_image


@pytest.mark.unit
def test_ocr_provider_is_available() -> None:
    provider = PaddleOCRProvider()
    assert provider.is_available() is True


@pytest.mark.unit
def test_ocr_provider_empty_data() -> None:
    provider = PaddleOCRProvider()
    with pytest.raises(OCRNoTextFound, match="empty"):
        provider.recognize(b"")


@pytest.mark.unit
def test_ocr_provider_corrupt_data() -> None:
    provider = PaddleOCRProvider()
    with pytest.raises(OCRError, match="Failed to decode"):
        provider.recognize(b"not an image file content")


@pytest.mark.unit
def test_ocr_provider_reading_order_sorting() -> None:
    # 3 blocks: block1 is top-left, block2 is top-right (same line), block3 is bottom line
    block1 = OCRBlock(text="TopLeft", box=[[10, 10], [50, 10], [50, 30], [10, 30]], confidence=0.99)
    block2 = OCRBlock(
        text="TopRight", box=[[120, 12], [180, 12], [180, 32], [120, 32]], confidence=0.98
    )
    block3 = OCRBlock(
        text="BottomLine", box=[[15, 80], [100, 80], [100, 105], [15, 105]], confidence=0.97
    )

    # Scramble input order
    scrambled = [block3, block2, block1]
    sorted_blocks = PaddleOCRProvider._sort_reading_order(scrambled)

    assert len(sorted_blocks) == 3
    assert sorted_blocks[0].text == "TopLeft"
    assert sorted_blocks[0].reading_order == 1
    assert sorted_blocks[1].text == "TopRight"
    assert sorted_blocks[1].reading_order == 2
    assert sorted_blocks[2].text == "BottomLine"
    assert sorted_blocks[2].reading_order == 3


@pytest.mark.unit
def test_ocr_provider_mocked_inference() -> None:
    provider = PaddleOCRProvider()

    # Mock engine
    mock_engine = MagicMock()
    # PaddleOCR format: [ [ [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("안녕하세요", 0.96)] ] ]
    mock_engine.ocr.return_value = [
        [
            [[[10, 20], [90, 20], [90, 45], [10, 45]], ("안녕하세요", 0.96)],
            [[[10, 60], [110, 60], [110, 85], [10, 85]], ("반가워요", 0.94)],
        ]
    ]

    provider._engines["korean"] = mock_engine

    blank_bytes = create_blank_image(width=200, height=120)
    blocks = provider.recognize(blank_bytes, language="ko")

    assert len(blocks) == 2
    assert blocks[0].text == "안녕하세요"
    assert blocks[0].confidence == 0.96
    assert blocks[0].reading_order == 1
    assert blocks[1].text == "반가워요"
    assert blocks[1].confidence == 0.94
    assert blocks[1].reading_order == 2


@pytest.mark.unit
def test_ocr_provider_no_text_found() -> None:
    provider = PaddleOCRProvider()
    mock_engine = MagicMock()
    mock_engine.ocr.return_value = [[]]
    provider._engines["korean"] = mock_engine

    blank_bytes = create_blank_image(width=100, height=100)
    with pytest.raises(OCRNoTextFound):
        provider.recognize(blank_bytes, language="ko")
