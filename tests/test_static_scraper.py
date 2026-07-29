from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from src.lead_intelligence.static_scraper import (
    clean_link,
    extract_emails,
    extract_links,
    extract_phone_numbers,
    extract_visible_text,
    normalise_domain,
    parse_page,
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
