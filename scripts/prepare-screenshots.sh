#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "README.md" || ! -d "src/lead_intelligence" ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

SCREENSHOT_DIR="docs/screenshots"
OUTPUT_DIR="data/output"
EXCEL_FILE="${OUTPUT_DIR}/lead_intelligence_report.xlsx"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Python was not found on PATH. Activate your environment and rerun." >&2
  exit 1
fi

mkdir -p "${SCREENSHOT_DIR}" "${OUTPUT_DIR}"

echo "Screenshot folder: ${SCREENSHOT_DIR}"
echo
echo "Use these filenames:"
echo "  ${SCREENSHOT_DIR}/cli-analysis.png"
echo "  ${SCREENSHOT_DIR}/dashboard.png"
echo "  ${SCREENSHOT_DIR}/excel-report.png"
echo "  ${SCREENSHOT_DIR}/github-actions.png"
echo "  ${SCREENSHOT_DIR}/docker-demo.png"
echo
echo "CLI analysis screenshot command:"
cat <<'COMMAND'
python -m src.lead_intelligence analyse \
  --website https://example.com \
  --name "Example Organisation" \
  --type Municipality \
  --city "Example City" \
  --state Hessen \
  --scrape-mode static \
  --no-export
COMMAND
echo

echo "Running safe fictional dashboard demo:"
"${PYTHON_BIN}" -m src.lead_intelligence demo-dashboard
echo

echo "Running safe fictional Excel export:"
"${PYTHON_BIN}" -m src.lead_intelligence demo-export
echo "Excel file: ${EXCEL_FILE}"
echo

echo "Docker screenshot commands:"
echo "  docker run --rm lead-intelligence version"
echo "  docker run --rm lead-intelligence demo-dashboard"

if command -v docker >/dev/null 2>&1 \
  && docker image inspect lead-intelligence >/dev/null 2>&1; then
  echo
  echo "Running Docker version command with the existing local image:"
  docker run --rm lead-intelligence version
else
  echo
  echo "Docker image 'lead-intelligence' was not found locally."
  echo "Build it first with: docker build -t lead-intelligence ."
fi

echo
echo "Capture GitHub Actions manually after the CI workflow is green."
