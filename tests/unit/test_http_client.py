"""Unit tests for HTTPClient"""

from __future__ import annotations

import asyncio
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import aiohttp

from src.core.http_client import (
    Cookie,
    HTTPClient,
    HTTPClientError,
    MaxRetriesExceeded,
    Response,
    TimeoutError,
    USER_AGENTS,
)
from src.models.config import ProxyConfig
from src.models.models import BrowserFingerprint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_fingerprint() -> BrowserFingerprint:
    return BrowserFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        platform="Windows",
        browser="Chrome",
        browser_version="120.0.0.0",
        screen_resolution=(1920, 1080),
        viewport_size=(1280, 720),
        timezone="Asia/Jakarta",
        timezone_offset=-420,
        language="id-ID",
        languages=["id-ID", "id", "en-US", "en"],
        color_depth=24,
        pixel_ratio=1.0,
        hardware_concurrency=8,
        device_memory=8,
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        sec_ch_ua_mobile="?0",
        sec_ch_ua_platform='"Windows"',
        plugins=["PDF Viewer", "Chrome PDF Viewer"],
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)",
    )


def make_proxy() -> ProxyConfig:
    return ProxyConfig(protocol="http", host="127.0.0.1", port=8080)


# ---------------------------------------------------------------------------
# Response dataclass tests
# ---------------------------------------------------------------------------

class TestResponse:
    def test_json_parses_text(self):
        resp = Response(
            status=200,
            url="https://example.com",
            headers={},
            body=b'{"key": "value"}',
            text='{"key": "value"}',
        )
        assert resp.json() == {"key": "value"}

    def test_json_returns_cached_data(self):
        resp = Response(
            status=200,
            url="https://example.com",
            headers={},
            body=b"",
            text="",
            json_data={"cached": True},
        )
        assert resp.json() == {"cached": True}


# ---------------------------------------------------------------------------
# Cookie dataclass tests
# ---------------------------------------------------------------------------

class TestCookie:
    def test_defaults(self):
        c = Cookie(name="session", value="abc123")
        assert c.domain == ""
        assert c.path == "/"
        assert c.secure is False
        assert c.http_only is False
        assert c.expires is None

    def test_full_cookie(self):
        c = Cookie(
            name="token",
            value="xyz",
            domain="tokopedia.com",
            path="/",
            secure=True,
            http_only=True,
            expires=9999999999,
        )
        assert c.name == "token"
        assert c.domain == "tokopedia.com"
        assert c.secure is True


# ---------------------------------------------------------------------------
# HTTPClient initialization tests
# ---------------------------------------------------------------------------

class TestHTTPClientInit:
    def test_default_init(self):
        client = HTTPClient()
        assert client._fingerprint is None
        assert client._proxy is None
        assert client._cookies == []
        assert client._session is None

    def test_init_with_fingerprint(self):
        fp = make_fingerprint()
        client = HTTPClient(fingerprint=fp)
        assert client._fingerprint is fp

    def test_init_with_proxy(self):
        proxy = make_proxy()
        client = HTTPClient(proxy=proxy)
        assert client._proxy is proxy

    def test_constants(self):
        assert HTTPClient.TIMEOUT_SECONDS == 30
        assert HTTPClient.MAX_RETRIES == 3
        assert HTTPClient.MAX_REDIRECTS == 5


# ---------------------------------------------------------------------------
# Header building tests
# ---------------------------------------------------------------------------

class TestBuildHeaders:
    def test_headers_contain_required_keys(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "Connection" in headers
        assert "DNT" in headers

    def test_accept_language_has_indonesian_locale(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert "id-ID" in headers["Accept-Language"]
        assert "id" in headers["Accept-Language"]

    def test_accept_encoding_has_br(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert "br" in headers["Accept-Encoding"]
        assert "gzip" in headers["Accept-Encoding"]

    def test_connection_keep_alive(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert headers["Connection"] == "keep-alive"

    def test_dnt_is_1(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert headers["DNT"] == "1"

    def test_fingerprint_user_agent_used(self):
        fp = make_fingerprint()
        client = HTTPClient(fingerprint=fp)
        headers = client._build_headers()
        assert headers["User-Agent"] == fp.user_agent

    def test_fingerprint_sec_ch_ua_used(self):
        fp = make_fingerprint()
        client = HTTPClient(fingerprint=fp)
        headers = client._build_headers()
        assert headers["sec-ch-ua"] == fp.sec_ch_ua
        assert headers["sec-ch-ua-mobile"] == fp.sec_ch_ua_mobile
        assert headers["sec-ch-ua-platform"] == fp.sec_ch_ua_platform

    def test_viewport_width_from_fingerprint(self):
        fp = make_fingerprint()
        client = HTTPClient(fingerprint=fp)
        headers = client._build_headers()
        assert headers["sec-ch-viewport-width"] == str(fp.viewport_size[0])

    def test_extra_headers_merged(self):
        client = HTTPClient()
        headers = client._build_headers({"X-Custom": "test-value"})
        assert headers["X-Custom"] == "test-value"

    def test_extra_headers_override_defaults(self):
        client = HTTPClient()
        headers = client._build_headers({"Accept": "application/json"})
        assert headers["Accept"] == "application/json"

    def test_referer_uses_last_url(self):
        client = HTTPClient()
        client._last_url = "https://tokopedia.com/previous-page"
        headers = client._build_headers()
        assert headers["Referer"] == "https://tokopedia.com/previous-page"

    def test_referer_default_when_no_last_url(self):
        client = HTTPClient()
        headers = client._build_headers()
        assert "Referer" in headers

    def test_user_agent_rotates_without_fingerprint(self):
        """Without fingerprint, user agent should be from USER_AGENTS list"""
        client = HTTPClient()
        ua = client._build_headers()["User-Agent"]
        assert ua in USER_AGENTS


# ---------------------------------------------------------------------------
# Proxy URL tests
# ---------------------------------------------------------------------------

class TestProxyUrl:
    def test_no_proxy_returns_none(self):
        client = HTTPClient()
        assert client._get_proxy_url() is None

    def test_proxy_returns_url(self):
        proxy = ProxyConfig(protocol="http", host="proxy.example.com", port=3128)
        client = HTTPClient(proxy=proxy)
        assert client._get_proxy_url() == "http://proxy.example.com:3128"

    def test_proxy_with_auth(self):
        proxy = ProxyConfig(
            protocol="socks5",
            host="proxy.example.com",
            port=1080,
            username="user",
            password="pass",
        )
        client = HTTPClient(proxy=proxy)
        assert client._get_proxy_url() == "socks5://user:pass@proxy.example.com:1080"


# ---------------------------------------------------------------------------
# Cookie management tests
# ---------------------------------------------------------------------------

class TestCookieManagement:
    def test_set_and_get_cookies(self):
        client = HTTPClient()
        cookies = [
            Cookie(name="session_id", value="abc123", domain="tokopedia.com"),
            Cookie(name="user_token", value="xyz789", domain="tokopedia.com"),
        ]
        client.set_cookies(cookies)
        result = client.get_cookies()
        assert len(result) == 2
        names = {c.name for c in result}
        assert "session_id" in names
        assert "user_token" in names

    def test_get_cookies_returns_copy(self):
        client = HTTPClient()
        cookies = [Cookie(name="a", value="1")]
        client.set_cookies(cookies)
        result = client.get_cookies()
        result.append(Cookie(name="b", value="2"))
        # Internal list should not be modified
        assert len(client.get_cookies()) == 1

    def test_set_cookies_replaces_existing(self):
        client = HTTPClient()
        client.set_cookies([Cookie(name="old", value="old_val")])
        client.set_cookies([Cookie(name="new", value="new_val")])
        result = client.get_cookies()
        assert len(result) == 1
        assert result[0].name == "new"

    def test_initial_cookies_empty(self):
        client = HTTPClient()
        assert client.get_cookies() == []


# ---------------------------------------------------------------------------
# GET / POST request tests (mocked)
# ---------------------------------------------------------------------------

def _make_cm_mock(status: int = 200, body: bytes = b"OK", headers: dict = None):
    """Create a mock that works as an async context manager for session.request()"""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.url = "https://example.com/result"
    mock_resp.headers = headers or {"Content-Type": "text/html"}
    mock_resp.read = AsyncMock(return_value=body)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    # session.request() must return the context manager directly (not a coroutine)
    request_mock = MagicMock(return_value=mock_resp)
    return request_mock, mock_resp


@pytest.mark.asyncio
class TestGetRequest:
    async def test_get_returns_response(self):
        client = HTTPClient()
        request_mock, _ = _make_cm_mock(200, b"<html>Hello</html>")

        with patch.object(aiohttp.ClientSession, "request", request_mock):
            response = await client.get("https://example.com")

        assert response.status == 200
        assert response.text == "<html>Hello</html>"
        await client.close()

    async def test_get_updates_last_url(self):
        client = HTTPClient()
        request_mock, _ = _make_cm_mock(200, b"body")

        with patch.object(aiohttp.ClientSession, "request", request_mock):
            await client.get("https://example.com/page")

        assert client._last_url == "https://example.com/result"
        await client.close()

    async def test_get_passes_extra_headers(self):
        client = HTTPClient()
        request_mock, _ = _make_cm_mock(200, b"body")

        with patch.object(aiohttp.ClientSession, "request", request_mock):
            await client.get("https://example.com", headers={"X-Test": "value"})

        _, call_kwargs = request_mock.call_args
        assert "X-Test" in call_kwargs.get("headers", {})
        await client.close()


@pytest.mark.asyncio
class TestPostRequest:
    async def test_post_returns_response(self):
        client = HTTPClient()
        request_mock, _ = _make_cm_mock(200, b'{"result": "ok"}')

        with patch.object(aiohttp.ClientSession, "request", request_mock):
            response = await client.post("https://example.com/api", data={"key": "value"})

        assert response.status == 200
        await client.close()

    async def test_post_with_json(self):
        client = HTTPClient()
        request_mock, _ = _make_cm_mock(200, b'{"ok": true}')

        with patch.object(aiohttp.ClientSession, "request", request_mock):
            await client.post("https://example.com/api", json={"payload": 1})

        _, call_kwargs = request_mock.call_args
        assert call_kwargs.get("json") == {"payload": 1}
        await client.close()


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRetryLogic:
    async def test_retries_on_connection_error(self):
        client = HTTPClient()
        call_count = 0

        success_mock, _ = _make_cm_mock(200, b"OK")

        def flaky_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientConnectionError("Connection refused")
            return success_mock.return_value

        with patch.object(aiohttp.ClientSession, "request", flaky_request):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("https://example.com")

        assert response.status == 200
        assert call_count == 3
        await client.close()

    async def test_raises_max_retries_exceeded(self):
        client = HTTPClient()

        def always_fail(*args, **kwargs):
            raise aiohttp.ClientConnectionError("Connection refused")

        with patch.object(aiohttp.ClientSession, "request", always_fail):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(MaxRetriesExceeded):
                    await client.get("https://example.com")

        await client.close()

    async def test_exponential_backoff_delays(self):
        client = HTTPClient()
        sleep_calls = []

        def always_fail(*args, **kwargs):
            raise aiohttp.ClientConnectionError("fail")

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch.object(aiohttp.ClientSession, "request", always_fail):
            with patch("asyncio.sleep", mock_sleep):
                with pytest.raises(MaxRetriesExceeded):
                    await client.get("https://example.com")

        # Should sleep 2^0=1, 2^1=2, 2^2=4 between attempts
        assert sleep_calls == [1, 2, 4]
        await client.close()

    async def test_retries_on_429_with_retry_after(self):
        client = HTTPClient()
        call_count = 0
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        mock_429 = MagicMock()
        mock_429.status = 429
        mock_429.url = "https://example.com"
        mock_429.headers = {"Retry-After": "5"}
        mock_429.read = AsyncMock(return_value=b"rate limited")
        mock_429.__aenter__ = AsyncMock(return_value=mock_429)
        mock_429.__aexit__ = AsyncMock(return_value=False)

        mock_200 = MagicMock()
        mock_200.status = 200
        mock_200.url = "https://example.com"
        mock_200.headers = {}
        mock_200.read = AsyncMock(return_value=b"OK")
        mock_200.__aenter__ = AsyncMock(return_value=mock_200)
        mock_200.__aexit__ = AsyncMock(return_value=False)

        def request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_429 if call_count == 1 else mock_200

        with patch.object(aiohttp.ClientSession, "request", request_side_effect):
            with patch("asyncio.sleep", mock_sleep):
                response = await client.get("https://example.com")

        assert response.status == 200
        assert 5 in sleep_calls
        await client.close()

    async def test_raises_timeout_error(self):
        client = HTTPClient()

        def timeout_request(*args, **kwargs):
            raise aiohttp.ServerTimeoutError()

        with patch.object(aiohttp.ClientSession, "request", timeout_request):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(TimeoutError):
                    await client.get("https://example.com")

        await client.close()

    async def test_raises_on_too_many_redirects(self):
        client = HTTPClient()

        def redirect_request(*args, **kwargs):
            raise aiohttp.TooManyRedirects(None, None)

        with patch.object(aiohttp.ClientSession, "request", redirect_request):
            with pytest.raises(HTTPClientError, match="Too many redirects"):
                await client.get("https://example.com")

        await client.close()


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextManager:
    async def test_context_manager_closes_session(self):
        async with HTTPClient() as client:
            assert client._session is None  # not yet created

        # After exit, session should be closed/None
        assert client._session is None

    async def test_context_manager_closes_open_session(self):
        async with HTTPClient() as client:
            # Force session creation
            await client._get_session()
            assert client._session is not None

        assert client._session is None
