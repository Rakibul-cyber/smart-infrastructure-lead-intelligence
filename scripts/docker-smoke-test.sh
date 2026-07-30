#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-lead-intelligence:smoke}"
VOLUME_NAME="lead-intelligence-smoke-${RANDOM}-$$"

cleanup() {
  docker volume rm -f "${VOLUME_NAME}" >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker build -t "${IMAGE_NAME}" .
docker run --rm "${IMAGE_NAME}" version
docker run --rm "${IMAGE_NAME}" demo-dashboard
docker volume create "${VOLUME_NAME}" >/dev/null
docker run --rm \
  --user root \
  -v "${VOLUME_NAME}:/app/data/output" \
  --entrypoint /bin/sh \
  "${IMAGE_NAME}" \
  -c 'chown -R appuser:appuser /app/data/output'
docker run --rm \
  -v "${VOLUME_NAME}:/app/data/output" \
  "${IMAGE_NAME}" demo-export
docker run --rm \
  -v "${VOLUME_NAME}:/app/data/output:ro" \
  --entrypoint /bin/sh \
  "${IMAGE_NAME}" \
  -c 'find /app/data/output -maxdepth 1 -type f -name "*.xlsx" | grep -q .'

echo "Docker smoke test passed."
