from __future__ import annotations

import argparse
from pathlib import Path

import pytest

import src.lead_intelligence.cli as cli_module
from src.lead_intelligence.cli import (
    VERSION_TEXT,
    main,
    sanitise_filename,
    validate_website_url,
)
from src.lead_intelligence.config import AppConfig
from src.lead_intelligence.crawler import CrawlFailure, CrawledWebsite
from src.lead_intelligence.dynamic_scraper import DynamicScraperError
from src.lead_intelligence.exporter import LeadRecord
from src.lead_intelligence.scorer import LeadScore
from src.lead_intelligence.signal_detector import (
    DetectedSignals,
    SignalEvidence,
)
from src.lead_intelligence.static_scraper import parse_page


def make_crawler_result(
    *,
    successful_pages: int = 1,
    failed_pages: int = 0,
) -> CrawledWebsite:
    """Build a deterministic crawl result."""

    page_results = [
        parse_page(
            url="https://example-city.de",
            html="<html><body><h1>Example</h1></body></html>",
        )
        for _position in range(successful_pages)
    ]

    return CrawledWebsite(
        start_url="https://example-city.de",
        visited_urls=[
            f"https://example-city.de/page-{position}"
            for position in range(successful_pages)
        ],
        failed_pages=[
            CrawlFailure(
                url=f"https://example-city.de/fail-{position}",
                error="failed",
            )
            for position in range(failed_pages)
        ],
        emails=["secret@example-city.de"] if successful_pages else [],
        phone_numbers=["030 1234 5678"] if successful_pages else [],
        contact_links=["https://example-city.de/contact"],
        document_links=["https://example-city.de/report.pdf"]
        if successful_pages
        else [],
        page_results=page_results,
    )


def make_signals() -> DetectedSignals:
    """Build deterministic detected signals."""

    return DetectedSignals(
        street_lighting=True,
        smart_city=False,
        energy_efficiency=False,
        climate_action=False,
        infrastructure_modernisation=False,
        procurement=False,
        municipal_utility=False,
        matched_keywords=["street lighting"],
        evidence=[
            SignalEvidence(
                category="street_lighting",
                keyword="street lighting",
                excerpt="Fictional evidence.",
                source_url="https://example-city.de",
            )
        ],
    )


def make_score() -> LeadScore:
    """Build deterministic lead score."""

    return LeadScore(
        total_score=30,
        priority="Low",
        breakdown=[],
        summary="Low-priority fictional summary.",
    )


def make_record() -> LeadRecord:
    """Build deterministic lead record."""

    return LeadRecord(
        organisation_name="Example City",
        organisation_type="Municipality",
        city="Example City",
        state="Hessen",
        website="https://example-city.de",
        visited_pages=1,
        emails=["secret@example-city.de"],
        phone_numbers=["030 1234 5678"],
        contact_links=["https://example-city.de/contact"],
        document_links=["https://example-city.de/report.pdf"],
        street_lighting=True,
        smart_city=False,
        energy_efficiency=False,
        climate_action=False,
        infrastructure_modernisation=False,
        procurement=False,
        municipal_utility=False,
        matched_keywords=["street lighting"],
        evidence_count=1,
        lead_score=30,
        priority="Low",
        score_summary="Low-priority fictional summary.",
        score_breakdown=[],
        last_checked="2026-07-30T08:00:00+02:00",
    )


def install_fake_analysis_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    crawler_result: CrawledWebsite | None = None,
) -> dict[str, object]:
    """Install fake analysis pipeline functions and capture calls."""

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: AppConfig(
            request_delay_seconds=0,
            output_directory=Path("data/output"),
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "configure_logging",
        lambda **kwargs: calls.setdefault("configure_logging", kwargs),
    )

    def fake_crawl_website(*args, **kwargs):
        calls["crawl_website"] = (args, kwargs)
        return crawler_result or make_crawler_result()

    def fake_detect_signals_from_pages(page_results):
        calls["detect_signals_from_pages"] = page_results
        return make_signals()

    def fake_score_lead(*args, **kwargs):
        calls["score_lead"] = (args, kwargs)
        return make_score()

    def fake_build_lead_record(**kwargs):
        calls["build_lead_record"] = kwargs
        return make_record()

    def fake_build_dashboard_summary(records, top_limit):
        calls["build_dashboard_summary"] = (records, top_limit)
        return object()

    def fake_print_dashboard(summary):
        calls["print_dashboard"] = summary
        print("DASHBOARD")

    def fake_export_leads_to_excel(*args, **kwargs):
        calls["export_leads_to_excel"] = (args, kwargs)
        return Path("/tmp/report.xlsx")

    monkeypatch.setattr(
        cli_module,
        "crawl_website",
        fake_crawl_website,
    )
    monkeypatch.setattr(
        cli_module,
        "detect_signals_from_pages",
        fake_detect_signals_from_pages,
    )
    monkeypatch.setattr(
        cli_module,
        "score_lead",
        fake_score_lead,
    )
    monkeypatch.setattr(
        cli_module,
        "build_lead_record",
        fake_build_lead_record,
    )
    monkeypatch.setattr(
        cli_module,
        "build_dashboard_summary",
        fake_build_dashboard_summary,
    )
    monkeypatch.setattr(
        cli_module,
        "print_dashboard",
        fake_print_dashboard,
    )
    monkeypatch.setattr(
        cli_module,
        "export_leads_to_excel",
        fake_export_leads_to_excel,
    )

    return calls


def analyse_args(*extra_args: str) -> list[str]:
    """Build valid analyse command args with optional extras."""

    return [
        "analyse",
        "--website",
        "https://example-city.de",
        "--name",
        "Example City",
        *extra_args,
    ]


def test_root_command_without_subcommand_displays_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running without a subcommand should print help and succeed."""

    assert main([]) == 0

    assert "usage:" in capsys.readouterr().out


def test_version_command_prints_expected_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Version command should print the package version."""

    assert main(["version"]) == 0

    assert VERSION_TEXT in capsys.readouterr().out


def test_valid_website_url_accepted() -> None:
    """Valid HTTP(S) URLs should be accepted."""

    assert (
        validate_website_url(
            " https://example-city.de/path?q=1 "
        )
        == "https://example-city.de/path?q=1"
    )


def test_invalid_scheme_rejected() -> None:
    """Only HTTP and HTTPS are valid."""

    with pytest.raises(argparse.ArgumentTypeError):
        validate_website_url("ftp://example-city.de")


def test_missing_hostname_rejected() -> None:
    """A website URL needs a host."""

    with pytest.raises(argparse.ArgumentTypeError):
        validate_website_url("https:///path")


def test_embedded_credentials_rejected() -> None:
    """Credentials should not be embedded in URLs."""

    with pytest.raises(argparse.ArgumentTypeError):
        validate_website_url("https://user:pass@example-city.de")


def test_filename_sanitisation() -> None:
    """Organisation names should become safe filename stems."""

    assert sanitise_filename(" Example City GmbH! ") == "example_city_gmbh"
    assert sanitise_filename("___") == "organisation"


def test_analyse_requires_website_and_name() -> None:
    """Analyse requires both website and name."""

    assert main(["analyse"]) == 2


def test_cli_overrides_configuration_correctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyse should apply optional CLI config overrides."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(
        analyse_args(
            "--max-pages",
            "3",
            "--timeout",
            "4.5",
            "--request-delay",
            "0",
            "--max-retries",
            "5",
            "--retry-backoff",
            "0.25",
            "--top-limit",
            "2",
            "--no-export",
        )
    ) == 0

    crawl_args, crawl_kwargs = calls["crawl_website"]

    assert crawl_args == ("https://example-city.de",)
    assert crawl_kwargs["max_pages"] == 3
    assert crawl_kwargs["request_timeout"] == 4.5
    assert crawl_kwargs["request_delay_seconds"] == 0
    assert crawl_kwargs["max_retries"] == 5
    assert crawl_kwargs["retry_backoff_seconds"] == 0.25
    assert crawl_kwargs["business_link_priority_enabled"] is True
    assert crawl_kwargs["general_links_enabled"] is True
    assert calls["build_dashboard_summary"][1] == 2


def test_analyse_browser_flags_are_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyse browser options should be forwarded to the crawler."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(
        analyse_args(
            "--scrape-mode",
            "dynamic",
            "--headed",
            "--browser-timeout",
            "12",
            "--wait-for-selector",
            " main.ready ",
            "--browser-wait",
            "0.5",
            "--accept-cookies",
            "--no-export",
        )
    ) == 0

    _crawl_args, crawl_kwargs = calls["crawl_website"]
    dynamic_options = crawl_kwargs["dynamic_options"]

    assert crawl_kwargs["scrape_mode"] == "dynamic"
    assert dynamic_options.headless is False
    assert dynamic_options.browser_timeout_seconds == 12
    assert dynamic_options.wait_for_selector == "main.ready"
    assert dynamic_options.wait_after_load_seconds == 0.5
    assert dynamic_options.accept_cookies is True


def test_analyse_default_scrape_mode_remains_static(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyse should keep static scraping as the default."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(analyse_args("--no-export")) == 0

    _crawl_args, crawl_kwargs = calls["crawl_website"]

    assert crawl_kwargs["scrape_mode"] == "static"


def test_analyse_priority_flags_are_forwarded(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Analyse priority flags should update config and crawler kwargs."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(
        analyse_args(
            "--disable-business-priority",
            "--business-links-only",
            "--no-export",
        )
    ) == 0

    _crawl_args, crawl_kwargs = calls["crawl_website"]
    output = capsys.readouterr().out

    assert crawl_kwargs["business_link_priority_enabled"] is False
    assert crawl_kwargs["general_links_enabled"] is False
    assert "Crawler priority mode: legacy contact-first" in output


def test_analyse_business_links_only_prints_effective_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Business-only mode should be visible in CLI output."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(
        analyse_args(
            "--business-links-only",
            "--no-export",
        )
    ) == 0

    _crawl_args, crawl_kwargs = calls["crawl_website"]
    output = capsys.readouterr().out

    assert crawl_kwargs["business_link_priority_enabled"] is True
    assert crawl_kwargs["general_links_enabled"] is False
    assert (
        "Crawler priority mode: business-aware, business and contact "
        "links only"
        in output
    )


def test_batch_priority_flags_are_available() -> None:
    """Batch should expose the same crawler priority overrides."""

    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "batch",
            "--input",
            "data/input/organisations.example.csv",
            "--disable-business-priority",
            "--business-links-only",
        ]
    )

    assert args.disable_business_priority is True
    assert args.business_links_only is True


def test_dynamic_runtime_failure_returns_exit_code_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dynamic scraping failures that stop analysis should return 1."""

    install_fake_analysis_pipeline(monkeypatch)

    monkeypatch.setattr(
        cli_module,
        "crawl_website",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            DynamicScraperError("browser failed")
        ),
    )

    assert main(analyse_args("--scrape-mode", "dynamic")) == 1


def test_no_export_prevents_export_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--no-export should skip Excel export."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(analyse_args("--no-export")) == 0
    assert "export_leads_to_excel" not in calls


def test_export_is_called_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Export should run unless --no-export is supplied."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(analyse_args()) == 0
    assert "export_leads_to_excel" in calls


def test_explicit_output_is_respected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An explicit --output path should be used exactly."""

    calls = install_fake_analysis_pipeline(monkeypatch)
    output_path = tmp_path / "custom.xlsx"

    assert main(
        analyse_args(
            "--output",
            str(output_path),
        )
    ) == 0

    _args, kwargs = calls["export_leads_to_excel"]

    assert kwargs["output_path"] == output_path


def test_default_output_filename_is_created_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default export path should include a sanitised organisation name."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(
        [
            "analyse",
            "--website",
            "https://example-city.de",
            "--name",
            "Example City!",
        ]
    ) == 0

    _args, kwargs = calls["export_leads_to_excel"]
    output_path = kwargs["output_path"]

    assert output_path.parent == Path("data/output")
    assert output_path.name.startswith("lead_report_example_city_")
    assert output_path.suffix == ".xlsx"


def test_zero_successful_pages_returns_exit_code_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero successfully analysed pages should fail without export."""

    calls = install_fake_analysis_pipeline(
        monkeypatch,
        crawler_result=make_crawler_result(successful_pages=0),
    )

    assert main(analyse_args()) == 1
    assert "export_leads_to_excel" not in calls


def test_partial_crawl_failure_succeeds_when_page_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial crawl failure should still succeed if at least one page worked."""

    install_fake_analysis_pipeline(
        monkeypatch,
        crawler_result=make_crawler_result(
            successful_pages=1,
            failed_pages=1,
        ),
    )

    assert main(analyse_args("--no-export")) == 0


def test_invalid_numeric_overrides_return_exit_code_two() -> None:
    """Invalid numeric CLI values should produce argument error code 2."""

    assert main(analyse_args("--max-pages", "0")) == 2


def test_analysis_pipeline_calls_all_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyse should call the crawler, detector, scorer, builder, dashboard, and exporter."""

    calls = install_fake_analysis_pipeline(monkeypatch)

    assert main(analyse_args()) == 0

    assert "crawl_website" in calls
    assert "detect_signals_from_pages" in calls
    assert "score_lead" in calls
    assert "build_lead_record" in calls
    assert "build_dashboard_summary" in calls
    assert "print_dashboard" in calls
    assert "export_leads_to_excel" in calls


def test_no_raw_emails_or_phone_values_in_standard_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Analyse output should include contact counts, not raw contact values."""

    install_fake_analysis_pipeline(monkeypatch)

    assert main(analyse_args("--no-export")) == 0

    output = capsys.readouterr().out

    assert "secret@example-city.de" not in output
    assert "030 1234 5678" not in output
    assert "Emails found: 1" in output
    assert "Valid phone numbers found: 1" in output
    assert "Document links found: 1" in output


def test_configuration_failure_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid configuration should produce exit code 2."""

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: (_ for _ in ()).throw(ValueError("bad config")),
    )

    assert main(analyse_args("--no-export")) == 2


def test_demo_export_command_completes_using_fictional_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """demo-export should call the production demo helper."""

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: AppConfig(output_directory=tmp_path),
    )
    monkeypatch.setattr(
        cli_module,
        "configure_logging",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        cli_module,
        "run_demo_export",
        lambda output_directory: Path(output_directory) / "demo.xlsx",
    )

    assert main(["demo-export"]) == 0
    assert "demo.xlsx" in capsys.readouterr().out


def test_demo_dashboard_command_prints_dashboard_sections(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """demo-dashboard should print dashboard output."""

    monkeypatch.setattr(
        cli_module,
        "load_config_with_env_file",
        lambda: AppConfig(),
    )
    monkeypatch.setattr(
        cli_module,
        "configure_logging",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        cli_module,
        "print_demo_dashboard",
        lambda top_limit: print("LEAD OVERVIEW\nTOP LEADS"),
    )

    assert main(["demo-dashboard"]) == 0

    output = capsys.readouterr().out

    assert "LEAD OVERVIEW" in output
    assert "TOP LEADS" in output


def test_command_handlers_return_integers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI entrypoint should return integers rather than exiting internally."""

    install_fake_analysis_pipeline(monkeypatch)

    assert isinstance(main(["version"]), int)
    assert isinstance(main(analyse_args("--no-export")), int)
