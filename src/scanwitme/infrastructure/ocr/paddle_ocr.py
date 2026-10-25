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

from scanwitme.domain.metadata import get_language_to_ocr_mapping

logger = logging.getLogger("scanwitme.ocr")

LANGUAGE_MAPPING: dict[str, str] = get_language_to_ocr_mapping()
LANGUAGE_MAPPING.update(
    {
        "auto": "auto",
        "zh": "ch",
        "zh-TW": "chinese_cht",
    }
)


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


def detect_text_layout_direction(blocks: list[OCRBlock]) -> str:
    """Smart-detect whether dialogue blocks are arranged vertically (tategaki) or horizontally."""
    if not blocks:
        return "horizontal"

    # 1. Check aspect ratio of detected blocks (tall boxes height >= 1.2 * width)
    vertical_box_count = 0
    for b in blocks:
        h = b.max_y - b.min_y
        w = b.max_x - b.min_x
        if h >= 1.2 * w:
            vertical_box_count += 1

    if (vertical_box_count / len(blocks)) >= 0.35:
        return "vertical"

    # 2. Check vertical column grouping vs horizontal row grouping
    vertical_pairs = 0
    horizontal_pairs = 0
    for i in range(len(blocks)):
        b1 = blocks[i]
        c1_x = (b1.min_x + b1.max_x) / 2
        c1_y = (b1.min_y + b1.max_y) / 2
        for j in range(i + 1, len(blocks)):
            b2 = blocks[j]
            c2_x = (b2.min_x + b2.max_x) / 2
            c2_y = (b2.min_y + b2.max_y) / 2
            dx = abs(c1_x - c2_x)
            dy = abs(c1_y - c2_y)
            if dx <= 25 and dy >= 15:
                vertical_pairs += 1
            elif dy <= 18 and dx >= 15:
                horizontal_pairs += 1

    if vertical_pairs > horizontal_pairs and vertical_pairs >= 2:
        return "vertical"

    return "horizontal"


def sort_vertical_reading_order(blocks: list[OCRBlock]) -> list[OCRBlock]:
    """Sort vertical manga dialogue: columns Right-to-Left, lines Top-to-Bottom."""
    if not blocks:
        return []

    avg_width = sum(b.max_x - b.min_x for b in blocks) / len(blocks)
    x_tolerance = max(12.0, avg_width * 0.6)

    # Sort primarily from Right to Left (highest max_x first)
    blocks_by_x = sorted(blocks, key=lambda b: (-b.max_x, b.min_y))

    columns: list[list[OCRBlock]] = []
    for block in blocks_by_x:
        placed = False
        block_cx = (block.min_x + block.max_x) / 2
        for col in columns:
            col_cx = sum((b.min_x + b.max_x) / 2 for b in col) / len(col)
            if abs(block_cx - col_cx) <= x_tolerance:
                col.append(block)
                placed = True
                break
        if not placed:
            columns.append([block])

    # Ensure columns are sorted from Right to Left (highest avg X first)
    columns.sort(key=lambda col: -sum((b.min_x + b.max_x) / 2 for b in col) / len(col))

    ordered: list[OCRBlock] = []
    order_index = 1
    for col in columns:
        col_sorted = sorted(col, key=lambda b: b.min_y)
        for b in col_sorted:
            b.reading_order = order_index
            ordered.append(b)
            order_index += 1

    return ordered


def sort_horizontal_reading_order(blocks: list[OCRBlock]) -> list[OCRBlock]:
    """Sort standard horizontal dialogue: lines Top-to-Bottom, words Left-to-Right."""
    if not blocks:
        return []

    avg_height = sum(b.max_y - b.min_y for b in blocks) / len(blocks)
    y_tolerance = max(8.0, avg_height * 0.5)

    blocks_by_y = sorted(blocks, key=lambda b: (b.min_y, b.min_x))

    lines: list[list[OCRBlock]] = []
    for block in blocks_by_y:
        placed = False
        for line in lines:
            line_y = sum(b.min_y for b in line) / len(line)
            if abs(block.min_y - line_y) <= y_tolerance:
                line.append(block)
                placed = True
                break
        if not placed:
            lines.append([block])

    ordered: list[OCRBlock] = []
    order_index = 1
    for line in lines:
        line_sorted = sorted(line, key=lambda b: b.min_x)
        for b in line_sorted:
            b.reading_order = order_index
            ordered.append(b)
            order_index += 1

    return ordered


class PaddleOCRProvider(OCRProvider):
    """Local OCR engine wrapping PaddleOCR with multi-language caching and spatial sorting."""

    def __init__(self, use_textline_orientation: bool = True) -> None:
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

    def recognize(
        self,
        image_data: bytes,
        language: str = "auto",
        direction: str = "auto",
    ) -> list[OCRBlock]:
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

        # If explicitly Japanese:
        if language in ("ja", "japan"):
            try:
                engine_ja = self._get_engine("japan")
                res_ja = engine_ja.ocr(img_np)
                raw_blocks = self._parse_results(res_ja)
            except Exception as exc:
                logger.warning("Japanese OCR pass failed: %s", exc)

        elif language == "auto":
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

            # If kana is present or vertical text layout detected with Asian characters,
            # verify or refine with dedicated Japan engine
            has_kana = any(
                "\u3040" <= ch <= "\u309f" or "\u30a0" <= ch <= "\u30ff" for ch in combined_text
            )
            if has_kana or (direction == "vertical" and blocks_zh):
                try:
                    engine_ja = self._get_engine("japan")
                    res_ja = engine_ja.ocr(img_np)
                    blocks_ja = self._parse_results(res_ja)
                    if blocks_ja:
                        raw_blocks = blocks_ja
                    else:
                        raw_blocks = blocks_zh
                except Exception:
                    raw_blocks = blocks_zh
            elif (
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

        # Sort blocks into deterministic reading order (supports vertical manga and horizontal)
        sorted_blocks = self._sort_reading_order(raw_blocks, direction=direction)
        return sorted_blocks

    @classmethod
    def _sort_reading_order(
        cls,
        blocks: list[OCRBlock],
        direction: str = "auto",
    ) -> list[OCRBlock]:
        """Sort detected dialogue blocks using smart layout or explicit direction."""
        if not blocks:
            return []

        if direction == "vertical":
            logger.info("Applying Japanese vertical reading order (Right-to-Left, Top-to-Bottom).")
            return sort_vertical_reading_order(blocks)
        elif direction == "horizontal":
            return sort_horizontal_reading_order(blocks)
        else:  # "auto"
            detected = detect_text_layout_direction(blocks)
            if detected == "vertical":
                logger.info(
                    "Smart-detected vertical dialogue layout. Applying RTL/TTB reading order."
                )
                return sort_vertical_reading_order(blocks)
            else:
                return sort_horizontal_reading_order(blocks)
