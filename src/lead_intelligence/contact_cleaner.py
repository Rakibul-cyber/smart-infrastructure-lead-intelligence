from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CleanedPhoneNumber:
    """Validation result for one raw phone-number candidate."""

    raw: str
    normalised: str
    country_code: str
    valid: bool
    reason: str | None


DATE_PATTERNS = (
    re.compile(r"\b20\d{2}\b"),
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]20\d{2}\b"),
    re.compile(r"\b20\d{2}-\d{1,2}-\d{1,2}\b"),
)


def normalise_phone_candidate(value: str) -> str:
    """
    Return a canonical phone value.

    German domestic numbers are converted to +49 followed by the national
    number without the leading zero.
    """

    stripped_value = value.strip().replace("\u00a0", " ")
    stripped_value = re.sub(r"\s+", " ", stripped_value)
    stripped_value = re.sub(r"^\s*tel:\s*", "", stripped_value, flags=re.I)
    stripped_value = stripped_value.replace("(0)", "")
    stripped_value = re.sub(r"[\s()/\-.]", "", stripped_value)

    if stripped_value.startswith("0049"):
        return "+49" + stripped_value[4:]

    if stripped_value.startswith("+490"):
        return "+49" + stripped_value[4:]

    if stripped_value.startswith("+49"):
        return stripped_value

    if stripped_value.startswith("0"):
        return "+49" + stripped_value[1:]

    return stripped_value


def validate_phone_candidate(
    value: str,
) -> CleanedPhoneNumber:
    """Validate and normalise a German-focused phone-number candidate."""

    raw = value.strip().replace("\u00a0", " ")
    normalised = normalise_phone_candidate(raw)
    digits = re.sub(r"\D", "", normalised)
    country_code = _country_code(normalised)

    invalid_reason = _invalid_reason(
        raw=raw,
        normalised=normalised,
        digits=digits,
    )

    if invalid_reason is not None:
        return CleanedPhoneNumber(
            raw=value,
            normalised=normalised,
            country_code=country_code,
            valid=False,
            reason=invalid_reason,
        )

    return CleanedPhoneNumber(
        raw=value,
        normalised=normalised,
        country_code=country_code,
        valid=True,
        reason=None,
    )


def _invalid_reason(
    *,
    raw: str,
    normalised: str,
    digits: str,
) -> str | None:
    if not raw:
        return "blank value"

    if re.search(r"[A-Za-z]", raw):
        return "contains letters"

    if any(pattern.search(raw) for pattern in DATE_PATTERNS):
        return "looks like a date or year"

    if "%" in raw:
        return "looks like a percentage"

    if _looks_like_decimal(raw):
        return "looks like a decimal value"

    if len(digits) < 7:
        return "too short"

    if len(digits) > 15:
        return "too long"

    significant_digits = _significant_digits(normalised, digits)

    if significant_digits and len(set(significant_digits)) == 1:
        return "repeated single digit"

    if len(digits) <= 5:
        return "too short for a phone number"

    if not (
        normalised.startswith("+")
        or normalised.startswith("0049")
        or normalised.startswith("0")
    ):
        return "missing plausible phone prefix"

    return None


def _looks_like_decimal(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[+-]?\d{1,3}(?:[.,]\d{1,3})",
            value.strip(),
        )
    )


def _country_code(normalised: str) -> str:
    if normalised.startswith("+49"):
        return "49"

    if normalised.startswith("+"):
        match = re.match(r"\+(\d{1,3})", normalised)

        if match:
            return match.group(1)

    if normalised.startswith("0049"):
        return "49"

    return ""


def _significant_digits(normalised: str, digits: str) -> str:
    if normalised.startswith("+49") and digits.startswith("49"):
        return digits[2:]

    if normalised.startswith("0049") and digits.startswith("0049"):
        return digits[4:]

    return digits
