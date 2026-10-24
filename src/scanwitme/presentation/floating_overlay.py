"""Floating, movable, always-on-top translation result overlay card."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
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

OVERLAY_STYLESHEET = """
QFrame#card {
    background-color: rgba(26, 28, 35, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 12px;
}

QLabel#title {
    color: #e2e8f0;
    font-size: 13px;
    font-weight: 600;
}

QLabel#status {
    color: #94a3b8;
    font-size: 11px;
}

QLabel#sectionHeader {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QLabel#sourceText {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.4;
    padding: 6px 8px;
    background-color: rgba(15, 23, 42, 0.6);
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}

QLabel#translatedText {
    color: #f8fafc;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    padding: 8px 10px;
    background-color: rgba(30, 41, 59, 0.7);
    border-radius: 6px;
    border: 1px solid rgba(59, 130, 246, 0.3);
}

QPushButton {
    background-color: rgba(51, 65, 85, 0.8);
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(71, 85, 105, 0.95);
    border-color: rgba(255, 255, 255, 0.25);
}

QPushButton:pressed {
    background-color: rgba(30, 41, 59, 0.95);
}

QPushButton#primaryAction {
    background-color: #2563eb;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton#primaryAction:hover {
    background-color: #1d4ed8;
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    color: #94a3b8;
    font-size: 14px;
    padding: 2px 6px;
    border-radius: 4px;
}

QPushButton#iconBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #f8fafc;
}

QPushButton#closeBtn:hover {
    background-color: #ef4444;
    color: #ffffff;
}
"""


class FloatingOverlay(QWidget):
    """Movable, frameless, always-on-top floating card displaying translation results."""

    copy_source_requested = Signal(str)
    copy_translation_requested = Signal(str)
    search_requested = Signal(str)
    web_translate_requested = Signal(str, str, str)  # text, src_lang, tgt_lang
    google_lens_requested = Signal()
    retry_requested = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(OVERLAY_STYLESHEET)

        self._drag_pos = QPoint()
        self._source_text = ""
        self._translated_text = ""
        self._source_lang = "ko"
        self._target_lang = "id"

        self._build_ui()
        self.resize(380, 260)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame(self)
        self._card.setObjectName("card")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # Header bar (Draggable handle + Title + Close)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        self._title_label = QLabel("ScanWitMe — Terjemahan", self._card)
        self._title_label.setObjectName("title")
        self._status_label = QLabel("Siap", self._card)
        self._status_label.setObjectName("status")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._status_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        self._close_btn = QPushButton("✕", self._card)
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.dismiss)
        header_layout.addWidget(self._close_btn)

        card_layout.addLayout(header_layout)

        # Content area inside scroll
        scroll = QScrollArea(self._card)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 4, 0, 4)
        scroll_layout.setSpacing(6)

        # Source Text Header & Copy
        src_header_layout = QHBoxLayout()
        self._src_header_label = QLabel("Teks Asli", scroll_content)
        self._src_header_label.setObjectName("sectionHeader")
        src_header_layout.addWidget(self._src_header_label)
        src_header_layout.addStretch()

        self._copy_src_btn = QPushButton("Salin", scroll_content)
        self._copy_src_btn.setObjectName("iconBtn")
        self._copy_src_btn.clicked.connect(self._copy_source)
        src_header_layout.addWidget(self._copy_src_btn)
        scroll_layout.addLayout(src_header_layout)

        self._source_label = QLabel("...", scroll_content)
        self._source_label.setObjectName("sourceText")
        self._source_label.setWordWrap(True)
        self._source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll_layout.addWidget(self._source_label)

        # Translated Text Header & Copy
        tgt_header_layout = QHBoxLayout()
        self._tgt_header_label = QLabel("Indonesia", scroll_content)
        self._tgt_header_label.setObjectName("sectionHeader")
        tgt_header_layout.addWidget(self._tgt_header_label)
        tgt_header_layout.addStretch()

        self._copy_tgt_btn = QPushButton("Salin", scroll_content)
        self._copy_tgt_btn.setObjectName("iconBtn")
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

        # Action Toolbar at bottom
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

    def display_result(self, result: TranslationResult) -> None:
        """Populate overlay with translation result and metrics."""
        self._source_text = result.source_text
        self._translated_text = result.translated_text
        self._source_lang = result.source_language
        self._target_lang = result.target_language

        self._source_label.setText(self._source_text or "(Kosong)")
        self._translated_label.setText(self._translated_text or "(Kosong)")

        src_title = f"Teks Asli ({self._source_lang.upper()})"
        self._src_header_label.setText(src_title)

        cache_str = " (dari cache)" if result.cached else ""
        timing_str = f" • {result.latency_ms:.0f}ms" if result.latency_ms > 0 else ""
        self._status_label.setText(f"Provider: {result.provider}{cache_str}{timing_str}")

        self.adjustSize()
        self.show()
        self.raise_()

    def set_loading(self, message: str = "Mengenali teks...") -> None:
        """Display loading status."""
        self._status_label.setText(message)
        self._source_label.setText("Memproses gambar...")
        self._translated_label.setText("Menunggu hasil terjemahan...")
        self.show()
        self.raise_()

    def set_error(self, error_message: str) -> None:
        """Display error banner on card."""
        self._status_label.setText("Gagal")
        self._translated_label.setText(f"⚠️ {error_message}")
        self.show()
        self.raise_()

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
        self.hide()
        self.dismissed.emit()

    # Drag handling
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
