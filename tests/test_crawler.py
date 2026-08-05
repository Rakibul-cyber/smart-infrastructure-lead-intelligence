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
from src.lead_intelligence.static_scraper import (
    ScrapedPage,
    UnsupportedContentError,
    parse_page,
)


FIXTURE_DIR = Path("tests/fixtures")
BASE_URL = "https://example-city.de/"
CONTACT_URL = "https://example-city.de/kontakt"
INFRASTRUCTURE_URL = "https://example-city.de/infrastructure"
MISSING_URL = "https://example-city.de/missing"
PRIORITY_BASE_URL = "https://priority.example/"
PRIORITY_STREET_LIGHTING_URL = (
    "https://priority.example/infrastruktur/strassenbeleuchtung"
)
PRIORITY_PROCUREMENT_URL = "https://priority.example/ausschreibungen"
PRIORITY_SMART_CITY_URL = "https://priority.example/smart-city"
PRIORITY_ENERGY_URL = "https://priority.example/energie/energieeffizienz"
PRIORITY_CONTACT_URL = "https://priority.example/kontakt"
PRIORITY_IMPRESSUM_URL = "https://priority.example/impressum"
PRIORITY_NEWS_URL = "https://priority.example/aktuelles"
PRIORITY_PDF_URL = "https://priority.example/downloads/beleuchtung.pdf"


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


def install_priority_fake_scraper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace network scraping with prioritisation fixtures."""

    fixture_map = {
        PRIORITY_BASE_URL: "crawler_priority_home.html",
        PRIORITY_STREET_LIGHTING_URL: (
            "crawler_priority_street_lighting.html"
        ),
        PRIORITY_PROCUREMENT_URL: "crawler_priority_procurement.html",
        PRIORITY_SMART_CITY_URL: "crawler_priority_smart_city.html",
        PRIORITY_ENERGY_URL: "crawler_priority_energy.html",
        PRIORITY_CONTACT_URL: "crawler_priority_contact.html",
        PRIORITY_IMPRESSUM_URL: "crawler_priority_impressum.html",
        PRIORITY_NEWS_URL: "crawler_priority_news.html",
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


def test_business_page_is_prioritized_before_contact_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Business-relevant links should be queued before contact links."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        sleep_function=no_sleep,
    )

    assert result.visited_urls == [
        BASE_URL,
        INFRASTRUCTURE_URL,
        CONTACT_URL,
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
        INFRASTRUCTURE_URL,
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
        "+493011112222",
        "+493033334444",
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
        INFRASTRUCTURE_URL,
        CONTACT_URL,
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


def test_contact_page_is_queued_before_general_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contact links should remain ahead of general internal links."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=8,
        sleep_function=no_sleep,
    )

    assert result.visited_urls.index(PRIORITY_CONTACT_URL) < (
        result.visited_urls.index(PRIORITY_NEWS_URL)
    )


def test_privacy_and_login_pages_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Excluded privacy and login pages should not be queued."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=8,
        sleep_function=no_sleep,
    )

    assert "https://priority.example/datenschutz" not in result.visited_urls
    assert "https://priority.example/login" not in result.visited_urls


def test_pdf_links_are_collected_as_document_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal document links should be recorded but not visited."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=8,
        sleep_function=no_sleep,
    )

    assert result.document_links == [PRIORITY_PDF_URL]
    assert PRIORITY_PDF_URL not in result.visited_urls


def test_html_looking_pdf_response_is_recorded_as_document_link() -> None:
    """A document Content-Type on an HTML-looking URL should be recorded."""

    def fake_strategy(url: str, **kwargs):
        if url == PRIORITY_BASE_URL:
            return ScrapeDecision(
                requested_mode=kwargs["mode"],
                used_mode="static",
                fallback_reason=None,
                page=parse_page(
                    url=url,
                    html="<html><body><a href='/download'>Download</a></body></html>",
                ),
            )

        raise UnsupportedContentError(
            url,
            content_type="application/pdf",
            category="document",
            document_link=True,
        )

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=2,
        sleep_function=no_sleep,
        scrape_strategy_function=fake_strategy,
    )

    assert result.visited_urls == [PRIORITY_BASE_URL]
    assert result.document_links == ["https://priority.example/download"]
    assert result.failed_pages == []


def test_assets_are_skipped_without_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CSS, JavaScript, and images should not be queued as failures."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=8,
        sleep_function=no_sleep,
    )

    assert "https://priority.example/assets/site.css" not in result.visited_urls
    assert "https://priority.example/assets/app.js" not in result.visited_urls
    assert "https://priority.example/assets/logo.png" not in result.visited_urls
    assert result.failed_pages == []


def test_skipped_assets_do_not_trigger_request_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipped resource links should not create extra crawl attempts."""

    install_priority_fake_scraper(monkeypatch)
    sleeps: list[float] = []

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=2,
        request_delay_seconds=1,
        sleep_function=sleeps.append,
    )

    assert result.visited_urls == [
        PRIORITY_BASE_URL,
        PRIORITY_STREET_LIGHTING_URL,
    ]
    assert sleeps == [1]


def test_duplicate_urls_are_not_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate normalised URLs should not create duplicate visits."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.visited_urls.count(CONTACT_URL) == 1


def test_disabling_priority_restores_legacy_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The legacy option should use the old contact-first queue order."""

    install_fake_scraper(monkeypatch)

    result = crawl_website(
        BASE_URL,
        max_pages=3,
        sleep_function=no_sleep,
        business_link_priority_enabled=False,
    )

    assert result.visited_urls == [
        BASE_URL,
        CONTACT_URL,
        INFRASTRUCTURE_URL,
    ]


def test_business_links_only_omits_general_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Business-only mode should retain business and contact links."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=8,
        sleep_function=no_sleep,
        general_links_enabled=False,
    )

    assert PRIORITY_NEWS_URL not in result.visited_urls
    assert PRIORITY_CONTACT_URL in result.visited_urls
    assert PRIORITY_STREET_LIGHTING_URL in result.visited_urls


def test_duplicate_site_wide_phone_numbers_collapse() -> None:
    """Normalised phone numbers repeated across pages should appear once."""

    def fake_strategy(url: str, **kwargs):
        if url == PRIORITY_BASE_URL:
            html = (
                "<html><body>"
                "<p>Header phone 030 1234 5678</p>"
                "<a href='/kontakt'>Kontakt</a>"
                "</body></html>"
            )
        else:
            html = (
                "<html><body>"
                "<a href='tel:+49 (0) 30 12345678'>Call</a>"
                "<p>Footer phone 0049 30 12345678</p>"
                "</body></html>"
            )

        return ScrapeDecision(
            requested_mode=kwargs["mode"],
            used_mode="static",
            fallback_reason=None,
            page=parse_page(
                url=url,
                html=html,
            ),
        )

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=2,
        sleep_function=no_sleep,
        scrape_strategy_function=fake_strategy,
    )

    assert result.phone_numbers == ["+493012345678"]


@pytest.mark.parametrize("scrape_mode", ["static", "dynamic", "auto"])
def test_priority_settings_work_with_scrape_modes(
    scrape_mode: str,
) -> None:
    """Priority queueing should be independent of scrape strategy mode."""

    def fake_strategy(url: str, **kwargs):
        if url == PRIORITY_BASE_URL:
            html = (
                "<html><body>"
                "<a href='/kontakt'>Kontakt</a>"
                "<a href='/smart-city'>Smart City</a>"
                "</body></html>"
            )
        else:
            html = "<html><body><h1>Child</h1></body></html>"

        return ScrapeDecision(
            requested_mode=kwargs["mode"],
            used_mode="dynamic"
            if kwargs["mode"] == "dynamic"
            else "static",
            fallback_reason=None,
            page=parse_page(
                url=url,
                html=html,
            ),
        )

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=2,
        sleep_function=no_sleep,
        scrape_mode=scrape_mode,
        scrape_strategy_function=fake_strategy,
    )

    assert result.visited_urls == [
        PRIORITY_BASE_URL,
        PRIORITY_SMART_CITY_URL,
    ]


def test_limited_page_budget_visits_business_pages_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A limited page budget should reach business pages before generic pages."""

    install_priority_fake_scraper(monkeypatch)

    result = crawl_website(
        PRIORITY_BASE_URL,
        max_pages=4,
        sleep_function=no_sleep,
    )

    assert result.visited_urls == [
        PRIORITY_BASE_URL,
        PRIORITY_STREET_LIGHTING_URL,
        PRIORITY_PROCUREMENT_URL,
        PRIORITY_SMART_CITY_URL,
    ]
    assert PRIORITY_CONTACT_URL not in result.visited_urls
    assert PRIORITY_NEWS_URL not in result.visited_urls
