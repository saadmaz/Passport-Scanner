"""MRZ field normalization utilities."""

from __future__ import annotations

import os
from typing import Literal, Optional


def strip_filler(value: str) -> str:
    return value.replace("<", " ").strip()


def _century_threshold() -> int:
    return int(os.getenv("CENTURY_THRESHOLD", "30"))


def yymmdd_to_iso(yymmdd: str, is_expiry: bool = False) -> Optional[str]:
    """Convert YYMMDD to YYYY-MM-DD with century inference.

    - YY > threshold → 1900s
    - YY <= threshold → 2000s
    - is_expiry=True shifts the threshold: expiry dates are always in the future,
      so we lean toward 2000s more aggressively.
    """
    if not yymmdd or len(yymmdd) != 6 or not yymmdd.isdigit():
        return None
    yy, mm, dd = int(yymmdd[:2]), yymmdd[2:4], yymmdd[4:6]
    threshold = _century_threshold()
    if is_expiry:
        century = 2000
    else:
        century = 1900 if yy > threshold else 2000
    return f"{century + yy:04d}-{mm}-{dd}"


def detect_mrz_format(line1: str, line2: str) -> Literal["TD1", "TD2", "TD3"]:
    """Detect TD1/TD2/TD3 from line lengths."""
    l1, l2 = len(line1.rstrip()), len(line2.rstrip())
    if l1 == 30 and l2 == 30:
        return "TD1"
    if l1 == 36 and l2 == 36:
        return "TD2"
    return "TD3"


def parse_td3_names(name_field: str) -> tuple[str, str]:
    """Split TD3 name field (44 chars, positions 5-43 of line 1) into surname and given names."""
    parts = name_field.split("<<", 1)
    surname = strip_filler(parts[0]) if parts else ""
    given = strip_filler(parts[1]) if len(parts) > 1 else ""
    return surname, given
