from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_project_file(path: str) -> str:
    """Read a repository file as UTF-8 text."""

    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_workflow_exists() -> None:
    """CI workflow should be present."""

    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()


def test_ci_workflow_triggers_on_push_and_pull_request() -> None:
    """CI should run for main-branch pushes and pull requests."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "on:" in workflow
    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "branches: [main]" in workflow


def test_ci_permissions_are_read_only() -> None:
    """Workflow permissions should stay minimal."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow


def test_ci_uses_python_312() -> None:
    """CI should configure Python 3.12."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert 'python-version: "3.12"' in workflow


def test_ci_runs_pytest_and_compileall() -> None:
    """CI should run the normal test suite and compilation check."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "python -m pytest -v" in workflow
    assert "python -m compileall src tests" in workflow


def test_ci_installs_playwright_chromium() -> None:
    """CI should install Chromium and Linux dependencies for Playwright."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "python -m playwright install --with-deps chromium" in workflow


def test_ci_uploads_fictional_excel_artifact() -> None:
    """CI should upload only generated fictional Excel output."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "actions/upload-artifact@v4" in workflow
    assert "name: fictional-excel-demo" in workflow
    assert "path: data/output/*.xlsx" in workflow
    assert "if-no-files-found: error" in workflow


def test_ci_builds_docker_runtime_image() -> None:
    """Docker job should build the runtime image."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "docker build -t lead-intelligence ." in workflow


def test_ci_builds_docker_test_target() -> None:
    """Docker job should build the test target."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "docker build --target test -t lead-intelligence-test ." in workflow


def test_ci_validates_docker_compose() -> None:
    """Docker job should validate Compose syntax."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "docker compose config" in workflow


def test_ci_does_not_push_container_images() -> None:
    """CI should not publish Docker images."""

    workflow = read_project_file(".github/workflows/ci.yml")

    assert "docker push" not in workflow
    assert "--push" not in workflow
    assert "push: true" not in workflow


def test_dependabot_configuration_exists() -> None:
    """Dependabot configuration should be present."""

    assert (ROOT / ".github" / "dependabot.yml").is_file()


def test_dependabot_includes_requested_ecosystems() -> None:
    """Dependabot should check pip, actions, and Docker dependencies."""

    dependabot = read_project_file(".github/dependabot.yml")

    assert 'package-ecosystem: "pip"' in dependabot
    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'package-ecosystem: "docker"' in dependabot
    assert 'interval: "weekly"' in dependabot
    assert 'day: "monday"' in dependabot
    assert "open-pull-requests-limit: 5" in dependabot


def test_readme_contains_ci_badge() -> None:
    """README should show the CI badge."""

    readme = read_project_file("README.md")

    assert (
        "[![CI](https://github.com/Rakibul-cyber/"
        "smart-infrastructure-lead-intelligence/actions/workflows/ci.yml/"
        "badge.svg)](https://github.com/Rakibul-cyber/"
        "smart-infrastructure-lead-intelligence/actions/workflows/ci.yml)"
    ) in readme
