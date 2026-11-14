"""UI tests for FloatingOverlay widget."""

import pytest
from pytestqt.qtbot import QtBot

from scanwitme.domain.models import TranslationResult
from scanwitme.presentation.floating_overlay import FloatingOverlay


@pytest.mark.ui
def test_floating_overlay_display_result(qtbot: QtBot) -> None:
    overlay = FloatingOverlay()
    qtbot.addWidget(overlay)

    result = TranslationResult(
        source_text="안녕하세요",
        translated_text="Halo",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
        latency_ms=85.0,
    )
    overlay.display_result(result)

    assert overlay.isVisible()
    assert overlay._source_label.text() == "안녕하세요"
    assert overlay._translated_label.text() == "Halo"
    assert "cloud_v2" in overlay._status_label.text()


@pytest.mark.ui
def test_floating_overlay_copy_actions(qtbot: QtBot) -> None:
    overlay = FloatingOverlay()
    qtbot.addWidget(overlay)

    result = TranslationResult(
        source_text="이것은 만화입니다",
        translated_text="Ini adalah manga",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
    )
    overlay.display_result(result)

    # Copy source
    with qtbot.waitSignal(overlay.copy_source_requested, timeout=1000) as blocker:
        overlay._copy_src_btn.click()
    assert blocker.args == ["이것은 만화입니다"]
    assert overlay._copy_src_btn.text() == "Tersalin!"

    # Copy translation
    with qtbot.waitSignal(overlay.copy_translation_requested, timeout=1000) as blocker:
        overlay._copy_tgt_btn.click()
    assert blocker.args == ["Ini adalah manga"]
    assert overlay._copy_tgt_btn.text() == "Tersalin!"


@pytest.mark.ui
def test_floating_overlay_buttons_and_dismiss(qtbot: QtBot) -> None:
    overlay = FloatingOverlay()
    qtbot.addWidget(overlay)

    result = TranslationResult(
        source_text="Test source",
        translated_text="Hasil tes",
        source_language="ko",
        target_language="id",
        provider="cloud_v2",
    )
    overlay.display_result(result)

    # Search Google button
    with qtbot.waitSignal(overlay.search_requested, timeout=1000) as blocker:
        overlay._search_btn.click()
    assert blocker.args == ["Test source"]

    # Web Translate button
    with qtbot.waitSignal(overlay.web_translate_requested, timeout=1000) as blocker:
        overlay._web_translate_btn.click()
    assert blocker.args == ["Test source", "ko", "id"]

    # Google Lens button
    with qtbot.waitSignal(overlay.google_lens_requested, timeout=1000):
        overlay._lens_btn.click()

    # Retry button
    with qtbot.waitSignal(overlay.retry_requested, timeout=1000):
        overlay._retry_btn.click()

    # Close button
    with qtbot.waitSignal(overlay.dismissed, timeout=1000):
        overlay._close_btn.click()
    assert not overlay.isVisible()


@pytest.mark.ui
def test_sliding_drawer_modes_and_dock_toggle(qtbot: QtBot) -> None:
    overlay = FloatingOverlay(dock_mode="bottom")
    qtbot.addWidget(overlay)

    assert overlay.dock_mode == "bottom"
    assert overlay._dock_btn.text() == "⇄ Sisi Kiri"

    # Toggle to left
    with qtbot.waitSignal(overlay.dock_mode_changed, timeout=1000) as blocker:
        overlay._dock_btn.click()
    assert blocker.args == ["left"]
    assert overlay.dock_mode == "left"
    assert overlay._dock_btn.text() == "⇄ Bawah"

    # Toggle back to bottom
    with qtbot.waitSignal(overlay.dock_mode_changed, timeout=1000) as blocker:
        overlay._dock_btn.click()
    assert blocker.args == ["bottom"]
    assert overlay.dock_mode == "bottom"


@pytest.mark.ui
def test_sliding_drawer_loading_and_error_states(qtbot: QtBot) -> None:
    overlay = FloatingOverlay()
    qtbot.addWidget(overlay)

    # Loading state
    overlay.set_loading("Mengenali teks...")
    assert overlay.isVisible()
    assert overlay._status_label.text() == "Mengenali teks..."
    assert overlay._source_label.text() == "Memproses gambar..."

    # Error state
    overlay.set_error("No readable text")
    assert overlay.isVisible()
    assert overlay._status_label.text() == "Gagal"
    assert "No readable text" in overlay._translated_label.text()
