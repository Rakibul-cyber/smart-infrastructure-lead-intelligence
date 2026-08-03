from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import ParseResult, unquote, urlparse, urlunparse, urldefrag


@dataclass(frozen=True)
class LinkPriority:
    """Transparent priority assigned to one discovered link."""

    url: str
    score: int
    matched_terms: tuple[str, ...]
    category: str


BUSINESS_LINK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "street_lighting": (
        "straßenbeleuchtung",
        "strassenbeleuchtung",
        "street-lighting",
        "beleuchtung",
        "lighting",
        "lichtmanagement",
        "led-umruestung",
        "led-umrüstung",
        "laternen",
    ),
    "smart_city": (
        "smart-city",
        "smartcity",
        "digitalisierung",
        "digitalisation",
        "digitalization",
        "digitale-stadt",
    ),
    "energy": (
        "energie",
        "energy",
        "energieeffizienz",
        "energy-efficiency",
        "strom",
        "electricity",
        "energiewende",
    ),
    "climate_sustainability": (
        "klimaschutz",
        "climate",
        "nachhaltigkeit",
        "sustainability",
        "klimaneutral",
        "decarbonisation",
        "decarbonization",
    ),
    "infrastructure_modernisation": (
        "infrastruktur",
        "infrastructure",
        "modernisierung",
        "modernisation",
        "modernization",
        "sanierung",
        "renovation",
        "tiefbau",
    ),
    "procurement": (
        "ausschreibung",
        "ausschreibungen",
        "vergabe",
        "beschaffung",
        "tender",
        "procurement",
        "public-contract",
    ),
    "municipal_utility": (
        "stadtwerke",
        "municipal-utility",
        "versorgung",
        "utility",
        "netze",
        "networks",
    ),
}

CONTACT_LINK_KEYWORDS: tuple[str, ...] = (
    "kontakt",
    "contact",
    "ansprechpartner",
    "team",
    "abteilung",
    "department",
    "impressum",
)

EXCLUDED_LINK_KEYWORDS: tuple[str, ...] = (
    "datenschutz",
    "privacy",
    "cookie",
    "login",
    "logout",
    "anmeldung",
    "register",
    "search",
    "suche",
    "sitemap",
    "accessibility",
    "barrierefreiheit",
    "social-media",
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
)

BUSINESS_CATEGORY_SCORES: dict[str, int] = {
    "street_lighting": 100,
    "procurement": 90,
    "smart_city": 85,
    "energy": 80,
    "climate_sustainability": 70,
    "infrastructure_modernisation": 70,
    "municipal_utility": 60,
}

CONTACT_SCORE = 30
GENERAL_SCORE = 0
EXCLUDED_SCORE = -1000
ADDITIONAL_BUSINESS_CATEGORY_BONUS = 5
MAX_ADDITIONAL_BUSINESS_BONUS = 15


def normalise_link_text(value: str) -> str:
    """
    Normalise URL and anchor text for transparent keyword matching.

    The returned text stays readable enough for debugging while making German
    umlauts, punctuation, underscores, and repeated separators predictable.
    """

    normalized = unquote(value).casefold()
    normalized = normalized.translate(
        str.maketrans(
            {
                "ä": "ae",
                "ö": "oe",
                "ü": "ue",
                "ß": "ss",
            }
        )
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def score_link(
    url: str,
    anchor_text: str = "",
) -> LinkPriority:
    """Score one link without making network requests."""

    normalized_url = _normalise_priority_url(url)
    searchable_text = _build_searchable_text(url, anchor_text)

    excluded_matches = _match_terms(
        searchable_text,
        EXCLUDED_LINK_KEYWORDS,
    )

    if excluded_matches:
        return LinkPriority(
            url=normalized_url,
            score=EXCLUDED_SCORE,
            matched_terms=excluded_matches,
            category="excluded",
        )

    business_matches_by_category: dict[str, tuple[str, ...]] = {}

    for category, keywords in BUSINESS_LINK_KEYWORDS.items():
        matches = _match_terms(searchable_text, keywords)

        if matches:
            business_matches_by_category[category] = matches

    if business_matches_by_category:
        base_score = max(
            BUSINESS_CATEGORY_SCORES[category]
            for category in business_matches_by_category
        )
        additional_categories = len(business_matches_by_category) - 1
        bonus = min(
            additional_categories * ADDITIONAL_BUSINESS_CATEGORY_BONUS,
            MAX_ADDITIONAL_BUSINESS_BONUS,
        )

        return LinkPriority(
            url=normalized_url,
            score=base_score + bonus,
            matched_terms=_dedupe_terms(
                term
                for category in sorted(business_matches_by_category)
                for term in business_matches_by_category[category]
            ),
            category="business",
        )

    contact_matches = _match_terms(
        searchable_text,
        CONTACT_LINK_KEYWORDS,
    )

    if contact_matches:
        return LinkPriority(
            url=normalized_url,
            score=CONTACT_SCORE,
            matched_terms=contact_matches,
            category="contact",
        )

    return LinkPriority(
        url=normalized_url,
        score=GENERAL_SCORE,
        matched_terms=(),
        category="general",
    )


def prioritise_links(
    links: list[tuple[str, str]],
) -> list[LinkPriority]:
    """
    Score and sort crawl candidates.

    Duplicate normalised URLs retain the highest-scoring representation.
    Excluded links are intentionally omitted from the returned candidates.
    """

    best_by_url: dict[str, LinkPriority] = {}

    for url, anchor_text in links:
        priority = score_link(
            url=url,
            anchor_text=anchor_text,
        )

        if priority.category == "excluded":
            continue

        existing = best_by_url.get(priority.url)

        if existing is None or _candidate_sort_key(priority) < (
            _candidate_sort_key(existing)
        ):
            best_by_url[priority.url] = priority

    return sorted(
        best_by_url.values(),
        key=_candidate_sort_key,
    )


def _build_searchable_text(url: str, anchor_text: str) -> str:
    parsed_url = urlparse(url)
    url_parts = " ".join(
        part
        for part in (
            parsed_url.path,
            parsed_url.query,
            anchor_text,
        )
        if part
    )

    return normalise_link_text(url_parts)


def _match_terms(
    searchable_text: str,
    keywords: tuple[str, ...],
) -> tuple[str, ...]:
    matches: list[str] = []
    seen_normalized_terms: set[str] = set()

    for keyword in keywords:
        normalized_keyword = normalise_link_text(keyword)

        if not normalized_keyword:
            continue

        if normalized_keyword in seen_normalized_terms:
            continue

        if _contains_term(searchable_text, normalized_keyword):
            matches.append(keyword)
            seen_normalized_terms.add(normalized_keyword)

    return tuple(matches)


def _contains_term(
    searchable_text: str,
    normalized_keyword: str,
) -> bool:
    return (
        f" {normalized_keyword} "
        in f" {searchable_text} "
    )


def _dedupe_terms(terms: Iterable[str]) -> tuple[str, ...]:
    unique_terms: dict[str, str] = {}

    for term in terms:
        normalized_term = normalise_link_text(term)

        if normalized_term and normalized_term not in unique_terms:
            unique_terms[normalized_term] = term

    return tuple(
        unique_terms[key]
        for key in sorted(unique_terms)
    )


def _candidate_sort_key(priority: LinkPriority) -> tuple[int, str]:
    return (-priority.score, priority.url)


def _normalise_priority_url(url: str) -> str:
    def normalized_netloc(parsed_url: ParseResult) -> str:
        hostname = parsed_url.hostname or ""
        hostname = hostname.casefold()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        if parsed_url.port is None:
            return hostname

        return f"{hostname}:{parsed_url.port}"

    url_without_fragment, _fragment = urldefrag(url)
    parsed_url = urlparse(url_without_fragment)
    path = parsed_url.path or "/"

    if path != "/":
        path = path.rstrip("/")

        if not path:
            path = "/"

    normalized = parsed_url._replace(
        scheme=parsed_url.scheme.casefold(),
        netloc=normalized_netloc(parsed_url),
        path=path,
    )

    return urlunparse(normalized)
