"""Integration tests for BrowserEngine (mocked Playwright)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from src.anti_detection.browser_engine import BrowserEngine
from src.models.models import BrowserFingerprint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_fingerprint() -> BrowserFingerprint:
    return BrowserFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.6099.130 Safari/537.36",
        platform="Win32",
        browser="Chrome",
        browser_version="120",
        screen_resolution=(1920, 1080),
        viewport_size=(1920, 960),
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
        plugins=["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        webgl_vendor="Google Inc. (Intel)",
        webgl_renderer='ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
    )


def _make_mock_playwright():
    """Build a minimal mock Playwright stack."""
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body>Hello</body></html>")
    mock_page.goto = AsyncMock()
    mock_page.mouse = AsyncMock()
    mock_page.evaluate = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.add_init_script = AsyncMock()
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium
    mock_pw.stop = AsyncMock()

    return mock_pw, mock_browser, mock_context, mock_page


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBrowserEngineInit:
    def test_default_engine_type(self):
        engine = BrowserEngine()
        assert engine._engine_type == "playwright"

    def test_explicit_playwright_engine(self):
        engine = BrowserEngine("playwright")
        assert engine._engine_type == "playwright"

    def test_unsupported_engine_raises(self):
        with pytest.raises(ValueError, match="playwright"):
            BrowserEngine("puppeteer")  # type: ignore


class TestLaunch:
    @pytest.mark.asyncio
    async def test_launch_returns_browser(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            result = await engine.launch(sample_fingerprint)

            assert result is mock_browser

    @pytest.mark.asyncio
    async def test_launch_applies_user_agent(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            call_kwargs = mock_browser.new_context.call_args.kwargs
            assert call_kwargs["user_agent"] == sample_fingerprint.user_agent

    @pytest.mark.asyncio
    async def test_launch_applies_viewport(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            call_kwargs = mock_browser.new_context.call_args.kwargs
            w, h = sample_fingerprint.viewport_size
            assert call_kwargs["viewport"] == {"width": w, "height": h}

    @pytest.mark.asyncio
    async def test_launch_applies_timezone(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            call_kwargs = mock_browser.new_context.call_args.kwargs
            assert call_kwargs["timezone_id"] == sample_fingerprint.timezone

    @pytest.mark.asyncio
    async def test_launch_injects_stealth_scripts(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            # Should have called add_init_script multiple times (one per stealth patch)
            assert mock_context.add_init_script.call_count >= 5

    @pytest.mark.asyncio
    async def test_launch_includes_sec_ch_ua_headers(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            call_kwargs = mock_browser.new_context.call_args.kwargs
            headers = call_kwargs.get("extra_http_headers", {})
            assert "sec-ch-ua" in headers
            assert headers["sec-ch-ua"] == sample_fingerprint.sec_ch_ua


class TestNavigate:
    @pytest.mark.asyncio
    async def test_navigate_returns_page(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            page = await engine.navigate("https://example.com")

            assert page is mock_page

    @pytest.mark.asyncio
    async def test_navigate_default_wait_networkidle(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.navigate("https://example.com")

            mock_page.goto.assert_called_once()
            call_kwargs = mock_page.goto.call_args.kwargs
            assert call_kwargs["wait_until"] == "networkidle"

    @pytest.mark.asyncio
    async def test_navigate_wait_domcontentloaded(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.navigate("https://example.com", wait_for="domcontentloaded")

            call_kwargs = mock_page.goto.call_args.kwargs
            assert call_kwargs["wait_until"] == "domcontentloaded"

    @pytest.mark.asyncio
    async def test_navigate_wait_load(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.navigate("https://example.com", wait_for="load")

            call_kwargs = mock_page.goto.call_args.kwargs
            assert call_kwargs["wait_until"] == "load"

    @pytest.mark.asyncio
    async def test_navigate_without_launch_raises(self):
        engine = BrowserEngine()
        with pytest.raises(RuntimeError, match="launch"):
            await engine.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_navigate_passes_url(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.navigate("https://affiliate.tokopedia.com/creator")

            call_args = mock_page.goto.call_args
            assert call_args.args[0] == "https://affiliate.tokopedia.com/creator"


class TestGetHtml:
    @pytest.mark.asyncio
    async def test_get_html_returns_content(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()
        expected_html = "<html><body><h1>Test</h1></body></html>"
        mock_page.content = AsyncMock(return_value=expected_html)

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            html = await engine.get_html(mock_page)

            assert html == expected_html

    @pytest.mark.asyncio
    async def test_get_html_calls_page_content(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, mock_page = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.get_html(mock_page)

            mock_page.content.assert_called_once()


class TestClose:
    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.close()

            mock_context.close.assert_called_once()
            mock_browser.close.assert_called_once()
            mock_pw.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_resets_internal_state(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)
            await engine.close()

            assert engine._browser is None
            assert engine._context is None
            assert engine._playwright is None


class TestStealthPatches:
    """Verify that the correct stealth init scripts are injected."""

    @pytest.mark.asyncio
    async def test_webdriver_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            assert "navigator.webdriver" in combined

    @pytest.mark.asyncio
    async def test_chrome_runtime_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            assert "chrome.runtime" in combined

    @pytest.mark.asyncio
    async def test_canvas_noise_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            assert "toDataURL" in combined

    @pytest.mark.asyncio
    async def test_webgl_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            assert "WebGLRenderingContext" in combined
            # Vendor and renderer values should appear in the injected script
            assert sample_fingerprint.webgl_vendor in combined

    @pytest.mark.asyncio
    async def test_audio_noise_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            assert "AudioBuffer" in combined

    @pytest.mark.asyncio
    async def test_languages_patch_injected(self, sample_fingerprint):
        mock_pw, mock_browser, mock_context, _ = _make_mock_playwright()

        with patch("src.anti_detection.browser_engine.async_playwright") as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=mock_pw)

            engine = BrowserEngine()
            await engine.launch(sample_fingerprint)

            scripts = [
                call.args[0] if call.args else ""
                for call in mock_context.add_init_script.call_args_list
            ]
            combined = "\n".join(scripts)
            # The languages patch defines navigator 'languages' property
            assert "languages" in combined and "navigator" in combined
