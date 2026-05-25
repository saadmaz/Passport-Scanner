from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class CheckDigitResult(BaseModel):
    passport_number: bool
    date_of_birth: bool
    date_of_expiry: bool
    composite: bool


class PassportData(BaseModel):
    # MRZ line 1
    document_type: Optional[str] = Field(None, description="P for passport")
    issuing_country: Optional[str] = Field(None, description="3-letter ISO country code")
    surname: Optional[str] = None
    given_names: Optional[str] = None

    # MRZ line 2
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="ISO 8601 YYYY-MM-DD")
    sex: Optional[Literal["M", "F", "X"]] = None
    date_of_expiry: Optional[str] = Field(None, description="ISO 8601 YYYY-MM-DD")
    personal_number: Optional[str] = None

    # Raw MRZ
    mrz_line_1: Optional[str] = None
    mrz_line_2: Optional[str] = None

    # TD format
    mrz_format: Optional[Literal["TD1", "TD2", "TD3"]] = None


class ScanResponse(BaseModel):
    success: bool
    extraction_method: Literal["tesseract_mrz", "none"]
    confidence: Literal["high", "medium", "low"]
    check_digits_valid: CheckDigitResult
    warnings: list[str] = Field(default_factory=list)
    processing_time_ms: float
    data: Optional[PassportData] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    tesseract_available: bool


class SchemaResponse(BaseModel):
    schema_: dict = Field(alias="schema")

    class Config:
        populate_by_name = True


class ValidateMRZRequest(BaseModel):
    mrz_line_1: str
    mrz_line_2: str
