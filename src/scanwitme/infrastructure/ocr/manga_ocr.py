"""Optional Manga-OCR engine adapter for Japanese vertical manga dialogues."""

from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image

from scanwitme.domain.errors import OCRError, OCRNoTextFound
from scanwitme.domain.interfaces import OCRProvider
from scanwitme.domain.models import OCRBlock

logger = logging.getLogger("scanwitme.infrastructure.ocr.manga_ocr")


class MangaOCRProvider(OCRProvider):
    """Local Manga-OCR engine by kha-white specifically trained on Japanese manga dialogues."""

    def __init__(self) -> None:
        self._mocr: Any = None

    def is_available(self) -> bool:
        """Check if manga_ocr is installed in the python environment."""
        try:
            import manga_ocr  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_engine(self) -> Any:
        if self._mocr is None:
            try:
                from manga_ocr import MangaOcr

                logger.info("Initializing Manga-OCR model...")
                self._mocr = MangaOcr()
                logger.info("Manga-OCR initialized successfully.")
            except Exception as exc:
                raise OCRError(f"Gagal memuat Manga-OCR: {exc}") from exc
        return self._mocr

    def recognize(
        self,
        image_data: bytes,
        language: str = "ja",
        direction: str = "vertical",
    ) -> list[OCRBlock]:
        if not image_data:
            raise OCRNoTextFound("Image data is empty.")

        if not self.is_available():
            raise OCRError(
                "Manga-OCR belum terpasang. Jalankan 'pip install manga-ocr' "
                "atau gunakan mode PaddleOCR Jepang Vertikal bawaan."
            )

        try:
            pil_image = Image.open(io.BytesIO(image_data))
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
        except Exception as exc:
            raise OCRError(f"Gagal membaca gambar: {exc}") from exc

        engine = self._get_engine()
        try:
            text = engine(pil_image).strip()
        except Exception as exc:
            raise OCRError(f"Manga-OCR inference error: {exc}") from exc

        if not text:
            raise OCRNoTextFound("Tidak ada teks terbaca oleh Manga-OCR.")

        w, h = pil_image.size
        # Full crop box
        box = [[0, 0], [w, 0], [w, h], [0, h]]
        return [OCRBlock(text=text, box=box, confidence=0.98, reading_order=1)]
