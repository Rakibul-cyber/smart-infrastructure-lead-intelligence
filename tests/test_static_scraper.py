from __future__ import annotations

from pathlib import Path

import pytest
import requests
from bs4 import BeautifulSoup

import src.lead_intelligence.static_scraper as static_scraper_module
from src.lead_intelligence.static_scraper import (
    DiscoveredLink,
    calculate_retry_delay,
    clean_link,
    download_page,
    extract_emails,
    extract_links,
    extract_phone_numbers,
    extract_visible_text,
    is_retryable_exception,
    normalise_domain,
    parse_page,
    scrape_page,
)


FIXTURE_PATH = Path(
    "tests/fixtures/sample_municipality.html"
)

BASE_URL = "https://example-city.de"


class FakeResponse:
    """Small fake response for download retry tests."""

    def __init__(
        self,
        status_code: int = 200,
        text: str = "<html><body>Example</body></html>",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return

        error = requests.HTTPError(
            f"HTTP {self.status_code}"
        )
        error.response = self
        raise error


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
    assert result.discovered_internal_links == [
        DiscoveredLink(
            url="https://example-city.de/infrastructure",
            anchor_text="Infrastructure Department",
        ),
        DiscoveredLink(
            url="https://example-city.de/team",
            anchor_text="Team",
        ),
        DiscoveredLink(
            url="https://example-city.de/kontakt",
            anchor_text="Kontakt",
        ),
        DiscoveredLink(
            url="https://www.example-city.de/impressum",
            anchor_text="Impressum",
        ),
    ]


def test_parse_page_preserves_anchor_text_for_internal_links() -> None:
    """ScrapedPage should preserve internal anchor text for prioritisation."""

    result = parse_page(
        url=BASE_URL,
        html=(
            "<html><body>"
            "<a href='/smart-city'>Smart City programme</a>"
            "<a href='/kontakt'>Kontakt</a>"
            "<a href='https://external.example/contact'>External</a>"
            "</body></html>"
        ),
    )

    assert result.internal_links == [
        "https://example-city.de/kontakt",
        "https://example-city.de/smart-city",
    ]
    assert result.contact_links == [
        "https://example-city.de/kontakt",
        "https://external.example/contact",
    ]
    assert result.discovered_internal_links == [
        DiscoveredLink(
            url="https://example-city.de/smart-city",
            anchor_text="Smart City programme",
        ),
        DiscoveredLink(
            url="https://example-city.de/kontakt",
            anchor_text="Kontakt",
        ),
    ]


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
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> str:
        captured_call["url"] = url
        captured_call["timeout"] = timeout
        captured_call["user_agent"] = user_agent
        captured_call["max_retries"] = max_retries
        captured_call["retry_backoff_seconds"] = retry_backoff_seconds
        captured_call["sleep_function"] = sleep_function
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
        "max_retries": 2,
        "retry_backoff_seconds": 1.0,
        "sleep_function": static_scraper_module.time.sleep,
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
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
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


def install_fake_get(
    monkeypatch,
    outcomes: list[FakeResponse | requests.RequestException],
) -> list[tuple[str, dict[str, str], float]]:
    """Install a requests.get fake that consumes outcomes in order."""

    calls: list[tuple[str, dict[str, str], float]] = []

    def fake_get(
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        calls.append(
            (
                url,
                headers,
                timeout,
            )
        )
        outcome = outcomes.pop(0)

        if isinstance(outcome, requests.RequestException):
            raise outcome

        return outcome

    monkeypatch.setattr(
        static_scraper_module.requests,
        "get",
        fake_get,
    )

    return calls


def test_successful_first_attempt_performs_no_sleep(monkeypatch) -> None:
    """A successful first attempt should not sleep."""

    sleeps: list[float] = []
    install_fake_get(monkeypatch, [FakeResponse(text="success")])

    assert download_page(
        BASE_URL,
        sleep_function=sleeps.append,
    ) == "success"
    assert sleeps == []


@pytest.mark.parametrize(
    "error",
    [
        requests.Timeout("timeout"),
        requests.ConnectionError("connection"),
    ],
)
def test_timeout_and_connection_errors_are_retried(
    monkeypatch,
    error: requests.RequestException,
) -> None:
    """Timeout and connection errors should be retried."""

    sleeps: list[float] = []
    calls = install_fake_get(
        monkeypatch,
        [
            error,
            FakeResponse(text="after retry"),
        ],
    )

    result = download_page(
        BASE_URL,
        retry_backoff_seconds=2,
        sleep_function=sleeps.append,
    )

    assert result == "after retry"
    assert len(calls) == 2
    assert sleeps == [2.0]


@pytest.mark.parametrize("status_code", [429, 500])
def test_retryable_http_statuses_are_retried(
    monkeypatch,
    status_code: int,
) -> None:
    """Retryable HTTP status codes should be retried."""

    sleeps: list[float] = []
    calls = install_fake_get(
        monkeypatch,
        [
            FakeResponse(status_code=status_code),
            FakeResponse(text="ok"),
        ],
    )

    assert download_page(
        BASE_URL,
        sleep_function=sleeps.append,
    ) == "ok"
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_404_is_not_retried(monkeypatch) -> None:
    """Non-retryable HTTP statuses should fail immediately."""

    sleeps: list[float] = []
    calls = install_fake_get(
        monkeypatch,
        [FakeResponse(status_code=404)],
    )

    with pytest.raises(requests.HTTPError):
        download_page(
            BASE_URL,
            sleep_function=sleeps.append,
        )

    assert len(calls) == 1
    assert sleeps == []


def test_retries_stop_after_max_retries(monkeypatch) -> None:
    """Retry attempts should stop after max_retries."""

    sleeps: list[float] = []
    calls = install_fake_get(
        monkeypatch,
        [
            requests.Timeout("first"),
            requests.Timeout("second"),
        ],
    )

    with pytest.raises(requests.Timeout):
        download_page(
            BASE_URL,
            max_retries=1,
            sleep_function=sleeps.append,
        )

    assert len(calls) == 2
    assert sleeps == [1.0]


def test_total_attempts_equal_one_plus_max_retries(monkeypatch) -> None:
    """Total attempts should equal 1 + max_retries."""

    calls = install_fake_get(
        monkeypatch,
        [
            requests.Timeout("one"),
            requests.Timeout("two"),
            requests.Timeout("three"),
            FakeResponse(text="ok"),
        ],
    )

    assert download_page(
        BASE_URL,
        max_retries=3,
        sleep_function=lambda delay: None,
    ) == "ok"
    assert len(calls) == 4


def test_sleep_delays_follow_exponential_backoff(monkeypatch) -> None:
    """Retry sleeps should use exponential backoff."""

    sleeps: list[float] = []
    install_fake_get(
        monkeypatch,
        [
            requests.Timeout("one"),
            requests.Timeout("two"),
            FakeResponse(text="ok"),
        ],
    )

    download_page(
        BASE_URL,
        max_retries=2,
        retry_backoff_seconds=2,
        sleep_function=sleeps.append,
    )

    assert sleeps == [2.0, 4.0]


def test_retry_after_numeric_header_is_respected_when_greater(
    monkeypatch,
) -> None:
    """Retry-After seconds should win when greater than backoff."""

    sleeps: list[float] = []
    install_fake_get(
        monkeypatch,
        [
            FakeResponse(
                status_code=429,
                headers={"Retry-After": "5"},
            ),
            FakeResponse(text="ok"),
        ],
    )

    download_page(
        BASE_URL,
        retry_backoff_seconds=1,
        sleep_function=sleeps.append,
    )

    assert sleeps == [5.0]


def test_invalid_retry_after_is_ignored(monkeypatch) -> None:
    """Invalid Retry-After values should not break retry delay calculation."""

    sleeps: list[float] = []
    install_fake_get(
        monkeypatch,
        [
            FakeResponse(
                status_code=429,
                headers={"Retry-After": "tomorrow"},
            ),
            FakeResponse(text="ok"),
        ],
    )

    download_page(
        BASE_URL,
        retry_backoff_seconds=3,
        sleep_function=sleeps.append,
    )

    assert sleeps == [3.0]


def test_no_sleep_occurs_after_final_failure(monkeypatch) -> None:
    """The final failed attempt should not sleep."""

    sleeps: list[float] = []
    install_fake_get(
        monkeypatch,
        [requests.Timeout("only")],
    )

    with pytest.raises(requests.Timeout):
        download_page(
            BASE_URL,
            max_retries=0,
            sleep_function=sleeps.append,
        )

    assert sleeps == []


def test_max_retries_below_zero_raises_value_error() -> None:
    """Negative max_retries should be rejected."""

    with pytest.raises(ValueError):
        download_page(BASE_URL, max_retries=-1)


def test_negative_retry_backoff_seconds_raises_value_error() -> None:
    """Negative retry backoff should be rejected."""

    with pytest.raises(ValueError):
        download_page(BASE_URL, retry_backoff_seconds=-1)


def test_is_retryable_exception_classifications() -> None:
    """Retryable exception classification should match policy."""

    retryable_response = FakeResponse(status_code=503)
    retryable_http_error = requests.HTTPError("503")
    retryable_http_error.response = retryable_response

    not_found_response = FakeResponse(status_code=404)
    not_found_error = requests.HTTPError("404")
    not_found_error.response = not_found_response

    response_missing_error = requests.HTTPError("missing")

    assert is_retryable_exception(requests.Timeout()) is True
    assert is_retryable_exception(requests.ConnectionError()) is True
    assert is_retryable_exception(retryable_http_error) is True
    assert is_retryable_exception(not_found_error) is False
    assert is_retryable_exception(response_missing_error) is False
    assert is_retryable_exception(requests.RequestException()) is False


def test_calculate_retry_delay_validation_and_output() -> None:
    """Retry delay helper should validate and calculate expected delays."""

    assert calculate_retry_delay(1, 2) == 2.0
    assert calculate_retry_delay(3, 2) == 8.0
    assert calculate_retry_delay(1, 2, "5") == 5.0
    assert calculate_retry_delay(1, 2, "-1") == 2.0
    assert calculate_retry_delay(1, 2, "Wed, 21 Oct 2015") == 2.0

    with pytest.raises(ValueError):
        calculate_retry_delay(0, 1)

    with pytest.raises(ValueError):
        calculate_retry_delay(1, -1)


def test_scrape_page_forwards_retry_settings_and_sleep_function(
    monkeypatch,
) -> None:
    """scrape_page should forward retry settings to download_page."""

    captured_call: dict[str, object] = {}

    def fake_sleep(delay: float) -> None:
        return None

    def fake_download_page(
        url: str,
        *,
        timeout: float,
        user_agent: str,
        max_retries: int,
        retry_backoff_seconds: float,
        sleep_function,
    ) -> str:
        captured_call["url"] = url
        captured_call["timeout"] = timeout
        captured_call["user_agent"] = user_agent
        captured_call["max_retries"] = max_retries
        captured_call["retry_backoff_seconds"] = retry_backoff_seconds
        captured_call["sleep_function"] = sleep_function
        return (
            "<html><head><title>Retry</title></head>"
            "<body><h1>Retry Page</h1></body></html>"
        )

    monkeypatch.setattr(
        static_scraper_module,
        "download_page",
        fake_download_page,
    )

    result = scrape_page(
        BASE_URL,
        timeout=9,
        user_agent="RetryAgent/1.0",
        max_retries=4,
        retry_backoff_seconds=0.5,
        sleep_function=fake_sleep,
    )

    assert result.title == "Retry"
    assert captured_call == {
        "url": BASE_URL,
        "timeout": 9,
        "user_agent": "RetryAgent/1.0",
        "max_retries": 4,
        "retry_backoff_seconds": 0.5,
        "sleep_function": fake_sleep,
    }


def test_retry_warning_includes_delay_and_attempt_information(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retry warnings should include delay and attempt information."""

    install_fake_get(
        monkeypatch,
        [
            requests.Timeout("timeout"),
            FakeResponse(text="ok"),
        ],
    )

    with caplog.at_level("WARNING"):
        download_page(
            BASE_URL,
            retry_backoff_seconds=2,
            sleep_function=lambda delay: None,
        )

    assert any(
        "attempt=1/3" in record.message
        and "delay=2.00" in record.message
        for record in caplog.records
    )


def test_final_request_failure_is_logged(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Final request failure should be logged."""

    install_fake_get(
        monkeypatch,
        [requests.Timeout("timeout")],
    )

    with caplog.at_level("ERROR"):
        with pytest.raises(requests.Timeout):
            download_page(
                BASE_URL,
                max_retries=0,
                sleep_function=lambda delay: None,
            )

    assert any(
        "Request failed" in record.message
        for record in caplog.records
    )
