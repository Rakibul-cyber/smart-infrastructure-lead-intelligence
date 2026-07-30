from __future__ import annotations

import logging
from dataclasses import dataclass

from .signal_detector import DetectedSignals


logger = logging.getLogger(__name__)

SCORE_WEIGHTS: dict[str, int] = {
    "street_lighting": 25,
    "procurement": 20,
    "smart_city": 15,
    "energy_efficiency": 15,
    "climate_action": 10,
    "infrastructure_modernisation": 10,
    "municipal_utility": 5,
    "contact_information": 5,
}

SCORE_REASONS: dict[str, str] = {
    "street_lighting": (
        "Street-lighting or public-lighting activity was detected."
    ),
    "procurement": (
        "A tender, procurement, or public-contract signal was detected."
    ),
    "smart_city": (
        "A Smart City or municipal digitalisation initiative was detected."
    ),
    "energy_efficiency": (
        "Energy-efficiency or energy-saving activity was detected."
    ),
    "climate_action": (
        "A climate-action or climate-protection initiative was detected."
    ),
    "infrastructure_modernisation": (
        "Infrastructure modernisation or upgrade activity was detected."
    ),
    "municipal_utility": (
        "A municipal or public utility was referenced."
    ),
    "contact_information": (
        "At least one public business email address or telephone number was found."
    ),
}

CRITERION_LABELS: dict[str, str] = {
    "street_lighting": "street-lighting",
    "procurement": "procurement",
    "smart_city": "smart-city",
    "energy_efficiency": "energy-efficiency",
    "climate_action": "climate-action",
    "infrastructure_modernisation": "infrastructure-modernisation",
    "municipal_utility": "municipal-utility",
    "contact_information": "contact-information",
}


@dataclass
class ScoreBreakdownItem:
    """One awarded criterion in a transparent lead score."""

    criterion: str
    points: int
    reason: str


@dataclass
class LeadScore:
    """Transparent priority score for one crawled organisation."""

    total_score: int
    priority: str
    breakdown: list[ScoreBreakdownItem]
    summary: str


def classify_priority(score: int) -> str:
    """
    Classify a score into Low, Medium, or High priority.

    Scores must be within the configured 0 to 100 range.
    """

    if score < 0 or score > 100:
        raise ValueError("score must be between 0 and 100")

    if score >= 80:
        return "High"

    if score >= 50:
        return "Medium"

    return "Low"


def build_score_summary(
    total_score: int,
    priority: str,
    active_criteria: list[str],
) -> str:
    """
    Build a concise human-readable score explanation.

    The summary mentions only criteria supplied in active_criteria.
    """

    signal_criteria = [
        criterion
        for criterion in active_criteria
        if criterion != "contact_information"
    ]

    if not signal_criteria:
        return (
            f"{priority}-priority lead with limited evidence of an immediate "
            "smart-infrastructure opportunity."
        )

    joined_criteria = _join_labels(
        [
            CRITERION_LABELS[criterion]
            for criterion in signal_criteria
        ]
    )

    if priority == "High":
        return (
            "High-priority lead with strong "
            f"{joined_criteria} signals."
        )

    if priority == "Medium":
        return (
            "Medium-priority lead with relevant "
            f"{joined_criteria} signals."
        )

    return (
        "Low-priority lead with limited "
        f"{joined_criteria} signals."
    )


def score_lead(
    signals: DetectedSignals,
    emails: list[str] | None = None,
    phone_numbers: list[str] | None = None,
) -> LeadScore:
    """
    Score a lead using detected business signals and public contact presence.

    Contact information is awarded once when at least one email address or
    telephone number is available. The score is capped at 100.
    """

    email_values = set(emails or [])
    phone_values = set(phone_numbers or [])
    has_contact_information = bool(email_values or phone_values)

    breakdown: list[ScoreBreakdownItem] = []
    active_criteria: list[str] = []
    total_score = 0

    for criterion, weight in SCORE_WEIGHTS.items():
        if criterion == "contact_information":
            criterion_is_active = has_contact_information
        else:
            criterion_is_active = bool(getattr(signals, criterion))

        if not criterion_is_active:
            continue

        remaining_points = 100 - total_score
        awarded_points = min(
            weight,
            remaining_points,
        )

        active_criteria.append(criterion)

        if awarded_points <= 0:
            continue

        total_score += awarded_points
        breakdown.append(
            ScoreBreakdownItem(
                criterion=criterion,
                points=awarded_points,
                reason=SCORE_REASONS[criterion],
            )
        )

    priority = classify_priority(total_score)
    summary = build_score_summary(
        total_score=total_score,
        priority=priority,
        active_criteria=active_criteria,
    )
    logger.debug(
        "Lead score calculated: criteria=%s total_score=%d priority=%s",
        [
            item.criterion
            for item in breakdown
        ],
        total_score,
        priority,
    )

    return LeadScore(
        total_score=total_score,
        priority=priority,
        breakdown=breakdown,
        summary=summary,
    )


def _join_labels(labels: list[str]) -> str:
    """Join labels into a readable English phrase."""

    if not labels:
        return ""

    if len(labels) == 1:
        return labels[0]

    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"

    return f"{', '.join(labels[:-1])}, and {labels[-1]}"
