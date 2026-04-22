"""Proxy rotation management for the scraper"""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Literal

import aiohttp

from src.models.config import ProxyConfig

logger = logging.getLogger(__name__)

RotationStrategy = Literal[
    "per_request",
    "per_session",
    "per_n_requests",
    "round_robin",
    "random",
    "least_used",
]

PROXY_VALIDATE_URL = "http://httpbin.org/ip"


@dataclass
class ProxyHealth:
    """Tracks health metrics for a single proxy"""
    proxy: ProxyConfig
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    disabled: bool = False

    @property
    def total_uses(self) -> int:
        return self.success_count + self.failure_count


class ProxyRotator:
    """Manages a pool of proxies and rotates them according to a strategy."""

    def __init__(
        self,
        proxies: List[ProxyConfig],
        strategy: RotationStrategy = "round_robin",
        max_failures: int = 3,
        n_requests: int = 10,
        fallback_to_direct: bool = True,
        validate_url: str = PROXY_VALIDATE_URL,
    ):
        self._strategy = strategy
        self._max_failures = max_failures
        self._n_requests = n_requests
        self._fallback_to_direct = fallback_to_direct
        self._validate_url = validate_url

        # Build health records keyed by proxy identity
        self._health: List[ProxyHealth] = [ProxyHealth(proxy=p) for p in proxies]

        # State for stateful strategies
        self._round_robin_index: int = 0
        self._request_count: int = 0          # total requests served
        self._session_proxy: Optional[ProxyConfig] = None  # per_session current proxy

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _active_health(self) -> List[ProxyHealth]:
        """Return health records for non-disabled proxies."""
        return [h for h in self._health if not h.disabled]

    def _find_health(self, proxy: ProxyConfig) -> Optional[ProxyHealth]:
        """Locate the health record for a given proxy (by identity)."""
        for h in self._health:
            if h.proxy is proxy or (
                h.proxy.host == proxy.host
                and h.proxy.port == proxy.port
                and h.proxy.protocol == proxy.protocol
            ):
                return h
        return None

    def _pick_round_robin(self, active: List[ProxyHealth]) -> Optional[ProxyConfig]:
        if not active:
            return None
        # Map global index into active list
        idx = self._round_robin_index % len(active)
        self._round_robin_index = (idx + 1) % len(active)
        return active[idx].proxy

    def _pick_random(self, active: List[ProxyHealth]) -> Optional[ProxyConfig]:
        if not active:
            return None
        return random.choice(active).proxy

    def _pick_least_used(self, active: List[ProxyHealth]) -> Optional[ProxyConfig]:
        if not active:
            return None
        return min(active, key=lambda h: h.total_uses).proxy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Return the next proxy according to the configured strategy.

        Returns None when all proxies are disabled and fallback_to_direct is True
        (caller should use a direct connection).  Raises RuntimeError when
        fallback_to_direct is False and no proxy is available.
        """
        active = self._active_health()

        if not active:
            if self._fallback_to_direct:
                logger.warning("All proxies disabled – falling back to direct connection")
                return None
            raise RuntimeError("All proxies are disabled and fallback_to_direct is False")

        proxy: Optional[ProxyConfig] = None

        if self._strategy == "per_session":
            # Keep the same proxy until it is marked failed
            if self._session_proxy is not None:
                # Verify the session proxy is still active
                if self._find_health(self._session_proxy) and not self._find_health(self._session_proxy).disabled:  # type: ignore[union-attr]
                    proxy = self._session_proxy
            if proxy is None:
                proxy = self._pick_round_robin(active)
                self._session_proxy = proxy

        elif self._strategy == "per_request":
            proxy = self._pick_round_robin(active)

        elif self._strategy == "per_n_requests":
            # Rotate every n_requests
            if self._session_proxy is None or (self._request_count % self._n_requests == 0):
                proxy = self._pick_round_robin(active)
                self._session_proxy = proxy
            else:
                # Reuse current session proxy if still active
                if self._session_proxy and not self._find_health(self._session_proxy).disabled:  # type: ignore[union-attr]
                    proxy = self._session_proxy
                else:
                    proxy = self._pick_round_robin(active)
                    self._session_proxy = proxy

        elif self._strategy == "round_robin":
            proxy = self._pick_round_robin(active)

        elif self._strategy == "random":
            proxy = self._pick_random(active)

        elif self._strategy == "least_used":
            proxy = self._pick_least_used(active)

        else:
            # Fallback to round-robin for unknown strategies
            proxy = self._pick_round_robin(active)

        if proxy is not None:
            self._request_count += 1
            health = self._find_health(proxy)
            if health:
                health.last_used = datetime.now()

        return proxy

    def mark_failed(self, proxy: ProxyConfig) -> None:
        """Increment failure count; disable proxy when max_failures is reached."""
        health = self._find_health(proxy)
        if health is None:
            logger.warning("mark_failed called for unknown proxy %s:%s", proxy.host, proxy.port)
            return

        health.failure_count += 1
        logger.debug(
            "Proxy %s:%s failure_count=%d", proxy.host, proxy.port, health.failure_count
        )

        if health.failure_count >= self._max_failures:
            health.disabled = True
            logger.warning(
                "Proxy %s:%s disabled after %d failures",
                proxy.host,
                proxy.port,
                health.failure_count,
            )

        # If this was the session proxy, clear it so a new one is chosen next time
        if self._session_proxy is not None and (
            self._session_proxy is proxy
            or (
                self._session_proxy.host == proxy.host
                and self._session_proxy.port == proxy.port
            )
        ):
            self._session_proxy = None

    def mark_success(self, proxy: ProxyConfig) -> None:
        """Increment success count and reset failure count."""
        health = self._find_health(proxy)
        if health is None:
            logger.warning("mark_success called for unknown proxy %s:%s", proxy.host, proxy.port)
            return

        health.success_count += 1
        health.failure_count = 0
        logger.debug(
            "Proxy %s:%s success_count=%d", proxy.host, proxy.port, health.success_count
        )

    async def validate_proxy(self, proxy: ProxyConfig) -> bool:
        """Test proxy connectivity by making a simple HTTP request.

        Returns True if the proxy responds successfully, False otherwise.
        """
        proxy_url = proxy.to_url()
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    self._validate_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as exc:
            logger.debug("Proxy validation failed for %s:%s – %s", proxy.host, proxy.port, exc)
            return False
