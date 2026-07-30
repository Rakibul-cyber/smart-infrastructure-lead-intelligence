from __future__ import annotations

from pathlib import Path

import pytest
import requests

import src.lead_intelligence.crawler as crawler_module
from src.lead_intelligence.crawler import (
    crawl_website,
    normalise_crawl_url,
)
from src.lead_intelligence.dynamic_scraper import DynamicPageOptions
from src.lead_intelligence.scrape_strategy import ScrapeDecision
from src.lead_intelligence.static_scraper import ScrapedPage, parse_page


FIXTURE_DIR = Path("tests/fixtures")
BASE_URL = "https://example-city.de/"
CONTACT_URL = "https://example-city.de/kontakt"
INFRASTRUCTURE_URL = "https://example-city.de/infrastructure"
MISSING_URL = "https://example-city.de/missing"


def no_sleep(delay: float) -> None:
    """Do not sleep in tests that are not testing pacing."""

    return None


def install_fake_scraper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace network scraping with deterministic fixture parsing."""

    fixture_map = {
        BASE_URL: "crawler_home.html",
        CONTACT_URL: "crawler_contact.html",
        INFRASTRUCTURE_URL: "crawler_infrastructure.html",
    }

    def fake_scrape_page(
        url: str,
        *,
        timeout: float = 20.0,
        user_agent: str = "SmartInfrastructureLeadIntelligence/0.1",
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
        sleep_function=lambda delay: None,
    ) -> ScrapedPage:
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

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        sleep_function=no_sleep,
    )

    assert result.visited_urls[0] == BASE_URL


def test_contact_page_is_prioritized_before_general_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contact-related links should be queued before other internal links."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        sleep_function=no_sleep,
    )

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

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

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

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.visited_urls.count(BASE_URL) == 1
    assert result.visited_urls.count(CONTACT_URL) == 1
    assert result.visited_urls.count(INFRASTRUCTURE_URL) == 1


def test_max_pages_limits_successful_page_visits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """max_pages should limit successful visits, not queued candidates."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=2,
        sleep_function=no_sleep,
    )

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

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.emails == [
        "contact.office@example-city.de",
        "roads.office@example-city.de",
    ]


def test_phone_numbers_from_multiple_pages_are_combined_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phone numbers from all successful pages should be returned once."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.phone_numbers == [
        "030 1111 2222",
        "030 3333 4444",
    ]


def test_contact_links_from_multiple_pages_are_combined_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contact-related links should be returned once in sorted order."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.contact_links == [CONTACT_URL]


def test_failed_pages_are_recorded_and_do_not_stop_crawl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing page should be reported without losing prior successes."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

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

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

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

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        sleep_function=no_sleep,
    )

    assert [
        page_result.url
        for page_result in result.page_results
    ] == result.visited_urls


def test_crawler_forwards_timeout_and_user_agent_to_scrape_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Crawler should pass configured HTTP values to scrape_page."""

    captured_calls: list[tuple[str, float, str, int, float]] = []

    def fake_scrape_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> ScrapedPage:
        captured_calls.append(
            (
                url,
                timeout,
                user_agent,
                max_retries,
                retry_backoff_seconds,
            )
        )
        return parse_page(
            url=url,
            html=(
                "<html><head><title>Configured</title></head>"
                "<body><h1>Configured</h1></body></html>"
            ),
        )

    monkeypatch.setattr(
        crawler_module,
        "scrape_page",
        fake_scrape_page,
    )

    crawl_website(
        BASE_URL,
        max_pages=1,
        request_timeout=6.5,
        user_agent="ConfiguredCrawler/1.0",
        sleep_function=no_sleep,
    )

    assert captured_calls == [
        (
            BASE_URL,
            6.5,
            "ConfiguredCrawler/1.0",
            2,
            1.0,
        )
    ]


def test_crawler_legacy_call_without_config_still_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """crawl_website(start_url) should still work with default config."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=1,
        sleep_function=no_sleep,
    )

    assert result.visited_urls == [BASE_URL]


def test_crawler_logs_page_failure_as_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Individual page failures should be logged as warnings."""

    install_fake_scraper(monkeypatch)

    with caplog.at_level("WARNING"):
        crawl_website(
            BASE_URL,
            max_pages=4,
            sleep_function=no_sleep,
        )

    assert any(
        record.levelname == "WARNING"
        and "Page failed during crawl" in record.message
        for record in caplog.records
    )


def test_crawler_logs_completion(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Crawler completion should be logged."""

    install_fake_scraper(monkeypatch)

    with caplog.at_level("INFO"):
        crawl_website(
            BASE_URL,
            max_pages=1,
            sleep_function=no_sleep,
        )

    assert any(
        "Crawl completed" in record.message
        for record in caplog.records
    )


def test_request_delay_does_not_happen_before_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request pacing should not sleep before the first page attempt."""

    attempts: list[str] = []
    sleeps: list[float] = []

    def fake_scrape_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> ScrapedPage:
        attempts.append(url)
        return parse_page(
            url=url,
            html="<html><body><h1>Only one page</h1></body></html>",
        )

    monkeypatch.setattr(
        crawler_module,
        "scrape_page",
        fake_scrape_page,
    )

    crawl_website(
        BASE_URL,
        max_pages=1,
        request_delay_seconds=3,
        sleep_function=sleeps.append,
    )

    assert attempts == [BASE_URL]
    assert sleeps == []


def test_request_delay_occurs_between_attempted_page_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request pacing should sleep between actual page attempts."""

    install_fake_scraper(monkeypatch)
    sleeps: list[float] = []

    crawl_website(
        BASE_URL,
        max_pages=3,
        request_delay_seconds=2.5,
        sleep_function=sleeps.append,
    )

    assert sleeps == [2.5, 2.5]


def test_zero_request_delay_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A zero request delay should be valid and forwarded to sleep."""

    install_fake_scraper(monkeypatch)
    sleeps: list[float] = []

    crawl_website(
        BASE_URL,
        max_pages=2,
        request_delay_seconds=0,
        sleep_function=sleeps.append,
    )

    assert sleeps == [0]


def test_negative_request_delay_raises_value_error() -> None:
    """Negative request pacing values should be rejected."""

    with pytest.raises(ValueError):
        crawl_website(
            BASE_URL,
            request_delay_seconds=-1,
        )


def test_retry_related_parameters_and_sleep_function_are_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Crawler should forward retry settings and sleeper to scrape_page."""

    captured_call: dict[str, object] = {}

    def fake_sleep(delay: float) -> None:
        return None

    def fake_scrape_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> ScrapedPage:
        captured_call["url"] = url
        captured_call["timeout"] = timeout
        captured_call["user_agent"] = user_agent
        captured_call["max_retries"] = max_retries
        captured_call["retry_backoff_seconds"] = retry_backoff_seconds
        captured_call["sleep_function"] = sleep_function
        return parse_page(
            url=url,
            html="<html><body><h1>Forwarded</h1></body></html>",
        )

    monkeypatch.setattr(
        crawler_module,
        "scrape_page",
        fake_scrape_page,
    )

    crawl_website(
        BASE_URL,
        max_pages=1,
        request_timeout=4,
        user_agent="CrawlerAgent/1.0",
        max_retries=5,
        retry_backoff_seconds=0.75,
        sleep_function=fake_sleep,
    )

    assert captured_call == {
        "url": BASE_URL,
        "timeout": 4,
        "user_agent": "CrawlerAgent/1.0",
        "max_retries": 5,
        "retry_backoff_seconds": 0.75,
        "sleep_function": fake_sleep,
    }


def test_skipped_duplicate_or_external_urls_do_not_create_extra_delays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipped duplicate/external URLs should not add pacing sleeps."""

    install_fake_scraper(monkeypatch)
    sleeps: list[float] = []

    crawl_website(
        BASE_URL,
        max_pages=4,
        request_delay_seconds=1,
        sleep_function=sleeps.append,
    )

    assert sleeps == [1, 1, 1]


def test_failed_page_counts_as_attempt_for_pacing_before_next_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed page should trigger pacing before the next actual URL."""

    sleeps: list[float] = []

    def fake_scrape_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> ScrapedPage:
        if url == BASE_URL:
            return parse_page(
                url=url,
                html=(
                    "<html><body><h1>Home</h1>"
                    "<a href='/missing'>Missing</a>"
                    "<a href='/next'>Next</a>"
                    "</body></html>"
                ),
            )

        if url == "https://example-city.de/missing":
            raise requests.RequestException("missing")

        return parse_page(
            url=url,
            html="<html><body><h1>Next</h1></body></html>",
        )

    monkeypatch.setattr(
        crawler_module,
        "scrape_page",
        fake_scrape_page,
    )

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        request_delay_seconds=2,
        sleep_function=sleeps.append,
    )

    assert [
        failure.url
        for failure in result.failed_pages
    ] == ["https://example-city.de/missing"]
    assert result.visited_urls == [
        BASE_URL,
        "https://example-city.de/next",
    ]
    assert sleeps == [2, 2]


def test_crawler_logs_request_pacing_at_debug(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Request pacing should be logged at DEBUG level."""

    install_fake_scraper(monkeypatch)

    with caplog.at_level("DEBUG"):
        crawl_website(
            BASE_URL,
            max_pages=2,
            request_delay_seconds=1,
            sleep_function=lambda delay: None,
        )

    assert any(
        record.levelname == "DEBUG"
        and "Applying request pacing delay" in record.message
        for record in caplog.records
    )


def test_crawler_default_scrape_mode_remains_static() -> None:
    """The crawler should default to static scraping for compatibility."""

    captured_kwargs: dict[str, object] = {}

    def fake_strategy(url: str, **kwargs):
        captured_kwargs.update(kwargs)
        return ScrapeDecision(
            requested_mode=kwargs["mode"],
            used_mode="static",
            fallback_reason=None,
            page=parse_page(
                url=url,
                html="<html><body><h1>Static</h1></body></html>",
            ),
        )

    crawl_website(
        BASE_URL,
        max_pages=1,
        scrape_strategy_function=fake_strategy,
    )

    assert captured_kwargs["mode"] == "static"


def test_crawler_forwards_scrape_mode_and_dynamic_options() -> None:
    """Crawler should pass browser strategy options to the page fetcher."""

    captured_kwargs: dict[str, object] = {}
    dynamic_options = DynamicPageOptions(
        headless=False,
        wait_for_selector="main.ready",
    )

    def fake_strategy(url: str, **kwargs):
        captured_kwargs.update(kwargs)
        return ScrapeDecision(
            requested_mode=kwargs["mode"],
            used_mode="dynamic",
            fallback_reason="requested",
            page=parse_page(
                url=url,
                html="<html><body><h1>Dynamic</h1></body></html>",
            ),
        )

    result = crawl_website(
        BASE_URL,
        max_pages=1,
        scrape_mode="dynamic",
        dynamic_options=dynamic_options,
        scrape_strategy_function=fake_strategy,
    )

    assert captured_kwargs["mode"] == "dynamic"
    assert captured_kwargs["dynamic_options"] is dynamic_options
    assert result.page_results[0].main_heading == "Dynamic"
