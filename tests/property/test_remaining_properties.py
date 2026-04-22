"""Property-based tests for remaining properties (24-30).

**Validates: Requirements 7, 9, 12, 14, 15, 16**
"""

from __future__ import annotations

import tempfile
from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from src.control.rate_limiter import RateLimiter
from src.core.data_store import DataStore
from src.core.deduplicator import Deduplicator
from src.core.error_analyzer import ErrorAnalyzer
from src.core.http_client import Response
from src.models.config import Configuration
from src.models.models import AffiliatorData, Checkpoint


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

delay_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

scraped_usernames_strategy = st.sets(
    st.text(min_size=1, max_size=50),
    min_size=0,
    max_size=30,
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


def make_response(status: int = 200, url: str = "https://example.com", text: str = "ok") -> Response:
    return Response(status=status, url=url, text=text, headers={}, body=b"")


# ---------------------------------------------------------------------------
# Property 24: Deduplicator.clear() always resets counts to 0
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 24: Deduplicator.clear() Always Resets Counts to 0"
)
@settings(max_examples=100)
@given(usernames=st.lists(username_strategy, min_size=1, max_size=30))
def test_deduplicator_clear_resets_counts(usernames: list[str]):
    """**Validates: Requirements 15.3**

    FOR ALL sequences of add() calls, calling clear() SHALL reset
    unique_count, duplicate_count, and get_all() to zero/empty.
    """
    d = Deduplicator()
    for username in usernames:
        d.add(make_affiliator(username))

    d.clear()

    assert d.get_unique_count() == 0
    assert d.get_duplicate_count() == 0
    assert d.get_all() == []


# ---------------------------------------------------------------------------
# Property 25: RateLimiter.reset() always restores initial delays
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 25: RateLimiter.reset() Always Restores Initial Delays"
)
@settings(max_examples=100)
@given(
    min_delay=delay_strategy,
    extra=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    factor=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
)
def test_rate_limiter_reset_restores_initial_delays(
    min_delay: float, extra: float, factor: float
):
    """**Validates: Requirements 14.3**

    FOR ALL (min_delay, max_delay, factor) combinations, calling reset()
    after adjust_delay() SHALL restore min_delay and max_delay to their
    initial values.
    """
    max_delay = min_delay + extra
    rl = RateLimiter(min_delay=min_delay, max_delay=max_delay, jitter=0.1)

    rl.adjust_delay(factor)
    rl.reset()

    assert rl.min_delay == min_delay
    assert rl.max_delay == max_delay


# ---------------------------------------------------------------------------
# Property 26: DataStore save then load preserves record count
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 26: DataStore save then load Preserves Record Count"
)
@settings(max_examples=50)
@given(
    records=st.lists(affiliator_strategy, min_size=0, max_size=20),
    fmt=st.sampled_from(["json", "csv"]),
)
def test_data_store_save_load_preserves_count(records: list[AffiliatorData], fmt: str):
    """**Validates: Requirements 7.1, 7.2, 7.3, 12.1, 12.2**

    FOR ALL lists of AffiliatorData and both output formats, saving then
    loading SHALL return the same number of records.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        path = os.path.join(tmpdir, f"data.{fmt}")
        ds = DataStore(fmt, path)
        ds.save(records)
        loaded = ds.load()

    assert len(loaded) == len(records)


# ---------------------------------------------------------------------------
# Property 27: Configuration.validate() returns empty list for valid config
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 27: Configuration.validate() Returns Empty List for Valid Config"
)
@settings(max_examples=100)
@given(
    min_delay=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    extra=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    jitter=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_valid_configuration_returns_no_errors(
    min_delay: float, extra: float, jitter: float
):
    """**Validates: Requirements 9.1**

    FOR ALL valid (min_delay, max_delay, jitter) combinations, a Configuration
    with those values SHALL produce an empty errors list from validate().
    """
    max_delay = min_delay + extra
    config = Configuration(min_delay=min_delay, max_delay=max_delay, jitter=jitter)
    errors = config.validate()
    assert errors == [], f"Unexpected validation errors: {errors}"


# ---------------------------------------------------------------------------
# Property 28: AffiliatorData.to_dict() then from_dict() preserves username
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 28: AffiliatorData to_dict/from_dict Preserves Username"
)
@settings(max_examples=100)
@given(affiliator=affiliator_strategy)
def test_affiliator_data_dict_round_trip_preserves_username(affiliator: AffiliatorData):
    """**Validates: Requirements 2.6**

    FOR ALL AffiliatorData objects, converting to dict and back SHALL
    preserve the username field exactly.
    """
    restored = AffiliatorData.from_dict(affiliator.to_dict())
    assert restored.username == affiliator.username


# ---------------------------------------------------------------------------
# Property 29: Checkpoint.save() then load() preserves scraped_usernames set
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 29: Checkpoint save/load Preserves scraped_usernames Set"
)
@settings(max_examples=100)
@given(scraped_usernames=scraped_usernames_strategy)
def test_checkpoint_save_load_preserves_scraped_usernames(scraped_usernames: set[str]):
    """**Validates: Requirements 16.1, 16.2**

    FOR ALL sets of scraped usernames, saving a Checkpoint to disk and
    loading it back SHALL produce an identical scraped_usernames set.
    """
    checkpoint = Checkpoint(
        last_list_page=1,
        last_affiliator_index=0,
        scraped_usernames=scraped_usernames,
        timestamp=datetime(2024, 1, 1),
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    checkpoint.save(path)
    restored = Checkpoint.load(path)

    assert restored.scraped_usernames == scraped_usernames


# ---------------------------------------------------------------------------
# Property 30: ErrorAnalyzer consecutive errors count never exceeds total analyze() calls
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 30: ErrorAnalyzer Consecutive Errors Never Exceeds Total analyze() Calls"
)
@settings(max_examples=100)
@given(
    status_codes=st.lists(
        st.sampled_from([200, 403, 429, 404, 500]),
        min_size=1,
        max_size=20,
    )
)
def test_error_analyzer_consecutive_errors_never_exceeds_total_calls(
    status_codes: list[int],
):
    """**Validates: Requirements 16.4**

    FOR ALL sequences of analyze() calls, the length of consecutive_errors
    SHALL never exceed the total number of analyze() calls made.
    """
    analyzer = ErrorAnalyzer()
    total_calls = len(status_codes)

    for status in status_codes:
        response = make_response(status=status)
        analyzer.analyze(response, response_time=0.1)

    assert len(analyzer.consecutive_errors) <= total_calls
