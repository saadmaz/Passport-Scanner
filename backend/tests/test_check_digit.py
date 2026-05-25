"""ICAO 9303 check digit tests using official test vectors."""

import pytest
from backend.services.check_digit import compute_check_digit, validate_check_digit, validate_td3


# ICAO 9303 Part 3 official test vectors
class TestComputeCheckDigit:
    def test_icao_vector_passport_number(self):
        # From ICAO 9303 Part 3 §4.9: L898902C<3
        assert compute_check_digit("L898902C<") == 3

    def test_icao_vector_dob(self):
        # 740812 → 2
        assert compute_check_digit("740812") == 2

    def test_icao_vector_expiry(self):
        # 120415 → 9
        assert compute_check_digit("120415") == 9

    def test_icao_vector_composite(self):
        # TD3 line2 positions 0-9 + 13-19 + 21-42
        # Using the ICAO sample: L898902C<3740812<<<<<<<2120415<<<<<<<1<<<<<<<<<<<<<<8
        line2 = "L898902C<3740812<<<<<<<2120415<<<<<<<1<<<<<<<<<<<<<<8"
        composite = line2[0:10] + line2[13:20] + line2[21:43]
        assert compute_check_digit(composite) == 8

    def test_all_zeros(self):
        assert compute_check_digit("000000") == 0

    def test_all_fillers(self):
        assert compute_check_digit("<<<<<<") == 0

    def test_mixed_alphanumeric(self):
        # A = 10, weight 7 → 70 % 10 = 0
        assert compute_check_digit("A") == 0

    def test_digit_9_weight_7(self):
        # 9 × 7 = 63 % 10 = 3
        assert compute_check_digit("9") == 3


class TestValidateCheckDigit:
    def test_valid(self):
        assert validate_check_digit("L898902C<", "3") is True

    def test_invalid(self):
        assert validate_check_digit("L898902C<", "4") is False

    def test_bad_check_char(self):
        assert validate_check_digit("L898902C<", "X") is False


class TestValidateTD3:
    # ICAO sample passport from Part 3
    LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<"
    LINE2 = "L898902C<3740812<<<<<<<2120415<<<<<<<1<<<<<<<<<<<<<<8"

    def test_all_pass(self):
        result = validate_td3(self.LINE1, self.LINE2)
        assert result["passport_number"] is True
        assert result["date_of_birth"] is True
        assert result["date_of_expiry"] is True
        assert result["composite"] is True

    def test_short_line2_all_fail(self):
        result = validate_td3(self.LINE1, "SHORT")
        assert all(v is False for v in result.values())

    def test_corrupted_passport_number(self):
        corrupted = "X" + self.LINE2[1:]
        result = validate_td3(self.LINE1, corrupted)
        assert result["passport_number"] is False

    def test_corrupted_dob(self):
        line2 = list(self.LINE2)
        line2[13] = "9"  # corrupt DOB first digit
        result = validate_td3(self.LINE1, "".join(line2))
        assert result["date_of_birth"] is False
