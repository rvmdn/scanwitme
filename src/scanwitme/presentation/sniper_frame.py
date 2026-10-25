"""Movable and resizable on-screen framing overlay for instant one-click region capture."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.models import Rect

logger = logging.getLogger("scanwitme.ui.sniper_frame")

BORDER_WIDTH = 3
TOP_BAR_HEIGHT = 34
RESIZE_MARGIN = 10


class SniperFrame(QWidget):
    """Framed sniper overlay that stays on screen ready to scan its framed area at any time."""

    scan_requested = Signal(object)  # Emits Rect
    auto_scan_toggled = Signal(bool)
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(180, 120)
        self.resize(420, 260)

        # Mouse tracking for dragging and resizing
        self._drag_position: QPoint | None = None
        self._resize_drag: bool = False
        self._resize_corner: str | None = None
        self._resize_start_geometry: QRect | None = None
        self._resize_start_mouse: QPoint | None = None
        self._auto_scan_active = False

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Control Bar
        self._top_bar = QWidget(self)
        self._top_bar.setFixedHeight(TOP_BAR_HEIGHT)
        self._top_bar.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #334155;
                border-bottom: none;
            }
        """)

        bar_layout = QHBoxLayout(self._top_bar)
        bar_layout.setContentsMargins(10, 2, 8, 2)
        bar_layout.setSpacing(8)

        # Title / Handle
        self._title_label = QLabel("🎯 Bingkai Pemindai", self._top_bar)
        self._title_label.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: bold; border: none;"
        )
        bar_layout.addWidget(self._title_label)

        # Dimension badge
        self._dim_label = QLabel("", self._top_bar)
        self._dim_label.setStyleSheet(
            "color: #94a3b8; font-size: 10px; font-family: monospace; border: none;"
        )
        self._update_dim_label()
        bar_layout.addWidget(self._dim_label)

        bar_layout.addStretch()

        # Auto-Scan (Live) Toggle Button
        self._auto_btn = QPushButton("🔄 Auto: OFF", self._top_bar)
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_btn.setToolTip(
            "Mode Live: Otomatis mendeteksi saat komik di-scroll dan menerjemahkan."
        )
        self._update_auto_btn_style()
        self._auto_btn.clicked.connect(self._toggle_auto_scan_clicked)
        bar_layout.addWidget(self._auto_btn)

        # Instant Scan Button
        self._scan_btn = QPushButton("⚡ Scan (Enter)", self._top_bar)
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                padding: 3px 10px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
            }
            QPushButton:pressed {
                background: #075985;
            }
        """)
        self._scan_btn.clicked.connect(self.trigger_capture)
        bar_layout.addWidget(self._scan_btn)

        # Close Button
        self._close_btn = QPushButton("✕", self._top_bar)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        self._close_btn.clicked.connect(self.close_frame)
        bar_layout.addWidget(self._close_btn)

        main_layout.addWidget(self._top_bar)

        # Hollow body space
        self._body_widget = QWidget(self)
        self._body_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        main_layout.addWidget(self._body_widget)

    def _update_dim_label(self) -> None:
        rect = self.get_capture_rect()
        self._dim_label.setText(f"[{rect.width} × {rect.height}]")

    def get_capture_rect(self) -> Rect:
        """Calculate the exact screen rectangle inside the hollow framed viewfinder."""
        # Frame coordinates in global screen space
        top_left = self.mapToGlobal(QPoint(0, 0))
        gx = top_left.x() + BORDER_WIDTH
        gy = top_left.y() + TOP_BAR_HEIGHT + BORDER_WIDTH
        gw = max(10, self.width() - (2 * BORDER_WIDTH))
        gh = max(10, self.height() - TOP_BAR_HEIGHT - (2 * BORDER_WIDTH))
        return Rect(x=int(gx), y=int(gy), width=int(gw), height=int(gh))

    def _update_auto_btn_style(self) -> None:
        if self._auto_scan_active:
            self._auto_btn.setText("🟢 Auto: ON")
            self._auto_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 3px 8px;
                    border: 1px solid #34d399;
                }
                QPushButton:hover {
                    background: #047857;
                }
            """)
            self._title_label.setText("🎯 Bingkai [LIVE]")
        else:
            self._auto_btn.setText("🔄 Auto: OFF")
            self._auto_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #94a3b8;
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 4px;
                    padding: 3px 8px;
                    border: 1px solid #334155;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #f8fafc;
                }
            """)
            self._title_label.setText("🎯 Bingkai Pemindai")

    def set_auto_scan_active(self, active: bool) -> None:
        """Update auto-scan toggle state."""
        self._auto_scan_active = active
        self._update_auto_btn_style()

    def _toggle_auto_scan_clicked(self) -> None:
        self._auto_scan_active = not self._auto_scan_active
        self._update_auto_btn_style()
        self.auto_scan_toggled.emit(self._auto_scan_active)

    def trigger_capture(self) -> None:
        """Trigger scan signal for current frame rectangle."""
        rect = self.get_capture_rect()
        logger.info("Sniper frame scan triggered for rect: %s", rect)
        self.scan_requested.emit(rect)

    def close_frame(self) -> None:
        """Hide frame and emit closed signal."""
        if self._auto_scan_active:
            self.set_auto_scan_active(False)
            self.auto_scan_toggled.emit(False)
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # Check if bottom-right resize corner
            if (
                pos.x() >= self.width() - RESIZE_MARGIN * 2
                and pos.y() >= self.height() - RESIZE_MARGIN * 2
            ):
                self._resize_drag = True
                self._resize_start_geometry = self.geometry()
                self._resize_start_mouse = event.globalPosition().toPoint()
                event.accept()
                return

            # Check if clicked on top bar for moving
            if pos.y() <= TOP_BAR_HEIGHT:
                self._drag_position = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()

        # Update cursor when hovering over bottom-right resize area
        if not self._resize_drag and not self._drag_position:
            if (
                pos.x() >= self.width() - RESIZE_MARGIN * 2
                and pos.y() >= self.height() - RESIZE_MARGIN * 2
            ):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif pos.y() <= TOP_BAR_HEIGHT:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

        if self._resize_drag and self._resize_start_geometry and self._resize_start_mouse:
            delta = event.globalPosition().toPoint() - self._resize_start_mouse
            new_w = max(self.minimumWidth(), self._resize_start_geometry.width() + delta.x())
            new_h = max(self.minimumHeight(), self._resize_start_geometry.height() + delta.y())
            self.resize(new_w, new_h)
            self._update_dim_label()
            event.accept()
            return

        if self._drag_position and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            self._update_dim_label()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_position = None
        self._resize_drag = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._update_dim_label()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.trigger_capture()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.close_frame()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Outer Frame Border (Glowing Cyan Viewfinder)
        border_pen = QPen(QColor(56, 189, 248, 220), BORDER_WIDTH)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw rect border around entire frame
        painter.drawRoundedRect(
            1,
            1,
            w - 2,
            h - 2,
            8,
            8,
        )

        # 2. Viewfinder Tech Corner Brackets on the hollow viewport
        corner_pen = QPen(QColor(14, 165, 233, 255), 3)
        painter.setPen(corner_pen)
        bracket_len = 16
        view_top = TOP_BAR_HEIGHT

        # Top-Left corner bracket
        painter.drawLine(
            BORDER_WIDTH,
            view_top + BORDER_WIDTH,
            BORDER_WIDTH + bracket_len,
            view_top + BORDER_WIDTH,
        )
        painter.drawLine(
            BORDER_WIDTH,
            view_top + BORDER_WIDTH,
            BORDER_WIDTH,
            view_top + BORDER_WIDTH + bracket_len,
        )

        # Top-Right corner bracket
        painter.drawLine(
            w - BORDER_WIDTH,
            view_top + BORDER_WIDTH,
            w - BORDER_WIDTH - bracket_len,
            view_top + BORDER_WIDTH,
        )
        painter.drawLine(
            w - BORDER_WIDTH,
            view_top + BORDER_WIDTH,
            w - BORDER_WIDTH,
            view_top + BORDER_WIDTH + bracket_len,
        )

        # Bottom-Left corner bracket
        painter.drawLine(
            BORDER_WIDTH, h - BORDER_WIDTH, BORDER_WIDTH + bracket_len, h - BORDER_WIDTH
        )
        painter.drawLine(
            BORDER_WIDTH, h - BORDER_WIDTH, BORDER_WIDTH, h - BORDER_WIDTH - bracket_len
        )

        # Bottom-Right corner bracket and resize grip dots
        painter.drawLine(
            w - BORDER_WIDTH, h - BORDER_WIDTH, w - BORDER_WIDTH - bracket_len, h - BORDER_WIDTH
        )
        painter.drawLine(
            w - BORDER_WIDTH, h - BORDER_WIDTH, w - BORDER_WIDTH, h - BORDER_WIDTH - bracket_len
        )

        # Resize grip indicator (diagonal lines in bottom right corner)
        grip_pen = QPen(QColor(56, 189, 248, 180), 2)
        painter.setPen(grip_pen)
        painter.drawLine(w - 12, h - 4, w - 4, h - 12)
        painter.drawLine(w - 8, h - 4, w - 4, h - 8)

        # 3. Subtle Center Crosshair
        cx = w // 2
        cy = view_top + (h - view_top) // 2
        cross_pen = QPen(QColor(56, 189, 248, 60), 1)
        painter.setPen(cross_pen)
        painter.drawLine(cx - 8, cy, cx + 8, cy)
        painter.drawLine(cx, cy - 8, cx, cy + 8)

        painter.end()
