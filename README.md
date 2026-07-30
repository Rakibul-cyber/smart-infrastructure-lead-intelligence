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
- Offline Pytest coverage using deterministic HTML fixtures.

Business signal detection is intentionally simple and inspectable at this
stage. It uses explicit keyword categories and evidence excerpts rather than
machine learning or AI classification.

Lead scores support prioritisation for manual research. They are transparent
rules, not predictive AI, and do not replace human review.

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

## Project Status

Completed checkpoints:

- Static scraper
- Controlled multi-page crawler
- Rule-based business signal detection
- Transparent lead scoring
- Professional Excel export

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
