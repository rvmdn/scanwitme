"""Unit tests for QtScreenCaptureProvider."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap

from scanwitme.domain.errors import CaptureError
from scanwitme.domain.models import Rect
from scanwitme.infrastructure.capture.qt_capture import QtScreenCaptureProvider


@pytest.mark.unit
def test_capture_invalid_dimensions() -> None:
    provider = QtScreenCaptureProvider()
    with pytest.raises(CaptureError, match="invalid region"):
        # We test rect with 0 dimensions (bypassing Rect __post_init__ or direct check)
        # Create valid rect then manipulate or test invalid bounds
        dummy_rect = Rect(x=0, y=0, width=10, height=10)
        object.__setattr__(dummy_rect, "width", 0)
        provider.capture_region(dummy_rect)


@pytest.mark.unit
def test_capture_region_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock QGuiApplication.screenAt
    mock_screen = MagicMock()
    mock_screen.geometry.return_value = QRect(0, 0, 1920, 1080)
    mock_screen.devicePixelRatio.return_value = 1.25
    mock_screen.name.return_value = "Display-1"

    # Mock pixmap and image
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    mock_screen.grabWindow.return_value = pixmap

    monkeypatch.setattr(
        "scanwitme.infrastructure.capture.qt_capture.QGuiApplication.screenAt",
        lambda pt: mock_screen,
    )

    provider = QtScreenCaptureProvider()
    rect = Rect(x=100, y=100, width=100, height=50)
    result = provider.capture_region(rect)

    assert result is not None
    assert len(result.image_bytes) > 0
    assert result.bounds.width == 100
    assert result.bounds.height == 50
    assert result.device_pixel_ratio == 1.25
    assert result.extra["screen_name"] == "Display-1"
