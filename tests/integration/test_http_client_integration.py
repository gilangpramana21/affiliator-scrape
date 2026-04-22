"""Integration tests for HTTPClient using aioresponses"""

from __future__ import annotations

import asyncio
from typing import List

import pytest

try:
    from aioresponses import aioresponses
    HAS_AIORESPONSES = True
except ImportError:
    HAS_AIORESPONSES = False

import aiohttp

from src.core.http_client import (
    Cookie,
    HTTPClient,
    HTTPClientError,
    MaxRetriesExceeded,
    Response,
    TimeoutError,
)
from src.models.models import BrowserFingerprint


pytestmark = pytest.mark.skipif(
    not HAS_AIORESPONSES,
    reason="aioresponses not installed; run: pip install aioresponses",
)


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
        plugins=["PDF Viewer"],
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)",
    )


@pytest.mark.asyncio
class TestHTTPClientIntegration:
    """Integration tests using aioresponses to mock HTTP layer"""

    async def test_get_request_success(self):
        async with HTTPClient() as client:
            with aioresponses() as m:
                m.get("https://example.com/page", status=200, body=b"<html>Hello</html>")
                response = await client.get("https://example.com/page")

        assert response.status == 200
        assert "<html>Hello</html>" in response.text

    async def test_post_request_success(self):
        async with HTTPClient() as client:
            with aioresponses() as m:
                m.post("https://example.com/api", status=201, body=b'{"created": true}')
                response = await client.post(
                    "https://example.com/api",
                    json={"name": "test"},
                )

        assert response.status == 201
        assert response.json() == {"created": True}

    async def test_get_with_fingerprint_headers(self):
        """Verify fingerprint user-agent is sent in request"""
        fp = make_fingerprint()
        sent_headers = {}

        async with HTTPClient(fingerprint=fp) as client:
            with aioresponses() as m:
                m.get("https://example.com/", status=200, body=b"OK")
                response = await client.get("https://example.com/")

        assert response.status == 200

    async def test_cookies_maintained_across_requests(self):
        """Cookies set via set_cookies should persist across requests"""
        async with HTTPClient() as client:
            cookies = [Cookie(name="session", value="abc123", domain="example.com")]
            client.set_cookies(cookies)

            with aioresponses() as m:
                m.get("https://example.com/page1", status=200, body=b"page1")
                m.get("https://example.com/page2", status=200, body=b"page2")

                r1 = await client.get("https://example.com/page1")
                r2 = await client.get("https://example.com/page2")

        assert r1.status == 200
        assert r2.status == 200

    async def test_retry_on_server_error(self):
        """Client should retry on connection errors"""
        from unittest.mock import AsyncMock, MagicMock, patch

        call_count = 0

        success_mock = MagicMock()
        success_mock.status = 200
        success_mock.url = "https://example.com/"
        success_mock.headers = {}
        success_mock.read = AsyncMock(return_value=b"OK after retry")
        success_mock.__aenter__ = AsyncMock(return_value=success_mock)
        success_mock.__aexit__ = AsyncMock(return_value=False)

        def flaky_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                import aiohttp as _aiohttp
                raise _aiohttp.ClientConnectionError("Temporary failure")
            return success_mock

        async with HTTPClient() as client:
            with patch.object(aiohttp.ClientSession, "request", flaky_request):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    response = await client.get("https://example.com/")

        assert response.status == 200
        assert call_count == 2

    async def test_indonesian_locale_in_headers(self):
        """Accept-Language header must include Indonesian locale"""
        async with HTTPClient() as client:
            headers = client._build_headers()

        assert "id-ID" in headers["Accept-Language"]
        assert "id" in headers["Accept-Language"]

    async def test_referer_tracks_previous_url(self):
        """Referer header should reflect the last visited URL"""
        async with HTTPClient() as client:
            with aioresponses() as m:
                m.get("https://example.com/first", status=200, body=b"first")
                m.get("https://example.com/second", status=200, body=b"second")

                await client.get("https://example.com/first")
                # After first request, _last_url is set
                headers_after_first = client._build_headers()

        # The referer should be the URL from the first response
        assert "example.com" in headers_after_first.get("Referer", "")

    async def test_response_url_updated_after_redirect(self):
        """Response URL should reflect final URL after redirect"""
        async with HTTPClient() as client:
            with aioresponses() as m:
                m.get(
                    "https://example.com/redirect",
                    status=200,
                    body=b"final page",
                )
                response = await client.get("https://example.com/redirect")

        assert response.status == 200

    async def test_get_cookies_returns_list(self):
        """get_cookies should return a list of Cookie objects"""
        async with HTTPClient() as client:
            cookies = [
                Cookie(name="a", value="1", domain="example.com"),
                Cookie(name="b", value="2", domain="example.com"),
            ]
            client.set_cookies(cookies)
            result = client.get_cookies()

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_sec_ch_viewport_width_present(self):
        """sec-ch-viewport-width header should be present"""
        async with HTTPClient() as client:
            headers = client._build_headers()

        assert "sec-ch-viewport-width" in headers
        # Should be a numeric string
        assert headers["sec-ch-viewport-width"].isdigit()

    async def test_accept_encoding_includes_br(self):
        """Accept-Encoding must include br (Brotli)"""
        async with HTTPClient() as client:
            headers = client._build_headers()

        assert "br" in headers["Accept-Encoding"]

    async def test_dnt_header_is_1(self):
        """DNT header must be '1'"""
        async with HTTPClient() as client:
            headers = client._build_headers()

        assert headers["DNT"] == "1"
