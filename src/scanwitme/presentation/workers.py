"""Background worker threads and signal bridges for non-blocking OCR and translation."""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QRunnable, Signal

from scanwitme.application.workflow import TranslationWorkflow
from scanwitme.domain.interfaces import OCRProvider
from scanwitme.domain.models import OCRBlock

logger = logging.getLogger("scanwitme.workers")


class WorkerSignals(QObject):
    """Signals emitted from background workers to update the Qt GUI thread."""

    ocr_done = Signal(str, list, float)  # session_id, list[OCRBlock], duration_ms
    translation_done = Signal(str, object, float)  # session_id, TranslationResult, duration_ms
    error = Signal(str, str)  # session_id, error_message


class OCRWorker(QRunnable):
    """Performs local OCR in a background thread pool."""

    def __init__(
        self,
        session_id: str,
        image_bytes: bytes,
        language: str,
        ocr_provider: OCRProvider,
        signals: WorkerSignals,
        direction: str = "auto",
    ) -> None:
        super().__init__()
        self._session_id = session_id
        self._image_bytes = image_bytes
        self._language = language
        self._ocr_provider = ocr_provider
        self.signals = signals
        self._direction = direction

    def run(self) -> None:
        start_time = time.perf_counter()
        try:
            blocks = self._ocr_provider.recognize(
                image_data=self._image_bytes,
                language=self._language,
                direction=self._direction,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.signals.ocr_done.emit(self._session_id, blocks, duration_ms)
        except Exception as exc:
            logger.warning("OCR worker error for session %s: %s", self._session_id, exc)
            self.signals.error.emit(self._session_id, str(exc))


class TranslationWorker(QRunnable):
    """Performs translation and caching in a background thread pool."""

    def __init__(
        self,
        session_id: str,
        ocr_blocks: list[OCRBlock],
        source_language: str,
        target_language: str,
        workflow: TranslationWorkflow,
        signals: WorkerSignals,
    ) -> None:
        super().__init__()
        self._session_id = session_id
        self._ocr_blocks = ocr_blocks
        self._source_lang = source_language
        self._target_lang = target_language
        self._workflow = workflow
        self.signals = signals

    def run(self) -> None:
        start_time = time.perf_counter()
        try:
            result = self._workflow.execute(
                ocr_blocks=self._ocr_blocks,
                source_language=self._source_lang,
                target_language=self._target_lang,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.signals.translation_done.emit(self._session_id, result, duration_ms)
        except Exception as exc:
            logger.warning("Translation worker error for session %s: %s", self._session_id, exc)
            self.signals.error.emit(self._session_id, str(exc))
