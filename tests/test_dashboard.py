from __future__ import annotations

from copy import deepcopy

import pytest

from src.lead_intelligence.dashboard import (
    build_dashboard_summary,
    format_dashboard,
)
from src.lead_intelligence.exporter import LeadRecord


def make_record(
    *,
    name: str = "Example City",
    score: int = 50,
    priority: str = "Medium",
    emails: list[str] | None = None,
    phone_numbers: list[str] | None = None,
    contact_links: list[str] | None = None,
    evidence_count: int = 1,
    street_lighting: bool = False,
    smart_city: bool = False,
    energy_efficiency: bool = False,
    climate_action: bool = False,
    infrastructure_modernisation: bool = False,
    procurement: bool = False,
    municipal_utility: bool = False,
    matched_keywords: list[str] | None = None,
) -> LeadRecord:
    """Build a fictional LeadRecord for dashboard tests."""

    return LeadRecord(
        organisation_name=name,
        organisation_type="Municipality",
        city="Example City",
        state="Example State",
        website=f"https://{name.casefold().replace(' ', '-')}.example",
        visited_pages=2,
        emails=emails if emails is not None else [],
        phone_numbers=phone_numbers
        if phone_numbers is not None
        else [],
        contact_links=contact_links
        if contact_links is not None
        else [],
        street_lighting=street_lighting,
        smart_city=smart_city,
        energy_efficiency=energy_efficiency,
        climate_action=climate_action,
        infrastructure_modernisation=infrastructure_modernisation,
        procurement=procurement,
        municipal_utility=municipal_utility,
        matched_keywords=matched_keywords
        if matched_keywords is not None
        else [],
        evidence_count=evidence_count,
        lead_score=score,
        priority=priority,
        score_summary=f"{priority}-priority fictional summary.",
        score_breakdown=[],
        last_checked="2026-07-30",
    )


def test_empty_records_raise_value_error() -> None:
    """Dashboard summaries need at least one record."""

    with pytest.raises(ValueError):
        build_dashboard_summary([])


def test_top_limit_below_one_raises_value_error() -> None:
    """top_limit must be positive."""

    with pytest.raises(ValueError):
        build_dashboard_summary(
            [make_record()],
            top_limit=0,
        )


def test_priority_counts_are_correct() -> None:
    """High, Medium, and Low leads should be counted separately."""

    summary = build_dashboard_summary(
        [
            make_record(priority="High"),
            make_record(priority="Medium"),
            make_record(priority="Medium"),
            make_record(priority="Low"),
        ]
    )

    assert summary.high_priority_leads == 1
    assert summary.medium_priority_leads == 2
    assert summary.low_priority_leads == 1


def test_total_and_unique_email_counts_are_correct() -> None:
    """Email totals should include repeats while unique counts dedupe."""

    summary = build_dashboard_summary(
        [
            make_record(
                emails=[
                    "alpha@example.test",
                    "beta@example.test",
                ]
            ),
            make_record(emails=["alpha@example.test"]),
        ]
    )

    assert summary.total_emails == 3
    assert summary.unique_emails == 2


def test_unique_email_matching_is_case_insensitive() -> None:
    """Email uniqueness should ignore casing."""

    summary = build_dashboard_summary(
        [
            make_record(emails=["Office@Example.test"]),
            make_record(emails=["office@example.test"]),
        ]
    )

    assert summary.total_emails == 2
    assert summary.unique_emails == 1


def test_total_and_unique_phone_counts_are_correct() -> None:
    """Phone uniqueness should trim surrounding whitespace."""

    summary = build_dashboard_summary(
        [
            make_record(
                phone_numbers=[
                    "030 1111 2222",
                    " 030 1111 2222 ",
                    "030 3333 4444",
                ]
            )
        ]
    )

    assert summary.total_phone_numbers == 3
    assert summary.unique_phone_numbers == 2


def test_contact_link_count_is_correct() -> None:
    """All contact links should be counted across records."""

    summary = build_dashboard_summary(
        [
            make_record(contact_links=["https://one.example/contact"]),
            make_record(
                contact_links=[
                    "https://two.example/contact",
                    "https://two.example/team",
                ]
            ),
        ]
    )

    assert summary.total_contact_links == 3


def test_evidence_total_is_correct() -> None:
    """Evidence counts should sum across records."""

    summary = build_dashboard_summary(
        [
            make_record(evidence_count=2),
            make_record(evidence_count=5),
        ]
    )

    assert summary.total_evidence_items == 7


def test_average_score_is_rounded_correctly() -> None:
    """Average score should be rounded to two decimal places."""

    summary = build_dashboard_summary(
        [
            make_record(score=10),
            make_record(score=10),
            make_record(score=11),
        ]
    )

    assert summary.average_lead_score == 10.33


def test_highest_and_lowest_scores_are_correct() -> None:
    """Dashboard should expose score range."""

    summary = build_dashboard_summary(
        [
            make_record(score=15),
            make_record(score=95),
            make_record(score=50),
        ]
    )

    assert summary.highest_lead_score == 95
    assert summary.lowest_lead_score == 15


def test_top_leads_are_sorted_by_score_descending() -> None:
    """Top leads should prefer higher scores."""

    summary = build_dashboard_summary(
        [
            make_record(name="Medium Office", score=60),
            make_record(name="High Office", score=90),
            make_record(name="Low Office", score=15),
        ]
    )

    assert [
        record.organisation_name
        for record in summary.top_leads
    ] == [
        "High Office",
        "Medium Office",
        "Low Office",
    ]


def test_organisation_name_resolves_deterministic_ties() -> None:
    """Equal score and priority ties should sort by organisation name."""

    summary = build_dashboard_summary(
        [
            make_record(
                name="Beta Utility",
                score=80,
                priority="High",
            ),
            make_record(
                name="alpha Utility",
                score=80,
                priority="High",
            ),
        ]
    )

    assert [
        record.organisation_name
        for record in summary.top_leads
    ] == [
        "alpha Utility",
        "Beta Utility",
    ]


def test_priority_rank_resolves_score_ties_before_name() -> None:
    """Equal score ties should prefer High before Medium before Low."""

    summary = build_dashboard_summary(
        [
            make_record(
                name="Alpha Medium",
                score=80,
                priority="Medium",
            ),
            make_record(
                name="Zulu High",
                score=80,
                priority="High",
            ),
        ]
    )

    assert summary.top_leads[0].organisation_name == "Zulu High"


def test_top_limit_is_respected() -> None:
    """Top lead selection should be limited."""

    summary = build_dashboard_summary(
        [
            make_record(name="One", score=90),
            make_record(name="Two", score=80),
            make_record(name="Three", score=70),
        ],
        top_limit=2,
    )

    assert len(summary.top_leads) == 2


def test_signal_counts_count_organisations_not_keywords() -> None:
    """Signal counts should count records, not keyword occurrences."""

    summary = build_dashboard_summary(
        [
            make_record(
                street_lighting=True,
                matched_keywords=[
                    "street lighting",
                    "public lighting",
                ],
            ),
            make_record(street_lighting=True),
            make_record(street_lighting=False),
        ]
    )

    street_lighting_count = next(
        signal_count.count
        for signal_count in summary.signal_counts
        if signal_count.signal_name == "Street lighting"
    )

    assert street_lighting_count == 2


def test_signal_counts_are_ordered_by_count_descending() -> None:
    """Signals with higher organisation counts should come first."""

    summary = build_dashboard_summary(
        [
            make_record(
                smart_city=True,
                energy_efficiency=True,
            ),
            make_record(energy_efficiency=True),
        ]
    )

    assert summary.signal_counts[0].signal_name == "Energy efficiency"
    assert summary.signal_counts[0].count == 2


def test_alphabetical_ordering_resolves_equal_signal_counts() -> None:
    """Equal signal counts should sort alphabetically by display name."""

    summary = build_dashboard_summary(
        [
            make_record(
                procurement=True,
                smart_city=True,
            )
        ]
    )

    one_count_signal_names = [
        signal_count.signal_name
        for signal_count in summary.signal_counts
        if signal_count.count == 1
    ]

    assert one_count_signal_names == [
        "Procurement",
        "Smart city",
    ]


def test_format_dashboard_contains_required_section_headings() -> None:
    """Formatted output should include all required sections."""

    dashboard = format_dashboard(
        build_dashboard_summary([make_record()])
    )

    assert "SMART INFRASTRUCTURE LEAD INTELLIGENCE" in dashboard
    assert "LEAD OVERVIEW" in dashboard
    assert "CONTACT DISCOVERY" in dashboard
    assert "RESEARCH COVERAGE" in dashboard
    assert "TOP LEADS" in dashboard
    assert "MOST COMMON SIGNALS" in dashboard


def test_formatted_output_contains_organisation_names_and_scores() -> None:
    """Top lead output should include lead names and scores."""

    dashboard = format_dashboard(
        build_dashboard_summary(
            [
                make_record(
                    name="Example Regional Utility",
                    score=95,
                    priority="High",
                )
            ]
        )
    )

    assert "Example Regional Utility" in dashboard
    assert "95/100" in dashboard
    assert "High" in dashboard


def test_average_score_displays_two_decimal_places() -> None:
    """Average score should always render with two decimals."""

    dashboard = format_dashboard(
        build_dashboard_summary(
            [
                make_record(score=60),
                make_record(score=69),
            ]
        )
    )

    assert "64.50" in dashboard


def test_build_dashboard_summary_does_not_mutate_input_records() -> None:
    """Dashboard building should not modify supplied LeadRecord objects."""

    records = [
        make_record(
            name="Beta",
            score=80,
        ),
        make_record(
            name="Alpha",
            score=80,
        ),
    ]
    original_records = deepcopy(records)

    build_dashboard_summary(records)

    assert records == original_records
