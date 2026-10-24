"""Google Cloud Translation Basic (v2) REST API provider."""

from __future__ import annotations

import html
import logging
import os
import time
from typing import Any

import httpx

from scanwitme.domain.errors import (
    AuthenticationError,
    InvalidRequestError,
    NetworkError,
    QuotaExceededError,
    TranslationError,
)
from scanwitme.domain.interfaces import TranslationProvider
from scanwitme.domain.models import TranslationResult

logger = logging.getLogger("scanwitme.translation.cloud_v2")

API_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class CloudTranslationV2Provider(TranslationProvider):
    """Translates text via Google Cloud Translation Basic (v2) API."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip()
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client = client

    @property
    def provider_id(self) -> str:
        return "cloud_v2"

    def set_api_key(self, api_key: str) -> None:
        self._api_key = api_key.strip()

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "id",
    ) -> TranslationResult:
        """Translate text into Indonesian using Google Cloud Translation Basic v2 API."""
        if not text or not text.strip():
            raise InvalidRequestError("Source text is empty.")

        if not self._api_key:
            raise AuthenticationError(
                "Google Translate API key is not configured. Please set GOOGLE_TRANSLATE_API_KEY or configure it in Settings."
            )

        # Build payload according to official Google Cloud Translation v2 specifications
        payload: dict[str, Any] = {
            "q": [text.strip()],
            "target": target_language,
            "format": "text",
        }

        # If source language is specified and not auto-detect, include it
        if source_language and source_language.lower() != "auto":
            payload["source"] = source_language

        start_time = time.perf_counter()
        response = self._execute_request(payload)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        try:
            data = response.json()
            translations = data.get("data", {}).get("translations", [])
            if not translations:
                raise TranslationError("Response did not contain any translation data.")

            raw_translated = translations[0].get("translatedText", "")
            # Google Cloud Translation v2 can return HTML-escaped characters (e.g. &#39;)
            clean_translated = html.unescape(raw_translated)

            detected_source = translations[0].get("detectedSourceLanguage", source_language)

            return TranslationResult(
                source_text=text.strip(),
                translated_text=clean_translated,
                source_language=detected_source,
                target_language=target_language,
                provider=self.provider_id,
                latency_ms=latency_ms,
            )
        except TranslationError:
            raise
        except Exception as exc:
            logger.exception("Failed to parse translation response")
            raise TranslationError(
                f"Unexpected response format from translation API: {exc}"
            ) from exc

    def _execute_request(self, payload: dict[str, Any]) -> httpx.Response:
        """Execute HTTP POST with bounded exponential backoff for transient errors."""
        url = f"{API_ENDPOINT}?key={self._api_key}"
        attempt = 0
        backoff_delay = 0.5

        client = self._client or httpx.Client(timeout=self._timeout)
        should_close_client = self._client is None

        try:
            while True:
                attempt += 1
                try:
                    response = client.post(url, json=payload)
                except httpx.TimeoutException as exc:
                    if attempt < self._max_retries:
                        time.sleep(backoff_delay)
                        backoff_delay *= 2
                        continue
                    raise NetworkError("Translation request timed out.") from exc
                except httpx.RequestError as exc:
                    if attempt < self._max_retries:
                        time.sleep(backoff_delay)
                        backoff_delay *= 2
                        continue
                    raise NetworkError(f"Network connection failed: {exc}") from exc

                # Check HTTP status codes
                status = response.status_code
                if status == 200:
                    return response

                # Transient errors that can be retried (429 rate limit, 502/503/504 gateway issues)
                if status in (429, 502, 503, 504) and attempt < self._max_retries:
                    logger.warning(
                        "Transient HTTP %d received, retrying attempt %d...", status, attempt
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue

                # Permanent error handling
                if status in (401, 403):
                    raise AuthenticationError(
                        "Google Cloud API authentication failed. Please check your API key."
                    )
                elif status == 429:
                    raise QuotaExceededError(
                        "Google Cloud Translation API quota exceeded or rate limit reached."
                    )
                elif status == 400:
                    try:
                        err_detail = response.json().get("error", {}).get("message", "Bad Request")
                    except Exception:
                        err_detail = response.text
                    raise InvalidRequestError(f"Invalid translation request: {err_detail}")
                else:
                    raise TranslationError(f"Google Cloud Translation API returned HTTP {status}")
        finally:
            if should_close_client:
                client.close()
