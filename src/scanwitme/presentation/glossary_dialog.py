"""Dialog panel for comic dictionary and custom term glossary management."""

from __future__ import annotations

import logging
import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
from scanwitme.domain.interfaces import GlossaryRepository
from scanwitme.domain.models import GlossaryEntry

logger = logging.getLogger("scanwitme.ui.glossary")

GLOSSARY_STYLESHEET = """
QDialog#glossaryDialog {
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

QFrame#addPanel {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px;
}

QLineEdit.inputField {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
}

QLineEdit.inputField:focus {
    border: 1px solid #38bdf8;
}

QComboBox#langCombo {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}

QPushButton#addBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
    color: #ffffff;
    border: 1px solid #34d399;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#addBtn:hover {
    background: #059669;
}

QLineEdit#searchInput {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
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

QFrame#glossaryRow {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 10px;
}

QFrame#glossaryRow:hover {
    border-color: #475569;
}

QLabel#termBadge {
    background-color: #0f172a;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}

QLabel#termText {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 600;
}

QLabel#arrowText {
    color: #38bdf8;
    font-size: 14px;
    font-weight: bold;
}

QLabel#replacementText {
    color: #34d399;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.rowActionBtn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    padding: 2px 6px;
}

QPushButton.rowActionBtn:hover {
    background-color: #334155;
    color: #f8fafc;
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

QPushButton#presetBtn {
    background-color: rgba(37, 99, 235, 0.2);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#presetBtn:hover {
    background-color: #2563eb;
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


class GlossaryRowWidget(QFrame):
    """Row displaying a single glossary entry with toggle switch and delete."""

    toggled = Signal(str, bool)
    deleted = Signal(str)

    def __init__(self, entry: GlossaryEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("glossaryRow")
        self._entry = entry
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Enable/Disable Checkbox
        self._check = QCheckBox(self)
        self._check.setChecked(self._entry.enabled)
        self._check.setToolTip("Aktifkan / Nonaktifkan istilah ini")
        self._check.toggled.connect(self._on_check_toggled)
        layout.addWidget(self._check)

        # Language pill badge
        lang_label = QLabel(self._entry.language.upper(), self)
        lang_label.setObjectName("termBadge")
        layout.addWidget(lang_label)

        # Source term
        term_label = QLabel(self._entry.term, self)
        term_label.setObjectName("termText")
        term_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(term_label)

        # Arrow
        arrow = QLabel("➔", self)
        arrow.setObjectName("arrowText")
        layout.addWidget(arrow)

        # Custom replacement
        repl_label = QLabel(self._entry.replacement, self)
        repl_label.setObjectName("replacementText")
        repl_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(repl_label)

        layout.addStretch()

        # Delete button
        del_btn = QPushButton("🗑️", self)
        del_btn.setProperty("class", "rowActionBtn")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Hapus istilah ini")
        del_btn.clicked.connect(lambda: self.deleted.emit(self._entry.id))
        layout.addWidget(del_btn)

    def _on_check_toggled(self, checked: bool) -> None:
        self._entry.enabled = checked
        self.toggled.emit(self._entry.id, checked)


class GlossaryDialog(QDialog):
    """Modal dialog managing custom comic glossary terms and popular presets."""

    glossary_changed = Signal()

    FILTER_KEYS = [
        ("ALL", "glossary_filter_all"),
        ("JA", "glossary_filter_ja"),
        ("KO", "glossary_filter_ko"),
        ("ZH", "glossary_filter_zh"),
        ("EN", "glossary_filter_en"),
    ]

    def __init__(
        self,
        glossary_repo: GlossaryRepository,
        ui_lang: str = "id",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("glossaryDialog")
        self._repo = glossary_repo
        self._ui_lang = ui_lang
        self._current_filter = "ALL"
        self._current_query = ""
        self._chip_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle(tr("glossary_title", ui_lang))
        self.resize(650, 580)
        self.setMinimumSize(550, 440)
        self.setStyleSheet(GLOSSARY_STYLESHEET)

        self._build_ui()
        self.refresh_items()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        # 1. Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        title_label = QLabel(tr("glossary_title", self._ui_lang), self)
        title_label.setObjectName("dialogTitle")
        header.addWidget(title_label)

        self._counter_label = QLabel("0 Istilah", self)
        self._counter_label.setObjectName("counterBadge")
        header.addWidget(self._counter_label)

        header.addStretch()

        close_top_btn = QPushButton("✕", self)
        close_top_btn.setProperty("class", "rowActionBtn")
        close_top_btn.setFixedSize(28, 28)
        close_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_top_btn.clicked.connect(self.accept)
        header.addWidget(close_top_btn)

        root_layout.addLayout(header)

        # 2. Quick Add Panel
        add_frame = QFrame(self)
        add_frame.setObjectName("addPanel")
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(10, 8, 10, 8)
        add_layout.setSpacing(8)

        self._term_edit = QLineEdit(add_frame)
        self._term_edit.setProperty("class", "inputField")
        self._term_edit.setPlaceholderText(tr("glossary_term_input_placeholder", self._ui_lang))
        add_layout.addWidget(self._term_edit, stretch=2)

        arrow_add = QLabel("➔", add_frame)
        arrow_add.setStyleSheet("color: #38bdf8; font-weight: bold;")
        add_layout.addWidget(arrow_add)

        self._repl_edit = QLineEdit(add_frame)
        self._repl_edit.setProperty("class", "inputField")
        self._repl_edit.setPlaceholderText(tr("glossary_repl_input_placeholder", self._ui_lang))
        add_layout.addWidget(self._repl_edit, stretch=2)

        self._lang_combo = QComboBox(add_frame)
        self._lang_combo.setObjectName("langCombo")
        self._lang_combo.addItem("Semua", "ALL")
        self._lang_combo.addItem("Manga (JA)", "JA")
        self._lang_combo.addItem("Manhwa (KO)", "KO")
        self._lang_combo.addItem("Manhua (ZH)", "ZH")
        self._lang_combo.addItem("English (EN)", "EN")
        add_layout.addWidget(self._lang_combo, stretch=1)

        self._add_btn = QPushButton(tr("glossary_btn_add", self._ui_lang), add_frame)
        self._add_btn.setObjectName("addBtn")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_clicked)
        add_layout.addWidget(self._add_btn)

        root_layout.addWidget(add_frame)

        # 3. Search & Filter Bar
        self._search_edit = QLineEdit(self)
        self._search_edit.setObjectName("searchInput")
        self._search_edit.setPlaceholderText(tr("glossary_search_placeholder", self._ui_lang))
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        root_layout.addWidget(self._search_edit)

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

        # 4. Scroll Area
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("scrollArea")
        self._scroll.setWidgetResizable(True)

        self._scroll_content = QWidget()
        self._rows_layout = QVBoxLayout(self._scroll_content)
        self._rows_layout.setContentsMargins(0, 4, 0, 4)
        self._rows_layout.setSpacing(8)
        self._rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._scroll_content)
        root_layout.addWidget(self._scroll, stretch=1)

        # 5. Bottom Action Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self._preset_btn = QPushButton(tr("glossary_btn_presets", self._ui_lang), self)
        self._preset_btn.setObjectName("presetBtn")
        self._preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._preset_btn.clicked.connect(self._on_load_presets_clicked)
        bottom_layout.addWidget(self._preset_btn)

        self._clear_btn = QPushButton(tr("glossary_btn_clear", self._ui_lang), self)
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
        # Properly detach and remove previous widgets
        while self._rows_layout.count() > 0:
            child = self._rows_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.setParent(None)
                widget.hide()
                widget.deleteLater()

        entries = self._repo.get_entries(
            language=self._current_filter,
            query=self._current_query,
        )
        count_text = f"{len(entries)} Istilah" if self._ui_lang == "id" else f"{len(entries)} Terms"
        self._counter_label.setText(count_text)

        if not entries:
            empty_label = QLabel(tr("glossary_empty", self._ui_lang), self._scroll_content)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")
            self._rows_layout.addWidget(empty_label)
            empty_label.show()
            self._scroll_content.adjustSize()
            return

        for entry in entries:
            row = GlossaryRowWidget(entry, self._scroll_content)
            row.toggled.connect(self._on_row_toggled)
            row.deleted.connect(self._on_row_deleted)
            self._rows_layout.addWidget(row)
            row.show()

        self._scroll_content.adjustSize()

    def _on_add_clicked(self) -> None:
        term = self._term_edit.text().strip()
        repl = self._repl_edit.text().strip()
        lang = self._lang_combo.currentData()

        if not term or not repl:
            return

        entry = GlossaryEntry(
            id=str(uuid.uuid4()),
            term=term,
            replacement=repl,
            language=lang,
            enabled=True,
        )
        self._repo.add_entry(entry)
        self._term_edit.clear()
        self._repl_edit.clear()
        self.glossary_changed.emit()
        self.refresh_items()

    def _on_row_toggled(self, entry_id: str, enabled: bool) -> None:
        self._repo.toggle_enabled(entry_id)
        self.glossary_changed.emit()

    def _on_row_deleted(self, entry_id: str) -> None:
        self._repo.delete_entry(entry_id)
        self.glossary_changed.emit()
        self.refresh_items()

    def _on_load_presets_clicked(self) -> None:
        count = self._repo.load_presets(overwrite=False)
        self.glossary_changed.emit()
        self.refresh_items()
        msg = tr("glossary_status_presets", self._ui_lang, count=count)
        QMessageBox.information(self, "Preset Dimuat", msg)

    def _on_clear_all_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus" if self._ui_lang == "id" else "Confirm Clear",
            tr("glossary_clear_confirm", self._ui_lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._repo.clear_all()
            self.glossary_changed.emit()
            self.refresh_items()
