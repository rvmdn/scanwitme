"""UI tests for SniperFrame widget."""

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from scanwitme.presentation.sniper_frame import SniperFrame


@pytest.mark.ui
def test_sniper_frame_lifecycle_and_signals(qtbot: QtBot) -> None:
    frame = SniperFrame()
    qtbot.addWidget(frame)
    frame.show()

    assert frame.isVisible()
    rect = frame.get_capture_rect()
    assert rect.width > 0
    assert rect.height > 0

    # Test scan button click
    with qtbot.waitSignal(frame.scan_requested, timeout=1000) as blocker:
        frame._scan_btn.click()
    assert blocker.args[0].width == rect.width

    # Test Enter key press
    with qtbot.waitSignal(frame.scan_requested, timeout=1000):
        qtbot.keyPress(frame, Qt.Key.Key_Return)

    # Test Close button click
    with qtbot.waitSignal(frame.closed, timeout=1000):
        frame._close_btn.click()
    assert not frame.isVisible()
