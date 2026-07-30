from __future__ import annotations

from pathlib import Path

import pytest
import requests

import src.lead_intelligence.crawler as crawler_module
from src.lead_intelligence.crawler import (
    crawl_website,
    normalise_crawl_url,
)
from src.lead_intelligence.static_scraper import ScrapedPage, parse_page


FIXTURE_DIR = Path("tests/fixtures")
BASE_URL = "https://example-city.de/"
CONTACT_URL = "https://example-city.de/kontakt"
INFRASTRUCTURE_URL = "https://example-city.de/infrastructure"
MISSING_URL = "https://example-city.de/missing"


def install_fake_scraper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace network scraping with deterministic fixture parsing."""

    fixture_map = {
        BASE_URL: "crawler_home.html",
        CONTACT_URL: "crawler_contact.html",
        INFRASTRUCTURE_URL: "crawler_infrastructure.html",
    }

    def fake_scrape_page(url: str) -> ScrapedPage:
        normalized_url = normalise_crawl_url(url)

        if normalized_url == MISSING_URL:
            raise requests.RequestException("fictional missing page")

        fixture_name = fixture_map.get(normalized_url)

        if fixture_name is None:
            raise AssertionError(f"Unexpected crawl URL: {url}")

        html = (FIXTURE_DIR / fixture_name).read_text(
            encoding="utf-8",
        )

        return parse_page(
            url=normalized_url,
            html=html,
        )

    monkeypatch.setattr(
        crawler_module,
        "scrape_page",
        fake_scrape_page,
    )


def test_start_page_is_visited_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The homepage should be the first successful crawl result."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=3)

    assert result.visited_urls[0] == BASE_URL


def test_contact_page_is_prioritized_before_general_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contact-related links should be queued before other internal links."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=3)

    assert result.visited_urls == [
        BASE_URL,
        CONTACT_URL,
        INFRASTRUCTURE_URL,
    ]


def test_external_links_are_never_visited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The crawler should stay on the start domain."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert "https://external.example/report" not in result.visited_urls
    assert all(
        failure.url != "https://external.example/report"
        for failure in result.failed_pages
    )


def test_duplicate_links_and_loops_do_not_duplicate_visits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loops and duplicate URL spellings should not create repeat visits."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.visited_urls.count(BASE_URL) == 1
    assert result.visited_urls.count(CONTACT_URL) == 1
    assert result.visited_urls.count(INFRASTRUCTURE_URL) == 1


def test_max_pages_limits_successful_page_visits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """max_pages should limit successful visits, not queued candidates."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=2)

    assert result.visited_urls == [
        BASE_URL,
        CONTACT_URL,
    ]
    assert result.failed_pages == []


def test_emails_from_multiple_pages_are_combined_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Emails from all successful pages should be returned once."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.emails == [
        "contact.office@example-city.de",
        "roads.office@example-city.de",
    ]


def test_phone_numbers_from_multiple_pages_are_combined_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phone numbers from all successful pages should be returned once."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.phone_numbers == [
        "030 1111 2222",
        "030 3333 4444",
    ]


def test_contact_links_from_multiple_pages_are_combined_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contact-related links should be returned once in sorted order."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.contact_links == [CONTACT_URL]


def test_failed_pages_are_recorded_and_do_not_stop_crawl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing page should be reported without losing prior successes."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.visited_urls == [
        BASE_URL,
        CONTACT_URL,
        INFRASTRUCTURE_URL,
    ]
    assert len(result.failed_pages) == 1
    assert result.failed_pages[0].url == MISSING_URL
    assert result.failed_pages[0].error == "fictional missing page"


def test_trailing_slash_and_non_trailing_slash_are_same_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent trailing-slash URLs should share one crawl identity."""

    install_fake_scraper(monkeypatch)

    assert (
        normalise_crawl_url(
            "https://www.EXAMPLE-CITY.de/kontakt/"
        )
        == CONTACT_URL
    )

    result = crawl_website(BASE_URL, max_pages=4)

    assert result.visited_urls.count(CONTACT_URL) == 1


def test_max_pages_zero_raises_value_error() -> None:
    """max_pages must be at least one."""

    with pytest.raises(ValueError):
        crawl_website(BASE_URL, max_pages=0)


def test_page_results_order_matches_visited_urls_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured page results should preserve successful visit order."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(BASE_URL, max_pages=3)

    assert [
        page_result.url
        for page_result in result.page_results
    ] == result.visited_urls
