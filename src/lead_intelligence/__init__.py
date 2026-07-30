from __future__ import annotations

from .crawler import (
    CrawlFailure,
    CrawledWebsite,
    crawl_website,
    normalise_crawl_url,
)
from .scorer import (
    LeadScore,
    ScoreBreakdownItem,
    build_score_summary,
    classify_priority,
    score_lead,
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
    "LeadScore",
    "ScrapedPage",
    "ScoreBreakdownItem",
    "SignalEvidence",
    "build_score_summary",
    "classify_priority",
    "create_excerpt",
    "crawl_website",
    "detect_signals_from_pages",
    "detect_signals_in_text",
    "normalise_crawl_url",
    "normalise_text",
    "parse_page",
    "score_lead",
    "scrape_page",
]
