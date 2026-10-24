"""Unit tests for domain exceptions."""

import pytest

from scanwitme.domain.errors import (
    AuthenticationError,
    CaptureCancelled,
    CaptureError,
    InvalidRequestError,
    NetworkError,
    OCRNoTextFound,
    QuotaExceededError,
    ScanWitMeError,
    TranslationError,
)


@pytest.mark.unit
def test_exception_hierarchy() -> None:
    auth_err = AuthenticationError("Invalid API key")
    assert isinstance(auth_err, TranslationError)
    assert isinstance(auth_err, ScanWitMeError)
    assert auth_err.code == "auth_error"
    assert "Invalid API key" in str(auth_err)


@pytest.mark.unit
def test_capture_errors() -> None:
    cap_err = CaptureError("Screen device not available")
    assert isinstance(cap_err, ScanWitMeError)
    assert cap_err.code == "capture_error"

    cancel_err = CaptureCancelled()
    assert cancel_err.code == "capture_cancelled"


@pytest.mark.unit
def test_translation_errors() -> None:
    quota_err = QuotaExceededError()
    assert quota_err.code == "quota_exceeded"

    net_err = NetworkError()
    assert net_err.code == "network_error"

    inv_err = InvalidRequestError()
    assert inv_err.code == "invalid_request"

    ocr_none = OCRNoTextFound()
    assert ocr_none.code == "ocr_no_text"
