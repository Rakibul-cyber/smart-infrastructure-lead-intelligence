from __future__ import annotations

from .crawler import (
    CrawlFailure,
    CrawledWebsite,
    crawl_website,
    normalise_crawl_url,
)
from .exporter import (
    LeadRecord,
    build_lead_record,
    export_leads_to_excel,
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
    "LeadRecord",
    "LeadScore",
    "ScrapedPage",
    "ScoreBreakdownItem",
    "SignalEvidence",
    "build_lead_record",
    "build_score_summary",
    "classify_priority",
    "create_excerpt",
    "crawl_website",
    "detect_signals_from_pages",
    "detect_signals_in_text",
    "export_leads_to_excel",
    "normalise_crawl_url",
    "normalise_text",
    "parse_page",
    "score_lead",
    "scrape_page",
]
