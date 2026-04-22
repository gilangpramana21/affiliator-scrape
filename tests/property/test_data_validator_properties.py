"""Property-based tests for DataValidator

**Validates: Requirements 6**
"""

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.data_validator import DataValidator, PHONE_REGEX, USERNAME_MAX_LEN
from src.models.models import AffiliatorData

validator = DataValidator()


def make_valid_data(**overrides) -> AffiliatorData:
    defaults = dict(
        username="affiliator123",
        kategori="Fashion",
        pengikut=1000,
        gmv=500000.0,
        produk_terjual=50,
        rata_rata_tayangan=2000,
        tingkat_interaksi=4.5,
        nomor_kontak=None,
        detail_url="https://example.com",
        scraped_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return AffiliatorData(**defaults)


# ── Generators ────────────────────────────────────────────────────────────────

valid_usernames = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-."),
    min_size=1,
    max_size=USERNAME_MAX_LEN,
).filter(lambda s: s.strip() != "")

invalid_usernames = st.one_of(
    st.just(""),
    st.just("   "),
    st.text(min_size=USERNAME_MAX_LEN + 1, max_size=USERNAME_MAX_LEN + 50),
    st.none(),
    st.integers(),
)

valid_percentages = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)

invalid_percentages = st.one_of(
    st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False),
    st.floats(min_value=100.001, allow_nan=False, allow_infinity=False),
)

valid_non_negative_ints = st.integers(min_value=0, max_value=10_000_000)
invalid_negative_ints = st.integers(max_value=-1)

valid_non_negative_floats = st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)

# Valid Indonesian phone numbers
valid_phones = st.one_of(
    # 08 prefix + 8-13 digits
    st.integers(min_value=10_000_000, max_value=9_999_999_999_999).map(lambda n: f"08{n}"),
    # +62 prefix + 8-13 digits
    st.integers(min_value=10_000_000, max_value=9_999_999_999_999).map(lambda n: f"+62{n}"),
).filter(lambda p: PHONE_REGEX.match(p) is not None)

# Invalid phones: wrong prefix or wrong length
invalid_phones = st.one_of(
    st.just(""),
    st.just("07123456789"),
    st.just("+63123456789"),
    st.just("081234"),          # too short
    st.just("08" + "1" * 14),  # too long
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=15),
)


# ── Properties ────────────────────────────────────────────────────────────────

@given(username=valid_usernames)
@settings(max_examples=200)
def test_property_valid_usernames_always_pass(username):
    """**Validates: Requirements 6** — valid usernames always pass validation"""
    fv = validator.validate_field("username", username)
    assert fv.is_valid is True, f"Expected valid username {username!r} to pass"


@given(username=invalid_usernames)
@settings(max_examples=100)
def test_property_invalid_usernames_always_fail(username):
    """**Validates: Requirements 6** — invalid usernames always fail validation"""
    fv = validator.validate_field("username", username)
    assert fv.is_valid is False, f"Expected invalid username {username!r} to fail"


@given(pct=valid_percentages)
@settings(max_examples=200)
def test_property_valid_percentages_always_pass(pct):
    """**Validates: Requirements 6** — values in [0, 100] always pass percentage validation"""
    fv = validator.validate_field("tingkat_interaksi", pct)
    assert fv.is_valid is True, f"Expected percentage {pct} to pass"


@given(pct=invalid_percentages)
@settings(max_examples=100)
def test_property_invalid_percentages_always_fail(pct):
    """**Validates: Requirements 6** — values outside [0, 100] always fail percentage validation"""
    fv = validator.validate_field("tingkat_interaksi", pct)
    assert fv.is_valid is False, f"Expected out-of-range percentage {pct} to fail"


@given(phone=valid_phones)
@settings(max_examples=200)
def test_property_valid_phones_always_pass(phone):
    """**Validates: Requirements 6** — valid Indonesian phone numbers always pass"""
    fv = validator.validate_field("nomor_kontak", phone)
    assert fv.is_valid is True, f"Expected valid phone {phone!r} to pass"


@given(phone=invalid_phones)
@settings(max_examples=100)
def test_property_invalid_phones_always_fail(phone):
    """**Validates: Requirements 6** — invalid phone numbers always fail"""
    fv = validator.validate_field("nomor_kontak", phone)
    assert fv.is_valid is False, f"Expected invalid phone {phone!r} to fail"


@pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
@given(value=valid_non_negative_ints)
@settings(max_examples=100)
def test_property_non_negative_ints_always_pass(field_name, value):
    """**Validates: Requirements 6** — non-negative integers always pass numeric validation"""
    fv = validator.validate_field(field_name, value)
    assert fv.is_valid is True


@pytest.mark.parametrize("field_name", ["pengikut", "produk_terjual", "rata_rata_tayangan"])
@given(value=invalid_negative_ints)
@settings(max_examples=100)
def test_property_negative_ints_always_fail(field_name, value):
    """**Validates: Requirements 6** — negative integers always fail numeric validation"""
    fv = validator.validate_field(field_name, value)
    assert fv.is_valid is False


@given(value=valid_non_negative_floats)
@settings(max_examples=100)
def test_property_non_negative_gmv_always_pass(value):
    """**Validates: Requirements 6** — non-negative gmv values always pass"""
    fv = validator.validate_field("gmv", value)
    assert fv.is_valid is True


@given(username=valid_usernames)
@settings(max_examples=100)
def test_property_valid_data_with_valid_username_is_valid(username):
    """**Validates: Requirements 6** — AffiliatorData with all valid fields passes validate()"""
    data = make_valid_data(username=username)
    result = validator.validate(data)
    assert result.is_valid is True


@given(pct=valid_percentages)
@settings(max_examples=100)
def test_property_validate_result_consistent_with_field_errors(pct):
    """**Validates: Requirements 6** — is_valid is False iff field_errors is non-empty"""
    data = make_valid_data(tingkat_interaksi=pct)
    result = validator.validate(data)
    assert result.is_valid == (len(result.field_errors) == 0)
    assert result.is_valid == (len(result.errors) == 0)
