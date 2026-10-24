"""Local OCR provider using PaddleOCR with lazy model initialization and deterministic ordering."""

from __future__ import annotations

import io
import logging
import os
from typing import Any

import numpy as np
from PIL import Image

from scanwitme.domain.errors import OCRError, OCRModelError, OCRNoTextFound
from scanwitme.domain.interfaces import OCRProvider
from scanwitme.domain.models import OCRBlock

# Prevent Windows oneDNN NotImplementedError in Paddle static runner
os.environ["FLAGS_use_mkldnn"] = "0"
try:
    import paddle.inference as p_inf

    if not hasattr(p_inf, "_scanwitme_patched"):
        _orig_create_predictor = p_inf.create_predictor

        def _patched_create_predictor(config):
            if hasattr(config, "disable_onednn"):
                config.disable_onednn()
            if hasattr(config, "disable_mkldnn"):
                config.disable_mkldnn()
            return _orig_create_predictor(config)

        p_inf.create_predictor = _patched_create_predictor
        p_inf._scanwitme_patched = True
except Exception:
    pass

logger = logging.getLogger("scanwitme.ocr")

LANGUAGE_MAPPING = {
    "auto": "auto",
    "ko": "korean",
    "korean": "korean",
    "zh": "ch",
    "zh-CN": "ch",
    "zh-TW": "chinese_cht",
    "chinese": "ch",
    "ja": "japan",
    "japan": "japan",
    "en": "en",
}


def detect_script(text: str) -> str:
    """Heuristically identify Asian script or Latin from unicode character ranges."""
    has_hangul = any("\uac00" <= ch <= "\ud7af" or "\u1100" <= ch <= "\u11ff" for ch in text)
    if has_hangul:
        return "ko"
    has_kana = any("\u3040" <= ch <= "\u309f" or "\u30a0" <= ch <= "\u30ff" for ch in text)
    if has_kana:
        return "ja"
    has_hanzi = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    if has_hanzi:
        return "zh"
    return "en"


class PaddleOCRProvider(OCRProvider):
    """Local OCR engine wrapping PaddleOCR with multi-language caching and spatial sorting."""

    def __init__(self, use_textline_orientation: bool = False) -> None:
        self._use_textline_orientation = use_textline_orientation
        self._engines: dict[str, Any] = {}

    def _get_engine(self, ocr_lang: str) -> Any:
        """Lazily initialize and cache PaddleOCR engine for the requested language."""
        if ocr_lang not in self._engines:
            try:
                from paddleocr import PaddleOCR

                logger.info("Initializing PaddleOCR engine for language '%s'...", ocr_lang)
                engine = PaddleOCR(
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=self._use_textline_orientation,
                    lang=ocr_lang,
                )
                self._engines[ocr_lang] = engine
                logger.info("PaddleOCR engine for language '%s' ready.", ocr_lang)
            except Exception as exc:
                logger.exception("Failed to initialize PaddleOCR for language '%s'", ocr_lang)
                raise OCRModelError(f"Failed to load OCR model for '{ocr_lang}': {exc}") from exc
        return self._engines[ocr_lang]

    def preload(self, language: str = "ch") -> None:
        """Preload OCR models in background to eliminate first-scan cold-start latency."""
        try:
            self._get_engine(language)
        except Exception as exc:
            logger.warning("Background OCR preloading failed: %s", exc)

    def is_available(self) -> bool:
        """Check if PaddleOCR can be imported successfully."""
        try:
            import paddleocr  # noqa: F401

            return True
        except ImportError:
            return False

    def _parse_results(self, results: Any) -> list[OCRBlock]:
        """Normalize both PaddleOCR 2.x and 3.x / PaddleX output structures into OCRBlocks."""
        if not results:
            return []

        raw_blocks: list[OCRBlock] = []

        # PaddleOCR 3.x / PaddleX format: [dict with 'rec_texts', 'rec_scores', 'rec_polys']
        if isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
            res_dict = results[0]
            rec_texts = res_dict.get("rec_texts", [])
            rec_scores = res_dict.get("rec_scores", [])
            rec_polys = res_dict.get("rec_polys", [])
            if not rec_polys and "rec_boxes" in res_dict:
                # Fallback to rec_boxes if polys not present: [x1, y1, x2, y2]
                for text, score, box_arr in zip(
                    rec_texts, rec_scores, res_dict["rec_boxes"], strict=False
                ):
                    text_clean = str(text).strip()
                    if not text_clean:
                        continue
                    x1, y1, x2, y2 = [int(round(v)) for v in box_arr]
                    box = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    raw_blocks.append(OCRBlock(text=text_clean, box=box, confidence=float(score)))
                return raw_blocks

            for text, score, poly in zip(rec_texts, rec_scores, rec_polys, strict=False):
                text_clean = str(text).strip()
                if not text_clean:
                    continue
                if hasattr(poly, "tolist"):
                    box_pts = poly.tolist()
                else:
                    box_pts = list(poly)
                box = [[int(round(pt[0])), int(round(pt[1]))] for pt in box_pts]
                raw_blocks.append(OCRBlock(text=text_clean, box=box, confidence=float(score)))

        # PaddleOCR 2.x format: [[ [box_points, (text, confidence)], ... ]]
        elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
            for line in results[0]:
                if len(line) >= 2 and isinstance(line[1], (list, tuple)):
                    raw_box = line[0]
                    text, conf = line[1][0], float(line[1][1])
                    text_clean = str(text).strip()
                    if not text_clean:
                        continue
                    box = [[int(round(pt[0])), int(round(pt[1]))] for pt in raw_box]
                    raw_blocks.append(OCRBlock(text=text_clean, box=box, confidence=conf))

        return raw_blocks

    def recognize(self, image_data: bytes, language: str = "auto") -> list[OCRBlock]:
        """Perform text detection and recognition on image bytes."""
        if not image_data:
            raise OCRNoTextFound("Image data is empty.")

        try:
            pil_image = Image.open(io.BytesIO(image_data))
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            img_np = np.array(pil_image)
        except Exception as exc:
            raise OCRError(f"Failed to decode image for OCR: {exc}") from exc

        if img_np.shape[0] < 4 or img_np.shape[1] < 4:
            raise OCRNoTextFound("Image dimensions too small for text recognition.")

        raw_blocks: list[OCRBlock] = []

        if language == "auto":
            # Auto-detect language:
            # First attempt with "ch" model (PP-OCRv6 handles Chinese, Japanese, and English)
            try:
                engine_zh = self._get_engine("ch")
                res_zh = engine_zh.ocr(img_np)
                blocks_zh = self._parse_results(res_zh)
            except Exception as exc:
                logger.warning("Auto OCR pass with 'ch' model failed: %s", exc)
                blocks_zh = []

            # Check recognized text
            combined_text = "".join(b.text for b in blocks_zh)
            avg_score = sum(b.confidence for b in blocks_zh) / len(blocks_zh) if blocks_zh else 0.0

            # If Chinese/Japanese characters detected with solid confidence, use it
            if (
                blocks_zh
                and avg_score >= 0.55
                and not any("\uac00" <= ch <= "\ud7af" for ch in combined_text)
            ):
                raw_blocks = blocks_zh
            else:
                # If low confidence or Hangul detected or no text, try Korean model
                try:
                    engine_ko = self._get_engine("korean")
                    res_ko = engine_ko.ocr(img_np)
                    blocks_ko = self._parse_results(res_ko)
                    avg_ko = (
                        sum(b.confidence for b in blocks_ko) / len(blocks_ko) if blocks_ko else 0.0
                    )
                    if blocks_ko and (avg_ko >= avg_score or not blocks_zh):
                        raw_blocks = blocks_ko
                    else:
                        raw_blocks = blocks_zh
                except Exception as exc:
                    logger.warning("Auto OCR pass with 'korean' model failed: %s", exc)
                    raw_blocks = blocks_zh
        else:
            ocr_lang = LANGUAGE_MAPPING.get(language, "korean")
            engine = self._get_engine(ocr_lang)
            try:
                results = engine.ocr(img_np)
                raw_blocks = self._parse_results(results)
            except Exception as exc:
                logger.exception("OCR inference error")
                raise OCRError(f"OCR inference failed: {exc}") from exc

        if not raw_blocks:
            raise OCRNoTextFound("No readable text recognized in image.")

        # Sort blocks into deterministic reading order
        sorted_blocks = self._sort_reading_order(raw_blocks)
        return sorted_blocks

    @staticmethod
    def _sort_reading_order(blocks: list[OCRBlock]) -> list[OCRBlock]:
        """Sort detected dialogue blocks top-to-bottom, left-to-right with line grouping."""
        if not blocks:
            return []

        # Calculate average block height to determine line-grouping tolerance
        avg_height = sum(b.max_y - b.min_y for b in blocks) / len(blocks)
        y_tolerance = max(8.0, avg_height * 0.5)

        # Sort primarily by min_y
        blocks_by_y = sorted(blocks, key=lambda b: (b.min_y, b.min_x))

        lines: list[list[OCRBlock]] = []
        for block in blocks_by_y:
            placed = False
            for line in lines:
                # Check if block vertically overlaps within tolerance with this line
                line_y = sum(b.min_y for b in line) / len(line)
                if abs(block.min_y - line_y) <= y_tolerance:
                    line.append(block)
                    placed = True
                    break
            if not placed:
                lines.append([block])

        # Sort each line left-to-right (or right-to-left if needed; manhwa is LTR)
        ordered: list[OCRBlock] = []
        order_index = 1
        for line in lines:
            line_sorted = sorted(line, key=lambda b: b.min_x)
            for b in line_sorted:
                b.reading_order = order_index
                ordered.append(b)
                order_index += 1

        return ordered
