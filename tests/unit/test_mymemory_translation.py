"""Unit tests for MyMemoryTranslationProvider using mocked HTTP responses."""

from unittest.mock import MagicMock

import httpx
import pytest

from scanwitme.domain.errors import (
    InvalidRequestError,
    NetworkError,
    QuotaExceededError,
)
from scanwitme.infrastructure.translation.mymemory import (
    MyMemoryTranslationProvider,
    _split_into_chunks,
)


@pytest.mark.unit
def test_split_into_chunks() -> None:
    short_text = "Kalimat pendek saja."
    assert _split_into_chunks(short_text, max_chars=100) == [short_text]

    long_text = "Ini kalimat pertama. " * 10 + "Ini kalimat kedua. " * 10
    chunks = _split_into_chunks(long_text, max_chars=120)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 250


@pytest.mark.unit
def test_mymemory_translation_empty_text() -> None:
    provider = MyMemoryTranslationProvider()
    with pytest.raises(InvalidRequestError, match="empty"):
        provider.translate("", source_language="ko")


@pytest.mark.unit
def test_mymemory_translation_success() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "responseStatus": 200,
        "responseData": {
            "translatedText": "Halo dunia &amp; kawan",
        },
    }
    mock_client.get.return_value = mock_response

    provider = MyMemoryTranslationProvider(client=mock_client)
    result = provider.translate("Hello world", source_language="en", target_language="id")

    assert result.source_text == "Hello world"
    # Verifies HTML unescaping
    assert result.translated_text == "Halo dunia & kawan"
    assert result.source_language == "en"
    assert result.target_language == "id"
    assert result.provider == "free_direct"
    assert result.latency_ms > 0


@pytest.mark.unit
def test_mymemory_translation_auto_detect() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "responseStatus": 200,
        "responseData": {
            "translatedText": "Halo dari Korea",
        },
    }
    mock_client.get.return_value = mock_response

    provider = MyMemoryTranslationProvider(client=mock_client)
    result = provider.translate("안녕하세요", source_language="auto", target_language="id")

    assert result.source_language == "ko"
    assert result.translated_text == "Halo dari Korea"


@pytest.mark.unit
def test_mymemory_quota_exceeded() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "responseStatus": 429,
        "responseData": {
            "translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS TODAY",
        },
    }
    mock_client.get.return_value = mock_response

    provider = MyMemoryTranslationProvider(client=mock_client)
    with pytest.raises(QuotaExceededError, match="kuota"):
        provider.translate("Text", source_language="en")


@pytest.mark.unit
def test_mymemory_network_error() -> None:
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    provider = MyMemoryTranslationProvider(client=mock_client, max_retries=1)
    with pytest.raises(NetworkError, match="Gagal menghubungi server"):
        provider.translate("Text", source_language="en")
