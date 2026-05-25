"""Integration tests for POST /api/v1/scan using httpx + stub for Anthropic."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend.models.passport import CheckDigitResult, PassportData, ScanResponse

client = TestClient(app)


def _make_jpeg(width: int = 1600, height: int = 1200) -> bytes:
    img = Image.new("RGB", (width, height), color=(220, 220, 220))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


MOCK_PASSPORT = PassportData(
    document_type="P",
    issuing_country="UTO",
    surname="ERIKSSON",
    given_names="ANNA MARIA",
    passport_number="L898902C",
    nationality="UTO",
    date_of_birth="1974-08-12",
    sex="F",
    date_of_expiry="2012-04-15",
    personal_number=None,
    mrz_line_1="P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<<",
    mrz_line_2="L898902C<3740812<<<<<<<2120415<<<<<<<1<<<<<<<<<<<<<<8",
    mrz_format="TD3",
)

MOCK_RESPONSE = ScanResponse(
    success=True,
    extraction_method="claude_vision",
    confidence="high",
    check_digits_valid=CheckDigitResult(
        passport_number=True, date_of_birth=True, date_of_expiry=True, composite=True
    ),
    warnings=[],
    processing_time_ms=120.5,
    data=MOCK_PASSPORT,
)


class TestScanEndpoint:
    def test_missing_file_returns_422(self):
        resp = client.post("/api/v1/scan")
        assert resp.status_code == 422

    def test_wrong_content_type_returns_415(self):
        resp = client.post(
            "/api/v1/scan",
            files={"passport_image": ("test.gif", b"GIF89a", "image/gif")},
        )
        assert resp.status_code == 415

    def test_file_too_large_returns_413(self):
        big = b"X" * (10 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/v1/scan",
            files={"passport_image": ("big.jpg", big, "image/jpeg")},
        )
        assert resp.status_code == 413

    def test_valid_scan_with_stubbed_claude(self):
        jpeg = _make_jpeg()
        with patch("backend.services.scanner.extract_via_claude", return_value=(MOCK_PASSPORT, "high")):
            resp = client.post(
                "/api/v1/scan",
                files={"passport_image": ("passport.jpg", jpeg, "image/jpeg")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["extraction_method"] == "claude_vision"
        assert body["data"]["surname"] == "ERIKSSON"

    def test_claude_failure_falls_back(self):
        from backend.services.claude_ocr import OCRServiceUnavailable

        jpeg = _make_jpeg()
        with (
            patch(
                "backend.services.scanner.extract_via_claude",
                side_effect=OCRServiceUnavailable("test"),
            ),
            patch(
                "backend.services.scanner.extract_via_tesseract",
                return_value=(None, "low"),
            ),
        ):
            resp = client.post(
                "/api/v1/scan",
                files={"passport_image": ("passport.jpg", jpeg, "image/jpeg")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "Claude Vision unavailable" in str(body["warnings"])


class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "anthropic_reachable" in body
        assert "tesseract_available" in body


class TestSchemaEndpoint:
    def test_schema_returns_200(self):
        resp = client.get("/api/v1/schema")
        assert resp.status_code == 200
        body = resp.json()
        assert "properties" in body


class TestValidateEndpoint:
    LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<"
    LINE2 = "L898902C<3740812<<<<<<<2120415<<<<<<<1<<<<<<<<<<<<<<8"

    def test_valid_mrz(self):
        resp = client.post(
            "/api/v1/validate",
            json={"mrz_line_1": self.LINE1, "mrz_line_2": self.LINE2},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_invalid_mrz(self):
        resp = client.post(
            "/api/v1/validate",
            json={"mrz_line_1": self.LINE1, "mrz_line_2": "X" * 44},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
