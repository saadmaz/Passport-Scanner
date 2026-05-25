"""Scan router: /api/v1/* endpoints."""

from __future__ import annotations

import io
import os
import shutil

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.passport import (
    HealthResponse,
    ScanResponse,
    ValidateMRZRequest,
)
from backend.services.check_digit import validate_td3
from backend.services.preprocessing import (
    ImageTooLargeError,
    ImageTooSmallError,
    UnsupportedFormatError,
)
from backend.services.scanner import scan_image

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

_rate_limit = os.getenv("RATE_LIMIT_PER_HOUR", "100")


@router.post("/scan", response_model=ScanResponse)
@limiter.limit(f"{_rate_limit}/hour")
async def scan_passport(request: Request, passport_image: UploadFile = File(...)):
    content_type = (passport_image.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Upload JPEG or PNG.",
        )

    # Stream into memory via SpooledTemporaryFile — never touch disk
    buf = io.BytesIO()
    chunk_size = 65_536
    total = 0
    while True:
        chunk = await passport_image.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds 10 MB limit.",
            )
        buf.write(chunk)

    image_bytes = buf.getvalue()

    try:
        result = scan_image(image_bytes, content_type)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))
    except ImageTooSmallError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return result


@router.get("/health", response_model=HealthResponse)
async def health():
    anthropic_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    tesseract_ok = shutil.which("tesseract") is not None

    overall = "ok" if (anthropic_ok and tesseract_ok) else "degraded"
    return HealthResponse(
        status=overall,
        anthropic_reachable=anthropic_ok,
        tesseract_available=tesseract_ok,
    )


@router.get("/schema")
async def schema():
    return ScanResponse.model_json_schema()


@router.post("/validate")
async def validate_mrz(req: ValidateMRZRequest):
    results = validate_td3(req.mrz_line_1, req.mrz_line_2)
    all_valid = all(results.values())
    return {
        "valid": all_valid,
        "check_digits": results,
    }
