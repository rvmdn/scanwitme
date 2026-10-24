"""Web launchers for opening Google Translate and Google Search in the default OS browser."""

from __future__ import annotations

import logging
import urllib.parse
import webbrowser

from scanwitme.domain.errors import InvalidRequestError

logger = logging.getLogger("scanwitme.translation.web_launcher")


class GoogleTranslateWebLauncher:
    """Constructs official Google Translate website URLs and opens them in the default browser."""

    BASE_URL = "https://translate.google.com/"

    @classmethod
    def generate_url(
        cls,
        text: str,
        source_language: str = "ko",
        target_language: str = "id",
    ) -> str:
        """Construct safe, URL-encoded URL for Google Translate website."""
        if not text or not text.strip():
            raise InvalidRequestError("Cannot launch Google Translate with empty text.")

        sl = source_language.lower().strip() if source_language else "auto"
        tl = target_language.lower().strip() if target_language else "id"

        query_params = {
            "sl": sl,
            "tl": tl,
            "text": text.strip(),
            "op": "translate",
        }
        encoded_query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote_plus)
        return f"{cls.BASE_URL}?{encoded_query}"

    @classmethod
    def launch(
        cls,
        text: str,
        source_language: str = "ko",
        target_language: str = "id",
    ) -> str:
        """Open the official Google Translate website in user's default browser."""
        url = cls.generate_url(text, source_language, target_language)
        logger.info("Opening Google Translate in default browser (length: %d chars)", len(text))
        webbrowser.open(url)
        return url


class GoogleSearchLauncher:
    """Constructs official Google Search query URLs and opens them in the default browser."""

    BASE_URL = "https://www.google.com/search"

    @classmethod
    def generate_url(cls, query: str) -> str:
        """Construct safe URL for Google Search."""
        if not query or not query.strip():
            raise InvalidRequestError("Cannot search with empty query.")

        encoded_query = urllib.parse.urlencode(
            {"q": query.strip()}, quote_via=urllib.parse.quote_plus
        )
        return f"{cls.BASE_URL}?{encoded_query}"

    @classmethod
    def launch(cls, query: str) -> str:
        """Open Google Search in user's default browser."""
        url = cls.generate_url(query)
        logger.info("Opening Google Search in default browser: '%s'", query[:30])
        webbrowser.open(url)
        return url


class GoogleLensLauncher:
    """Launches Google Lens in the user's default browser."""

    BASE_URL = "https://lens.google.com/"

    @classmethod
    def launch(cls) -> str:
        """Open Google Lens homepage in default browser."""
        logger.info("Opening Google Lens in default browser")
        webbrowser.open(cls.BASE_URL)
        return cls.BASE_URL
