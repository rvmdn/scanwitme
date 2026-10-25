"""UI tests for HistoryDialog and HistoryCardWidget."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from scanwitme.domain.models import HistoryItem
from scanwitme.infrastructure.history.sqlite_history import SQLiteHistoryRepository
from scanwitme.presentation.history_dialog import HistoryDialog


@pytest.fixture
def populated_repo() -> SQLiteHistoryRepository:
    repo = SQLiteHistoryRepository(db_path=":memory:")
    repo.add_item(
        HistoryItem(
            "id-1", "こんにちは世界", "Halo dunia", "JA", "ID", time.time() - 200, is_favorite=True
        )
    )
    repo.add_item(
        HistoryItem(
            "id-2", "안녕 친구", "Halo kawan", "KO", "ID", time.time() - 100, is_favorite=False
        )
    )
    repo.add_item(
        HistoryItem(
            "id-3", "谢谢你", "Terima kasih", "ZH", "ID", time.time() - 50, is_favorite=False
        )
    )
    return repo


@pytest.mark.ui
def test_history_dialog_display_and_chips(
    qtbot: QtBot, populated_repo: SQLiteHistoryRepository
) -> None:
    dialog = HistoryDialog(history_repo=populated_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    # Initial state: 3 items
    assert "3 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 3

    # Filter FAV
    fav_btn = dialog._chip_buttons["FAV"]
    fav_btn.click()
    assert "1 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 1

    # Filter KO
    ko_btn = dialog._chip_buttons["KO"]
    ko_btn.click()
    assert "1 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 1

    # Filter ALL
    all_btn = dialog._chip_buttons["ALL"]
    all_btn.click()
    assert "3 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 3


@pytest.mark.ui
def test_history_dialog_search_filter(
    qtbot: QtBot, populated_repo: SQLiteHistoryRepository
) -> None:
    dialog = HistoryDialog(history_repo=populated_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    # Search Japanese source text
    dialog._search_edit.setText("こんにちは")
    assert "1 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 1

    # Search Indonesian translated text
    dialog._search_edit.setText("Terima kasih")
    assert "1 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 1

    # Non-matching search
    dialog._search_edit.setText("xyz123tidakada")
    assert "0 Dialog" in dialog._counter_label.text()
    # When 0 items, one empty_label widget is present
    assert dialog._cards_layout.count() == 1

    # Clear search
    dialog._search_edit.clear()
    assert "3 Dialog" in dialog._counter_label.text()
    assert dialog._cards_layout.count() == 3


@pytest.mark.ui
def test_history_dialog_toggle_star_and_delete(
    qtbot: QtBot, populated_repo: SQLiteHistoryRepository
) -> None:
    dialog = HistoryDialog(history_repo=populated_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    # Item 2 (KO) is not favorite
    items = populated_repo.get_items("ALL")
    ko_item = [i for i in items if i.id == "id-2"][0]
    assert not ko_item.is_favorite

    # Find KO card widget in layout
    ko_card = None
    for idx in range(dialog._cards_layout.count()):
        widget = dialog._cards_layout.itemAt(idx).widget()
        if hasattr(widget, "_item") and widget._item.id == "id-2":
            ko_card = widget
            break
    assert ko_card is not None

    # Click star
    ko_card._star_btn.click()
    assert populated_repo.get_items("ALL")[1].is_favorite is True
    assert ko_card._star_btn.text() == "⭐"

    # Delete KO item
    ko_card._del_btn.click()
    assert len(populated_repo.get_items("ALL")) == 2
    assert dialog._cards_layout.count() == 2


@pytest.mark.ui
def test_history_dialog_export_and_clear_all(
    qtbot: QtBot, populated_repo: SQLiteHistoryRepository
) -> None:
    dialog = HistoryDialog(history_repo=populated_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    # Click export
    dialog._export_btn.click()
    clipboard_text = QApplication.clipboard().text()
    assert "ScanWitMe PC — Comic Dialogue History" in clipboard_text
    assert "Halo dunia" in clipboard_text

    # Clear all with mock confirmation
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        dialog._clear_btn.click()

    assert len(populated_repo.get_items("ALL")) == 0
    assert "0 Dialog" in dialog._counter_label.text()
