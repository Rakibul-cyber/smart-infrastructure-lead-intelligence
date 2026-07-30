from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .static_scraper import ScrapedPage


logger = logging.getLogger(__name__)

SIGNAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "street_lighting": (
        "street lighting",
        "public lighting",
        "lighting infrastructure",
        "straßenbeleuchtung",
        "strassenbeleuchtung",
        "straßenlaternen",
        "strassenlaternen",
        "beleuchtungsanlage",
        "lichtmanagement",
        "led-umrüstung",
        "led umrüstung",
        "led-umruestung",
    ),
    "smart_city": (
        "smart city",
        "smart-city",
        "digitale stadt",
        "digital city",
        "urban digitalisation",
        "urban digitisation",
        "kommunale digitalisierung",
    ),
    "energy_efficiency": (
        "energy efficiency",
        "energy-efficient",
        "energy saving",
        "energy savings",
        "energieeffizienz",
        "energiesparen",
        "energieeinsparung",
        "stromverbrauch",
        "energieverbrauch",
    ),
    "climate_action": (
        "climate action",
        "climate protection",
        "climate plan",
        "climate-neutral",
        "klimafreundlich",
        "klimaschutz",
        "klimaschutzkonzept",
        "klimaneutral",
        "co2-reduktion",
        "co₂-reduktion",
    ),
    "infrastructure_modernisation": (
        "infrastructure modernisation",
        "infrastructure modernization",
        "modernisation programme",
        "modernization program",
        "infrastructure upgrade",
        "sanierung",
        "modernisierung",
        "infrastrukturprojekt",
        "infrastrukturmaßnahmen",
        "infrastrukturmassnahmen",
    ),
    "procurement": (
        "tender",
        "procurement",
        "invitation to tender",
        "public contract",
        "ausschreibung",
        "vergabe",
        "vergabeverfahren",
        "beschaffung",
        "leistungsbeschreibung",
    ),
    "municipal_utility": (
        "municipal utility",
        "public utility",
        "utility company",
        "stadtwerke",
        "kommunalbetrieb",
        "eigenbetrieb",
        "versorgungsbetrieb",
    ),
}

WHITESPACE_PATTERN = re.compile(r"\s+")
GERMAN_CHARACTER_REPLACEMENTS = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "ẞ": "ss",
    "Ä": "ae",
    "Ö": "oe",
    "Ü": "ue",
    "₂": "2",
}


@dataclass
class SignalEvidence:
    """One transparent keyword match supporting a business signal."""

    category: str
    keyword: str
    excerpt: str
    source_url: str


@dataclass
class DetectedSignals:
    """Rule-based business signals detected in page text."""

    street_lighting: bool
    smart_city: bool
    energy_efficiency: bool
    climate_action: bool
    infrastructure_modernisation: bool
    procurement: bool
    municipal_utility: bool
    matched_keywords: list[str]
    evidence: list[SignalEvidence]


def normalise_text(text: str) -> str:
    """
    Normalize text for transparent, case-insensitive keyword matching.

    German umlauts, ß, and subscript ₂ are converted to searchable equivalents
    while whitespace is collapsed into single spaces.
    """

    normalized_characters: list[str] = []

    for character in text:
        replacement = GERMAN_CHARACTER_REPLACEMENTS.get(
            character,
            character.casefold(),
        )
        normalized_characters.append(replacement)

    normalized_text = "".join(normalized_characters)
    normalized_text = WHITESPACE_PATTERN.sub(" ", normalized_text)

    return normalized_text.strip()


def create_excerpt(
    text: str,
    keyword: str,
    context_characters: int = 100,
) -> str:
    """
    Return a readable excerpt around the first keyword occurrence.

    The search uses the same normalization rules as signal detection, while the
    returned excerpt preserves the original page text.
    """

    if context_characters < 0:
        raise ValueError("context_characters must not be negative")

    match_span = _find_keyword_span(
        text=text,
        keyword=keyword,
    )

    if match_span is None:
        return ""

    match_start, match_end = match_span
    excerpt_start = max(
        0,
        match_start - context_characters,
    )
    excerpt_end = min(
        len(text),
        match_end + context_characters,
    )

    excerpt = text[excerpt_start:excerpt_end]
    excerpt = WHITESPACE_PATTERN.sub(" ", excerpt).strip()

    if excerpt_start > 0:
        excerpt = f"...{excerpt}"

    if excerpt_end < len(text):
        excerpt = f"{excerpt}..."

    return excerpt


def detect_signals_in_text(
    text: str,
    source_url: str,
) -> DetectedSignals:
    """
    Detect rule-based business signals in one text source.

    Every keyword is checked once in category definition order. No fuzzy
    matching or machine learning is used.
    """

    normalized_text = normalise_text(text)
    matched_keywords: set[str] = set()
    evidence: list[SignalEvidence] = []
    category_matches: dict[str, bool] = {
        category: False
        for category in SIGNAL_KEYWORDS
    }

    for category, keywords in SIGNAL_KEYWORDS.items():
        matched_normalized_keywords: set[str] = set()

        for keyword in keywords:
            normalized_keyword = normalise_text(keyword)

            if not normalized_keyword:
                continue

            if normalized_keyword in matched_normalized_keywords:
                continue

            if normalized_keyword not in normalized_text:
                continue

            matched_normalized_keywords.add(normalized_keyword)
            matched_keywords.add(keyword)
            category_matches[category] = True
            evidence.append(
                SignalEvidence(
                    category=category,
                    keyword=keyword,
                    excerpt=create_excerpt(
                        text=text,
                        keyword=keyword,
                    ),
                    source_url=source_url,
                )
            )

    detected_signals = _build_detected_signals(
        category_matches=category_matches,
        matched_keywords=matched_keywords,
        evidence=evidence,
    )
    detected_categories = [
        category
        for category in SIGNAL_KEYWORDS
        if getattr(detected_signals, category)
    ]
    logger.debug(
        "Signals detected in text: source_url=%s matched_keywords=%d "
        "evidence_items=%d categories=%s",
        source_url,
        len(detected_signals.matched_keywords),
        len(detected_signals.evidence),
        detected_categories,
    )

    return detected_signals


def detect_signals_from_pages(
    page_results: list[ScrapedPage],
) -> DetectedSignals:
    """
    Detect and combine business signals from multiple scraped pages.

    Evidence keeps page order, then category order, then keyword definition
    order. Duplicate category, keyword, and source URL entries are skipped.
    """

    category_matches: dict[str, bool] = {
        category: False
        for category in SIGNAL_KEYWORDS
    }
    matched_keywords: set[str] = set()
    evidence: list[SignalEvidence] = []
    seen_evidence_keys: set[tuple[str, str, str]] = set()

    logger.debug("Analysing pages for signals: pages=%d", len(page_results))

    for page_result in page_results:
        page_signals = detect_signals_in_text(
            text=page_result.visible_text,
            source_url=page_result.url,
        )

        for category in SIGNAL_KEYWORDS:
            if getattr(page_signals, category):
                category_matches[category] = True

        matched_keywords.update(page_signals.matched_keywords)

        for evidence_item in page_signals.evidence:
            evidence_key = (
                evidence_item.category,
                evidence_item.keyword,
                evidence_item.source_url,
            )

            if evidence_key in seen_evidence_keys:
                continue

            seen_evidence_keys.add(evidence_key)
            evidence.append(evidence_item)

    detected_signals = _build_detected_signals(
        category_matches=category_matches,
        matched_keywords=matched_keywords,
        evidence=evidence,
    )
    detected_categories = [
        category
        for category in SIGNAL_KEYWORDS
        if getattr(detected_signals, category)
    ]
    logger.debug(
        "Combined signal detection complete: pages=%d matched_keywords=%d "
        "evidence_items=%d categories=%s",
        len(page_results),
        len(detected_signals.matched_keywords),
        len(detected_signals.evidence),
        detected_categories,
    )

    return detected_signals


def _build_detected_signals(
    category_matches: dict[str, bool],
    matched_keywords: set[str],
    evidence: list[SignalEvidence],
) -> DetectedSignals:
    """Create a DetectedSignals object from accumulated values."""

    return DetectedSignals(
        street_lighting=category_matches["street_lighting"],
        smart_city=category_matches["smart_city"],
        energy_efficiency=category_matches["energy_efficiency"],
        climate_action=category_matches["climate_action"],
        infrastructure_modernisation=category_matches[
            "infrastructure_modernisation"
        ],
        procurement=category_matches["procurement"],
        municipal_utility=category_matches["municipal_utility"],
        matched_keywords=sorted(matched_keywords),
        evidence=evidence,
    )


def _normalise_text_with_index(text: str) -> tuple[str, list[int]]:
    """Normalize text and map each normalized character to an original index."""

    normalized_characters: list[str] = []
    original_indexes: list[int] = []
    previous_was_whitespace = False

    for index, character in enumerate(text):
        if character.isspace():
            if previous_was_whitespace:
                continue

            normalized_characters.append(" ")
            original_indexes.append(index)
            previous_was_whitespace = True
            continue

        previous_was_whitespace = False
        replacement = GERMAN_CHARACTER_REPLACEMENTS.get(
            character,
            character.casefold(),
        )

        for replacement_character in replacement:
            normalized_characters.append(replacement_character)
            original_indexes.append(index)

    raw_normalized_text = "".join(normalized_characters)
    leading_spaces = len(raw_normalized_text) - len(
        raw_normalized_text.lstrip()
    )
    trailing_spaces = len(raw_normalized_text) - len(
        raw_normalized_text.rstrip()
    )
    normalized_text = raw_normalized_text.strip()

    if leading_spaces:
        original_indexes = original_indexes[leading_spaces:]

    if trailing_spaces:
        original_indexes = original_indexes[:-trailing_spaces]

    return normalized_text, original_indexes


def _find_keyword_span(
    text: str,
    keyword: str,
) -> tuple[int, int] | None:
    """Find the original-text span for a normalized keyword match."""

    normalized_text, original_indexes = _normalise_text_with_index(text)
    normalized_keyword = normalise_text(keyword)

    if not normalized_keyword:
        return None

    match_start = normalized_text.find(normalized_keyword)

    if match_start < 0:
        return None

    match_end = match_start + len(normalized_keyword)
    original_start = original_indexes[match_start]
    original_end = original_indexes[match_end - 1] + 1

    return original_start, original_end
