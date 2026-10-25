"""Unit tests for SQLiteHistoryRepository."""

from __future__ import annotations

import time

from scanwitme.domain.models import HistoryItem
from scanwitme.infrastructure.history.sqlite_history import SQLiteHistoryRepository


def test_history_repository_add_and_retrieve() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    item1 = HistoryItem(
        id="item-1",
        source_text="こんにちは世界",
        translated_text="Halo dunia",
        source_lang="JA",
        target_lang="ID",
        timestamp=time.time() - 10,
        is_favorite=False,
    )
    repo.add_item(item1)

    items = repo.get_items("ALL")
    assert len(items) == 1
    assert items[0].id == "item-1"
    assert items[0].source_text == "こんにちは世界"
    assert items[0].translated_text == "Halo dunia"
    assert not items[0].is_favorite


def test_history_repository_deduplication_preserves_favorite() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    item1 = HistoryItem(
        id="item-1",
        source_text="おはよう",
        translated_text="Selamat pagi",
        source_lang="JA",
        target_lang="ID",
        timestamp=1000.0,
        is_favorite=True,
    )
    repo.add_item(item1)

    # Re-scan with identical source_text but is_favorite=False
    item2 = HistoryItem(
        id="item-2",
        source_text="おはよう",
        translated_text="Selamat pagi!",
        source_lang="JA",
        target_lang="ID",
        timestamp=2000.0,
        is_favorite=False,
    )
    repo.add_item(item2)

    items = repo.get_items("ALL")
    assert len(items) == 1
    # Favorite state must remain True
    assert items[0].is_favorite is True
    assert items[0].translated_text == "Selamat pagi!"
    assert items[0].timestamp == 2000.0


def test_history_repository_filtering_by_language_and_favorites() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    repo.add_item(HistoryItem("1", "テスト1", "Tes 1", "JA", "ID", 100.0, is_favorite=True))
    repo.add_item(HistoryItem("2", "안녕하세요", "Halo", "KO", "ID", 200.0, is_favorite=False))
    repo.add_item(HistoryItem("3", "你好", "Halo", "ZH", "ID", 300.0, is_favorite=True))
    repo.add_item(HistoryItem("4", "Hello", "Halo", "EN", "ID", 400.0, is_favorite=False))

    all_items = repo.get_items("ALL")
    assert len(all_items) == 4

    fav_items = repo.get_items("FAV")
    assert len(fav_items) == 2
    assert {i.id for i in fav_items} == {"1", "3"}

    ja_items = repo.get_items("JA")
    assert len(ja_items) == 1
    assert ja_items[0].id == "1"

    ko_items = repo.get_items("KO")
    assert len(ko_items) == 1
    assert ko_items[0].id == "2"

    zh_items = repo.get_items("ZH")
    assert len(zh_items) == 1
    assert zh_items[0].id == "3"

    en_items = repo.get_items("EN")
    assert len(en_items) == 1
    assert en_items[0].id == "4"


def test_history_repository_search_query() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    repo.add_item(
        HistoryItem("1", "すごい技だ！", "Jurus yang hebat!", "JA", "ID", 100.0, is_favorite=False)
    )
    repo.add_item(
        HistoryItem("2", "逃げろ！", "Cepat kabur!", "JA", "ID", 200.0, is_favorite=False)
    )

    # Search in original
    results = repo.get_items("ALL", query="すごい")
    assert len(results) == 1
    assert results[0].id == "1"

    # Search in translation
    results = repo.get_items("ALL", query="kabur")
    assert len(results) == 1
    assert results[0].id == "2"

    # Search non-matching
    results = repo.get_items("ALL", query="tidakada")
    assert len(results) == 0


def test_history_repository_toggle_favorite_and_delete() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    repo.add_item(HistoryItem("item-a", "すごい", "Hebat", "JA", "ID", 100.0, is_favorite=False))

    new_fav = repo.toggle_favorite("item-a")
    assert new_fav is True
    assert repo.get_items("FAV")[0].id == "item-a"

    new_fav = repo.toggle_favorite("item-a")
    assert new_fav is False
    assert len(repo.get_items("FAV")) == 0

    # Non-existent item
    assert repo.toggle_favorite("non-existent") is False

    # Delete item
    repo.delete_item("item-a")
    assert len(repo.get_items("ALL")) == 0


def test_history_repository_clear_all_and_export() -> None:
    repo = SQLiteHistoryRepository(db_path=":memory:")

    # Empty export
    empty_export = repo.export_formatted()
    assert "ScanWitMe PC — Comic Dialogue History" in empty_export
    assert "Total   : 0 Dialogues" in empty_export
    assert "Tidak ada riwayat" in empty_export

    # Add items
    repo.add_item(
        HistoryItem("1", "テスト1", "Hasil 1", "JA", "ID", 1700000000.0, is_favorite=True)
    )
    repo.add_item(
        HistoryItem("2", "テスト2", "Hasil 2", "JA", "ID", 1700000100.0, is_favorite=False)
    )

    export_text = repo.export_formatted("ALL")
    assert "Total   : 2 Dialogues" in export_text
    assert "[⭐ FAVORIT]" in export_text
    assert "RAW   : テスト1" in export_text
    assert "TRANS : Hasil 1" in export_text

    # Clear all
    repo.clear_all()
    assert len(repo.get_items("ALL")) == 0
