# Smart Infrastructure Lead Intelligence

[![CI](https://github.com/Rakibul-cyber/smart-infrastructure-lead-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/Rakibul-cyber/smart-infrastructure-lead-intelligence/actions/workflows/ci.yml)

A Python-based portfolio project for discovering, extracting, and analysing
publicly available B2B and public-sector lead data. Later checkpoints may add
cleaning and dynamic website automation workflows.

## Overview

Sales teams working with smart infrastructure products often need to identify
municipalities, public utilities, infrastructure operators, and organisations
that may have relevant digitalisation, energy-efficiency, or modernisation needs.

Manual research is slow, inconsistent, and difficult to scale.

This project demonstrates how Python can support that workflow by collecting
public information from websites and transforming it into structured,
reviewable lead data.

## Current Features

- Static HTML webpage scraping with Requests and Beautiful Soup.
- Extraction of public email addresses, telephone numbers, internal links, and
  contact-related links.
- Controlled breadth-first crawling across a small number of internal pages.
- Business signal detection for smart infrastructure sales research.
- Transparent rule-based keyword matching with English and German terms.
- Transparent lead scoring based on detected signals and public contact
  information.
- Professional Excel reporting with lead tables, evidence, and run summaries.
- Management dashboard summary for fast review of run-level lead research
  results.
- Professional command-line interface for one-organisation, batch, and demo
  workflows.
- Batch CSV organisation analysis with combined Excel reporting and failure
  CSV output.
- Targeted Playwright rendering for JavaScript-heavy pages when explicitly
  requested or when `auto` mode judges static HTML insufficient.
- Central application configuration with environment-variable and optional
  `.env` file support.
- Structured console logging with optional UTF-8 file logging.
- Controlled retry logic and respectful request pacing for public webpages.
- Offline Pytest coverage using deterministic HTML fixtures.
- Docker runtime and test-image packaging with local smoke testing.
- GitHub Actions continuous integration for tests, demos, and Docker checks.

Business signal detection is intentionally simple and inspectable at this
stage. It uses explicit keyword categories and evidence excerpts rather than
machine learning or AI classification.

Lead scores support prioritisation for manual research. They are transparent
rules, not predictive AI, and do not replace human review.

## Command-Line Usage

Show available commands:

```bash
python -m src.lead_intelligence --help
```

Print the package version:

```bash
python -m src.lead_intelligence version
```

Analyse one organisation website:

```bash
python -m src.lead_intelligence analyse \
  --website https://example-city.de \
  --name "Example City" \
  --type Municipality \
  --city "Example City" \
  --state Hessen
```

The `analyse` command crawls the supplied HTTP or HTTPS URL, detects business
signals, scores the lead, prints a dashboard plus a concise organisation
summary, and writes an Excel report by default. The summary prints contact
counts only, not raw email addresses or phone numbers.

Useful analysis options:

```bash
python -m src.lead_intelligence analyse \
  --website https://example-city.de \
  --name "Example City" \
  --max-pages 3 \
  --timeout 10 \
  --request-delay 0.5 \
  --max-retries 2 \
  --retry-backoff 1 \
  --top-limit 5 \
  --output data/output/example_city.xlsx
```

Use `--no-export` to print the analysis without creating an Excel workbook.
Without `--output`, reports are written to:

```text
data/output/lead_report_<organisation-name>_<YYYYMMDD_HHMMSS>.xlsx
```

Static scraping remains the default. Use dynamic rendering only for websites
where public content is JavaScript-rendered:

```bash
python -m src.lead_intelligence analyse \
  --website https://example-city.de \
  --name "Example City" \
  --scrape-mode dynamic \
  --headed
```

Use `auto` mode to try the static scraper first and fall back to Chromium only
when the static HTML looks too thin or clearly asks for JavaScript:

```bash
python -m src.lead_intelligence analyse \
  --website https://example-city.de \
  --name "Example City" \
  --scrape-mode auto
```

For pages that need a specific rendered element before extraction:

```bash
python -m src.lead_intelligence analyse \
  --website https://example-city.de \
  --name "Example City" \
  --scrape-mode dynamic \
  --wait-for-selector "main .content" \
  --browser-wait 0.5
```

Analyse a CSV batch and write a combined Excel report:

```bash
python -m src.lead_intelligence batch \
  --input data/input/organisations.example.csv \
  --output data/output/batch_report.xlsx
```

The batch command analyses each organisation independently and continues when
one row fails. It prints a combined dashboard when at least one organisation
succeeds, writes one Excel workbook for successful records unless `--no-export`
is supplied, and writes a failure CSV unless `--no-failure-report` is supplied.

Without explicit paths, batch outputs are written to:

```text
data/output/batch_lead_report_<YYYYMMDD_HHMMSS>.xlsx
data/output/batch_failures_<YYYYMMDD_HHMMSS>.csv
```

Demo commands use fictional data, do not crawl live websites, and do not use
real customer data:

```bash
python -m src.lead_intelligence demo-dashboard
python -m src.lead_intelligence demo-export
```

Run the local fictional dynamic-rendering demo with:

```bash
python -m tests.manual_dynamic_demo
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Success, including help/version/demo commands. |
| `1` | Analysis ran but failed meaningfully: a one-site runtime/network/no-pages failure, or one or more failed rows in a batch. |
| `2` | Argument, configuration, or CSV validation error. |

## Batch CSV Analysis

Batch input files are UTF-8 CSV files with flexible, case-insensitive column
matching. Spaces and hyphens in headers are treated as underscores.

Required columns:

- `organisation_name`
- `website`

Optional columns:

- `organisation_type`, defaulting to `Unknown`
- `city`, defaulting to blank
- `state`, defaulting to blank

Example CSV content:

```csv
organisation_name,organisation_type,city,state,website
Example City Infrastructure Office,Municipality,Example City,Example State,https://example-city.example
Sample Stadtwerke Services,Public Utility,Sampletown,Fictional Region,https://sample-stadtwerke.example
Fictional Infrastructure Authority,Infrastructure Authority,Demoburg,Example State,https://infrastructure-authority.example
```

The committed sample file at `data/input/organisations.example.csv` contains
fictional data only and uses reserved example domains. Running it may still
attempt normal website requests, so it is primarily a schema example.

Failure reports contain:

- Row Number
- Organisation Name
- Website
- Error

The failure CSV includes headers even when no rows fail. If every organisation
fails, the command still writes the failure report unless disabled, skips the
empty Excel workbook, and returns exit code `1`.

## Configuration

Configuration uses the Python standard library and can be supplied through
environment variables or an optional `.env` file.

Create a local environment file with:

```bash
cp .env.example .env
```

Supported variables:

| Variable | Default | Description |
| --- | --- | --- |
| `REQUEST_TIMEOUT` | `20` | HTTP request timeout in seconds. |
| `REQUEST_DELAY_SECONDS` | `1` | Delay between different page URL requests during crawling. |
| `MAX_PAGES_PER_SITE` | `5` | Maximum successful pages to crawl per site. |
| `MAX_RETRIES` | `2` | Number of retry attempts for retryable request failures. |
| `RETRY_BACKOFF_SECONDS` | `1` | Base exponential backoff delay for retries to the same URL. |
| `USER_AGENT` | `SmartInfrastructureLeadIntelligence/0.1` | HTTP User-Agent string. |
| `SCRAPE_MODE` | `static` | Scraping mode: `static`, `dynamic`, or `auto`. |
| `BROWSER_HEADLESS` | `true` | Run Chromium headlessly when browser rendering is used. |
| `BROWSER_TIMEOUT_SECONDS` | `30` | Browser navigation and action timeout in seconds. |
| `BROWSER_WAIT_AFTER_LOAD_SECONDS` | `0` | Optional post-load browser wait before parsing. |
| `BROWSER_WAIT_FOR_SELECTOR` | blank | Optional CSS selector to wait for in browser mode. |
| `BROWSER_ACCEPT_COOKIES` | `false` | Try conservative cookie-accept buttons in browser mode. |
| `TOP_LEADS_LIMIT` | `5` | Number of top leads to show in dashboard summaries. |
| `OUTPUT_DIRECTORY` | `data/output` | Default generated-output directory. |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `LOG_FILE` | blank | Optional path for a UTF-8 application log file. |

Precedence is:

1. Explicit environment variables
2. Values from `.env`
3. Application defaults

The `.env` file remains ignored by Git. Do not store secrets or real
credentials in this project.

Console logging is enabled by default. File logging is optional:

```text
LOG_LEVEL=DEBUG
LOG_FILE=logs/lead-intelligence.log
```

Generated log files should not be committed.

## Scraping Modes

The application supports three scraping modes:

- `static`: Requests plus Beautiful Soup only. This is the default because it is
  faster, simpler, more resource-efficient, and usually sufficient for public
  HTML pages.
- `dynamic`: Chromium rendering with Playwright for JavaScript-rendered public
  pages.
- `auto`: Static first, then dynamic only when the static HTML appears
  insufficient.

Automatic fallback is conservative. It considers short visible text, missing
title and main heading, or clear JavaScript-required phrases. It does not use
the absence of email addresses or phone numbers as a fallback trigger.

Install Playwright support with:

```bash
python -m pip install playwright
python -m playwright install chromium
```

Cookie-dialog handling is intentionally limited. When `--accept-cookies` or
`BROWSER_ACCEPT_COOKIES=true` is used, the browser scraper tries a small list of
common accept-style button labels. It does not click arbitrary buttons or
inject JavaScript to bypass consent systems.

The tool does not bypass CAPTCHA, authentication, robots restrictions, access
controls, anti-bot controls, or blocked HTTP responses. It does not use stealth
plugins, proxies, or user-agent rotation.

## Docker

The Docker image uses the pinned Playwright Python base image:

```text
mcr.microsoft.com/playwright/python:v1.61.0-noble
```

Build the runtime image:

```bash
docker build -t lead-intelligence .
```

Run CLI commands:

```bash
docker run --rm lead-intelligence --help
docker run --rm lead-intelligence version
docker run --rm lead-intelligence demo-dashboard
```

Generate the fictional demo workbook into the local output folder:

```bash
mkdir -p data/output
docker run --rm \
  -v "$(pwd)/data/output:/app/data/output" \
  lead-intelligence demo-export
```

Run the container with Compose:

```bash
docker compose run --rm lead-intelligence --help
```

Compose mounts `data/input` read-only and mounts `data/output` plus `logs` as
writable directories.

Build the test target:

```bash
docker build --target test -t lead-intelligence:test .
docker run --rm lead-intelligence:test
```

Run the local Docker smoke test:

```bash
scripts/docker-smoke-test.sh
```

## Continuous Integration

GitHub Actions runs on pushes to `main`, pull requests targeting `main`, and
manual workflow dispatches. Outdated runs on the same branch are cancelled, and
the workflow uses read-only repository permissions.

CI verifies:

- Python tests.
- The local Playwright Chromium browser test.
- Compilation validation with `compileall`.
- CLI version, dashboard demo, and fictional Excel demo commands.
- Fictional Excel output generation under `data/output`.
- Docker runtime image build.
- Docker test image build.
- Docker Compose configuration.
- The Docker smoke test.

The CI workflow uses fictional demo data and local fixtures only. It does not
scrape public organisations or upload logs containing scraped contact data.

## Retry And Pacing

The scraper retries only controlled, retryable request failures:

- Timeouts
- Connection errors
- HTTP `408`, `425`, `429`, `500`, `502`, `503`, and `504`

It does not retry blocking or permanent-looking statuses such as `401`, `403`,
or `404`. Retry delays use exponential backoff:

```text
RETRY_BACKOFF_SECONDS * (2 ** (retry_number - 1))
```

Numeric `Retry-After` headers are respected when they are greater than the
calculated backoff. HTTP-date `Retry-After` values are ignored for now.

`RETRY_BACKOFF_SECONDS` controls repeated attempts to the same URL.
`REQUEST_DELAY_SECONDS` controls the respectful delay between different page
URLs in a crawl. The crawler remains deliberately rate-limited and does not
bypass CAPTCHA, anti-bot, or access-control systems.

Example:

```text
MAX_RETRIES=2
RETRY_BACKOFF_SECONDS=1
REQUEST_DELAY_SECONDS=1
```

## Lead Scoring

Default scoring weights:

- Street lighting: 25
- Procurement: 20
- Smart city: 15
- Energy efficiency: 15
- Climate action: 10
- Infrastructure modernisation: 10
- Municipal utility: 5
- Contact information: 5

Scores are capped at 100 and classified as:

- High: 80-100
- Medium: 50-79
- Low: 0-49

## Excel Reporting

The exporter creates an `.xlsx` workbook with four sheets:

- All Leads: one row per analysed organisation.
- High Priority: only leads with High priority, with headers even when empty.
- Evidence: one row per transparent keyword evidence item.
- Run Summary: aggregate counts, average score, and export timestamp.

Generate the fictional demo workbook with:

```bash
python -m src.lead_intelligence demo-export
python -m tests.manual_export_demo
```

The demo writes:

```text
data/output/lead_intelligence_report.xlsx
```

Generated files in `data/output/` are ignored by Git, except for the
placeholder `.gitkeep`.

## Management Dashboard

The terminal dashboard is designed for fast decision-making by founders, sales
managers, and business-development users. It summarises a completed research
run without generating charts or files.

Included metrics:

- Total, High, Medium, and Low priority leads.
- Average, highest, and lowest lead scores.
- Total and unique email addresses.
- Total and unique phone numbers.
- Contact links discovered.
- Evidence items collected.
- Top leads by score and priority.
- Most common business signals across organisations.

View the fictional dashboard demo with:

```bash
python -m src.lead_intelligence demo-dashboard
python -m tests.manual_dashboard_demo
```

## Project Status

Completed checkpoints:

- Static scraper
- Controlled multi-page crawler
- Rule-based business signal detection
- Transparent lead scoring
- Professional Excel export
- Management dashboard summary
- Central application configuration
- Structured application logging
- Controlled retry and request pacing
- Professional command-line interface
- Batch CSV organisation analysis
- Targeted Playwright fallback for JavaScript-rendered pages
- Docker packaging and smoke testing
- GitHub Actions continuous integration

Not implemented yet:

- External APIs or databases

## Planned Workflow

1. Read a list of target organisations.
2. Visit official organisation websites.
3. Discover relevant pages.
4. Extract public business contact information.
5. Detect infrastructure and energy-related signals.
6. Clean and deduplicate the records.
7. Calculate a transparent lead score.
8. Export the results to Excel.
9. Review combined reports and failure CSVs for follow-up research.

## Technologies

Current:

- Python
- Requests
- Beautiful Soup
- lxml
- OpenPyXL
- Playwright
- Pytest
- Git and GitHub

Planned for later checkpoints:

- Pandas

## Project Structure

```text
smart-infrastructure-lead-intelligence/
├── data/
├── reports/
├── screenshots/
├── src/
│   └── lead_intelligence/
├── tests/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
