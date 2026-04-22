"""Property-based tests for Deduplicator.

**Validates: Requirement 15**
"""

from __future__ import annotations

from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from src.core.deduplicator import Deduplicator
from src.models.models import AffiliatorData


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

username_strategy = st.text(min_size=1, max_size=50)

affiliator_strategy = st.builds(
    AffiliatorData,
    username=username_strategy,
    kategori=st.just("Fashion"),
    pengikut=st.integers(min_value=0, max_value=10_000_000),
    gmv=st.floats(min_value=0, max_value=1_000_000_000, allow_nan=False, allow_infinity=False),
    produk_terjual=st.integers(min_value=0, max_value=1_000_000),
    rata_rata_tayangan=st.integers(min_value=0, max_value=10_000_000),
    tingkat_interaksi=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    nomor_kontak=st.none(),
    detail_url=st.just("https://affiliate.tokopedia.com/creator/x"),
    scraped_at=st.just(datetime(2024, 1, 1)),
)


def make_affiliator(username: str) -> AffiliatorData:
    return AffiliatorData(
        username=username,
        kategori="Fashion",
        pengikut=0,
        gmv=0.0,
        produk_terjual=0,
        rata_rata_tayangan=0,
        tingkat_interaksi=0.0,
        nomor_kontak=None,
        detail_url="https://affiliate.tokopedia.com/creator/x",
        scraped_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Property 20: Adding the same affiliator twice results in exactly 1 unique record
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 20: Adding Same Affiliator Twice Yields Exactly One Unique Record"
)
@settings(max_examples=200)
@given(username=username_strategy)
def test_adding_same_affiliator_twice_yields_one_unique(username: str):
    """**Validates: Requirements 15.1, 15.2**

    FOR ALL usernames, adding an affiliator with that username twice SHALL
    result in exactly 1 unique record and 1 duplicate count.
    """
    d = Deduplicator()
    a1 = make_affiliator(username)
    a2 = make_affiliator(username)

    d.add(a1)
    d.add(a2)

    assert d.get_unique_count() == 1
    assert d.get_duplicate_count() == 1
    assert len(d.get_all()) == 1
    assert d.get_all()[0].username == username


# ---------------------------------------------------------------------------
# Property 21: unique count + duplicate count = total add() calls
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 21: Unique Count + Duplicate Count Equals Total Add Calls"
)
@settings(max_examples=200)
@given(usernames=st.lists(username_strategy, min_size=1, max_size=50))
def test_unique_plus_duplicate_equals_total_adds(usernames: list[str]):
    """**Validates: Requirements 15.4**

    FOR ALL sequences of add() calls, the sum of unique_count and
    duplicate_count SHALL equal the total number of add() calls made.
    """
    d = Deduplicator()
    total_adds = len(usernames)

    for username in usernames:
        d.add(make_affiliator(username))

    assert d.get_unique_count() + d.get_duplicate_count() == total_adds
