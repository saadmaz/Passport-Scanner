"""Orchestrator: preprocessing → Tesseract OCR → validation."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from backend.models.passport import CheckDigitResult, PassportData, ScanResponse
from backend.services.check_digit import validate_td3
from backend.services.preprocessing import preprocess
from backend.services.tesseract_ocr import extract_via_tesseract


def _validate_check_digits(data: Optional[PassportData]) -> CheckDigitResult:
    if data is None or data.mrz_line_2 is None:
        return CheckDigitResult(
            passport_number=False,
            date_of_birth=False,
            date_of_expiry=False,
            composite=False,
        )
    line1 = data.mrz_line_1 or ""
    line2 = data.mrz_line_2
    results = validate_td3(line1, line2)
    return CheckDigitResult(**results)


def scan_image(image_bytes: bytes, content_type: str) -> ScanResponse:
    t0 = time.perf_counter()
    warnings: list[str] = []

    jpeg_bytes, mrz_candidates = preprocess(image_bytes, content_type)

    data: Optional[PassportData] = None
    confidence = "low"
    extraction_method: str = "none"

    # Try each MRZ candidate region; stop at first high/medium confidence result
    for mrz_region in mrz_candidates:
        tess_data, tess_confidence = extract_via_tesseract(mrz_region)
        if tess_data is None:
            continue
        if data is None or tess_confidence == "medium":
            data = tess_data
            confidence = tess_confidence
            extraction_method = "tesseract_mrz"
        if confidence == "medium":
            break

    check_digits = _validate_check_digits(data)

    failed = [k for k, v in check_digits.model_dump().items() if not v]
    if failed and data is not None:
        warnings.append(f"Check digit mismatch for: {', '.join(failed)}")

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return ScanResponse(
        success=data is not None,
        extraction_method=extraction_method,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        check_digits_valid=check_digits,
        warnings=warnings,
        processing_time_ms=round(elapsed_ms, 2),
        data=data,
    )
