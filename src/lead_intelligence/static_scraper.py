from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from .config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_USER_AGENT,
)


logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?:\+49|0)[\d\s()/.-]{7,}"
)

CONTACT_KEYWORDS = (
    "contact",
    "kontakt",
    "ansprechpartner",
    "impressum",
    "team",
    "staff",
    "department",
    "abteilung",
)

RETRYABLE_STATUS_CODES = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
}


@dataclass
class DiscoveredLink:
    """Internal link with the anchor text that exposed it."""

    url: str
    anchor_text: str


@dataclass
class ScrapedPage:
    """Structured information collected from one webpage."""

    url: str
    title: str
    main_heading: str
    visible_text: str
    emails: list[str]
    phone_numbers: list[str]
    absolute_links: list[str]
    internal_links: list[str]
    contact_links: list[str]
    discovered_internal_links: list[DiscoveredLink] = field(
        default_factory=list
    )


def is_retryable_exception(
    error: requests.RequestException,
) -> bool:
    """Return whether a request exception is safe to retry."""

    if isinstance(error, requests.Timeout | requests.ConnectionError):
        return True

    if isinstance(error, requests.HTTPError):
        response = error.response

        if response is None:
            return False

        return response.status_code in RETRYABLE_STATUS_CODES

    return False


def calculate_retry_delay(
    attempt_number: int,
    backoff_seconds: float,
    retry_after_header: str | None = None,
) -> float:
    """
    Calculate retry delay using exponential backoff.

    attempt_number starts at 1 for the first retry.
    """

    if attempt_number < 1:
        raise ValueError("attempt_number must be at least 1")

    if backoff_seconds < 0:
        raise ValueError("backoff_seconds must be zero or greater")

    calculated_delay = backoff_seconds * (2 ** (attempt_number - 1))

    if retry_after_header is None:
        return float(calculated_delay)

    try:
        retry_after_seconds = float(retry_after_header.strip())

    except ValueError:
        return float(calculated_delay)

    if retry_after_seconds < 0:
        return float(calculated_delay)

    return float(max(calculated_delay, retry_after_seconds))


def download_page(
    url: str,
    *,
    timeout: float = DEFAULT_REQUEST_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    sleep_function: Callable[[float], None] = time.sleep,
) -> str:
    """
    Download raw HTML from a public webpage.

    Args:
        url: Complete webpage URL.

    Returns:
        Raw HTML returned by the server.

    Raises:
        requests.RequestException:
            If the request fails or returns an unsuccessful HTTP status.
    """

    if max_retries < 0:
        raise ValueError("max_retries must be zero or greater")

    if retry_backoff_seconds < 0:
        raise ValueError(
            "retry_backoff_seconds must be zero or greater"
        )

    headers = {
        "User-Agent": user_agent
    }
    total_attempts = 1 + max_retries

    for attempt in range(1, total_attempts + 1):
        try:
            logger.debug(
                "Preparing request for %s attempt=%d/%d",
                url,
                attempt,
                total_attempts,
            )
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            logger.info("Page downloaded successfully: %s", url)

            return response.text

        except requests.RequestException as error:
            final_attempt = attempt == total_attempts

            if (
                final_attempt
                or not is_retryable_exception(error)
            ):
                logger.error(
                    "Request failed: %s attempt=%d/%d retryable=%s",
                    url,
                    attempt,
                    total_attempts,
                    is_retryable_exception(error),
                )
                raise

            retry_after_header = None

            if isinstance(error, requests.HTTPError):
                response = error.response

                if response is not None:
                    retry_after_header = response.headers.get(
                        "Retry-After"
                    )

            retry_number = attempt
            delay = calculate_retry_delay(
                attempt_number=retry_number,
                backoff_seconds=retry_backoff_seconds,
                retry_after_header=retry_after_header,
            )
            logger.warning(
                "Retryable request failure: %s attempt=%d/%d retry=%d/%d "
                "delay=%.2f",
                url,
                attempt,
                total_attempts,
                retry_number,
                max_retries,
                delay,
            )
            sleep_function(delay)

    raise RuntimeError("unreachable request retry state")


def normalise_domain(url: str) -> str:
    """
    Extract and normalise the domain from a URL.

    Example:
        https://www.example.com/contact
        becomes:
        example.com
    """

    domain = urlparse(url).hostname or ""
    domain = domain.casefold()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def clean_link(base_url: str, href: str) -> str | None:
    """
    Convert a page link into a clean absolute HTTP or HTTPS URL.

    Returns None for unsupported links such as:
    mailto:, tel:, javascript:, and page anchors.
    """

    href = href.strip()

    if not href:
        return None

    ignored_prefixes = (
        "mailto:",
        "tel:",
        "javascript:",
        "data:",
    )

    if href.casefold().startswith(ignored_prefixes):
        return None

    if href.startswith("#"):
        return None

    absolute_url = urljoin(base_url, href)

    absolute_url, _fragment = urldefrag(absolute_url)

    parsed_url = urlparse(absolute_url)

    if parsed_url.scheme not in {"http", "https"}:
        return None

    return absolute_url


def extract_visible_text(soup: BeautifulSoup) -> str:
    """
    Extract human-visible text while removing scripts,
    styles, templates, and other non-content elements.
    """

    for unwanted_element in soup(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
        ]
    ):
        unwanted_element.decompose()

    text_source = soup.body or soup

    return " ".join(text_source.stripped_strings)


def extract_emails(
    soup: BeautifulSoup,
    visible_text: str,
) -> list[str]:
    """
    Extract email addresses from visible text and mailto links.
    """

    emails = {
        email.casefold()
        for email in EMAIL_PATTERN.findall(visible_text)
    }

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        if not href.casefold().startswith("mailto:"):
            continue

        email_value = href.split(":", 1)[1]
        email_value = email_value.split("?")[0].strip()

        if EMAIL_PATTERN.fullmatch(email_value):
            emails.add(email_value.casefold())

    return sorted(emails)


def extract_phone_numbers(
    soup: BeautifulSoup,
    visible_text: str,
) -> list[str]:
    """
    Extract probable German telephone numbers from visible text
    and telephone links.
    """

    phone_numbers = {
        phone.strip(" \t\r\n.,;:")
        for phone in PHONE_PATTERN.findall(visible_text)
    }

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        if not href.casefold().startswith("tel:"):
            continue

        phone_value = href.split(":", 1)[1].strip()

        if phone_value:
            phone_numbers.add(phone_value)

    return sorted(phone_numbers)


def extract_links(
    soup: BeautifulSoup,
    base_url: str,
) -> tuple[list[str], list[str], list[str]]:
    """
    Extract absolute, internal, and contact-related links.

    Returns:
        A tuple containing all valid absolute links, internal links from the
        same domain, and contact-related links.
    """

    absolute_links, internal_links, contact_links, _discovered = (
        extract_link_details(
            soup=soup,
            base_url=base_url,
        )
    )

    return absolute_links, internal_links, contact_links


def extract_link_details(
    soup: BeautifulSoup,
    base_url: str,
) -> tuple[list[str], list[str], list[str], list[DiscoveredLink]]:
    """
    Extract links and preserve internal-link anchor text for prioritisation.
    """

    base_domain = normalise_domain(base_url)

    absolute_links: set[str] = set()
    internal_links: set[str] = set()
    contact_links: set[str] = set()
    discovered_internal_links: list[DiscoveredLink] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        absolute_url = clean_link(
            base_url=base_url,
            href=href,
        )

        if absolute_url is None:
            continue

        absolute_links.add(absolute_url)

        anchor_text = anchor.get_text(
            " ",
            strip=True,
        )

        searchable_value = (
            f"{anchor_text.casefold()} {absolute_url.casefold()}"
        )

        if any(
            keyword in searchable_value
            for keyword in CONTACT_KEYWORDS
        ):
            contact_links.add(absolute_url)

        if normalise_domain(absolute_url) != base_domain:
            continue

        internal_links.add(absolute_url)
        discovered_internal_links.append(
            DiscoveredLink(
                url=absolute_url,
                anchor_text=anchor_text,
            )
        )

    return (
        sorted(absolute_links),
        sorted(internal_links),
        sorted(contact_links),
        discovered_internal_links,
    )


def parse_page(
    url: str,
    html: str,
) -> ScrapedPage:
    """
    Parse webpage HTML and return structured information.
    """

    logger.debug("Parsing page: %s", url)
    soup = BeautifulSoup(html, "lxml")

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True,
        )

    main_heading = ""

    heading = soup.find("h1")

    if heading:
        main_heading = heading.get_text(
            " ",
            strip=True,
        )

    (
        absolute_links,
        internal_links,
        contact_links,
        discovered_internal_links,
    ) = extract_link_details(
        soup=soup,
        base_url=url,
    )

    visible_text = extract_visible_text(soup)

    emails = extract_emails(
        soup=soup,
        visible_text=visible_text,
    )

    phone_numbers = extract_phone_numbers(
        soup=soup,
        visible_text=visible_text,
    )

    scraped_page = ScrapedPage(
        url=url,
        title=title,
        main_heading=main_heading,
        visible_text=visible_text,
        emails=emails,
        phone_numbers=phone_numbers,
        absolute_links=absolute_links,
        internal_links=internal_links,
        contact_links=contact_links,
        discovered_internal_links=discovered_internal_links,
    )

    logger.debug(
        "Extracted counts for %s: emails=%d phones=%d absolute_links=%d "
        "internal_links=%d contact_links=%d",
        url,
        len(scraped_page.emails),
        len(scraped_page.phone_numbers),
        len(scraped_page.absolute_links),
        len(scraped_page.internal_links),
        len(scraped_page.contact_links),
    )

    return scraped_page


def scrape_page(
    url: str,
    *,
    timeout: float = DEFAULT_REQUEST_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    sleep_function: Callable[[float], None] = time.sleep,
) -> ScrapedPage:
    """
    Download and parse one webpage.
    """

    html = download_page(
        url,
        timeout=timeout,
        user_agent=user_agent,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        sleep_function=sleep_function,
    )

    return parse_page(
        url=url,
        html=html,
    )
