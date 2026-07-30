from __future__ import annotations

from .crawler import (
    CrawlFailure,
    CrawledWebsite,
    crawl_website,
    normalise_crawl_url,
)
from .signal_detector import (
    DetectedSignals,
    SignalEvidence,
    create_excerpt,
    detect_signals_from_pages,
    detect_signals_in_text,
    normalise_text,
)
from .static_scraper import (
    ScrapedPage,
    parse_page,
    scrape_page,
)


__all__ = [
    "CrawlFailure",
    "CrawledWebsite",
    "DetectedSignals",
    "ScrapedPage",
    "SignalEvidence",
    "create_excerpt",
    "crawl_website",
    "detect_signals_from_pages",
    "detect_signals_in_text",
    "normalise_crawl_url",
    "normalise_text",
    "parse_page",
    "scrape_page",
]
