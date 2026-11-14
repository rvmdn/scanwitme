"""Unit and UI tests for BubbleOverlayWindow and comic inpainting clustering."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from scanwitme.domain.models import OCRBlock, Rect
from scanwitme.presentation.bubble_overlay import (
    BubbleItem,
    BubbleOverlayWindow,
    cluster_ocr_blocks,
)


def test_cluster_ocr_blocks_empty() -> None:
    assert cluster_ocr_blocks([]) == []


def test_cluster_ocr_blocks_single_and_close() -> None:
    # 2 vertically stacked lines of dialogue in the same speech bubble
    b1 = OCRBlock(
        text="안녕하세요",
        box=[[10, 10], [80, 10], [80, 25], [10, 25]],
        confidence=0.99,
        reading_order=1,
    )
    b2 = OCRBlock(
        text="반갑습니다",
        box=[[12, 30], [82, 30], [82, 45], [12, 45]],
        confidence=0.98,
        reading_order=2,
    )

    clusters = cluster_ocr_blocks([b1, b2], max_v_gap=24, max_h_gap=40)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cluster_ocr_blocks_distant() -> None:
    # Two different bubbles located far apart on the page
    b1 = OCRBlock(
        text="Bubble 1",
        box=[[10, 10], [60, 10], [60, 25], [10, 25]],
        confidence=0.95,
        reading_order=1,
    )
    b2 = OCRBlock(
        text="Bubble 2",
        box=[[200, 300], [250, 300], [250, 315], [200, 315]],
        confidence=0.95,
        reading_order=2,
    )

    clusters = cluster_ocr_blocks([b1, b2], max_v_gap=24, max_h_gap=40)
    assert len(clusters) == 2


def test_cluster_ocr_blocks_transitive_bridging() -> None:
    # b1 and b3 are not directly adjacent, but b2 bridges them
    b1 = OCRBlock(text="Line 1", box=[[10, 10], [60, 10], [60, 25], [10, 25]], confidence=0.99)
    b3 = OCRBlock(text="Line 3", box=[[10, 50], [60, 50], [60, 65], [10, 65]], confidence=0.99)
    b2 = OCRBlock(text="Line 2", box=[[10, 30], [60, 30], [60, 45], [10, 45]], confidence=0.99)

    clusters = cluster_ocr_blocks([b1, b3, b2], max_v_gap=15, max_h_gap=20)
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_bubble_overlay_display_and_clear(qtbot: QtBot) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    capture_rect = Rect(100, 150, 400, 300)
    bubble1 = BubbleItem(
        rect=QRect(10, 10, 120, 50),
        original_text="안녕",
        translated_text="Halo!",
    )
    overlay.display_bubbles(capture_rect, [bubble1])

    assert overlay.isVisible()
    assert overlay.x() == 100
    assert overlay.y() == 150
    assert overlay.width() == 400
    assert overlay.height() == 300
    assert len(overlay._bubbles) == 1

    overlay.clear_bubbles()
    assert not overlay.isVisible()
    assert len(overlay._bubbles) == 0


def test_bubble_overlay_click_toggle_peek(qtbot: QtBot) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(20, 20, 100, 60),
        original_text="원문",
        translated_text="Terjemahan",
        show_original=False,
    )
    overlay.display_bubbles(Rect(0, 0, 300, 300), [bubble])

    # Click inside the bubble (25, 25)
    with qtbot.waitSignal(overlay.bubble_clicked, timeout=1000) as blocker:
        click_pos = QPointF(25.0, 25.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            click_pos,
            click_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        overlay.mousePressEvent(event)

    assert blocker.args == [0]
    # Verify toggled to show original text
    assert overlay._bubbles[0].show_original is True
    assert overlay._bubbles[0].current_text == "원문"

    # Click inside again to toggle back to translation
    event2 = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        click_pos,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mousePressEvent(event2)
    assert overlay._bubbles[0].show_original is False
    assert overlay._bubbles[0].current_text == "Terjemahan"


def test_bubble_overlay_click_outside_closes(qtbot: QtBot) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(20, 20, 50, 50),
        original_text="A",
        translated_text="B",
    )
    overlay.display_bubbles(Rect(0, 0, 300, 300), [bubble])

    # Click outside (200, 200)
    with qtbot.waitSignal(overlay.closed, timeout=1000):
        click_pos = QPointF(200.0, 200.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            click_pos,
            click_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        overlay.mousePressEvent(event)

    assert not overlay.isVisible()


def test_bubble_overlay_escape_closes(qtbot: QtBot) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(10, 10, 50, 50),
        original_text="A",
        translated_text="B",
    )
    overlay.display_bubbles(Rect(0, 0, 200, 200), [bubble])

    with qtbot.waitSignal(overlay.closed, timeout=1000):
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        overlay.keyPressEvent(event)

    assert not overlay.isVisible()


def test_bubble_overlay_action_toolbar_copy(qtbot: QtBot, monkeypatch) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(20, 50, 100, 60),
        original_text="Hello",
        translated_text="Halo",
    )
    overlay.display_bubbles(Rect(0, 0, 400, 400), [bubble])

    # First click bubble to show toolbar and select it
    click_bubble = QPointF(30.0, 60.0)
    ev_bubble = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        click_bubble,
        click_bubble,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mousePressEvent(ev_bubble)
    assert overlay._selected_bubble_index == 0

    # Trigger repaint to generate hitboxes
    overlay.repaint()

    # Click copy button
    copy_pt = QPointF(
        float(overlay._action_copy_rect.center().x()),
        float(overlay._action_copy_rect.center().y()),
    )
    ev_copy = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        copy_pt,
        copy_pt,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(overlay.bubble_copied, timeout=1000) as blocker:
        overlay.mousePressEvent(ev_copy)

    # current_text is "Hello" because first click toggled peek
    assert blocker.args[0] == "Hello"
    assert overlay._copied_feedback is True


def test_bubble_overlay_action_toolbar_search(qtbot: QtBot, monkeypatch) -> None:
    import webbrowser

    searched_url = []
    monkeypatch.setattr(webbrowser, "open", lambda url: searched_url.append(url))

    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(20, 50, 100, 60),
        original_text="Dungeon",
        translated_text="Penjara Bawah Tanah",
    )
    overlay.display_bubbles(Rect(0, 0, 400, 400), [bubble])

    # Select bubble
    click_bubble = QPointF(30.0, 60.0)
    ev_bubble = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        click_bubble,
        click_bubble,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mousePressEvent(ev_bubble)
    overlay.repaint()

    # Click search button
    search_pt = QPointF(
        float(overlay._action_search_rect.center().x()),
        float(overlay._action_search_rect.center().y()),
    )
    ev_search = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        search_pt,
        search_pt,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(overlay.bubble_searched, timeout=1000):
        overlay.mousePressEvent(ev_search)

    assert len(searched_url) == 1
    assert "https://www.google.com/search?q=" in searched_url[0]


def test_bubble_overlay_action_toolbar_close(qtbot: QtBot) -> None:
    overlay = BubbleOverlayWindow()
    qtbot.addWidget(overlay)

    bubble = BubbleItem(
        rect=QRect(20, 50, 100, 60),
        original_text="A",
        translated_text="B",
    )
    overlay.display_bubbles(Rect(0, 0, 400, 400), [bubble])

    # Select bubble
    click_bubble = QPointF(30.0, 60.0)
    ev_bubble = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        click_bubble,
        click_bubble,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mousePressEvent(ev_bubble)
    overlay.repaint()
    assert overlay._selected_bubble_index == 0

    # Click close button on toolbar
    close_pt = QPointF(
        float(overlay._action_close_rect.center().x()),
        float(overlay._action_close_rect.center().y()),
    )
    ev_close = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        close_pt,
        close_pt,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    overlay.mousePressEvent(ev_close)
    assert overlay._selected_bubble_index == -1

