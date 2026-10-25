"""Master application orchestrator integrating presentation, application, and infrastructure layers."""

from __future__ import annotations

import logging
import re
import time
import uuid

from PySide6.QtCore import QObject, QPoint, QRect, QRunnable, QThreadPool
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from scanwitme.application.cache_service import CacheService
from scanwitme.application.controller import ScanController
from scanwitme.application.workflow import TranslationWorkflow
from scanwitme.domain.errors import CaptureError
from scanwitme.domain.i18n import tr
from scanwitme.domain.interfaces import GlossaryRepository, HistoryRepository
from scanwitme.domain.metadata import (
    DEFAULT_DISPLAY_MODE,
    DEFAULT_OCR_ENGINE,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_TEXT_DIRECTION,
    DEFAULT_TRANSLATION_PROVIDER,
    DEFAULT_UI_LANGUAGE,
)
from scanwitme.domain.models import HistoryItem, OCRBlock, Rect, ScanState, TranslationResult
from scanwitme.infrastructure.cache.sqlite_cache import SQLiteCacheRepository
from scanwitme.infrastructure.capture.qt_capture import QtScreenCaptureProvider
from scanwitme.infrastructure.glossary.sqlite_glossary import SQLiteGlossaryRepository
from scanwitme.infrastructure.history.sqlite_history import SQLiteHistoryRepository
from scanwitme.infrastructure.ocr.manga_ocr import MangaOCRProvider
from scanwitme.infrastructure.ocr.paddle_ocr import PaddleOCRProvider, detect_script
from scanwitme.infrastructure.settings.json_settings import JsonSettingsRepository
from scanwitme.infrastructure.translation.cloud_v2 import CloudTranslationV2Provider
from scanwitme.infrastructure.translation.mymemory import MyMemoryTranslationProvider
from scanwitme.infrastructure.translation.web_launcher import (
    GoogleLensLauncher,
    GoogleSearchLauncher,
    GoogleTranslateWebLauncher,
)
from scanwitme.presentation.bubble_overlay import (
    BubbleItem,
    BubbleOverlayWindow,
    cluster_ocr_blocks,
)
from scanwitme.presentation.floating_overlay import FloatingOverlay
from scanwitme.presentation.glossary_dialog import GlossaryDialog
from scanwitme.presentation.history_dialog import HistoryDialog
from scanwitme.presentation.hotkey import GlobalHotkeyManager
from scanwitme.presentation.live_watcher import LiveAutoScanWatcher
from scanwitme.presentation.main_window import MainWindow
from scanwitme.presentation.region_selector import RegionSelector
from scanwitme.presentation.settings_dialog import SettingsDialog
from scanwitme.presentation.sniper_frame import SniperFrame
from scanwitme.presentation.tray import TrayManager
from scanwitme.presentation.workers import OCRWorker, TranslationWorker, WorkerSignals

logger = logging.getLogger("scanwitme.app")


class ScanWitMeApp(QObject):
    """Coordinates lifecycle, GUI windows, worker threads, and domain services."""

    def __init__(
        self,
        q_app: QApplication,
        history_repo: HistoryRepository | None = None,
        glossary_repo: GlossaryRepository | None = None,
    ) -> None:
        super().__init__()
        self._q_app = q_app

        # Infrastructure
        self.settings_repo = JsonSettingsRepository()
        self.app_settings = self.settings_repo.to_app_settings()

        self.cache_repo = SQLiteCacheRepository(db_path=self.app_settings.cache_db_path)
        self.cache_service = CacheService(repository=self.cache_repo)

        if history_repo is not None:
            self.history_repo: HistoryRepository = history_repo
        else:
            self.history_repo = SQLiteHistoryRepository(db_path=self.app_settings.history_db_path)

        if glossary_repo is not None:
            self.glossary_repo: GlossaryRepository = glossary_repo
        else:
            self.glossary_repo = SQLiteGlossaryRepository(
                db_path=self.app_settings.glossary_db_path
            )
            if not self.glossary_repo.get_entries("ALL"):
                self.glossary_repo.load_presets()

        self.capture_provider = QtScreenCaptureProvider(self._q_app)
        self.ocr_provider = PaddleOCRProvider()
        self.manga_ocr_provider = MangaOCRProvider()

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
            glossary_service=self.glossary_repo,
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
        self.bubble_overlay = BubbleOverlayWindow()
        self.tray = TrayManager(self.main_window)
        self.settings_dialog: SettingsDialog | None = None
        self.history_dialog: HistoryDialog | None = None
        self.glossary_dialog: GlossaryDialog | None = None

        # Live Auto-Scan Watcher
        self.live_watcher = LiveAutoScanWatcher()
        self.live_watcher.set_callbacks(
            get_rect_fn=self.sniper_frame.get_capture_rect,
            is_busy_fn=lambda: (
                self.controller.state
                not in (
                    ScanState.IDLE,
                    ScanState.COMPLETED,
                    ScanState.ERROR,
                    ScanState.CANCELLED,
                )
            ),
        )

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
        self.main_window.history_requested.connect(self._open_history)
        self.main_window.glossary_requested.connect(self._open_glossary)
        self.main_window.display_mode_changed.connect(self._on_display_mode_changed)
        self.main_window.text_direction_changed.connect(self._on_text_direction_changed)
        self.main_window.source_language_changed.connect(self._on_source_lang_changed)
        self.main_window.target_language_changed.connect(self._on_target_lang_changed)
        self.main_window.ui_language_changed.connect(self._on_ui_lang_changed)
        self.main_window.theme_changed.connect(self._on_theme_changed)
        self.main_window.provider_changed.connect(self._on_provider_changed)
        self.tray.scan_requested.connect(self.trigger_scan)
        self.tray.show_main_requested.connect(self._show_main_window)
        self.tray.glossary_requested.connect(self._open_glossary)
        self.tray.history_requested.connect(self._open_history)
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.exit_requested.connect(self._exit_app)
        self.hotkey_manager.hotkey_triggered.connect(self.trigger_scan)

        # Region selector
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.region_selector.cancelled.connect(self._on_region_cancelled)

        # Sniper frame & Live Auto-Scan
        self.sniper_frame.scan_requested.connect(self._on_sniper_scan_requested)
        self.sniper_frame.auto_scan_toggled.connect(self._toggle_auto_scan)
        self.main_window.auto_scan_toggled.connect(self._toggle_auto_scan)
        self.live_watcher.scan_triggered.connect(self._on_sniper_scan_requested)
        self.live_watcher.status_updated.connect(self.main_window.set_status)

        # Overlay actions
        self.overlay.search_requested.connect(self._on_search_requested)
        self.overlay.web_translate_requested.connect(self._on_web_translate_requested)
        self.overlay.google_lens_requested.connect(self._on_google_lens_requested)
        self.overlay.retry_requested.connect(self._on_retry_requested)
        self.overlay.dismissed.connect(self._on_overlay_dismissed)

    def _toggle_sniper_frame(self) -> None:
        """Toggle on-screen sniper frame visibility."""
        if self.sniper_frame.isVisible():
            if self.live_watcher.is_active:
                self._toggle_auto_scan(False)
            self.sniper_frame.hide()
            self.main_window.set_status("Bingkai pemindai disembunyikan.")
        else:
            self.sniper_frame.show()
            self.main_window.set_status(
                "Bingkai pemindai aktif. Posisikan di atas manga & tekan Scan (atau aktifkan Live Auto)."
            )

    def _toggle_auto_scan(self, enabled: bool) -> None:
        """Toggle real-time auto-scan on comic panel scroll/movement."""
        if enabled:
            if not self.sniper_frame.isVisible():
                self.sniper_frame.show()
            self.live_watcher.start()
            self.sniper_frame.set_auto_scan_active(True)
            self.main_window.set_auto_scan_active(True)
            self.main_window.set_status(
                "🟢 Live Auto-Scan Aktif — Komik akan dipindai otomatis saat di-scroll."
            )
        else:
            self.live_watcher.stop()
            self.sniper_frame.set_auto_scan_active(False)
            self.main_window.set_auto_scan_active(False)
            self.main_window.set_status("Mode Live Auto-Scan dinonaktifkan.")

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
        self.bubble_overlay.clear_bubbles()
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
        self.bubble_overlay.clear_bubbles()
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

        self.bubble_overlay.clear_bubbles()
        self.main_window.set_status("Menangkap layar dan memproses OCR...")

        # 1. Capture screen region
        try:
            capture_result = self.capture_provider.capture_region(rect)
            self.controller.on_capture_completed(session.session_id, capture_result)
        except CaptureError as exc:
            self.controller.on_error(session.session_id, str(exc))
            self.main_window.set_status(f"Gagal menangkap layar: {exc}")
            return

        # 2. Position overlay conveniently near the selection within visible screen boundaries
        display_mode = self.settings_repo.get("display_mode", DEFAULT_DISPLAY_MODE)
        if display_mode in ("card", "both"):
            center_x = rect.x + rect.width // 2
            center_y = rect.y + rect.height // 2
            screen = (
                QGuiApplication.screenAt(QPoint(center_x, center_y))
                or QGuiApplication.primaryScreen()
            )
            card_w = max(380, self.overlay.width())
            card_h = max(220, self.overlay.height())

            if screen:
                screen_geo = screen.availableGeometry()
                # Vertical positioning: place below if fits, otherwise place above
                if rect.bottom + 8 + card_h <= screen_geo.bottom():
                    overlay_y = rect.bottom + 8
                elif rect.y - card_h - 8 >= screen_geo.top():
                    overlay_y = rect.y - card_h - 8
                else:
                    overlay_y = max(screen_geo.top() + 8, screen_geo.bottom() - card_h - 8)

                # Horizontal positioning: align with left edge, but clamp within screen width
                overlay_x = min(
                    max(screen_geo.left() + 8, rect.x),
                    screen_geo.right() - card_w - 8,
                )
            else:
                overlay_x = rect.x
                overlay_y = rect.bottom + 8

            self.overlay.move(QPoint(overlay_x, overlay_y))
            self.overlay.set_loading("Mengenali teks...")
        else:
            self.overlay.hide()

        # 3. Dispatch OCR worker to thread pool
        source_lang = self.settings_repo.get("default_source_language", DEFAULT_SOURCE_LANGUAGE)
        text_direction = self.settings_repo.get("text_direction", DEFAULT_TEXT_DIRECTION)
        ocr_engine_name = self.settings_repo.get("ocr_engine", DEFAULT_OCR_ENGINE)
        active_ocr_provider = (
            self.manga_ocr_provider
            if ocr_engine_name == "manga_ocr" and self.manga_ocr_provider.is_available()
            else self.ocr_provider
        )
        ocr_worker = OCRWorker(
            session_id=session.session_id,
            image_bytes=capture_result.image_bytes,
            language=source_lang,
            ocr_provider=active_ocr_provider,
            signals=self.worker_signals,
            direction=text_direction,
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

        provider_name = self.settings_repo.get(
            "default_translation_provider", DEFAULT_TRANSLATION_PROVIDER
        )
        configured_source_lang = self.settings_repo.get(
            "default_source_language", DEFAULT_SOURCE_LANGUAGE
        )
        target_lang = self.settings_repo.get("default_target_language", DEFAULT_TARGET_LANGUAGE)

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
                f"Google Translate ({source_lang.upper()} ➔ {target_lang.upper()}) dibuka di browser."
            )
            return

        # 2. In-App Translation (Free Direct or Cloud API v2)
        api_key = self.settings_repo.get("google_translate_api_key")
        if provider_name == "cloud_v2" and api_key and api_key.strip():
            self.cloud_provider.set_api_key(api_key.strip())
            self.workflow.set_provider(self.cloud_provider)
        else:
            self.workflow.set_provider(self.free_provider)

        has_vert = any((b.max_y - b.min_y) > 1.2 * (b.max_x - b.min_x) for b in blocks)
        vert_tag = " (⛩️ Vertikal)" if has_vert else ""
        self.overlay.set_loading(
            f"Menerjemahkan teks ({source_lang.upper()}{vert_tag}, OCR: {ocr_duration_ms:.0f}ms)..."
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

        display_mode = self.settings_repo.get("display_mode", DEFAULT_DISPLAY_MODE)
        session = self.controller.current_session
        capture_rect = session.capture.bounds if session and session.capture else None

        # 1. Floating card display
        if display_mode in ("card", "both"):
            self.overlay.display_result(result)
        else:
            self.overlay.hide()

        # 2. Direct comic bubble inpainting overlay
        if display_mode in ("bubble", "both") and capture_rect and session and session.ocr_blocks:
            bubbles = self._create_bubble_items(
                session.ocr_blocks, result.translated_text, capture_rect
            )
            if bubbles:
                self.bubble_overlay.display_bubbles(capture_rect, bubbles)
            else:
                self.bubble_overlay.clear_bubbles()
        else:
            self.bubble_overlay.clear_bubbles()

        # Record dialogue to history repository
        if (
            result.source_text.strip()
            and result.translated_text.strip()
            and not result.translated_text.startswith("[Dibuka")
        ):
            try:
                hist_item = HistoryItem(
                    id=str(uuid.uuid4()),
                    source_text=result.source_text.strip(),
                    translated_text=result.translated_text.strip(),
                    source_lang=result.source_language,
                    target_lang=result.target_language,
                    timestamp=time.time(),
                    is_favorite=False,
                )
                self.history_repo.add_item(hist_item)
            except Exception as exc:
                logger.warning("Failed to record dialogue history: %s", exc)

        self.main_window.set_status("Terjemahan selesai.")
        if self.live_watcher.is_active:
            self.live_watcher.reset_baseline()

    def _create_bubble_items(
        self,
        blocks: list[OCRBlock],
        translated_text: str,
        capture_rect: Rect | None = None,
    ) -> list[BubbleItem]:
        """Map OCR block clusters to translated comic dialogue bubbles."""
        if not blocks:
            return []

        clusters = cluster_ocr_blocks(blocks)
        if not clusters:
            return []

        # Determine reading direction (Japanese manga dialogue reads Right-to-Left)
        text_dir = self.settings_repo.get("text_direction", DEFAULT_TEXT_DIRECTION)
        is_vert = text_dir == "vertical" or (
            text_dir == "auto"
            and any((b.max_y - b.min_y) > 1.2 * (b.max_x - b.min_x) for b in blocks)
        )

        if is_vert:
            # Japanese manga: columns Right-to-Left, lines Top-to-Bottom
            clusters.sort(key=lambda c: (-max(b.max_x for b in c), min(b.min_y for b in c)))
        else:
            # Standard horizontal comics: Top-to-Bottom, Left-to-Right
            clusters.sort(key=lambda c: (min(b.min_y for b in c), min(b.min_x for b in c)))

        pad_x = 8
        pad_y = 6

        def _make_clamped_rect(min_x: int, min_y: int, max_x: int, max_y: int) -> QRect:
            rx = max(0, min_x - pad_x)
            ry = max(0, min_y - pad_y)
            rw = (max_x - min_x) + (pad_x * 2)
            rh = (max_y - min_y) + (pad_y * 2)
            if capture_rect:
                rw = max(1, min(capture_rect.width - rx, rw))
                rh = max(1, min(capture_rect.height - ry, rh))
            return QRect(rx, ry, rw, rh)

        if len(clusters) == 1:
            c = clusters[0]
            min_x = min(b.min_x for b in c)
            min_y = min(b.min_y for b in c)
            max_x = max(b.max_x for b in c)
            max_y = max(b.max_y for b in c)
            rect = _make_clamped_rect(min_x, min_y, max_x, max_y)
            orig = " ".join(b.text.strip() for b in c)
            return [BubbleItem(rect=rect, original_text=orig, translated_text=translated_text)]

        # Multiple speech bubbles detected
        lines = [line.strip() for line in translated_text.splitlines() if line.strip()]
        if len(lines) == len(clusters):
            bubble_texts = lines
        else:
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", translated_text) if s.strip()
            ]
            if len(sentences) == len(clusters):
                bubble_texts = sentences
            else:
                words = translated_text.split()
                total_orig_len = sum(len(" ".join(b.text for b in c)) for c in clusters) or 1
                bubble_texts = []
                curr_w = 0
                for i, c in enumerate(clusters):
                    if i == len(clusters) - 1:
                        bubble_texts.append(" ".join(words[curr_w:]))
                    else:
                        c_len = len(" ".join(b.text for b in c))
                        take_count = max(1, round(len(words) * (c_len / total_orig_len)))
                        take_count = min(
                            take_count,
                            max(1, len(words) - curr_w - (len(clusters) - 1 - i)),
                        )
                        bubble_texts.append(" ".join(words[curr_w : curr_w + take_count]))
                        curr_w += take_count

        bubbles: list[BubbleItem] = []
        for i, c in enumerate(clusters):
            min_x = min(b.min_x for b in c)
            min_y = min(b.min_y for b in c)
            max_x = max(b.max_x for b in c)
            max_y = max(b.max_y for b in c)
            rect = _make_clamped_rect(min_x, min_y, max_x, max_y)
            orig = " ".join(b.text.strip() for b in c)
            trans = bubble_texts[i] if i < len(bubble_texts) else orig
            bubbles.append(BubbleItem(rect=rect, original_text=orig, translated_text=trans))

        return bubbles

    def _on_display_mode_changed(self, mode: str) -> None:
        self.app_settings.display_mode = mode
        if mode == "bubble":
            self.overlay.hide()
        elif mode == "card":
            self.bubble_overlay.clear_bubbles()
        logger.info("Display mode changed to: %s", mode)

    def _on_text_direction_changed(self, direction: str) -> None:
        self.app_settings.text_direction = direction
        logger.info("Text reading direction set to: %s", direction)

    def _on_source_lang_changed(self, lang: str) -> None:
        self.app_settings.default_source_language = lang
        logger.info("Source language set to: %s", lang)

    def _on_provider_changed(self, provider: str) -> None:
        self.app_settings.default_translation_provider = provider
        logger.info("Translation provider set to: %s", provider)

    def _on_worker_error(self, session_id: str, error_message: str) -> None:
        if not self.controller.on_error(session_id, error_message):
            return

        display_mode = self.settings_repo.get("display_mode", DEFAULT_DISPLAY_MODE)
        if display_mode in ("card", "both") and not self.live_watcher.is_active:
            self.overlay.set_error(error_message)
        self.main_window.set_status(f"Error: {error_message}")

    def _on_display_mode_changed(self, mode: str) -> None:
        logger.info("Display mode changed to: %s", mode)
        self.main_window.set_status(f"Mode tampilan diubah ke: {mode}")

    def _on_text_direction_changed(self, direction: str) -> None:
        logger.info("Text direction changed to: %s", direction)
        self.main_window.set_status(f"Arah bacaan diubah ke: {direction}")

    def _on_source_lang_changed(self, lang: str) -> None:
        logger.info("Source language changed to: %s", lang)
        self.main_window.set_status(f"Bahasa asli diubah ke: {lang.upper()}")

    def _on_target_lang_changed(self, lang: str) -> None:
        logger.info("Target language changed to: %s", lang)
        ui_l = self.settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        self.main_window.set_status(tr("status_target_changed", ui_l, lang=lang.upper()))

    def _on_ui_lang_changed(self, lang: str) -> None:
        logger.info("UI language changed to: %s", lang)
        self.main_window.set_status(tr("status_ui_changed", lang, lang=lang.upper()))

    def _on_theme_changed(self, theme_id: str) -> None:
        logger.info("Theme changed to: %s", theme_id)
        ui_l = self.settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        self.main_window.set_status(tr("status_theme_changed", ui_l, theme=theme_id.capitalize()))

    def _on_provider_changed(self, provider: str) -> None:
        logger.info("Provider changed to: %s", provider)
        self.main_window.set_status(f"Provider diubah ke: {provider}")

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

    def _open_history(self) -> None:
        ui_lang = self.settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        self.history_dialog = HistoryDialog(
            history_repo=self.history_repo,
            ui_lang=ui_lang,
            parent=self.main_window,
        )
        self.history_dialog.exec()

    def _open_glossary(self) -> None:
        ui_lang = self.settings_repo.get("default_ui_language", DEFAULT_UI_LANGUAGE)
        self.glossary_dialog = GlossaryDialog(
            glossary_repo=self.glossary_repo,
            ui_lang=ui_lang,
            parent=self.main_window,
        )
        self.glossary_dialog.exec()

    def _on_settings_saved(self) -> None:
        self.app_settings = self.settings_repo.to_app_settings()
        self.main_window.update_from_settings()

        # Update API key
        if self.app_settings.google_translate_api_key:
            self.cloud_provider.set_api_key(self.app_settings.google_translate_api_key)

        # Update hotkey
        self.hotkey_manager.update_hotkey(self.app_settings.hotkey)

        # Refresh overlay state according to display mode
        if self.app_settings.display_mode == "bubble":
            self.overlay.hide()
        elif self.app_settings.display_mode == "card":
            self.bubble_overlay.clear_bubbles()
        self.main_window.set_status("Pengaturan diperbarui.")

    def _show_main_window(self) -> None:
        self.main_window.showNormal()
        self.main_window.activateWindow()

    def _exit_app(self) -> None:
        self.live_watcher.stop()
        self.hotkey_manager.stop()
        self.bubble_overlay.clear_bubbles()
        self.tray.hide()
        self._q_app.quit()
