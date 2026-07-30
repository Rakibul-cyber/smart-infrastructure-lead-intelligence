from __future__ import annotations

import argparse
import logging
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import __version__
from .batch import (
    BatchResult,
    build_dynamic_options_from_config,
    export_batch_failures,
    read_parsed_organisations_csv,
    run_batch_analysis,
)
from .config import AppConfig, load_config_with_env_file
from .crawler import CrawledWebsite, crawl_website
from .dashboard import build_dashboard_summary, print_dashboard
from .demo_data import print_demo_dashboard, run_demo_export
from .dynamic_scraper import DynamicScraperError, validate_css_selector
from .exporter import LeadRecord, build_lead_record, export_leads_to_excel
from .logging_config import configure_logging
from .scorer import LeadScore, score_lead
from .signal_detector import DetectedSignals, detect_signals_from_pages


logger = logging.getLogger(__name__)

VERSION_TEXT = f"Smart Infrastructure Lead Intelligence {__version__}"


def validate_website_url(value: str) -> str:
    """Validate a complete HTTP or HTTPS website URL for analysis."""

    stripped_value = value.strip()
    parsed_url = urlparse(stripped_value)

    if parsed_url.scheme not in {"http", "https"}:
        raise argparse.ArgumentTypeError(
            "--website must use http or https."
        )

    if not parsed_url.hostname:
        raise argparse.ArgumentTypeError(
            "--website must include a hostname."
        )

    if parsed_url.username or parsed_url.password:
        raise argparse.ArgumentTypeError(
            "--website must not contain embedded credentials."
        )

    return stripped_value


def sanitise_filename(value: str) -> str:
    """Return a filesystem-friendly lowercase filename stem."""

    lowered_value = value.lower()
    replaced_value = re.sub(r"[^a-z0-9_-]+", "_", lowered_value)
    collapsed_value = re.sub(r"_+", "_", replaced_value)
    sanitised_value = collapsed_value.strip("_-")

    if not sanitised_value:
        return "organisation"

    return sanitised_value


def positive_int(value: str) -> int:
    """Parse an integer that must be at least one."""

    try:
        parsed_value = int(value)

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "value must be a valid integer."
        ) from error

    if parsed_value < 1:
        raise argparse.ArgumentTypeError(
            "value must be at least 1."
        )

    return parsed_value


def positive_float(value: str) -> float:
    """Parse a float that must be greater than zero."""

    try:
        parsed_value = float(value)

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "value must be a valid number."
        ) from error

    if parsed_value <= 0:
        raise argparse.ArgumentTypeError(
            "value must be greater than zero."
        )

    return parsed_value


def non_negative_int(value: str) -> int:
    """Parse an integer that may be zero or greater."""

    try:
        parsed_value = int(value)

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "value must be a valid integer."
        ) from error

    if parsed_value < 0:
        raise argparse.ArgumentTypeError(
            "value must be zero or greater."
        )

    return parsed_value


def non_negative_float(value: str) -> float:
    """Parse a float that may be zero or greater."""

    try:
        parsed_value = float(value)

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "value must be a valid number."
        ) from error

    if parsed_value < 0:
        raise argparse.ArgumentTypeError(
            "value must be zero or greater."
        )

    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="python -m src.lead_intelligence",
        description="Smart infrastructure lead intelligence tools.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyse_parser = subparsers.add_parser(
        "analyse",
        help="Analyse one organisation website.",
    )
    analyse_parser.add_argument(
        "--website",
        required=True,
        type=validate_website_url,
    )
    analyse_parser.add_argument("--name", required=True)
    analyse_parser.add_argument("--type", default="Unknown")
    analyse_parser.add_argument("--city", default="")
    analyse_parser.add_argument("--state", default="")
    analyse_parser.add_argument("--output", type=Path)
    analyse_parser.add_argument("--max-pages", type=positive_int)
    analyse_parser.add_argument("--timeout", type=positive_float)
    analyse_parser.add_argument("--request-delay", type=non_negative_float)
    analyse_parser.add_argument("--max-retries", type=non_negative_int)
    analyse_parser.add_argument("--retry-backoff", type=non_negative_float)
    analyse_parser.add_argument("--top-limit", type=positive_int)
    add_browser_arguments(analyse_parser)
    analyse_parser.add_argument(
        "--no-export",
        action="store_true",
        help="Do not create an Excel report.",
    )
    analyse_parser.set_defaults(handler=handle_analyse)

    batch_parser = subparsers.add_parser(
        "batch",
        help="Analyse organisations from a CSV input file.",
    )
    batch_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="CSV file containing organisations to analyse.",
    )
    batch_parser.add_argument("--output", type=Path)
    batch_parser.add_argument("--failures-output", type=Path)
    batch_parser.add_argument("--top-limit", type=positive_int)
    batch_parser.add_argument("--max-pages", type=positive_int)
    batch_parser.add_argument("--timeout", type=positive_float)
    batch_parser.add_argument("--request-delay", type=non_negative_float)
    batch_parser.add_argument("--max-retries", type=non_negative_int)
    batch_parser.add_argument("--retry-backoff", type=non_negative_float)
    add_browser_arguments(batch_parser)
    batch_parser.add_argument(
        "--no-export",
        action="store_true",
        help="Do not create an Excel report.",
    )
    batch_parser.add_argument(
        "--no-failure-report",
        action="store_true",
        help="Do not create a CSV report of failed rows.",
    )
    batch_parser.set_defaults(handler=handle_batch)

    demo_export_parser = subparsers.add_parser(
        "demo-export",
        help="Generate a fictional Excel demonstration report.",
    )
    demo_export_parser.set_defaults(handler=handle_demo_export)

    demo_dashboard_parser = subparsers.add_parser(
        "demo-dashboard",
        help="Print a fictional management dashboard.",
    )
    demo_dashboard_parser.set_defaults(handler=handle_demo_dashboard)

    version_parser = subparsers.add_parser(
        "version",
        help="Print package version.",
    )
    version_parser.set_defaults(handler=handle_version)

    return parser


def add_browser_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared browser-rendering arguments."""

    parser.add_argument(
        "--scrape-mode",
        choices=("static", "dynamic", "auto"),
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chromium in headed mode when browser rendering is used.",
    )
    parser.add_argument("--browser-timeout", type=positive_float)
    parser.add_argument("--wait-for-selector")
    parser.add_argument("--browser-wait", type=non_negative_float)
    parser.add_argument(
        "--accept-cookies",
        action="store_true",
        help="Click a conservative common cookie-accept button if present.",
    )


def apply_overrides(
    config: AppConfig,
    args: argparse.Namespace,
) -> AppConfig:
    """Return a config copy with provided CLI overrides applied."""

    replacements: dict[str, object] = {}

    if getattr(args, "max_pages", None) is not None:
        replacements["max_pages_per_site"] = args.max_pages

    if getattr(args, "timeout", None) is not None:
        replacements["request_timeout"] = args.timeout

    if getattr(args, "request_delay", None) is not None:
        replacements["request_delay_seconds"] = args.request_delay

    if getattr(args, "max_retries", None) is not None:
        replacements["max_retries"] = args.max_retries

    if getattr(args, "retry_backoff", None) is not None:
        replacements["retry_backoff_seconds"] = args.retry_backoff

    if getattr(args, "top_limit", None) is not None:
        replacements["top_leads_limit"] = args.top_limit

    if getattr(args, "scrape_mode", None) is not None:
        replacements["scrape_mode"] = args.scrape_mode

    if getattr(args, "headed", False):
        replacements["browser_headless"] = False

    if getattr(args, "browser_timeout", None) is not None:
        replacements["browser_timeout_seconds"] = args.browser_timeout

    if getattr(args, "wait_for_selector", None) is not None:
        replacements["browser_wait_for_selector"] = validate_css_selector(
            args.wait_for_selector
        )

    if getattr(args, "browser_wait", None) is not None:
        replacements["browser_wait_after_load_seconds"] = args.browser_wait

    if getattr(args, "accept_cookies", False):
        replacements["browser_accept_cookies"] = True

    if not replacements:
        return config

    return replace(config, **replacements)


def handle_analyse(args: argparse.Namespace) -> int:
    """Run the one-organisation analysis command."""

    try:
        base_config = load_config_with_env_file()
        config = apply_overrides(base_config, args)

    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2

    configure_logging(
        log_level=config.log_level,
        log_file=config.log_file,
    )
    logger.info("CLI analyse command started")
    print(f"Scraping mode: {config.scrape_mode}")

    try:
        crawler_result = crawl_website(
            args.website,
            max_pages=config.max_pages_per_site,
            request_timeout=config.request_timeout,
            user_agent=config.user_agent,
            max_retries=config.max_retries,
            retry_backoff_seconds=config.retry_backoff_seconds,
            request_delay_seconds=config.request_delay_seconds,
            scrape_mode=config.scrape_mode,
            dynamic_options=build_dynamic_options_from_config(config),
        )

    except (requests.RequestException, DynamicScraperError) as error:
        logger.error("Analysis crawl failed: %s", error)
        print(f"Analysis failed: {error}")
        return 1

    if not crawler_result.page_results:
        print("Analysis failed: no pages were successfully analysed.")
        return 1

    signals = detect_signals_from_pages(crawler_result.page_results)
    lead_score = score_lead(
        signals=signals,
        emails=crawler_result.emails,
        phone_numbers=crawler_result.phone_numbers,
    )
    last_checked = datetime.now().astimezone().isoformat(timespec="seconds")
    lead_record = build_lead_record(
        organisation_name=args.name,
        organisation_type=args.type,
        city=args.city,
        state=args.state,
        website=args.website,
        crawler_result=crawler_result,
        signals=signals,
        lead_score=lead_score,
        last_checked=last_checked,
    )
    dashboard_summary = build_dashboard_summary(
        [lead_record],
        top_limit=config.top_leads_limit,
    )
    print_dashboard(dashboard_summary)
    print_analysis_summary(
        lead_record=lead_record,
        crawler_result=crawler_result,
        signals=signals,
        lead_score=lead_score,
    )

    if not args.no_export:
        output_path = args.output or build_default_output_path(
            output_directory=config.output_directory,
            organisation_name=args.name,
            checked_at=datetime.now().astimezone(),
        )
        exported_path = export_leads_to_excel(
            records=[lead_record],
            evidence_by_website={args.website: signals.evidence},
            output_path=output_path,
        )
        print(f"\nExcel report written to: {exported_path}")

    logger.info("CLI analyse command finished")

    return 0


def handle_batch(args: argparse.Namespace) -> int:
    """Run batch analysis from a CSV input file."""

    try:
        base_config = load_config_with_env_file()
        config = apply_overrides(base_config, args)
        parsed_organisations = read_parsed_organisations_csv(args.input)

    except FileNotFoundError as error:
        print(f"CSV error: input file not found: {error.filename}")
        return 2

    except ValueError as error:
        print(f"Configuration or CSV error: {error}")
        return 2

    configure_logging(
        log_level=config.log_level,
        log_file=config.log_file,
    )
    logger.info("CLI batch command started")
    print(f"Scraping mode: {config.scrape_mode}")

    timestamp = datetime.now().astimezone()

    try:
        batch_result = run_batch_analysis(
            organisations=parsed_organisations,
            config=config,
        )

    except ValueError as error:
        print(f"Batch error: {error}")
        return 2

    excel_report: Path | None = None
    failure_report: Path | None = None

    if batch_result.successful_records:
        dashboard_summary = build_dashboard_summary(
            batch_result.successful_records,
            top_limit=config.top_leads_limit,
        )
        print_dashboard(dashboard_summary)

        if not args.no_export:
            excel_report = export_leads_to_excel(
                records=batch_result.successful_records,
                evidence_by_website=batch_result.evidence_by_website,
                output_path=args.output
                or build_batch_output_path(
                    output_directory=config.output_directory,
                    checked_at=timestamp,
                ),
            )

    if not args.no_failure_report:
        failure_report = export_batch_failures(
            failures=batch_result.failures,
            output_path=args.failures_output
            or build_batch_failures_output_path(
                output_directory=config.output_directory,
                checked_at=timestamp,
            ),
        )

    print_batch_summary(
        batch_result=batch_result,
        excel_report=excel_report,
        failure_report=failure_report,
        export_disabled=args.no_export,
        failure_report_disabled=args.no_failure_report,
    )

    if excel_report is not None:
        print(f"\nExcel report written to: {excel_report}")

    if failure_report is not None:
        print(f"Failure report written to: {failure_report}")

    logger.info("CLI batch command finished")

    if batch_result.failures:
        return 1

    return 0


def print_analysis_summary(
    lead_record: LeadRecord,
    crawler_result: CrawledWebsite,
    signals: DetectedSignals,
    lead_score: LeadScore,
) -> None:
    """Print a concise organisation analysis summary."""

    print("\nORGANISATION ANALYSIS")
    print("-" * 70)
    print(f"Organisation name: {lead_record.organisation_name}")
    print(f"Website: {lead_record.website}")
    print(f"Pages visited: {lead_record.visited_pages}")
    print(f"Failed pages: {len(crawler_result.failed_pages)}")
    print(f"Emails found: {len(lead_record.emails)}")
    print(f"Phone numbers found: {len(lead_record.phone_numbers)}")
    print(f"Evidence count: {len(signals.evidence)}")
    print(f"Score: {lead_score.total_score}/100")
    print(f"Priority: {lead_score.priority}")
    print(f"Score summary: {lead_score.summary}")


def build_default_output_path(
    output_directory: Path,
    organisation_name: str,
    checked_at: datetime,
) -> Path:
    """Build the default Excel report path for one analysis run."""

    timestamp = checked_at.strftime("%Y%m%d_%H%M%S")
    filename = (
        f"lead_report_{sanitise_filename(organisation_name)}_"
        f"{timestamp}.xlsx"
    )

    return output_directory / filename


def build_batch_output_path(
    output_directory: Path,
    checked_at: datetime,
) -> Path:
    """Build the default Excel report path for a batch run."""

    timestamp = checked_at.strftime("%Y%m%d_%H%M%S")

    return output_directory / f"batch_lead_report_{timestamp}.xlsx"


def build_batch_failures_output_path(
    output_directory: Path,
    checked_at: datetime,
) -> Path:
    """Build the default failure CSV path for a batch run."""

    timestamp = checked_at.strftime("%Y%m%d_%H%M%S")

    return output_directory / f"batch_failures_{timestamp}.csv"


def print_batch_summary(
    batch_result: BatchResult,
    excel_report: Path | None,
    failure_report: Path | None,
    *,
    export_disabled: bool,
    failure_report_disabled: bool,
) -> None:
    """Print a concise batch analysis summary."""

    if excel_report is not None:
        excel_report_text = str(excel_report)
    elif export_disabled:
        excel_report_text = "disabled"
    else:
        excel_report_text = "not created"

    if failure_report is not None:
        failure_report_text = str(failure_report)
    elif failure_report_disabled:
        failure_report_text = "disabled"
    else:
        failure_report_text = "not created"

    print("\nBATCH ANALYSIS")
    print("-" * 70)
    print(f"Total input rows: {batch_result.total_input_rows}")
    print(f"Successful: {len(batch_result.successful_records)}")
    print(f"Failed: {len(batch_result.failures)}")
    print(f"Excel report: {excel_report_text}")
    print(f"Failure report: {failure_report_text}")


def handle_demo_export(args: argparse.Namespace) -> int:
    """Run the fictional Excel export demonstration."""

    try:
        config = load_config_with_env_file()

    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2

    configure_logging(
        log_level=config.log_level,
        log_file=config.log_file,
    )
    output_path = run_demo_export(config.output_directory)

    print(f"Excel demo report written to: {output_path}")

    return 0


def handle_demo_dashboard(args: argparse.Namespace) -> int:
    """Run the fictional dashboard demonstration."""

    try:
        config = load_config_with_env_file()

    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2

    configure_logging(
        log_level=config.log_level,
        log_file=config.log_file,
    )
    print_demo_dashboard(top_limit=config.top_leads_limit)

    return 0


def handle_version(args: argparse.Namespace) -> int:
    """Print version information."""

    print(VERSION_TEXT)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()

    try:
        args = parser.parse_args(argv)

    except SystemExit as error:
        code = error.code

        if isinstance(code, int):
            return code

        return 2

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args)
