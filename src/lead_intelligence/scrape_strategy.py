from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_USER_AGENT,
)
from .dynamic_scraper import (
    DynamicPageOptions,
    DynamicScrapeResult,
    scrape_dynamic_page,
)
from .static_scraper import ScrapedPage, scrape_page


logger = logging.getLogger(__name__)

ScrapeMode = Literal["static", "dynamic", "auto"]
UsedScrapeMode = Literal["static", "dynamic"]

JAVASCRIPT_REQUIRED_PHRASES = (
    "enable javascript",
    "javascript is required",
    "please enable javascript",
    "you need to enable javascript",
    "requires javascript",
)


@dataclass
class ScrapeDecision:
    """Chosen scrape mode and parsed page result."""

    requested_mode: ScrapeMode
    used_mode: UsedScrapeMode
    fallback_reason: str | None
    page: ScrapedPage


def static_page_appears_insufficient(
    page: ScrapedPage,
    *,
    minimum_visible_text_length: int = 200,
) -> bool:
    """Return whether static HTML looks too thin for reliable analysis."""

    if minimum_visible_text_length < 0:
        raise ValueError("minimum_visible_text_length must be zero or greater")

    visible_text = page.visible_text.strip()

    if len(visible_text) < minimum_visible_text_length:
        return True

    if not page.title.strip() and not page.main_heading.strip():
        return True

    normalized_text = visible_text.casefold()

    return any(
        phrase in normalized_text
        for phrase in JAVASCRIPT_REQUIRED_PHRASES
    )


def scrape_with_strategy(
    url: str,
    *,
    mode: ScrapeMode = "auto",
    timeout: float = DEFAULT_REQUEST_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    dynamic_options: DynamicPageOptions | None = None,
    static_scrape_function: Callable[..., ScrapedPage] = scrape_page,
    dynamic_scrape_function: Callable[..., DynamicScrapeResult] = scrape_dynamic_page,
    sleep_function: Callable[[float], None] = time.sleep,
) -> ScrapeDecision:
    """Scrape a page using static, dynamic, or conservative auto mode."""

    if mode not in {"static", "dynamic", "auto"}:
        raise ValueError("mode must be one of: static, dynamic, auto")

    if mode == "static":
        page = static_scrape_function(
            url,
            timeout=timeout,
            user_agent=user_agent,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            sleep_function=sleep_function,
        )

        return ScrapeDecision(
            requested_mode=mode,
            used_mode="static",
            fallback_reason=None,
            page=page,
        )

    if mode == "dynamic":
        dynamic_result = dynamic_scrape_function(
            url,
            options=dynamic_options,
            user_agent=user_agent,
        )

        return ScrapeDecision(
            requested_mode=mode,
            used_mode="dynamic",
            fallback_reason=None,
            page=dynamic_result.scraped_page,
        )

    static_page = static_scrape_function(
        url,
        timeout=timeout,
        user_agent=user_agent,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        sleep_function=sleep_function,
    )

    if not static_page_appears_insufficient(static_page):
        return ScrapeDecision(
            requested_mode=mode,
            used_mode="static",
            fallback_reason=None,
            page=static_page,
        )

    fallback_reason = "static HTML appeared insufficient for analysis"
    logger.info(
        "Static scrape fallback triggered: url=%s reason=%s",
        url,
        fallback_reason,
    )
    dynamic_result = dynamic_scrape_function(
        url,
        options=dynamic_options,
        user_agent=user_agent,
    )

    return ScrapeDecision(
        requested_mode=mode,
        used_mode="dynamic",
        fallback_reason=fallback_reason,
        page=dynamic_result.scraped_page,
    )
