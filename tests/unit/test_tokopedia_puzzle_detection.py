"""Unit tests for Tokopedia puzzle CAPTCHA detection and handling.

Tests cover:
- Tokopedia puzzle detection via DOM elements
- Tokopedia puzzle detection via missing profile data
- Tokopedia puzzle detection via text patterns
- Puzzle solving with auto-refresh strategy
- Profile data visibility verification
- Consecutive puzzle tracking and pause mechanism
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.captcha_handler import CAPTCHAHandler


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_page(
    *,
    url: str = "https://affiliate.tokopedia.com/creator/detail/test",
    html: str = "",
    selector_results: dict | None = None,
    visible_elements: dict | None = None,
) -> MagicMock:
    """Build a mock Playwright Page with configurable behaviour."""
    page = MagicMock()
    page.url = url

    # page.content() returns the HTML string
    page.content = AsyncMock(return_value=html)

    # page.query_selector() returns elements based on selector_results
    _selector_map = selector_results or {}
    _visible_map = visible_elements or {}

    async def _query_selector(selector: str):
        element = _selector_map.get(selector, None)
        if element:
            # Mock is_visible() method
            element.is_visible = AsyncMock(return_value=_visible_map.get(selector, True))
        return element

    page.query_selector = _query_selector

    # page.wait_for_selector() mock
    async def _wait_for_selector(selector: str, timeout: int = 30000):
        element = _selector_map.get(selector, None)
        if element and _visible_map.get(selector, True):
            return element
        raise Exception(f"Timeout waiting for selector: {selector}")

    page.wait_for_selector = _wait_for_selector

    # page.evaluate() for text content
    page.evaluate = AsyncMock(return_value="Sample profile content with enough text to indicate a loaded page")

    # page.reload() mock
    page.reload = AsyncMock()

    return page


# ---------------------------------------------------------------------------
# Task 17.12 – Tokopedia puzzle detection tests
# ---------------------------------------------------------------------------


class TestTokopediaPuzzleDetection:
    @pytest.mark.asyncio
    async def test_detects_puzzle_via_dom_elements(self):
        """Test detection via puzzle-specific DOM elements."""
        page = _make_page(
            selector_results={
                'div[class*="puzzle"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_puzzle_via_challenge_element(self):
        """Test detection via challenge-related elements."""
        page = _make_page(
            selector_results={
                'div[id*="challenge"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_puzzle_via_captcha_container(self):
        """Test detection via Tokopedia-specific captcha container."""
        page = _make_page(
            selector_results={
                'div[class*="captcha-container"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_puzzle_via_missing_profile_data(self):
        """Test detection when profile data elements are missing."""
        page = _make_page(
            selector_results={
                # Only one profile element present (insufficient)
                'div[class*="stats"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_puzzle_via_text_patterns(self):
        """Test detection via puzzle-related text in page content."""
        page = _make_page(
            html='<html><body><div>Please complete the verification puzzle</div></body></html>'
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_puzzle_when_profile_data_present(self):
        """Test no puzzle detection when sufficient profile data is present."""
        page = _make_page(
            selector_results={
                'div[class*="creator-profile"]': MagicMock(),
                'span[class*="follower"]': MagicMock(),
                'div[class*="contact"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_puzzle_on_normal_page(self):
        """Test no puzzle detection on normal profile page."""
        page = _make_page(
            html='<html><body><div class="creator-profile">Normal profile content</div></body></html>',
            selector_results={
                'div[class*="creator-profile"]': MagicMock(),
                'span[class*="follower"]': MagicMock(),
            }
        )
        handler = CAPTCHAHandler()
        
        result = await handler.detect_tokopedia_puzzle(page)
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_detection_errors_gracefully(self):
        """Test that detection errors are handled gracefully."""
        page = _make_page()
        
        # Make all page operations fail
        async def failing_query_selector(selector):
            raise Exception("DOM error")
        
        async def failing_content():
            raise Exception("Content error")
            
        page.query_selector = failing_query_selector
        page.content = failing_content
        
        handler = CAPTCHAHandler()
        
        # Mock asyncio.sleep to avoid waiting
        with patch('asyncio.sleep', new=AsyncMock()):
            result = await handler.detect_tokopedia_puzzle(page)
        
        # When all operations fail, the method should return False
        assert result is False


# ---------------------------------------------------------------------------
# Task 17.13 – Tokopedia puzzle solving tests
# ---------------------------------------------------------------------------


class TestTokopediaPuzzleSolving:
    @pytest.mark.asyncio
    async def test_solve_puzzle_success_first_attempt(self):
        """Test successful puzzle solving on first attempt."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        # Mock detection: puzzle present initially, then gone after refresh
        detection_calls = [True, False]  # First call: puzzle present, second: gone
        handler.detect_tokopedia_puzzle = AsyncMock(side_effect=detection_calls)
        handler._verify_profile_data_visible = AsyncMock(return_value=True)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is True
        page.reload.assert_called_once()
        assert handler.puzzle_encounter_count == 1

    @pytest.mark.asyncio
    async def test_solve_puzzle_success_after_retries(self):
        """Test successful puzzle solving after multiple attempts."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        # Mock detection: puzzle present for first check, then gone after first refresh
        detection_calls = [True, False]  # First: puzzle present, after refresh: gone
        handler.detect_tokopedia_puzzle = AsyncMock(side_effect=detection_calls)
        handler._verify_profile_data_visible = AsyncMock(return_value=True)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is True
        assert page.reload.call_count == 1  # One refresh needed
        assert handler.puzzle_encounter_count == 1

    @pytest.mark.asyncio
    async def test_solve_puzzle_success_after_multiple_retries(self):
        """Test successful puzzle solving after multiple refresh attempts."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        # Mock detection: puzzle present for 2 checks, then gone
        # First call: puzzle present, second call: still present, third call: gone
        detection_calls = [True, True, False]
        handler.detect_tokopedia_puzzle = AsyncMock(side_effect=detection_calls)
        
        # Mock profile verification to fail first time, succeed second time
        verification_calls = [False, True]
        handler._verify_profile_data_visible = AsyncMock(side_effect=verification_calls)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is True
        assert page.reload.call_count == 2  # Two refreshes needed
        assert handler.puzzle_encounter_count == 1

    @pytest.mark.asyncio
    async def test_solve_puzzle_failure_max_attempts(self):
        """Test puzzle solving failure after max attempts."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        # Mock detection: puzzle always present
        handler.detect_tokopedia_puzzle = AsyncMock(return_value=True)
        handler._verify_profile_data_visible = AsyncMock(return_value=False)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is False
        assert page.reload.call_count == 3  # Max attempts
        assert handler.puzzle_encounter_count == 1

    @pytest.mark.asyncio
    async def test_solve_puzzle_already_bypassed(self):
        """Test when puzzle is already bypassed (no puzzle detected)."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        handler.detect_tokopedia_puzzle = AsyncMock(return_value=False)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is True
        page.reload.assert_not_called()  # No refresh needed
        assert handler.puzzle_encounter_count == 1  # Still counts as encounter

    @pytest.mark.asyncio
    async def test_solve_puzzle_handles_reload_errors(self):
        """Test handling of page reload errors during puzzle solving."""
        page = _make_page()
        page.reload = AsyncMock(side_effect=Exception("Reload failed"))
        handler = CAPTCHAHandler()
        
        handler.detect_tokopedia_puzzle = AsyncMock(return_value=True)
        
        result = await handler.solve_tokopedia_puzzle(page)
        
        assert result is False
        assert handler.puzzle_encounter_count == 1


# ---------------------------------------------------------------------------
# Task 17.14 – Profile data visibility verification tests
# ---------------------------------------------------------------------------


class TestProfileDataVerification:
    @pytest.mark.asyncio
    async def test_verify_profile_data_visible_success(self):
        """Test successful profile data verification."""
        page = _make_page()
        handler = CAPTCHAHandler()
        
        # Mock wait_for_selector to return elements for the first two selectors
        call_count = 0
        async def mock_wait_for_selector(selector: str, timeout: int = 30000):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First two calls succeed
                element = MagicMock()
                element.is_visible = AsyncMock(return_value=True)
                return element
            else:
                raise Exception(f"Timeout waiting for selector: {selector}")
        
        page.wait_for_selector = mock_wait_for_selector
        
        result = await handler._verify_profile_data_visible(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_profile_data_via_text_content(self):
        """Test profile data verification via text content."""
        page = _make_page()
        # Mock no visible elements but sufficient text content
        page.wait_for_selector = AsyncMock(side_effect=Exception("No elements"))
        page.evaluate = AsyncMock(return_value="A" * 150)  # Sufficient content
        
        handler = CAPTCHAHandler()
        
        result = await handler._verify_profile_data_visible(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_profile_data_insufficient_elements(self):
        """Test profile data verification failure with insufficient elements."""
        page = _make_page()
        page.wait_for_selector = AsyncMock(side_effect=Exception("No elements"))
        page.evaluate = AsyncMock(return_value="Short")  # Insufficient content
        
        handler = CAPTCHAHandler()
        
        result = await handler._verify_profile_data_visible(page)
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_profile_data_handles_errors(self):
        """Test profile data verification handles errors gracefully."""
        page = _make_page()
        page.wait_for_selector = AsyncMock(side_effect=Exception("DOM error"))
        page.evaluate = AsyncMock(side_effect=Exception("Evaluate error"))
        
        handler = CAPTCHAHandler()
        
        result = await handler._verify_profile_data_visible(page)
        assert result is False


# ---------------------------------------------------------------------------
# Task 17.16 – Consecutive puzzle tracking tests
# ---------------------------------------------------------------------------


class TestConsecutivePuzzleTracking:
    def test_consecutive_puzzle_count_increments(self):
        """Test consecutive puzzle count increments on failures."""
        handler = CAPTCHAHandler()
        
        handler._record_puzzle_encounter(success=False)
        assert handler.consecutive_puzzle_count == 1
        
        handler._record_puzzle_encounter(success=False)
        assert handler.consecutive_puzzle_count == 2

    def test_consecutive_puzzle_count_resets_on_success(self):
        """Test consecutive puzzle count resets on success."""
        handler = CAPTCHAHandler()
        
        handler._record_puzzle_encounter(success=False)
        handler._record_puzzle_encounter(success=False)
        assert handler.consecutive_puzzle_count == 2
        
        handler._record_puzzle_encounter(success=True)
        assert handler.consecutive_puzzle_count == 0

    def test_consecutive_puzzle_count_resets_after_time(self):
        """Test consecutive puzzle count resets after time gap."""
        handler = CAPTCHAHandler()
        
        # Record first encounter
        handler._record_puzzle_encounter(success=False)
        assert handler.consecutive_puzzle_count == 1
        
        # Mock time passage (6 minutes)
        with patch('time.time', return_value=time.time() + 360):
            handler._record_puzzle_encounter(success=False)
            assert handler.consecutive_puzzle_count == 1  # Reset due to time gap

    def test_should_pause_for_puzzles(self):
        """Test pause recommendation for consecutive puzzles."""
        handler = CAPTCHAHandler()
        
        # Less than 5 consecutive puzzles
        for _ in range(4):
            handler._record_puzzle_encounter(success=False)
        assert handler.should_pause_for_puzzles() is False
        
        # 5 consecutive puzzles
        handler._record_puzzle_encounter(success=False)
        assert handler.should_pause_for_puzzles() is True

    @pytest.mark.asyncio
    async def test_wait_puzzle_pause(self):
        """Test puzzle pause mechanism."""
        handler = CAPTCHAHandler()
        
        # Set up consecutive puzzles to trigger pause
        for _ in range(5):
            handler._record_puzzle_encounter(success=False)
        
        with patch('asyncio.sleep', new=AsyncMock()) as mock_sleep:
            await handler.wait_puzzle_pause()
            
            # Should sleep for 5-10 minutes (300-600 seconds)
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            assert 300 <= sleep_duration <= 600
            
            # Consecutive count should reset after pause
            assert handler.consecutive_puzzle_count == 0

    @pytest.mark.asyncio
    async def test_no_pause_when_not_needed(self):
        """Test no pause when consecutive puzzle count is low."""
        handler = CAPTCHAHandler()
        
        # Only 2 consecutive puzzles (below threshold)
        for _ in range(2):
            handler._record_puzzle_encounter(success=False)
        
        with patch('asyncio.sleep', new=AsyncMock()) as mock_sleep:
            await handler.wait_puzzle_pause()
            
            # Should not sleep
            mock_sleep.assert_not_called()

    def test_puzzle_encounter_count_tracking(self):
        """Test total puzzle encounter count tracking."""
        handler = CAPTCHAHandler()
        
        assert handler.puzzle_encounter_count == 0
        
        handler._record_puzzle_encounter(success=False)
        assert handler.puzzle_encounter_count == 1
        
        handler._record_puzzle_encounter(success=True)
        assert handler.puzzle_encounter_count == 2
        
        handler._record_puzzle_encounter(success=False)
        assert handler.puzzle_encounter_count == 3


# ---------------------------------------------------------------------------
# Integration with existing CAPTCHA detection
# ---------------------------------------------------------------------------


class TestTokopediaPuzzleIntegration:
    @pytest.mark.asyncio
    async def test_puzzle_detection_separate_from_standard_captcha(self):
        """Test that Tokopedia puzzle detection is separate from standard CAPTCHA detection."""
        page = _make_page(
            html='<script src="https://www.google.com/recaptcha/api.js"></script>',
            selector_results={
                'div[class*="puzzle"]': MagicMock(),  # Tokopedia puzzle
                'div.g-recaptcha': MagicMock(),       # Standard reCAPTCHA
            }
        )
        handler = CAPTCHAHandler()
        
        # Standard CAPTCHA detection should still work
        standard_captcha = await handler.detect(page)
        assert standard_captcha is not None  # Should detect reCAPTCHA
        
        # Tokopedia puzzle detection should also work independently
        tokopedia_puzzle = await handler.detect_tokopedia_puzzle(page)
        assert tokopedia_puzzle is True

    @pytest.mark.asyncio
    async def test_puzzle_properties_accessible(self):
        """Test that puzzle-related properties are accessible."""
        handler = CAPTCHAHandler()
        
        # Initial state
        assert handler.puzzle_encounter_count == 0
        assert handler.consecutive_puzzle_count == 0
        assert handler.should_pause_for_puzzles() is False
        
        # After encounters
        handler._record_puzzle_encounter(success=False)
        assert handler.puzzle_encounter_count == 1
        assert handler.consecutive_puzzle_count == 1