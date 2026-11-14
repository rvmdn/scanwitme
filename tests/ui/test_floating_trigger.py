"""Unit and UI tests for FloatingTriggerWidget."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from pytestqt.qtbot import QtBot

from scanwitme.presentation.floating_trigger import FloatingTriggerWidget


def test_floating_trigger_init_and_properties(qtbot: QtBot) -> None:
    widget = FloatingTriggerWidget()
    qtbot.addWidget(widget)

    assert widget.width() == 54
    assert widget.height() == 54
    assert widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert widget.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_floating_trigger_click_signal(qtbot: QtBot) -> None:
    widget = FloatingTriggerWidget()
    qtbot.addWidget(widget)
    widget.show()

    with qtbot.waitSignal(widget.trigger_clicked, timeout=1000):
        # Normal click without dragging
        pt = QPointF(20.0, 20.0)
        ev_press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pt,
            pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(ev_press)

        ev_release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            pt,
            pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseReleaseEvent(ev_release)


def test_floating_trigger_drag_movement(qtbot: QtBot) -> None:
    widget = FloatingTriggerWidget()
    qtbot.addWidget(widget)
    widget.move(100, 100)
    widget.show()

    # Press
    pt_press = QPointF(10.0, 10.0)
    global_press = QPointF(110.0, 110.0)
    ev_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pt_press,
        global_press,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(ev_press)

    # Move far enough to be considered a drag
    global_move = QPointF(200.0, 250.0)
    ev_move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        pt_press,
        global_move,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mouseMoveEvent(ev_move)
    assert widget._is_dragging is True

    # Release
    with qtbot.waitSignal(widget.position_changed, timeout=1000) as blocker:
        ev_release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            pt_press,
            global_move,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseReleaseEvent(ev_release)

    assert blocker.args[0] == widget.x()
    assert blocker.args[1] == widget.y()


def test_floating_trigger_scanning_state(qtbot: QtBot) -> None:
    widget = FloatingTriggerWidget()
    qtbot.addWidget(widget)

    assert widget._is_scanning is False
    assert not widget._anim_timer.isActive()

    widget.set_scanning(True)
    assert widget._is_scanning is True
    assert widget._anim_timer.isActive()

    widget.set_scanning(False)
    assert widget._is_scanning is False
    assert not widget._anim_timer.isActive()


def test_floating_trigger_hover_events(qtbot: QtBot) -> None:
    widget = FloatingTriggerWidget()
    qtbot.addWidget(widget)

    assert widget._hovered is False

    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QEnterEvent

    enter_ev = QEnterEvent(QPointF(10, 10), QPointF(10, 10), QPointF(10, 10))
    widget.enterEvent(enter_ev)
    assert widget._hovered is True

    leave_ev = QEvent(QEvent.Type.Leave)
    widget.leaveEvent(leave_ev)
    assert widget._hovered is False
