from __future__ import annotations

from pathlib import Path

import pytest

from src.lead_intelligence.signal_detector import (
    SIGNAL_KEYWORDS,
    create_excerpt,
    detect_signals_from_pages,
    detect_signals_in_text,
    normalise_text,
)
from src.lead_intelligence.static_scraper import ScrapedPage, parse_page


FIXTURE_DIR = Path("tests/fixtures")
HOME_URL = "https://example-city.de/signals"
PROCUREMENT_URL = "https://example-city.de/procurement"
IRRELEVANT_URL = "https://example-city.de/notice"


def parse_fixture_page(
    fixture_name: str,
    url: str,
) -> ScrapedPage:
    """Parse a signal detector HTML fixture into a ScrapedPage."""

    html = (FIXTURE_DIR / fixture_name).read_text(
        encoding="utf-8",
    )

    return parse_page(
        url=url,
        html=html,
    )


def category_values(signals: object) -> list[bool]:
    """Return signal category booleans in definition order."""

    return [
        getattr(signals, category)
        for category in SIGNAL_KEYWORDS
    ]


def test_normalise_text_handles_casing_and_repeated_whitespace() -> None:
    """Matching text should be case-insensitive and whitespace-stable."""

    assert (
        normalise_text("  STRAẞEN   Übung \n CO₂  ")
        == "strassen uebung co2"
    )


def test_german_and_english_keywords_are_detected() -> None:
    """English and German keyword variants should both be searchable."""

    signals = detect_signals_in_text(
        text=(
            "The Smart City team updates Straßenbeleuchtung "
            "for energy savings."
        ),
        source_url=HOME_URL,
    )

    assert signals.smart_city is True
    assert signals.street_lighting is True
    assert signals.energy_efficiency is True
    assert "smart city" in signals.matched_keywords
    assert "straßenbeleuchtung" in signals.matched_keywords
    assert "energy savings" in signals.matched_keywords


def test_irrelevant_text_produces_no_signals() -> None:
    """Ordinary municipal text should not create target signals."""

    page = parse_fixture_page(
        fixture_name="signal_page_irrelevant.html",
        url=IRRELEVANT_URL,
    )

    signals = detect_signals_in_text(
        text=page.visible_text,
        source_url=page.url,
    )

    assert category_values(signals) == [False] * len(SIGNAL_KEYWORDS)
    assert signals.matched_keywords == []
    assert signals.evidence == []


def test_category_booleans_are_correct() -> None:
    """The home fixture should set only its represented categories."""

    page = parse_fixture_page(
        fixture_name="signal_page_home.html",
        url=HOME_URL,
    )

    signals = detect_signals_in_text(
        text=page.visible_text,
        source_url=page.url,
    )

    assert signals.street_lighting is True
    assert signals.smart_city is True
    assert signals.energy_efficiency is True
    assert signals.climate_action is True
    assert signals.infrastructure_modernisation is False
    assert signals.procurement is False
    assert signals.municipal_utility is True


def test_matched_keywords_are_sorted_and_unique() -> None:
    """Returned matched keywords should be deduplicated and sorted."""

    signals = detect_signals_in_text(
        text="Smart City smart city Stadtwerke Stadtwerke",
        source_url=HOME_URL,
    )

    assert signals.matched_keywords == [
        "smart city",
        "stadtwerke",
    ]


def test_excerpts_contain_the_matched_keyword() -> None:
    """Evidence excerpts should include readable original matched text."""

    excerpt = create_excerpt(
        text="The fictional plan upgrades Straßenbeleuchtung downtown.",
        keyword="strassenbeleuchtung",
    )

    assert "Straßenbeleuchtung" in excerpt


def test_excerpts_use_ellipses_when_context_is_omitted() -> None:
    """Excerpt boundaries should indicate omitted surrounding text."""

    excerpt = create_excerpt(
        text=(
            "Alpha beta gamma delta epsilon street lighting "
            "zeta eta theta iota kappa"
        ),
        keyword="street lighting",
        context_characters=8,
    )

    assert excerpt.startswith("...")
    assert excerpt.endswith("...")
    assert "street lighting" in excerpt


def test_negative_context_characters_raises_value_error() -> None:
    """Excerpt context must not be negative."""

    with pytest.raises(ValueError):
        create_excerpt(
            text="Smart City",
            keyword="smart city",
            context_characters=-1,
        )


def test_source_url_is_stored_in_evidence() -> None:
    """Each evidence item should retain the page source URL."""

    signals = detect_signals_in_text(
        text="Smart City planning",
        source_url=HOME_URL,
    )

    assert signals.evidence[0].source_url == HOME_URL


def test_multiple_pages_combine_their_signals() -> None:
    """Signals and keywords should combine across scraped pages."""

    home_page = parse_fixture_page(
        fixture_name="signal_page_home.html",
        url=HOME_URL,
    )
    procurement_page = parse_fixture_page(
        fixture_name="signal_page_procurement.html",
        url=PROCUREMENT_URL,
    )

    signals = detect_signals_from_pages(
        [home_page, procurement_page]
    )

    assert category_values(signals) == [True] * len(SIGNAL_KEYWORDS)
    assert "smart city" in signals.matched_keywords
    assert "ausschreibung" in signals.matched_keywords
    assert "modernisierung" in signals.matched_keywords


def test_duplicate_evidence_entries_are_removed() -> None:
    """Duplicate category, keyword, and source URL evidence should be skipped."""

    page = parse_fixture_page(
        fixture_name="signal_page_home.html",
        url=HOME_URL,
    )

    signals = detect_signals_from_pages([page, page])
    evidence_keys = [
        (
            item.category,
            item.keyword,
            item.source_url,
        )
        for item in signals.evidence
    ]

    assert len(evidence_keys) == len(set(evidence_keys))


def test_empty_page_list_returns_empty_signals() -> None:
    """Empty input should be handled without special-case failures."""

    signals = detect_signals_from_pages([])

    assert category_values(signals) == [False] * len(SIGNAL_KEYWORDS)
    assert signals.matched_keywords == []
    assert signals.evidence == []


def test_evidence_order_is_deterministic() -> None:
    """Evidence should follow category order, then keyword definition order."""

    page = parse_fixture_page(
        fixture_name="signal_page_home.html",
        url=HOME_URL,
    )

    signals = detect_signals_from_pages([page])

    assert [
        (
            item.category,
            item.keyword,
        )
        for item in signals.evidence
    ] == [
        ("street_lighting", "street lighting"),
        ("street_lighting", "led-umrüstung"),
        ("smart_city", "smart city"),
        ("energy_efficiency", "energy efficiency"),
        ("energy_efficiency", "energy-efficient"),
        ("climate_action", "climate protection"),
        ("climate_action", "co2-reduktion"),
        ("municipal_utility", "stadtwerke"),
    ]
