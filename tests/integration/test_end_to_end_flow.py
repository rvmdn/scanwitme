"""Integration test verifying full end-to-end capture, OCR, translation, and overlay flow."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from scanwitme.app import ScanWitMeApp
from scanwitme.domain.models import OCRBlock, Rect, TranslationResult
from tests.fixtures.synthetic_images import create_synthetic_image


@pytest.mark.integration
def test_full_application_flow(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. Setup mock app environment
    monkeypatch.setenv("APPDATA", str(tmp_path))

    q_app = QApplication.instance() or QApplication([])
    app = ScanWitMeApp(q_app=q_app)
    app.settings_repo.set("default_translation_provider", "cloud_v2")
    app.settings_repo.set("google_translate_api_key", "test_mock_api_key")

    # Mock screen capture to return synthetic Korean text image
    test_image_bytes = create_synthetic_image(["안녕하세요", "만화 번역입니다"])
    mock_capture = MagicMock()
    mock_capture.image_bytes = test_image_bytes
    mock_capture.bounds = Rect(100, 100, 300, 150)
    app.capture_provider.capture_region = MagicMock(return_value=mock_capture)

    # Mock OCR engine to return deterministic blocks without downloading external weights in test
    app.ocr_provider.recognize = MagicMock(
        return_value=[
            OCRBlock(
                text="안녕하세요",
                box=[[10, 10], [90, 10], [90, 30], [10, 30]],
                confidence=0.98,
                reading_order=1,
            ),
            OCRBlock(
                text="만화 번역입니다",
                box=[[10, 40], [150, 40], [150, 60], [10, 60]],
                confidence=0.97,
                reading_order=2,
            ),
        ]
    )

    # Mock Cloud Translation provider
    app.cloud_provider.translate = MagicMock(
        return_value=TranslationResult(
            source_text="안녕하세요 만화 번역입니다",
            translated_text="Halo ini terjemahan manga",
            source_language="ko",
            target_language="id",
            provider="cloud_v2",
            latency_ms=115.0,
        )
    )

    # 2. Trigger scan
    app.trigger_scan()
    assert app.controller.state.value == "capturing"

    # 3. Simulate region selection
    selected_rect = Rect(100, 100, 300, 150)
    app._on_region_selected(selected_rect)

    # Wait for thread pool workers to complete
    qtbot.waitUntil(lambda: app.controller.state.value == "completed", timeout=3000)

    # 4. Verify results displayed on overlay
    assert app.overlay.isVisible()
    assert app.overlay._source_label.text() == "안녕하세요 만화 번역입니다"
    assert app.overlay._translated_label.text() == "Halo ini terjemahan manga"
    assert "cloud_v2" in app.overlay._status_label.text()

    # 5. Verify caching occurred
    cached = app.cache_service.get(
        "안녕하세요 만화 번역입니다",
        source_lang="ko",
        target_lang="id",
        provider="cloud_v2",
    )
    assert cached is not None
    assert cached.translated_text == "Halo ini terjemahan manga"

    # 6. Verify history auto-recording
    history_items = app.history_repo.get_items("ALL")
    assert len(history_items) == 1
    assert history_items[0].source_text == "안녕하세요 만화 번역입니다"
    assert history_items[0].translated_text == "Halo ini terjemahan manga"
    assert history_items[0].source_lang == "ko"
    assert history_items[0].target_lang == "id"

    # 7. Test copy action
    with qtbot.waitSignal(app.overlay.copy_translation_requested, timeout=1000) as blocker:
        app.overlay._copy_tgt_btn.click()
    assert blocker.args == ["Halo ini terjemahan manga"]
    assert app.overlay._copy_tgt_btn.text() == "Tersalin!"


@pytest.mark.integration
def test_free_direct_flow(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))

    q_app = QApplication.instance() or QApplication([])
    app = ScanWitMeApp(q_app=q_app)
    # Default is free_direct without api key
    assert app.app_settings.default_translation_provider == "free_direct"

    test_image_bytes = create_synthetic_image(["渐的意识到自己"])
    mock_capture = MagicMock()
    mock_capture.image_bytes = test_image_bytes
    mock_capture.bounds = Rect(50, 50, 200, 100)
    app.capture_provider.capture_region = MagicMock(return_value=mock_capture)

    app.ocr_provider.recognize = MagicMock(
        return_value=[
            OCRBlock(
                text="渐的意识到自己",
                box=[[10, 10], [90, 10], [90, 30], [10, 30]],
                confidence=0.98,
                reading_order=1,
            )
        ]
    )

    app.free_provider.translate = MagicMock(
        return_value=TranslationResult(
            source_text="渐的意识到自己",
            translated_text="Secara bertahap menyadari diri",
            source_language="zh",
            target_language="id",
            provider="free_direct",
            latency_ms=80.0,
        )
    )

    app.trigger_scan()
    app._on_region_selected(Rect(50, 50, 200, 100))

    qtbot.waitUntil(lambda: app.controller.state.value == "completed", timeout=3000)

    assert app.overlay.isVisible()
    assert app.overlay._source_label.text() == "渐的意识到自己"
    assert app.overlay._translated_label.text() == "Secara bertahap menyadari diri"
    assert "free_direct" in app.overlay._status_label.text()
