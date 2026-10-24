"""Manga comic speech bubble inpainting overlay window.

Displays translated Indonesian dialogue directly positioned over original
manga speech bubbles with authentic comic-book typography and speech bubble styling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

from scanwitme.domain.models import OCRBlock, Rect

logger = logging.getLogger("scanwitme.presentation.bubble_overlay")

PADDING_X = 6
PADDING_Y = 5


@dataclass
class BubbleItem:
    """Represents a speech bubble patch and its text content."""

    rect: QRect  # Local coordinates relative to capture area
    original_text: str
    translated_text: str
    show_original: bool = False

    @property
    def current_text(self) -> str:
        return self.original_text if self.show_original else self.translated_text


def cluster_ocr_blocks(
    blocks: list[OCRBlock],
    max_v_gap: int = 24,
    max_h_gap: int = 40,
) -> list[list[OCRBlock]]:
    """Group neighboring dialogue lines into unified speech bubble clusters."""
    if not blocks:
        return []

    clusters: list[list[OCRBlock]] = []
    for b in blocks:
        merged = False
        for c in clusters:
            for cb in c:
                v_gap = max(0, b.min_y - cb.max_y, cb.min_y - b.max_y)
                h_gap = max(0, b.min_x - cb.max_x, cb.min_x - b.max_x)
                if v_gap <= max_v_gap and h_gap <= max_h_gap:
                    c.append(b)
                    merged = True
                    break
            if merged:
                break
        if not merged:
            clusters.append([b])
    return clusters


class BubbleOverlayWindow(QWidget):
    """Transparent on-screen overlay rendering direct speech bubble inpainting over comics."""

    closed = Signal()
    bubble_clicked = Signal(int)  # Emits bubble index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._bubbles: list[BubbleItem] = []
        self._capture_rect = Rect(0, 0, 100, 100)

    def display_bubbles(self, capture_rect: Rect, bubbles: list[BubbleItem]) -> None:
        """Position overlay over the captured comic region and render speech bubbles."""
        self._capture_rect = capture_rect
        self._bubbles = bubbles

        self.setGeometry(
            capture_rect.x,
            capture_rect.y,
            max(10, capture_rect.width),
            max(10, capture_rect.height),
        )
        self.show()
        self.update()
        logger.info(
            "Rendering %d comic bubble overlays at (%d, %d)",
            len(bubbles),
            capture_rect.x,
            capture_rect.y,
        )

    def clear_bubbles(self) -> None:
        """Clear all active bubble overlays and hide window."""
        self._bubbles.clear()
        self.hide()
        self.update()

    def _calculate_optimal_font_size(
        self,
        text: str,
        target_rect: QRect,
        min_size: int = 7,
        max_size: int = 14,
    ) -> int:
        """Find the largest comic font size that comfortably fits the dialogue."""
        avail_w = max(10, target_rect.width())
        avail_h = max(10, target_rect.height())

        for size in range(max_size, min_size - 1, -1):
            font = QFont("Comic Sans MS", size, QFont.Weight.Bold)
            fm = QFontMetrics(font)
            bounds = fm.boundingRect(
                0,
                0,
                avail_w,
                avail_h,
                int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                text,
            )
            if bounds.width() <= avail_w and bounds.height() <= avail_h:
                return size

        return min_size

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._bubbles:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for bubble in self._bubbles:
            r = bubble.rect

            # 1. Comic Speech Bubble Inpainting Background
            # Clean opaque manga paper white with rounded pill corners
            bg_color = (
                QColor(254, 243, 199, 250) if bubble.show_original else QColor(255, 255, 255, 252)
            )
            border_color = (
                QColor(217, 119, 6, 220) if bubble.show_original else QColor(15, 23, 42, 220)
            )

            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, 1.5))
            painter.drawRoundedRect(r, 6, 6)

            # 2. Text Bounds with Padding
            inner_rect = r.adjusted(4, 3, -4, -3)

            # 3. Dynamic Font Typography
            text = bubble.current_text
            font_size = self._calculate_optimal_font_size(text, inner_rect)
            comic_font = QFont("Comic Sans MS", font_size, QFont.Weight.Bold)
            painter.setFont(comic_font)

            text_color = (
                QColor(146, 64, 14) if bubble.show_original else QColor(15, 23, 42)
            )  # Ink dark
            painter.setPen(text_color)

            painter.drawText(
                inner_rect,
                int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                text,
            )

            # 4. Tiny Mode Indicator Badge in Bubble Corner
            if bubble.show_original:
                badge_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                painter.setFont(badge_font)
                painter.setPen(QColor(180, 83, 9))
                painter.drawText(r.adjusted(4, 2, -4, -2), int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight), "ASLI")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked inside any bubble to toggle Peek Original
            for idx, bubble in enumerate(self._bubbles):
                if bubble.rect.contains(pos):
                    bubble.show_original = not bubble.show_original
                    self.update()
                    self.bubble_clicked.emit(idx)
                    event.accept()
                    return

            # Clicking outside bubbles closes the overlay
            self.clear_bubbles()
            self.closed.emit()
            event.accept()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            # Right click closes overlay
            self.clear_bubbles()
            self.closed.emit()
            event.accept()
            return

        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.clear_bubbles()
            self.closed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)
