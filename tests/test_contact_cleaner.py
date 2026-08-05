from __future__ import annotations

from src.lead_intelligence.contact_cleaner import (
    normalise_phone_candidate,
    validate_phone_candidate,
)


def test_german_domestic_number_normalises() -> None:
    """German domestic numbers should become +49 canonical values."""

    assert normalise_phone_candidate("030 1234 5678") == "+493012345678"


def test_0049_number_normalises() -> None:
    """German 0049 international prefix should become +49."""

    assert normalise_phone_candidate("0049 30 123456") == "+4930123456"


def test_plus_49_optional_trunk_prefix_normalises() -> None:
    """The common +49 (0) form should remove the optional trunk prefix."""

    assert normalise_phone_candidate("+49 (0) 30 123456") == "+4930123456"


def test_tel_value_normalises() -> None:
    """tel: values should normalise like visible text values."""

    assert normalise_phone_candidate("tel:+49-30-123456") == "+4930123456"


def test_duplicate_formats_collapse_to_one_normalised_value() -> None:
    """Different formats for one number should share one canonical value."""

    values = {
        validate_phone_candidate("030 123456").normalised,
        validate_phone_candidate("0049 30 123456").normalised,
        validate_phone_candidate("+49 (0) 30 123456").normalised,
    }

    assert values == {"+4930123456"}


def test_date_rejected() -> None:
    """Date-like values should be invalid."""

    result = validate_phone_candidate("30.07.2026")

    assert result.valid is False
    assert result.reason == "looks like a date or year"


def test_year_rejected() -> None:
    """Standalone years should be invalid."""

    result = validate_phone_candidate("2026")

    assert result.valid is False
    assert result.reason == "looks like a date or year"


def test_postcode_rejected() -> None:
    """Short postal-code-like values should be invalid."""

    result = validate_phone_candidate("06421")

    assert result.valid is False
    assert result.reason == "too short"


def test_percentage_rejected() -> None:
    """Percentages should be invalid."""

    result = validate_phone_candidate("0.75%")

    assert result.valid is False
    assert result.reason == "looks like a percentage"


def test_repeated_digits_rejected() -> None:
    """Repeated single-digit values should be invalid."""

    result = validate_phone_candidate("00000000")

    assert result.valid is False
    assert result.reason == "repeated single digit"


def test_too_short_rejected() -> None:
    """Very short values should be invalid."""

    result = validate_phone_candidate("030 12")

    assert result.valid is False
    assert result.reason == "too short"


def test_too_long_rejected() -> None:
    """Overlong values should be invalid."""

    result = validate_phone_candidate("+49 1234567890123456")

    assert result.valid is False
    assert result.reason == "too long"


def test_letters_rejected() -> None:
    """Phone candidates containing letters should be invalid."""

    result = validate_phone_candidate("030 CALL 123")

    assert result.valid is False
    assert result.reason == "contains letters"


def test_valid_international_format_accepted() -> None:
    """Explicit plausible international numbers may be accepted."""

    result = validate_phone_candidate("+44 20 7946 0958")

    assert result.valid is True
    assert result.normalised == "+442079460958"


def test_reason_is_populated_for_invalid_values() -> None:
    """Invalid values should explain why they were rejected."""

    result = validate_phone_candidate("")

    assert result.valid is False
    assert result.reason == "blank value"
