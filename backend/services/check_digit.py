"""ICAO 9303 Part 3 check digit calculation and validation."""

from __future__ import annotations

MRZ_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<"
WEIGHTS = [7, 3, 1]


def _char_value(ch: str) -> int:
    ch = ch.upper()
    if ch.isdigit():
        return int(ch)
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    if ch == "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {ch!r}")


def compute_check_digit(field: str) -> int:
    """Return the ICAO 9303 check digit (0-9) for *field*."""
    total = sum(_char_value(ch) * WEIGHTS[i % 3] for i, ch in enumerate(field))
    return total % 10


def validate_check_digit(field: str, expected: str) -> bool:
    try:
        return compute_check_digit(field) == int(expected)
    except (ValueError, TypeError):
        return False


def validate_td3(line1: str, line2: str) -> dict[str, bool]:
    """Validate all four TD3 check digits; return per-field pass/fail."""
    results: dict[str, bool] = {
        "passport_number": False,
        "date_of_birth": False,
        "date_of_expiry": False,
        "composite": False,
    }
    if len(line2) < 44:
        return results

    # Passport number: line2[0:9], check at line2[9]
    results["passport_number"] = validate_check_digit(line2[0:9], line2[9])
    # Date of birth: line2[13:19], check at line2[19]
    results["date_of_birth"] = validate_check_digit(line2[13:19], line2[19])
    # Date of expiry: line2[21:27], check at line2[27]
    results["date_of_expiry"] = validate_check_digit(line2[21:27], line2[27])
    # Composite: line2[0:10] + line2[13:20] + line2[21:43], check at line2[43]
    composite_field = line2[0:10] + line2[13:20] + line2[21:43]
    results["composite"] = validate_check_digit(composite_field, line2[43])
    return results
