"""Unit tests for GoogleTranslateWebLauncher and GoogleSearchLauncher."""

import pytest

from scanwitme.domain.errors import InvalidRequestError
from scanwitme.infrastructure.translation.web_launcher import (
    GoogleSearchLauncher,
    GoogleTranslateWebLauncher,
)


@pytest.mark.unit
def test_web_launcher_url_generation() -> None:
    text = "안녕하세요! 반갑습니다."
    url = GoogleTranslateWebLauncher.generate_url(text, source_language="ko", target_language="id")

    assert url.startswith("https://translate.google.com/?")
    assert "sl=ko" in url
    assert "tl=id" in url
    assert "op=translate" in url
    # Verify proper URL encoding (no raw Korean characters in URL)
    assert "%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94" in url


@pytest.mark.unit
def test_web_launcher_empty_text_error() -> None:
    with pytest.raises(InvalidRequestError, match="empty"):
        GoogleTranslateWebLauncher.generate_url("   ")


@pytest.mark.unit
def test_google_search_launcher_url() -> None:
    query = "도깨비 만화"
    url = GoogleSearchLauncher.generate_url(query)

    assert url.startswith("https://www.google.com/search?")
    assert "q=" in url


@pytest.mark.unit
def test_google_search_empty_query() -> None:
    with pytest.raises(InvalidRequestError, match="empty"):
        GoogleSearchLauncher.generate_url("")


@pytest.mark.unit
def test_google_lens_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    from scanwitme.infrastructure.translation.web_launcher import GoogleLensLauncher

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    res = GoogleLensLauncher.launch()
    assert res == "https://lens.google.com/"
    assert opened == ["https://lens.google.com/"]
