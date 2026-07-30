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


def test_smoke_test_uses_temporary_docker_volume() -> None:
    """Smoke test should use a temporary Docker volume for Excel output."""

    script = read_project_file("scripts/docker-smoke-test.sh")

    assert 'VOLUME_NAME="lead-intelligence-smoke-${RANDOM}-$$"' in script
    assert 'docker volume create "${VOLUME_NAME}"' in script
    assert '-v "${VOLUME_NAME}:/app/data/output"' in script


def test_smoke_test_cleans_up_temporary_docker_volume() -> None:
    """Smoke test should remove the temporary Docker volume on exit."""

    script = read_project_file("scripts/docker-smoke-test.sh")

    assert 'docker volume rm -f "${VOLUME_NAME}"' in script
    assert "trap cleanup EXIT" in script


def test_smoke_test_initialises_volume_permissions_with_root() -> None:
    """Smoke test may use root only to prepare volume ownership."""

    script = read_project_file("scripts/docker-smoke-test.sh")

    assert "--user root" in script
    assert "chown -R appuser:appuser /app/data/output" in script


def test_smoke_test_runs_demo_export_as_image_user() -> None:
    """demo-export should run as the Dockerfile's non-root user."""

    script = read_project_file("scripts/docker-smoke-test.sh")
    demo_export_index = script.index('"${IMAGE_NAME}" demo-export')
    run_index = script.rfind("docker run --rm", 0, demo_export_index)
    demo_export_block = script[run_index:demo_export_index]

    assert "--user root" not in demo_export_block
    assert "-u root" not in demo_export_block
    assert "--privileged" not in script


def test_smoke_test_verifies_xlsx_inside_volume() -> None:
    """Smoke test should verify an Excel workbook inside the volume."""

    script = read_project_file("scripts/docker-smoke-test.sh")

    assert '-v "${VOLUME_NAME}:/app/data/output:ro"' in script
    assert 'find /app/data/output -maxdepth 1 -type f -name "*.xlsx"' in script
    assert "grep -q ." in script
