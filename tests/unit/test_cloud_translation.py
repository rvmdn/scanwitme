"""Unit tests for CloudTranslationV2Provider using mocked HTTP responses."""

from unittest.mock import MagicMock

import httpx
import pytest

from scanwitme.domain.errors import (
    AuthenticationError,
    InvalidRequestError,
    NetworkError,
    QuotaExceededError,
)
from scanwitme.infrastructure.translation.cloud_v2 import CloudTranslationV2Provider


@pytest.mark.unit
def test_cloud_translation_empty_text() -> None:
    provider = CloudTranslationV2Provider(api_key="valid-key")
    with pytest.raises(InvalidRequestError, match="empty"):
        provider.translate("", source_language="ko")


@pytest.mark.unit
def test_cloud_translation_missing_key() -> None:
    provider = CloudTranslationV2Provider(api_key="")
    with pytest.raises(AuthenticationError, match="not configured"):
        provider.translate("안녕하세요", source_language="ko")


@pytest.mark.unit
def test_cloud_translation_success() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "translations": [
                {
                    "translatedText": "Halo dunia &amp; teman",
                    "detectedSourceLanguage": "ko",
                }
            ]
        }
    }
    mock_client.post.return_value = mock_response

    provider = CloudTranslationV2Provider(api_key="test-api-key", client=mock_client)
    result = provider.translate("안녕하세요 세상", source_language="ko", target_language="id")

    assert result.source_text == "안녕하세요 세상"
    # Verify HTML unescaping: &amp; -> &
    assert result.translated_text == "Halo dunia & teman"
    assert result.source_language == "ko"
    assert result.target_language == "id"
    assert result.provider == "cloud_v2"
    assert not result.cached
    assert result.latency_ms > 0


@pytest.mark.unit
def test_cloud_translation_auth_error() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"message": "The request is missing a valid API key."}
    }
    mock_client.post.return_value = mock_response

    provider = CloudTranslationV2Provider(api_key="invalid-key", client=mock_client)
    with pytest.raises(AuthenticationError, match="authentication failed"):
        provider.translate("안녕하세요", source_language="ko")


@pytest.mark.unit
def test_cloud_translation_quota_error() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"error": {"message": "Quota exceeded"}}
    mock_client.post.return_value = mock_response

    provider = CloudTranslationV2Provider(api_key="valid-key", max_retries=1, client=mock_client)
    with pytest.raises(QuotaExceededError, match="quota exceeded"):
        provider.translate("안녕하세요", source_language="ko")


@pytest.mark.unit
def test_cloud_translation_timeout() -> None:
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

    provider = CloudTranslationV2Provider(api_key="valid-key", max_retries=1, client=mock_client)
    with pytest.raises(NetworkError, match="timed out"):
        provider.translate("안녕하세요", source_language="ko")


@pytest.mark.unit
def test_cloud_translation_retry_and_succeed() -> None:
    mock_client = MagicMock()
    # First response: 503 Service Unavailable, Second response: 200 OK
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "data": {
            "translations": [
                {
                    "translatedText": "Berhasil setelah retry",
                }
            ]
        }
    }
    mock_client.post.side_effect = [resp_503, resp_200]

    provider = CloudTranslationV2Provider(api_key="valid-key", max_retries=3, client=mock_client)
    result = provider.translate("성공", source_language="ko", target_language="id")

    assert result.translated_text == "Berhasil setelah retry"
    assert mock_client.post.call_count == 2
