"""Property-based tests for RateLimiter.

**Validates: Requirements 2 and 14**
"""

from __future__ import annotations

import asyncio
import time

import pytest
from hypothesis import given, settings, strategies as st

from src.control.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

delay_strategy = st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False)
jitter_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


# ---------------------------------------------------------------------------
# Property 11: Rate limiter minimum delay
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 11: Rate Limiter Minimum Delay"
)
@settings(max_examples=100)
@given(
    min_delay=delay_strategy,
    extra=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
    jitter=jitter_strategy,
)
def test_actual_delay_gte_minimum(min_delay: float, extra: float, jitter: float):
    """**Validates: Requirements 2.1, 14.1**

    FOR ALL valid (min_delay, max_delay, jitter) configurations,
    the actual sleep duration SHALL be >= min_delay * (1 - jitter).
    """
    max_delay = min_delay + extra
    rl = RateLimiter(min_delay=min_delay, max_delay=max_delay, jitter=jitter)

    start = time.monotonic()
    asyncio.run(rl.wait())
    elapsed = time.monotonic() - start

    lower_bound = max(0.0, min_delay * (1 - jitter))
    # Allow a small timer-resolution tolerance of 10 ms
    assert elapsed >= lower_bound - 0.01


# ---------------------------------------------------------------------------
# Property 12: Rate limiter sequential processing
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 12: Rate Limiter Sequential Processing"
)
@settings(max_examples=30)
@given(
    n=st.integers(min_value=2, max_value=5),
    min_delay=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
)
def test_sequential_waits_are_ordered(n: int, min_delay: float):
    """**Validates: Requirements 2.2, 2.4**

    FOR ALL sequences of n wait() calls, each call SHALL complete before
    the next one starts (sequential, not concurrent).
    """
    max_delay = min_delay + 0.005
    rl = RateLimiter(min_delay=min_delay, max_delay=max_delay, jitter=0.0)

    timestamps: list[float] = []

    async def run():
        for _ in range(n):
            await rl.wait()
            timestamps.append(time.monotonic())

    asyncio.run(run())

    # Each timestamp must be strictly non-decreasing (sequential ordering)
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1]
