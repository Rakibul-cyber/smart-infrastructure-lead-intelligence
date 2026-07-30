# Screenshot Capture Guide

This folder is reserved for professional project screenshots. Capture images
manually after running the safe fictional demo commands below. Do not use real
organisation data, private contact data, access tokens, private paths, or
personal browser details in screenshots.

## Required Screenshots

### `cli-analysis.png`

- What it should show: A terminal running a single-organisation CLI analysis
  with a fictional or reserved-domain example. Show the command, the scraping
  mode or analysis heading, safe failure handling or page counts, and score or
  priority when available.
- Exact command:

  ```bash
  python -m src.lead_intelligence analyse \
    --website https://example.com \
    --name "Example Organisation" \
    --type Municipality \
    --city "Example City" \
    --state Hessen \
    --scrape-mode static \
    --no-export
  ```

- Recommended crop: Terminal content only, from the command through the result
  summary. Crop out personal terminal prompts and full local paths where
  practical.
- Must not be visible: Private contact values, real customer names, secrets,
  tokens, personal usernames, or unrelated shell history.
- Recommended filename: `cli-analysis.png`
- README caption: CLI analysis of a reserved-domain organisation.

### `dashboard.png`

- What it should show: The fictional management dashboard with lead overview,
  contact discovery, top leads, and most common signals.
- Exact command:

  ```bash
  python -m src.lead_intelligence demo-dashboard
  ```

- Recommended crop: Terminal output from the dashboard title through the most
  common signals section.
- Must not be visible: Personal terminal paths, private contacts, real
  organisations, or unrelated commands.
- Recommended filename: `dashboard.png`
- README caption: Management dashboard generated from fictional demo data.


### `excel-report.png`

- What it should show: The generated Excel workbook with a professional header
  row, several lead rows, and visible workbook tabs for `All Leads`,
  `High Priority`, `Evidence`, and `Run Summary`.
- Exact command:

  ```bash
  python -m src.lead_intelligence demo-export
  ```

- Location to open:

  ```text
  data/output/lead_intelligence_report.xlsx
  ```

- Recommended crop: Workbook grid plus sheet tabs, with enough rows to show the
  report structure.
- Must not be visible: Real organisation information, private contact values,
  unrelated desktop files, or personal account details.
- Recommended filename: `excel-report.png`
- README caption: Excel report workbook generated from fictional demo data.

### `github-actions.png`

- What it should show: The GitHub Actions `CI` workflow after both Python and
  Docker jobs pass. Include the green status, Python job, Docker job, and branch
  or commit context where useful.
- Location: The repository's GitHub Actions page for
  `.github/workflows/ci.yml`.
- Recommended crop: Workflow run summary and job list.
- Must not be visible: Irrelevant browser tabs, personal account details,
  private notifications, secrets, or unrelated repositories.
- Recommended filename: `github-actions.png`
- README caption: GitHub Actions CI run with Python and Docker jobs passing.

### `docker-demo.png`

- What it should show: Docker running the packaged CLI successfully.
- Exact commands:

  ```bash
  docker run --rm lead-intelligence version
  docker run --rm lead-intelligence demo-dashboard
  ```

- Recommended crop: Terminal output showing both Docker commands and successful
  CLI output.
- Must not be visible: Personal terminal paths, private shell history, secrets,
  tokens, or unrelated Docker output.
- Recommended filename: `docker-demo.png`
- README caption: Packaged CLI running successfully inside Docker.

## Capture Checklist

- [ ] `cli-analysis.png`
- [x] `dashboard.png`
- [ ] `excel-report.png`
- [ ] `github-actions.png`
- [ ] `docker-demo.png`

Run `scripts/prepare-screenshots.sh` from the repository root to create the
screenshot folder, generate the fictional Excel workbook, and print the commands
needed for manual capture.
