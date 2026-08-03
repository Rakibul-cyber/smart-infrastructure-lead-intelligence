from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

import src.lead_intelligence.cli as cli_module
from src.lead_intelligence.batch import (
    BatchFailure,
    BatchResult,
    OrganisationInput,
    ParsedOrganisationRow,
    analyse_organisation,
    export_batch_failures,
    normalise_column_name,
    read_organisations_csv,
    read_parsed_organisations_csv,
    run_batch_analysis,
)
from src.lead_intelligence.config import AppConfig
from src.lead_intelligence.crawler import CrawledWebsite
from src.lead_intelligence.exporter import LeadRecord
from src.lead_intelligence.signal_detector import SignalEvidence
from src.lead_intelligence.static_scraper import parse_page


def write_csv(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    """Write a tiny CSV fixture."""

    path.write_text(content, encoding=encoding)

    return path


def make_organisation(
    name: str = "Example City",
    website: str = "https://example-city.example",
) -> OrganisationInput:
    """Build deterministic organisation input."""

    return OrganisationInput(
        organisation_name=name,
        organisation_type="Municipality",
        city="Example City",
        state="Example State",
        website=website,
    )


def make_parsed_row(
    row_number: int = 2,
    name: str = "Example City",
    website: str = "https://example-city.example",
) -> ParsedOrganisationRow:
    """Build deterministic parsed CSV row."""

    return ParsedOrganisationRow(
        row_number=row_number,
        organisation=make_organisation(
            name=name,
            website=website,
        ),
    )


def make_record(
    name: str = "Example City",
    website: str = "https://example-city.example",
    score: int = 30,
) -> LeadRecord:
    """Build deterministic lead record."""

    return LeadRecord(
        organisation_name=name,
        organisation_type="Municipality",
        city="Example City",
        state="Example State",
        website=website,
        visited_pages=1,
        emails=["secret@example-city.example"],
        phone_numbers=["030 1234 5678"],
        contact_links=["https://example-city.example/contact"],
        street_lighting=True,
        smart_city=False,
        energy_efficiency=False,
        climate_action=False,
        infrastructure_modernisation=False,
        procurement=False,
        municipal_utility=False,
        matched_keywords=["street lighting"],
        evidence_count=1,
        lead_score=score,
        priority="Low",
        score_summary="Low-priority fictional summary.",
        score_breakdown=[],
        last_checked="2026-07-30T08:00:00+02:00",
    )


def make_evidence(
    keyword: str = "street lighting",
    source_url: str = "https://example-city.example",
    excerpt: str = "Fictional evidence.",
) -> SignalEvidence:
    """Build deterministic signal evidence."""

    return SignalEvidence(
        category="street_lighting",
        keyword=keyword,
        excerpt=excerpt,
        source_url=source_url,
    )


def make_crawler_result(successful_pages: int = 1) -> CrawledWebsite:
    """Build deterministic crawler result."""

    page_results = [
        parse_page(
            url="https://example-city.example",
            html=(
                "<html><body>Street lighting procurement "
                "contact@example-city.example 030 1234 5678</body></html>"
            ),
        )
        for _position in range(successful_pages)
    ]

    return CrawledWebsite(
        start_url="https://example-city.example",
        visited_urls=[
            f"https://example-city.example/page-{position}"
            for position in range(successful_pages)
        ],
        failed_pages=[],
        emails=["secret@example-city.example"] if successful_pages else [],
        phone_numbers=["030 1234 5678"] if successful_pages else [],
        contact_links=["https://example-city.example/contact"],
        page_results=page_results,
    )


def install_fake_batch_cli(
    monkeypatch: pytest.MonkeyPatch,
    *,
    result: BatchResult,
    output_directory: Path,
) -> dict[str, object]:
    """Patch CLI batch dependencies and capture calls."""

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: AppConfig(
            output_directory=output_directory,
            request_delay_seconds=0,
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "configure_logging",
        lambda **kwargs: calls.setdefault("configure_logging", kwargs),
    )
    monkeypatch.setattr(
        cli_module,
        "read_parsed_organisations_csv",
        lambda input_path: [
            make_parsed_row(
                row_number=2,
                name="Example City",
            )
        ],
    )
    monkeypatch.setattr(
        cli_module,
        "run_batch_analysis",
        lambda organisations, config: calls.setdefault(
            "run_batch_analysis",
            (organisations, config),
        )
        and result,
    )
    monkeypatch.setattr(
        cli_module,
        "build_dashboard_summary",
        lambda records, top_limit: calls.setdefault(
            "build_dashboard_summary",
            (records, top_limit),
        )
        or object(),
    )
    def fake_print_dashboard(summary):
        calls["print_dashboard"] = summary
        print("DASHBOARD")

    monkeypatch.setattr(
        cli_module,
        "print_dashboard",
        fake_print_dashboard,
    )
    def fake_export_leads_to_excel(**kwargs):
        calls["export_leads_to_excel"] = kwargs
        return Path(kwargs["output_path"])

    def fake_export_batch_failures(failures, output_path):
        calls["export_batch_failures"] = (failures, output_path)
        return Path(output_path)

    monkeypatch.setattr(
        cli_module,
        "export_leads_to_excel",
        fake_export_leads_to_excel,
    )
    monkeypatch.setattr(
        cli_module,
        "export_batch_failures",
        fake_export_batch_failures,
    )

    return calls


def test_normalise_column_name() -> None:
    """Column matching should be case-insensitive and separator-flexible."""

    assert normalise_column_name(" Organisation Name ") == "organisation_name"
    assert normalise_column_name("organisation-name") == "organisation_name"
    assert normalise_column_name("__Website  URL__") == "website_url"


def test_valid_required_only_csv(tmp_path: Path) -> None:
    """Only organisation_name and website are required."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\nExample City,https://example-city.example\n",
    )

    organisations = read_organisations_csv(csv_path)

    assert organisations == [
        OrganisationInput(
            organisation_name="Example City",
            organisation_type="Unknown",
            city="",
            state="",
            website="https://example-city.example",
        )
    ]


def test_optional_fields_and_defaults(tmp_path: Path) -> None:
    """Optional fields should be stripped and defaulted."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        (
            "organisation_name,organisation_type,city,state,website\n"
            " Example City , Municipality , Example City , Hesse , "
            " https://example-city.example/path?q=1 \n"
        ),
    )

    organisation = read_organisations_csv(csv_path)[0]

    assert organisation.organisation_type == "Municipality"
    assert organisation.city == "Example City"
    assert organisation.state == "Hesse"
    assert organisation.website == "https://example-city.example/path?q=1"


def test_bom_support(tmp_path: Path) -> None:
    """CSV input should support UTF-8 with BOM."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\nExample City,https://example-city.example\n",
        encoding="utf-8-sig",
    )

    assert read_organisations_csv(csv_path)[0].organisation_name == "Example City"


def test_flexible_header_normalisation(tmp_path: Path) -> None:
    """Alternative header spellings should map to required columns."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "Organisation Name,Website\nExample City,https://example-city.example\n",
    )

    organisation = read_organisations_csv(csv_path)[0]

    assert organisation.organisation_name == "Example City"
    assert organisation.website == "https://example-city.example"


def test_unknown_columns_are_ignored(tmp_path: Path) -> None:
    """Extra CSV columns should not affect parsing."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        (
            "organisation_name,website,unknown\n"
            "Example City,https://example-city.example,ignored\n"
        ),
    )

    assert len(read_organisations_csv(csv_path)) == 1


def test_duplicate_normalised_headers_rejected(tmp_path: Path) -> None:
    """Duplicate headers after normalisation should be rejected."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        (
            "organisation_name,Organisation Name,website\n"
            "Example City,Duplicate,https://example-city.example\n"
        ),
    )

    with pytest.raises(ValueError, match="duplicate columns"):
        read_organisations_csv(csv_path)


def test_missing_required_headers_rejected(tmp_path: Path) -> None:
    """Required headers should be enforced."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name\nExample City\n",
    )

    with pytest.raises(ValueError, match="website"):
        read_organisations_csv(csv_path)


def test_blank_organisation_rejected_with_row_number(tmp_path: Path) -> None:
    """Blank organisation names should include row number."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\n,https://example-city.example\n",
    )

    with pytest.raises(ValueError, match="row 2.*organisation_name"):
        read_organisations_csv(csv_path)


def test_blank_website_rejected_with_row_number(tmp_path: Path) -> None:
    """Blank website values should include row number."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\nExample City,\n",
    )

    with pytest.raises(ValueError, match="row 2.*website"):
        read_organisations_csv(csv_path)


def test_invalid_website_rejected_with_row_number(tmp_path: Path) -> None:
    """Invalid website values should include row number."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\nExample City,ftp://example-city.example\n",
    )

    with pytest.raises(ValueError, match="row 2"):
        read_organisations_csv(csv_path)


def test_blank_rows_skipped(tmp_path: Path) -> None:
    """Completely blank rows should be ignored."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        (
            "organisation_name,website\n"
            ",\n"
            "Example City,https://example-city.example\n"
        ),
    )

    parsed_rows = read_parsed_organisations_csv(csv_path)

    assert len(parsed_rows) == 1
    assert parsed_rows[0].row_number == 3


def test_no_usable_rows_rejected(tmp_path: Path) -> None:
    """A header-only or blank-only CSV should fail validation."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        "organisation_name,website\n,\n",
    )

    with pytest.raises(ValueError, match="no usable data rows"):
        read_organisations_csv(csv_path)


def test_input_order_preserved(tmp_path: Path) -> None:
    """CSV parsing should preserve input row order."""

    csv_path = write_csv(
        tmp_path / "input.csv",
        (
            "organisation_name,website\n"
            "First,https://first.example\n"
            "Second,https://second.example\n"
        ),
    )

    organisations = read_organisations_csv(csv_path)

    assert [organisation.organisation_name for organisation in organisations] == [
        "First",
        "Second",
    ]


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    """Missing files should raise FileNotFoundError."""

    with pytest.raises(FileNotFoundError):
        read_organisations_csv(tmp_path / "missing.csv")


def test_empty_batch_input_rejected() -> None:
    """Batch processing should reject empty organisation lists."""

    with pytest.raises(ValueError, match="must not be empty"):
        run_batch_analysis([], AppConfig())


def test_successful_records_preserve_order() -> None:
    """Successful records should preserve input order."""

    rows = [
        make_parsed_row(2, "First", "https://first.example"),
        make_parsed_row(3, "Second", "https://second.example"),
    ]

    def fake_analyse(organisation: OrganisationInput, config: AppConfig):
        return (
            make_record(
                name=organisation.organisation_name,
                website=organisation.website,
            ),
            [make_evidence(source_url=organisation.website)],
        )

    result = run_batch_analysis(
        rows,
        AppConfig(),
        analyse_function=fake_analyse,
    )

    assert [
        record.organisation_name
        for record in result.successful_records
    ] == ["First", "Second"]


def test_one_failure_does_not_stop_later_rows() -> None:
    """One row failure should not abort later rows."""

    rows = [
        make_parsed_row(2, "First", "https://first.example"),
        make_parsed_row(3, "Broken", "https://broken.example"),
        make_parsed_row(4, "Later", "https://later.example"),
    ]

    def fake_analyse(organisation: OrganisationInput, config: AppConfig):
        if organisation.organisation_name == "Broken":
            raise RuntimeError("failed")

        return (
            make_record(
                name=organisation.organisation_name,
                website=organisation.website,
            ),
            [],
        )

    result = run_batch_analysis(
        rows,
        AppConfig(),
        analyse_function=fake_analyse,
    )

    assert [record.organisation_name for record in result.successful_records] == [
        "First",
        "Later",
    ]
    assert len(result.failures) == 1


def test_failures_contain_row_number_and_organisation_details() -> None:
    """Failure entries should contain useful row metadata."""

    row = make_parsed_row(7, "Broken", "https://broken.example")

    result = run_batch_analysis(
        [row],
        AppConfig(),
        analyse_function=lambda organisation, config: (_ for _ in ()).throw(
            RuntimeError("boom")
        ),
    )

    assert result.failures == [
        BatchFailure(
            row_number=7,
            organisation_name="Broken",
            website="https://broken.example",
            error="boom",
        )
    ]


def test_all_failures_handled_safely() -> None:
    """A batch where every row fails should still return a result."""

    rows = [
        make_parsed_row(2, "First", "https://first.example"),
        make_parsed_row(3, "Second", "https://second.example"),
    ]

    result = run_batch_analysis(
        rows,
        AppConfig(),
        analyse_function=lambda organisation, config: (_ for _ in ()).throw(
            RuntimeError("failed")
        ),
    )

    assert result.successful_records == []
    assert len(result.failures) == 2
    assert result.total_input_rows == 2


def test_duplicate_website_evidence_combined_and_deduplicated() -> None:
    """Duplicate website evidence is combined by category, keyword, and source URL."""

    rows = [
        make_parsed_row(2, "First", "https://same.example"),
        make_parsed_row(3, "Second", "https://same.example"),
    ]

    def fake_analyse(organisation: OrganisationInput, config: AppConfig):
        return (
            make_record(
                name=organisation.organisation_name,
                website=organisation.website,
            ),
            [
                make_evidence(
                    keyword="street lighting",
                    source_url="https://same.example/source",
                    excerpt=f"{organisation.organisation_name} duplicate",
                ),
                make_evidence(
                    keyword=organisation.organisation_name,
                    source_url="https://same.example/source",
                ),
            ],
        )

    result = run_batch_analysis(
        rows,
        AppConfig(),
        analyse_function=fake_analyse,
    )

    assert len(result.evidence_by_website["https://same.example"]) == 3


def test_analyse_organisation_maps_pipeline_correctly() -> None:
    """analyse_organisation should map crawl, signal, score, and record data."""

    calls: dict[str, object] = {}
    config = AppConfig(
        max_pages_per_site=2,
        request_timeout=3,
        request_delay_seconds=0,
        max_retries=4,
        retry_backoff_seconds=0.5,
    )

    def fake_crawl(*args, **kwargs):
        calls["crawl"] = (args, kwargs)
        return make_crawler_result()

    record, evidence = analyse_organisation(
        make_organisation(),
        config,
        crawl_function=fake_crawl,
    )

    crawl_args, crawl_kwargs = calls["crawl"]

    assert crawl_args == ("https://example-city.example",)
    assert crawl_kwargs["max_pages"] == 2
    assert crawl_kwargs["request_timeout"] == 3
    assert crawl_kwargs["request_delay_seconds"] == 0
    assert crawl_kwargs["max_retries"] == 4
    assert crawl_kwargs["retry_backoff_seconds"] == 0.5
    assert crawl_kwargs["business_link_priority_enabled"] is True
    assert crawl_kwargs["general_links_enabled"] is True
    assert record.organisation_name == "Example City"
    assert record.visited_pages == 1
    assert evidence


def test_zero_successful_pages_raises_runtime_error() -> None:
    """Zero successfully crawled pages should fail one organisation."""

    with pytest.raises(RuntimeError, match="no pages"):
        analyse_organisation(
            make_organisation(),
            AppConfig(),
            crawl_function=lambda *args, **kwargs: make_crawler_result(
                successful_pages=0
            ),
        )


def test_supplied_analyse_function_is_used() -> None:
    """run_batch_analysis should use the injected analyse function."""

    calls: list[str] = []

    def fake_analyse(organisation: OrganisationInput, config: AppConfig):
        calls.append(organisation.organisation_name)
        return make_record(), []

    run_batch_analysis(
        [make_parsed_row(name="Injected")],
        AppConfig(),
        analyse_function=fake_analyse,
    )

    assert calls == ["Injected"]


def test_input_configuration_is_not_mutated() -> None:
    """Batch helpers should not mutate frozen AppConfig."""

    config = AppConfig(request_delay_seconds=0)
    original_config = replace(config)

    run_batch_analysis(
        [make_parsed_row()],
        config,
        analyse_function=lambda organisation, config: (make_record(), []),
    )

    assert config == original_config


def test_failure_csv_file_and_parent_created(tmp_path: Path) -> None:
    """Failure CSV export should create parent directories."""

    output_path = tmp_path / "nested" / "failures.csv"

    created_path = export_batch_failures(
        [
            BatchFailure(
                row_number=2,
                organisation_name="Fictional Ämt",
                website="https://example-city.example",
                error="failed",
            )
        ],
        output_path,
    )

    assert created_path == output_path.resolve()
    assert output_path.exists()


def test_failure_csv_headers_and_rows(tmp_path: Path) -> None:
    """Failure CSV should include expected headers and rows."""

    output_path = tmp_path / "failures.csv"
    export_batch_failures(
        [
            BatchFailure(
                row_number=2,
                organisation_name="Example City",
                website="https://example-city.example",
                error="failed",
            )
        ],
        output_path,
    )

    with output_path.open(encoding="utf-8", newline="") as input_file:
        rows = list(csv.reader(input_file))

    assert rows == [
        ["Row Number", "Organisation Name", "Website", "Error"],
        ["2", "Example City", "https://example-city.example", "failed"],
    ]


def test_empty_failures_still_writes_headers(tmp_path: Path) -> None:
    """An empty failure list should still produce a header-only CSV."""

    output_path = tmp_path / "failures.csv"
    export_batch_failures([], output_path)

    assert output_path.read_text(encoding="utf-8").startswith(
        "Row Number,Organisation Name,Website,Error"
    )


def test_failure_csv_utf8_content_works(tmp_path: Path) -> None:
    """Failure CSV should preserve UTF-8 content."""

    output_path = tmp_path / "failures.csv"
    export_batch_failures(
        [
            BatchFailure(
                row_number=2,
                organisation_name="München Infrastruktur",
                website="https://muenchen.example",
                error="ungültig",
            )
        ],
        output_path,
    )

    assert "München Infrastruktur" in output_path.read_text(encoding="utf-8")


def test_batch_cli_requires_input() -> None:
    """The batch command requires --input."""

    assert cli_module.main(["batch"]) == 2


def test_valid_batch_success_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A fully successful batch should return 0."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 0


def test_batch_browser_flags_are_applied_to_effective_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Batch browser flags should be passed through effective config."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert (
        cli_module.main(
            [
                "batch",
                "--input",
                "input.csv",
                "--scrape-mode",
                "auto",
                "--headed",
                "--browser-timeout",
                "8",
                "--wait-for-selector",
                " main.ready ",
                "--browser-wait",
                "0.25",
                "--accept-cookies",
            ]
        )
        == 0
    )

    _organisations, config = calls["run_batch_analysis"]

    assert config.scrape_mode == "auto"
    assert config.browser_headless is False
    assert config.browser_timeout_seconds == 8
    assert config.browser_wait_for_selector == "main.ready"
    assert config.browser_wait_after_load_seconds == 0.25
    assert config.browser_accept_cookies is True


def test_partial_failure_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A partial batch failure should return exit code 1."""

    result = BatchResult(
        total_input_rows=2,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[
            BatchFailure(
                3,
                "Broken",
                "https://broken.example",
                "failed",
            )
        ],
    )
    install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 1


def test_all_failures_return_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An all-failure batch should return exit code 1."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[],
        evidence_by_website={},
        failures=[
            BatchFailure(
                2,
                "Broken",
                "https://broken.example",
                "failed",
            )
        ],
    )
    install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 1


def test_csv_validation_error_returns_two(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CSV validation errors should return exit code 2."""

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: AppConfig(output_directory=tmp_path),
    )
    monkeypatch.setattr(
        cli_module,
        "read_parsed_organisations_csv",
        lambda input_path: (_ for _ in ()).throw(ValueError("bad csv")),
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 2


def test_no_export_prevents_batch_excel_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """--no-export should prevent Excel creation."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv", "--no-export"]) == 0
    assert "export_leads_to_excel" not in calls


def test_no_failure_report_prevents_failure_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """--no-failure-report should prevent failure CSV creation."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert (
        cli_module.main(
            ["batch", "--input", "input.csv", "--no-failure-report"]
        )
        == 0
    )
    assert "export_batch_failures" not in calls


def test_explicit_batch_output_paths_respected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Explicit Excel and failure paths should be used exactly."""

    excel_path = tmp_path / "batch.xlsx"
    failures_path = tmp_path / "failures.csv"
    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert (
        cli_module.main(
            [
                "batch",
                "--input",
                "input.csv",
                "--output",
                str(excel_path),
                "--failures-output",
                str(failures_path),
            ]
        )
        == 0
    )

    assert calls["export_leads_to_excel"]["output_path"] == excel_path
    assert calls["export_batch_failures"][1] == failures_path


def test_default_timestamped_paths_generated_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Default batch outputs should use timestamped filenames."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 0

    excel_path = calls["export_leads_to_excel"]["output_path"]
    failure_path = calls["export_batch_failures"][1]

    assert excel_path.parent == tmp_path
    assert excel_path.name.startswith("batch_lead_report_")
    assert excel_path.suffix == ".xlsx"
    assert failure_path.parent == tmp_path
    assert failure_path.name.startswith("batch_failures_")
    assert failure_path.suffix == ".csv"


def test_dashboard_printed_when_successes_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The batch command should print the dashboard when records succeed."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 0
    assert "DASHBOARD" in capsys.readouterr().out


def test_no_excel_export_when_every_row_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A fully failed batch should not create an empty Excel report."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[],
        evidence_by_website={},
        failures=[
            BatchFailure(
                2,
                "Broken",
                "https://broken.example",
                "failed",
            )
        ],
    )
    calls = install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 1
    assert "export_leads_to_excel" not in calls


def test_no_raw_contact_values_printed_by_batch_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batch output should not print raw email or phone values."""

    result = BatchResult(
        total_input_rows=1,
        successful_records=[make_record()],
        evidence_by_website={"https://example-city.example": [make_evidence()]},
        failures=[],
    )
    install_fake_batch_cli(
        monkeypatch,
        result=result,
        output_directory=tmp_path,
    )

    assert cli_module.main(["batch", "--input", "input.csv"]) == 0
    output = capsys.readouterr().out

    assert "secret@example-city.example" not in output
    assert "030 1234 5678" not in output
    assert "BATCH ANALYSIS" in output
