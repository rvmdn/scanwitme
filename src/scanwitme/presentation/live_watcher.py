"""Live auto-scan watcher that monitors sniper frame pixels and triggers OCR on page/scroll changes."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage

from scanwitme.domain.models import Rect

logger = logging.getLogger("scanwitme.presentation.live_watcher")


def compute_thumb_diff(b1: bytes | None, b2: bytes | None) -> float:
    """Compute normalized mean absolute difference between two 32x32 grayscale thumbnails."""
    if not b1 or not b2 or len(b1) != len(b2):
        return 1.0
    total_diff = sum(abs(x - y) for x, y in zip(b1, b2, strict=False))
    return total_diff / (len(b1) * 255.0)


class LiveAutoScanWatcher(QObject):
    """Monitors screen pixels under the sniper frame and auto-triggers translation when changes settle."""

    scan_triggered = Signal(object)  # Emits Rect
    state_changed = Signal(bool)  # Emits is_active
    status_updated = Signal(str)  # Emits status message

    def __init__(
        self,
        poll_interval_ms: int = 400,
        settle_ticks: int = 2,
        change_threshold: float = 0.03,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._poll_interval_ms = poll_interval_ms
        self._settle_ticks = settle_ticks
        self._change_threshold = change_threshold

        self._timer = QTimer(self)
        self._timer.setInterval(self._poll_interval_ms)
        self._timer.timeout.connect(self._check_frame)

        self._is_active = False
        self._get_rect_callback: Callable[[], Rect] | None = None
        self._is_busy_callback: Callable[[], bool] | None = None

        self._last_translated_thumb: bytes | None = None
        self._last_seen_thumb: bytes | None = None
        self._motion_detected = False
        self._stable_ticks_count = 0

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_callbacks(
        self,
        get_rect_fn: Callable[[], Rect],
        is_busy_fn: Callable[[], bool],
    ) -> None:
        """Register callbacks for retrieving current frame geometry and busy state."""
        self._get_rect_callback = get_rect_fn
        self._is_busy_callback = is_busy_fn

    def start(self) -> None:
        """Start auto-scan monitoring."""
        if self._is_active:
            return

        self._is_active = True
        self._motion_detected = False
        self._stable_ticks_count = 0

        # Grab initial baseline thumbnail
        if self._get_rect_callback:
            rect = self._get_rect_callback()
            initial_thumb = self._capture_thumbnail(rect)
            self._last_translated_thumb = initial_thumb
            self._last_seen_thumb = initial_thumb

        self._timer.start()
        self.state_changed.emit(True)
        self.status_updated.emit("🟢 Live Auto-Scan Aktif — Memantau perubahan...")
        logger.info("LiveAutoScanWatcher started (interval: %dms)", self._poll_interval_ms)

    def stop(self) -> None:
        """Stop auto-scan monitoring."""
        if not self._is_active:
            return

        self._timer.stop()
        self._is_active = False
        self._motion_detected = False
        self._stable_ticks_count = 0
        self.state_changed.emit(False)
        self.status_updated.emit("Live Auto-Scan Nonaktif.")
        logger.info("LiveAutoScanWatcher stopped")

    def toggle(self) -> bool:
        """Toggle active state and return new state."""
        if self._is_active:
            self.stop()
        else:
            self.start()
        return self._is_active

    def reset_baseline(self, new_thumb: bytes | None = None) -> None:
        """Update last translated baseline after a scan completes."""
        if new_thumb:
            self._last_translated_thumb = new_thumb
            self._last_seen_thumb = new_thumb
        elif self._get_rect_callback:
            rect = self._get_rect_callback()
            thumb = self._capture_thumbnail(rect)
            self._last_translated_thumb = thumb
            self._last_seen_thumb = thumb
        self._motion_detected = False
        self._stable_ticks_count = 0

    def _capture_thumbnail(self, rect: Rect) -> bytes | None:
        """Capture low-resolution 32x32 grayscale thumbnail of rect directly from screen."""
        if rect.width <= 0 or rect.height <= 0:
            return None

        center_x = rect.x + rect.width // 2
        center_y = rect.y + rect.height // 2
        screen = (
            QGuiApplication.screenAt(QPoint(center_x, center_y)) or QGuiApplication.primaryScreen()
        )
        if not screen:
            return None

        screen_geo = screen.geometry()
        rel_x = rect.x - screen_geo.x()
        rel_y = rect.y - screen_geo.y()
        crop_x = max(0, rel_x)
        crop_y = max(0, rel_y)
        crop_right = min(screen_geo.width(), rel_x + rect.width)
        crop_bottom = min(screen_geo.height(), rel_y + rect.height)
        crop_w = max(0, crop_right - crop_x)
        crop_h = max(0, crop_bottom - crop_y)

        if crop_w <= 0 or crop_h <= 0:
            return None

        try:
            pixmap = screen.grabWindow(0, crop_x, crop_y, crop_w, crop_h)
            if pixmap.isNull():
                return None
            img = (
                pixmap.toImage()
                .scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
                .convertToFormat(QImage.Format.Format_Grayscale8)
            )
            return bytes(img.constBits())
        except Exception as exc:
            logger.debug("Failed to capture thumbnail for live check: %s", exc)
            return None

    def _check_frame(self) -> None:
        """Periodic tick checking for screen changes under the frame."""
        if not self._is_active or not self._get_rect_callback:
            return

        # If OCR or translation is actively running, pause checks to avoid collision
        if self._is_busy_callback and self._is_busy_callback():
            return

        rect = self._get_rect_callback()
        current_thumb = self._capture_thumbnail(rect)
        if not current_thumb:
            return

        if self._last_seen_thumb is None:
            self._last_seen_thumb = current_thumb
            self._last_translated_thumb = current_thumb
            return

        # Check difference from previous tick
        diff_from_last_tick = compute_thumb_diff(current_thumb, self._last_seen_thumb)

        if diff_from_last_tick >= self._change_threshold:
            # Significant motion occurring (user is scrolling or flipping pages)
            self._motion_detected = True
            self._stable_ticks_count = 0
            self.status_updated.emit("🔄 Mendeteksi pergerakan komik...")
        else:
            # Frame is currently static compared to last tick
            if self._motion_detected:
                self._stable_ticks_count += 1
                if self._stable_ticks_count >= self._settle_ticks:
                    # Content has stopped moving and settled! Check against last translated panel
                    diff_from_translated = compute_thumb_diff(
                        current_thumb, self._last_translated_thumb
                    )
                    if diff_from_translated >= self._change_threshold:
                        logger.info(
                            "New stable panel detected (diff: %.3f). Triggering auto-scan.",
                            diff_from_translated,
                        )
                        self._last_translated_thumb = current_thumb
                        self._motion_detected = False
                        self._stable_ticks_count = 0
                        self.status_updated.emit("⚡ Panel baru terdeteksi! Memindai...")
                        self.scan_triggered.emit(rect)
                    else:
                        # Returned to the already translated panel
                        self._motion_detected = False
                        self._stable_ticks_count = 0
                        self.status_updated.emit("🟢 Live: Diam (Panel sama)")

        self._last_seen_thumb = current_thumb
