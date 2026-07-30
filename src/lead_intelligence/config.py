from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


DEFAULT_REQUEST_TIMEOUT = 20.0
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
DEFAULT_MAX_PAGES_PER_SITE = 5
DEFAULT_USER_AGENT = "SmartInfrastructureLeadIntelligence/0.1"
DEFAULT_TOP_LEADS_LIMIT = 5
DEFAULT_OUTPUT_DIRECTORY = Path("data/output")
DEFAULT_LOG_LEVEL = "INFO"

VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration values."""

    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    max_pages_per_site: int = DEFAULT_MAX_PAGES_PER_SITE
    user_agent: str = DEFAULT_USER_AGENT
    top_leads_limit: int = DEFAULT_TOP_LEADS_LIMIT
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY
    log_level: str = DEFAULT_LOG_LEVEL


def parse_positive_float(
    value: str | None,
    default: float,
    variable_name: str,
    allow_zero: bool = False,
) -> float:
    """
    Parse a positive float from an environment variable value.

    Missing or blank values return the supplied default.
    """

    if value is None or not value.strip():
        return default

    stripped_value = value.strip()

    try:
        parsed_value = float(stripped_value)

    except ValueError as error:
        raise ValueError(
            f"{variable_name} must be a valid number."
        ) from error

    if not isfinite(parsed_value):
        raise ValueError(
            f"{variable_name} must be a finite number."
        )

    if allow_zero:
        if parsed_value < 0:
            raise ValueError(
                f"{variable_name} must be zero or greater."
            )
    elif parsed_value <= 0:
        raise ValueError(
            f"{variable_name} must be greater than zero."
        )

    return parsed_value


def parse_positive_int(
    value: str | None,
    default: int,
    variable_name: str,
) -> int:
    """
    Parse a positive integer from an environment variable value.

    Missing or blank values return the supplied default.
    """

    if value is None or not value.strip():
        return default

    stripped_value = value.strip()

    try:
        parsed_value = int(stripped_value)

    except ValueError as error:
        raise ValueError(
            f"{variable_name} must be a valid integer."
        ) from error

    if parsed_value < 1:
        raise ValueError(
            f"{variable_name} must be at least 1."
        )

    return parsed_value


def normalise_log_level(value: str | None) -> str:
    """
    Normalize and validate a log level value.

    Missing or blank values default to INFO.
    """

    if value is None or not value.strip():
        return DEFAULT_LOG_LEVEL

    log_level = value.strip().upper()

    if log_level not in VALID_LOG_LEVELS:
        allowed_values = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ValueError(
            f"LOG_LEVEL must be one of: {allowed_values}."
        )

    return log_level


def load_config(
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """
    Load application configuration from environment-style values.

    The supplied mapping is not mutated. When environ is None, os.environ is
    used.
    """

    environment = os.environ if environ is None else environ

    user_agent = environment.get(
        "USER_AGENT",
        DEFAULT_USER_AGENT,
    ).strip()

    if not user_agent:
        user_agent = DEFAULT_USER_AGENT

    if not user_agent:
        raise ValueError("USER_AGENT must not be blank.")

    output_directory_value = environment.get(
        "OUTPUT_DIRECTORY",
        str(DEFAULT_OUTPUT_DIRECTORY),
    ).strip()

    if not output_directory_value:
        output_directory_value = str(DEFAULT_OUTPUT_DIRECTORY)

    return AppConfig(
        request_timeout=parse_positive_float(
            value=environment.get("REQUEST_TIMEOUT"),
            default=DEFAULT_REQUEST_TIMEOUT,
            variable_name="REQUEST_TIMEOUT",
        ),
        request_delay_seconds=parse_positive_float(
            value=environment.get("REQUEST_DELAY_SECONDS"),
            default=DEFAULT_REQUEST_DELAY_SECONDS,
            variable_name="REQUEST_DELAY_SECONDS",
            allow_zero=True,
        ),
        max_pages_per_site=parse_positive_int(
            value=environment.get("MAX_PAGES_PER_SITE"),
            default=DEFAULT_MAX_PAGES_PER_SITE,
            variable_name="MAX_PAGES_PER_SITE",
        ),
        user_agent=user_agent,
        top_leads_limit=parse_positive_int(
            value=environment.get("TOP_LEADS_LIMIT"),
            default=DEFAULT_TOP_LEADS_LIMIT,
            variable_name="TOP_LEADS_LIMIT",
        ),
        output_directory=Path(output_directory_value),
        log_level=normalise_log_level(
            environment.get("LOG_LEVEL")
        ),
    )


def load_env_file(
    path: str | Path = ".env",
) -> dict[str, str]:
    """
    Read simple KEY=VALUE pairs from a .env-style file.

    The function does not modify os.environ.
    """

    env_path = Path(path)

    if not env_path.exists():
        return {}

    values: dict[str, str] = {}

    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            raise ValueError(
                f"Malformed .env line {line_number}: missing '='."
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError(
                f"Malformed .env line {line_number}: blank key."
            )

        values[key] = _strip_matching_quotes(value)

    return values


def load_config_with_env_file(
    path: str | Path = ".env",
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """
    Load configuration with .env-file values and environment overrides.

    Precedence is explicit/system environment, then .env file, then defaults.
    """

    merged_environment = load_env_file(path)
    environment = os.environ if environ is None else environ
    merged_environment.update(environment)

    return load_config(merged_environment)


def _strip_matching_quotes(value: str) -> str:
    """Remove matching single or double quotes around a full value."""

    if len(value) < 2:
        return value

    if value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    return value
