"""Unit tests for TrafficController (Task 13)."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.control.traffic_controller import TrafficConfig, TrafficController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_controller(**kwargs) -> TrafficController:
    """Create a TrafficController with sensible test defaults."""
    defaults = dict(
        hourly_limit=5,
        daily_limit=10,
        max_session_duration=60,   # 1 minute for fast tests
        break_duration_min=1,
        break_duration_max=2,
        quiet_hours=[(1, 6)],
    )
    defaults.update(kwargs)
    return TrafficController(TrafficConfig(**defaults))


# ---------------------------------------------------------------------------
# 13.1 TrafficController class
# ---------------------------------------------------------------------------

class TestTrafficControllerInit:
    def test_creates_with_config(self):
        config = TrafficConfig()
        tc = TrafficController(config)
        assert tc.config is config

    def test_request_log_starts_empty(self):
        tc = make_controller()
        assert tc.get_request_log() == []

    def test_session_start_is_none_initially(self):
        tc = make_controller()
        assert tc._session_start is None


# ---------------------------------------------------------------------------
# 13.2 Hourly request limit tracking
# ---------------------------------------------------------------------------

class TestHourlyLimitTracking:
    def test_hourly_count_counts_recent_requests(self):
        tc = make_controller(hourly_limit=5)
        now = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(3):
            tc._request_log.append(now - timedelta(minutes=10 + i))
        assert tc._hourly_count(now) == 3

    def test_hourly_count_excludes_old_requests(self):
        tc = make_controller(hourly_limit=5)
        now = datetime(2024, 1, 1, 12, 0, 0)
        tc._request_log.append(now - timedelta(hours=2))
        tc._request_log.append(now - timedelta(minutes=30))
        assert tc._hourly_count(now) == 1

    @pytest.mark.asyncio
    async def test_hourly_limit_blocks_permission(self):
        tc = make_controller(hourly_limit=3, daily_limit=100, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)
        for _ in range(3):
            tc._request_log.append(now - timedelta(minutes=5))

        with patch.object(tc, '_now', return_value=now):
            result = await tc.check_permission()
        assert result is False


# ---------------------------------------------------------------------------
# 13.3 Daily request limit tracking
# ---------------------------------------------------------------------------

class TestDailyLimitTracking:
    def test_daily_count_counts_last_24h(self):
        tc = make_controller()
        now = datetime(2024, 1, 2, 12, 0, 0)
        tc._request_log.append(now - timedelta(hours=23))
        tc._request_log.append(now - timedelta(hours=25))  # outside window
        assert tc._daily_count(now) == 1

    @pytest.mark.asyncio
    async def test_daily_limit_blocks_permission(self):
        tc = make_controller(hourly_limit=100, daily_limit=3, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)
        for _ in range(3):
            tc._request_log.append(now - timedelta(hours=1))

        with patch.object(tc, '_now', return_value=now):
            result = await tc.check_permission()
        assert result is False

    def test_prune_log_removes_old_entries(self):
        tc = make_controller()
        now = datetime(2024, 1, 2, 12, 0, 0)
        tc._request_log.append(now - timedelta(hours=25))  # old
        tc._request_log.append(now - timedelta(hours=1))   # recent
        tc._prune_log(now)
        assert len(tc._request_log) == 1


# ---------------------------------------------------------------------------
# 13.4 check_permission() method
# ---------------------------------------------------------------------------

class TestCheckPermission:
    @pytest.mark.asyncio
    async def test_allows_when_under_limits(self):
        tc = make_controller(hourly_limit=10, daily_limit=100, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)
        with patch.object(tc, '_now', return_value=now):
            assert await tc.check_permission() is True

    @pytest.mark.asyncio
    async def test_denies_when_hourly_limit_reached(self):
        tc = make_controller(hourly_limit=2, daily_limit=100, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)
        tc._request_log = [now - timedelta(minutes=5)] * 2
        with patch.object(tc, '_now', return_value=now):
            assert await tc.check_permission() is False

    @pytest.mark.asyncio
    async def test_denies_when_daily_limit_reached(self):
        tc = make_controller(hourly_limit=100, daily_limit=2, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)
        tc._request_log = [now - timedelta(hours=2)] * 2
        with patch.object(tc, '_now', return_value=now):
            assert await tc.check_permission() is False

    @pytest.mark.asyncio
    async def test_denies_during_quiet_hours(self):
        tc = make_controller(hourly_limit=100, daily_limit=100, quiet_hours=[(1, 6)])
        quiet_time = datetime(2024, 1, 1, 3, 0, 0)  # 3 AM
        with patch.object(tc, '_now', return_value=quiet_time):
            assert await tc.check_permission() is False

    @pytest.mark.asyncio
    async def test_allows_outside_quiet_hours(self):
        tc = make_controller(hourly_limit=100, daily_limit=100, quiet_hours=[(1, 6)])
        active_time = datetime(2024, 1, 1, 10, 0, 0)  # 10 AM
        with patch.object(tc, '_now', return_value=active_time):
            assert await tc.check_permission() is True


# ---------------------------------------------------------------------------
# 13.5 wait_for_window_reset() method
# ---------------------------------------------------------------------------

class TestWaitForWindowReset:
    @pytest.mark.asyncio
    async def test_waits_for_hourly_window(self):
        tc = make_controller(hourly_limit=2, daily_limit=100)
        now = datetime(2024, 1, 1, 12, 30, 0)
        # Two requests 20 minutes ago — they expire in 40 minutes
        tc._request_log = [now - timedelta(minutes=20)] * 2

        slept = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        with patch.object(tc, '_now', return_value=now), \
             patch('asyncio.sleep', side_effect=fake_sleep):
            await tc.wait_for_window_reset()

        assert len(slept) == 1
        # Should sleep ~40 minutes (2400 seconds), allow small float tolerance
        assert abs(slept[0] - 2400) < 2

    @pytest.mark.asyncio
    async def test_waits_for_daily_window_when_longer(self):
        tc = make_controller(hourly_limit=100, daily_limit=2)
        now = datetime(2024, 1, 2, 12, 0, 0)
        # Two requests 23 hours ago — daily window expires in 1 hour
        tc._request_log = [now - timedelta(hours=23)] * 2

        slept = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        with patch.object(tc, '_now', return_value=now), \
             patch('asyncio.sleep', side_effect=fake_sleep):
            await tc.wait_for_window_reset()

        assert len(slept) == 1
        assert abs(slept[0] - 3600) < 2  # ~1 hour

    @pytest.mark.asyncio
    async def test_no_sleep_when_under_limits(self):
        tc = make_controller(hourly_limit=10, daily_limit=100)
        now = datetime(2024, 1, 1, 12, 0, 0)

        slept = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        with patch.object(tc, '_now', return_value=now), \
             patch('asyncio.sleep', side_effect=fake_sleep):
            await tc.wait_for_window_reset()

        assert slept == []


# ---------------------------------------------------------------------------
# 13.6 Session break logic
# ---------------------------------------------------------------------------

class TestSessionBreakLogic:
    def test_should_take_break_false_before_session_starts(self):
        tc = make_controller(max_session_duration=60)
        assert tc.should_take_break() is False

    def test_should_take_break_false_within_duration(self):
        tc = make_controller(max_session_duration=3600)
        now = datetime(2024, 1, 1, 12, 0, 0)
        tc._session_start = now - timedelta(minutes=30)
        with patch.object(tc, '_now', return_value=now):
            assert tc.should_take_break() is False

    def test_should_take_break_true_after_duration(self):
        tc = make_controller(max_session_duration=3600)
        now = datetime(2024, 1, 1, 14, 0, 0)
        tc._session_start = now - timedelta(hours=2)
        with patch.object(tc, '_now', return_value=now):
            assert tc.should_take_break() is True

    @pytest.mark.asyncio
    async def test_take_break_resets_session_start(self):
        tc = make_controller(break_duration_min=0, break_duration_max=0)
        tc._session_start = datetime(2024, 1, 1, 10, 0, 0)

        async def fake_sleep(_):
            pass

        with patch('asyncio.sleep', side_effect=fake_sleep):
            await tc.take_break()

        assert tc._session_start is None

    @pytest.mark.asyncio
    async def test_take_break_sleeps_within_range(self):
        tc = make_controller(break_duration_min=10, break_duration_max=20)
        slept = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        with patch('asyncio.sleep', side_effect=fake_sleep):
            await tc.take_break()

        assert len(slept) == 1
        assert 10 <= slept[0] <= 20


# ---------------------------------------------------------------------------
# 13.7 Quiet hours enforcement
# ---------------------------------------------------------------------------

class TestQuietHoursEnforcement:
    @pytest.mark.parametrize("hour", [1, 2, 3, 4, 5])
    def test_in_quiet_hours_during_configured_range(self, hour):
        tc = make_controller(quiet_hours=[(1, 6)])
        now = datetime(2024, 1, 1, hour, 0, 0)
        assert tc._in_quiet_hours(now) is True

    @pytest.mark.parametrize("hour", [0, 6, 7, 12, 23])
    def test_not_in_quiet_hours_outside_range(self, hour):
        tc = make_controller(quiet_hours=[(1, 6)])
        now = datetime(2024, 1, 1, hour, 0, 0)
        assert tc._in_quiet_hours(now) is False

    def test_no_quiet_hours_always_allowed(self):
        tc = make_controller(quiet_hours=[])
        for hour in range(24):
            now = datetime(2024, 1, 1, hour, 0, 0)
            assert tc._in_quiet_hours(now) is False

    def test_overnight_quiet_hours(self):
        """Quiet hours spanning midnight, e.g. (22, 6)."""
        tc = make_controller(quiet_hours=[(22, 6)])
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 23, 0)) is True
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 0, 0)) is True
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 5, 0)) is True
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 6, 0)) is False
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 12, 0)) is False
        assert tc._in_quiet_hours(datetime(2024, 1, 1, 21, 0)) is False


# ---------------------------------------------------------------------------
# 13.8 Request log with timestamps
# ---------------------------------------------------------------------------

class TestRequestLog:
    def test_record_request_appends_timestamp(self):
        tc = make_controller()
        now = datetime(2024, 1, 1, 12, 0, 0)
        with patch.object(tc, '_now', return_value=now):
            tc.record_request()
        assert tc.get_request_log() == [now]

    def test_record_request_sets_session_start(self):
        tc = make_controller()
        now = datetime(2024, 1, 1, 12, 0, 0)
        with patch.object(tc, '_now', return_value=now):
            tc.record_request()
        assert tc._session_start == now

    def test_record_request_does_not_reset_session_start(self):
        tc = make_controller()
        first = datetime(2024, 1, 1, 12, 0, 0)
        second = datetime(2024, 1, 1, 12, 5, 0)
        with patch.object(tc, '_now', return_value=first):
            tc.record_request()
        with patch.object(tc, '_now', return_value=second):
            tc.record_request()
        assert tc._session_start == first  # unchanged

    def test_get_request_log_returns_copy(self):
        tc = make_controller()
        log = tc.get_request_log()
        log.append(datetime.now())
        assert tc.get_request_log() == []  # original unaffected

    def test_multiple_requests_logged(self):
        tc = make_controller()
        times = [datetime(2024, 1, 1, 12, i, 0) for i in range(5)]
        for t in times:
            with patch.object(tc, '_now', return_value=t):
                tc.record_request()
        assert tc.get_request_log() == times


# ---------------------------------------------------------------------------
# Integration: full flow
# ---------------------------------------------------------------------------

class TestIntegrationFlow:
    @pytest.mark.asyncio
    async def test_permission_denied_then_granted_after_window(self):
        """Simulate hourly limit hit, then window resets."""
        tc = make_controller(hourly_limit=2, daily_limit=100, quiet_hours=[])
        base = datetime(2024, 1, 1, 12, 0, 0)

        # Fill hourly limit
        tc._request_log = [base - timedelta(minutes=30)] * 2

        with patch.object(tc, '_now', return_value=base):
            assert await tc.check_permission() is False

        # Advance time past the window
        future = base + timedelta(hours=1, seconds=1)
        with patch.object(tc, '_now', return_value=future):
            assert await tc.check_permission() is True

    @pytest.mark.asyncio
    async def test_record_then_check_permission(self):
        tc = make_controller(hourly_limit=3, daily_limit=100, quiet_hours=[])
        now = datetime(2024, 1, 1, 12, 0, 0)

        with patch.object(tc, '_now', return_value=now):
            tc.record_request()
            tc.record_request()
            assert await tc.check_permission() is True
            tc.record_request()
            assert await tc.check_permission() is False
