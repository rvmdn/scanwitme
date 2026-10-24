"""ScanController managing scan lifecycle, concurrency control, and stale result rejection."""

from __future__ import annotations

import logging
import time

from scanwitme.domain.errors import ScanWitMeError
from scanwitme.domain.models import (
    CaptureResult,
    OCRBlock,
    ScanSession,
    ScanState,
    TranslationResult,
)

logger = logging.getLogger("scanwitme.application.controller")


class ScanController:
    """Coordinates scan state machine, active session lifecycle, and asynchronous result validation."""

    def __init__(self) -> None:
        self._current_session: ScanSession | None = None
        self._session_counter: int = 0
        self._state: ScanState = ScanState.IDLE

    @property
    def state(self) -> ScanState:
        return self._state

    @property
    def current_session(self) -> ScanSession | None:
        return self._current_session

    def start_new_session(self) -> ScanSession:
        """Initiate a new scan session. Rejects if a scan is currently active."""
        if self._state in (ScanState.CAPTURING, ScanState.RECOGNIZING, ScanState.TRANSLATING):
            logger.warning("Rejecting overlapping scan trigger while in state '%s'", self._state)
            raise ScanWitMeError(
                f"A scan operation is already in progress (state: {self._state.value}).",
                code="scan_in_progress",
            )

        self._session_counter += 1
        session_id = f"session-{self._session_counter}-{int(time.time())}"
        session = ScanSession(session_id=session_id, status=ScanState.CAPTURING)

        self._current_session = session
        self._state = ScanState.CAPTURING
        logger.info("Started new scan session: %s", session_id)
        return session

    def is_current_session(self, session_id: str) -> bool:
        """Check if the provided session_id corresponds to the active session (stale rejection)."""
        return self._current_session is not None and self._current_session.session_id == session_id

    def on_capture_completed(self, session_id: str, capture_result: CaptureResult) -> bool:
        """Handle screen capture completion. Returns False if session is stale."""
        if not self.is_current_session(session_id):
            logger.warning("Discarded stale capture result for session: %s", session_id)
            return False

        assert self._current_session is not None
        self._current_session.capture = capture_result
        self._current_session.status = ScanState.RECOGNIZING
        self._state = ScanState.RECOGNIZING
        return True

    def on_ocr_completed(
        self,
        session_id: str,
        blocks: list[OCRBlock],
        ocr_duration_ms: float = 0.0,
    ) -> bool:
        """Handle OCR recognition completion. Returns False if session is stale."""
        if not self.is_current_session(session_id):
            logger.warning("Discarded stale OCR result for session: %s", session_id)
            return False

        assert self._current_session is not None
        self._current_session.ocr_blocks = blocks
        self._current_session.metrics["ocr_ms"] = ocr_duration_ms
        self._current_session.status = ScanState.TRANSLATING
        self._state = ScanState.TRANSLATING
        return True

    def on_translation_completed(
        self,
        session_id: str,
        result: TranslationResult,
        translation_duration_ms: float = 0.0,
    ) -> bool:
        """Handle translation completion. Returns False if session is stale."""
        if not self.is_current_session(session_id):
            logger.warning("Discarded stale translation result for session: %s", session_id)
            return False

        assert self._current_session is not None
        self._current_session.translation = result
        self._current_session.metrics["translation_ms"] = translation_duration_ms
        self._current_session.status = ScanState.COMPLETED
        self._state = ScanState.COMPLETED
        logger.info("Session %s completed successfully.", session_id)
        return True

    def on_error(self, session_id: str, error_message: str) -> bool:
        """Transition session to ERROR state."""
        if not self.is_current_session(session_id):
            return False

        assert self._current_session is not None
        self._current_session.status = ScanState.ERROR
        self._current_session.error_message = error_message
        self._state = ScanState.ERROR
        logger.error("Session %s encountered error: %s", session_id, error_message)
        return True

    def on_cancelled(self, session_id: str | None = None) -> None:
        """Cancel current session and return to IDLE."""
        if self._current_session:
            if session_id is None or self._current_session.session_id == session_id:
                self._current_session.status = ScanState.CANCELLED
                logger.info("Session %s cancelled.", self._current_session.session_id)
        self._state = ScanState.IDLE
