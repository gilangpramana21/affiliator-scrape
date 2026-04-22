"""Traffic controller for managing request volume, quiet hours, and session breaks."""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


@dataclass
class TrafficConfig:
    """Configuration for traffic control limits."""
    hourly_limit: int = 50
    daily_limit: int = 500
    max_session_duration: int = 7200  # 2 hours in seconds
    break_duration_min: int = 900    # 15 minutes in seconds
    break_duration_max: int = 1800   # 30 minutes in seconds
    quiet_hours: List[Tuple[int, int]] = field(default_factory=lambda: [(1, 6)])


class TrafficController:
    """Controls traffic volume, enforces quiet hours, and manages session breaks.

    Tracks requests using rolling windows:
    - Hourly: requests in the last 60 minutes
    - Daily: requests in the last 24 hours

    Enforces quiet hours (no scraping during configured time ranges) and
    mandatory session breaks after max_session_duration is reached.
    """

    def __init__(self, config: TrafficConfig):
        """Initialize with traffic limits.

        Args:
            config: TrafficConfig with all limit settings.
        """
        self.config = config
        # Request log: list of datetime timestamps
        self._request_log: List[datetime] = []
        # Session start time (set on first request or after break)
        self._session_start: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        """Return current datetime. Overridable in tests."""
        return datetime.now()

    def _prune_log(self, now: datetime) -> None:
        """Remove entries older than 24 hours from the request log."""
        cutoff = now - timedelta(hours=24)
        self._request_log = [ts for ts in self._request_log if ts > cutoff]

    def _hourly_count(self, now: datetime) -> int:
        """Count requests in the last 60 minutes."""
        cutoff = now - timedelta(hours=1)
        return sum(1 for ts in self._request_log if ts > cutoff)

    def _daily_count(self, now: datetime) -> int:
        """Count requests in the last 24 hours."""
        cutoff = now - timedelta(hours=24)
        return sum(1 for ts in self._request_log if ts > cutoff)

    def _in_quiet_hours(self, now: datetime) -> bool:
        """Return True if current time falls within any configured quiet-hour range."""
        current_hour = now.hour
        for start, end in self.config.quiet_hours:
            if start <= end:
                # Normal range, e.g. (1, 6) means 01:00–06:00
                if start <= current_hour < end:
                    return True
            else:
                # Overnight range, e.g. (22, 6) means 22:00–06:00
                if current_hour >= start or current_hour < end:
                    return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_permission(self) -> bool:
        """Check if a request is allowed under current limits.

        Returns:
            True if both hourly and daily limits are not exceeded AND
            the current time is not within quiet hours.
        """
        now = self._now()
        self._prune_log(now)

        if self._in_quiet_hours(now):
            return False

        if self._hourly_count(now) >= self.config.hourly_limit:
            return False

        if self._daily_count(now) >= self.config.daily_limit:
            return False

        return True

    async def wait_for_window_reset(self) -> None:
        """Wait until the earliest rate-limit window resets.

        Calculates the time until the oldest request in the current
        hourly window expires, then sleeps for that duration.
        If the daily limit is also exceeded, waits for the daily window.
        """
        now = self._now()
        self._prune_log(now)

        hourly_cutoff = now - timedelta(hours=1)
        daily_cutoff = now - timedelta(hours=24)

        # Find the oldest timestamp that is still within each window
        hourly_requests = sorted(ts for ts in self._request_log if ts > hourly_cutoff)
        daily_requests = sorted(ts for ts in self._request_log if ts > daily_cutoff)

        wait_seconds = 0.0

        if len(hourly_requests) >= self.config.hourly_limit and hourly_requests:
            # Wait until the oldest hourly request falls out of the window
            oldest_hourly = hourly_requests[0]
            expires_at = oldest_hourly + timedelta(hours=1)
            wait_seconds = max(wait_seconds, (expires_at - now).total_seconds())

        if len(daily_requests) >= self.config.daily_limit and daily_requests:
            oldest_daily = daily_requests[0]
            expires_at = oldest_daily + timedelta(hours=24)
            wait_seconds = max(wait_seconds, (expires_at - now).total_seconds())

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    def record_request(self) -> None:
        """Record a request timestamp for rate limiting.

        Also initialises the session start time on the first request
        (or after a break resets it).
        """
        now = self._now()
        self._request_log.append(now)
        if self._session_start is None:
            self._session_start = now

    def should_take_break(self) -> bool:
        """Check if a session break is needed.

        Returns:
            True if the session has been running longer than
            max_session_duration seconds.
        """
        if self._session_start is None:
            return False
        elapsed = (self._now() - self._session_start).total_seconds()
        return elapsed >= self.config.max_session_duration

    async def take_break(self) -> None:
        """Pause for a random duration between break_duration_min and break_duration_max.

        Resets the session start time after the break so the next
        request begins a fresh session.
        """
        duration = random.uniform(
            self.config.break_duration_min,
            self.config.break_duration_max,
        )
        await asyncio.sleep(duration)
        # Reset session so the next request starts a new session window
        self._session_start = None

    def get_request_log(self) -> List[datetime]:
        """Return a copy of the current request log (timestamps).

        Returns:
            List of datetime objects representing recorded requests.
        """
        return list(self._request_log)
