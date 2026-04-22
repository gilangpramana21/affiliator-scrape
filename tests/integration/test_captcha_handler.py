"""Integration tests for CAPTCHAHandler.

Tests cover:
- CAPTCHA detection (reCAPTCHA v2, v3, hCaptcha, image)
- Manual solving workflow (pause and wait)
- 2Captcha API integration (mocked)
- Anti-Captcha API integration (mocked)
- Exponential backoff after CAPTCHA encounters
- Max-attempt skip behaviour
"""

from __future__ import annotations

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.captcha_handler import (
    MAX_SOLVE_ATTEMPTS,
    CAPTCHAHandler,
    CAPTCHAType,
    _INITIAL_BACKOFF,
    _MAX_BACKOFF,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_page(
    *,
    url: str = "https://example.com",
    html: str = "",
    selector_results: Optional[dict] = None,
) -> MagicMock:
    """Build a mock Playwright Page with configurable behaviour."""
    page = MagicMock()
    page.url = url

    # page.content() returns the HTML string
    page.content = AsyncMock(return_value=html)

    # page.evaluate() returns None by default
    page.evaluate = AsyncMock(return_value=None)

    # page.query_selector() returns None (no element) by default
    _selector_map = selector_results or {}

    async def _query_selector(selector: str):
        return _selector_map.get(selector, None)

    page.query_selector = _query_selector

    # page.context.cookies() returns empty list
    context = MagicMock()
    context.cookies = AsyncMock(return_value=[])
    page.context = context

    return page


# ---------------------------------------------------------------------------
# 17.1 – CAPTCHAHandler initialisation
# ---------------------------------------------------------------------------


class TestCAPTCHAHandlerInit:
    def test_default_solver_is_manual(self):
        handler = CAPTCHAHandler()
        assert handler.solver_type == "manual"

    def test_invalid_solver_raises(self):
        with pytest.raises(ValueError, match="Invalid solver_type"):
            CAPTCHAHandler(solver_type="unknown")

    def test_2captcha_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key is required"):
            CAPTCHAHandler(solver_type="2captcha")

    def test_anticaptcha_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key is required"):
            CAPTCHAHandler(solver_type="anticaptcha")

    def test_valid_2captcha_init(self):
        handler = CAPTCHAHandler(solver_type="2captcha", api_key="test-key")
        assert handler.solver_type == "2captcha"
        assert handler.api_key == "test-key"

    def test_initial_backoff(self):
        handler = CAPTCHAHandler()
        assert handler.backoff_seconds == _INITIAL_BACKOFF

    def test_initial_encounter_count(self):
        handler = CAPTCHAHandler()
        assert handler.captcha_encounter_count == 0


# ---------------------------------------------------------------------------
# 17.2 / 17.3 – reCAPTCHA v2 detection
# ---------------------------------------------------------------------------


class TestDetectReCAPTCHAv2:
    @pytest.mark.asyncio
    async def test_detects_anchor_iframe(self):
        page = _make_page(
            selector_results={'iframe[src*="recaptcha/api2/anchor"]': MagicMock()}
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V2

    @pytest.mark.asyncio
    async def test_detects_g_recaptcha_div(self):
        page = _make_page(selector_results={"div.g-recaptcha": MagicMock()})
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V2

    @pytest.mark.asyncio
    async def test_detects_bframe_iframe(self):
        page = _make_page(
            selector_results={'iframe[src*="recaptcha/api2/bframe"]': MagicMock()}
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V2


# ---------------------------------------------------------------------------
# 17.4 – reCAPTCHA v3 detection
# ---------------------------------------------------------------------------


class TestDetectReCAPTCHAv3:
    @pytest.mark.asyncio
    async def test_detects_api_js_script(self):
        html = '<script src="https://www.google.com/recaptcha/api.js"></script>'
        page = _make_page(html=html)
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V3

    @pytest.mark.asyncio
    async def test_detects_enterprise_js_script(self):
        html = '<script src="https://www.google.com/recaptcha/enterprise.js"></script>'
        page = _make_page(html=html)
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V3

    @pytest.mark.asyncio
    async def test_v3_not_detected_without_script(self):
        page = _make_page(html="<html><body>No captcha here</body></html>")
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result is None


# ---------------------------------------------------------------------------
# 17.5 – hCaptcha detection
# ---------------------------------------------------------------------------


class TestDetectHCaptcha:
    @pytest.mark.asyncio
    async def test_detects_hcaptcha_iframe(self):
        page = _make_page(
            selector_results={'iframe[src*="hcaptcha.com"]': MagicMock()}
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.HCAPTCHA

    @pytest.mark.asyncio
    async def test_detects_h_captcha_div(self):
        page = _make_page(selector_results={"div.h-captcha": MagicMock()})
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.HCAPTCHA


# ---------------------------------------------------------------------------
# Image CAPTCHA detection
# ---------------------------------------------------------------------------


class TestDetectImageCaptcha:
    @pytest.mark.asyncio
    async def test_detects_captcha_img(self):
        page = _make_page(
            selector_results={'img[src*="captcha"]': MagicMock()}
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.IMAGE

    @pytest.mark.asyncio
    async def test_detects_captcha_input(self):
        page = _make_page(
            selector_results={'input[name*="captcha"]': MagicMock()}
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.IMAGE


# ---------------------------------------------------------------------------
# No CAPTCHA
# ---------------------------------------------------------------------------


class TestDetectNoCaptcha:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_captcha(self):
        page = _make_page(html="<html><body>Normal page</body></html>")
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result is None


# ---------------------------------------------------------------------------
# 17.6 – Manual solving workflow
# ---------------------------------------------------------------------------


class TestManualSolving:
    @pytest.mark.asyncio
    async def test_manual_solve_returns_true(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")

        # Patch input() so the test doesn't block waiting for stdin
        with patch("builtins.input", return_value=""):
            result = await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is True

    @pytest.mark.asyncio
    async def test_manual_solve_increments_encounter_count(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")

        with patch("builtins.input", return_value=""):
            await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert handler.captcha_encounter_count == 1

    @pytest.mark.asyncio
    async def test_manual_solve_resets_backoff_on_success(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")
        # Artificially increase backoff
        handler._backoff_seconds = 40.0

        with patch("builtins.input", return_value=""):
            await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert handler.backoff_seconds == _INITIAL_BACKOFF


# ---------------------------------------------------------------------------
# 17.7 – 2Captcha API integration
# ---------------------------------------------------------------------------


class Test2CaptchaSolving:
    @pytest.mark.asyncio
    async def test_2captcha_recaptcha_v2_success(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="2captcha", api_key="fake-key")

        mock_solver_instance = MagicMock()
        mock_solver_instance.recaptcha.return_value = {"code": "solved-token-123"}
        mock_twocaptcha_module = MagicMock()
        mock_twocaptcha_module.TwoCaptcha.return_value = mock_solver_instance

        with patch("src.core.captcha_handler.CAPTCHAHandler._get_recaptcha_site_key",
                   new=AsyncMock(return_value="6Le-test")):
            with patch.dict("sys.modules", {"twocaptcha": mock_twocaptcha_module}):
                result = await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is True

    @pytest.mark.asyncio
    async def test_2captcha_missing_library_returns_false(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="2captcha", api_key="fake-key")

        with patch.dict("sys.modules", {"twocaptcha": None}):
            result = await handler._solve_2captcha(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is False

    @pytest.mark.asyncio
    async def test_2captcha_no_site_key_returns_false(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="2captcha", api_key="fake-key")

        mock_solver_instance = MagicMock()
        mock_twocaptcha_module = MagicMock()
        mock_twocaptcha_module.TwoCaptcha.return_value = mock_solver_instance

        with patch("src.core.captcha_handler.CAPTCHAHandler._get_recaptcha_site_key",
                   new=AsyncMock(return_value=None)):
            with patch.dict("sys.modules", {"twocaptcha": mock_twocaptcha_module}):
                result = await handler._solve_2captcha(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is False

    @pytest.mark.asyncio
    async def test_2captcha_hcaptcha_success(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="2captcha", api_key="fake-key")

        mock_solver_instance = MagicMock()
        mock_solver_instance.hcaptcha.return_value = {"code": "hcaptcha-token"}
        mock_twocaptcha_module = MagicMock()
        mock_twocaptcha_module.TwoCaptcha.return_value = mock_solver_instance

        with patch("src.core.captcha_handler.CAPTCHAHandler._get_hcaptcha_site_key",
                   new=AsyncMock(return_value="hcaptcha-site-key")):
            with patch.dict("sys.modules", {"twocaptcha": mock_twocaptcha_module}):
                result = await handler._solve_2captcha(page, CAPTCHAType.HCAPTCHA)

        assert result is True


# ---------------------------------------------------------------------------
# 17.8 – Anti-Captcha API integration
# ---------------------------------------------------------------------------


class TestAntiCaptchaSolving:
    @pytest.mark.asyncio
    async def test_anticaptcha_recaptcha_v2_success(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="anticaptcha", api_key="fake-key")

        mock_solver_instance = MagicMock()
        mock_solver_instance.solve_and_return_solution.return_value = "anti-token-123"

        mock_solver_class = MagicMock(return_value=mock_solver_instance)

        with patch("src.core.captcha_handler.CAPTCHAHandler._get_recaptcha_site_key",
                   new=AsyncMock(return_value="6Le-test")):
            with patch.dict("sys.modules", {
                "anticaptchaofficial": MagicMock(),
                "anticaptchaofficial.recaptchav2proxyless": MagicMock(
                    recaptchaV2Proxyless=mock_solver_class
                ),
                "anticaptchaofficial.recaptchav3proxyless": MagicMock(),
                "anticaptchaofficial.hcaptchaproxyless": MagicMock(),
            }):
                result = await handler._solve_anticaptcha(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is True

    @pytest.mark.asyncio
    async def test_anticaptcha_missing_library_returns_false(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="anticaptcha", api_key="fake-key")

        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = await handler._solve_anticaptcha(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is False


# ---------------------------------------------------------------------------
# 17.9 – Exponential backoff
# ---------------------------------------------------------------------------


class TestExponentialBackoff:
    def test_backoff_doubles_after_failure(self):
        handler = CAPTCHAHandler()
        initial = handler.backoff_seconds
        handler._increase_backoff()
        assert handler.backoff_seconds == initial * 2

    def test_backoff_capped_at_max(self):
        handler = CAPTCHAHandler()
        handler._backoff_seconds = _MAX_BACKOFF
        handler._increase_backoff()
        assert handler.backoff_seconds == _MAX_BACKOFF

    def test_backoff_resets_after_success(self):
        handler = CAPTCHAHandler()
        handler._backoff_seconds = 160.0
        handler._reset_backoff()
        assert handler.backoff_seconds == _INITIAL_BACKOFF

    @pytest.mark.asyncio
    async def test_wait_backoff_sleeps_when_elevated(self):
        handler = CAPTCHAHandler()
        handler._backoff_seconds = 20.0

        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await handler.wait_backoff()
            mock_sleep.assert_called_once_with(20.0)

    @pytest.mark.asyncio
    async def test_wait_backoff_skips_at_initial_value(self):
        handler = CAPTCHAHandler()
        # backoff_seconds == _INITIAL_BACKOFF → no sleep

        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await handler.wait_backoff()
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_solve_failure_increases_backoff(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")
        initial_backoff = handler.backoff_seconds

        # Make input() raise so all attempts fail
        with patch("builtins.input", side_effect=Exception("no stdin")):
            result = await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is False
        assert handler.backoff_seconds > initial_backoff


# ---------------------------------------------------------------------------
# Max attempts / skip behaviour (Requirement 20.4)
# ---------------------------------------------------------------------------


class TestMaxAttempts:
    @pytest.mark.asyncio
    async def test_returns_false_after_max_attempts(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")

        with patch("builtins.input", side_effect=Exception("no stdin")):
            result = await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        assert result is False

    @pytest.mark.asyncio
    async def test_encounter_count_increments_per_attempt(self):
        page = _make_page()
        handler = CAPTCHAHandler(solver_type="manual")

        with patch("builtins.input", side_effect=Exception("no stdin")):
            await handler.solve(page, CAPTCHAType.RECAPTCHA_V2)

        # Each attempt calls _solve_once which increments the counter
        assert handler.captcha_encounter_count == MAX_SOLVE_ATTEMPTS


# ---------------------------------------------------------------------------
# Detection priority ordering
# ---------------------------------------------------------------------------


class TestDetectionPriority:
    @pytest.mark.asyncio
    async def test_recaptcha_v2_takes_priority_over_v3(self):
        """If both v2 and v3 indicators are present, v2 should be returned."""
        html = '<script src="https://www.google.com/recaptcha/api.js"></script>'
        page = _make_page(
            html=html,
            selector_results={"div.g-recaptcha": MagicMock()},
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.RECAPTCHA_V2

    @pytest.mark.asyncio
    async def test_hcaptcha_takes_priority_over_v3(self):
        """hCaptcha should be detected before reCAPTCHA v3."""
        html = '<script src="https://www.google.com/recaptcha/api.js"></script>'
        page = _make_page(
            html=html,
            selector_results={'iframe[src*="hcaptcha.com"]': MagicMock()},
        )
        handler = CAPTCHAHandler()
        result = await handler.detect(page)
        assert result == CAPTCHAType.HCAPTCHA
