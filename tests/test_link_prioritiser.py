from __future__ import annotations

from src.lead_intelligence.link_prioritiser import (
    BUSINESS_CATEGORY_SCORES,
    CONTACT_SCORE,
    EXCLUDED_SCORE,
    GENERAL_SCORE,
    normalise_link_text,
    prioritise_links,
    score_link,
)


def test_normalise_link_text_handles_case_umlauts_and_separators() -> None:
    """Link text normalisation should keep matching predictable."""

    assert (
        normalise_link_text("  LED-Umrüstung__Straßenbeleuchtung!!! ")
        == "led umruestung strassenbeleuchtung"
    )


def test_street_lighting_url_receives_highest_business_priority() -> None:
    """Street-lighting pages should receive the top business score."""

    priority = score_link(
        "https://example.de/strassenbeleuchtung"
    )

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES["street_lighting"]
    assert priority.matched_terms == ("straßenbeleuchtung",)


def test_german_and_english_variants_match() -> None:
    """German and English spellings should both be recognised."""

    german = score_link("https://example.de/led-umrüstung")
    english = score_link(
        "https://example.de/public-lighting",
        "Street lighting programme",
    )

    assert german.category == "business"
    assert english.category == "business"
    assert german.score == BUSINESS_CATEGORY_SCORES["street_lighting"]
    assert english.score == BUSINESS_CATEGORY_SCORES["street_lighting"]


def test_procurement_matches() -> None:
    """Procurement links should be business-priority links."""

    priority = score_link("https://example.de/ausschreibungen")

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES["procurement"]


def test_smart_city_matches() -> None:
    """Smart City links should be business-priority links."""

    priority = score_link("https://example.de/smart-city")

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES["smart_city"]


def test_energy_matches() -> None:
    """Energy links should be business-priority links."""

    priority = score_link("https://example.de/energie/energieeffizienz")

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES["energy"]


def test_climate_matches() -> None:
    """Climate and sustainability links should be business-priority links."""

    priority = score_link("https://example.de/klimaschutz")

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES[
        "climate_sustainability"
    ]


def test_infrastructure_matches() -> None:
    """Infrastructure links should be business-priority links."""

    priority = score_link("https://example.de/infrastruktur")

    assert priority.category == "business"
    assert priority.score == BUSINESS_CATEGORY_SCORES[
        "infrastructure_modernisation"
    ]


def test_stadtwerke_and_utility_matches() -> None:
    """Municipal utility links should be business-priority links."""

    stadtwerke = score_link("https://example.de/stadtwerke")
    utility = score_link("https://example.de/about", "Municipal utility")

    assert stadtwerke.category == "business"
    assert utility.category == "business"
    assert stadtwerke.score == BUSINESS_CATEGORY_SCORES[
        "municipal_utility"
    ]
    assert utility.score == BUSINESS_CATEGORY_SCORES["municipal_utility"]


def test_contact_only_link_receives_contact_score() -> None:
    """Contact-only links should remain useful but secondary."""

    priority = score_link("https://example.de/kontakt")

    assert priority.category == "contact"
    assert priority.score == CONTACT_SCORE
    assert priority.matched_terms == ("kontakt",)


def test_unmatched_link_receives_general_score() -> None:
    """Unmatched internal links should be general candidates."""

    priority = score_link("https://example.de/aktuelles")

    assert priority.category == "general"
    assert priority.score == GENERAL_SCORE
    assert priority.matched_terms == ()


def test_excluded_url_is_categorised_as_excluded() -> None:
    """Privacy/login/search style pages should be excluded."""

    priority = score_link("https://example.de/datenschutz")

    assert priority.category == "excluded"
    assert priority.score == EXCLUDED_SCORE
    assert priority.matched_terms == ("datenschutz",)


def test_excluded_terms_override_business_terms() -> None:
    """Excluded terms should win when a URL also contains business terms."""

    priority = score_link("https://example.de/login/smart-city")

    assert priority.category == "excluded"
    assert priority.score == EXCLUDED_SCORE
    assert priority.matched_terms == ("login",)


def test_multiple_business_categories_receive_bonus() -> None:
    """Multiple distinct business categories should add a capped bonus."""

    priority = score_link(
        "https://example.de/smart-city/strassenbeleuchtung",
        "Energieeffizienz",
    )

    assert priority.category == "business"
    assert priority.score == (
        BUSINESS_CATEGORY_SCORES["street_lighting"] + 10
    )


def test_matched_terms_are_unique_and_deterministic() -> None:
    """Equivalent keyword variants should not create duplicate matches."""

    priority = score_link("https://example.de/strassenbeleuchtung")

    assert priority.matched_terms == ("straßenbeleuchtung",)


def test_duplicate_urls_are_deduplicated() -> None:
    """The same normalised URL should appear only once."""

    result = prioritise_links(
        [
            ("https://example.de/kontakt/", "Kontakt"),
            ("https://www.example.de/kontakt#team", "Kontakt Team"),
        ]
    )

    assert [priority.url for priority in result] == [
        "https://example.de/kontakt"
    ]


def test_highest_scoring_duplicate_representation_is_retained() -> None:
    """Anchor text can make the best duplicate representation business-related."""

    result = prioritise_links(
        [
            ("https://example.de/projekte", "Projects"),
            ("https://example.de/projekte/", "Straßenbeleuchtung"),
        ]
    )

    assert len(result) == 1
    assert result[0].url == "https://example.de/projekte"
    assert result[0].category == "business"


def test_order_is_deterministic() -> None:
    """Candidates should sort by score descending and URL for ties."""

    result = prioritise_links(
        [
            ("https://example.de/kontakt", "Kontakt"),
            ("https://example.de/z-smart-city", "Smart City"),
            ("https://example.de/a-smart-city", "Smart City"),
            ("https://example.de/aktuelles", "Aktuelles"),
        ]
    )

    assert [priority.url for priority in result] == [
        "https://example.de/a-smart-city",
        "https://example.de/z-smart-city",
        "https://example.de/kontakt",
        "https://example.de/aktuelles",
    ]


def test_input_is_not_mutated() -> None:
    """Prioritisation should not modify caller-supplied links."""

    links = [
        ("https://example.de/kontakt", "Kontakt"),
        ("https://example.de/smart-city", "Smart City"),
    ]
    original_links = list(links)

    prioritise_links(links)

    assert links == original_links
