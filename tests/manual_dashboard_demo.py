from __future__ import annotations

from src.lead_intelligence.dashboard import (
    build_dashboard_summary,
    print_dashboard,
)
from src.lead_intelligence.exporter import LeadRecord


def build_demo_records() -> list[LeadRecord]:
    """Build fictional records for the management dashboard demo."""

    return [
        LeadRecord(
            organisation_name="Example Regional Utility",
            organisation_type="Municipal Utility",
            city="Example City",
            state="Example State",
            website="https://example-regional-utility.example",
            visited_pages=5,
            emails=[
                "office@example-utility.example",
                "projects@example-utility.example",
            ],
            phone_numbers=["030 1000 2000"],
            contact_links=[
                "https://example-regional-utility.example/contact"
            ],
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
            climate_action=True,
            infrastructure_modernisation=True,
            procurement=True,
            municipal_utility=True,
            matched_keywords=[
                "street lighting",
                "procurement",
                "smart city",
            ],
            evidence_count=8,
            lead_score=95,
            priority="High",
            score_summary="High-priority fictional utility lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Demo Smart City Office",
            organisation_type="Municipality",
            city="Demo City",
            state="North Example",
            website="https://demo-smart-city.example",
            visited_pages=4,
            emails=["digital@demo-smart-city.example"],
            phone_numbers=[
                "030 3333 4444",
                " 030 3333 4444 ",
            ],
            contact_links=["https://demo-smart-city.example/team"],
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
            climate_action=False,
            infrastructure_modernisation=True,
            procurement=False,
            municipal_utility=False,
            matched_keywords=[
                "smart city",
                "energy efficiency",
            ],
            evidence_count=6,
            lead_score=85,
            priority="High",
            score_summary="High-priority fictional municipal lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Sample Infrastructure Department",
            organisation_type="Municipality",
            city="Sampleburg",
            state="West Example",
            website="https://sample-infrastructure.example",
            visited_pages=3,
            emails=["office@example-utility.example"],
            phone_numbers=["040 5555 6666"],
            contact_links=[
                "https://sample-infrastructure.example/kontakt",
                "https://sample-infrastructure.example/procurement",
            ],
            street_lighting=True,
            smart_city=False,
            energy_efficiency=False,
            climate_action=True,
            infrastructure_modernisation=True,
            procurement=True,
            municipal_utility=False,
            matched_keywords=[
                "ausschreibung",
                "modernisierung",
            ],
            evidence_count=5,
            lead_score=70,
            priority="Medium",
            score_summary="Medium-priority fictional infrastructure lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Fictional Energy Service",
            organisation_type="Public Utility",
            city="Fictional Harbor",
            state="South Example",
            website="https://fictional-energy.example",
            visited_pages=2,
            emails=["energy@fictional-energy.example"],
            phone_numbers=[],
            contact_links=["https://fictional-energy.example/contact"],
            street_lighting=False,
            smart_city=False,
            energy_efficiency=True,
            climate_action=True,
            infrastructure_modernisation=False,
            procurement=False,
            municipal_utility=True,
            matched_keywords=[
                "energy saving",
                "climate protection",
            ],
            evidence_count=4,
            lead_score=50,
            priority="Medium",
            score_summary="Medium-priority fictional energy lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Illustrative Borough Services",
            organisation_type="Municipality",
            city="Illustrative Borough",
            state="East Example",
            website="https://illustrative-borough.example",
            visited_pages=2,
            emails=[],
            phone_numbers=["050 1111 2222"],
            contact_links=[],
            street_lighting=False,
            smart_city=False,
            energy_efficiency=False,
            climate_action=True,
            infrastructure_modernisation=False,
            procurement=False,
            municipal_utility=False,
            matched_keywords=["climate plan"],
            evidence_count=2,
            lead_score=15,
            priority="Low",
            score_summary="Low-priority fictional borough lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Example Community Archive",
            organisation_type="Municipality",
            city="Example Village",
            state="North Example",
            website="https://example-community-archive.example",
            visited_pages=1,
            emails=[],
            phone_numbers=[],
            contact_links=[],
            street_lighting=False,
            smart_city=False,
            energy_efficiency=False,
            climate_action=False,
            infrastructure_modernisation=False,
            procurement=False,
            municipal_utility=False,
            matched_keywords=[],
            evidence_count=0,
            lead_score=0,
            priority="Low",
            score_summary="Low-priority fictional archive lead.",
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
    ]


def main() -> None:
    """Print the fictional management dashboard demonstration."""

    summary = build_dashboard_summary(
        records=build_demo_records(),
        top_limit=5,
    )

    print_dashboard(summary)


if __name__ == "__main__":
    main()
