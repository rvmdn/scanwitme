"""Fullscreen transparent region selection overlay with rubber-band dragging."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from scanwitme.domain.models import Rect

logger = logging.getLogger("scanwitme.ui.region_selector")


class RegionSelector(QWidget):
    """Transparent fullscreen widget allowing rectangular screen region selection."""

    region_selected = Signal(object)  # Emits Rect
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos: QPoint | None = None
        self._current_pos: QPoint | None = None
        self._is_selecting = False

    def start_selection(self) -> None:
        """Cover the entire virtual desktop and show."""
        # Calculate bounding box of all attached screens
        screens = QGuiApplication.screens()
        if not screens:
            return

        combined_rect = screens[0].geometry()
        for screen in screens[1:]:
            combined_rect = combined_rect.united(screen.geometry())

        self.setGeometry(combined_rect)
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False
        self.show()
        self.raise_()
        self.activateWindow()

    def _get_normalized_qrect(self) -> QRect | None:
        if not self._start_pos or not self._current_pos:
            return None
        x = min(self._start_pos.x(), self._current_pos.x())
        y = min(self._start_pos.y(), self._current_pos.y())
        w = abs(self._start_pos.x() - self._current_pos.x())
        h = abs(self._start_pos.y() - self._current_pos.y())
        return QRect(x, y, w, h)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position().toPoint()
            self._start_pos = pt
            self._current_pos = pt
            self._is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self._cancel()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_selecting:
            self._current_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._current_pos = event.position().toPoint()
            qrect = self._get_normalized_qrect()

            # Ensure minimum viable selection size (at least 8x8 px)
            if qrect and qrect.width() >= 8 and qrect.height() >= 8:
                # Map widget coordinates to global screen coordinates
                global_top_left = self.mapToGlobal(qrect.topLeft())
                selected_rect = Rect(
                    x=global_top_left.x(),
                    y=global_top_left.y(),
                    width=qrect.width(),
                    height=qrect.height(),
                )
                self.hide()
                # Ensure the window is fully unmapped by Windows compositor before capture
                QApplication.processEvents()
                self.region_selected.emit(selected_rect)
            else:
                self._cancel()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)

    def _cancel(self) -> None:
        self._is_selecting = False
        self.hide()
        QApplication.processEvents()
        self.cancelled.emit()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw darkened background over whole desktop
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        qrect = self._get_normalized_qrect()
        if qrect and qrect.width() > 0 and qrect.height() > 0:
            # Cut out selection rectangle so screen shines through clearly
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(qrect, Qt.GlobalColor.transparent)

            # Draw crisp accent border around selected region
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            border_pen = QPen(QColor(66, 133, 244), 2)  # Google blue accent
            painter.setPen(border_pen)
            painter.drawRect(qrect)

            # Draw size & hint badge
            badge_text = f"{qrect.width()} × {qrect.height()} px — Esc to cancel"
            font = QFont("Segoe UI", 9)
            painter.setFont(font)

            badge_y = qrect.bottom() + 6
            if badge_y + 24 > self.height():
                badge_y = qrect.top() - 26

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 20, 24, 210))
            badge_w = 210
            badge_rect = QRect(qrect.left(), max(4, badge_y), badge_w, 22)
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor(240, 240, 240))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
        else:
            # Draw center guidance prompt if not dragging yet
            painter.setPen(QColor(255, 255, 255, 210))
            font = QFont("Segoe UI", 12, QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Drag to select manga text region • Press ESC to cancel",
            )
