from __future__ import annotations

import os
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_project_file(path: str) -> str:
    """Read a repository file as UTF-8 text."""

    return (ROOT / path).read_text(encoding="utf-8")


def test_dockerfile_exists() -> None:
    """Dockerfile should be present."""

    assert (ROOT / "Dockerfile").is_file()


def test_dockerfile_uses_pinned_playwright_image() -> None:
    """Dockerfile should use the requested pinned Playwright base image."""

    dockerfile = read_project_file("Dockerfile")

    assert "mcr.microsoft.com/playwright/python:v1.61.0-noble" in dockerfile


def test_dockerfile_runs_as_non_root_user() -> None:
    """Dockerfile should create and switch to a non-root user."""

    dockerfile = read_project_file("Dockerfile")

    assert "useradd" in dockerfile
    assert "USER appuser" in dockerfile


def test_dockerfile_configures_package_cli_entrypoint() -> None:
    """Docker runtime should execute the package CLI."""

    dockerfile = read_project_file("Dockerfile")

    assert 'ENTRYPOINT ["python", "-m", "src.lead_intelligence"]' in dockerfile
    assert 'CMD ["--help"]' in dockerfile


def test_dockerignore_excludes_env_and_venv() -> None:
    """Docker context should exclude local env files and virtualenvs."""

    dockerignore = read_project_file(".dockerignore").splitlines()

    assert ".env" in dockerignore
    assert ".venv" in dockerignore


def test_compose_has_no_ports() -> None:
    """Compose service should not expose ports."""

    compose = read_project_file("docker-compose.yml")

    assert "ports:" not in compose


def test_compose_input_mount_is_read_only() -> None:
    """Input mount should be read-only."""

    compose = read_project_file("docker-compose.yml")

    assert "./data/input:/app/data/input:ro" in compose


def test_compose_output_mount_is_writable() -> None:
    """Output mount should not be read-only."""

    compose = read_project_file("docker-compose.yml")

    assert "./data/output:/app/data/output" in compose
    assert "./data/output:/app/data/output:ro" not in compose


def test_compose_init_is_true() -> None:
    """Compose service should enable init."""

    compose = read_project_file("docker-compose.yml")

    assert "init: true" in compose


def test_smoke_test_script_exists_and_is_executable() -> None:
    """Docker smoke script should exist and be executable."""

    script = ROOT / "scripts" / "docker-smoke-test.sh"
    mode = script.stat().st_mode

    assert script.is_file()
    assert mode & stat.S_IXUSR
    assert os.access(script, os.X_OK)
