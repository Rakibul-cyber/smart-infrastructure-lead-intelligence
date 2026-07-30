from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

import src.lead_intelligence.static_scraper as static_scraper_module
from src.lead_intelligence.static_scraper import (
    clean_link,
    download_page,
    extract_emails,
    extract_links,
    extract_phone_numbers,
    extract_visible_text,
    normalise_domain,
    parse_page,
    scrape_page,
)


FIXTURE_PATH = Path(
    "tests/fixtures/sample_municipality.html"
)

BASE_URL = "https://example-city.de"


def load_fixture_html() -> str:
    """Load the fictional municipality HTML fixture."""

    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_normalise_domain_removes_www() -> None:
    """www and non-www domains should be treated as equal."""

    assert (
        normalise_domain(
            "https://www.example-city.de/contact"
        )
        == "example-city.de"
    )

    assert (
        normalise_domain(
            "https://example-city.de/contact"
        )
        == "example-city.de"
    )


def test_clean_link_converts_relative_url() -> None:
    """A relative URL should become an absolute URL."""

    result = clean_link(
        base_url=BASE_URL,
        href="/kontakt",
    )

    assert result == "https://example-city.de/kontakt"


def test_clean_link_removes_fragment() -> None:
    """URL fragments should not create duplicate crawl targets."""

    result = clean_link(
        base_url=BASE_URL,
        href="/kontakt#telephone",
    )

    assert result == "https://example-city.de/kontakt"


def test_clean_link_rejects_non_web_links() -> None:
    """Communication and script links are not crawlable pages."""

    assert clean_link(BASE_URL, "mailto:test@example.com") is None
    assert clean_link(BASE_URL, "tel:+4930123456") is None
    assert clean_link(BASE_URL, "javascript:void(0)") is None
    assert clean_link(BASE_URL, "data:text/plain,hello") is None
    assert clean_link(BASE_URL, "#contact") is None


def test_extract_visible_text_removes_script_and_style() -> None:
    """Visible text should not include CSS or JavaScript content."""

    html = load_fixture_html()
    soup = BeautifulSoup(html, "lxml")

    visible_text = extract_visible_text(soup)

    assert "Smart Infrastructure and Energy Services" in visible_text
    assert "console.log" not in visible_text
    assert "font-family" not in visible_text


def test_extract_emails_from_text_and_mailto() -> None:
    """Emails should be detected from text and mailto links."""

    html = load_fixture_html()
    soup = BeautifulSoup(html, "lxml")

    visible_text = extract_visible_text(soup)
    emails = extract_emails(soup, visible_text)

    assert emails == [
        "energy.office@example-city.de",
        "infrastructure.office@example-city.de",
    ]


def test_extract_phone_numbers_from_text_and_tel() -> None:
    """Phone numbers should be detected from text and tel links."""

    html = load_fixture_html()
    soup = BeautifulSoup(html, "lxml")

    visible_text = extract_visible_text(soup)

    phone_numbers = extract_phone_numbers(
        soup,
        visible_text,
    )

    assert "+493012345679" in phone_numbers
    assert "030 1234 5678" in phone_numbers


def test_extract_links_separates_internal_and_external() -> None:
    """External URLs must not be classified as internal."""

    html = load_fixture_html()
    soup = BeautifulSoup(html, "lxml")

    absolute_links, internal_links, contact_links = extract_links(
        soup=soup,
        base_url=BASE_URL,
    )

    assert (
        "https://regional-energy.example/partners"
        in absolute_links
    )

    assert (
        "https://regional-energy.example/partners"
        not in internal_links
    )

    assert (
        "https://example-city.de/kontakt"
        in internal_links
    )

    assert (
        "https://www.example-city.de/impressum"
        in internal_links
    )

    assert (
        "https://example-city.de/kontakt"
        in contact_links
    )


def test_parse_page_returns_complete_result() -> None:
    """parse_page should return all expected structured values."""

    html = load_fixture_html()

    result = parse_page(
        url=BASE_URL,
        html=html,
    )

    assert result.url == BASE_URL

    assert (
        result.title
        == "Example City Infrastructure Office"
    )

    assert (
        result.main_heading
        == "Smart Infrastructure and Energy Services"
    )

    assert len(result.emails) == 2
    assert len(result.phone_numbers) == 2
    assert len(result.absolute_links) == 5
    assert len(result.internal_links) == 4
    assert len(result.contact_links) == 4


def test_download_page_passes_configured_timeout_and_user_agent(
    monkeypatch,
) -> None:
    """download_page should pass timeout and User-Agent to requests.get."""

    captured_request: dict[str, object] = {}

    class FakeResponse:
        text = "<html><body>Example</body></html>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        captured_request["url"] = url
        captured_request["headers"] = headers
        captured_request["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        static_scraper_module.requests,
        "get",
        fake_get,
    )

    html = download_page(
        "https://example-city.de",
        timeout=7.5,
        user_agent="ConfiguredAgent/1.0",
    )

    assert html == "<html><body>Example</body></html>"
    assert captured_request["url"] == "https://example-city.de"
    assert captured_request["timeout"] == 7.5
    assert captured_request["headers"] == {
        "User-Agent": "ConfiguredAgent/1.0"
    }


def test_scrape_page_forwards_timeout_and_user_agent(
    monkeypatch,
) -> None:
    """scrape_page should forward HTTP configuration to download_page."""

    captured_call: dict[str, object] = {}

    def fake_download_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
    ) -> str:
        captured_call["url"] = url
        captured_call["timeout"] = timeout
        captured_call["user_agent"] = user_agent
        return (
            "<html><head><title>Configured</title></head>"
            "<body><h1>Configured Page</h1></body></html>"
        )

    monkeypatch.setattr(
        static_scraper_module,
        "download_page",
        fake_download_page,
    )

    result = scrape_page(
        "https://example-city.de",
        timeout=4.0,
        user_agent="ConfiguredAgent/2.0",
    )

    assert result.title == "Configured"
    assert captured_call == {
        "url": "https://example-city.de",
        "timeout": 4.0,
        "user_agent": "ConfiguredAgent/2.0",
    }


def test_scrape_page_legacy_call_without_config_still_works(
    monkeypatch,
) -> None:
    """scrape_page(url) should remain backward compatible."""

    def fake_download_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
    ) -> str:
        return (
            "<html><head><title>Legacy</title></head>"
            "<body><h1>Legacy Page</h1></body></html>"
        )

    monkeypatch.setattr(
        static_scraper_module,
        "download_page",
        fake_download_page,
    )

    result = scrape_page("https://example-city.de")

    assert result.title == "Legacy"
