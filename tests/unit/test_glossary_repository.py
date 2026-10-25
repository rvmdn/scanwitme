"""Unit tests for SQLiteGlossaryRepository."""

from __future__ import annotations

from scanwitme.domain.models import GlossaryEntry
from scanwitme.infrastructure.glossary.sqlite_glossary import SQLiteGlossaryRepository


def test_glossary_add_and_retrieve() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")

    entry = GlossaryEntry(
        id="entry-1",
        term="宗主",
        replacement="Ketua Sekte",
        language="ZH",
        enabled=True,
    )
    repo.add_entry(entry)

    entries = repo.get_entries("ALL")
    assert len(entries) == 1
    assert entries[0].term == "宗主"
    assert entries[0].replacement == "Ketua Sekte"
    assert entries[0].language == "ZH"
    assert entries[0].enabled is True


def test_glossary_load_presets() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")

    count = repo.load_presets()
    assert count > 20

    entries = repo.get_entries("ALL")
    terms = {e.term for e in entries}

    # Verify key comic terms from Manhwa, Manga, and Manhua
    assert "선배" in terms
    assert "先輩" in terms
    assert "宗主" in terms
    assert "丹田" in terms
    assert "senior" in terms

    # Test load presets again without overwrite
    assert repo.load_presets(overwrite=False) == 0


def test_glossary_apply_glossary_cjk() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")
    repo.add_entry(GlossaryEntry("1", "선배", "Sunbae", "KO"))
    repo.add_entry(GlossaryEntry("2", "宗主", "Ketua Sekte", "ZH"))

    # Test Korean replacement
    text_ko = "안녕하세요 선배님!"
    replaced_ko = repo.apply_glossary(text_ko, language="KO")
    assert "Sunbae" in replaced_ko
    assert "선배" not in replaced_ko

    # Test Chinese replacement
    text_zh = "参见宗主大人！"
    replaced_zh = repo.apply_glossary(text_zh, language="ZH")
    assert "Ketua Sekte" in replaced_zh
    assert "宗主" not in replaced_zh


def test_glossary_apply_glossary_word_boundary() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")
    repo.add_entry(GlossaryEntry("1", "senior", "Sunbae", "KO"))

    # "senior" must be replaced, but not "seniors"
    text = "Halo senior kita, ini para seniors."
    replaced = repo.apply_glossary(text, language="KO")
    assert "Halo Sunbae kita, ini para seniors." == replaced


def test_glossary_toggle_and_delete() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")
    repo.add_entry(GlossaryEntry("1", "hyung", "Hyung", "KO", enabled=True))

    text = "Apa kabar hyung?"
    assert repo.apply_glossary(text, language="KO") == "Apa kabar Hyung?"

    # Toggle disable
    new_state = repo.toggle_enabled("1")
    assert new_state is False

    # Disabled term must NOT be replaced
    assert repo.apply_glossary(text, language="KO") == "Apa kabar hyung?"

    # Re-enable
    assert repo.toggle_enabled("1") is True
    assert repo.apply_glossary(text, language="KO") == "Apa kabar Hyung?"

    # Delete
    repo.delete_entry("1")
    assert len(repo.get_entries("ALL")) == 0
    assert repo.apply_glossary(text, language="KO") == "Apa kabar hyung?"


def test_glossary_filtering_and_search() -> None:
    repo = SQLiteGlossaryRepository(db_path=":memory:")
    repo.add_entry(GlossaryEntry("1", "선배", "Sunbae", "KO"))
    repo.add_entry(GlossaryEntry("2", "先輩", "Senpai", "JA"))
    repo.add_entry(GlossaryEntry("3", "宗主", "Ketua Sekte", "ZH"))

    # Language filter
    ko_entries = repo.get_entries(language="KO")
    assert len(ko_entries) == 1
    assert ko_entries[0].term == "선배"

    ja_entries = repo.get_entries(language="JA")
    assert len(ja_entries) == 1
    assert ja_entries[0].term == "先輩"

    # Search query
    search_res = repo.get_entries(query="Ketua")
    assert len(search_res) == 1
    assert search_res[0].term == "宗主"

    # Clear all
    repo.clear_all()
    assert len(repo.get_entries()) == 0
