from __future__ import annotations

import io
import logging
import re
import sys
from pathlib import Path

import pytest

from src.lead_intelligence.logging_config import (
    MANAGED_HANDLER_MARKER,
    configure_logging,
)


@pytest.fixture(autouse=True)
def restore_root_logger_state():
    """Restore root logger handlers and level after each test."""

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    yield

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    for handler in original_handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(original_level)


def managed_handlers() -> list[logging.Handler]:
    """Return handlers managed by configure_logging."""

    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, MANAGED_HANDLER_MARKER, False)
    ]


def managed_console_handlers() -> list[logging.Handler]:
    """Return managed console handlers."""

    return [
        handler
        for handler in managed_handlers()
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
    ]


def managed_file_handlers() -> list[logging.FileHandler]:
    """Return managed file handlers."""

    return [
        handler
        for handler in managed_handlers()
        if isinstance(handler, logging.FileHandler)
    ]


@pytest.mark.parametrize(
    "level",
    ["debug", "INFO", "Warning", "error", "CRITICAL"],
)
def test_valid_levels_are_accepted_case_insensitively(
    level: str,
) -> None:
    """Supported log levels should configure successfully."""

    configure_logging(level)

    assert logging.getLogger().level == logging.getLevelName(
        level.strip().upper()
    )


def test_invalid_level_raises_value_error() -> None:
    """Unsupported log levels should fail clearly."""

    with pytest.raises(ValueError):
        configure_logging("verbose")


def test_one_console_handler_is_added() -> None:
    """A single managed console handler should be configured."""

    configure_logging("INFO")

    assert len(managed_console_handlers()) == 1


def test_repeated_calls_do_not_duplicate_managed_handlers() -> None:
    """Repeated configuration should replace managed handlers."""

    configure_logging("INFO")
    configure_logging("INFO")

    assert len(managed_console_handlers()) == 1
    assert len(managed_handlers()) == 1


def test_reconfiguration_changes_level() -> None:
    """Reconfiguring should update root and handler levels."""

    configure_logging("INFO")
    configure_logging("DEBUG")

    assert logging.getLogger().level == logging.DEBUG
    assert all(
        handler.level == logging.DEBUG
        for handler in managed_handlers()
    )


def test_log_messages_use_expected_format(monkeypatch) -> None:
    """Console messages should use the structured formatter."""

    stream = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stream)
    configure_logging("INFO")

    logging.getLogger("example.logger").info("hello")

    output = stream.getvalue().strip()

    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} "
        r"\| INFO \| example\.logger \| hello",
        output,
    )


def test_file_handler_is_created_when_requested(tmp_path: Path) -> None:
    """A managed file handler should be added when log_file is provided."""

    configure_logging(
        "INFO",
        log_file=tmp_path / "app.log",
    )

    assert len(managed_file_handlers()) == 1


def test_parent_directory_for_log_file_is_created(
    tmp_path: Path,
) -> None:
    """Log-file parent directories should be created automatically."""

    log_file = tmp_path / "nested" / "logs" / "app.log"

    configure_logging(
        "INFO",
        log_file=log_file,
    )

    assert log_file.parent.exists()


def test_file_receives_utf8_log_content(tmp_path: Path) -> None:
    """File logging should write UTF-8 content."""

    log_file = tmp_path / "app.log"
    configure_logging(
        "INFO",
        log_file=log_file,
    )

    logging.getLogger("example.file").info("café")

    for handler in managed_handlers():
        handler.flush()

    assert "café" in log_file.read_text(encoding="utf-8")


def test_calling_without_file_removes_previous_managed_file_handler(
    tmp_path: Path,
) -> None:
    """Reconfiguring without a file should remove prior managed file handlers."""

    configure_logging(
        "INFO",
        log_file=tmp_path / "app.log",
    )
    configure_logging("INFO")

    assert managed_file_handlers() == []
    assert len(managed_console_handlers()) == 1


def test_unrelated_external_handler_is_not_removed() -> None:
    """Unmanaged handlers should be preserved."""

    external_handler = logging.StreamHandler(io.StringIO())
    root_logger = logging.getLogger()
    root_logger.addHandler(external_handler)

    configure_logging("INFO")

    assert external_handler in root_logger.handlers


def test_handler_levels_match_configured_level(tmp_path: Path) -> None:
    """Managed handler levels should match the configured level."""

    configure_logging(
        "ERROR",
        log_file=tmp_path / "app.log",
    )

    assert all(
        handler.level == logging.ERROR
        for handler in managed_handlers()
    )
