"""Dribbble-grade persistent floating AI quick trigger widget for ScanWitMe desktop.

Adapted from the mobile edition (ScanWitMe.ai Android):
A sleek, draggable, stay-on-top squircle trigger with signature purple AI gradient,
sparkle star glyph, active scanning spinner, and quick context actions.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QEnterEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QMenu, QWidget

logger = logging.getLogger("scanwitme.presentation.floating_trigger")


class FloatingTriggerWidget(QWidget):
    """Floating draggable squircle button staying on top of all windows."""

    trigger_clicked = Signal()
    scan_requested = Signal()
    sniper_requested = Signal()
    live_toggled = Signal()
    show_main_requested = Signal()
    position_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(54, 54)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._drag_start_pos: QPoint | None = None
        self._is_dragging: bool = False
        self._is_scanning: bool = False
        self._hovered: bool = False
        self._spinner_angle: float = 0.0

        # Animation timer for scanning spinner
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)
        self._anim_timer.timeout.connect(self._on_anim_tick)

    def set_scanning(self, scanning: bool) -> None:
        """Toggle active scanning animation (radial rotating pulse ring)."""
        self._is_scanning = scanning
        if scanning:
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            if self._anim_timer.isActive():
                self._anim_timer.stop()
        self.update()

    def _on_anim_tick(self) -> None:
        if self._is_scanning:
            self._spinner_angle = (self._spinner_angle + 12.0) % 360.0
            self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)
            self._is_dragging = True
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_dragging:
                self.trigger_clicked.emit()
            else:
                self.position_changed.emit(self.x(), self.y())
            self._drag_start_pos = None
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            """
        )

        scan_act = menu.addAction("⚡ Scan Area Layar")
        sniper_act = menu.addAction("🎯 Bingkai Bidik (Sniper)")
        live_act = menu.addAction("🔄 Toggle Live Auto-Scan")
        menu.addSeparator()
        main_act = menu.addAction("🪟 Buka ScanWitMe")
        menu.addSeparator()
        hide_act = menu.addAction("✖ Sembunyikan Tombol")

        chosen = menu.exec(global_pos)
        if chosen == scan_act:
            self.scan_requested.emit()
        elif chosen == sniper_act:
            self.sniper_requested.emit()
        elif chosen == live_act:
            self.live_toggled.emit()
        elif chosen == main_act:
            self.show_main_requested.emit()
        elif chosen == hide_act:
            self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pad = 4.0
        rect = QRectF(pad, pad, w - pad * 2, h - pad * 2)
        corner_radius = 16.0

        # 1. Gradient Background (#6366F1 to #8B5CF6)
        gradient = QLinearGradient(0, 0, w, h)
        if self._hovered:
            gradient.setColorAt(0.0, QColor(99, 102, 241))  # Indigo 500
            gradient.setColorAt(1.0, QColor(168, 85, 247))  # Purple 500
        else:
            gradient.setColorAt(0.0, QColor(79, 70, 229))  # Indigo 600
            gradient.setColorAt(1.0, QColor(139, 92, 246))  # Purple 600

        painter.setBrush(gradient)
        stroke_color = QColor(255, 255, 255, 120 if self._hovered else 70)
        painter.setPen(QPen(stroke_color, 1.5))
        painter.drawRoundedRect(rect, corner_radius, corner_radius)

        cx = w / 2.0
        cy = h / 2.0

        # 2. Scanning Neon Ring Indicator
        if self._is_scanning:
            ring_pen = QPen(QColor(16, 185, 129), 3.0)  # Emerald green
            ring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            spinner_rect = QRectF(2.0, 2.0, w - 4.0, h - 4.0)
            start_angle = int(-self._spinner_angle * 16)
            span_angle = int(240 * 16)
            painter.drawArc(spinner_rect, start_angle, span_angle)

        # 3. AI Sparkle Glyph (4-pointed star + miniature accent star)
        self._draw_ai_sparkle(painter, cx, cy)

    def _draw_ai_sparkle(self, painter: QPainter, cx: float, cy: float) -> None:
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)

        # Main 4-point AI Star
        outer_r = 10.0
        inner_r = 3.2
        path = QPainterPath()
        for i in range(8):
            r = outer_r if (i % 2 == 0) else inner_r
            angle = (i * math.pi / 4.0) - (math.pi / 2.0)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        painter.drawPath(path)

        # Miniature accent sparkle at top-right
        mini_cx = cx + 8.5
        mini_cy = cy - 8.5
        mini_outer = 4.0
        mini_inner = 1.5
        mini_path = QPainterPath()
        for i in range(8):
            r = mini_outer if (i % 2 == 0) else mini_inner
            angle = (i * math.pi / 4.0) - (math.pi / 2.0)
            x = mini_cx + r * math.cos(angle)
            y = mini_cy + r * math.sin(angle)
            if i == 0:
                mini_path.moveTo(x, y)
            else:
                mini_path.lineTo(x, y)
        mini_path.closeSubpath()
        painter.drawPath(mini_path)
