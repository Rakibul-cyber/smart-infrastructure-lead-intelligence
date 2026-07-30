from __future__ import annotations

import pytest

from src.lead_intelligence.scorer import (
    SCORE_WEIGHTS,
    build_score_summary,
    classify_priority,
    score_lead,
)
from src.lead_intelligence.signal_detector import DetectedSignals


def make_signals(
    *,
    street_lighting: bool = False,
    smart_city: bool = False,
    energy_efficiency: bool = False,
    climate_action: bool = False,
    infrastructure_modernisation: bool = False,
    procurement: bool = False,
    municipal_utility: bool = False,
) -> DetectedSignals:
    """Build a DetectedSignals object for scorer tests."""

    return DetectedSignals(
        street_lighting=street_lighting,
        smart_city=smart_city,
        energy_efficiency=energy_efficiency,
        climate_action=climate_action,
        infrastructure_modernisation=infrastructure_modernisation,
        procurement=procurement,
        municipal_utility=municipal_utility,
        matched_keywords=[],
        evidence=[],
    )


def test_no_signals_and_no_contacts_returns_zero_and_low() -> None:
    """An empty lead should score zero and be low priority."""

    lead_score = score_lead(make_signals())

    assert lead_score.total_score == 0
    assert lead_score.priority == "Low"
    assert lead_score.breakdown == []


def test_all_signals_plus_contact_returns_100_and_high() -> None:
    """All criteria should cap at the configured maximum score."""

    lead_score = score_lead(
        make_signals(
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
            climate_action=True,
            infrastructure_modernisation=True,
            procurement=True,
            municipal_utility=True,
        ),
        emails=["office@example-city.de"],
        phone_numbers=["030 1234 5678"],
    )

    assert lead_score.total_score == 100
    assert lead_score.priority == "High"


def test_street_lighting_procurement_and_smart_city_returns_medium() -> None:
    """A strong three-signal match should produce a medium score."""

    lead_score = score_lead(
        make_signals(
            street_lighting=True,
            procurement=True,
            smart_city=True,
        )
    )

    assert lead_score.total_score == 60
    assert lead_score.priority == "Medium"


def test_contact_points_are_added_for_email_only() -> None:
    """One public email should add contact-information points."""

    lead_score = score_lead(
        make_signals(),
        emails=["office@example-city.de"],
    )

    assert lead_score.total_score == SCORE_WEIGHTS["contact_information"]


def test_contact_points_are_added_for_phone_only() -> None:
    """One public phone number should add contact-information points."""

    lead_score = score_lead(
        make_signals(),
        phone_numbers=["030 1234 5678"],
    )

    assert lead_score.total_score == SCORE_WEIGHTS["contact_information"]


def test_contact_points_are_added_once_when_both_exist() -> None:
    """Emails and phone numbers should not double-count contact points."""

    lead_score = score_lead(
        make_signals(),
        emails=[
            "office@example-city.de",
            "office@example-city.de",
        ],
        phone_numbers=[
            "030 1234 5678",
            "030 1234 5678",
        ],
    )

    assert lead_score.total_score == SCORE_WEIGHTS["contact_information"]
    assert [
        item.criterion
        for item in lead_score.breakdown
    ] == ["contact_information"]


def test_false_signals_do_not_appear_in_breakdown() -> None:
    """Only awarded criteria should be listed in the breakdown."""

    lead_score = score_lead(
        make_signals(street_lighting=True)
    )

    assert [
        item.criterion
        for item in lead_score.breakdown
    ] == ["street_lighting"]


def test_breakdown_order_is_deterministic() -> None:
    """Breakdown order should follow SCORE_WEIGHTS."""

    lead_score = score_lead(
        make_signals(
            smart_city=True,
            street_lighting=True,
            procurement=True,
            municipal_utility=True,
        ),
        emails=["office@example-city.de"],
    )

    assert [
        item.criterion
        for item in lead_score.breakdown
    ] == [
        "street_lighting",
        "procurement",
        "smart_city",
        "municipal_utility",
        "contact_information",
    ]


def test_total_score_equals_sum_of_breakdown_points() -> None:
    """The visible breakdown should reconcile with the total score."""

    lead_score = score_lead(
        make_signals(
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
        ),
        emails=["office@example-city.de"],
    )

    assert lead_score.total_score == sum(
        item.points
        for item in lead_score.breakdown
    )


def test_score_never_exceeds_100() -> None:
    """The configured 105 possible raw points should cap at 100."""

    lead_score = score_lead(
        make_signals(
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
            climate_action=True,
            infrastructure_modernisation=True,
            procurement=True,
            municipal_utility=True,
        ),
        emails=["office@example-city.de"],
    )

    assert lead_score.total_score == 100
    assert sum(
        item.points
        for item in lead_score.breakdown
    ) == 100


@pytest.mark.parametrize(
    ("score", "expected_priority"),
    [
        (0, "Low"),
        (49, "Low"),
        (50, "Medium"),
        (79, "Medium"),
        (80, "High"),
        (100, "High"),
    ],
)
def test_priority_boundaries(
    score: int,
    expected_priority: str,
) -> None:
    """Boundary scores should map to the required priority bands."""

    assert classify_priority(score) == expected_priority


@pytest.mark.parametrize("score", [-1, 101])
def test_invalid_priority_scores_raise_value_error(score: int) -> None:
    """Priority classification should reject out-of-range scores."""

    with pytest.raises(ValueError):
        classify_priority(score)


def test_summary_reflects_detected_criteria() -> None:
    """Summary text should mention detected signal criteria."""

    summary = build_score_summary(
        total_score=60,
        priority="Medium",
        active_criteria=[
            "street_lighting",
            "procurement",
            "smart_city",
        ],
    )

    assert summary == (
        "Medium-priority lead with relevant "
        "street-lighting, procurement, and smart-city signals."
    )


def test_empty_input_summary_does_not_invent_opportunities() -> None:
    """An empty summary should not name specific absent signals."""

    lead_score = score_lead(make_signals())

    assert lead_score.summary == (
        "Low-priority lead with limited evidence of an immediate "
        "smart-infrastructure opportunity."
    )
    assert "street-lighting" not in lead_score.summary
    assert "procurement" not in lead_score.summary
