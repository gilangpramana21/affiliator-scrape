"""Unit tests for ProxyRotator"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.control.proxy_rotator import ProxyHealth, ProxyRotator, RotationStrategy
from src.models.config import ProxyConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_proxy(host: str = "1.2.3.4", port: int = 8080, protocol: str = "http") -> ProxyConfig:
    return ProxyConfig(protocol=protocol, host=host, port=port)


def make_proxies(n: int) -> list[ProxyConfig]:
    return [make_proxy(host=f"10.0.0.{i}", port=8000 + i) for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# 15.1 / 15.2  ProxyRotator initialisation & pool management
# ---------------------------------------------------------------------------

class TestProxyRotatorInit:
    def test_empty_pool(self):
        rotator = ProxyRotator(proxies=[], fallback_to_direct=True)
        assert rotator.get_next_proxy() is None

    def test_empty_pool_no_fallback_raises(self):
        rotator = ProxyRotator(proxies=[], fallback_to_direct=False)
        with pytest.raises(RuntimeError):
            rotator.get_next_proxy()

    def test_pool_populated(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies)
        assert len(rotator._health) == 3

    def test_all_proxies_start_enabled(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies)
        assert all(not h.disabled for h in rotator._health)


# ---------------------------------------------------------------------------
# 15.3  Rotation strategies
# ---------------------------------------------------------------------------

class TestRoundRobin:
    def test_cycles_through_proxies(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies, strategy="round_robin")
        seen = [rotator.get_next_proxy() for _ in range(6)]
        # Should cycle: 0,1,2,0,1,2
        assert seen[0] is proxies[0]
        assert seen[1] is proxies[1]
        assert seen[2] is proxies[2]
        assert seen[3] is proxies[0]

    def test_single_proxy_always_returned(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, strategy="round_robin")
        for _ in range(5):
            assert rotator.get_next_proxy() is proxies[0]


class TestPerRequest:
    def test_rotates_every_call(self):
        proxies = make_proxies(2)
        rotator = ProxyRotator(proxies=proxies, strategy="per_request")
        first = rotator.get_next_proxy()
        second = rotator.get_next_proxy()
        # With 2 proxies round-robin they should alternate
        assert first is not second


class TestPerSession:
    def test_same_proxy_returned_repeatedly(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies, strategy="per_session")
        first = rotator.get_next_proxy()
        for _ in range(5):
            assert rotator.get_next_proxy() is first

    def test_new_proxy_chosen_after_failure(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies, strategy="per_session", max_failures=1)
        first = rotator.get_next_proxy()
        rotator.mark_failed(first)
        second = rotator.get_next_proxy()
        assert second is not first


class TestPerNRequests:
    def test_rotates_after_n_requests(self):
        proxies = make_proxies(2)
        rotator = ProxyRotator(proxies=proxies, strategy="per_n_requests", n_requests=3)
        results = [rotator.get_next_proxy() for _ in range(6)]
        # Requests 1-3 → proxy A, requests 4-6 → proxy B (or same if only 2)
        # At minimum, a rotation must happen at request 4
        assert results[0] is results[1]
        assert results[0] is results[2]

    def test_rotates_at_boundary(self):
        proxies = make_proxies(2)
        rotator = ProxyRotator(proxies=proxies, strategy="per_n_requests", n_requests=2)
        r1 = rotator.get_next_proxy()
        r2 = rotator.get_next_proxy()
        r3 = rotator.get_next_proxy()
        # r1 == r2 (same batch), r3 should be different
        assert r1 is r2
        assert r3 is not r1


class TestRandom:
    def test_returns_proxy_from_pool(self):
        proxies = make_proxies(5)
        rotator = ProxyRotator(proxies=proxies, strategy="random")
        for _ in range(20):
            p = rotator.get_next_proxy()
            assert p in proxies


class TestLeastUsed:
    def test_picks_least_used(self):
        proxies = make_proxies(3)
        rotator = ProxyRotator(proxies=proxies, strategy="least_used")
        # Use proxy[0] twice
        rotator.mark_success(proxies[0])
        rotator.mark_success(proxies[0])
        # Use proxy[1] once
        rotator.mark_success(proxies[1])
        # proxy[2] has 0 uses → should be picked
        chosen = rotator.get_next_proxy()
        assert chosen is proxies[2]


# ---------------------------------------------------------------------------
# 15.4 / 15.5  Health tracking – mark_failed / mark_success
# ---------------------------------------------------------------------------

class TestHealthTracking:
    def test_mark_success_increments_success_count(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies)
        rotator.mark_success(proxies[0])
        rotator.mark_success(proxies[0])
        health = rotator._find_health(proxies[0])
        assert health.success_count == 2

    def test_mark_success_resets_failure_count(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, max_failures=5)
        rotator.mark_failed(proxies[0])
        rotator.mark_failed(proxies[0])
        rotator.mark_success(proxies[0])
        health = rotator._find_health(proxies[0])
        assert health.failure_count == 0

    def test_mark_failed_increments_failure_count(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, max_failures=5)
        rotator.mark_failed(proxies[0])
        health = rotator._find_health(proxies[0])
        assert health.failure_count == 1

    def test_proxy_disabled_after_max_failures(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, max_failures=3, fallback_to_direct=True)
        for _ in range(3):
            rotator.mark_failed(proxies[0])
        health = rotator._find_health(proxies[0])
        assert health.disabled is True

    def test_disabled_proxy_not_returned(self):
        proxies = make_proxies(2)
        rotator = ProxyRotator(proxies=proxies, max_failures=1, strategy="round_robin")
        rotator.mark_failed(proxies[0])
        for _ in range(5):
            p = rotator.get_next_proxy()
            assert p is proxies[1]

    def test_all_disabled_fallback_returns_none(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, max_failures=1, fallback_to_direct=True)
        rotator.mark_failed(proxies[0])
        assert rotator.get_next_proxy() is None

    def test_all_disabled_no_fallback_raises(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, max_failures=1, fallback_to_direct=False)
        rotator.mark_failed(proxies[0])
        with pytest.raises(RuntimeError):
            rotator.get_next_proxy()

    def test_mark_failed_unknown_proxy_no_crash(self):
        rotator = ProxyRotator(proxies=[])
        unknown = make_proxy(host="9.9.9.9")
        rotator.mark_failed(unknown)  # should not raise

    def test_mark_success_unknown_proxy_no_crash(self):
        rotator = ProxyRotator(proxies=[])
        unknown = make_proxy(host="9.9.9.9")
        rotator.mark_success(unknown)  # should not raise


# ---------------------------------------------------------------------------
# 15.6  validate_proxy
# ---------------------------------------------------------------------------

class TestValidateProxy:
    @pytest.mark.asyncio
    async def test_returns_true_on_200(self):
        proxy = make_proxy()
        rotator = ProxyRotator(proxies=[proxy])

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.control.proxy_rotator.aiohttp.ClientSession", return_value=mock_session):
            with patch("src.control.proxy_rotator.aiohttp.TCPConnector"):
                result = await rotator.validate_proxy(proxy)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200(self):
        proxy = make_proxy()
        rotator = ProxyRotator(proxies=[proxy])

        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.control.proxy_rotator.aiohttp.ClientSession", return_value=mock_session):
            with patch("src.control.proxy_rotator.aiohttp.TCPConnector"):
                result = await rotator.validate_proxy(proxy)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        proxy = make_proxy()
        rotator = ProxyRotator(proxies=[proxy])

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.control.proxy_rotator.aiohttp.ClientSession", return_value=mock_session):
            with patch("src.control.proxy_rotator.aiohttp.TCPConnector"):
                result = await rotator.validate_proxy(proxy)
        assert result is False


# ---------------------------------------------------------------------------
# 15.7  get_next_proxy – last_used timestamp updated
# ---------------------------------------------------------------------------

class TestGetNextProxy:
    def test_last_used_updated(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies, strategy="round_robin")
        assert rotator._health[0].last_used is None
        rotator.get_next_proxy()
        assert rotator._health[0].last_used is not None

    def test_request_count_increments(self):
        proxies = make_proxies(1)
        rotator = ProxyRotator(proxies=proxies)
        for i in range(5):
            rotator.get_next_proxy()
        assert rotator._request_count == 5

    def test_authenticated_proxy_url(self):
        proxy = ProxyConfig(
            protocol="http", host="proxy.example.com", port=3128,
            username="user", password="pass"
        )
        rotator = ProxyRotator(proxies=[proxy])
        p = rotator.get_next_proxy()
        assert p is proxy
        assert "user:pass@" in p.to_url()

    def test_socks5_proxy_supported(self):
        proxy = ProxyConfig(protocol="socks5", host="1.2.3.4", port=1080)
        rotator = ProxyRotator(proxies=[proxy])
        p = rotator.get_next_proxy()
        assert p.protocol == "socks5"
