"""Unit tests for LiveAutoScanWatcher."""

from unittest.mock import MagicMock

import pytest
from pytestqt.qtbot import QtBot

from scanwitme.domain.models import Rect
from scanwitme.presentation.live_watcher import LiveAutoScanWatcher, compute_thumb_diff


@pytest.mark.unit
def test_compute_thumb_diff() -> None:
    # Identical
    b1 = bytes([100] * 1024)
    assert compute_thumb_diff(b1, b1) == 0.0

    # None or mismatched
    assert compute_thumb_diff(None, b1) == 1.0
    assert compute_thumb_diff(b1, bytes([100] * 500)) == 1.0

    # 50% inverted
    b2 = bytes([0] * 512 + [100] * 512)
    diff = compute_thumb_diff(b1, b2)
    assert 0.15 < diff < 0.25


@pytest.mark.unit
def test_live_watcher_start_stop_toggle(qtbot: QtBot) -> None:
    watcher = LiveAutoScanWatcher(poll_interval_ms=50, settle_ticks=2)
    assert not watcher.is_active

    with qtbot.waitSignal(watcher.state_changed, timeout=1000) as blocker:
        watcher.start()
    assert blocker.args == [True]
    assert watcher.is_active

    with qtbot.waitSignal(watcher.state_changed, timeout=1000) as blocker:
        watcher.stop()
    assert blocker.args == [False]
    assert not watcher.is_active

    # Test toggle
    watcher.toggle()
    assert watcher.is_active
    watcher.toggle()
    assert not watcher.is_active


@pytest.mark.unit
def test_live_watcher_motion_settle_and_trigger(qtbot: QtBot) -> None:
    watcher = LiveAutoScanWatcher(poll_interval_ms=10, settle_ticks=2, change_threshold=0.03)

    mock_rect = Rect(10, 20, 200, 150)
    watcher.set_callbacks(
        get_rect_fn=lambda: mock_rect,
        is_busy_fn=lambda: False,
    )

    frame_panel1 = bytes([50] * 1024)
    frame_scroll = bytes([100] * 1024)
    frame_panel2 = bytes([200] * 1024)

    current_frame = frame_panel1
    watcher._capture_thumbnail = MagicMock(side_effect=lambda rect: current_frame)

    watcher.start()
    assert watcher._last_translated_thumb == frame_panel1

    # Tick 1 & 2: Same panel 1 (idle, no signal)
    watcher._check_frame()
    watcher._check_frame()
    assert not watcher._motion_detected

    # Tick 3: User starts scrolling -> motion detected
    current_frame = frame_scroll
    watcher._check_frame()
    assert watcher._motion_detected
    assert watcher._stable_ticks_count == 0

    # Tick 4: User stops at panel 2 -> first stable tick
    current_frame = frame_panel2
    watcher._check_frame()
    assert watcher._motion_detected
    assert watcher._stable_ticks_count == 0  # panel2 was different from frame_scroll

    # Tick 5: Still at panel 2 -> stable tick 1
    watcher._check_frame()
    assert watcher._stable_ticks_count == 1

    # Tick 6: Still at panel 2 -> stable tick 2 -> triggers scan!
    with qtbot.waitSignal(watcher.scan_triggered, timeout=1000) as blocker:
        watcher._check_frame()

    assert blocker.args == [mock_rect]
    assert watcher._last_translated_thumb == frame_panel2
    assert not watcher._motion_detected

    watcher.stop()


@pytest.mark.unit
def test_live_watcher_skips_when_busy(qtbot: QtBot) -> None:
    watcher = LiveAutoScanWatcher(poll_interval_ms=10)

    # Busy is True
    watcher.set_callbacks(
        get_rect_fn=lambda: Rect(0, 0, 100, 100),
        is_busy_fn=lambda: True,
    )

    mock_capture = MagicMock()
    watcher._capture_thumbnail = mock_capture

    watcher.start()
    mock_capture.reset_mock()
    watcher._check_frame()

    # Capture should not be called when busy during periodic frame check
    assert not mock_capture.called
    watcher.stop()
