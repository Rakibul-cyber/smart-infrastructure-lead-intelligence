from __future__ import annotations

import requests
import pytest

from src.lead_intelligence.dynamic_scraper import DynamicScrapeResult
from src.lead_intelligence.scrape_strategy import (
    ScrapeDecision,
    scrape_with_strategy,
    static_page_appears_insufficient,
)
from src.lead_intelligence.static_scraper import (
    ScrapedPage,
    UnsupportedContentError,
)


def make_page(
    *,
    title: str = "Title",
    main_heading: str = "Heading",
    visible_text: str | None = None,
    emails: list[str] | None = None,
) -> ScrapedPage:
    """Build a deterministic scraped page."""

    return ScrapedPage(
        url="https://example.test",
        title=title,
        main_heading=main_heading,
        visible_text=visible_text
        if visible_text is not None
        else "This is enough visible municipal infrastructure text. " * 8,
        emails=emails or [],
        phone_numbers=[],
        absolute_links=[],
        internal_links=[],
        contact_links=[],
    )


def make_dynamic_result(page: ScrapedPage | None = None) -> DynamicScrapeResult:
    """Build a deterministic dynamic scrape result."""

    scraped_page = page or make_page(
        title="Dynamic",
        main_heading="Dynamic Heading",
    )

    return DynamicScrapeResult(
        scraped_page=scraped_page,
        final_url=scraped_page.url,
        page_title=scraped_page.title,
        rendered_html_length=100,
        cookie_dialog_handled=False,
        used_selector_wait=False,
    )


def test_static_mode_never_calls_dynamic_function() -> None:
    """Static mode should use only the static scraper."""

    called_dynamic = False

    def fake_dynamic(*args, **kwargs):
        nonlocal called_dynamic
        called_dynamic = True
        return make_dynamic_result()

    decision = scrape_with_strategy(
        "https://example.test",
        mode="static",
        static_scrape_function=lambda *args, **kwargs: make_page(),
        dynamic_scrape_function=fake_dynamic,
    )

    assert decision.used_mode == "static"
    assert called_dynamic is False


def test_dynamic_mode_never_calls_static_function() -> None:
    """Dynamic mode should use only Playwright rendering."""

    called_static = False

    def fake_static(*args, **kwargs):
        nonlocal called_static
        called_static = True
        return make_page()

    decision = scrape_with_strategy(
        "https://example.test",
        mode="dynamic",
        static_scrape_function=fake_static,
        dynamic_scrape_function=lambda *args, **kwargs: make_dynamic_result(),
    )

    assert decision.used_mode == "dynamic"
    assert called_static is False


def test_auto_mode_keeps_sufficient_static_result() -> None:
    """Auto mode should not render when static content looks sufficient."""

    called_dynamic = False

    def fake_dynamic(*args, **kwargs):
        nonlocal called_dynamic
        called_dynamic = True
        return make_dynamic_result()

    decision = scrape_with_strategy(
        "https://example.test",
        mode="auto",
        static_scrape_function=lambda *args, **kwargs: make_page(),
        dynamic_scrape_function=fake_dynamic,
    )

    assert decision.used_mode == "static"
    assert decision.fallback_reason is None
    assert called_dynamic is False


def test_auto_mode_falls_back_for_short_visible_text() -> None:
    """Short static text should trigger dynamic fallback."""

    decision = scrape_with_strategy(
        "https://example.test",
        mode="auto",
        static_scrape_function=lambda *args, **kwargs: make_page(
            visible_text="tiny"
        ),
        dynamic_scrape_function=lambda *args, **kwargs: make_dynamic_result(),
    )

    assert decision.used_mode == "dynamic"
    assert decision.fallback_reason is not None


def test_auto_mode_falls_back_for_javascript_required_phrase() -> None:
    """Clear JavaScript-required pages should trigger fallback."""

    page = make_page(
        visible_text=(
            "Please enable JavaScript to view this municipal content. "
            + ("Additional text. " * 30)
        )
    )

    assert static_page_appears_insufficient(page) is True


def test_absence_of_contact_details_alone_does_not_trigger_fallback() -> None:
    """No emails or phones alone should not trigger Playwright."""

    page = make_page(emails=[])

    assert static_page_appears_insufficient(page) is False


def test_invalid_mode_rejected() -> None:
    """Unknown scrape modes should fail clearly."""

    with pytest.raises(ValueError, match="mode"):
        scrape_with_strategy(
            "https://example.test",
            mode="browser",  # type: ignore[arg-type]
        )


def test_threshold_validation() -> None:
    """Negative text thresholds should be rejected."""

    with pytest.raises(ValueError, match="minimum_visible_text_length"):
        static_page_appears_insufficient(
            make_page(),
            minimum_visible_text_length=-1,
        )


def test_fallback_reason_is_populated() -> None:
    """Dynamic fallback decisions should include concise reasoning."""

    decision = scrape_with_strategy(
        "https://example.test",
        mode="auto",
        static_scrape_function=lambda *args, **kwargs: make_page(
            visible_text="tiny"
        ),
        dynamic_scrape_function=lambda *args, **kwargs: make_dynamic_result(),
    )

    assert decision.fallback_reason == "static HTML appeared insufficient for analysis"


def test_static_403_is_not_converted_into_browser_fallback() -> None:
    """Blocked static access should not trigger browser fallback."""

    response = requests.Response()
    response.status_code = 403
    error = requests.HTTPError("forbidden", response=response)

    def fake_static(*args, **kwargs):
        raise error

    with pytest.raises(requests.HTTPError):
        scrape_with_strategy(
            "https://example.test",
            mode="auto",
            static_scrape_function=fake_static,
            dynamic_scrape_function=lambda *args, **kwargs: make_dynamic_result(),
        )


def test_unsupported_content_does_not_launch_dynamic_scraper() -> None:
    """Unsupported content should not trigger browser fallback in auto mode."""

    called_dynamic = False

    def fake_static(*args, **kwargs):
        raise UnsupportedContentError(
            "https://example.test/download",
            content_type="application/pdf",
            category="document",
            document_link=True,
        )

    def fake_dynamic(*args, **kwargs):
        nonlocal called_dynamic
        called_dynamic = True
        return make_dynamic_result()

    with pytest.raises(UnsupportedContentError):
        scrape_with_strategy(
            "https://example.test/download",
            mode="auto",
            static_scrape_function=fake_static,
            dynamic_scrape_function=fake_dynamic,
        )

    assert called_dynamic is False


def test_pdf_url_does_not_launch_dynamic_scraper() -> None:
    """Known document URLs should not use Playwright even in dynamic mode."""

    called_dynamic = False

    def fake_dynamic(*args, **kwargs):
        nonlocal called_dynamic
        called_dynamic = True
        return make_dynamic_result()

    with pytest.raises(UnsupportedContentError):
        scrape_with_strategy(
            "https://example.test/report.pdf",
            mode="dynamic",
            dynamic_scrape_function=fake_dynamic,
        )

    assert called_dynamic is False


def test_dynamic_options_forwarded() -> None:
    """Dynamic options should be forwarded to the dynamic scrape function."""

    captured_kwargs: dict[str, object] = {}
    options = object()

    def fake_dynamic(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return make_dynamic_result()

    scrape_with_strategy(
        "https://example.test",
        mode="dynamic",
        dynamic_options=options,  # type: ignore[arg-type]
        dynamic_scrape_function=fake_dynamic,
    )

    assert captured_kwargs["options"] is options


def test_static_scrape_settings_forwarded() -> None:
    """Static scraper should receive retry and user-agent settings."""

    captured_kwargs: dict[str, object] = {}

    def fake_static(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return make_page()

    scrape_with_strategy(
        "https://example.test",
        mode="static",
        timeout=3,
        user_agent="Agent/1.0",
        max_retries=4,
        retry_backoff_seconds=0.25,
        static_scrape_function=fake_static,
    )

    assert captured_kwargs["timeout"] == 3
    assert captured_kwargs["user_agent"] == "Agent/1.0"
    assert captured_kwargs["max_retries"] == 4
    assert captured_kwargs["retry_backoff_seconds"] == 0.25
