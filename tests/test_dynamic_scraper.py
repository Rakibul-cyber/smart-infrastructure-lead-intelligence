from __future__ import annotations

import threading
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import src.lead_intelligence.dynamic_scraper as dynamic_module
from src.lead_intelligence.dynamic_scraper import (
    DynamicPageOptions,
    DynamicScraperError,
    scrape_dynamic_page,
    seconds_to_milliseconds,
    try_accept_cookie_dialog,
    validate_css_selector,
)


class FakePlaywrightError(Exception):
    """Fake Playwright base error for tests."""


class FakePlaywrightTimeoutError(FakePlaywrightError):
    """Fake Playwright timeout error for tests."""


class FakeLocator:
    def __init__(self, *, should_click: bool = False):
        self.first = self
        self.should_click = should_click
        self.clicks = 0

    def click(self, timeout: int):
        self.clicks += 1

        if not self.should_click:
            raise FakePlaywrightTimeoutError("missing")


class FakeCookiePage:
    def __init__(self, successful_name: str | None = None):
        self.successful_name = successful_name
        self.names: list[object] = []

    def get_by_role(self, role: str, name):
        self.names.append(name)
        should_click = False

        if self.successful_name is not None:
            should_click = bool(
                isinstance(name, re.Pattern)
                and name.fullmatch(self.successful_name)
            )

        return FakeLocator(should_click=should_click)


class FakePage:
    def __init__(
        self,
        html: str,
        *,
        final_url: str = "https://example.test/rendered",
        title: str = "Rendered Title",
        fail_on: str | None = None,
    ):
        self.html = html
        self.url = final_url
        self._title = title
        self.fail_on = fail_on
        self.closed = False
        self.navigation_timeout: int | None = None
        self.action_timeout: int | None = None
        self.goto_calls: list[dict[str, object]] = []
        self.selector_calls: list[dict[str, object]] = []
        self.waits: list[int] = []

    def set_default_navigation_timeout(self, timeout: int) -> None:
        self.navigation_timeout = timeout

    def set_default_timeout(self, timeout: int) -> None:
        self.action_timeout = timeout

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append(
            {
                "url": url,
                "wait_until": wait_until,
                "timeout": timeout,
            }
        )

        if self.fail_on == "goto":
            raise FakePlaywrightError("navigation failed")

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: str,
        timeout: int,
    ) -> None:
        self.selector_calls.append(
            {
                "selector": selector,
                "state": state,
                "timeout": timeout,
            }
        )

        if self.fail_on == "selector":
            raise FakePlaywrightTimeoutError("selector failed")

    def wait_for_timeout(self, milliseconds: int) -> None:
        self.waits.append(milliseconds)

    def content(self) -> str:
        if self.fail_on == "content":
            raise FakePlaywrightError("content failed")

        return self.html

    def title(self) -> str:
        return self._title

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, page: FakePage):
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext):
        self.context = context
        self.closed = False
        self.context_user_agent: str | None = None

    def new_context(self, *, user_agent: str) -> FakeContext:
        self.context_user_agent = user_agent
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser):
        self.browser = browser
        self.launch_kwargs: dict[str, object] | None = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium):
        self.chromium = chromium


class FakeSyncPlaywright:
    def __init__(self, playwright: FakePlaywright):
        self.playwright = playwright
        self.exited = False

    def __enter__(self):
        return self.playwright

    def __exit__(self, exc_type, exc_value, traceback):
        self.exited = True


def install_fake_playwright(
    monkeypatch: pytest.MonkeyPatch,
    *,
    page: FakePage | None = None,
) -> tuple[FakePage, FakeContext, FakeBrowser, FakeChromium, FakeSyncPlaywright]:
    """Install a fake Playwright sync API."""

    fake_page = page or FakePage(
        "<html><head><title>Rendered Title</title></head>"
        "<body><h1>Rendered Heading</h1><p>Street lighting text</p></body></html>"
    )
    context = FakeContext(fake_page)
    browser = FakeBrowser(context)
    chromium = FakeChromium(browser)
    sync_context = FakeSyncPlaywright(FakePlaywright(chromium))

    monkeypatch.setattr(dynamic_module, "PlaywrightError", FakePlaywrightError)
    monkeypatch.setattr(
        dynamic_module,
        "PlaywrightTimeoutError",
        FakePlaywrightTimeoutError,
    )
    monkeypatch.setattr(dynamic_module, "sync_playwright", lambda: sync_context)

    return fake_page, context, browser, chromium, sync_context


def test_seconds_conversion_preserves_reasonable_precision() -> None:
    assert seconds_to_milliseconds(1.2345, "timeout") == 1234


def test_negative_seconds_rejected() -> None:
    with pytest.raises(ValueError, match="timeout"):
        seconds_to_milliseconds(-0.1, "timeout")


def test_selector_cleanup() -> None:
    assert validate_css_selector("  main .result  ") == "main .result"
    assert validate_css_selector(" ") is None
    assert validate_css_selector(None) is None


def test_long_selector_rejected() -> None:
    with pytest.raises(ValueError, match="500"):
        validate_css_selector("." + ("x" * 501))


def test_cookie_helper_returns_false_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dynamic_module, "PlaywrightError", FakePlaywrightError)
    monkeypatch.setattr(
        dynamic_module,
        "PlaywrightTimeoutError",
        FakePlaywrightTimeoutError,
    )

    assert try_accept_cookie_dialog(FakeCookiePage()) is False


def test_cookie_helper_stops_after_successful_click(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dynamic_module, "PlaywrightError", FakePlaywrightError)
    monkeypatch.setattr(
        dynamic_module,
        "PlaywrightTimeoutError",
        FakePlaywrightTimeoutError,
    )
    page = FakeCookiePage(successful_name="Agree")

    assert try_accept_cookie_dialog(page) is True
    assert len(page.names) == 4


def test_dynamic_scrape_forwards_options_and_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page, _context, browser, chromium, _sync_context = install_fake_playwright(
        monkeypatch
    )

    scrape_dynamic_page(
        "https://example.test",
        options=DynamicPageOptions(
            headless=False,
            browser_timeout_seconds=12.5,
        ),
        user_agent="Agent/1.0",
    )

    assert chromium.launch_kwargs == {"headless": False}
    assert browser.context_user_agent == "Agent/1.0"
    assert page.navigation_timeout == 12500
    assert page.action_timeout == 12500


def test_dynamic_navigation_uses_domcontentloaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page, _context, _browser, _chromium, _sync_context = install_fake_playwright(
        monkeypatch
    )

    scrape_dynamic_page("https://example.test")

    assert page.goto_calls == [
        {
            "url": "https://example.test",
            "wait_until": "domcontentloaded",
            "timeout": 30000,
        }
    ]


def test_selector_wait_and_optional_browser_wait_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page, _context, _browser, _chromium, _sync_context = install_fake_playwright(
        monkeypatch
    )

    result = scrape_dynamic_page(
        "https://example.test",
        options=DynamicPageOptions(
            wait_for_selector="main.ready",
            wait_after_load_seconds=0.25,
        ),
    )

    assert page.selector_calls == [
        {
            "selector": "main.ready",
            "state": "visible",
            "timeout": 30000,
        }
    ]
    assert page.waits == [250]
    assert result.used_selector_wait is True


def test_rendered_html_is_parsed_and_metadata_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = (
        "<html><head><title>Rendered Title</title></head>"
        "<body><h1>Rendered Heading</h1>"
        "<a href='mailto:info@example.test'>mail</a>"
        "<a href='/contact'>Contact</a></body></html>"
    )
    install_fake_playwright(monkeypatch, page=FakePage(html))

    result = scrape_dynamic_page("https://example.test")

    assert result.final_url == "https://example.test/rendered"
    assert result.page_title == "Rendered Title"
    assert result.rendered_html_length == len(html)
    assert result.scraped_page.main_heading == "Rendered Heading"
    assert result.scraped_page.emails == ["info@example.test"]


def test_resources_close_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    page, context, browser, _chromium, sync_context = install_fake_playwright(
        monkeypatch
    )

    scrape_dynamic_page("https://example.test")

    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert sync_context.exited is True


def test_resources_close_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    page, context, browser, _chromium, sync_context = install_fake_playwright(
        monkeypatch,
        page=FakePage("<html></html>", fail_on="goto"),
    )

    with pytest.raises(DynamicScraperError):
        scrape_dynamic_page("https://example.test")

    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert sync_context.exited is True


def test_expected_playwright_failures_become_dynamic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_playwright(
        monkeypatch,
        page=FakePage("<html></html>", fail_on="content"),
    )

    with pytest.raises(DynamicScraperError, match="content"):
        scrape_dynamic_page("https://example.test")


def test_selector_timeout_becomes_dynamic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_playwright(
        monkeypatch,
        page=FakePage("<html></html>", fail_on="selector"),
    )

    with pytest.raises(DynamicScraperError, match="Timed out waiting"):
        scrape_dynamic_page(
            "https://example.test",
            options=DynamicPageOptions(wait_for_selector="main.ready"),
        )


@pytest.mark.playwright
def test_dynamic_scrape_renders_local_javascript_fixture() -> None:
    """Render the local JavaScript fixture when Chromium is available."""

    fixture_directory = Path(__file__).parent / "fixtures"

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(
                *args,
                directory=str(fixture_directory),
                **kwargs,
            )

        def log_message(self, format: str, *args) -> None:
            return None

    try:
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            QuietHandler,
        )

    except PermissionError as error:
        pytest.skip(f"Local HTTP server unavailable in sandbox: {error}")

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/dynamic_page.html"

        try:
            result = scrape_dynamic_page(
                url,
                options=DynamicPageOptions(
                    wait_for_selector="#dynamic-content",
                    wait_after_load_seconds=0.1,
                ),
            )

        except DynamicScraperError as error:
            pytest.skip(f"Playwright browser unavailable: {error}")

        assert result.scraped_page.main_heading == (
            "Fictional Dynamic Infrastructure Office"
        )
        assert result.scraped_page.emails == ["dynamic@example-city.example"]
        assert result.scraped_page.phone_numbers == ["030 1234 5678"]

    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
