"""Manga comic speech bubble inpainting overlay window.

Displays translated Indonesian dialogue directly positioned over original
manga speech bubbles with authentic comic-book typography and speech bubble styling.
"""

from __future__ import annotations

import logging
import urllib.parse
import webbrowser
from dataclasses import dataclass

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
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
    """Group neighboring dialogue lines into unified speech bubble clusters using connected components."""
    if not blocks:
        return []

    n = len(blocks)
    parent = list(range(n))

    def find(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n):
        b1 = blocks[i]
        for j in range(i + 1, n):
            b2 = blocks[j]
            v_gap = max(0, b1.min_y - b2.max_y, b2.min_y - b1.max_y)
            h_gap = max(0, b1.min_x - b2.max_x, b2.min_x - b1.max_x)
            if v_gap <= max_v_gap and h_gap <= max_h_gap:
                union(i, j)

    groups: dict[int, list[OCRBlock]] = {}
    for idx, b in enumerate(blocks):
        root = find(idx)
        groups.setdefault(root, []).append(b)

    return list(groups.values())


class BubbleOverlayWindow(QWidget):
    """Transparent on-screen overlay rendering direct speech bubble inpainting over comics."""

    closed = Signal()
    bubble_clicked = Signal(int)  # Emits bubble index
    bubble_copied = Signal(str)  # Emits copied text
    bubble_searched = Signal(str)  # Emits searched query

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
        self._selected_bubble_index: int = -1
        self._copied_feedback: bool = False

        self._action_toolbar_rect: QRect = QRect()
        self._action_copy_rect: QRect = QRect()
        self._action_search_rect: QRect = QRect()
        self._action_close_rect: QRect = QRect()

    def display_bubbles(self, capture_rect: Rect, bubbles: list[BubbleItem]) -> None:
        """Position overlay over the captured comic region and render speech bubbles."""
        self._capture_rect = capture_rect
        self._bubbles = bubbles
        self._selected_bubble_index = -1
        self._copied_feedback = False

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
        self._selected_bubble_index = -1
        self._copied_feedback = False
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

            # 2. Text Bounds with Adaptive Padding
            pad_h = min(4, max(0, r.width() // 4))
            pad_v = min(3, max(0, r.height() // 4))
            inner_rect = r.adjusted(pad_h, pad_v, -pad_h, -pad_v)

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
                painter.drawText(
                    r.adjusted(4, 2, -4, -2),
                    int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight),
                    "ASLI",
                )

        # 5. Draw Interactive Action Toolbar if a bubble is selected
        if 0 <= self._selected_bubble_index < len(self._bubbles):
            self._draw_action_toolbar(painter, self._bubbles[self._selected_bubble_index])

    def _update_toolbar_rects(self, bubble: BubbleItem) -> None:
        """Calculate layout coordinates for floating quick action toolbar."""
        toolbar_w = 200
        toolbar_h = 32
        r = bubble.rect

        if r.top() >= toolbar_h + 8:
            tb_y = r.top() - toolbar_h - 4
        else:
            tb_y = min(self.height() - toolbar_h - 2, r.bottom() + 4)

        tb_x = max(4, min(self.width() - toolbar_w - 4, r.center().x() - toolbar_w // 2))

        self._action_toolbar_rect = QRect(tb_x, tb_y, toolbar_w, toolbar_h)
        self._action_copy_rect = QRect(tb_x + 4, tb_y + 3, 76, toolbar_h - 6)
        self._action_search_rect = QRect(tb_x + 84, tb_y + 3, 76, toolbar_h - 6)
        self._action_close_rect = QRect(tb_x + 164, tb_y + 3, 32, toolbar_h - 6)

    def _draw_action_toolbar(self, painter: QPainter, bubble: BubbleItem) -> None:
        """Render floating quick action toolbar directly anchored to the selected bubble."""
        self._update_toolbar_rects(bubble)
        tb_x = self._action_toolbar_rect.x()
        tb_y = self._action_toolbar_rect.y()
        toolbar_h = self._action_toolbar_rect.height()

        # Toolbar background & border
        painter.setBrush(QColor(15, 23, 42, 245))
        painter.setPen(QPen(QColor(99, 102, 241, 200), 1.5))
        painter.drawRoundedRect(self._action_toolbar_rect, 8, 8)

        # Dividers
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawLine(tb_x + 82, tb_y + 6, tb_x + 82, tb_y + toolbar_h - 6)
        painter.drawLine(tb_x + 162, tb_y + 6, tb_x + 162, tb_y + toolbar_h - 6)

        # Typography
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)

        copy_label = "✓ Disalin!" if self._copied_feedback else "📋 Salin"
        copy_color = QColor(16, 185, 129) if self._copied_feedback else QColor(248, 250, 252)
        painter.setPen(copy_color)
        painter.drawText(self._action_copy_rect, int(Qt.AlignmentFlag.AlignCenter), copy_label)

        painter.setPen(QColor(248, 250, 252))
        painter.drawText(self._action_search_rect, int(Qt.AlignmentFlag.AlignCenter), "🔍 Cari")

        painter.setPen(QColor(148, 163, 184))
        painter.drawText(self._action_close_rect, int(Qt.AlignmentFlag.AlignCenter), "✖")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()

        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Check Action Toolbar buttons if toolbar is active
            if 0 <= self._selected_bubble_index < len(self._bubbles):
                active_bubble = self._bubbles[self._selected_bubble_index]

                if self._action_copy_rect.contains(pos):
                    clipboard = QGuiApplication.clipboard()
                    if clipboard:
                        clipboard.setText(active_bubble.current_text)
                    self._copied_feedback = True
                    self.update()
                    self.bubble_copied.emit(active_bubble.current_text)
                    event.accept()
                    return

                if self._action_search_rect.contains(pos):
                    query = urllib.parse.quote(active_bubble.current_text)
                    webbrowser.open(f"https://www.google.com/search?q={query}")
                    self.bubble_searched.emit(active_bubble.current_text)
                    event.accept()
                    return

                if self._action_close_rect.contains(pos):
                    self._selected_bubble_index = -1
                    self._copied_feedback = False
                    self._action_toolbar_rect = QRect()
                    self._action_copy_rect = QRect()
                    self._action_search_rect = QRect()
                    self._action_close_rect = QRect()
                    self.update()
                    event.accept()
                    return

            # 2. Check if clicked inside any bubble
            for idx, bubble in enumerate(self._bubbles):
                if bubble.rect.contains(pos):
                    bubble.show_original = not bubble.show_original
                    self._selected_bubble_index = idx
                    self._copied_feedback = False
                    self._update_toolbar_rects(bubble)
                    self.update()
                    self.bubble_clicked.emit(idx)
                    event.accept()
                    return

            # 3. Clicking outside bubbles closes the overlay
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
