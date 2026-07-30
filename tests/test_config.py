from __future__ import annotations

from pathlib import Path

import pytest

from src.lead_intelligence.config import (
    AppConfig,
    load_config,
    load_config_with_env_file,
    load_env_file,
    normalise_log_level,
    normalise_scrape_mode,
    parse_bool,
    parse_non_negative_int,
    parse_positive_float,
    parse_positive_int,
)


def test_default_configuration_values() -> None:
    """Empty mappings should produce default configuration values."""

    config = load_config({})

    assert config == AppConfig()


def test_supplied_mapping_overrides_defaults() -> None:
    """Environment-style mappings should override defaults."""

    config = load_config(
        {
            "REQUEST_TIMEOUT": "12.5",
            "REQUEST_DELAY_SECONDS": "0",
            "MAX_PAGES_PER_SITE": "9",
            "MAX_RETRIES": "4",
            "RETRY_BACKOFF_SECONDS": "0.25",
            "USER_AGENT": "ExampleAgent/1.0",
            "TOP_LEADS_LIMIT": "7",
            "OUTPUT_DIRECTORY": "tmp/output",
            "LOG_LEVEL": "debug",
            "LOG_FILE": "logs/app.log",
            "SCRAPE_MODE": "auto",
            "BROWSER_HEADLESS": "false",
            "BROWSER_TIMEOUT_SECONDS": "42",
            "BROWSER_WAIT_AFTER_LOAD_SECONDS": "0.5",
            "BROWSER_WAIT_FOR_SELECTOR": " main.ready ",
            "BROWSER_ACCEPT_COOKIES": "yes",
        }
    )

    assert config.request_timeout == 12.5
    assert config.request_delay_seconds == 0
    assert config.max_pages_per_site == 9
    assert config.max_retries == 4
    assert config.retry_backoff_seconds == 0.25
    assert config.user_agent == "ExampleAgent/1.0"
    assert config.top_leads_limit == 7
    assert config.output_directory == Path("tmp/output")
    assert config.log_level == "DEBUG"
    assert config.log_file == Path("logs/app.log")
    assert config.scrape_mode == "auto"
    assert config.browser_headless is False
    assert config.browser_timeout_seconds == 42
    assert config.browser_wait_after_load_seconds == 0.5
    assert config.browser_wait_for_selector == "main.ready"
    assert config.browser_accept_cookies is True


def test_blank_values_use_defaults() -> None:
    """Blank variables should fall back to defaults."""

    config = load_config(
        {
            "REQUEST_TIMEOUT": " ",
            "REQUEST_DELAY_SECONDS": "\t",
            "MAX_PAGES_PER_SITE": "",
            "MAX_RETRIES": "",
            "RETRY_BACKOFF_SECONDS": " ",
            "USER_AGENT": " ",
            "TOP_LEADS_LIMIT": "",
            "OUTPUT_DIRECTORY": " ",
            "LOG_LEVEL": " ",
            "LOG_FILE": " ",
            "SCRAPE_MODE": " ",
            "BROWSER_HEADLESS": " ",
            "BROWSER_TIMEOUT_SECONDS": " ",
            "BROWSER_WAIT_AFTER_LOAD_SECONDS": " ",
            "BROWSER_WAIT_FOR_SELECTOR": " ",
            "BROWSER_ACCEPT_COOKIES": " ",
        }
    )

    assert config == AppConfig()


def test_valid_positive_integer_parsing() -> None:
    """Positive integer strings should parse."""

    assert parse_positive_int(" 3 ", 5, "MAX_PAGES_PER_SITE") == 3


@pytest.mark.parametrize("value", ["0", "-1"])
def test_zero_and_negative_integers_raise_value_error(
    value: str,
) -> None:
    """Positive integers must be at least one."""

    with pytest.raises(ValueError, match="MAX_PAGES_PER_SITE"):
        parse_positive_int(value, 5, "MAX_PAGES_PER_SITE")


def test_invalid_integer_text_raises_value_error() -> None:
    """Invalid integer text should raise a variable-specific error."""

    with pytest.raises(ValueError, match="TOP_LEADS_LIMIT"):
        parse_positive_int("five", 5, "TOP_LEADS_LIMIT")


def test_positive_float_parsing() -> None:
    """Positive float strings should parse."""

    assert parse_positive_float(" 2.5 ", 20.0, "REQUEST_TIMEOUT") == 2.5


def test_delay_allows_zero() -> None:
    """Delay parsing should allow zero when requested."""

    assert (
        parse_positive_float(
            "0",
            1.0,
            "REQUEST_DELAY_SECONDS",
            allow_zero=True,
        )
        == 0
    )


def test_negative_delay_raises_value_error() -> None:
    """Negative delay values should be rejected."""

    with pytest.raises(ValueError, match="REQUEST_DELAY_SECONDS"):
        parse_positive_float(
            "-0.1",
            1.0,
            "REQUEST_DELAY_SECONDS",
            allow_zero=True,
        )


def test_invalid_float_text_raises_value_error() -> None:
    """Invalid float text should raise a variable-specific error."""

    with pytest.raises(ValueError, match="REQUEST_TIMEOUT"):
        parse_positive_float("fast", 20.0, "REQUEST_TIMEOUT")


def test_log_levels_are_case_insensitive() -> None:
    """Supported log levels should normalize to uppercase."""

    assert normalise_log_level("debug") == "DEBUG"
    assert normalise_log_level(" Warning ") == "WARNING"


def test_invalid_log_level_raises_value_error() -> None:
    """Unsupported log levels should fail clearly."""

    with pytest.raises(ValueError, match="LOG_LEVEL"):
        normalise_log_level("verbose")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("FALSE", False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
        ("on", True),
        ("off", False),
    ],
)
def test_boolean_parsing(value: str, expected: bool) -> None:
    """Common boolean spellings should parse case-insensitively."""

    assert parse_bool(value, False, "BROWSER_HEADLESS") is expected


def test_invalid_boolean_raises_value_error() -> None:
    """Unsupported boolean values should fail clearly."""

    with pytest.raises(ValueError, match="BROWSER_HEADLESS"):
        parse_bool("maybe", True, "BROWSER_HEADLESS")


@pytest.mark.parametrize("value", ["static", "dynamic", "auto", " AUTO "])
def test_valid_scrape_modes(value: str) -> None:
    """Supported scrape modes should normalize to lowercase."""

    assert normalise_scrape_mode(value) in {"static", "dynamic", "auto"}


def test_invalid_scrape_mode_raises_value_error() -> None:
    """Unsupported scrape modes should fail clearly."""

    with pytest.raises(ValueError, match="SCRAPE_MODE"):
        normalise_scrape_mode("stealth")


def test_blank_browser_selector_becomes_none() -> None:
    """Blank selector config should be treated as unset."""

    config = load_config({"BROWSER_WAIT_FOR_SELECTOR": " "})

    assert config.browser_wait_for_selector is None


def test_long_browser_selector_raises_value_error() -> None:
    """Overlong browser selector config should be rejected."""

    with pytest.raises(ValueError, match="BROWSER_WAIT_FOR_SELECTOR"):
        load_config({"BROWSER_WAIT_FOR_SELECTOR": "." + ("x" * 501)})


def test_output_directory_becomes_path() -> None:
    """OUTPUT_DIRECTORY should be represented as pathlib.Path."""

    config = load_config({"OUTPUT_DIRECTORY": "data/custom"})

    assert config.output_directory == Path("data/custom")


def test_load_config_does_not_mutate_supplied_mapping() -> None:
    """load_config should not change the mapping supplied by tests or callers."""

    environment = {"REQUEST_TIMEOUT": "3"}
    original_environment = dict(environment)

    load_config(environment)

    assert environment == original_environment


def test_env_file_missing_returns_empty_dict(tmp_path: Path) -> None:
    """Missing .env files should be optional."""

    assert load_env_file(tmp_path / ".env") == {}


def test_env_file_parses_comments_and_blank_lines(tmp_path: Path) -> None:
    """Comments and blank lines should be ignored."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n# comment\nREQUEST_TIMEOUT=10\n\n",
        encoding="utf-8",
    )

    assert load_env_file(env_path) == {"REQUEST_TIMEOUT": "10"}


def test_env_file_handles_optional_export_prefix(tmp_path: Path) -> None:
    """A leading export prefix should be ignored."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "export MAX_PAGES_PER_SITE=4\n",
        encoding="utf-8",
    )

    assert load_env_file(env_path) == {"MAX_PAGES_PER_SITE": "4"}


def test_env_file_removes_matching_quotes(tmp_path: Path) -> None:
    """Matching full-value quotes should be stripped."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "USER_AGENT='QuotedAgent/1.0'\nLOG_LEVEL=\"warning\"\n",
        encoding="utf-8",
    )

    assert load_env_file(env_path) == {
        "USER_AGENT": "QuotedAgent/1.0",
        "LOG_LEVEL": "warning",
    }


def test_env_file_allows_empty_values(tmp_path: Path) -> None:
    """Empty env-file values should be preserved by the parser."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "USER_AGENT=\n",
        encoding="utf-8",
    )

    assert load_env_file(env_path) == {"USER_AGENT": ""}


def test_malformed_line_raises_value_error(tmp_path: Path) -> None:
    """Non-comment lines need a KEY=VALUE separator."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "REQUEST_TIMEOUT\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 1"):
        load_env_file(env_path)


def test_blank_key_raises_value_error(tmp_path: Path) -> None:
    """Blank keys should be rejected."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        " =value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="blank key"):
        load_env_file(env_path)


def test_explicit_environment_overrides_env_file_values(
    tmp_path: Path,
) -> None:
    """Runtime environment values should win over .env values."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "MAX_PAGES_PER_SITE=3\n",
        encoding="utf-8",
    )

    config = load_config_with_env_file(
        path=env_path,
        environ={"MAX_PAGES_PER_SITE": "8"},
    )

    assert config.max_pages_per_site == 8


def test_env_file_values_override_defaults(tmp_path: Path) -> None:
    """Env-file values should be used when explicit environment is absent."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "REQUEST_TIMEOUT=11\n",
        encoding="utf-8",
    )

    config = load_config_with_env_file(
        path=env_path,
        environ={},
    )

    assert config.request_timeout == 11


def test_load_config_with_env_file_does_not_mutate_supplied_mapping(
    tmp_path: Path,
) -> None:
    """Merged config loading should not mutate caller mappings."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "REQUEST_TIMEOUT=11\n",
        encoding="utf-8",
    )
    environment = {"REQUEST_TIMEOUT": "12"}
    original_environment = dict(environment)

    load_config_with_env_file(
        path=env_path,
        environ=environment,
    )

    assert environment == original_environment


def test_new_app_config_is_returned_each_time() -> None:
    """Loading config should create a fresh dataclass instance."""

    first_config = load_config({})
    second_config = load_config({})

    assert first_config == second_config
    assert first_config is not second_config


def test_default_max_retries() -> None:
    """MAX_RETRIES should default to two."""

    assert load_config({}).max_retries == 2


def test_default_retry_backoff_seconds() -> None:
    """RETRY_BACKOFF_SECONDS should default to one second."""

    assert load_config({}).retry_backoff_seconds == 1.0


def test_max_retries_zero_is_valid() -> None:
    """MAX_RETRIES may be zero."""

    assert parse_non_negative_int("0", 2, "MAX_RETRIES") == 0
    assert load_config({"MAX_RETRIES": "0"}).max_retries == 0


def test_negative_retries_raise_value_error() -> None:
    """Negative retry counts should be rejected."""

    with pytest.raises(ValueError, match="MAX_RETRIES"):
        parse_non_negative_int("-1", 2, "MAX_RETRIES")


def test_invalid_retry_integer_raises_value_error() -> None:
    """Invalid retry integer text should fail clearly."""

    with pytest.raises(ValueError, match="MAX_RETRIES"):
        parse_non_negative_int("two", 2, "MAX_RETRIES")


def test_zero_retry_backoff_is_valid() -> None:
    """RETRY_BACKOFF_SECONDS may be zero."""

    assert (
        load_config({"RETRY_BACKOFF_SECONDS": "0"}).retry_backoff_seconds
        == 0
    )


def test_negative_backoff_raises_value_error() -> None:
    """Negative retry backoff should be rejected."""

    with pytest.raises(ValueError, match="RETRY_BACKOFF_SECONDS"):
        load_config({"RETRY_BACKOFF_SECONDS": "-1"})


def test_explicit_retry_environment_values_override_env_file_values(
    tmp_path: Path,
) -> None:
    """Explicit retry config should override env-file retry config."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "MAX_RETRIES=1\nRETRY_BACKOFF_SECONDS=3\n",
        encoding="utf-8",
    )

    config = load_config_with_env_file(
        path=env_path,
        environ={
            "MAX_RETRIES": "5",
            "RETRY_BACKOFF_SECONDS": "0.5",
        },
    )

    assert config.max_retries == 5
    assert config.retry_backoff_seconds == 0.5


def test_default_log_file_is_none() -> None:
    """LOG_FILE should default to None."""

    assert load_config({}).log_file is None


def test_blank_log_file_produces_none() -> None:
    """Blank LOG_FILE values should produce None."""

    assert load_config({"LOG_FILE": " "}).log_file is None


def test_configured_log_file_becomes_path() -> None:
    """LOG_FILE should become a pathlib.Path when configured."""

    config = load_config({"LOG_FILE": "logs/app.log"})

    assert config.log_file == Path("logs/app.log")


def test_env_file_log_file_works(tmp_path: Path) -> None:
    """LOG_FILE should load from an env file."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "LOG_FILE=logs/file.log\n",
        encoding="utf-8",
    )

    config = load_config_with_env_file(
        path=env_path,
        environ={},
    )

    assert config.log_file == Path("logs/file.log")


def test_explicit_environment_log_file_overrides_file_value(
    tmp_path: Path,
) -> None:
    """Explicit LOG_FILE should override an env-file LOG_FILE."""

    env_path = tmp_path / ".env"
    env_path.write_text(
        "LOG_FILE=logs/file.log\n",
        encoding="utf-8",
    )

    config = load_config_with_env_file(
        path=env_path,
        environ={"LOG_FILE": "logs/runtime.log"},
    )

    assert config.log_file == Path("logs/runtime.log")
