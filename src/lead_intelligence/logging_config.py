from __future__ import annotations

import logging
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}
MANAGED_HANDLER_MARKER = "_lead_intelligence_managed_handler"


def configure_logging(
    log_level: str = "INFO",
    log_file: str | Path | None = None,
) -> None:
    """
    Configure structured application logging.

    Handlers created by this function are marked and replaced on repeated
    calls. Unrelated handlers are preserved where possible.
    """

    normalized_level = log_level.strip().upper()

    if normalized_level not in VALID_LOG_LEVELS:
        allowed_values = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ValueError(
            f"log_level must be one of: {allowed_values}."
        )

    level = logging.getLevelName(normalized_level)
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )
    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        if getattr(handler, MANAGED_HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    setattr(console_handler, MANAGED_HANDLER_MARKER, True)
    root_logger.addHandler(console_handler)

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        file_handler = logging.FileHandler(
            log_path,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        setattr(file_handler, MANAGED_HANDLER_MARKER, True)
        root_logger.addHandler(file_handler)

    root_logger.setLevel(level)
