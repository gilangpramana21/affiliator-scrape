"""Unit tests for DataValidator"""

from datetime import datetime

import pytest

from src.core.data_validator import DataValidator, FieldValidation, ValidationResult
from src.models.models import AffiliatorData


def make_valid_data(**overrides) -> AffiliatorData:
    defaults = dict(
        username="affiliator123",
        kategori="Fashion",
        pengikut=1000,
        gmv=500000.0,
        produk_terjual=50,
        rata_rata_tayangan=2000,
        tingkat_interaksi=4.5,
        nomor_kontak="081234567890",
        detail_url="https://example.com/affiliator123",
        scraped_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return AffiliatorData(**defaults)


@pytest.fixture
def validator():
    return DataValidator()


# ── validate() ────────────────────────────────────────────────────────────────

class TestValidateMethod:
    def test_valid_data_returns_is_valid_true(self, validator):
        result = validator.validate(make_valid_data())
        assert result.is_valid is True
        assert result.errors == []
        assert result.field_errors == {}

    def test_valid_data_without_phone_is_valid(self, validator):
        result = validator.validate(make_valid_data(nomor_kontak=None))
        assert result.is_valid is True

    def test_invalid_username_captured(self, validator):
        result = validator.validate(make_valid_data(username=""))
        assert result.is_valid is False
        assert "username" in result.field_errors

    def test_multiple_invalid_fields_all_captured(self, validator):
        result = validator.validate(make_valid_data(username="", pengikut=-1))
        assert result.is_valid is False
        assert "username" in result.field_errors
        assert "pengikut" in result.field_errors
        assert len(result.errors) == 2

    def test_invalid_phone_captured(self, validator):
        result = validator.validate(make_valid_data(nomor_kontak="12345"))
        assert result.is_valid is False
        assert "nomor_kontak" in result.field_errors

    def test_returns_validation_result_type(self, validator):
        result = validator.validate(make_valid_data())
        assert isinstance(result, ValidationResult)


# ── username ──────────────────────────────────────────────────────────────────

class TestUsernameValidation:
    def test_valid_username(self, validator):
        fv = validator.validate_field("username", "john_doe")
        assert fv.is_valid is True
        assert fv.error is None

    def test_empty_string_invalid(self, validator):
        fv = validator.validate_field("username", "")
        assert fv.is_valid is False

    def test_whitespace_only_invalid(self, validator):
        fv = validator.validate_field("username", "   ")
        assert fv.is_valid is False

    def test_none_invalid(self, validator):
        fv = validator.validate_field("username", None)
        assert fv.is_valid is False

    def test_exactly_100_chars_valid(self, validator):
        fv = validator.validate_field("username", "a" * 100)
        assert fv.is_valid is True

    def test_101_chars_invalid(self, validator):
        fv = validator.validate_field("username", "a" * 101)
        assert fv.is_valid is False

    def test_returns_field_validation_type(self, validator):
        fv = validator.validate_field("username", "user")
        assert isinstance(fv, FieldValidation)


# ── numeric fields ────────────────────────────────────────────────────────────

class TestNumericFieldValidation:
    @pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
    def test_valid_non_negative_int(self, validator, field_name):
        fv = validator.validate_field(field_name, 100)
        assert fv.is_valid is True
        assert fv.value == 100

    @pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
    def test_zero_is_valid(self, validator, field_name):
        fv = validator.validate_field(field_name, 0)
        assert fv.is_valid is True

    @pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
    def test_negative_int_invalid(self, validator, field_name):
        fv = validator.validate_field(field_name, -1)
        assert fv.is_valid is False

    @pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
    def test_string_number_converted(self, validator, field_name):
        fv = validator.validate_field(field_name, "42")
        assert fv.is_valid is True
        assert fv.value == 42

    @pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
    def test_non_numeric_string_invalid(self, validator, field_name):
        fv = validator.validate_field(field_name, "abc")
        assert fv.is_valid is False

    def test_gmv_valid_float(self, validator):
        fv = validator.validate_field("gmv", 1234.56)
        assert fv.is_valid is True
        assert fv.value == 1234.56

    def test_gmv_zero_valid(self, validator):
        fv = validator.validate_field("gmv", 0.0)
        assert fv.is_valid is True

    def test_gmv_negative_invalid(self, validator):
        fv = validator.validate_field("gmv", -0.01)
        assert fv.is_valid is False

    def test_gmv_string_converted(self, validator):
        fv = validator.validate_field("gmv", "999.99")
        assert fv.is_valid is True
        assert fv.value == pytest.approx(999.99)


# ── percentage ────────────────────────────────────────────────────────────────

class TestPercentageValidation:
    def test_valid_percentage_middle(self, validator):
        fv = validator.validate_field("tingkat_interaksi", 50.0)
        assert fv.is_valid is True

    def test_zero_valid(self, validator):
        fv = validator.validate_field("tingkat_interaksi", 0.0)
        assert fv.is_valid is True

    def test_hundred_valid(self, validator):
        fv = validator.validate_field("tingkat_interaksi", 100.0)
        assert fv.is_valid is True

    def test_above_100_invalid(self, validator):
        fv = validator.validate_field("tingkat_interaksi", 100.01)
        assert fv.is_valid is False

    def test_negative_invalid(self, validator):
        fv = validator.validate_field("tingkat_interaksi", -0.01)
        assert fv.is_valid is False

    def test_string_percentage_converted(self, validator):
        fv = validator.validate_field("tingkat_interaksi", "75.5")
        assert fv.is_valid is True
        assert fv.value == pytest.approx(75.5)

    def test_non_numeric_invalid(self, validator):
        fv = validator.validate_field("tingkat_interaksi", "high")
        assert fv.is_valid is False


# ── phone number ──────────────────────────────────────────────────────────────

class TestPhoneValidation:
    @pytest.mark.parametrize("phone", [
        "081234567890",
        "08123456789012",
        "+6281234567890",
        "+628123456789012",
        "0812345678",   # 8 digits after 08
    ])
    def test_valid_phones(self, validator, phone):
        fv = validator.validate_field("nomor_kontak", phone)
        assert fv.is_valid is True, f"Expected {phone!r} to be valid"

    @pytest.mark.parametrize("phone", [
        "12345678901",       # doesn't start with 08 or +62
        "07123456789",       # starts with 07
        "+63123456789",      # wrong country code
        "081234",            # too short
        "08" + "1" * 14,     # too long (14 digits after 08)
        "",                  # empty
        "abc",               # non-numeric
    ])
    def test_invalid_phones(self, validator, phone):
        fv = validator.validate_field("nomor_kontak", phone)
        assert fv.is_valid is False, f"Expected {phone!r} to be invalid"

    def test_none_value_invalid(self, validator):
        fv = validator.validate_field("nomor_kontak", None)
        assert fv.is_valid is False

    def test_valid_phone_value_preserved(self, validator):
        phone = "081234567890"
        fv = validator.validate_field("nomor_kontak", phone)
        assert fv.value == phone
