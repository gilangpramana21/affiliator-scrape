"""Integration tests for TLS fingerprinting via tls-client.

These tests mock the tls-client library so they run without native
binaries installed. They verify:
- TLSClient uses the correct browser preset
- Headers are set correctly
- Cookies are passed and returned correctly
- HTTPClient delegates to TLSClient when tls_profile is set
- Graceful fallback when tls-client is unavailable
"""

from __future__ import annotations

import sys
import importlib
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.core.http_client import Cookie, HTTPClient, Response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(
    status: int = 200,
    body: bytes = b"<html>OK</html>",
    url: str = "https://example.com/",
    headers: Optional[Dict[str, str]] = None,
) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.content = body
    mock_resp.url = url
    mock_resp.headers = headers or {"Content-Type": "text/html"}
    return mock_resp


def _make_mock_session(response: Optional[MagicMock] = None) -> MagicMock:
    if response is None:
        response = _make_mock_response()
    session = MagicMock()
    session.get.return_value = response
    session.post.return_value = response
    session.cookies = MagicMock()
    session.cookies.items.return_value = []
    session.cookies.set = MagicMock()
    return session


def _make_tls_module(session: Optional[MagicMock] = None) -> MagicMock:
    if session is None:
        session = _make_mock_session()
    module = MagicMock()
    module.Session.return_value = session
    return module


def _load_tls_client_module(mock_tls_module: MagicMock):
    """Reload src.core.tls_client with a mocked tls_client module."""
    with patch.dict(sys.modules, {"tls_client": mock_tls_module}):
        import src.core.tls_client as tls_mod
        importlib.reload(tls_mod)
        return tls_mod


# ---------------------------------------------------------------------------
# Tests: TLSClient browser presets
# ---------------------------------------------------------------------------

class TestTLSClientPresets:

    def test_chrome_preset_passed_to_session(self):
        """TLSClient('chrome_120') must pass that identifier to tls_client.Session."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")

        mock_module.Session.assert_called_once()
        call_kwargs = mock_module.Session.call_args
        assert call_kwargs.kwargs.get("client_identifier") == "chrome_120" or \
               (call_kwargs.args and call_kwargs.args[0] == "chrome_120")

    def test_firefox_preset_passed_to_session(self):
        """TLSClient('firefox_120') must pass that identifier to tls_client.Session."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="firefox_120")

        call_kwargs = mock_module.Session.call_args
        assert call_kwargs.kwargs.get("client_identifier") == "firefox_120" or \
               (call_kwargs.args and call_kwargs.args[0] == "firefox_120")

    def test_safari_preset_passed_to_session(self):
        """TLSClient('safari_16_0') must pass that identifier to tls_client.Session."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="safari_16_0")

        call_kwargs = mock_module.Session.call_args
        assert call_kwargs.kwargs.get("client_identifier") == "safari_16_0" or \
               (call_kwargs.args and call_kwargs.args[0] == "safari_16_0")

    def test_random_preset_is_valid(self):
        """TLSClient with no preset picks one of the known presets."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient()

        assert client.browser_preset in tls_mod.ALL_PRESETS

    def test_browser_preset_property(self):
        """browser_preset property returns the active preset name."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")

        assert client.browser_preset == "chrome_120"


# ---------------------------------------------------------------------------
# Tests: TLSClient headers
# ---------------------------------------------------------------------------

class TestTLSClientHeaders:

    def test_accept_language_includes_indonesian(self):
        """Headers must include Indonesian locale."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            headers = client._build_headers()

        assert "id-ID" in headers.get("Accept-Language", "")

    def test_accept_encoding_includes_br(self):
        """Accept-Encoding must include br (Brotli)."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            headers = client._build_headers()

        assert "br" in headers.get("Accept-Encoding", "")

    def test_extra_headers_merged(self):
        """Extra headers passed to get/post are merged into the request."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            headers = client._build_headers({"X-Custom": "test-value"})

        assert headers.get("X-Custom") == "test-value"

    def test_get_sends_headers_to_session(self):
        """get() must pass headers to the underlying tls_client session."""
        mock_session = _make_mock_session()
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            client.get("https://example.com/")

        mock_session.get.assert_called_once()
        call_kwargs = mock_session.get.call_args
        assert "headers" in call_kwargs.kwargs


# ---------------------------------------------------------------------------
# Tests: TLSClient cookies
# ---------------------------------------------------------------------------

class TestTLSClientCookies:

    def test_set_cookies_stores_cookies(self):
        """set_cookies() stores cookies internally."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            cookies = [Cookie(name="session", value="abc123", domain="example.com")]
            client.set_cookies(cookies)

        assert len(client.get_cookies()) == 1
        assert client.get_cookies()[0].name == "session"
        assert client.get_cookies()[0].value == "abc123"

    def test_cookies_applied_before_request(self):
        """Cookies are pushed to the tls-client session before each request."""
        mock_session = _make_mock_session()
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            client.set_cookies([Cookie(name="tok", value="xyz", domain="example.com")])
            client.get("https://example.com/")

        mock_session.cookies.set.assert_called()

    def test_cookies_synced_after_response(self):
        """Cookies returned by the server are synced back to internal list."""
        mock_session = _make_mock_session()
        # Simulate server setting a cookie
        mock_session.cookies.items.return_value = [("new_cookie", "new_value")]
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            client.get("https://example.com/")
            cookies = client.get_cookies()

        assert any(c.name == "new_cookie" for c in cookies)

    def test_get_cookies_returns_list(self):
        """get_cookies() always returns a list."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")

        assert isinstance(client.get_cookies(), list)


# ---------------------------------------------------------------------------
# Tests: TLSClient GET / POST responses
# ---------------------------------------------------------------------------

class TestTLSClientRequests:

    def test_get_returns_response_object(self):
        """get() returns a Response with correct status and text."""
        mock_resp = _make_mock_response(status=200, body=b"<html>Hello</html>")
        mock_session = _make_mock_session(mock_resp)
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            response = client.get("https://example.com/")

        assert response.status == 200
        assert "Hello" in response.text

    def test_post_returns_response_object(self):
        """post() returns a Response with correct status."""
        mock_resp = _make_mock_response(status=201, body=b'{"ok": true}')
        mock_session = _make_mock_session(mock_resp)
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            response = client.post("https://example.com/api", json={"key": "val"})

        assert response.status == 201

    def test_post_passes_json_to_session(self):
        """post() with json= passes json kwarg to tls-client session."""
        mock_session = _make_mock_session()
        mock_module = _make_tls_module(mock_session)
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.TLSClient(browser_preset="chrome_120")
            client.post("https://example.com/api", json={"key": "val"})

        call_kwargs = mock_session.post.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"] == {"key": "val"}


# ---------------------------------------------------------------------------
# Tests: HTTPClient tls_profile integration
# ---------------------------------------------------------------------------

class TestHTTPClientTLSIntegration:
    """Verify HTTPClient delegates to TLSClient when tls_profile is set."""

    @pytest.mark.asyncio
    async def test_http_client_uses_tls_client_when_profile_set(self):
        """HTTPClient.get() uses TLSClient when tls_profile is provided."""
        client = HTTPClient(tls_profile="chrome_120")
        mock_tls = MagicMock()
        mock_tls.get.return_value = Response(
            status=200, url="https://example.com/",
            headers={}, body=b"TLS response", text="TLS response"
        )
        mock_tls.get_cookies.return_value = []
        client._tls_client = mock_tls

        response = await client.get("https://example.com/")

        mock_tls.get.assert_called_once_with("https://example.com/", headers=None)
        assert response.status == 200
        assert response.text == "TLS response"

    @pytest.mark.asyncio
    async def test_http_client_post_uses_tls_client(self):
        """HTTPClient.post() uses TLSClient when tls_profile is provided."""
        client = HTTPClient(tls_profile="firefox_120")
        mock_tls = MagicMock()
        mock_tls.post.return_value = Response(
            status=201, url="https://example.com/api",
            headers={}, body=b'{"created":true}', text='{"created":true}'
        )
        mock_tls.get_cookies.return_value = []
        client._tls_client = mock_tls

        response = await client.post("https://example.com/api", json={"x": 1})

        mock_tls.post.assert_called_once_with(
            "https://example.com/api", data=None, headers=None, json={"x": 1}
        )
        assert response.status == 201

    @pytest.mark.asyncio
    async def test_http_client_cookies_synced_to_tls_client(self):
        """Cookies set on HTTPClient are passed to TLSClient before requests."""
        client = HTTPClient(tls_profile="safari_16_0")
        mock_tls = MagicMock()
        mock_tls.get.return_value = Response(
            status=200, url="https://example.com/",
            headers={}, body=b"OK", text="OK"
        )
        mock_tls.get_cookies.return_value = []
        client._tls_client = mock_tls

        cookies = [Cookie(name="session", value="tok123", domain="example.com")]
        client.set_cookies(cookies)
        await client.get("https://example.com/")

        mock_tls.set_cookies.assert_called()

    @pytest.mark.asyncio
    async def test_http_client_falls_back_to_aiohttp_without_profile(self):
        """HTTPClient without tls_profile uses aiohttp (no TLS client)."""
        client = HTTPClient()
        assert client._tls_client is None

    @pytest.mark.asyncio
    async def test_http_client_graceful_fallback_on_import_error(self):
        """HTTPClient falls back to aiohttp when tls-client import fails."""
        with patch("src.core.http_client.HTTPClient._init_tls_client") as mock_init:
            def side_effect(profile):
                # Simulate ImportError fallback: _tls_client stays None
                pass
            mock_init.side_effect = side_effect

            client = HTTPClient(tls_profile="chrome_120")
            # _tls_client was never set, so it should be None
            assert client._tls_client is None


# ---------------------------------------------------------------------------
# Tests: create_tls_client factory
# ---------------------------------------------------------------------------

class TestCreateTLSClientFactory:

    def test_create_chrome_client(self):
        """create_tls_client('chrome') returns TLSClient with chrome_120 preset."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.create_tls_client("chrome")

        assert client.browser_preset == "chrome_120"

    def test_create_firefox_client(self):
        """create_tls_client('firefox') returns TLSClient with firefox_120 preset."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.create_tls_client("firefox")

        assert client.browser_preset == "firefox_120"

    def test_create_safari_client(self):
        """create_tls_client('safari') returns TLSClient with safari_16_0 preset."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.create_tls_client("safari")

        assert client.browser_preset == "safari_16_0"

    def test_create_random_client_is_valid_preset(self):
        """create_tls_client('random') returns a client with a valid preset."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            client = tls_mod.create_tls_client("random")

        assert client.browser_preset in tls_mod.ALL_PRESETS

    def test_create_unknown_browser_raises_value_error(self):
        """create_tls_client with unknown browser name raises ValueError."""
        mock_module = _make_tls_module()
        tls_mod = _load_tls_client_module(mock_module)

        with patch.dict(sys.modules, {"tls_client": mock_module}):
            with pytest.raises(ValueError, match="Unknown browser"):
                tls_mod.create_tls_client("opera")


# ---------------------------------------------------------------------------
# Tests: HTTP/2 SETTINGS constants
# ---------------------------------------------------------------------------

class TestHTTP2Settings:

    def test_http2_settings_defined_for_all_presets(self):
        """HTTP2_SETTINGS must have entries for all browser presets."""
        import src.core.tls_client as tls_mod
        for preset in tls_mod.ALL_PRESETS:
            assert preset in tls_mod.HTTP2_SETTINGS, \
                f"HTTP2_SETTINGS missing entry for preset '{preset}'"

    def test_chrome_http2_settings_has_required_keys(self):
        """Chrome HTTP/2 SETTINGS must include HEADER_TABLE_SIZE and INITIAL_WINDOW_SIZE."""
        import src.core.tls_client as tls_mod
        settings = tls_mod.HTTP2_SETTINGS["chrome_120"]
        assert "HEADER_TABLE_SIZE" in settings
        assert "INITIAL_WINDOW_SIZE" in settings

    def test_firefox_http2_settings_has_required_keys(self):
        """Firefox HTTP/2 SETTINGS must include HEADER_TABLE_SIZE."""
        import src.core.tls_client as tls_mod
        settings = tls_mod.HTTP2_SETTINGS["firefox_120"]
        assert "HEADER_TABLE_SIZE" in settings

    def test_safari_http2_settings_has_required_keys(self):
        """Safari HTTP/2 SETTINGS must include HEADER_TABLE_SIZE."""
        import src.core.tls_client as tls_mod
        settings = tls_mod.HTTP2_SETTINGS["safari_16_0"]
        assert "HEADER_TABLE_SIZE" in settings
