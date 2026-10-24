"""Domain layer exports."""

from scanwitme.domain.errors import (
    AuthenticationError,
    CaptureCancelled,
    CaptureError,
    InvalidRequestError,
    NetworkError,
    OCRError,
    OCRModelError,
    OCRNoTextFound,
    QuotaExceededError,
    ScanWitMeError,
    TranslationError,
)
from scanwitme.domain.interfaces import (
    CacheRepository,
    CaptureProvider,
    OCRProvider,
    SettingsRepository,
    TranslationProvider,
)
from scanwitme.domain.models import (
    CaptureResult,
    OCRBlock,
    Rect,
    ScanSession,
    ScanState,
    TranslationResult,
)

__all__ = [
    "AuthenticationError",
    "CacheRepository",
    "CaptureCancelled",
    "CaptureError",
    "CaptureProvider",
    "CaptureResult",
    "InvalidRequestError",
    "NetworkError",
    "OCRError",
    "OCRBlock",
    "OCRModelError",
    "OCRNoTextFound",
    "OCRProvider",
    "QuotaExceededError",
    "Rect",
    "ScanSession",
    "ScanState",
    "ScanWitMeError",
    "SettingsRepository",
    "TranslationError",
    "TranslationProvider",
    "TranslationResult",
]
