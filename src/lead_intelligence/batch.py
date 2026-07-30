from __future__ import annotations

import csv
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from .config import AppConfig
from .crawler import CrawledWebsite, crawl_website
from .dynamic_scraper import DynamicPageOptions, DynamicScraperError
from .exporter import LeadRecord, build_lead_record
from .scorer import score_lead
from .signal_detector import SignalEvidence, detect_signals_from_pages


logger = logging.getLogger(__name__)


@dataclass
class OrganisationInput:
    """One organisation supplied by a batch CSV input file."""

    organisation_name: str
    organisation_type: str
    city: str
    state: str
    website: str


@dataclass
class BatchFailure:
    """One organisation row that could not be analysed."""

    row_number: int
    organisation_name: str
    website: str
    error: str


@dataclass
class BatchResult:
    """Combined result of a sequential batch analysis run."""

    total_input_rows: int
    successful_records: list[LeadRecord]
    evidence_by_website: dict[str, list[SignalEvidence]]
    failures: list[BatchFailure]


@dataclass
class ParsedOrganisationRow:
    """Organisation input with its physical CSV row number."""

    row_number: int
    organisation: OrganisationInput


def normalise_column_name(value: str) -> str:
    """Normalize a CSV column name for flexible matching."""

    stripped_value = value.strip().lower()
    replaced_value = re.sub(r"[\s-]+", "_", stripped_value)
    collapsed_value = re.sub(r"_+", "_", replaced_value)

    return collapsed_value.strip("_")


def read_organisations_csv(
    input_path: str | Path,
) -> list[OrganisationInput]:
    """Read organisation inputs from a UTF-8 CSV file."""

    return [
        parsed_row.organisation
        for parsed_row in read_parsed_organisations_csv(input_path)
    ]


def read_parsed_organisations_csv(
    input_path: str | Path,
) -> list[ParsedOrganisationRow]:
    """Read organisation inputs from CSV while preserving row numbers."""

    path = Path(input_path)
    parsed_rows: list[ParsedOrganisationRow] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        reader = csv.reader(input_file)

        try:
            raw_headers = next(reader)

        except StopIteration as error:
            raise ValueError("CSV file must include a header row.") from error

        normalized_headers = [
            normalise_column_name(header)
            for header in raw_headers
        ]
        duplicate_headers = _find_duplicate_headers(normalized_headers)

        if duplicate_headers:
            raise ValueError(
                "CSV file contains duplicate columns after normalisation: "
                f"{', '.join(duplicate_headers)}."
            )

        required_headers = {"organisation_name", "website"}
        missing_headers = required_headers - set(normalized_headers)

        if missing_headers:
            raise ValueError(
                "CSV file is missing required columns: "
                f"{', '.join(sorted(missing_headers))}."
            )

        for row_number, row in enumerate(reader, start=2):
            values_by_header = {
                header: row[index].strip()
                if index < len(row)
                else ""
                for index, header in enumerate(normalized_headers)
            }

            if not any(value for value in values_by_header.values()):
                continue

            organisation_name = values_by_header.get(
                "organisation_name",
                "",
            )
            website = values_by_header.get("website", "")

            if not organisation_name:
                raise ValueError(
                    f"CSV row {row_number}: organisation_name must not be blank."
                )

            if not website:
                raise ValueError(
                    f"CSV row {row_number}: website must not be blank."
                )

            try:
                validated_website = _validate_website_url(website)

            except ValueError as error:
                raise ValueError(
                    f"CSV row {row_number}: {error}"
                ) from error

            parsed_rows.append(
                ParsedOrganisationRow(
                    row_number=row_number,
                    organisation=OrganisationInput(
                        organisation_name=organisation_name,
                        organisation_type=values_by_header.get(
                            "organisation_type",
                            "",
                        ) or "Unknown",
                        city=values_by_header.get("city", ""),
                        state=values_by_header.get("state", ""),
                        website=validated_website,
                    ),
                )
            )

    if not parsed_rows:
        raise ValueError("CSV file contains no usable data rows.")

    return parsed_rows


def analyse_organisation(
    organisation: OrganisationInput,
    config: AppConfig,
    *,
    crawl_function: Callable[..., CrawledWebsite] = crawl_website,
) -> tuple[LeadRecord, list[SignalEvidence]]:
    """Analyse one organisation without printing or exporting files."""

    logger.info(
        "Organisation analysis started: organisation=%s website=%s",
        organisation.organisation_name,
        organisation.website,
    )
    crawler_result = crawl_function(
        organisation.website,
        max_pages=config.max_pages_per_site,
        request_timeout=config.request_timeout,
        user_agent=config.user_agent,
        max_retries=config.max_retries,
        retry_backoff_seconds=config.retry_backoff_seconds,
        request_delay_seconds=config.request_delay_seconds,
        scrape_mode=config.scrape_mode,
        dynamic_options=build_dynamic_options_from_config(config),
    )

    if not crawler_result.page_results:
        raise RuntimeError(
            "no pages were successfully analysed"
        )

    signals = detect_signals_from_pages(crawler_result.page_results)
    lead_score = score_lead(
        signals=signals,
        emails=crawler_result.emails,
        phone_numbers=crawler_result.phone_numbers,
    )
    last_checked = datetime.now().astimezone().isoformat(timespec="seconds")
    record = build_lead_record(
        organisation_name=organisation.organisation_name,
        organisation_type=organisation.organisation_type,
        city=organisation.city,
        state=organisation.state,
        website=organisation.website,
        crawler_result=crawler_result,
        signals=signals,
        lead_score=lead_score,
        last_checked=last_checked,
    )

    logger.info(
        "Organisation analysis completed: organisation=%s website=%s "
        "visited_pages=%d evidence=%d score=%d priority=%s",
        organisation.organisation_name,
        organisation.website,
        record.visited_pages,
        len(signals.evidence),
        record.lead_score,
        record.priority,
    )

    return record, signals.evidence


def run_batch_analysis(
    organisations: list[ParsedOrganisationRow],
    config: AppConfig,
    *,
    analyse_function: Callable[
        [OrganisationInput, AppConfig],
        tuple[LeadRecord, list[SignalEvidence]],
    ] = analyse_organisation,
) -> BatchResult:
    """Run sequential analysis for all supplied organisations."""

    if not organisations:
        raise ValueError("organisations must not be empty")

    logger.info("Batch analysis started: total_input_rows=%d", len(organisations))

    successful_records: list[LeadRecord] = []
    evidence_by_website: dict[str, list[SignalEvidence]] = {}
    failures: list[BatchFailure] = []

    for parsed_row in organisations:
        organisation = parsed_row.organisation
        logger.info(
            "Batch organisation started: row=%d organisation=%s website=%s",
            parsed_row.row_number,
            organisation.organisation_name,
            organisation.website,
        )

        try:
            record, evidence = analyse_function(organisation, config)

        except (
            RuntimeError,
            ValueError,
            requests.RequestException,
            DynamicScraperError,
        ) as error:
            failures.append(
                BatchFailure(
                    row_number=parsed_row.row_number,
                    organisation_name=organisation.organisation_name,
                    website=organisation.website,
                    error=str(error),
                )
            )
            logger.warning(
                "Batch organisation failed: row=%d organisation=%s "
                "website=%s error=%s",
                parsed_row.row_number,
                organisation.organisation_name,
                organisation.website,
                error,
            )
            continue

        successful_records.append(record)
        _extend_evidence_by_website(
            evidence_by_website=evidence_by_website,
            website=record.website,
            evidence=evidence,
        )
        logger.info(
            "Batch organisation completed: row=%d organisation=%s "
            "website=%s score=%d priority=%s",
            parsed_row.row_number,
            record.organisation_name,
            record.website,
            record.lead_score,
            record.priority,
        )

    logger.info(
        "Batch analysis completed: total_input_rows=%d successful=%d failed=%d",
        len(organisations),
        len(successful_records),
        len(failures),
    )

    return BatchResult(
        total_input_rows=len(organisations),
        successful_records=successful_records,
        evidence_by_website=evidence_by_website,
        failures=failures,
    )


def build_dynamic_options_from_config(config: AppConfig) -> DynamicPageOptions:
    """Build dynamic scraper options from application configuration."""

    return DynamicPageOptions(
        headless=config.browser_headless,
        browser_timeout_seconds=config.browser_timeout_seconds,
        wait_after_load_seconds=config.browser_wait_after_load_seconds,
        wait_for_selector=config.browser_wait_for_selector,
        accept_cookies=config.browser_accept_cookies,
    )


def export_batch_failures(
    failures: list[BatchFailure],
    output_path: str | Path,
) -> Path:
    """Export batch failures to a UTF-8 CSV file."""

    path = Path(output_path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.writer(output_file)
        writer.writerow(
            [
                "Row Number",
                "Organisation Name",
                "Website",
                "Error",
            ]
        )

        for failure in failures:
            writer.writerow(
                [
                    failure.row_number,
                    failure.organisation_name,
                    failure.website,
                    failure.error,
                ]
            )

    logger.info(
        "Batch failure CSV written: output_path=%s failures=%d",
        path,
        len(failures),
    )

    return path.resolve()


def _find_duplicate_headers(headers: list[str]) -> list[str]:
    """Return duplicate normalized headers in first-seen order."""

    seen_headers: set[str] = set()
    duplicate_headers: list[str] = []

    for header in headers:
        if header in seen_headers and header not in duplicate_headers:
            duplicate_headers.append(header)

        seen_headers.add(header)

    return duplicate_headers


def _validate_website_url(value: str) -> str:
    """Validate website URLs using the CLI helper without a module cycle."""

    from .cli import validate_website_url

    try:
        return validate_website_url(value)

    except Exception as error:
        raise ValueError(str(error)) from error


def _extend_evidence_by_website(
    evidence_by_website: dict[str, list[SignalEvidence]],
    website: str,
    evidence: list[SignalEvidence],
) -> None:
    """Append and deduplicate evidence for a website key."""

    existing_evidence = evidence_by_website.setdefault(website, [])
    seen_keys = {
        _evidence_deduplication_key(evidence_item)
        for evidence_item in existing_evidence
    }

    for evidence_item in evidence:
        evidence_key = _evidence_deduplication_key(evidence_item)

        if evidence_key in seen_keys:
            continue

        existing_evidence.append(evidence_item)
        seen_keys.add(evidence_key)


def _evidence_deduplication_key(
    evidence: SignalEvidence,
) -> tuple[str, str, str]:
    """Deduplicate evidence by category, keyword, and source URL."""

    return (
        evidence.category,
        evidence.keyword,
        evidence.source_url,
    )
