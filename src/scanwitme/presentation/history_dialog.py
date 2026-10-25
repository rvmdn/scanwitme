"""Dialog panel for comic dialogue history and bookmarking."""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from scanwitme.domain.i18n import tr
from scanwitme.domain.interfaces import HistoryRepository
from scanwitme.domain.models import HistoryItem

logger = logging.getLogger("scanwitme.ui.history")

HISTORY_STYLESHEET = """
QDialog#historyDialog {
    background-color: #0f172a;
}

QLabel#dialogTitle {
    color: #f8fafc;
    font-size: 16px;
    font-weight: 700;
}

QLabel#counterBadge {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLineEdit#searchInput {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit#searchInput:focus {
    border: 1px solid #38bdf8;
}

QPushButton.chipButton {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.chipButton:hover {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton.chipButtonActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    border: 1px solid #60a5fa;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}

QScrollArea#scrollArea {
    border: none;
    background-color: transparent;
}

QFrame#historyCard {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px;
}

QFrame#historyCard:hover {
    border-color: #475569;
}

QLabel#langBadge {
    background-color: #0f172a;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#timeLabel {
    color: #64748b;
    font-size: 11px;
}

QLabel#rawText {
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.4;
    padding: 4px 6px;
    background-color: rgba(15, 23, 42, 0.6);
    border-radius: 4px;
}

QLabel#transText {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.4;
    padding: 6px 8px;
    background-color: rgba(37, 99, 235, 0.15);
    border-left: 3px solid #38bdf8;
    border-radius: 4px;
}

QPushButton.cardActionBtn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    padding: 3px 6px;
}

QPushButton.cardActionBtn:hover {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton#starBtnFav {
    background-color: transparent;
    color: #fbbf24;
    border: none;
    font-size: 14px;
    padding: 2px 4px;
}

QPushButton#starBtnNormal {
    background-color: transparent;
    color: #64748b;
    border: none;
    font-size: 14px;
    padding: 2px 4px;
}

QPushButton#starBtnNormal:hover {
    color: #fbbf24;
}

QPushButton#bottomBtn {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#bottomBtn:hover {
    background-color: #334155;
    color: #ffffff;
}

QPushButton#clearBtn {
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#clearBtn:hover {
    background-color: #dc2626;
    color: #ffffff;
}
"""


class HistoryCardWidget(QFrame):
    """Visual card displaying a single comic dialogue history item."""

    favorite_toggled = Signal(str, bool)
    deleted = Signal(str)

    def __init__(self, item: HistoryItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyCard")
        self._item = item
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(8)

        lang_badge = QLabel(
            f"{self._item.source_lang.upper()} ➔ {self._item.target_lang.upper()}", self
        )
        lang_badge.setObjectName("langBadge")
        header.addWidget(lang_badge)

        dt_str = datetime.fromtimestamp(self._item.timestamp).strftime("%Y-%m-%d %H:%M")
        time_label = QLabel(dt_str, self)
        time_label.setObjectName("timeLabel")
        header.addWidget(time_label)

        header.addStretch()

        # Favorite Star Toggle
        self._star_btn = QPushButton("⭐" if self._item.is_favorite else "☆", self)
        self._star_btn.setObjectName("starBtnFav" if self._item.is_favorite else "starBtnNormal")
        self._star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._star_btn.setToolTip("Tandai Favorit / Bookmark")
        self._star_btn.clicked.connect(self._on_star_clicked)
        header.addWidget(self._star_btn)

        # Copy Button
        self._copy_btn = QPushButton("📋", self)
        self._copy_btn.setProperty("class", "cardActionBtn")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setToolTip("Salin Dialog")
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        header.addWidget(self._copy_btn)

        # Delete Button
        self._del_btn = QPushButton("🗑️", self)
        self._del_btn.setProperty("class", "cardActionBtn")
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setToolTip("Hapus dari riwayat")
        self._del_btn.clicked.connect(lambda: self.deleted.emit(self._item.id))
        header.addWidget(self._del_btn)

        layout.addLayout(header)

        # Raw Source Text
        raw_label = QLabel(self._item.source_text, self)
        raw_label.setObjectName("rawText")
        raw_label.setWordWrap(True)
        raw_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(raw_label)

        # Translated Text
        trans_label = QLabel(self._item.translated_text, self)
        trans_label.setObjectName("transText")
        trans_label.setWordWrap(True)
        trans_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(trans_label)

    def _on_star_clicked(self) -> None:
        new_fav = not self._item.is_favorite
        self._item.is_favorite = new_fav
        self._star_btn.setText("⭐" if new_fav else "☆")
        self._star_btn.setObjectName("starBtnFav" if new_fav else "starBtnNormal")
        # Force style update
        self._star_btn.style().unpolish(self._star_btn)
        self._star_btn.style().polish(self._star_btn)
        self.favorite_toggled.emit(self._item.id, new_fav)

    def _on_copy_clicked(self) -> None:
        text_to_copy = f"{self._item.source_text}\n{self._item.translated_text}"
        QApplication.clipboard().setText(text_to_copy)
        self._copy_btn.setText("✓")


class HistoryDialog(QDialog):
    """Modal dialog displaying comic dialogue history with search, chips, and export."""

    history_changed = Signal()

    FILTER_KEYS = [
        ("ALL", "history_filter_all"),
        ("FAV", "history_filter_fav"),
        ("JA", "history_filter_ja"),
        ("KO", "history_filter_ko"),
        ("ZH", "history_filter_zh"),
        ("EN", "history_filter_en"),
    ]

    def __init__(
        self,
        history_repo: HistoryRepository,
        ui_lang: str = "id",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("historyDialog")
        self._repo = history_repo
        self._ui_lang = ui_lang
        self._current_filter = "ALL"
        self._current_query = ""
        self._chip_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle(tr("history_title", ui_lang))
        self.resize(640, 560)
        self.setMinimumSize(540, 420)
        self.setStyleSheet(HISTORY_STYLESHEET)

        self._build_ui()
        self.refresh_items()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        # 1. Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        title_label = QLabel(tr("history_title", self._ui_lang), self)
        title_label.setObjectName("dialogTitle")
        header.addWidget(title_label)

        self._counter_label = QLabel("0 Dialog", self)
        self._counter_label.setObjectName("counterBadge")
        header.addWidget(self._counter_label)

        header.addStretch()

        close_top_btn = QPushButton("✕", self)
        close_top_btn.setProperty("class", "cardActionBtn")
        close_top_btn.setFixedSize(28, 28)
        close_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_top_btn.clicked.connect(self.accept)
        header.addWidget(close_top_btn)

        root_layout.addLayout(header)

        # 2. Search Box
        self._search_edit = QLineEdit(self)
        self._search_edit.setObjectName("searchInput")
        self._search_edit.setPlaceholderText(tr("history_search_placeholder", self._ui_lang))
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        root_layout.addWidget(self._search_edit)

        # 3. Filter Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        for filter_code, string_key in self.FILTER_KEYS:
            btn = QPushButton(tr(string_key, self._ui_lang), self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = filter_code == self._current_filter
            btn.setProperty("class", "chipButtonActive" if is_active else "chipButton")
            btn.clicked.connect(lambda _, f=filter_code: self._set_filter(f))
            self._chip_buttons[filter_code] = btn
            chips_layout.addWidget(btn)

        chips_layout.addStretch()
        root_layout.addLayout(chips_layout)

        # 4. Scrollable Content Area
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("scrollArea")
        self._scroll.setWidgetResizable(True)

        self._scroll_content = QWidget()
        self._cards_layout = QVBoxLayout(self._scroll_content)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)
        self._cards_layout.setSpacing(10)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._scroll_content)
        root_layout.addWidget(self._scroll, stretch=1)

        # 5. Bottom Action Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self._export_btn = QPushButton(tr("history_export_btn", self._ui_lang), self)
        self._export_btn.setObjectName("bottomBtn")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self._on_export_clicked)
        bottom_layout.addWidget(self._export_btn)

        self._save_btn = QPushButton(tr("history_save_btn", self._ui_lang), self)
        self._save_btn.setObjectName("bottomBtn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save_file_clicked)
        bottom_layout.addWidget(self._save_btn)

        self._clear_btn = QPushButton(tr("history_clear_btn", self._ui_lang), self)
        self._clear_btn.setObjectName("clearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_all_clicked)
        bottom_layout.addWidget(self._clear_btn)

        bottom_layout.addStretch()

        close_btn = QPushButton("Tutup", self)
        close_btn.setObjectName("bottomBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        root_layout.addLayout(bottom_layout)

    def _set_filter(self, filter_type: str) -> None:
        self._current_filter = filter_type
        for code, btn in self._chip_buttons.items():
            is_active = code == filter_type
            btn.setProperty("class", "chipButtonActive" if is_active else "chipButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh_items()

    def _on_search_text_changed(self, text: str) -> None:
        self._current_query = text.strip()
        self.refresh_items()

    def refresh_items(self) -> None:
        """Fetch items matching current filter and query, then update UI cards."""
        # Clear existing cards in layout
        while self._cards_layout.count() > 0:
            child = self._cards_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.setParent(None)
                widget.hide()
                widget.deleteLater()

        items = self._repo.get_items(filter_type=self._current_filter, query=self._current_query)
        count_text = f"{len(items)} Dialog" if self._ui_lang == "id" else f"{len(items)} Dialogues"
        self._counter_label.setText(count_text)

        if not items:
            empty_label = QLabel(tr("history_empty", self._ui_lang), self._scroll_content)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")
            self._cards_layout.addWidget(empty_label)
            empty_label.show()
            self._scroll_content.adjustSize()
            return

        for item in items:
            card = HistoryCardWidget(item, self._scroll_content)
            card.favorite_toggled.connect(self._on_card_favorite_toggled)
            card.deleted.connect(self._on_card_deleted)
            self._cards_layout.addWidget(card)
            card.show()

        self._scroll_content.adjustSize()

    def _on_card_favorite_toggled(self, item_id: str, is_favorite: bool) -> None:
        self._repo.toggle_favorite(item_id)
        self.history_changed.emit()
        # If currently filtered by favorites, refresh to remove unstarred item
        if self._current_filter == "FAV":
            self.refresh_items()

    def _on_card_deleted(self, item_id: str) -> None:
        self._repo.delete_item(item_id)
        self.history_changed.emit()
        self.refresh_items()

    def _on_clear_all_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus" if self._ui_lang == "id" else "Confirm Clear",
            tr("history_clear_confirm", self._ui_lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._repo.clear_all()
            self.history_changed.emit()
            self.refresh_items()

    def _on_export_clicked(self) -> None:
        formatted = self._repo.export_formatted(filter_type=self._current_filter)
        QApplication.clipboard().setText(formatted)
        orig_text = self._export_btn.text()
        self._export_btn.setText("✓ Tersalin!" if self._ui_lang == "id" else "✓ Copied!")
        self._export_btn.setEnabled(False)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, lambda: self._reset_export_btn(orig_text))

    def _reset_export_btn(self, orig_text: str) -> None:
        self._export_btn.setText(orig_text)
        self._export_btn.setEnabled(True)

    def _on_save_file_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Riwayat Dialog",
            "scanwitme_dialogues.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            formatted = self._repo.export_formatted(filter_type=self._current_filter)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(formatted)
                QMessageBox.information(
                    self,
                    "Berhasil Disimpan",
                    f"Riwayat berhasil disimpan ke:\n{file_path}",
                )
            except Exception as exc:
                QMessageBox.critical(self, "Gagal Menyimpan", f"Terjadi kesalahan: {exc}")
