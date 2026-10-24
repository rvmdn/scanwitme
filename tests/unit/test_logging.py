"""Unit tests for secret-sanitizing logging."""

import logging

import pytest

from scanwitme.infrastructure.logging import SecretSanitizingFilter, setup_logging


@pytest.mark.unit
def test_secret_sanitizing_filter() -> None:
    api_key = "AIzaSyD-fakeGoogleCloudKey123456789"
    filter_ = SecretSanitizingFilter(secrets_to_mask=[api_key])

    record = logging.LogRecord(
        name="scanwitme",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=f"Calling API with key {api_key}",
        args=(),
        exc_info=None,
    )
    assert filter_.filter(record)
    assert api_key not in record.msg
    assert "***REDACTED***" in record.msg or "[KEY_REDACTED]" in record.msg


@pytest.mark.unit
def test_setup_logging_returns_configured_logger() -> None:
    logger = setup_logging(level="DEBUG", api_key="secret-key-to-redact")
    assert logger.name == "scanwitme"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1
