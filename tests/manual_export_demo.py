from __future__ import annotations

from pathlib import Path

from src.lead_intelligence.exporter import (
    LeadRecord,
    export_leads_to_excel,
)
from src.lead_intelligence.signal_detector import SignalEvidence


OUTPUT_PATH = Path("data/output/lead_intelligence_report.xlsx")


def build_demo_records() -> list[LeadRecord]:
    """Build fictional records for the manual Excel export demo."""

    return [
        LeadRecord(
            organisation_name="Example City Infrastructure Office",
            organisation_type="Municipality",
            city="Example City",
            state="Example State",
            website="https://example-city.de",
            visited_pages=5,
            emails=["infrastructure@example-city.de"],
            phone_numbers=["030 1000 2000"],
            contact_links=["https://example-city.de/kontakt"],
            street_lighting=True,
            smart_city=True,
            energy_efficiency=True,
            climate_action=True,
            infrastructure_modernisation=True,
            procurement=True,
            municipal_utility=True,
            matched_keywords=[
                "ausschreibung",
                "smart city",
                "street lighting",
            ],
            evidence_count=3,
            lead_score=100,
            priority="High",
            score_summary=(
                "High-priority lead with strong street-lighting, "
                "procurement, and smart-city signals."
            ),
            score_breakdown=[
                "+25 Street lighting — Street-lighting or public-lighting activity was detected.",
                "+20 Procurement — A tender, procurement, or public-contract signal was detected.",
                "+15 Smart city — A Smart City or municipal digitalisation initiative was detected.",
            ],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Sample Stadtwerke Services",
            organisation_type="Municipal Utility",
            city="Sampletown",
            state="Fictional Region",
            website="https://sample-stadtwerke.example",
            visited_pages=3,
            emails=["service@sample-stadtwerke.example"],
            phone_numbers=[],
            contact_links=["https://sample-stadtwerke.example/contact"],
            street_lighting=False,
            smart_city=True,
            energy_efficiency=True,
            climate_action=False,
            infrastructure_modernisation=True,
            procurement=False,
            municipal_utility=True,
            matched_keywords=[
                "energy efficiency",
                "modernisierung",
                "stadtwerke",
            ],
            evidence_count=2,
            lead_score=50,
            priority="Medium",
            score_summary=(
                "Medium-priority lead with relevant energy-efficiency and "
                "infrastructure-modernisation signals."
            ),
            score_breakdown=[
                "+15 Smart city — A Smart City or municipal digitalisation initiative was detected.",
                "+15 Energy efficiency — Energy-efficiency or energy-saving activity was detected.",
                "+10 Infrastructure modernisation — Infrastructure modernisation or upgrade activity was detected.",
                "+5 Municipal utility — A municipal or public utility was referenced.",
                "+5 Contact information — At least one public business email address or telephone number was found.",
            ],
            last_checked="2026-07-30",
        ),
        LeadRecord(
            organisation_name="Fictional Borough Archive",
            organisation_type="Municipality",
            city="Fictional Borough",
            state="Example State",
            website="https://fictional-borough.example",
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
            score_summary=(
                "Low-priority lead with limited evidence of an immediate "
                "smart-infrastructure opportunity."
            ),
            score_breakdown=[],
            last_checked="2026-07-30",
        ),
    ]


def build_demo_evidence() -> dict[str, list[SignalEvidence]]:
    """Build fictional evidence for the manual Excel export demo."""

    return {
        "https://example-city.de": [
            SignalEvidence(
                category="street_lighting",
                keyword="street lighting",
                excerpt="A fictional street lighting programme is planned.",
                source_url="https://example-city.de/infrastructure",
            ),
            SignalEvidence(
                category="procurement",
                keyword="ausschreibung",
                excerpt="A fictional Ausschreibung describes infrastructure work.",
                source_url="https://example-city.de/procurement",
            ),
            SignalEvidence(
                category="smart_city",
                keyword="smart city",
                excerpt="The fictional Smart City roadmap includes lighting upgrades.",
                source_url="https://example-city.de/digital",
            ),
        ],
        "https://sample-stadtwerke.example": [
            SignalEvidence(
                category="energy_efficiency",
                keyword="energy efficiency",
                excerpt="The fictional utility describes energy efficiency projects.",
                source_url="https://sample-stadtwerke.example/projects",
            ),
            SignalEvidence(
                category="municipal_utility",
                keyword="stadtwerke",
                excerpt="Sample Stadtwerke Services is a fictional public utility.",
                source_url="https://sample-stadtwerke.example/about",
            ),
        ],
        "https://fictional-borough.example": [],
    }


def main() -> None:
    """Generate the fictional Excel demonstration workbook."""

    output_path = export_leads_to_excel(
        records=build_demo_records(),
        evidence_by_website=build_demo_evidence(),
        output_path=OUTPUT_PATH,
    )

    print(f"Excel demo report written to: {output_path}")


if __name__ == "__main__":
    main()
