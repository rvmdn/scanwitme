"""Synthetic test image generators for Korean and Chinese text."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def get_system_font(
    lang: str = "ko", size: int = 24
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Find a system font on Windows capable of rendering Korean/Chinese characters."""
    font_paths = {
        "ko": [
            r"C:\Windows\Fonts\malgun.ttf",  # Malgun Gothic
            r"C:\Windows\Fonts\gulim.ttc",  # Gulim
            r"C:\Windows\Fonts\batang.ttc",  # Batang
        ],
        "zh": [
            r"C:\Windows\Fonts\msyh.ttc",  # Microsoft YaHei
            r"C:\Windows\Fonts\simsun.ttc",  # SimSun
        ],
    }

    candidates = font_paths.get(lang, font_paths["ko"])
    for path_str in candidates:
        path = Path(path_str)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue

    return ImageFont.load_default()


def create_synthetic_image(
    text_lines: list[str],
    lang: str = "ko",
    width: int = 320,
    height: int = 160,
    bg_color: tuple[int, int, int] = (255, 255, 255),
    text_color: tuple[int, int, int] = (20, 20, 20),
) -> bytes:
    """Generate PNG bytes containing rendered dialogue lines on clean background."""
    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)
    font = get_system_font(lang=lang, size=24)

    y_offset = 20
    for line in text_lines:
        draw.text((20, y_offset), line, fill=text_color, font=font)
        y_offset += 36

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_blank_image(width: int = 100, height: int = 100) -> bytes:
    """Generate blank white PNG bytes."""
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
