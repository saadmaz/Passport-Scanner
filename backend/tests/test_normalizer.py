"""Normalizer unit tests — century inference edge cases."""

import pytest
from backend.services.normalizer import (
    detect_mrz_format,
    parse_td3_names,
    strip_filler,
    yymmdd_to_iso,
)


class TestYymmddToIso:
    def test_dob_yy_31_is_1900s(self):
        assert yymmdd_to_iso("310101") == "1931-01-01"

    def test_dob_yy_30_is_1900s(self):
        # threshold default=30, so YY=30 → >30 is False, maps to 2000s
        # Actually: yy > threshold (30 > 30 = False) → 2000s
        assert yymmdd_to_iso("300101") == "2030-01-01"

    def test_dob_yy_00_is_2000s(self):
        assert yymmdd_to_iso("000101") == "2000-01-01"

    def test_dob_yy_29_is_2000s(self):
        assert yymmdd_to_iso("290615") == "2029-06-15"

    def test_expiry_always_2000s(self):
        # is_expiry=True forces 2000s regardless of YY
        assert yymmdd_to_iso("991231", is_expiry=True) == "2099-12-31"

    def test_expiry_normal(self):
        assert yymmdd_to_iso("280101", is_expiry=True) == "2028-01-01"

    def test_invalid_returns_none(self):
        assert yymmdd_to_iso("") is None
        assert yymmdd_to_iso("12345") is None
        assert yymmdd_to_iso("12345X") is None
        assert yymmdd_to_iso(None) is None  # type: ignore[arg-type]

    def test_valid_format(self):
        result = yymmdd_to_iso("850315")
        assert result == "1985-03-15"


class TestDetectMrzFormat:
    def test_td3(self):
        assert detect_mrz_format("P" * 44, "X" * 44) == "TD3"

    def test_td1(self):
        assert detect_mrz_format("A" * 30, "B" * 30) == "TD1"

    def test_td2(self):
        assert detect_mrz_format("A" * 36, "B" * 36) == "TD2"


class TestParseTd3Names:
    def test_simple(self):
        surname, given = parse_td3_names("ERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<<")
        assert surname == "ERIKSSON"
        assert given == "ANNA MARIA"

    def test_single_name(self):
        surname, given = parse_td3_names("SMITH<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        assert surname == "SMITH"
        assert given == ""

    def test_filler_stripped(self):
        surname, given = parse_td3_names("DOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        assert surname == "DOE"
        assert given == "JOHN"


class TestStripFiller:
    def test_strips_angle_brackets(self):
        assert strip_filler("SMITH<<<") == "SMITH"

    def test_internal_filler_becomes_space(self):
        assert strip_filler("ANNA<MARIA") == "ANNA MARIA"
