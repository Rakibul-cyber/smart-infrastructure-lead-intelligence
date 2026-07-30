from __future__ import annotations

from .config import (
    AppConfig,
    load_config,
    load_config_with_env_file,
    load_env_file,
    normalise_log_level,
    parse_positive_float,
    parse_positive_int,
)
from .crawler import (
    CrawlFailure,
    CrawledWebsite,
    crawl_website,
    normalise_crawl_url,
)
from .dashboard import (
    DashboardSummary,
    SignalCount,
    build_dashboard_summary,
    format_dashboard,
    print_dashboard,
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
    "AppConfig",
    "CrawlFailure",
    "CrawledWebsite",
    "DashboardSummary",
    "DetectedSignals",
    "LeadRecord",
    "LeadScore",
    "ScrapedPage",
    "ScoreBreakdownItem",
    "SignalCount",
    "SignalEvidence",
    "build_dashboard_summary",
    "build_lead_record",
    "build_score_summary",
    "classify_priority",
    "create_excerpt",
    "crawl_website",
    "detect_signals_from_pages",
    "detect_signals_in_text",
    "export_leads_to_excel",
    "format_dashboard",
    "load_config",
    "load_config_with_env_file",
    "load_env_file",
    "normalise_crawl_url",
    "normalise_log_level",
    "normalise_text",
    "parse_page",
    "parse_positive_float",
    "parse_positive_int",
    "print_dashboard",
    "score_lead",
    "scrape_page",
]
