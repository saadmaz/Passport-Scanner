"""Claude Vision OCR integration for passport MRZ extraction."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import anthropic

from backend.models.passport import PassportData
from backend.services.normalizer import detect_mrz_format, parse_td3_names, yymmdd_to_iso, strip_filler


class OCRServiceUnavailable(Exception):
    pass


_SYSTEM_PROMPT = """\
You are an expert passport MRZ (Machine Readable Zone) reader.
Extract all MRZ fields from the passport image provided and return ONLY valid JSON.
No markdown fences, no explanation — just the JSON object.

The JSON must conform exactly to this structure:
{
  "mrz_line_1": "<44-char string or null>",
  "mrz_line_2": "<44-char string or null>",
  "document_type": "<string or null>",
  "issuing_country": "<3-letter code or null>",
  "surname": "<string or null>",
  "given_names": "<string or null>",
  "passport_number": "<string or null>",
  "nationality": "<string or null>",
  "date_of_birth": "<YYMMDD or null>",
  "sex": "<M|F|X or null>",
  "date_of_expiry": "<YYMMDD or null>",
  "personal_number": "<string or null>",
  "confidence": "<high|medium|low>"
}

Rules:
- Return raw YYMMDD for dates (not ISO), normalizer converts them.
- Strip trailing < filler only from name fields.
- If the MRZ is not visible or unreadable, return all fields as null with confidence=low.
"""


def _build_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise OCRServiceUnavailable("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


def extract_via_claude(jpeg_bytes: bytes) -> tuple[PassportData, str]:
    """Send image to Claude Vision and return (PassportData, confidence).

    Raises OCRServiceUnavailable on API errors.
    """
    client = _build_client()
    b64 = base64.standard_b64encode(jpeg_bytes).decode()

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": "Extract the MRZ from this passport image."},
                    ],
                }
            ],
        )
    except anthropic.APIConnectionError as exc:
        raise OCRServiceUnavailable("Anthropic API unreachable") from exc
    except anthropic.APITimeoutError as exc:
        raise OCRServiceUnavailable("Anthropic API timed out") from exc
    except anthropic.APIStatusError as exc:
        raise OCRServiceUnavailable(f"Anthropic API error {exc.status_code}") from exc

    raw_text = message.content[0].text.strip()
    try:
        payload: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OCRServiceUnavailable(f"Claude returned non-JSON: {raw_text[:200]}") from exc

    confidence = payload.pop("confidence", "low")

    line1 = payload.get("mrz_line_1") or ""
    line2 = payload.get("mrz_line_2") or ""
    mrz_format = detect_mrz_format(line1, line2) if line1 and line2 else "TD3"

    dob_raw = payload.get("date_of_birth")
    expiry_raw = payload.get("date_of_expiry")

    # Parse names from raw MRZ line1 if individual fields missing
    surname = payload.get("surname")
    given_names = payload.get("given_names")
    if (not surname or not given_names) and line1 and len(line1) >= 44:
        surname, given_names = parse_td3_names(line1[5:44])

    data = PassportData(
        document_type=payload.get("document_type"),
        issuing_country=payload.get("issuing_country"),
        surname=strip_filler(surname) if surname else None,
        given_names=strip_filler(given_names) if given_names else None,
        passport_number=payload.get("passport_number"),
        nationality=payload.get("nationality"),
        date_of_birth=yymmdd_to_iso(dob_raw) if dob_raw else None,
        sex=payload.get("sex"),
        date_of_expiry=yymmdd_to_iso(expiry_raw, is_expiry=True) if expiry_raw else None,
        personal_number=payload.get("personal_number"),
        mrz_line_1=line1 or None,
        mrz_line_2=line2 or None,
        mrz_format=mrz_format,
    )
    return data, confidence
