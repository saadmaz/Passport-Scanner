"""Tesseract + mrz library fallback OCR for passport MRZ."""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from backend.models.passport import PassportData
from backend.services.normalizer import detect_mrz_format, parse_td3_names, yymmdd_to_iso, strip_filler


def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _clean_mrz_line(raw: str) -> str:
    """Remove non-MRZ characters introduced by OCR noise."""
    cleaned = re.sub(r"[^A-Z0-9<]", "", raw.upper())
    return cleaned


def extract_via_tesseract(mrz_region: np.ndarray) -> tuple[Optional[PassportData], str]:
    """Run Tesseract on the MRZ region image and parse results.

    Returns (PassportData | None, confidence_level).
    """
    try:
        import pytesseract
        from PIL import Image as PILImage
    except ImportError:
        return None, "low"

    # Tesseract config for MRZ: whitelist MRZ charset, single-block mode
    config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
    pil = PILImage.fromarray(mrz_region)
    raw_text: str = pytesseract.image_to_string(pil, config=config)

    lines = [_clean_mrz_line(ln) for ln in raw_text.splitlines() if ln.strip()]
    # Keep lines that look like MRZ (mostly alpha/digit/<, length 30-44)
    mrz_lines = [ln for ln in lines if 28 <= len(ln) <= 44]

    if len(mrz_lines) < 2:
        return None, "low"

    line1, line2 = mrz_lines[0], mrz_lines[1]

    # Try mrz library for structured parsing
    data = _parse_with_mrz_lib(line1, line2)
    if data:
        return data, "medium"

    # Manual TD3 parse fallback
    data = _manual_td3_parse(line1, line2)
    return data, "low" if data is None else "medium"


def _parse_with_mrz_lib(line1: str, line2: str) -> Optional[PassportData]:
    try:
        from mrz.checker.td3 import TD3CodeChecker

        checker = TD3CodeChecker(line1 + "\n" + line2)
        fields = checker.fields()
        dob = getattr(fields, "birth_date", None)
        expiry = getattr(fields, "expiry_date", None)
        surname = getattr(fields, "surname", None) or ""
        given = getattr(fields, "name", None) or ""
        return PassportData(
            document_type=getattr(fields, "document_type", None),
            issuing_country=getattr(fields, "country", None),
            surname=strip_filler(surname),
            given_names=strip_filler(given),
            passport_number=getattr(fields, "document_number", None),
            nationality=getattr(fields, "nationality", None),
            date_of_birth=yymmdd_to_iso(dob) if dob else None,
            sex=getattr(fields, "sex", None),
            date_of_expiry=yymmdd_to_iso(expiry, is_expiry=True) if expiry else None,
            personal_number=getattr(fields, "optional_data", None),
            mrz_line_1=line1,
            mrz_line_2=line2,
            mrz_format=detect_mrz_format(line1, line2),
        )
    except Exception:
        return None


def _manual_td3_parse(line1: str, line2: str) -> Optional[PassportData]:
    """Bare-minimum TD3 parse without any library."""
    try:
        doc_type = line1[0]
        country = line1[2:5]
        name_field = line1[5:44]
        surname, given_names = parse_td3_names(name_field)

        pn = line2[0:9].replace("<", "")
        nat = line2[10:13]
        dob = yymmdd_to_iso(line2[13:19])
        sex_raw = line2[20]
        sex = sex_raw if sex_raw in ("M", "F") else "X"
        expiry = yymmdd_to_iso(line2[21:27], is_expiry=True)
        personal = strip_filler(line2[28:42])

        return PassportData(
            document_type=doc_type,
            issuing_country=country,
            surname=surname,
            given_names=given_names,
            passport_number=pn,
            nationality=nat,
            date_of_birth=dob,
            sex=sex,
            date_of_expiry=expiry,
            personal_number=personal or None,
            mrz_line_1=line1,
            mrz_line_2=line2,
            mrz_format="TD3",
        )
    except Exception:
        return None
