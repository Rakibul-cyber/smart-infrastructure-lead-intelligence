from __future__ import annotations

import logging
import sys

import requests

from .config import load_config_with_env_file
from .crawler import crawl_website
from .logging_config import configure_logging
from .scorer import score_lead
from .signal_detector import detect_signals_from_pages
from .static_scraper import scrape_page


logger = logging.getLogger(__name__)


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


def format_yes_no(value: bool) -> str:
    """Format a boolean value for console output."""

    if value:
        return "Yes"

    return "No"


def format_criterion_name(criterion: str) -> str:
    """Format a score criterion for console output."""

    return criterion.replace("_", " ").capitalize()


def main() -> None:
    """Run static scraper and crawler demonstrations."""

    try:
        config = load_config_with_env_file()

    except ValueError as error:
        print(f"Configuration error: {error}")
        sys.exit(2)

    configure_logging(
        log_level=config.log_level,
        log_file=config.log_file,
    )
    logger.info("Application started")

    target_url = "https://example.com"

    print("=" * 70)
    print("SMART INFRASTRUCTURE LEAD INTELLIGENCE")
    print("=" * 70)
    print("\nCONFIGURATION")
    print("-" * 70)
    print(f"Max pages per site: {config.max_pages_per_site}")
    print(f"Request timeout: {config.request_timeout}")
    print(f"Output directory: {config.output_directory}")
    print(f"Target URL: {target_url}")
    print("Downloading and analysing webpage...")

    try:
        result = scrape_page(
            target_url,
            timeout=config.request_timeout,
            user_agent=config.user_agent,
        )

    except requests.RequestException as error:
        logger.warning("Static scraper demonstration failed: %s", error)
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
            max_pages=config.max_pages_per_site,
            request_timeout=config.request_timeout,
            user_agent=config.user_agent,
        )

    except requests.RequestException as error:
        logger.error("Crawler demonstration failed: %s", error)
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

    signals = detect_signals_from_pages(
        crawled_website.page_results
    )

    print("\n" + "=" * 70)
    print("BUSINESS SIGNALS")
    print("=" * 70)
    print(
        "Street lighting: "
        f"{format_yes_no(signals.street_lighting)}"
    )
    print(f"Smart city: {format_yes_no(signals.smart_city)}")
    print(
        "Energy efficiency: "
        f"{format_yes_no(signals.energy_efficiency)}"
    )
    print(
        "Climate action: "
        f"{format_yes_no(signals.climate_action)}"
    )
    print(
        "Infrastructure modernisation: "
        f"{format_yes_no(signals.infrastructure_modernisation)}"
    )
    print(f"Procurement: {format_yes_no(signals.procurement)}")
    print(
        "Municipal utility: "
        f"{format_yes_no(signals.municipal_utility)}"
    )
    print(
        "Matched keywords: "
        f"{len(signals.matched_keywords)}"
    )

    print("\nEvidence:")

    if not signals.evidence:
        print("- None found")
    else:
        for evidence_item in signals.evidence[:5]:
            print(
                f"[{evidence_item.category}] "
                f"{evidence_item.keyword} — "
                f"{evidence_item.excerpt} — "
                f"{evidence_item.source_url}"
            )

    lead_score = score_lead(
        signals=signals,
        emails=crawled_website.emails,
        phone_numbers=crawled_website.phone_numbers,
    )

    print("\n" + "=" * 70)
    print("LEAD SCORE")
    print("=" * 70)
    print(f"Total score: {lead_score.total_score}/100")
    print(f"Priority: {lead_score.priority}")
    print(f"Summary: {lead_score.summary}")
    print("\nBreakdown:")

    if not lead_score.breakdown:
        print("- None")
    else:
        for breakdown_item in lead_score.breakdown:
            print(
                f"+{breakdown_item.points} "
                f"{format_criterion_name(breakdown_item.criterion)} — "
                f"{breakdown_item.reason}"
            )

    print(
        "\nRun `python -m tests.manual_export_demo` to generate the "
        "fictional Excel demonstration."
    )
    print(
        "Run `python -m tests.manual_dashboard_demo` to view the "
        "fictional management dashboard."
    )
    logger.info("Application finished")


if __name__ == "__main__":
    main()
