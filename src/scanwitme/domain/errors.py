"""Explicit application error hierarchy for ScanWitMe."""

from __future__ import annotations


class ScanWitMeError(Exception):
    """Base exception for all ScanWitMe errors."""

    def __init__(self, message: str, code: str = "internal_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# Capture Errors
class CaptureError(ScanWitMeError):
    """Raised when screen capture fails."""

    def __init__(self, message: str = "Failed to capture screen region") -> None:
        super().__init__(message, code="capture_error")


class CaptureCancelled(ScanWitMeError):
    """Raised when user cancels region selection."""

    def __init__(self, message: str = "Capture cancelled by user") -> None:
        super().__init__(message, code="capture_cancelled")


# OCR Errors
class OCRError(ScanWitMeError):
    """Raised when local OCR extraction fails."""

    def __init__(self, message: str = "OCR extraction failed", code: str = "ocr_error") -> None:
        super().__init__(message, code=code)


class OCRModelError(OCRError):
    """Raised when OCR model fails to load or download."""

    def __init__(self, message: str = "Failed to load OCR model") -> None:
        super().__init__(message, code="ocr_model_error")


class OCRNoTextFound(OCRError):
    """Raised when OCR detects no readable text in the image."""

    def __init__(self, message: str = "No text recognized in selected region") -> None:
        super().__init__(message, code="ocr_no_text")


# Translation Errors
class TranslationError(ScanWitMeError):
    """Base exception for translation failures."""

    def __init__(
        self, message: str = "Translation failed", code: str = "translation_error"
    ) -> None:
        super().__init__(message, code=code)


class AuthenticationError(TranslationError):
    """Raised when API credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication failed. Check your API key.") -> None:
        super().__init__(message, code="auth_error")


class QuotaExceededError(TranslationError):
    """Raised when provider quota or rate limit is reached."""

    def __init__(
        self, message: str = "Translation API quota exceeded or rate limit reached."
    ) -> None:
        super().__init__(message, code="quota_exceeded")


class NetworkError(TranslationError):
    """Raised on connection timeout or network unreachability."""

    def __init__(self, message: str = "Network request failed or timed out.") -> None:
        super().__init__(message, code="network_error")


class InvalidRequestError(TranslationError):
    """Raised when translation request payload or language parameters are invalid."""

    def __init__(self, message: str = "Invalid translation request parameters.") -> None:
        super().__init__(message, code="invalid_request")
