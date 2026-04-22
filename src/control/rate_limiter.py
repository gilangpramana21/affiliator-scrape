"""Rate limiter for controlling request frequency with jitter."""

import asyncio
import random


class RateLimiter:
    """Controls request frequency with configurable delay range and jitter."""

    def __init__(self, min_delay: float, max_delay: float, jitter: float = 0.2):
        """Initialize rate limiter with delay range and jitter.

        Args:
            min_delay: Minimum delay in seconds between requests.
            max_delay: Maximum delay in seconds between requests.
            jitter: Fractional jitter applied to base delay (default ±20%).
        """
        self._initial_min_delay = min_delay
        self._initial_max_delay = max_delay
        self._initial_jitter = jitter

        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter = jitter

    async def wait(self):
        """Wait for the appropriate delay before the next request."""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        jitter_amount = base_delay * random.uniform(-self.jitter, self.jitter)
        actual_delay = max(0.0, base_delay + jitter_amount)
        await asyncio.sleep(actual_delay)

    def adjust_delay(self, factor: float):
        """Adjust both min and max delay by a multiplicative factor.

        Args:
            factor: Multiplier for the delay (e.g. 1.5 to slow down).
        """
        self.min_delay *= factor
        self.max_delay *= factor

    def reset(self):
        """Reset min_delay and max_delay to the values set at initialisation."""
        self.min_delay = self._initial_min_delay
        self.max_delay = self._initial_max_delay
        self.jitter = self._initial_jitter
