"""Thread-safe SQLite repository for comic term dictionary and custom glossary."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
import uuid
from pathlib import Path

from scanwitme.domain.interfaces import GlossaryRepository
from scanwitme.domain.models import GlossaryEntry

logger = logging.getLogger("scanwitme.glossary")

DEFAULT_PRESETS: list[dict[str, str]] = [
    # Manhwa (Korean) honorifics & gaming terms
    {"term": "선배", "replacement": "Sunbae", "language": "KO"},
    {"term": "후배", "replacement": "Hubae", "language": "KO"},
    {"term": "형", "replacement": "Hyung", "language": "KO"},
    {"term": "오빠", "replacement": "Oppa", "language": "KO"},
    {"term": "누나", "replacement": "Noona", "language": "KO"},
    {"term": "언니", "replacement": "Unnie", "language": "KO"},
    {"term": "헌터", "replacement": "Hunter", "language": "KO"},
    {"term": "마나", "replacement": "Mana", "language": "KO"},
    {"term": "던전", "replacement": "Dungeon", "language": "KO"},
    {"term": "게이트", "replacement": "Gate", "language": "KO"},
    {"term": "senior", "replacement": "Sunbae", "language": "KO"},
    {"term": "atasan", "replacement": "Sunbae", "language": "KO"},
    {"term": "pemburu", "replacement": "Hunter", "language": "KO"},
    {"term": "penguasa dungeon", "replacement": "Dungeon Master", "language": "KO"},
    {"term": "inti mana", "replacement": "Mana Core", "language": "KO"},
    # Manga (Japanese) terms
    {"term": "先輩", "replacement": "Senpai", "language": "JA"},
    {"term": "せんぱい", "replacement": "Senpai", "language": "JA"},
    {"term": "後輩", "replacement": "Kouhai", "language": "JA"},
    {"term": "先生", "replacement": "Sensei", "language": "JA"},
    {"term": "仲間", "replacement": "Nakama", "language": "JA"},
    {"term": "お兄ちゃん", "replacement": "Onii-chan", "language": "JA"},
    {"term": "お姉ちゃん", "replacement": "Onee-chan", "language": "JA"},
    {"term": "senpai", "replacement": "Senpai", "language": "JA"},
    {"term": "sensei", "replacement": "Sensei", "language": "JA"},
    {"term": "nakama", "replacement": "Nakama", "language": "JA"},
    # Manhua & Wuxia / Xianxia (Chinese) terms
    {"term": "宗主", "replacement": "Ketua Sekte", "language": "ZH"},
    {"term": "师父", "replacement": "Shifu", "language": "ZH"},
    {"term": "师傅", "replacement": "Shifu", "language": "ZH"},
    {"term": "师兄", "replacement": "Kakak Seperguruan (Shixiong)", "language": "ZH"},
    {"term": "师姐", "replacement": "Kakak Seperguruan (Shijie)", "language": "ZH"},
    {"term": "师弟", "replacement": "Adik Seperguruan (Shidi)", "language": "ZH"},
    {"term": "师妹", "replacement": "Adik Seperguruan (Shimei)", "language": "ZH"},
    {"term": "丹田", "replacement": "Dantian", "language": "ZH"},
    {"term": "真气", "replacement": "Qi Sejati", "language": "ZH"},
    {"term": "筑基", "replacement": "Tahap Pondasi (Foundation Establishment)", "language": "ZH"},
    {"term": "金丹", "replacement": "Inti Emas (Golden Core)", "language": "ZH"},
    {"term": "元婴", "replacement": "Nascent Soul", "language": "ZH"},
    {"term": "渡劫", "replacement": "Tribulasi", "language": "ZH"},
    {"term": "tetua sekte", "replacement": "Tetua Sekte", "language": "ZH"},
    {"term": "pemimpin sekte", "replacement": "Ketua Sekte", "language": "ZH"},
    {"term": "inti emas", "replacement": "Golden Core (Inti Emas)", "language": "ZH"},
    {"term": "jiwa baru", "replacement": "Nascent Soul", "language": "ZH"},
]


class SQLiteGlossaryRepository(GlossaryRepository):
    """SQLite-backed glossary repository with thread-local connections."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._local = threading.local()

        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=10.0,
            )
            if self._db_path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_glossary (
                    id TEXT PRIMARY KEY,
                    term TEXT NOT NULL UNIQUE,
                    replacement TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'ALL',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    case_sensitive INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_glossary_term ON custom_glossary(term);")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_glossary_lang ON custom_glossary(language);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_glossary_enabled ON custom_glossary(enabled);"
            )

    def add_entry(self, entry: GlossaryEntry) -> None:
        """Add or update glossary entry by term."""
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO custom_glossary (id, term, replacement, language, enabled, case_sensitive)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(term) DO UPDATE SET
                    replacement = excluded.replacement,
                    language = excluded.language,
                    enabled = excluded.enabled,
                    case_sensitive = excluded.case_sensitive;
                """,
                (
                    entry.id,
                    entry.term.strip(),
                    entry.replacement.strip(),
                    entry.language.upper(),
                    1 if entry.enabled else 0,
                    1 if entry.case_sensitive else 0,
                ),
            )

    def update_entry(self, entry: GlossaryEntry) -> None:
        """Update existing glossary entry."""
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                UPDATE custom_glossary
                SET term = ?, replacement = ?, language = ?, enabled = ?, case_sensitive = ?
                WHERE id = ?;
                """,
                (
                    entry.term.strip(),
                    entry.replacement.strip(),
                    entry.language.upper(),
                    1 if entry.enabled else 0,
                    1 if entry.case_sensitive else 0,
                    entry.id,
                ),
            )

    def delete_entry(self, entry_id: str) -> None:
        """Delete glossary entry by id."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM custom_glossary WHERE id = ?;", (entry_id,))

    def get_entries(
        self,
        language: str = "ALL",
        enabled_only: bool = False,
        query: str = "",
    ) -> list[GlossaryEntry]:
        """Retrieve glossary entries with optional language, status, and search filters."""
        conn = self._get_connection()
        clauses: list[str] = []
        params: list[object] = []

        lang_upper = language.upper()
        if lang_upper in ("JA", "KO", "ZH", "EN"):
            clauses.append("(language = ? OR language = 'ALL')")
            params.append(lang_upper)

        if enabled_only:
            clauses.append("enabled = 1")

        if query.strip():
            clauses.append("(term LIKE ? OR replacement LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern])

        sql = "SELECT * FROM custom_glossary"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY LENGTH(term) DESC, term ASC;"

        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        return [
            GlossaryEntry(
                id=row["id"],
                term=row["term"],
                replacement=row["replacement"],
                language=row["language"],
                enabled=bool(row["enabled"]),
                case_sensitive=bool(row["case_sensitive"]),
            )
            for row in rows
        ]

    def toggle_enabled(self, entry_id: str) -> bool:
        """Toggle active state of a glossary entry."""
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT enabled FROM custom_glossary WHERE id = ?;", (entry_id,))
            row = cursor.fetchone()
            if not row:
                return False
            new_state = 0 if row["enabled"] else 1
            cursor.execute(
                "UPDATE custom_glossary SET enabled = ? WHERE id = ?;", (new_state, entry_id)
            )
            return bool(new_state)

    def apply_glossary(self, text: str, language: str = "ALL") -> str:
        """Apply enabled glossary replacements to text."""
        if not text or not text.strip():
            return text

        entries = self.get_entries(language=language, enabled_only=True)
        if not entries:
            return text

        res = text
        for entry in entries:
            term = entry.term.strip()
            if not term:
                continue

            flags = 0 if entry.case_sensitive else re.IGNORECASE
            term_escaped = re.escape(term)

            # Use word boundaries for ASCII words to avoid accidental substring matches
            if re.match(r"^[A-Za-z0-9_ ]+$", term):
                pattern = rf"\b{term_escaped}\b"
            else:
                pattern = term_escaped

            res = re.sub(pattern, entry.replacement, res, flags=flags)

        return res

    def load_presets(self, overwrite: bool = False) -> int:
        """Load default manga/manhwa/wuxia glossary terms, returning count added."""
        conn = self._get_connection()
        count = 0
        with conn:
            cursor = conn.cursor()
            for p in DEFAULT_PRESETS:
                cursor.execute(
                    "SELECT id FROM custom_glossary WHERE term = ? LIMIT 1;", (p["term"],)
                )
                exists = cursor.fetchone() is not None
                if exists and not overwrite:
                    continue
                entry_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO custom_glossary (id, term, replacement, language, enabled, case_sensitive)
                    VALUES (?, ?, ?, ?, 1, 0)
                    ON CONFLICT(term) DO UPDATE SET
                        replacement = excluded.replacement,
                        language = excluded.language;
                    """,
                    (entry_id, p["term"], p["replacement"], p["language"]),
                )
                count += 1
        return count

    def clear_all(self) -> None:
        """Remove all glossary entries."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM custom_glossary;")
