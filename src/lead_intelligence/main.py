from __future__ import annotations

import requests

from .crawler import crawl_website
from .static_scraper import scrape_page


def print_list(
    heading: str,
    values: list[str],
    limit: int | None = None,
) -> None:
    """
    Print a titled list with optional result limiting.
    """

    print(f"\n{heading}: {len(values)}")

    displayed_values = (
        values[:limit]
        if limit is not None
        else values
    )

    if not displayed_values:
        print("- None found")
        return

    for position, value in enumerate(
        displayed_values,
        start=1,
    ):
        print(f"{position}. {value}")

    if (
        limit is not None
        and len(values) > limit
    ):
        remaining = len(values) - limit
        print(f"... and {remaining} more")


def main() -> None:
    """Run static scraper and crawler demonstrations."""

    target_url = "https://example.com"

    print("=" * 70)
    print("SMART INFRASTRUCTURE LEAD INTELLIGENCE")
    print("=" * 70)
    print(f"Target URL: {target_url}")
    print("Downloading and analysing webpage...")

    try:
        result = scrape_page(target_url)

    except requests.RequestException as error:
        print(f"\nScraping failed: {error}")
    else:
        print("\nScraping completed successfully.")

        print(f"\nPage title: {result.title}")
        print(f"Main heading: {result.main_heading}")
        print(
            "Visible text preview: "
            f"{result.visible_text[:300]}"
        )

        print_list(
            heading="Email addresses",
            values=result.emails,
        )

        print_list(
            heading="Telephone numbers",
            values=result.phone_numbers,
        )

        print_list(
            heading="Absolute links",
            values=result.absolute_links,
            limit=10,
        )

        print_list(
            heading="Internal links",
            values=result.internal_links,
            limit=10,
        )

        print_list(
            heading="Contact-related links",
            values=result.contact_links,
            limit=10,
        )

    print("\n" + "=" * 70)
    print("CONTROLLED WEBSITE CRAWL")
    print("=" * 70)

    try:
        crawled_website = crawl_website(
            "https://example.com",
            max_pages=2,
        )

    except requests.RequestException as error:
        print(f"\nCrawling failed: {error}")
        return

    print(
        "\nSuccessfully visited pages: "
        f"{len(crawled_website.visited_urls)}"
    )

    print_list(
        heading="Visited URLs",
        values=crawled_website.visited_urls,
    )

    print(
        "\nFailed pages: "
        f"{len(crawled_website.failed_pages)}"
    )

    print_list(
        heading="Combined emails",
        values=crawled_website.emails,
    )

    print_list(
        heading="Combined phone numbers",
        values=crawled_website.phone_numbers,
    )

    print_list(
        heading="Combined contact links",
        values=crawled_website.contact_links,
    )


if __name__ == "__main__":
    main()
