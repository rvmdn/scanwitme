"""UI tests for RegionSelector widget."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from scanwitme.domain.models import Rect
from scanwitme.presentation.region_selector import RegionSelector


@pytest.mark.ui
def test_region_selector_cancel_via_escape(qtbot: QtBot) -> None:
    selector = RegionSelector()
    qtbot.addWidget(selector)
    selector.start_selection()
    assert selector.isVisible()

    with qtbot.waitSignal(selector.cancelled, timeout=1000):
        # Send ESC key event
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        selector.keyPressEvent(event)

    assert not selector.isVisible()


@pytest.mark.ui
def test_region_selector_drag_and_select(qtbot: QtBot) -> None:
    selector = RegionSelector()
    qtbot.addWidget(selector)
    selector.start_selection()

    captured_rect: list[Rect] = []
    selector.region_selected.connect(lambda r: captured_rect.append(r))

    # Simulate mouse press at (50, 50)
    p1 = QPointF(50.0, 50.0)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        p1,
        p1,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    selector.mousePressEvent(press_event)

    # Simulate mouse move to (250, 150)
    p2 = QPointF(250.0, 150.0)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        p2,
        p2,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    selector.mouseMoveEvent(move_event)

    # Simulate mouse release at (250, 150)
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        p2,
        p2,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    selector.mouseReleaseEvent(release_event)

    assert len(captured_rect) == 1
    rect = captured_rect[0]
    assert rect.width == 200
    assert rect.height == 100
    assert not selector.isVisible()


@pytest.mark.ui
def test_region_selector_too_small_cancels(qtbot: QtBot) -> None:
    selector = RegionSelector()
    qtbot.addWidget(selector)
    selector.start_selection()

    cancelled_called = []
    selector.cancelled.connect(lambda: cancelled_called.append(True))

    # Mouse press at (10, 10), release at (12, 12) -> only 2x2 px, below minimum 8x8 threshold
    p_start = QPointF(10.0, 10.0)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        p_start,
        p_start,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    selector.mousePressEvent(press_event)

    p_end = QPointF(12.0, 12.0)
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        p_end,
        p_end,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    selector.mouseReleaseEvent(release_event)

    assert len(cancelled_called) == 1
    assert not selector.isVisible()
