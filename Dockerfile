FROM mcr.microsoft.com/playwright/python:v1.61.0-noble AS app-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY README.md pytest.ini ./
COPY Dockerfile .dockerignore docker-compose.yml ./
COPY scripts ./scripts
COPY data/input/organisations.example.csv ./data/input/organisations.example.csv

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data/output /app/logs /app/.pytest_cache \
    && chmod +x /app/scripts/docker-smoke-test.sh \
    && chown -R appuser:appuser /app/data/output /app/logs /app/.pytest_cache

USER appuser

FROM app-base AS test
COPY --chown=appuser:appuser .github ./.github
ENTRYPOINT ["python", "-m", "pytest", "-v"]
CMD []

FROM app-base AS runtime
ENTRYPOINT ["python", "-m", "src.lead_intelligence"]
CMD ["--help"]
