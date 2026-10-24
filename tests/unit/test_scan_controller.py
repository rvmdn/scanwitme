"""Unit tests for ScanController state machine and stale result rejection."""

import pytest

from scanwitme.application.controller import ScanController
from scanwitme.domain.errors import ScanWitMeError
from scanwitme.domain.models import CaptureResult, OCRBlock, Rect, ScanState, TranslationResult


@pytest.mark.unit
def test_controller_initial_state() -> None:
    controller = ScanController()
    assert controller.state == ScanState.IDLE
    assert controller.current_session is None


@pytest.mark.unit
def test_controller_start_session() -> None:
    controller = ScanController()
    session = controller.start_new_session()
    assert session is not None
    assert controller.state == ScanState.CAPTURING
    assert controller.current_session == session


@pytest.mark.unit
def test_controller_reject_overlapping_scan() -> None:
    controller = ScanController()
    controller.start_new_session()
    assert controller.state == ScanState.CAPTURING

    with pytest.raises(ScanWitMeError, match="already in progress"):
        controller.start_new_session()


@pytest.mark.unit
def test_controller_stale_result_rejection() -> None:
    controller = ScanController()
    session1 = controller.start_new_session()
    session1_id = session1.session_id

    # Session 1 is cancelled or superseded
    controller.on_cancelled()
    assert controller.state == ScanState.IDLE

    # Session 2 starts
    session2 = controller.start_new_session()
    session2_id = session2.session_id

    # Slow callback from session 1 arrives
    cap_res = CaptureResult(image_bytes=b"fake", bounds=Rect(0, 0, 10, 10))
    accepted = controller.on_capture_completed(session1_id, cap_res)
    assert accepted is False  # Stale rejected!

    # Valid callback from session 2 arrives
    accepted_valid = controller.on_capture_completed(session2_id, cap_res)
    assert accepted_valid is True
    assert controller.state == ScanState.RECOGNIZING


@pytest.mark.unit
def test_controller_full_state_progression() -> None:
    controller = ScanController()
    session = controller.start_new_session()
    sid = session.session_id

    # Capture
    cap_res = CaptureResult(image_bytes=b"fake", bounds=Rect(0, 0, 50, 50))
    assert controller.on_capture_completed(sid, cap_res) is True
    assert controller.state == ScanState.RECOGNIZING

    # OCR
    blocks = [OCRBlock(text="Hello", box=[[0, 0], [10, 0], [10, 10], [0, 10]], confidence=0.9)]
    assert controller.on_ocr_completed(sid, blocks, ocr_duration_ms=45.0) is True
    assert controller.state == ScanState.TRANSLATING
    assert session.metrics["ocr_ms"] == 45.0

    # Translation
    trans_res = TranslationResult(
        source_text="Hello",
        translated_text="Halo",
        source_language="en",
        target_language="id",
        provider="cloud_v2",
    )
    assert (
        controller.on_translation_completed(sid, trans_res, translation_duration_ms=120.0) is True
    )
    assert controller.state == ScanState.COMPLETED
    assert session.metrics["translation_ms"] == 120.0
