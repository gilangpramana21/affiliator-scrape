"""Property-based tests for AffiliatorExtractor numeric parsing.

**Validates: Requirements 5**
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from src.core.affiliator_extractor import AffiliatorExtractor


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

# Non-negative float values as strings (plain numbers)
non_negative_number_strings = st.floats(
    min_value=0.0,
    max_value=1_000_000_000.0,
    allow_nan=False,
    allow_infinity=False,
).map(lambda f: str(f))

# Strings with K suffix representing thousands (1K to 999K)
k_suffix_strings = st.floats(
    min_value=1.0,
    max_value=999.9,
    allow_nan=False,
    allow_infinity=False,
).map(lambda f: f"{f:.1f}K")


# ---------------------------------------------------------------------------
# Property 17: parse_numeric(None) always returns None
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 17: parse_numeric(None) Always Returns None"
)
def test_parse_numeric_none_returns_none():
    """**Validates: Requirements 5.7**

    parse_numeric(None) SHALL always return None.
    """
    result = AffiliatorExtractor.parse_numeric(None)
    assert result is None


# ---------------------------------------------------------------------------
# Property 18: parse_numeric of non-negative number string returns non-negative float
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 18: parse_numeric of Non-Negative Number String Returns Non-Negative Float"
)
@settings(max_examples=100)
@given(value=non_negative_number_strings)
def test_parse_numeric_non_negative_string_returns_non_negative(value: str):
    """**Validates: Requirements 5.7**

    FOR ALL non-negative number strings, parse_numeric() SHALL return a
    non-negative float (or None if unparseable, but never a negative value).
    """
    result = AffiliatorExtractor.parse_numeric(value)
    if result is not None:
        assert result >= 0.0, (
            f"parse_numeric({value!r}) returned negative value {result}"
        )


# ---------------------------------------------------------------------------
# Property 19: parse_numeric with K suffix always returns value >= 1000
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 19: parse_numeric With K Suffix Returns Value >= 1000"
)
@settings(max_examples=100)
@given(value=k_suffix_strings)
def test_parse_numeric_k_suffix_returns_gte_1000(value: str):
    """**Validates: Requirements 5.7**

    FOR ALL strings with a K suffix (e.g. '1.5K'), parse_numeric() SHALL
    return a value >= 1000.
    """
    result = AffiliatorExtractor.parse_numeric(value)
    assert result is not None, f"parse_numeric({value!r}) returned None unexpectedly"
    assert result >= 1000.0, (
        f"parse_numeric({value!r}) returned {result}, expected >= 1000"
    )
