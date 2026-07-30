from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from urllib.parse import ParseResult, urlparse, urlunparse, urldefrag

import requests

from .config import DEFAULT_REQUEST_TIMEOUT, DEFAULT_USER_AGENT
from .static_scraper import ScrapedPage, normalise_domain, scrape_page


logger = logging.getLogger(__name__)

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
) -> CrawledWebsite:
    """
    Crawl a small number of internal pages and combine public contact data.

    The crawler uses breadth-first traversal, prioritizes contact-related links
    in each page's queue expansion, and continues past individual request
    failures.
    """

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

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

    while queue and len(visited_urls) < max_pages:
        current_url = queue.popleft()

        if (
            current_url in visited_url_set
            or current_url in failed_url_set
        ):
            continue

        try:
            page_result = scrape_page(
                current_url,
                timeout=request_timeout,
                user_agent=user_agent,
            )

        except requests.RequestException as error:
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

        emails.update(page_result.emails)
        phone_numbers.update(page_result.phone_numbers)

        contact_links.update(
            normalise_crawl_url(link)
            for link in page_result.contact_links
        )
        logger.debug(
            "Aggregated counts: visited=%d failed=%d emails=%d phones=%d "
            "contact_links=%d",
            len(visited_urls),
            len(failed_pages),
            len(emails),
            len(phone_numbers),
            len(contact_links),
        )

        prioritized_links = [
            *page_result.contact_links,
            *page_result.internal_links,
        ]

        for link in prioritized_links:
            normalized_link = normalise_crawl_url(link)

            if normalise_domain(normalized_link) != start_domain:
                logger.debug("External URL skipped: %s", normalized_link)
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
                "URL queued: %s queue_size=%d",
                normalized_link,
                len(queue),
            )

    result = CrawledWebsite(
        start_url=normalized_start_url,
        visited_urls=visited_urls,
        failed_pages=failed_pages,
        emails=sorted(emails),
        phone_numbers=sorted(phone_numbers),
        contact_links=sorted(contact_links),
        page_results=page_results,
    )

    logger.info(
        "Crawl completed: start_url=%s visited=%d failed=%d",
        normalized_start_url,
        len(result.visited_urls),
        len(result.failed_pages),
    )

    return result
