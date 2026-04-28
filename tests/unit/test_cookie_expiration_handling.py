"""Unit tests for cookie expiration handling in ScraperOrchestrator"""

import asyncio
import os
import tempfile
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration


@pytest.fixture
def mock_config():
    """Create a mock configuration"""
    config = Configuration()
    config.cookie_file = "test_cookies.json"
    config.require_cookie_file = True
    config.headless = True
    config.max_pages_per_run = 1
    return config


@pytest.fixture
def mock_orchestrator(mock_config):
    """Create a ScraperOrchestrator with mocked dependencies"""
    orchestrator = ScraperOrchestrator(mock_config)
    
    # Mock all the components
    orchestrator._browser_engine = AsyncMock()
    orchestrator._error_analyzer = MagicMock()
    orchestrator._traffic_controller = AsyncMock()
    orchestrator._behavioral_simulator = AsyncMock()
    orchestrator._html_parser = MagicMock()
    orchestrator._extractor = MagicMock()
    orchestrator._captcha_handler = AsyncMock()
    orchestrator._deduplicator = MagicMock()
    orchestrator._validator = MagicMock()
    orchestrator._data_store = MagicMock()
    
    return orchestrator


class TestCookieExpirationDetection:
    """Tests for cookie expiration detection during scraping"""
    
    @pytest.mark.asyncio
    async def test_detect_cookie_expiration_on_list_page(self, mock_orchestrator):
        """Test that cookie expiration is detected on list page"""
        # Setup
        mock_page = AsyncMock()
        mock_orchestrator._browser_engine.navigate.return_value = mock_page
        mock_orchestrator._browser_engine.get_html.return_value = "<html>Coba lagi</html>"
        mock_orchestrator._error_analyzer.detect_coba_lagi.return_value = True
        mock_orchestrator._traffic_controller.check_permission.return_value = True
        
        # Mock the cookie expiration handler to avoid blocking
        with patch.object(mock_orchestrator, '_handle_cookie_expiration', new_callable=AsyncMock) as mock_handler:
            # Call the method
            result = await mock_orchestrator._scrape_list_page("https://test.com")
            
            # Verify cookie expiration was detected and handler was called
            assert mock_handler.called
            assert mock_orchestrator._error_analyzer.detect_coba_lagi.called
    
    @pytest.mark.asyncio
    async def test_detect_cookie_expiration_on_detail_page(self, mock_orchestrator):
        """Test that cookie expiration is detected on detail page"""
        # Setup
        from src.core.affiliator_extractor import AffiliatorEntry
        
        entry = AffiliatorEntry(
            username="test_user",
            kategori="Fashion",
            pengikut=1000,
            gmv=50000.0,
            produk_terjual=100,
            rata_rata_tayangan=5000,
            tingkat_interaksi=5.0,
            gmv_per_pembeli=500.0,
            gmv_harian=1000.0,
            gmv_mingguan=7000.0,
            gmv_bulanan=30000.0,
            detail_url="https://test.com/detail"
        )
        
        mock_detail_page = AsyncMock()
        mock_detail_page.url = "https://test.com/detail"
        mock_detail_page.content = AsyncMock(return_value="<html>Coba lagi</html>")
        mock_detail_page.goto = AsyncMock()
        mock_detail_page.reload = AsyncMock()
        mock_detail_page.close = AsyncMock()
        
        mock_orchestrator._browser_engine.context = MagicMock()
        mock_orchestrator._browser_engine.context.new_page = AsyncMock(return_value=mock_detail_page)
        mock_orchestrator._error_analyzer.detect_coba_lagi.return_value = True
        mock_orchestrator._captcha_handler.should_pause_for_puzzles = AsyncMock(return_value=False)
        mock_orchestrator._traffic_controller.check_permission = AsyncMock(return_value=True)
        mock_orchestrator._traffic_controller.record_request = MagicMock()
        
        # Mock the behavioral simulator methods
        mock_orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        
        # Mock the cookie expiration handler to avoid blocking
        with patch.object(mock_orchestrator, '_handle_cookie_expiration', new_callable=AsyncMock) as mock_handler:
            with patch.object(mock_orchestrator, '_handle_coba_lagi_message', new_callable=AsyncMock):
                with patch.object(mock_orchestrator, '_handle_public_wifi_conditions', new_callable=AsyncMock):
                    # Call the method
                    await mock_orchestrator._scrape_single_detail(entry)
                    
                    # Verify cookie expiration was detected and handler was called
                    assert mock_handler.called
                    assert mock_orchestrator._error_analyzer.detect_coba_lagi.called


class TestCookieExpirationHandler:
    """Tests for the cookie expiration handler"""
    
    @pytest.mark.asyncio
    async def test_handle_cookie_expiration_prompts_user(self, mock_orchestrator):
        """Test that cookie expiration handler prompts user"""
        # Create a temporary cookie file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"name": "test", "value": "test", "domain": ".tokopedia.com"}], f)
            temp_cookie_file = f.name
        
        try:
            mock_orchestrator._config.cookie_file = temp_cookie_file
            
            # Mock user input to simulate pressing Enter
            with patch('builtins.input', return_value=''):
                # Mock the browser engine's load_cookies_from_file
                mock_orchestrator._browser_engine.load_cookies_from_file = AsyncMock()
                
                # Call the handler
                await mock_orchestrator._handle_cookie_expiration()
                
                # Verify cookies were reloaded
                mock_orchestrator._browser_engine.load_cookies_from_file.assert_called_once_with(temp_cookie_file)
        finally:
            # Clean up
            if os.path.exists(temp_cookie_file):
                os.unlink(temp_cookie_file)
    
    @pytest.mark.asyncio
    async def test_handle_cookie_expiration_missing_file(self, mock_orchestrator):
        """Test that handler raises error when cookie file is missing"""
        mock_orchestrator._config.cookie_file = "nonexistent_cookies.json"
        
        # Mock user input
        with patch('builtins.input', return_value=''):
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                await mock_orchestrator._handle_cookie_expiration()
    
    @pytest.mark.asyncio
    async def test_handle_cookie_expiration_warns_old_file(self, mock_orchestrator):
        """Test that handler warns when cookie file is old"""
        # Create a temporary cookie file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"name": "test", "value": "test", "domain": ".tokopedia.com"}], f)
            temp_cookie_file = f.name
        
        try:
            mock_orchestrator._config.cookie_file = temp_cookie_file
            
            # Set file modification time to 10 minutes ago
            import time
            old_time = time.time() - 600  # 10 minutes ago
            os.utime(temp_cookie_file, (old_time, old_time))
            
            # Mock user input to continue anyway
            with patch('builtins.input', side_effect=['', 'y']):
                mock_orchestrator._browser_engine.load_cookies_from_file = AsyncMock()
                
                # Call the handler
                await mock_orchestrator._handle_cookie_expiration()
                
                # Verify cookies were still reloaded
                mock_orchestrator._browser_engine.load_cookies_from_file.assert_called_once()
        finally:
            # Clean up
            if os.path.exists(temp_cookie_file):
                os.unlink(temp_cookie_file)
    
    @pytest.mark.asyncio
    async def test_handle_cookie_expiration_user_cancels(self, mock_orchestrator):
        """Test that handler stops when user cancels"""
        # Create a temporary cookie file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"name": "test", "value": "test", "domain": ".tokopedia.com"}], f)
            temp_cookie_file = f.name
        
        try:
            mock_orchestrator._config.cookie_file = temp_cookie_file
            
            # Set file modification time to 10 minutes ago
            import time
            old_time = time.time() - 600
            os.utime(temp_cookie_file, (old_time, old_time))
            
            # Mock user input to cancel
            with patch('builtins.input', side_effect=['', 'n']):
                # Should raise RuntimeError
                with pytest.raises(RuntimeError, match="User cancelled cookie refresh"):
                    await mock_orchestrator._handle_cookie_expiration()
        finally:
            # Clean up
            if os.path.exists(temp_cookie_file):
                os.unlink(temp_cookie_file)


class TestCookieExpirationRetry:
    """Tests for retry logic after cookie expiration"""
    
    @pytest.mark.asyncio
    async def test_retry_after_cookie_refresh_success(self, mock_orchestrator):
        """Test that scraping retries successfully after cookie refresh"""
        # Setup
        mock_page = AsyncMock()
        mock_orchestrator._browser_engine.navigate.return_value = mock_page
        
        # First call returns expired cookies, second call succeeds
        mock_orchestrator._browser_engine.get_html.side_effect = [
            "<html>Coba lagi</html>",  # First call - expired
            "<html>Valid content</html>"  # Second call - success
        ]
        mock_orchestrator._error_analyzer.detect_coba_lagi.side_effect = [True, False]
        mock_orchestrator._traffic_controller.check_permission.return_value = True
        
        # Mock successful extraction
        from src.core.affiliator_extractor import ListPageResult
        mock_orchestrator._html_parser.parse.return_value = MagicMock()
        mock_orchestrator._extractor.extract_list_page.return_value = ListPageResult(
            affiliators=[],
            next_page_url=None
        )
        
        # Mock the cookie expiration handler
        with patch.object(mock_orchestrator, '_handle_cookie_expiration', new_callable=AsyncMock):
            # Call the method
            result = await mock_orchestrator._scrape_list_page("https://test.com")
            
            # Verify it succeeded after retry
            assert result is not None
            assert mock_orchestrator._browser_engine.navigate.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_after_cookie_refresh_fails(self, mock_orchestrator):
        """Test that scraping stops when cookie refresh fails"""
        # Setup
        mock_page = AsyncMock()
        mock_orchestrator._browser_engine.navigate.return_value = mock_page
        
        # Both calls return expired cookies
        mock_orchestrator._browser_engine.get_html.return_value = "<html>Coba lagi</html>"
        mock_orchestrator._error_analyzer.detect_coba_lagi.return_value = True
        mock_orchestrator._traffic_controller.check_permission.return_value = True
        
        # Mock the cookie expiration handler
        with patch.object(mock_orchestrator, '_handle_cookie_expiration', new_callable=AsyncMock):
            # Call the method
            result = await mock_orchestrator._scrape_list_page("https://test.com")
            
            # Verify it returned None (failure)
            assert result is None
