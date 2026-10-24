"""Thread-safe SQLite persistent cache for translation results."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path

from scanwitme.domain.interfaces import CacheRepository
from scanwitme.domain.models import TranslationResult

logger = logging.getLogger("scanwitme.cache")


class SQLiteCacheRepository(CacheRepository):
    """SQLite-backed cache repository with thread-local connections and TTL support."""

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
            # Enable Write-Ahead Logging for concurrency if on disk
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
                CREATE TABLE IF NOT EXISTS translations (
                    cache_key TEXT PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON translations(cache_key);")

    def get(self, key: str) -> TranslationResult | None:
        """Look up cached translation by key. Returns None if absent or expired."""
        conn = self._get_connection()
        now = time.time()
        cursor = conn.execute(
            """
            SELECT source_text, translated_text, source_lang, target_lang, provider, expires_at
            FROM translations
            WHERE cache_key = ?
            """,
            (key,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Check TTL expiration
        expires_at = row["expires_at"]
        if expires_at is not None and now > expires_at:
            # Purge expired entry
            with conn:
                conn.execute("DELETE FROM translations WHERE cache_key = ?", (key,))
            return None

        return TranslationResult(
            source_text=row["source_text"],
            translated_text=row["translated_text"],
            source_language=row["source_lang"],
            target_language=row["target_lang"],
            provider=row["provider"],
            cached=True,
            latency_ms=0.0,
        )

    def set(self, key: str, result: TranslationResult, ttl_seconds: int | None = None) -> None:
        """Store translation result in cache with optional TTL."""
        conn = self._get_connection()
        now = time.time()
        expires_at = (now + ttl_seconds) if ttl_seconds else None

        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO translations
                (cache_key, source_text, translated_text, source_lang, target_lang, provider, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    key,
                    result.source_text,
                    result.translated_text,
                    result.source_language,
                    result.target_language,
                    result.provider,
                    now,
                    expires_at,
                ),
            )
        logger.debug("Cached translation for key: %s (TTL: %s)", key[:12], ttl_seconds)

    def clear(self) -> None:
        """Clear all entries from cache table."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM translations;")

        if self._db_path != ":memory:":
            try:
                prev_isolation = conn.isolation_level
                conn.isolation_level = None
                conn.execute("VACUUM;")
                conn.isolation_level = prev_isolation
            except Exception as exc:
                logger.debug("Failed to vacuum SQLite cache: %s", exc)

        logger.info("Translation cache cleared.")
