"""Master application orchestrator integrating presentation, application, and infrastructure layers."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QPoint, QRunnable, QThreadPool
from PySide6.QtWidgets import QApplication

from scanwitme.application.cache_service import CacheService
from scanwitme.application.controller import ScanController
from scanwitme.application.workflow import TranslationWorkflow
from scanwitme.domain.errors import CaptureError
from scanwitme.domain.models import OCRBlock, Rect, TranslationResult
from scanwitme.infrastructure.cache.sqlite_cache import SQLiteCacheRepository
from scanwitme.infrastructure.capture.qt_capture import QtScreenCaptureProvider
from scanwitme.infrastructure.ocr.paddle_ocr import PaddleOCRProvider, detect_script
from scanwitme.infrastructure.settings.json_settings import JsonSettingsRepository
from scanwitme.infrastructure.translation.cloud_v2 import CloudTranslationV2Provider
from scanwitme.infrastructure.translation.mymemory import MyMemoryTranslationProvider
from scanwitme.infrastructure.translation.web_launcher import (
    GoogleLensLauncher,
    GoogleSearchLauncher,
    GoogleTranslateWebLauncher,
)
from scanwitme.presentation.floating_overlay import FloatingOverlay
from scanwitme.presentation.hotkey import GlobalHotkeyManager
from scanwitme.presentation.main_window import MainWindow
from scanwitme.presentation.region_selector import RegionSelector
from scanwitme.presentation.settings_dialog import SettingsDialog
from scanwitme.presentation.sniper_frame import SniperFrame
from scanwitme.presentation.tray import TrayManager
from scanwitme.presentation.workers import OCRWorker, TranslationWorker, WorkerSignals

logger = logging.getLogger("scanwitme.app")


class ScanWitMeApp(QObject):
    """Coordinates lifecycle, GUI windows, worker threads, and domain services."""

    def __init__(self, q_app: QApplication) -> None:
        super().__init__()
        self._q_app = q_app

        # Infrastructure
        self.settings_repo = JsonSettingsRepository()
        self.app_settings = self.settings_repo.to_app_settings()

        self.cache_repo = SQLiteCacheRepository(db_path=self.app_settings.cache_db_path)
        self.cache_service = CacheService(repository=self.cache_repo)

        self.capture_provider = QtScreenCaptureProvider(self._q_app)
        self.ocr_provider = PaddleOCRProvider()

        self.cloud_provider = CloudTranslationV2Provider(
            api_key=self.app_settings.google_translate_api_key
        )
        self.free_provider = MyMemoryTranslationProvider()
        initial_provider = (
            self.cloud_provider
            if self.app_settings.default_translation_provider == "cloud_v2"
            and self.app_settings.google_translate_api_key
            else self.free_provider
        )
        self.workflow = TranslationWorkflow(
            translation_provider=initial_provider,
            cache_service=self.cache_service if self.app_settings.cache_enabled else None,
        )

        # Application Controller
        self.controller = ScanController()

        # Thread Pool and Signals
        self.thread_pool = QThreadPool.globalInstance()
        self.worker_signals = WorkerSignals()
        self.worker_signals.ocr_done.connect(self._on_ocr_completed)
        self.worker_signals.translation_done.connect(self._on_translation_completed)
        self.worker_signals.error.connect(self._on_worker_error)

        # Presentation Widgets
        self.main_window = MainWindow(settings_repo=self.settings_repo)
        self.region_selector = RegionSelector()
        self.sniper_frame = SniperFrame()
        self.overlay = FloatingOverlay()
        self.tray = TrayManager(self.main_window)
        self.settings_dialog: SettingsDialog | None = None

        # Global Hotkey Manager
        self.hotkey_manager = GlobalHotkeyManager(hotkey_str=self.app_settings.hotkey)

        self._connect_signals()

    def start(self) -> None:
        """Launch application UI, system tray, and hotkey listener."""
        self.main_window.show()
        self.tray.show()

        # Start global hotkey
        success = self.hotkey_manager.start()
        if not success:
            self.main_window.set_status("⚠️ Hotkey gagal didaftarkan. Gunakan tombol Scan di UI.")

        # Background warmup of OCR engine so first scan is not delayed
        class _OCRPreloadWorker(QRunnable):
            def __init__(self, provider: PaddleOCRProvider) -> None:
                super().__init__()
                self._provider = provider

            def run(self) -> None:
                try:
                    self._provider.preload("ch")
                except Exception:
                    pass

        self.thread_pool.start(_OCRPreloadWorker(self.ocr_provider))

    def _connect_signals(self) -> None:
        # Scan triggers
        self.main_window.scan_requested.connect(self.trigger_scan)
        self.main_window.toggle_frame_requested.connect(self._toggle_sniper_frame)
        self.main_window.settings_requested.connect(self._open_settings)
        self.tray.scan_requested.connect(self.trigger_scan)
        self.tray.show_main_requested.connect(self._show_main_window)
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.exit_requested.connect(self._exit_app)
        self.hotkey_manager.hotkey_triggered.connect(self.trigger_scan)

        # Region selector
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.region_selector.cancelled.connect(self._on_region_cancelled)

        # Sniper frame
        self.sniper_frame.scan_requested.connect(self._on_sniper_scan_requested)

        # Overlay actions
        self.overlay.search_requested.connect(self._on_search_requested)
        self.overlay.web_translate_requested.connect(self._on_web_translate_requested)
        self.overlay.google_lens_requested.connect(self._on_google_lens_requested)
        self.overlay.retry_requested.connect(self._on_retry_requested)
        self.overlay.dismissed.connect(self._on_overlay_dismissed)

    def _toggle_sniper_frame(self) -> None:
        """Toggle on-screen sniper frame visibility."""
        if self.sniper_frame.isVisible():
            self.sniper_frame.hide()
            self.main_window.set_status("Bingkai pemindai disembunyikan.")
        else:
            self.sniper_frame.show()
            self.main_window.set_status(
                "Bingkai pemindai aktif. Posisikan di atas manga & tekan Scan."
            )

    def trigger_scan(self) -> None:
        """Start region scan workflow. If sniper frame is active, scans it directly."""
        if self.sniper_frame.isVisible():
            self.sniper_frame.trigger_capture()
            return

        try:
            self.controller.start_new_session()
        except Exception as exc:
            logger.info("Scan trigger ignored: %s", exc)
            return

        # Hide any active ScanWitMe overlays before capture so they are not captured
        self.overlay.hide()
        self.region_selector.start_selection()
        self.main_window.set_status("Pilih area manga di layar...")

    def _on_region_cancelled(self) -> None:
        self.controller.on_cancelled()
        self.main_window.set_status("Pemindaian dibatalkan.")

    def _on_sniper_scan_requested(self, rect: Rect) -> None:
        """Handle scan triggered directly from the sniper frame."""
        try:
            self.controller.start_new_session()
        except Exception as exc:
            logger.info("Sniper scan ignored: %s", exc)
            return

        self.overlay.hide()
        # Temporarily hide sniper frame border during screenshot
        self.sniper_frame.hide()
        try:
            self._execute_scan_rect(rect)
        finally:
            self.sniper_frame.show()

    def _on_region_selected(self, rect: Rect) -> None:
        self._execute_scan_rect(rect)

    def _execute_scan_rect(self, rect: Rect) -> None:
        session = self.controller.current_session
        if not session:
            return

        self.main_window.set_status("Menangkap layar dan memproses OCR...")

        # 1. Capture screen region
        try:
            capture_result = self.capture_provider.capture_region(rect)
            self.controller.on_capture_completed(session.session_id, capture_result)
        except CaptureError as exc:
            self.controller.on_error(session.session_id, str(exc))
            self.main_window.set_status(f"Gagal menangkap layar: {exc}")
            return

        # 2. Position overlay conveniently near the bottom or side of selection
        overlay_x = rect.x
        overlay_y = rect.bottom + 8
        self.overlay.move(QPoint(overlay_x, overlay_y))
        self.overlay.set_loading("Mengenali teks...")

        # 3. Dispatch OCR worker to thread pool
        source_lang = self.settings_repo.get("default_source_language", "auto")
        ocr_worker = OCRWorker(
            session_id=session.session_id,
            image_bytes=capture_result.image_bytes,
            language=source_lang,
            ocr_provider=self.ocr_provider,
            signals=self.worker_signals,
        )
        self.thread_pool.start(ocr_worker)

    def _on_ocr_completed(
        self,
        session_id: str,
        blocks: list[OCRBlock],
        ocr_duration_ms: float,
    ) -> None:
        if not self.controller.on_ocr_completed(session_id, blocks, ocr_duration_ms):
            return

        provider_name = self.settings_repo.get("default_translation_provider", "free_direct")
        configured_source_lang = self.settings_repo.get("default_source_language", "auto")
        target_lang = "id"

        combined_text = " ".join(b.text.strip() for b in blocks if b.text.strip())

        # Auto-detect language if configured to "auto"
        if configured_source_lang == "auto":
            detected_lang = detect_script(combined_text)
            source_lang = detected_lang
            logger.info("Auto-detected script '%s' for text: %s", detected_lang, combined_text[:40])
        else:
            source_lang = configured_source_lang

        # 1. If explicitly set to launch web browser:
        if provider_name == "web_launcher":
            GoogleTranslateWebLauncher.launch(combined_text, source_lang, target_lang)
            pseudo_result = TranslationResult(
                source_text=combined_text,
                translated_text="[Dibuka di Google Translate Browser]",
                source_language=source_lang,
                target_language=target_lang,
                provider="web_launcher",
                latency_ms=ocr_duration_ms,
            )
            self.controller.on_translation_completed(session_id, pseudo_result, 0.0)
            self.overlay.display_result(pseudo_result)
            self.main_window.set_status(
                f"Google Translate ({source_lang.upper()} ➔ ID) dibuka di browser."
            )
            return

        # 2. In-App Translation (Free Direct or Cloud API v2)
        api_key = self.settings_repo.get("google_translate_api_key")
        if provider_name == "cloud_v2" and api_key and api_key.strip():
            self.cloud_provider.set_api_key(api_key.strip())
            self.workflow.set_provider(self.cloud_provider)
        else:
            self.workflow.set_provider(self.free_provider)

        self.overlay.set_loading(
            f"Menerjemahkan teks ({source_lang.upper()}, OCR: {ocr_duration_ms:.0f}ms)..."
        )

        trans_worker = TranslationWorker(
            session_id=session_id,
            ocr_blocks=blocks,
            source_language=source_lang,
            target_language=target_lang,
            workflow=self.workflow,
            signals=self.worker_signals,
        )
        self.thread_pool.start(trans_worker)

    def _on_translation_completed(
        self,
        session_id: str,
        result: TranslationResult,
        translation_duration_ms: float,
    ) -> None:
        if not self.controller.on_translation_completed(
            session_id, result, translation_duration_ms
        ):
            return

        self.overlay.display_result(result)
        self.main_window.set_status("Terjemahan selesai.")

    def _on_worker_error(self, session_id: str, error_message: str) -> None:
        if not self.controller.on_error(session_id, error_message):
            return

        self.overlay.set_error(error_message)
        self.main_window.set_status(f"Error: {error_message}")

    def _on_search_requested(self, query: str) -> None:
        GoogleSearchLauncher.launch(query)

    def _on_web_translate_requested(self, text: str, src_lang: str, tgt_lang: str) -> None:
        GoogleTranslateWebLauncher.launch(text, src_lang, tgt_lang)

    def _on_google_lens_requested(self) -> None:
        GoogleLensLauncher.launch()

    def _on_retry_requested(self) -> None:
        session = self.controller.current_session
        if session and session.ocr_blocks:
            self._on_ocr_completed(
                session.session_id, session.ocr_blocks, session.metrics.get("ocr_ms", 0.0)
            )
        else:
            self.trigger_scan()

    def _on_overlay_dismissed(self) -> None:
        self.controller.on_cancelled()

    def _open_settings(self) -> None:
        self.settings_dialog = SettingsDialog(
            settings_repo=self.settings_repo,
            cache_repo=self.cache_repo,
            parent=self.main_window,
        )
        self.settings_dialog.settings_saved.connect(self._on_settings_saved)
        self.settings_dialog.exec()

    def _on_settings_saved(self) -> None:
        self.app_settings = self.settings_repo.to_app_settings()
        self.main_window.update_from_settings()

        # Update API key
        if self.app_settings.google_translate_api_key:
            self.cloud_provider.set_api_key(self.app_settings.google_translate_api_key)

        # Update hotkey
        self.hotkey_manager.update_hotkey(self.app_settings.hotkey)
        self.main_window.set_status("Pengaturan diperbarui.")

    def _show_main_window(self) -> None:
        self.main_window.showNormal()
        self.main_window.activateWindow()

    def _exit_app(self) -> None:
        self.hotkey_manager.stop()
        self.tray.hide()
        self._q_app.quit()
