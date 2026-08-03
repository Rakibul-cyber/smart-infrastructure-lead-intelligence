from __future__ import annotations

import os
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = 20.0
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
DEFAULT_MAX_PAGES_PER_SITE = 5
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
DEFAULT_USER_AGENT = "SmartInfrastructureLeadIntelligence/0.1"
DEFAULT_TOP_LEADS_LIMIT = 5
DEFAULT_OUTPUT_DIRECTORY = Path("data/output")
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE: Path | None = None
DEFAULT_SCRAPE_MODE = "static"
DEFAULT_BROWSER_HEADLESS = True
DEFAULT_BROWSER_TIMEOUT_SECONDS = 30.0
DEFAULT_BROWSER_WAIT_AFTER_LOAD_SECONDS = 0.0
DEFAULT_BROWSER_WAIT_FOR_SELECTOR: str | None = None
DEFAULT_BROWSER_ACCEPT_COOKIES = False
DEFAULT_BUSINESS_LINK_PRIORITY_ENABLED = True
DEFAULT_GENERAL_LINKS_ENABLED = True
MAX_BROWSER_SELECTOR_LENGTH = 500

VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

VALID_SCRAPE_MODES = {
    "static",
    "dynamic",
    "auto",
}

BOOLEAN_VALUES = {
    "true": True,
    "1": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "off": False,
}


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration values."""

    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    max_pages_per_site: int = DEFAULT_MAX_PAGES_PER_SITE
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS
    user_agent: str = DEFAULT_USER_AGENT
    top_leads_limit: int = DEFAULT_TOP_LEADS_LIMIT
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: Path | None = DEFAULT_LOG_FILE
    scrape_mode: str = DEFAULT_SCRAPE_MODE
    browser_headless: bool = DEFAULT_BROWSER_HEADLESS
    browser_timeout_seconds: float = DEFAULT_BROWSER_TIMEOUT_SECONDS
    browser_wait_after_load_seconds: float = (
        DEFAULT_BROWSER_WAIT_AFTER_LOAD_SECONDS
    )
    browser_wait_for_selector: str | None = DEFAULT_BROWSER_WAIT_FOR_SELECTOR
    browser_accept_cookies: bool = DEFAULT_BROWSER_ACCEPT_COOKIES
    business_link_priority_enabled: bool = (
        DEFAULT_BUSINESS_LINK_PRIORITY_ENABLED
    )
    general_links_enabled: bool = DEFAULT_GENERAL_LINKS_ENABLED


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


def parse_non_negative_int(
    value: str | None,
    default: int,
    variable_name: str,
) -> int:
    """
    Parse a zero-or-greater integer from an environment variable value.

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

    if parsed_value < 0:
        raise ValueError(
            f"{variable_name} must be zero or greater."
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


def parse_bool(
    value: str | None,
    default: bool,
    variable_name: str,
) -> bool:
    """Parse common environment-style boolean values."""

    if value is None or not value.strip():
        return default

    normalized_value = value.strip().casefold()

    if normalized_value not in BOOLEAN_VALUES:
        raise ValueError(
            f"{variable_name} must be one of: true, false, 1, 0, "
            "yes, no, on, off."
        )

    return BOOLEAN_VALUES[normalized_value]


def normalise_scrape_mode(value: str | None) -> str:
    """Normalize and validate scrape mode configuration."""

    if value is None or not value.strip():
        return DEFAULT_SCRAPE_MODE

    scrape_mode = value.strip().casefold()

    if scrape_mode not in VALID_SCRAPE_MODES:
        allowed_values = ", ".join(sorted(VALID_SCRAPE_MODES))
        raise ValueError(
            f"SCRAPE_MODE must be one of: {allowed_values}."
        )

    return scrape_mode


def normalise_optional_selector(value: str | None) -> str | None:
    """Normalize an optional CSS selector setting."""

    if value is None:
        return None

    selector = value.strip()

    if not selector:
        return None

    if len(selector) > MAX_BROWSER_SELECTOR_LENGTH:
        raise ValueError(
            "BROWSER_WAIT_FOR_SELECTOR must be "
            f"{MAX_BROWSER_SELECTOR_LENGTH} characters or fewer."
        )

    return selector


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

    log_file_value = environment.get(
        "LOG_FILE",
        "",
    ).strip()
    log_file = Path(log_file_value) if log_file_value else None

    logger.debug("Loading application configuration")

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
        max_retries=parse_non_negative_int(
            value=environment.get("MAX_RETRIES"),
            default=DEFAULT_MAX_RETRIES,
            variable_name="MAX_RETRIES",
        ),
        retry_backoff_seconds=parse_positive_float(
            value=environment.get("RETRY_BACKOFF_SECONDS"),
            default=DEFAULT_RETRY_BACKOFF_SECONDS,
            variable_name="RETRY_BACKOFF_SECONDS",
            allow_zero=True,
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
        log_file=log_file,
        scrape_mode=normalise_scrape_mode(
            environment.get("SCRAPE_MODE")
        ),
        browser_headless=parse_bool(
            value=environment.get("BROWSER_HEADLESS"),
            default=DEFAULT_BROWSER_HEADLESS,
            variable_name="BROWSER_HEADLESS",
        ),
        browser_timeout_seconds=parse_positive_float(
            value=environment.get("BROWSER_TIMEOUT_SECONDS"),
            default=DEFAULT_BROWSER_TIMEOUT_SECONDS,
            variable_name="BROWSER_TIMEOUT_SECONDS",
        ),
        browser_wait_after_load_seconds=parse_positive_float(
            value=environment.get("BROWSER_WAIT_AFTER_LOAD_SECONDS"),
            default=DEFAULT_BROWSER_WAIT_AFTER_LOAD_SECONDS,
            variable_name="BROWSER_WAIT_AFTER_LOAD_SECONDS",
            allow_zero=True,
        ),
        browser_wait_for_selector=normalise_optional_selector(
            environment.get("BROWSER_WAIT_FOR_SELECTOR")
        ),
        browser_accept_cookies=parse_bool(
            value=environment.get("BROWSER_ACCEPT_COOKIES"),
            default=DEFAULT_BROWSER_ACCEPT_COOKIES,
            variable_name="BROWSER_ACCEPT_COOKIES",
        ),
        business_link_priority_enabled=parse_bool(
            value=environment.get("BUSINESS_LINK_PRIORITY_ENABLED"),
            default=DEFAULT_BUSINESS_LINK_PRIORITY_ENABLED,
            variable_name="BUSINESS_LINK_PRIORITY_ENABLED",
        ),
        general_links_enabled=parse_bool(
            value=environment.get("GENERAL_LINKS_ENABLED"),
            default=DEFAULT_GENERAL_LINKS_ENABLED,
            variable_name="GENERAL_LINKS_ENABLED",
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
