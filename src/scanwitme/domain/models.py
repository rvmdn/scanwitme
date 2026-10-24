"""Domain models for ScanWitMe."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ScanState(StrEnum):
    """Lifecycle states for a scan operation."""

    IDLE = "idle"
    CAPTURING = "capturing"
    RECOGNIZING = "recognizing"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Rect:
    """Screen coordinate rectangle (x, y, width, height)."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Rectangle dimensions must be positive: width={self.width}, height={self.height}"
            )

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass
class CaptureResult:
    """Result of screen region capture."""

    image_bytes: bytes
    bounds: Rect
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    device_pixel_ratio: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRBlock:
    """Single recognized text block with spatial coordinates."""

    text: str
    box: list[list[int]]  # 4 corner points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    confidence: float
    reading_order: int = 0

    @property
    def min_y(self) -> int:
        return min(point[1] for point in self.box)

    @property
    def min_x(self) -> int:
        return min(point[0] for point in self.box)

    @property
    def max_y(self) -> int:
        return max(point[1] for point in self.box)

    @property
    def max_x(self) -> int:
        return max(point[0] for point in self.box)


@dataclass
class TranslationResult:
    """Result of text translation."""

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    cached: bool = False
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ScanSession:
    """Tracks a single scan session's lifecycle and artifacts."""

    session_id: str
    status: ScanState = ScanState.IDLE
    capture: CaptureResult | None = None
    ocr_blocks: list[OCRBlock] = field(default_factory=list)
    translation: TranslationResult | None = None
    error_message: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def combined_source_text(self) -> str:
        """Concatenates all OCR blocks according to reading order."""
        return " ".join(block.text.strip() for block in self.ocr_blocks if block.text.strip())
