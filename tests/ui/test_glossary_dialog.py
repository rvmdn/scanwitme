"""UI tests for GlossaryDialog and GlossaryRowWidget."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from scanwitme.infrastructure.glossary.sqlite_glossary import SQLiteGlossaryRepository
from scanwitme.presentation.glossary_dialog import GlossaryDialog


@pytest.fixture
def empty_glossary_repo() -> SQLiteGlossaryRepository:
    return SQLiteGlossaryRepository(db_path=":memory:")


@pytest.mark.ui
def test_glossary_dialog_display_and_add(
    qtbot: QtBot, empty_glossary_repo: SQLiteGlossaryRepository
) -> None:
    dialog = GlossaryDialog(glossary_repo=empty_glossary_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    assert "0 Istilah" in dialog._counter_label.text()

    # Add new term
    dialog._term_edit.setText("선배")
    dialog._repl_edit.setText("Sunbae")
    ko_idx = dialog._lang_combo.findData("KO")
    dialog._lang_combo.setCurrentIndex(ko_idx)

    dialog._add_btn.click()

    assert "1 Istilah" in dialog._counter_label.text()
    assert dialog._rows_layout.count() == 1
    entries = empty_glossary_repo.get_entries("ALL")
    assert len(entries) == 1
    assert entries[0].term == "선배"
    assert entries[0].replacement == "Sunbae"


@pytest.mark.ui
def test_glossary_dialog_load_presets_and_chips(
    qtbot: QtBot, empty_glossary_repo: SQLiteGlossaryRepository
) -> None:
    dialog = GlossaryDialog(glossary_repo=empty_glossary_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    with patch.object(QMessageBox, "information"):
        dialog._preset_btn.click()

    assert empty_glossary_repo.get_entries("ALL")
    total_count = len(empty_glossary_repo.get_entries("ALL"))
    assert f"{total_count} Istilah" in dialog._counter_label.text()

    # Filter Manga (JA)
    ja_btn = dialog._chip_buttons["JA"]
    ja_btn.click()
    ja_count = len(empty_glossary_repo.get_entries("JA"))
    assert f"{ja_count} Istilah" in dialog._counter_label.text()

    # Filter Manhwa (KO)
    ko_btn = dialog._chip_buttons["KO"]
    ko_btn.click()
    ko_count = len(empty_glossary_repo.get_entries("KO"))
    assert f"{ko_count} Istilah" in dialog._counter_label.text()

    # Return to ALL
    dialog._chip_buttons["ALL"].click()
    assert f"{total_count} Istilah" in dialog._counter_label.text()


@pytest.mark.ui
def test_glossary_dialog_search_filter(
    qtbot: QtBot, empty_glossary_repo: SQLiteGlossaryRepository
) -> None:
    dialog = GlossaryDialog(glossary_repo=empty_glossary_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    with patch.object(QMessageBox, "information"):
        dialog._preset_btn.click()

    # Search for "Shifu"
    dialog._search_edit.setText("Shifu")
    assert "2 Istilah" in dialog._counter_label.text()

    # Non-existent search
    dialog._search_edit.setText("xyz_random_nonexistent")
    assert "0 Istilah" in dialog._counter_label.text()

    # Clear search
    dialog._search_edit.clear()
    total_count = len(empty_glossary_repo.get_entries("ALL"))
    assert f"{total_count} Istilah" in dialog._counter_label.text()


@pytest.mark.ui
def test_glossary_dialog_toggle_delete_and_clear(
    qtbot: QtBot, empty_glossary_repo: SQLiteGlossaryRepository
) -> None:
    dialog = GlossaryDialog(glossary_repo=empty_glossary_repo, ui_lang="id")
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._term_edit.setText("오빠")
    dialog._repl_edit.setText("Oppa")
    dialog._add_btn.click()

    entry = empty_glossary_repo.get_entries("ALL")[0]
    assert entry.enabled is True

    # Find row widget
    row_widget = dialog._rows_layout.itemAt(0).widget()
    assert row_widget is not None

    # Toggle checkbox
    row_widget._check.click()
    entry_updated = empty_glossary_repo.get_entries("ALL")[0]
    assert entry_updated.enabled is False

    # Delete row
    dialog._term_edit.setText("형")
    dialog._repl_edit.setText("Hyung")
    dialog._add_btn.click()
    assert len(empty_glossary_repo.get_entries("ALL")) == 2

    # Clear all with mock confirmation
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        dialog._clear_btn.click()

    assert len(empty_glossary_repo.get_entries("ALL")) == 0
    assert "0 Istilah" in dialog._counter_label.text()
