from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import ParseResult, urlparse, urlunparse, urldefrag

import requests

from .config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_DELAY_SECONDS,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_USER_AGENT,
)
from .dynamic_scraper import DynamicPageOptions, DynamicScraperError
from .link_prioritiser import (
    CONTACT_SCORE,
    GENERAL_SCORE,
    LinkPriority,
    prioritise_links,
)
from .resource_filter import classify_resource_url
from .scrape_strategy import ScrapeDecision, ScrapeMode, scrape_with_strategy
from .static_scraper import (
    ScrapedPage,
    UnsupportedContentError,
    normalise_domain,
    scrape_page,
)


logger = logging.getLogger(__name__)


def default_scrape_strategy(
    *args,
    **kwargs,
) -> ScrapeDecision:
    """Use the strategy layer with the crawler-local static scraper hook."""

    kwargs.setdefault("static_scrape_function", scrape_page)

    return scrape_with_strategy(*args, **kwargs)


@dataclass
class CrawlFailure:
    """A page that could not be fetched during a crawl."""

    url: str
    error: str


@dataclass
class CrawledWebsite:
    """Combined structured result from a controlled website crawl."""

    start_url: str
    visited_urls: list[str]
    failed_pages: list[CrawlFailure]
    emails: list[str]
    phone_numbers: list[str]
    contact_links: list[str]
    page_results: list[ScrapedPage]
    document_links: list[str] = field(default_factory=list)


def normalise_crawl_url(url: str) -> str:
    """
    Normalize a URL for deterministic crawl identity checks.

    Fragments are removed, scheme/domain are lowercased, leading www. is
    ignored, empty paths become /, and non-root trailing slashes are removed.
    """

    def normalized_netloc(parsed_url: ParseResult) -> str:
        hostname = parsed_url.hostname or ""
        hostname = hostname.casefold()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        if parsed_url.port is None:
            return hostname

        return f"{hostname}:{parsed_url.port}"

    url_without_fragment, _fragment = urldefrag(url)
    parsed_url = urlparse(url_without_fragment)

    path = parsed_url.path or "/"

    if path != "/":
        path = path.rstrip("/")

        if not path:
            path = "/"

    normalized = parsed_url._replace(
        scheme=parsed_url.scheme.casefold(),
        netloc=normalized_netloc(parsed_url),
        path=path,
    )

    return urlunparse(normalized)


def crawl_website(
    start_url: str,
    max_pages: int = 5,
    *,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    sleep_function: Callable[[float], None] = time.sleep,
    scrape_mode: ScrapeMode = "static",
    dynamic_options: DynamicPageOptions | None = None,
    scrape_strategy_function: Callable[..., ScrapeDecision] = (
        default_scrape_strategy
    ),
    business_link_priority_enabled: bool = True,
    general_links_enabled: bool = True,
) -> CrawledWebsite:
    """
    Crawl a small number of internal pages and combine public contact data.

    The crawler controls respectful delays between different page URLs.
    Per-page retry backoff is handled by static_scraper.download_page.
    """

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    if request_delay_seconds < 0:
        raise ValueError(
            "request_delay_seconds must be zero or greater"
        )

    normalized_start_url = normalise_crawl_url(start_url)
    start_domain = normalise_domain(normalized_start_url)
    logger.info(
        "Crawl started: start_url=%s max_pages=%d",
        normalized_start_url,
        max_pages,
    )

    queue: deque[str] = deque([normalized_start_url])
    queued_urls: set[str] = {normalized_start_url}
    visited_url_set: set[str] = set()
    failed_url_set: set[str] = set()

    visited_urls: list[str] = []
    failed_pages: list[CrawlFailure] = []
    page_results: list[ScrapedPage] = []
    emails: set[str] = set()
    phone_numbers: set[str] = set()
    contact_links: set[str] = set()
    document_links: set[str] = set()
    attempted_pages = 0

    while queue and len(visited_urls) < max_pages:
        current_url = queue.popleft()

        if (
            current_url in visited_url_set
            or current_url in failed_url_set
        ):
            continue

        if attempted_pages > 0:
            logger.debug(
                "Applying request pacing delay: delay=%.2f next_url=%s",
                request_delay_seconds,
                current_url,
            )
            sleep_function(request_delay_seconds)

        attempted_pages += 1

        try:
            scrape_decision = scrape_strategy_function(
                current_url,
                mode=scrape_mode,
                timeout=request_timeout,
                user_agent=user_agent,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                dynamic_options=dynamic_options,
                sleep_function=sleep_function,
            )
            page_result = scrape_decision.page

        except UnsupportedContentError as error:
            failed_url_set.add(current_url)

            if error.document_link:
                document_links.add(normalise_crawl_url(error.url))

            logger.info(
                "Unsupported resource skipped during crawl: %s error=%s",
                current_url,
                error,
            )
            continue

        except (requests.RequestException, DynamicScraperError) as error:
            failed_url_set.add(current_url)
            logger.warning(
                "Page failed during crawl: %s error=%s",
                current_url,
                error,
            )
            failed_pages.append(
                CrawlFailure(
                    url=current_url,
                    error=str(error),
                )
            )
            continue

        visited_url_set.add(current_url)
        visited_urls.append(current_url)
        page_results.append(page_result)
        logger.info("Page successfully visited: %s", current_url)

        if scrape_decision.used_mode == "dynamic":
            logger.info(
                "Dynamic scraping used during crawl: url=%s reason=%s",
                current_url,
                scrape_decision.fallback_reason or "requested",
            )

        emails.update(page_result.emails)
        phone_numbers.update(page_result.phone_numbers)

        contact_links.update(
            normalise_crawl_url(link)
            for link in page_result.contact_links
        )
        logger.debug(
            "Aggregated counts: visited=%d failed=%d emails=%d phones=%d "
            "contact_links=%d document_links=%d",
            len(visited_urls),
            len(failed_pages),
            len(emails),
            len(phone_numbers),
            len(contact_links),
            len(document_links),
        )

        prioritized_links = build_prioritized_crawl_candidates(
            page_result=page_result,
            business_link_priority_enabled=business_link_priority_enabled,
            general_links_enabled=general_links_enabled,
        )

        for priority in prioritized_links:
            normalized_link = normalise_crawl_url(priority.url)

            logger.debug(
                "URL priority evaluated: url=%s category=%s score=%d",
                normalized_link,
                priority.category,
                priority.score,
            )

            if normalise_domain(normalized_link) != start_domain:
                logger.debug("External URL skipped: %s", normalized_link)
                continue

            resource_classification = classify_resource_url(normalized_link)

            if resource_classification.document_link:
                document_links.add(normalized_link)
                logger.debug(
                    "Document URL recorded but not queued: %s reason=%s",
                    normalized_link,
                    resource_classification.excluded_reason,
                )
                continue

            if not resource_classification.crawlable_html:
                logger.debug(
                    "Non-HTML URL skipped: %s category=%s reason=%s",
                    normalized_link,
                    resource_classification.category,
                    resource_classification.excluded_reason,
                )
                continue

            if (
                normalized_link in queued_urls
                or normalized_link in visited_url_set
                or normalized_link in failed_url_set
            ):
                logger.debug("Duplicate URL skipped: %s", normalized_link)
                continue

            queue.append(normalized_link)
            queued_urls.add(normalized_link)
            logger.debug(
                "URL queued: %s queue_size=%d category=%s score=%d",
                normalized_link,
                len(queue),
                priority.category,
                priority.score,
            )

    result = CrawledWebsite(
        start_url=normalized_start_url,
        visited_urls=visited_urls,
        failed_pages=failed_pages,
        emails=sorted(emails),
        phone_numbers=sorted(phone_numbers),
        contact_links=sorted(contact_links),
        page_results=page_results,
        document_links=sorted(document_links),
    )

    logger.info(
        "Crawl completed: start_url=%s visited=%d failed=%d",
        normalized_start_url,
        len(result.visited_urls),
        len(result.failed_pages),
    )

    return result


def build_prioritized_crawl_candidates(
    page_result: ScrapedPage,
    *,
    business_link_priority_enabled: bool,
    general_links_enabled: bool,
) -> list[LinkPriority]:
    """Build page-local crawl candidates in the configured queue order."""

    if not business_link_priority_enabled:
        return [
            LinkPriority(
                url=link,
                score=CONTACT_SCORE if link in page_result.contact_links
                else GENERAL_SCORE,
                matched_terms=(),
                category="contact" if link in page_result.contact_links
                else "general",
            )
            for link in [
                *page_result.contact_links,
                *page_result.internal_links,
            ]
        ]

    discovered_links = _links_with_anchor_text(page_result)
    prioritized_links = prioritise_links(discovered_links)

    if general_links_enabled:
        return prioritized_links

    return [
        priority
        for priority in prioritized_links
        if priority.category in {"business", "contact"}
    ]


def _links_with_anchor_text(
    page_result: ScrapedPage,
) -> list[tuple[str, str]]:
    if page_result.discovered_internal_links:
        return [
            (link.url, link.anchor_text)
            for link in page_result.discovered_internal_links
        ]

    return [
        (link, "")
        for link in page_result.internal_links
    ]
