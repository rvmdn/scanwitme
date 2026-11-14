"""Sliding translation drawer / bottom sheet overlay.

Supports smooth animated sliding from the bottom (Bottom Sheet) or left (Sidebar Drawer)
instead of an isolated detached pop-up window.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QGuiApplication, QMouseEvent, QScreen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.models import TranslationResult

logger = logging.getLogger("scanwitme.ui.overlay")

DRAWER_STYLESHEET = """
QFrame#drawerCard {
    background-color: rgba(15, 23, 42, 0.97);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 16px;
}

QFrame#pillHandle {
    background-color: rgba(148, 163, 184, 0.4);
    border-radius: 2px;
}

QLabel#title {
    color: #f1f5f9;
    font-size: 13px;
    font-weight: 700;
}

QLabel#status {
    color: #94a3b8;
    font-size: 11px;
}

QLabel#sectionHeader {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QLabel#sourceText {
    color: #cbd5e1;
    font-size: 13px;
    line-height: 1.4;
    padding: 8px 10px;
    background-color: rgba(30, 41, 59, 0.7);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

QLabel#translatedText {
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.45;
    padding: 10px 12px;
    background-color: rgba(30, 58, 138, 0.35);
    border-radius: 8px;
    border: 1px solid rgba(99, 102, 241, 0.4);
}

QPushButton {
    background-color: rgba(51, 65, 85, 0.85);
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: rgba(71, 85, 105, 0.95);
    border-color: rgba(99, 102, 241, 0.5);
    color: #ffffff;
}

QPushButton:pressed {
    background-color: rgba(30, 41, 59, 0.95);
}

QPushButton#dockToggleBtn {
    background-color: rgba(30, 41, 59, 0.7);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}

QPushButton#dockToggleBtn:hover {
    background-color: rgba(56, 189, 248, 0.2);
    color: #ffffff;
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    color: #38bdf8;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
}

QPushButton#iconBtn:hover {
    background-color: rgba(56, 189, 248, 0.15);
    color: #ffffff;
}

QPushButton#closeBtn {
    background-color: transparent;
    border: none;
    color: #94a3b8;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
}

QPushButton#closeBtn:hover {
    background-color: #ef4444;
    color: #ffffff;
}
"""


class FloatingOverlay(QWidget):
    """Animated slide-in translation drawer / bottom sheet.

    Slides smoothly from the bottom of the screen (Bottom Sheet) or from the left
    side (Sidebar Drawer) to present translation without blocking the reading flow.
    """

    copy_source_requested = Signal(str)
    copy_translation_requested = Signal(str)
    search_requested = Signal(str)
    web_translate_requested = Signal(str, str, str)  # text, src_lang, tgt_lang
    google_lens_requested = Signal()
    retry_requested = Signal()
    dismissed = Signal()
    dock_mode_changed = Signal(str)  # Emits "bottom" or "left"

    def __init__(
        self,
        parent: QWidget | None = None,
        dock_mode: str = "bottom",
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(DRAWER_STYLESHEET)

        self._dock_mode = dock_mode if dock_mode in ("bottom", "left") else "bottom"
        self._drag_pos = QPoint()
        self._source_text = ""
        self._translated_text = ""
        self._source_lang = "auto"
        self._target_lang = "id"

        # Animation setup
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(240)
        self._anim.finished.connect(self._on_anim_finished)
        self._is_dismissing = False

        self._build_ui()
        self._update_dimensions_for_mode()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._card = QFrame(self)
        self._card.setObjectName("drawerCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(14, 8, 14, 12)
        card_layout.setSpacing(6)

        # 1. Top Drag Handle / Pill (Like Mobile Bottom Sheet)
        handle_container = QHBoxLayout()
        handle_container.setContentsMargins(0, 0, 0, 0)
        handle_container.addStretch()
        self._pill_handle = QFrame(self._card)
        self._pill_handle.setObjectName("pillHandle")
        self._pill_handle.setFixedSize(40, 4)
        handle_container.addWidget(self._pill_handle)
        handle_container.addStretch()
        card_layout.addLayout(handle_container)

        # 2. Header Bar (Title + Badges + Mode Toggle + Close)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 2, 0, 2)
        header_layout.setSpacing(8)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        self._title_label = QLabel("✨ ScanWitMe — Terjemahan", self._card)
        self._title_label.setObjectName("title")
        self._status_label = QLabel("Siap", self._card)
        self._status_label.setObjectName("status")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._status_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Switch dock mode button: "⇄ Sisi Kiri" or "⇄ Bawah"
        self._dock_btn = QPushButton("⇄ Sisi Kiri", self._card)
        self._dock_btn.setObjectName("dockToggleBtn")
        self._dock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dock_btn.setToolTip("Ganti posisi slide (Bawah ⇄ Sisi Kiri)")
        self._dock_btn.clicked.connect(self._toggle_dock_mode)
        header_layout.addWidget(self._dock_btn)

        # Close button
        self._close_btn = QPushButton("✕", self._card)
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.dismiss)
        header_layout.addWidget(self._close_btn)

        card_layout.addLayout(header_layout)

        # 3. Content Area inside Scroll
        scroll = QScrollArea(self._card)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 2, 0, 2)
        scroll_layout.setSpacing(6)

        # Source Text Section
        src_header_layout = QHBoxLayout()
        self._src_header_label = QLabel("Teks Asli", scroll_content)
        self._src_header_label.setObjectName("sectionHeader")
        src_header_layout.addWidget(self._src_header_label)
        src_header_layout.addStretch()

        self._copy_src_btn = QPushButton("Salin", scroll_content)
        self._copy_src_btn.setObjectName("iconBtn")
        self._copy_src_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_src_btn.clicked.connect(self._copy_source)
        src_header_layout.addWidget(self._copy_src_btn)
        scroll_layout.addLayout(src_header_layout)

        self._source_label = QLabel("...", scroll_content)
        self._source_label.setObjectName("sourceText")
        self._source_label.setWordWrap(True)
        self._source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll_layout.addWidget(self._source_label)

        # Translated Text Section
        tgt_header_layout = QHBoxLayout()
        self._tgt_header_label = QLabel("Indonesia", scroll_content)
        self._tgt_header_label.setObjectName("sectionHeader")
        tgt_header_layout.addWidget(self._tgt_header_label)
        tgt_header_layout.addStretch()

        self._copy_tgt_btn = QPushButton("Salin", scroll_content)
        self._copy_tgt_btn.setObjectName("iconBtn")
        self._copy_tgt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_tgt_btn.clicked.connect(self._copy_translation)
        tgt_header_layout.addWidget(self._copy_tgt_btn)
        scroll_layout.addLayout(tgt_header_layout)

        self._translated_label = QLabel("...", scroll_content)
        self._translated_label.setObjectName("translatedText")
        self._translated_label.setWordWrap(True)
        self._translated_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll_layout.addWidget(self._translated_label)

        scroll.setWidget(scroll_content)
        card_layout.addWidget(scroll)

        # 4. Action Toolbar at bottom
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)

        self._search_btn = QPushButton("🔍 Google Search", self._card)
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.clicked.connect(self._search_google)
        action_layout.addWidget(self._search_btn)

        self._web_translate_btn = QPushButton("🌐 Google Translate", self._card)
        self._web_translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._web_translate_btn.clicked.connect(self._open_web_translate)
        action_layout.addWidget(self._web_translate_btn)

        self._lens_btn = QPushButton("📷 Lens", self._card)
        self._lens_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lens_btn.setToolTip("Buka Google Lens di browser")
        self._lens_btn.clicked.connect(self.google_lens_requested.emit)
        action_layout.addWidget(self._lens_btn)

        self._retry_btn = QPushButton("🔄 Coba Lagi", self._card)
        self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry_btn.clicked.connect(self._on_retry)
        action_layout.addWidget(self._retry_btn)

        card_layout.addLayout(action_layout)
        root_layout.addWidget(self._card)

        self._update_dock_btn_label()

    @property
    def dock_mode(self) -> str:
        return self._dock_mode

    def set_dock_mode(self, mode: str) -> None:
        """Set slide-in mode: 'bottom' (Bottom Sheet) or 'left' (Left Drawer)."""
        if mode in ("bottom", "left") and mode != self._dock_mode:
            self._dock_mode = mode
            self._update_dock_btn_label()
            self._update_dimensions_for_mode()
            self.dock_mode_changed.emit(self._dock_mode)
            if self.isVisible():
                self.slide_in()

    def _toggle_dock_mode(self) -> None:
        new_mode = "left" if self._dock_mode == "bottom" else "bottom"
        self.set_dock_mode(new_mode)

    def _update_dock_btn_label(self) -> None:
        if self._dock_mode == "bottom":
            self._dock_btn.setText("⇄ Sisi Kiri")
            self._dock_btn.setToolTip("Ganti ke panel slide dari sisi kiri")
        else:
            self._dock_btn.setText("⇄ Bawah")
            self._dock_btn.setToolTip("Ganti ke panel slide dari bawah (Bottom Sheet)")

    def _update_dimensions_for_mode(self) -> None:
        if self._dock_mode == "bottom":
            self.resize(560, 240)
        else:
            self.resize(380, 420)

    def _get_target_screen(self, preferred_screen: QScreen | None = None) -> QScreen | None:
        if preferred_screen is not None:
            return preferred_screen
        return QGuiApplication.primaryScreen()

    def calculate_geometries(
        self, screen: QScreen | None = None
    ) -> tuple[QRect, QRect]:
        """Compute (start_offscreen_rect, target_onscreen_rect) for current dock mode."""
        scr = self._get_target_screen(screen)
        geom = scr.availableGeometry() if scr else QRect(0, 0, 1920, 1080)

        if self._dock_mode == "bottom":
            w = min(600, max(460, geom.width() - 48))
            h = min(300, max(220, self.height()))
            tx = geom.x() + (geom.width() - w) // 2
            ty = geom.bottom() - h - 14

            start_rect = QRect(tx, geom.bottom() + 20, w, h)
            target_rect = QRect(tx, ty, w, h)
        else:  # "left"
            w = min(420, max(340, self.width()))
            h = min(geom.height() - 60, max(380, self.height()))
            tx = geom.x() + 14
            ty = geom.y() + (geom.height() - h) // 2

            start_rect = QRect(geom.x() - w - 20, ty, w, h)
            target_rect = QRect(tx, ty, w, h)

        return start_rect, target_rect

    def slide_in(self, screen: QScreen | None = None) -> None:
        """Animate drawer sliding smoothly into screen from bottom or left."""
        self._is_dismissing = False
        start_rect, target_rect = self.calculate_geometries(screen)

        # If already visible near target, smoothly adjust to target
        if not self.isVisible():
            self.setGeometry(start_rect)
            self.show()
            self.raise_()

        self._anim.stop()
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(240)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target_rect)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._is_dismissing:
            self.hide()
            self._is_dismissing = False
            self.dismissed.emit()

    def slide_out(self) -> None:
        """Animate drawer sliding off-screen and then hide."""
        if not self.isVisible() or self._is_dismissing:
            return

        self._is_dismissing = True
        start_rect, _ = self.calculate_geometries()

        self._anim.stop()
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.setDuration(180)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(start_rect)
        self._anim.start()

    def display_result(self, result: TranslationResult) -> None:
        """Populate drawer with translation result and slide into view."""
        self._source_text = result.source_text
        self._translated_text = result.translated_text
        self._source_lang = result.source_language
        self._target_lang = result.target_language

        self._source_label.setText(self._source_text or "(Kosong)")
        self._translated_label.setText(self._translated_text or "(Kosong)")

        src_title = f"Teks Asli ({self._source_lang.upper()})"
        self._src_header_label.setText(src_title)

        cache_str = " (cache)" if result.cached else ""
        timing_str = f" • {result.latency_ms:.0f}ms" if result.latency_ms > 0 else ""
        self._status_label.setText(
            f"{result.source_language.upper()} ➔ {result.target_language.upper()} • {result.provider}{cache_str}{timing_str}"
        )

        self._copy_src_btn.setText("Salin")
        self._copy_tgt_btn.setText("Salin")
        self.slide_in()

    def set_loading(self, message: str = "Mengenali teks...") -> None:
        """Display loading status while drawer slides in."""
        self._status_label.setText(message)
        self._source_label.setText("Memproses gambar...")
        self._translated_label.setText("Menunggu hasil terjemahan...")
        self.slide_in()

    def set_error(self, error_message: str) -> None:
        """Display error banner inside drawer."""
        self._status_label.setText("Gagal")
        self._translated_label.setText(f"⚠️ {error_message}")
        self.slide_in()

    def _copy_source(self) -> None:
        if self._source_text:
            QApplication.clipboard().setText(self._source_text)
            self._copy_src_btn.setText("Tersalin!")
            self.copy_source_requested.emit(self._source_text)

    def _copy_translation(self) -> None:
        if self._translated_text:
            QApplication.clipboard().setText(self._translated_text)
            self._copy_tgt_btn.setText("Tersalin!")
            self.copy_translation_requested.emit(self._translated_text)

    def _search_google(self) -> None:
        if self._source_text:
            self.search_requested.emit(self._source_text)

    def _open_web_translate(self) -> None:
        if self._source_text:
            self.web_translate_requested.emit(
                self._source_text, self._source_lang, self._target_lang
            )

    def _on_retry(self) -> None:
        self.retry_requested.emit()

    def dismiss(self) -> None:
        """Dismiss the drawer with a smooth slide-out animation."""
        self.slide_out()
        # Ensure instantaneous hide for synchronous tests
        self.hide()
        self.dismissed.emit()

    # Drag handling
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and hasattr(self, "_drag_pos")
            and not self._drag_pos.isNull()
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)
