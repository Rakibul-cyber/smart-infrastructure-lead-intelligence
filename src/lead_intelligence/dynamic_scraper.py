from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import DEFAULT_USER_AGENT
from .static_scraper import ScrapedPage, parse_page

try:
    from playwright.sync_api import (
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )

except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    PlaywrightError = RuntimeError
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None

if TYPE_CHECKING:
    from playwright.sync_api import Page
else:
    Page = Any


logger = logging.getLogger(__name__)

MAX_SELECTOR_LENGTH = 500
COOKIE_BUTTON_NAMES = (
    "Accept",
    "Accept all",
    "Allow all",
    "Agree",
    "Alle akzeptieren",
    "Alle annehmen",
    "Akzeptieren",
    "Zustimmen",
)


class DynamicScraperError(RuntimeError):
    """Expected browser-rendering failure."""


@dataclass
class DynamicPageOptions:
    """Browser-rendering options for one dynamic page scrape."""

    headless: bool = True
    browser_timeout_seconds: float = 30.0
    wait_after_load_seconds: float = 0.0
    wait_for_selector: str | None = None
    accept_cookies: bool = False


@dataclass
class DynamicScrapeResult:
    """Rendered page data and browser scrape metadata."""

    scraped_page: ScrapedPage
    final_url: str
    page_title: str
    rendered_html_length: int
    cookie_dialog_handled: bool
    used_selector_wait: bool


def seconds_to_milliseconds(value: float, variable_name: str) -> int:
    """Convert seconds to rounded milliseconds after validation."""

    if value < 0:
        raise ValueError(f"{variable_name} must be zero or greater.")

    return int(round(value * 1000))


def validate_css_selector(value: str | None) -> str | None:
    """Clean a selector string without attempting full CSS parsing."""

    if value is None:
        return None

    selector = value.strip()

    if not selector:
        return None

    if len(selector) > MAX_SELECTOR_LENGTH:
        raise ValueError(
            f"CSS selector must be {MAX_SELECTOR_LENGTH} characters or fewer."
        )

    return selector


def try_accept_cookie_dialog(page: Page) -> bool:
    """Click a common cookie-consent button when it is clearly present."""

    for button_name in COOKIE_BUTTON_NAMES:
        pattern = re.compile(f"^{re.escape(button_name)}$", re.IGNORECASE)

        try:
            locator = page.get_by_role(
                "button",
                name=pattern,
            ).first
            locator.click(timeout=500)
            logger.info("Cookie dialog accepted with labelled button")

            return True

        except (PlaywrightError, PlaywrightTimeoutError):
            continue

    return False


def scrape_dynamic_page(
    url: str,
    *,
    options: DynamicPageOptions | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> DynamicScrapeResult:
    """Render one page with Chromium and parse the resulting HTML."""

    if sync_playwright is None:
        raise DynamicScraperError(
            "Playwright is not installed in the active Python environment."
        )

    dynamic_options = options or DynamicPageOptions()
    timeout_milliseconds = seconds_to_milliseconds(
        dynamic_options.browser_timeout_seconds,
        "browser_timeout_seconds",
    )
    wait_after_load_milliseconds = seconds_to_milliseconds(
        dynamic_options.wait_after_load_seconds,
        "wait_after_load_seconds",
    )
    selector = validate_css_selector(dynamic_options.wait_for_selector)

    playwright_context = None
    browser = None
    context = None
    page = None

    try:
        logger.info(
            "Launching browser for dynamic scrape: url=%s headless=%s",
            url,
            dynamic_options.headless,
        )
        playwright_context = sync_playwright()
        playwright = playwright_context.__enter__()
        browser = playwright.chromium.launch(
            headless=dynamic_options.headless,
        )
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        page.set_default_navigation_timeout(timeout_milliseconds)
        page.set_default_timeout(timeout_milliseconds)
        logger.info("Browser navigating: url=%s", url)
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout_milliseconds,
        )

        cookie_dialog_handled = False

        if dynamic_options.accept_cookies:
            cookie_dialog_handled = try_accept_cookie_dialog(page)

        used_selector_wait = selector is not None

        if selector is not None:
            try:
                page.wait_for_selector(
                    selector,
                    state="visible",
                    timeout=timeout_milliseconds,
                )

            except PlaywrightTimeoutError as error:
                raise DynamicScraperError(
                    f"Timed out waiting for selector: {selector}"
                ) from error

        if wait_after_load_milliseconds > 0:
            page.wait_for_timeout(wait_after_load_milliseconds)

        try:
            rendered_html = page.content()
            final_url = page.url
            page_title = page.title()

        except PlaywrightError as error:
            raise DynamicScraperError(
                f"Could not extract rendered page content: {url}"
            ) from error

        logger.info(
            "Rendered HTML collected: url=%s final_url=%s html_length=%d",
            url,
            final_url,
            len(rendered_html),
        )
        scraped_page = parse_page(
            url=final_url,
            html=rendered_html,
        )
        logger.info("Dynamic scrape completed: url=%s", url)

        return DynamicScrapeResult(
            scraped_page=scraped_page,
            final_url=final_url,
            page_title=page_title,
            rendered_html_length=len(rendered_html),
            cookie_dialog_handled=cookie_dialog_handled,
            used_selector_wait=used_selector_wait,
        )

    except DynamicScraperError:
        raise

    except PlaywrightTimeoutError as error:
        raise DynamicScraperError(
            f"Dynamic page navigation timed out: {url}"
        ) from error

    except PlaywrightError as error:
        raise DynamicScraperError(
            f"Dynamic browser scrape failed: {url}"
        ) from error

    finally:
        for resource in (page, context, browser):
            if resource is None:
                continue

            try:
                resource.close()

            except PlaywrightError:
                logger.debug("Browser resource close failed", exc_info=True)

        if playwright_context is not None:
            try:
                playwright_context.__exit__(None, None, None)

            except PlaywrightError:
                logger.debug("Playwright context close failed", exc_info=True)
