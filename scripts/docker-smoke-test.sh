#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-lead-intelligence:smoke}"
TEMP_OUTPUT_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TEMP_OUTPUT_DIR}"
}

trap cleanup EXIT

docker build -t "${IMAGE_NAME}" .
docker run --rm "${IMAGE_NAME}" version
docker run --rm "${IMAGE_NAME}" demo-dashboard
docker run --rm \
  -v "${TEMP_OUTPUT_DIR}:/app/data/output" \
  "${IMAGE_NAME}" demo-export

if ! find "${TEMP_OUTPUT_DIR}" -maxdepth 1 -type f -name "*.xlsx" | grep -q .; then
  echo "Expected demo-export to generate an .xlsx file" >&2
  exit 1
fi

echo "Docker smoke test passed."
