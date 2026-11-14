"""Screen capture provider utilizing PySide6 QScreen and High-DPI support."""

from __future__ import annotations

import logging

from PySide6.QtCore import QBuffer, QIODevice, QPoint
from PySide6.QtGui import QGuiApplication, QImage, QPixmap

from scanwitme.domain.errors import CaptureError
from scanwitme.domain.interfaces import CaptureProvider
from scanwitme.domain.models import CaptureResult, Rect

logger = logging.getLogger("scanwitme.capture")


class QtScreenCaptureProvider(CaptureProvider):
    """High-DPI and multi-monitor aware screen capture using Qt."""

    def __init__(self, application: QGuiApplication | None = None) -> None:
        self._app = application or QGuiApplication.instance()

    def capture_region(self, rect: Rect) -> CaptureResult:
        """Capture the screen rectangle defined by rect in virtual desktop coordinates."""
        if rect.width <= 0 or rect.height <= 0:
            raise CaptureError(
                f"Cannot capture invalid region: width={rect.width}, height={rect.height}"
            )

        # Locate the screen containing the center of the selection
        center_x = rect.x + rect.width // 2
        center_y = rect.y + rect.height // 2
        screen = QGuiApplication.screenAt(QPoint(center_x, center_y))

        if not screen:
            screen = QGuiApplication.primaryScreen()

        if not screen:
            raise CaptureError("No display screen found to capture.")

        dpr = screen.devicePixelRatio()
        screen_geo = screen.geometry()

        # Calculate relative coordinates on the chosen screen
        rel_x = rect.x - screen_geo.x()
        rel_y = rect.y - screen_geo.y()

        # Clamp relative coordinates within screen boundaries
        crop_x = max(0, rel_x)
        crop_y = max(0, rel_y)
        crop_right = min(screen_geo.width(), rel_x + rect.width)
        crop_bottom = min(screen_geo.height(), rel_y + rect.height)
        crop_w = max(0, crop_right - crop_x)
        crop_h = max(0, crop_bottom - crop_y)

        if crop_w <= 0 or crop_h <= 0:
            raise CaptureError(
                "Calculated capture region is completely outside visible screen bounds."
            )

        if self._app:
            self._app.processEvents()

        # Grab window pixels (0 = entire screen root)
        # On Windows High-DPI (DPR > 1, e.g. 125%, 150%, 200%), passing crop coordinates directly to
        # screen.grabWindow(0, crop_x, crop_y, crop_w, crop_h) can suffer from GDI scaling bugs.
        # Grabbing full screen and cropping device pixels ensures 100% precision across multi-DPI.
        full_pixmap: QPixmap = screen.grabWindow(0)
        if full_pixmap.isNull():
            pixmap: QPixmap = screen.grabWindow(0, crop_x, crop_y, crop_w, crop_h)
        else:
            phys_x = max(0, int(round(crop_x * dpr)))
            phys_y = max(0, int(round(crop_y * dpr)))
            phys_w = min(full_pixmap.width() - phys_x, max(1, int(round(crop_w * dpr))))
            phys_h = min(full_pixmap.height() - phys_y, max(1, int(round(crop_h * dpr))))
            pixmap = full_pixmap.copy(phys_x, phys_y, phys_w, phys_h)

        if pixmap.isNull():
            raise CaptureError("Screen grab produced a null pixmap.")

        image: QImage = pixmap.toImage()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        success = image.save(buffer, "PNG")
        buffer.close()

        if not success:
            raise CaptureError("Failed to encode captured pixmap to PNG bytes.")

        png_bytes = bytes(buffer.data())
        actual_x = screen_geo.x() + crop_x
        actual_y = screen_geo.y() + crop_y
        logger.debug(
            "Captured region (%d, %d, %d, %d) on screen %s with DPR %.2f, byte size %d",
            actual_x,
            actual_y,
            crop_w,
            crop_h,
            screen.name(),
            dpr,
            len(png_bytes),
        )

        return CaptureResult(
            image_bytes=png_bytes,
            bounds=Rect(x=actual_x, y=actual_y, width=crop_w, height=crop_h),
            device_pixel_ratio=dpr,
            extra={
                "screen_name": screen.name(),
                "width_px": image.width(),
                "height_px": image.height(),
            },
        )
