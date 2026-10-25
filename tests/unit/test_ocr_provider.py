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


@pytest.mark.unit
def test_detect_text_layout_direction() -> None:
    from scanwitme.infrastructure.ocr.paddle_ocr import detect_text_layout_direction

    # Empty
    assert detect_text_layout_direction([]) == "horizontal"

    # Tall vertical boxes (aspect ratio height > 1.2 * width)
    v1 = OCRBlock(text="何", box=[[100, 10], [125, 10], [125, 90], [100, 90]], confidence=0.99)
    v2 = OCRBlock(text="だ", box=[[60, 10], [85, 10], [85, 90], [60, 90]], confidence=0.99)
    assert detect_text_layout_direction([v1, v2]) == "vertical"

    # Horizontal boxes
    h1 = OCRBlock(text="Hello", box=[[10, 10], [100, 10], [100, 30], [10, 30]], confidence=0.99)
    h2 = OCRBlock(text="World", box=[[10, 40], [100, 40], [100, 60], [10, 60]], confidence=0.99)
    assert detect_text_layout_direction([h1, h2]) == "horizontal"


@pytest.mark.unit
def test_sort_vertical_reading_order_japanese_manga() -> None:
    from scanwitme.infrastructure.ocr.paddle_ocr import sort_vertical_reading_order

    # Right column (x: 100-120): Top "A", Bottom "B"
    right_top = OCRBlock(
        text="RightTop", box=[[100, 10], [120, 10], [120, 40], [100, 40]], confidence=0.99
    )
    right_bottom = OCRBlock(
        text="RightBottom", box=[[100, 50], [120, 50], [120, 80], [100, 80]], confidence=0.99
    )

    # Left column (x: 50-70): Top "C", Bottom "D"
    left_top = OCRBlock(
        text="LeftTop", box=[[50, 10], [70, 10], [70, 40], [50, 40]], confidence=0.99
    )
    left_bottom = OCRBlock(
        text="LeftBottom", box=[[50, 50], [70, 50], [70, 80], [50, 80]], confidence=0.99
    )

    # Scramble the input blocks
    scrambled = [left_bottom, right_top, left_top, right_bottom]
    ordered = sort_vertical_reading_order(scrambled)

    # In Japanese manga: Right column first (top to bottom), then Left column (top to bottom)
    assert [b.text for b in ordered] == ["RightTop", "RightBottom", "LeftTop", "LeftBottom"]
    assert [b.reading_order for b in ordered] == [1, 2, 3, 4]


@pytest.mark.unit
def test_manga_ocr_provider_lifecycle() -> None:
    from scanwitme.infrastructure.ocr.manga_ocr import MangaOCRProvider

    provider = MangaOCRProvider()
    assert isinstance(provider.is_available(), bool)

    # Empty data error
    with pytest.raises(OCRNoTextFound):
        provider.recognize(b"")

    if not provider.is_available():
        # Should raise friendly error explaining missing dependency
        blank_bytes = create_blank_image(width=50, height=50)
        with pytest.raises(OCRError, match="Manga-OCR belum terpasang"):
            provider.recognize(blank_bytes)
