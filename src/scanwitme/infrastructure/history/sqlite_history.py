"""Thread-safe SQLite repository for comic dialogue scan history."""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from scanwitme.domain.interfaces import HistoryRepository
from scanwitme.domain.models import HistoryItem

logger = logging.getLogger("scanwitme.history")


class SQLiteHistoryRepository(HistoryRepository):
    """SQLite-backed history repository with thread-local connections and bookmark support."""

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
                CREATE TABLE IF NOT EXISTS dialogue_history (
                    id TEXT PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    timestamp REAL NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hist_source ON dialogue_history(source_text);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hist_fav ON dialogue_history(is_favorite);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hist_time ON dialogue_history(timestamp DESC);"
            )

    def add_item(self, item: HistoryItem) -> None:
        """Add or update history item, preserving existing favorite status."""
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, is_favorite FROM dialogue_history WHERE source_text = ? LIMIT 1;",
                (item.source_text,),
            )
            row = cursor.fetchone()
            if row:
                existing_fav = bool(row["is_favorite"])
                keep_fav = 1 if (item.is_favorite or existing_fav) else 0
                cursor.execute(
                    """
                    UPDATE dialogue_history
                    SET translated_text = ?, source_lang = ?, target_lang = ?, is_favorite = ?, timestamp = ?
                    WHERE id = ?;
                    """,
                    (
                        item.translated_text,
                        item.source_lang,
                        item.target_lang,
                        keep_fav,
                        item.timestamp,
                        row["id"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO dialogue_history (id, source_text, translated_text, source_lang, target_lang, is_favorite, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item.id,
                        item.source_text,
                        item.translated_text,
                        item.source_lang,
                        item.target_lang,
                        1 if item.is_favorite else 0,
                        item.timestamp,
                    ),
                )

    def get_items(self, filter_type: str = "ALL", query: str = "") -> list[HistoryItem]:
        """Retrieve items filtered by category and search query."""
        conn = self._get_connection()
        clauses = []
        params: list[object] = []

        if filter_type == "FAV":
            clauses.append("is_favorite = 1")
        elif filter_type in ("JA", "KO", "ZH", "EN"):
            clauses.append("UPPER(source_lang) = ?")
            params.append(filter_type)

        if query.strip():
            clauses.append("(source_text LIKE ? OR translated_text LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern])

        sql = "SELECT * FROM dialogue_history"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp DESC;"

        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        return [
            HistoryItem(
                id=row["id"],
                source_text=row["source_text"],
                translated_text=row["translated_text"],
                source_lang=row["source_lang"],
                target_lang=row["target_lang"],
                timestamp=row["timestamp"],
                is_favorite=bool(row["is_favorite"]),
            )
            for row in rows
        ]

    def toggle_favorite(self, item_id: str) -> bool:
        """Toggle favorite status of item."""
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT is_favorite FROM dialogue_history WHERE id = ?;",
                (item_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False
            new_state = 0 if row["is_favorite"] else 1
            cursor.execute(
                "UPDATE dialogue_history SET is_favorite = ? WHERE id = ?;",
                (new_state, item_id),
            )
            return bool(new_state)

    def delete_item(self, item_id: str) -> None:
        """Delete dialogue item by id."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM dialogue_history WHERE id = ?;", (item_id,))

    def clear_all(self) -> None:
        """Delete all dialogue history."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM dialogue_history;")

    def export_formatted(self, filter_type: str = "ALL") -> str:
        """Generate formatted plain text export."""
        items = self.get_items(filter_type=filter_type)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        sb: list[str] = [
            "═══════════════════════════════════════",
            "ScanWitMe PC — Comic Dialogue History",
            f"Exported: {now_str}",
            f"Total   : {len(items)} Dialogues",
            "═══════════════════════════════════════\n",
        ]

        if not items:
            sb.append("(Tidak ada riwayat dialog untuk diekspor)\n")
        else:
            for idx, item in enumerate(items, start=1):
                fav_mark = " [⭐ FAVORIT]" if item.is_favorite else ""
                item_time = datetime.fromtimestamp(item.timestamp).strftime("%Y-%m-%d %H:%M")
                sb.append(
                    f"[{idx}] {item.source_lang} → {item.target_lang}{fav_mark} | {item_time}"
                )
                sb.append(f"RAW   : {item.source_text}")
                sb.append(f"TRANS : {item.translated_text}")
                sb.append("---------------------------------------")

        sb.append("\nGenerated by ScanWitMe PC — AI Comic Screen Translator")
        return "\n".join(sb)
