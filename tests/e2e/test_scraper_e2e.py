"""End-to-end tests for the scraper orchestrator.

These tests use mocked browser/network responses to simulate real scraping
scenarios without hitting actual websites.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.models.models import AffiliatorData, Checkpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> Configuration:
    """Return a minimal Configuration suitable for E2E tests."""
    defaults = dict(
        base_url="https://example.com",
        list_page_url="/list",
        min_delay=0.0,
        max_delay=0.0,
        jitter=0.0,
        hourly_limit=1000,
        daily_limit=10000,
        max_session_duration=7200,
        break_duration_min=0,
        break_duration_max=1,
        quiet_hours=[],
        output_format="json",
        output_path="output/test_e2e.json",
        incremental_save=False,
        save_interval=5,
        captcha_solver="manual",
        captcha_api_key=None,
        browser_engine="playwright",
        headless=True,
    )
    defaults.update(overrides)
    return Configuration(**defaults)


def _make_list_html(affiliators: list[str], has_next: bool = False) -> str:
    """Generate fake HTML for a list page using selectors from selectors.json."""
    cards = "\n".join(
        f"""<div class="creator-card">
            <a class="creator-card-link" href="/detail/{u}">
                <div class="creator-name"><span class="username">{u}</span></div>
                <span class="creator-category">Fashion</span>
                <span class="follower-count">1000</span>
                <span class="gmv-value">500000</span>
                <span class="product-sold-count">50</span>
                <span class="avg-view-count">2000</span>
                <span class="engagement-rate">5.0</span>
            </a>
        </div>"""
        for u in affiliators
    )
    next_link = '<a rel="next" href="/list?page=2">Next</a>' if has_next else ""
    return f"<html><body>{cards}{next_link}</body></html>"


def _make_detail_html(username: str) -> str:
    """Generate fake HTML for a detail page using selectors from selectors.json."""
    return f"""
    <html>
    <body>
        <h1 class="profile-username">{username}</h1>
        <span class="profile-category">Fashion</span>
        <span class="profile-follower-count">1000</span>
        <span class="profile-gmv">500000</span>
        <span class="profile-products-sold">50</span>
        <span class="profile-avg-views">2000</span>
        <span class="profile-engagement-rate">5.0</span>
        <a href="tel:081234567890">081234567890</a>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# E2E Test: Single page scraping
# ---------------------------------------------------------------------------

class TestE2ESinglePage:
    @pytest.mark.asyncio
    async def test_scrape_single_page_no_pagination(self, tmp_path):
        """E2E: Scrape a single list page with 3 affiliators, no pagination."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        # Mock browser engine
        mock_page = MagicMock()
        mock_page.url = "https://example.com/list?page=1"

        list_html = _make_list_html(["alice", "bob", "charlie"], has_next=False)

        async def fake_navigate(url: str):
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return list_html
            # Detail pages
            for user in ["alice", "bob", "charlie"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        # Mock behavioral simulator to avoid delays
        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()

        # Mock CAPTCHA handler
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Disable random skip for deterministic results
        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        assert result.unique_affiliators == 3
        assert result.duplicates_found == 0
        assert result.errors == 0

        # Check saved data
        loaded = orchestrator._data_store.load()
        assert len(loaded) == 3
        usernames = {a.username for a in loaded}
        assert usernames == {"alice", "bob", "charlie"}


# ---------------------------------------------------------------------------
# E2E Test: Multi-page scraping with pagination
# ---------------------------------------------------------------------------

class TestE2EMultiPage:
    @pytest.mark.asyncio
    async def test_scrape_multiple_pages(self, tmp_path):
        """E2E: Scrape 2 list pages with pagination."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        page1_html = _make_list_html(["user1", "user2"], has_next=True)
        page2_html = _make_list_html(["user3", "user4"], has_next=False)

        page_counter = {"count": 0}

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                if "page=1" in page.url or "page=" not in page.url:
                    page_counter["count"] += 1
                    return page1_html
                elif "page=2" in page.url:
                    return page2_html
            # Detail pages
            for user in ["user1", "user2", "user3", "user4"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Disable random skip for deterministic results
        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        assert result.unique_affiliators == 4
        assert result.duplicates_found == 0

        loaded = orchestrator._data_store.load()
        assert len(loaded) == 4
        usernames = {a.username for a in loaded}
        assert usernames == {"user1", "user2", "user3", "user4"}


# ---------------------------------------------------------------------------
# E2E Test: Checkpoint and resume
# ---------------------------------------------------------------------------

class TestE2ECheckpointResume:
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, tmp_path):
        """E2E: Resume scraping from a checkpoint."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path, save_interval=2)
        orchestrator = ScraperOrchestrator(config)

        # Simulate that we already scraped user1 and user2
        checkpoint = Checkpoint(
            last_list_page=1,
            last_affiliator_index=0,
            scraped_usernames={"user1", "user2"},
            timestamp=datetime.now(),
        )

        # Now we scrape page 1 again, but user1 and user2 should be skipped
        page1_html = _make_list_html(["user1", "user2", "user3"], has_next=False)

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return page1_html
            for user in ["user1", "user2", "user3"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Disable random skip for deterministic results
        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.resume(checkpoint)

        # Only user3 should be new
        assert result.unique_affiliators == 3  # 2 from checkpoint + 1 new
        assert result.duplicates_found == 2  # user1 and user2 re-encountered


# ---------------------------------------------------------------------------
# E2E Test: Error recovery
# ---------------------------------------------------------------------------

class TestE2EErrorRecovery:
    @pytest.mark.asyncio
    async def test_continues_after_detail_page_error(self, tmp_path):
        """E2E: Scraper continues after a detail page error."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        list_html = _make_list_html(["user1", "user2", "user3"], has_next=False)

        call_count = {"detail": 0}

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return list_html
            # Simulate error on user2
            if "user2" in page.url:
                call_count["detail"] += 1
                raise RuntimeError("Simulated error on user2")
            for user in ["user1", "user3"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Disable random skip for deterministic results
        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        # user1 and user3 should succeed, user2 should fail
        assert result.unique_affiliators == 2
        assert result.errors == 1

        loaded = orchestrator._data_store.load()
        usernames = {a.username for a in loaded}
        assert usernames == {"user1", "user3"}


# ---------------------------------------------------------------------------
# E2E Test: Deduplication
# ---------------------------------------------------------------------------

class TestE2EDeduplication:
    @pytest.mark.asyncio
    async def test_deduplicates_across_pages(self, tmp_path):
        """E2E: Duplicate usernames across pages are deduplicated."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        # Page 1 has alice, bob
        # Page 2 has bob, charlie (bob is duplicate)
        page1_html = _make_list_html(["alice", "bob"], has_next=True)
        page2_html = _make_list_html(["bob", "charlie"], has_next=False)

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                if "page=1" in page.url or "page=" not in page.url:
                    return page1_html
                elif "page=2" in page.url:
                    return page2_html
            for user in ["alice", "bob", "charlie"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Disable random skip to ensure deterministic results
        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        assert result.unique_affiliators == 3  # alice, bob, charlie
        assert result.duplicates_found == 1  # bob on page 2

        loaded = orchestrator._data_store.load()
        assert len(loaded) == 3
        usernames = {a.username for a in loaded}
        assert usernames == {"alice", "bob", "charlie"}


# ---------------------------------------------------------------------------
# E2E Test: Rate limiting enforcement (26.6)
# ---------------------------------------------------------------------------

class TestE2ERateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiter_wait_called_between_requests(self, tmp_path):
        """E2E: rate_limiter.wait() is called for each list and detail page request."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        list_html = _make_list_html(["user1", "user2"], has_next=False)

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return list_html
            for user in ["user1", "user2"]:
                if user in page.url:
                    return _make_detail_html(user)
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Spy on rate_limiter.wait
        orchestrator._rate_limiter.wait = AsyncMock()

        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        # wait() should be called at least once per list page + once per detail page
        # (1 list page + 2 detail pages = at least 3 calls)
        assert orchestrator._rate_limiter.wait.call_count >= 3
        assert result.unique_affiliators == 2

    @pytest.mark.asyncio
    async def test_traffic_controller_check_permission_called(self, tmp_path):
        """E2E: traffic_controller.check_permission() is called during scraping."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        list_html = _make_list_html(["user1"], has_next=False)

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return list_html
            if "user1" in page.url:
                return _make_detail_html("user1")
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # Spy on check_permission (must return True to allow scraping)
        original_check = orchestrator._traffic_controller.check_permission
        orchestrator._traffic_controller.check_permission = AsyncMock(return_value=True)

        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        assert orchestrator._traffic_controller.check_permission.call_count >= 1
        assert result.unique_affiliators == 1

    @pytest.mark.asyncio
    async def test_wait_for_window_reset_called_when_traffic_limit_hit(self, tmp_path):
        """E2E: wait_for_window_reset() is called when check_permission() returns False."""
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        list_html = _make_list_html(["user1"], has_next=False)

        async def fake_navigate(url: str):
            mock_page = MagicMock()
            mock_page.url = url
            return mock_page

        async def fake_get_html(page):
            if "list" in page.url:
                return list_html
            if "user1" in page.url:
                return _make_detail_html("user1")
            return "<html></html>"

        orchestrator._browser_engine.launch = AsyncMock()
        orchestrator._browser_engine.navigate = fake_navigate
        orchestrator._browser_engine.get_html = fake_get_html
        orchestrator._browser_engine.close = AsyncMock()

        orchestrator._behavioral_simulator.scroll_page = AsyncMock()
        orchestrator._behavioral_simulator.idle_behavior = AsyncMock()
        orchestrator._behavioral_simulator.think_time = AsyncMock()
        orchestrator._captcha_handler.detect = AsyncMock(return_value=None)

        # First call returns False (limit hit), subsequent calls return True
        permission_responses = [False, True, True, True, True]
        call_index = {"i": 0}

        async def fake_check_permission():
            idx = call_index["i"]
            call_index["i"] += 1
            if idx < len(permission_responses):
                return permission_responses[idx]
            return True

        orchestrator._traffic_controller.check_permission = fake_check_permission
        orchestrator._traffic_controller.wait_for_window_reset = AsyncMock()

        with patch("src.core.scraper_orchestrator.random.random", return_value=1.0):
            result = await orchestrator.start()

        # wait_for_window_reset should have been called once (when limit was hit)
        assert orchestrator._traffic_controller.wait_for_window_reset.call_count >= 1
