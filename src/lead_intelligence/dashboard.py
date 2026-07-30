from __future__ import annotations

import logging
from dataclasses import dataclass

from .exporter import LeadRecord


logger = logging.getLogger(__name__)

SIGNAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("Street lighting", "street_lighting"),
    ("Smart city", "smart_city"),
    ("Energy efficiency", "energy_efficiency"),
    ("Climate action", "climate_action"),
    ("Infrastructure modernisation", "infrastructure_modernisation"),
    ("Procurement", "procurement"),
    ("Municipal utility", "municipal_utility"),
)

PRIORITY_RANKS = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
}


@dataclass
class SignalCount:
    """Count of organisations where one signal was detected."""

    signal_name: str
    count: int


@dataclass
class DashboardSummary:
    """Run-level management summary for analysed lead records."""

    total_leads: int
    high_priority_leads: int
    medium_priority_leads: int
    low_priority_leads: int
    total_emails: int
    unique_emails: int
    total_phone_numbers: int
    unique_phone_numbers: int
    total_contact_links: int
    total_evidence_items: int
    average_lead_score: float
    highest_lead_score: int
    lowest_lead_score: int
    top_leads: list[LeadRecord]
    signal_counts: list[SignalCount]


def build_dashboard_summary(
    records: list[LeadRecord],
    top_limit: int = 5,
) -> DashboardSummary:
    """
    Build a run-level dashboard summary from analysed lead records.

    The supplied records are read only and never mutated.
    """

    if not records:
        raise ValueError("records must not be empty")

    if top_limit < 1:
        raise ValueError("top_limit must be at least 1")

    total_score = sum(record.lead_score for record in records)
    lead_scores = [
        record.lead_score
        for record in records
    ]

    summary = DashboardSummary(
        total_leads=len(records),
        high_priority_leads=_count_priority(records, "High"),
        medium_priority_leads=_count_priority(records, "Medium"),
        low_priority_leads=_count_priority(records, "Low"),
        total_emails=sum(len(record.emails) for record in records),
        unique_emails=len(_unique_emails(records)),
        total_phone_numbers=sum(
            len(record.phone_numbers)
            for record in records
        ),
        unique_phone_numbers=len(_unique_phone_numbers(records)),
        total_contact_links=sum(
            len(record.contact_links)
            for record in records
        ),
        total_evidence_items=sum(
            record.evidence_count
            for record in records
        ),
        average_lead_score=round(total_score / len(records), 2),
        highest_lead_score=max(lead_scores),
        lowest_lead_score=min(lead_scores),
        top_leads=_select_top_leads(
            records=records,
            top_limit=top_limit,
        ),
        signal_counts=_build_signal_counts(records),
    )
    logger.debug(
        "Dashboard summary calculated: total_leads=%d high=%d medium=%d "
        "low=%d average_score=%.2f",
        summary.total_leads,
        summary.high_priority_leads,
        summary.medium_priority_leads,
        summary.low_priority_leads,
        summary.average_lead_score,
    )

    return summary


def format_dashboard(
    summary: DashboardSummary,
) -> str:
    """
    Return a professional terminal-friendly dashboard string.

    The function formats only and does not print.
    """

    lines = [
        "=" * 70,
        "SMART INFRASTRUCTURE LEAD INTELLIGENCE — RUN SUMMARY",
        "=" * 70,
        "",
        "LEAD OVERVIEW",
        "-" * 70,
        _metric_line("Organisations analysed", summary.total_leads),
        _metric_line("High-priority leads", summary.high_priority_leads),
        _metric_line("Medium-priority leads", summary.medium_priority_leads),
        _metric_line("Low-priority leads", summary.low_priority_leads),
        _metric_line(
            "Average lead score",
            f"{summary.average_lead_score:.2f}",
        ),
        _metric_line("Highest lead score", summary.highest_lead_score),
        _metric_line("Lowest lead score", summary.lowest_lead_score),
        "",
        "CONTACT DISCOVERY",
        "-" * 70,
        _metric_line("Emails found", summary.total_emails),
        _metric_line("Unique emails", summary.unique_emails),
        _metric_line("Phone numbers found", summary.total_phone_numbers),
        _metric_line("Unique phone numbers", summary.unique_phone_numbers),
        _metric_line(
            "Contact links discovered",
            summary.total_contact_links,
        ),
        "",
        "RESEARCH COVERAGE",
        "-" * 70,
        _metric_line(
            "Evidence items collected",
            summary.total_evidence_items,
        ),
        "",
        "TOP LEADS",
        "-" * 70,
    ]

    if not summary.top_leads:
        lines.append("No leads available")
    else:
        for position, record in enumerate(
            summary.top_leads,
            start=1,
        ):
            lines.append(
                _top_lead_line(
                    position=position,
                    record=record,
                )
            )

    lines.extend(
        [
            "",
            "MOST COMMON SIGNALS",
            "-" * 70,
        ]
    )

    for signal_count in summary.signal_counts:
        lines.append(
            _metric_line(
                signal_count.signal_name,
                signal_count.count,
            )
        )

    return "\n".join(lines)


def print_dashboard(
    summary: DashboardSummary,
) -> None:
    """Print a formatted dashboard summary."""

    print(format_dashboard(summary))


def _count_priority(
    records: list[LeadRecord],
    priority: str,
) -> int:
    """Count records with one priority value."""

    return sum(
        1
        for record in records
        if record.priority == priority
    )


def _unique_emails(records: list[LeadRecord]) -> set[str]:
    """Return unique emails using case-insensitive comparison."""

    return {
        email.casefold()
        for record in records
        for email in record.emails
    }


def _unique_phone_numbers(records: list[LeadRecord]) -> set[str]:
    """Return unique phone numbers after trimming surrounding whitespace."""

    return {
        phone_number.strip()
        for record in records
        for phone_number in record.phone_numbers
    }


def _select_top_leads(
    records: list[LeadRecord],
    top_limit: int,
) -> list[LeadRecord]:
    """Select top leads using deterministic management-dashboard ordering."""

    sorted_records = sorted(
        records,
        key=lambda record: (
            -record.lead_score,
            PRIORITY_RANKS.get(record.priority, 99),
            record.organisation_name.casefold(),
        ),
    )

    return sorted_records[:top_limit]


def _build_signal_counts(records: list[LeadRecord]) -> list[SignalCount]:
    """Count organisations with each signal set to true."""

    signal_counts = [
        SignalCount(
            signal_name=signal_name,
            count=sum(
                1
                for record in records
                if getattr(record, field_name)
            ),
        )
        for signal_name, field_name in SIGNAL_FIELDS
    ]

    return sorted(
        signal_counts,
        key=lambda signal_count: (
            -signal_count.count,
            signal_count.signal_name,
        ),
    )


def _metric_line(
    label: str,
    value: int | float | str,
) -> str:
    """Format a left label and right value row."""

    return f"{label:<55}{value:>15}"


def _top_lead_line(
    position: int,
    record: LeadRecord,
) -> str:
    """Format one top-lead row."""

    lead_name = record.organisation_name[:43]

    return (
        f"{position}. {lead_name:<43}"
        f"{record.lead_score:>7}/100  "
        f"{record.priority}"
    )
