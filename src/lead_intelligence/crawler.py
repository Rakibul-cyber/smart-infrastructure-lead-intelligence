from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from urllib.parse import ParseResult, urlparse, urlunparse, urldefrag

import requests

from .static_scraper import ScrapedPage, normalise_domain, scrape_page


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
            page_result = scrape_page(current_url)

        except requests.RequestException as error:
            failed_url_set.add(current_url)
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

        emails.update(page_result.emails)
        phone_numbers.update(page_result.phone_numbers)

        internal_contact_links = [
            link
            for link in page_result.contact_links
            if normalise_domain(link) == start_domain
        ]

        contact_links.update(
            normalise_crawl_url(link)
            for link in page_result.contact_links
        )

        prioritized_links = [
            *internal_contact_links,
            *page_result.internal_links,
        ]

        for link in prioritized_links:
            normalized_link = normalise_crawl_url(link)

            if normalise_domain(normalized_link) != start_domain:
                continue

            if (
                normalized_link in queued_urls
                or normalized_link in visited_url_set
                or normalized_link in failed_url_set
            ):
                continue

            queue.append(normalized_link)
            queued_urls.add(normalized_link)

    return CrawledWebsite(
        start_url=normalized_start_url,
        visited_urls=visited_urls,
        failed_pages=failed_pages,
        emails=sorted(emails),
        phone_numbers=sorted(phone_numbers),
        contact_links=sorted(contact_links),
        page_results=page_results,
    )
