# Smart Infrastructure Lead Intelligence

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
- Central application configuration with environment-variable and optional
  `.env` file support.
- Structured console logging with optional UTF-8 file logging.
- Controlled retry logic and respectful request pacing for public webpages.
- Offline Pytest coverage using deterministic HTML fixtures.

Business signal detection is intentionally simple and inspectable at this
stage. It uses explicit keyword categories and evidence excerpts rather than
machine learning or AI classification.

Lead scores support prioritisation for manual research. They are transparent
rules, not predictive AI, and do not replace human review.

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

Not implemented yet:

- Dynamic website automation
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
9. Demonstrate dynamic website automation with Playwright.

## Technologies

Current:

- Python
- Requests
- Beautiful Soup
- lxml
- OpenPyXL
- Pytest
- Git and GitHub

Planned for later checkpoints:

- Pandas
- Playwright

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
