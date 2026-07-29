from __future__ import annotations

from pathlib import Path

from src.lead_intelligence.static_scraper import ScrapedPage, parse_page


def print_list(heading: str, values: list[str]) -> None:
    """Print a field list from a parsed sample page."""

    print(f"\n{heading}:")

    if not values:
        print("- None found")
        return

    for value in values:
        print(f"- {value}")


def print_page(page: ScrapedPage) -> None:
    """Print parsed fields from a scraped page object."""

    print(f"URL: {page.url}")
    print(f"Title: {page.title}")
    print(f"Main heading: {page.main_heading}")
    print(f"Visible text: {page.visible_text}")
    print_list("Emails", page.emails)
    print_list("Phone numbers", page.phone_numbers)
    print_list("Absolute links", page.absolute_links)
    print_list("Internal links", page.internal_links)
    print_list("Contact-related links", page.contact_links)


def main() -> None:
    """Load the HTML fixture and run the static parser."""

    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "sample_municipality.html"
    )
    html = fixture_path.read_text(encoding="utf-8")
    page = parse_page("https://example-city.de", html)

    print_page(page)


if __name__ == "__main__":
    main()
