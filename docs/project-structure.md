# Project Structure

This guide summarises the repository layout and the responsibility of the main
modules in the Smart Infrastructure Lead Intelligence pipeline. It reflects the
current implementation and avoids generated files, caches, and fixture details.

## Repository Tree

```text
smart-infrastructure-lead-intelligence/
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── dependabot.yml
├── data/
│   ├── input/
│   │   └── organisations.example.csv
│   └── output/
├── docs/
│   ├── architecture.md
│   └── project-structure.md
├── scripts/
│   └── docker-smoke-test.sh
├── src/
│   └── lead_intelligence/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py
│       ├── cli.py
│       ├── batch.py
│       ├── config.py
│       ├── logging_config.py
│       ├── static_scraper.py
│       ├── dynamic_scraper.py
│       ├── scrape_strategy.py
│       ├── crawler.py
│       ├── signal_detector.py
│       ├── scorer.py
│       ├── exporter.py
│       ├── dashboard.py
│       └── demo_data.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Core Module Responsibilities

| Module | Responsibility | Why It Matters |
| --- | --- | --- |
| `__init__.py` | Defines package version metadata and re-exports the public package API. | Gives callers a stable import surface for the core pipeline objects and functions. |
| `__main__.py` | Package entry point for `python -m src.lead_intelligence`. | Lets the project run as a Python module and delegates execution to the CLI. |
| `main.py` | Secondary module entry point that also delegates to the CLI. | Keeps command execution consistent for direct module-style invocation. |
| `cli.py` | `argparse` command-line interface for `analyse`, `batch`, demo, and version commands. | Provides the user-facing workflow and coordinates configuration, analysis, dashboard output, and Excel export. |
| `batch.py` | Parses organisation CSV files and coordinates sequential batch analysis with partial-failure handling. | Allows larger lead research runs to continue even when individual rows fail. |
| `config.py` | Loads validated configuration from environment variables and optional `.env` files. | Keeps runtime behaviour configurable without scattering hard-coded values through the pipeline. |
| `logging_config.py` | Configures console and optional file logging. | Provides observable command execution without requiring application logic to manage handlers directly. |
| `static_scraper.py` | Downloads and parses static HTML using Requests and Beautiful Soup. | Handles the default, faster path for public pages that do not require browser rendering. |
| `dynamic_scraper.py` | Renders JavaScript-driven pages with Playwright. | Supports pages where important public content is produced after browser execution. |
| `scrape_strategy.py` | Selects static, dynamic, or automatic fallback behaviour. | Centralises the decision about when Playwright should be used. |
| `crawler.py` | Coordinates controlled multi-page crawling with retries, request pacing, deduplication, and failure tracking. | Turns one starting website into a bounded set of parsed pages while recording recoverable failures. |
| `signal_detector.py` | Detects transparent rule-based business signals and supporting evidence. | Makes lead qualification inspectable through explicit keyword categories and excerpts. |
| `scorer.py` | Calculates a 0-100 lead score and priority classification. | Converts detected signals and public contact availability into a transparent prioritisation aid. |
| `exporter.py` | Produces the Excel workbook and reporting sheets. | Creates structured output for review, sharing, and follow-up analysis. |
| `dashboard.py` | Builds and formats management-level summary metrics. | Gives a quick terminal overview of priorities, contacts, evidence, and signal distribution. |
| `demo_data.py` | Provides fictional demonstration data without using real organisations or contact details. | Enables demos, tests, and CI checks without public-network scraping or real contact data. |

## Supporting Areas

| Area | Purpose |
| --- | --- |
| `tests/` | Deterministic unit and integration tests, including fixture-based HTML coverage and no public-network dependency for automated tests. |
| `data/input/` | Contains the example organisation CSV used to show the expected batch input format. |
| `data/output/` | Holds generated Excel reports and other local outputs; generated files are ignored by Git. |
| `scripts/` | Contains operational helper scripts, currently the Docker smoke test. |
| `.github/` | Contains GitHub Actions CI and Dependabot configuration. |
| `docs/` | Contains architecture and project documentation. |

## Design Principles

- Separation of concerns across CLI, configuration, scraping, crawling,
  detection, scoring, exporting, and dashboard modules.
- Dependency injection in scraper, crawler, and batch paths for deterministic
  tests.
- Static scraping first, with Playwright used only when requested or when
  automatic mode judges static content insufficient.
- Deterministic tests built around local fixtures and fictional demo data.
- Transparent rule-based scoring rather than predictive or machine-learning
  scoring.
- Configuration over hard-coded runtime values.
- Safe partial-failure handling for batch runs.
- No raw contact values in standard CLI summaries.
- Non-root Docker runtime.
- CI verification for Python tests, browser setup, CLI demos, Docker, Compose,
  and smoke testing.
