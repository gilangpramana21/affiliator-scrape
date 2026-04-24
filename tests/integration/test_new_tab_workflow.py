"""Integration tests for new tab management workflow.

Tests cover:
- New tab creation for detail pages
- Tokopedia puzzle detection and solving in new tabs
- Tab cleanup after processing
- Error handling for tab operations
- Integration with scraper orchestrator
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.core.affiliator_extractor import AffiliatorEntry


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_mock_browser_engine():
    """Create a mock browser engine with context support."""
    browser_engine = MagicMock()
    
    # Mock context
    context = MagicMock()
    browser_engine.context = context
    
    # Create a single page mock that will be reused
    page_mock = MagicMock()
    page_mock.goto = AsyncMock()
    page_mock.content = AsyncMock(return_value="<html><body>Profile content</body></html>")
    page_mock.close = AsyncMock()
    
    # Mock new_page to always return the same page mock
    context.new_page = AsyncMock(return_value=page_mock)
    
    # Store reference to page mock for test assertions
    browser_engine._test_page_mock = page_mock
    
    return browser_engine


def _make_mock_captcha_handler():
    """Create a mock CAPTCHA handler."""
    handler = MagicMock()
    handler.detect_tokopedia_puzzle = AsyncMock(return_value=False)
    handler.solve_tokopedia_puzzle = AsyncMock(return_value=True)
    handler.detect = AsyncMock(return_value=None)
    handler.should_pause_for_puzzles = MagicMock(return_value=False)
    handler.wait_puzzle_pause = AsyncMock()
    return handler


def _make_mock_config():
    """Create a mock configuration."""
    config = Configuration()
    config.headless = True
    config.browser_engine = "playwright"
    return config


def _make_mock_entry():
    """Create a mock affiliator entry."""
    return AffiliatorEntry(
        username="test_user",
        kategori="Fashion",
        pengikut=1000,
        gmv=50000.0,
        produk_terjual=100,
        rata_rata_tayangan=5000,
        tingkat_interaksi=5.5,
        detail_url="https://affiliate.tokopedia.com/creator/detail/test_user"
    )


# ---------------------------------------------------------------------------
# Task 20.12 – New tab workflow tests
# ---------------------------------------------------------------------------


class TestNewTabWorkflow:
    @pytest.mark.asyncio
    async def test_opens_detail_page_in_new_tab(self):
        """Test that detail pages are opened in new tabs."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        
        # Mock _merge_data to return a valid affiliator
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify new tab was created
        orchestrator._browser_engine.context.new_page.assert_called_once()
        
        # Verify page navigation
        page_mock = orchestrator._browser_engine._test_page_mock
        page_mock.goto.assert_called_once_with(
            entry.detail_url, 
            wait_until="networkidle", 
            timeout=30000
        )

    @pytest.mark.asyncio
    async def test_closes_tab_after_processing(self):
        """Test that tabs are properly closed after processing."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify tab was closed
        page_mock = orchestrator._browser_engine._test_page_mock
        page_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_tab_on_error(self):
        """Test that tabs are closed even when errors occur."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        
        # Make extractor raise an error
        orchestrator._extractor.extract_detail_page = MagicMock(
            side_effect=Exception("Extraction failed")
        )
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify tab was still closed despite error
        page_mock = orchestrator._browser_engine._test_page_mock
        page_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_browser_context_not_available(self):
        """Test handling when browser context is not available."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock browser engine with no context
        orchestrator._browser_engine = MagicMock()
        orchestrator._browser_engine.context = None
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Should increment error count
        assert orchestrator._errors == 1


# ---------------------------------------------------------------------------
# Task 20.13 – Tokopedia puzzle integration tests
# ---------------------------------------------------------------------------


class TestTokopediaPuzzleIntegration:
    @pytest.mark.asyncio
    async def test_detects_and_solves_puzzle_in_new_tab(self):
        """Test puzzle detection and solving in new tab workflow."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._captcha_handler.detect_tokopedia_puzzle = AsyncMock(return_value=True)
        orchestrator._captcha_handler.solve_tokopedia_puzzle = AsyncMock(return_value=True)
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify puzzle detection was called
        page_mock = orchestrator._browser_engine._test_page_mock
        orchestrator._captcha_handler.detect_tokopedia_puzzle.assert_called_once_with(page_mock)
        
        # Verify puzzle solving was called
        orchestrator._captcha_handler.solve_tokopedia_puzzle.assert_called_once_with(page_mock)

    @pytest.mark.asyncio
    async def test_handles_puzzle_solve_failure(self):
        """Test handling when puzzle solving fails."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._captcha_handler.detect_tokopedia_puzzle = AsyncMock(return_value=True)
        orchestrator._captcha_handler.solve_tokopedia_puzzle = AsyncMock(return_value=False)  # Fail
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Should increment error count and return early
        assert orchestrator._errors == 1
        
        # Tab should still be closed
        page_mock = orchestrator._browser_engine._test_page_mock
        page_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_checks_for_consecutive_puzzles_pause(self):
        """Test that consecutive puzzle pause is checked before processing."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._captcha_handler.should_pause_for_puzzles = MagicMock(return_value=True)
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify pause check was called
        orchestrator._captcha_handler.should_pause_for_puzzles.assert_called_once()
        
        # Verify pause was executed
        orchestrator._captcha_handler.wait_puzzle_pause.assert_called_once()


# ---------------------------------------------------------------------------
# Task 20.14 – Tab management error handling tests
# ---------------------------------------------------------------------------


class TestTabManagementErrorHandling:
    @pytest.mark.asyncio
    async def test_handles_tab_creation_failure(self):
        """Test handling when new tab creation fails."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock browser engine with failing new_page
        browser_engine = MagicMock()
        context = MagicMock()
        context.new_page = AsyncMock(side_effect=Exception("Tab creation failed"))
        browser_engine.context = context
        orchestrator._browser_engine = browser_engine
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Should increment error count
        assert orchestrator._errors == 1

    @pytest.mark.asyncio
    async def test_handles_tab_navigation_failure(self):
        """Test handling when tab navigation fails."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock browser engine with failing navigation
        browser_engine = MagicMock()
        context = MagicMock()
        
        page_mock = MagicMock()
        page_mock.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        page_mock.close = AsyncMock()
        
        context.new_page = AsyncMock(return_value=page_mock)
        browser_engine.context = context
        browser_engine._test_page_mock = page_mock
        orchestrator._browser_engine = browser_engine
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Should increment error count
        assert orchestrator._errors == 1
        
        # Tab should still be closed
        page_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_tab_close_failure(self):
        """Test handling when tab close fails."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock browser engine with failing close
        browser_engine = MagicMock()
        context = MagicMock()
        
        async def mock_new_page():
            page = MagicMock()
            page.goto = AsyncMock()
            page.content = AsyncMock(return_value="<html><body>Content</body></html>")
            page.close = AsyncMock(side_effect=Exception("Close failed"))
            return page
        
        context.new_page = mock_new_page
        browser_engine.context = context
        orchestrator._browser_engine = browser_engine
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        # Should not raise exception despite close failure
        await orchestrator._scrape_single_detail(entry)
        
        # Processing should still complete successfully
        assert orchestrator._errors == 0


# ---------------------------------------------------------------------------
# Task 20.15 – Behavioral simulation integration tests
# ---------------------------------------------------------------------------


class TestBehavioralSimulationIntegration:
    @pytest.mark.asyncio
    async def test_behavioral_simulation_called_on_new_tab(self):
        """Test that behavioral simulation is called on the new tab."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify behavioral simulation was called on the new tab
        page_mock = orchestrator._browser_engine._test_page_mock
        orchestrator._behavioral_simulator.scroll_page.assert_called_once_with(page_mock)

    @pytest.mark.asyncio
    async def test_standard_captcha_detection_on_new_tab(self):
        """Test that standard CAPTCHA detection works on new tabs."""
        config = _make_mock_config()
        orchestrator = ScraperOrchestrator(config)
        
        # Mock components
        orchestrator._browser_engine = _make_mock_browser_engine()
        orchestrator._captcha_handler = _make_mock_captcha_handler()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)  # No CAPTCHA
        orchestrator._traffic_controller = MagicMock()
        orchestrator._traffic_controller.record_request = MagicMock()
        orchestrator._behavioral_simulator = MagicMock()
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._html_parser = MagicMock()
        orchestrator._html_parser.parse = MagicMock()
        orchestrator._extractor = MagicMock()
        orchestrator._extractor.extract_detail_page = MagicMock()
        orchestrator._validator = MagicMock()
        orchestrator._validator.validate = MagicMock()
        orchestrator._validator.validate.return_value = MagicMock(is_valid=True)
        orchestrator._deduplicator = MagicMock()
        orchestrator._deduplicator.add = MagicMock(return_value=True)
        orchestrator._merge_data = MagicMock()
        orchestrator._merge_data.return_value = MagicMock(username="test_user")
        
        entry = _make_mock_entry()
        
        await orchestrator._scrape_single_detail(entry)
        
        # Verify standard CAPTCHA detection was called on the new tab
        page_mock = orchestrator._browser_engine._test_page_mock
        orchestrator._captcha_handler.detect.assert_called_once_with(page_mock)