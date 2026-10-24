"""Sanitized logging module for ScanWitMe."""

from __future__ import annotations

import logging
import re
import sys

_API_KEY_REGEX = re.compile(r"(AIza[0-9A-Za-z-_]{35}|[0-9a-fA-F]{32,64})")


class SecretSanitizingFilter(logging.Filter):
    """Logging filter that redacts API keys and sensitive tokens."""

    def __init__(self, secrets_to_mask: list[str] | None = None) -> None:
        super().__init__()
        self._secrets = [s for s in (secrets_to_mask or []) if s and len(s) > 4]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._sanitize(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._sanitize(v) if isinstance(v, str) else v for v in record.args
                )
        return True

    def _sanitize(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "***REDACTED***")
        return _API_KEY_REGEX.sub("[KEY_REDACTED]", text)


def setup_logging(
    level: str = "INFO",
    api_key: str | None = None,
) -> logging.Logger:
    """Configure root logger with secret redaction."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("scanwitme")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        secrets = [api_key] if api_key else []
        handler.addFilter(SecretSanitizingFilter(secrets))
        logger.addHandler(handler)

    return logger
