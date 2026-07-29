from __future__ import annotations

import sys
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class PageInformation:
    """Structured information extracted from one webpage."""

    url: str
    title: str
    main_heading: str
    links: list[str]


def download_page(url: str) -> str:
    """
    Download raw HTML from a public webpage.

    Args:
        url: The complete webpage URL.

    Returns:
        The webpage HTML.

    Raises:
        requests.RequestException:
            If the webpage cannot be downloaded successfully.
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


def extract_page_information(
    url: str,
    html: str,
) -> PageInformation:
    """
    Extract basic structured information from HTML.

    Args:
        url: The original webpage URL.
        html: Raw webpage HTML.

    Returns:
        A PageInformation object containing the extracted data.
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

    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if isinstance(href, str):
            links.append(href)

    return PageInformation(
        url=url,
        title=title,
        main_heading=main_heading,
        links=links,
    )


def main() -> None:
    """Run the first static scraping demonstration."""

    target_url = "https://example.com"

    print("=" * 60)
    print("SMART INFRASTRUCTURE LEAD INTELLIGENCE")
    print("=" * 60)
    print(f"Target URL: {target_url}")
    print("Downloading webpage...")

    try:
        html = download_page(target_url)

        page_information = extract_page_information(
            url=target_url,
            html=html,
        )

    except requests.RequestException as error:
        print(f"Download failed: {error}")
        sys.exit(1)

    print("\nScraping completed successfully.")
    print(f"Page title: {page_information.title}")
    print(f"Main heading: {page_information.main_heading}")
    print(f"Links found: {len(page_information.links)}")

    for position, link in enumerate(
        page_information.links,
        start=1,
    ):
        print(f"{position}. {link}")


if __name__ == "__main__":
    main()
