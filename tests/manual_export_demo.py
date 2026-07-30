from __future__ import annotations

from pathlib import Path

from src.lead_intelligence.demo_data import run_demo_export


OUTPUT_DIRECTORY = Path("data/output")


def main() -> None:
    """Generate the fictional Excel demonstration workbook."""

    output_path = run_demo_export(OUTPUT_DIRECTORY)

    print(f"Excel demo report written to: {output_path}")


if __name__ == "__main__":
    main()
