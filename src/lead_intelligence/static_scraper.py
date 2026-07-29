from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


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


def download_page(url: str) -> str:
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

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; SmartInfrastructureLeadIntelligence/0.1)"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()

    return response.text


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

    base_domain = normalise_domain(base_url)

    absolute_links: set[str] = set()
    internal_links: set[str] = set()
    contact_links: set[str] = set()

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
        ).casefold()

        searchable_value = (
            f"{anchor_text} {absolute_url.casefold()}"
        )

        if any(
            keyword in searchable_value
            for keyword in CONTACT_KEYWORDS
        ):
            contact_links.add(absolute_url)

        if normalise_domain(absolute_url) != base_domain:
            continue

        internal_links.add(absolute_url)

    return (
        sorted(absolute_links),
        sorted(internal_links),
        sorted(contact_links),
    )


def parse_page(
    url: str,
    html: str,
) -> ScrapedPage:
    """
    Parse webpage HTML and return structured information.
    """

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

    absolute_links, internal_links, contact_links = extract_links(
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

    return ScrapedPage(
        url=url,
        title=title,
        main_heading=main_heading,
        visible_text=visible_text,
        emails=emails,
        phone_numbers=phone_numbers,
        absolute_links=absolute_links,
        internal_links=internal_links,
        contact_links=contact_links,
    )


def scrape_page(url: str) -> ScrapedPage:
    """
    Download and parse one webpage.
    """

    html = download_page(url)

    return parse_page(
        url=url,
        html=html,
    )
