"""Unit tests for RateLimiter."""

import asyncio
import time

import pytest

from src.control.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def test_init_stores_delays():
    rl = RateLimiter(min_delay=2.0, max_delay=5.0)
    assert rl.min_delay == 2.0
    assert rl.max_delay == 5.0
    assert rl.jitter == 0.2


def test_init_custom_jitter():
    rl = RateLimiter(min_delay=1.0, max_delay=3.0, jitter=0.1)
    assert rl.jitter == 0.1


# ---------------------------------------------------------------------------
# wait()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wait_completes():
    """wait() should complete without error."""
    rl = RateLimiter(min_delay=0.0, max_delay=0.01, jitter=0.0)
    await rl.wait()  # should not raise


@pytest.mark.asyncio
async def test_wait_takes_at_least_min_delay():
    """Actual sleep should be >= min_delay * (1 - jitter)."""
    min_delay = 0.05
    jitter = 0.2
    rl = RateLimiter(min_delay=min_delay, max_delay=min_delay, jitter=jitter)
    start = time.monotonic()
    await rl.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= min_delay * (1 - jitter) - 0.01  # small tolerance for timer resolution


@pytest.mark.asyncio
async def test_wait_never_sleeps_negative():
    """Even with extreme jitter, wait() should not raise or sleep negative."""
    rl = RateLimiter(min_delay=0.001, max_delay=0.001, jitter=1.0)
    start = time.monotonic()
    await rl.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.0


# ---------------------------------------------------------------------------
# adjust_delay()
# ---------------------------------------------------------------------------

def test_adjust_delay_scales_both():
    rl = RateLimiter(min_delay=2.0, max_delay=4.0)
    rl.adjust_delay(1.5)
    assert rl.min_delay == pytest.approx(3.0)
    assert rl.max_delay == pytest.approx(6.0)


def test_adjust_delay_slow_down_then_speed_up():
    rl = RateLimiter(min_delay=2.0, max_delay=4.0)
    rl.adjust_delay(2.0)
    rl.adjust_delay(0.5)
    assert rl.min_delay == pytest.approx(2.0)
    assert rl.max_delay == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

def test_reset_restores_initial_values():
    rl = RateLimiter(min_delay=2.0, max_delay=5.0, jitter=0.2)
    rl.adjust_delay(3.0)
    rl.reset()
    assert rl.min_delay == 2.0
    assert rl.max_delay == 5.0
    assert rl.jitter == 0.2


def test_reset_idempotent():
    rl = RateLimiter(min_delay=1.0, max_delay=3.0)
    rl.reset()
    rl.reset()
    assert rl.min_delay == 1.0
    assert rl.max_delay == 3.0


def test_adjust_then_reset_does_not_affect_initial():
    """Calling adjust_delay multiple times then reset should always return to init."""
    rl = RateLimiter(min_delay=2.0, max_delay=5.0)
    for _ in range(5):
        rl.adjust_delay(1.5)
    rl.reset()
    assert rl.min_delay == 2.0
    assert rl.max_delay == 5.0
