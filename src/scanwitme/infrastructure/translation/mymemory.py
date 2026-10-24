"""Free in-app translation provider powered by MyMemory REST API.

Provides zero-configuration, in-app translation from Korean, Chinese, Japanese,
and English into Indonesian without requiring API keys or opening a web browser.
"""

from __future__ import annotations

import html
import logging
import re
import time
from typing import Any

import httpx

from scanwitme.domain.errors import (
    InvalidRequestError,
    NetworkError,
    QuotaExceededError,
    TranslationError,
)
from scanwitme.domain.interfaces import TranslationProvider
from scanwitme.domain.models import TranslationResult
from scanwitme.infrastructure.ocr.paddle_ocr import detect_script

logger = logging.getLogger("scanwitme.translation.mymemory")

API_ENDPOINT = "https://api.mymemory.translated.net/get"

LANGUAGE_MAP: dict[str, str] = {
    "ko": "ko",
    "korean": "ko",
    "zh": "zh",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "ch": "zh",
    "chinese": "zh",
    "ja": "ja",
    "japanese": "ja",
    "jp": "ja",
    "en": "en",
    "english": "en",
    "id": "id",
    "indonesian": "id",
}


def _split_into_chunks(text: str, max_chars: int = 400) -> list[str]:
    """Split text into sentence-sized chunks respecting MyMemory GET query constraints."""
    if len(text) <= max_chars:
        return [text]

    # Split on sentence boundaries (newline, period, fullwidth punctuation)
    parts = re.split(r"([\n。！？.!?]+)", text)
    sentences: list[str] = []
    for i in range(0, len(parts) - 1, 2):
        sentences.append(parts[i] + parts[i + 1])
    if len(parts) % 2 == 1 and parts[-1]:
        sentences.append(parts[-1])

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for s in sentences:
        s_len = len(s)
        if current_len + s_len > max_chars and current_chunk:
            chunks.append("".join(current_chunk).strip())
            current_chunk = [s]
            current_len = s_len
        else:
            current_chunk.append(s)
            current_len += s_len

    if current_chunk:
        remaining = "".join(current_chunk).strip()
        if remaining:
            chunks.append(remaining)

    return chunks if chunks else [text]


class MyMemoryTranslationProvider(TranslationProvider):
    """Direct, in-app translation provider using the public MyMemory REST API."""

    def __init__(
        self,
        timeout_seconds: float = 12.0,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        headers = {
            "User-Agent": "ScanWitMe/1.0 (Windows; Manga Translation Assistant)",
        }
        self._client = client or httpx.Client(timeout=self._timeout, headers=headers)
        self._owns_client = client is None

    def close(self) -> None:
        """Close underlying HTTP client connections."""
        if self._owns_client and self._client:
            self._client.close()

    @property
    def provider_id(self) -> str:
        return "free_direct"

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "id",
    ) -> TranslationResult:
        """Translate source text directly into Indonesian in-app."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            raise InvalidRequestError("Source text is empty.")

        # Normalize or auto-detect source language
        norm_source = source_language.lower().strip() if source_language else "auto"
        if norm_source == "auto":
            detected = detect_script(clean_text)
            norm_source = LANGUAGE_MAP.get(detected, "zh")
        else:
            norm_source = LANGUAGE_MAP.get(norm_source, norm_source)

        norm_target = LANGUAGE_MAP.get(target_language.lower().strip(), target_language)

        langpair = f"{norm_source}|{norm_target}"

        start_time = time.perf_counter()
        chunks = _split_into_chunks(clean_text, max_chars=400)
        translated_parts: list[str] = []

        for chunk in chunks:
            part = self._translate_chunk(chunk, langpair)
            translated_parts.append(part)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        final_translated = " ".join(translated_parts).strip()

        return TranslationResult(
            source_text=clean_text,
            translated_text=final_translated,
            source_language=norm_source,
            target_language=norm_target,
            provider=self.provider_id,
            latency_ms=latency_ms,
        )

    def _translate_chunk(self, chunk: str, langpair: str) -> str:
        """Translate a single chunk with bounded retries."""
        params: dict[str, Any] = {
            "q": chunk,
            "langpair": langpair,
        }

        attempt = 0
        backoff = 0.5
        client = self._client

        while True:
            attempt += 1
            try:
                response = client.get(API_ENDPOINT, params=params)
            except httpx.TimeoutException as exc:
                if attempt < self._max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise NetworkError("Koneksi terjemahan timed out.") from exc
            except httpx.RequestError as exc:
                if attempt < self._max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise NetworkError(f"Gagal menghubungi server terjemahan: {exc}") from exc

            status = response.status_code
            if status == 200:
                try:
                    data = response.json()
                except Exception as exc:
                    raise TranslationError(f"Format respon tidak valid: {exc}") from exc

                res_status = data.get("responseStatus")
                res_data = data.get("responseData") or {}
                translated = res_data.get("translatedText", "")

                if (
                    res_status == 429
                    or data.get("quotaFinished") is True
                    or "MYMEMORY WARNING" in translated.upper()
                ):
                    raise QuotaExceededError(
                        "Batas kuota harian terjemahan gratis tercapai. Gunakan Google Translate Web."
                    )

                if not translated and res_status != 200:
                    details = data.get("responseDetails", "Terjemahan kosong")
                    raise TranslationError(f"Gagal menerjemahkan: {details}")

                return html.unescape(translated).strip()

            if status in (429, 502, 503) and attempt < self._max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue

            if status == 429:
                raise QuotaExceededError("Rate limit / kuota server tercapai.")
            raise TranslationError(f"Server terjemahan mengembalikan kode HTTP {status}")

