"""Integration tests for ScraperOrchestrator."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.scraper_orchestrator import Progress, ScraperOrchestrator
from src.models.config import Configuration
from src.models.models import AffiliatorData, Checkpoint, ScrapingResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> Configuration:
    """Return a minimal Configuration suitable for tests."""
    defaults = dict(
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
        output_path="output/test_affiliators.json",
        incremental_save=False,
        save_interval=100,
        captcha_solver="manual",
        captcha_api_key=None,
        browser_engine="playwright",
        headless=True,
    )
    defaults.update(overrides)
    return Configuration(**defaults)


def _make_affiliator(username: str = "user1") -> AffiliatorData:
    return AffiliatorData(
        username=username,
        kategori="Fashion",
        pengikut=1000,
        gmv=500000.0,
        produk_terjual=50,
        rata_rata_tayangan=2000,
        tingkat_interaksi=5.0,
        nomor_kontak=None,
        detail_url=f"https://example.com/{username}",
        scraped_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# 20.1 / 20.2 – Class instantiation
# ---------------------------------------------------------------------------

class TestScraperOrchestratorInit:
    def test_init_creates_all_components(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        assert orchestrator._config is config
        assert orchestrator._rate_limiter is not None
        assert orchestrator._traffic_controller is not None
        assert orchestrator._error_analyzer is not None
        assert orchestrator._data_store is not None
        assert orchestrator._deduplicator is not None
        assert orchestrator._validator is not None
        assert orchestrator._html_parser is not None
        assert orchestrator._extractor is not None
        assert orchestrator._session_manager is not None
        assert orchestrator._captcha_handler is not None
        assert orchestrator._fingerprint_generator is not None
        assert orchestrator._browser_engine is not None
        assert orchestrator._behavioral_simulator is not None

    def test_init_sets_running_false(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        assert orchestrator._running is False

    def test_init_sets_current_page_one(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        assert orchestrator._current_page == 1


# ---------------------------------------------------------------------------
# 20.6 – Progress reporting
# ---------------------------------------------------------------------------

class TestGetProgress:
    def test_initial_progress(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        progress = orchestrator.get_progress()

        assert isinstance(progress, Progress)
        assert progress.current_page == 1
        assert progress.total_scraped == 0
        assert progress.unique_count == 0
        assert progress.duplicate_count == 0
        assert progress.errors == 0

    def test_progress_reflects_deduplicator_state(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        orchestrator._deduplicator.add(_make_affiliator("user1"))
        orchestrator._deduplicator.add(_make_affiliator("user2"))
        orchestrator._deduplicator.add(_make_affiliator("user1"))  # duplicate

        progress = orchestrator.get_progress()
        assert progress.unique_count == 2
        assert progress.duplicate_count == 1
        assert progress.total_scraped == 3


# ---------------------------------------------------------------------------
# 20.8 – Resume from checkpoint
# ---------------------------------------------------------------------------

class TestResume:
    @pytest.mark.asyncio
    async def test_resume_restores_known_usernames(self):
        """Resume should pre-populate the deduplicator with checkpoint usernames."""
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        checkpoint = Checkpoint(
            last_list_page=3,
            last_affiliator_index=0,
            scraped_usernames={"alice", "bob"},
            timestamp=datetime.now(),
        )

        # Patch _run_scraping_loop to avoid real browser calls
        async def fake_loop():
            return ScrapingResult(
                total_scraped=2,
                unique_affiliators=2,
                duplicates_found=0,
                errors=0,
                captchas_encountered=0,
                duration=0.1,
                start_time=datetime.now(),
                end_time=datetime.now(),
            )

        orchestrator._run_scraping_loop = fake_loop

        result = await orchestrator.resume(checkpoint)

        # After resume, deduplicator should know about alice and bob
        assert orchestrator._deduplicator.is_duplicate(_make_affiliator("alice"))
        assert orchestrator._deduplicator.is_duplicate(_make_affiliator("bob"))
        assert not orchestrator._deduplicator.is_duplicate(_make_affiliator("charlie"))

    @pytest.mark.asyncio
    async def test_resume_sets_current_page(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        checkpoint = Checkpoint(
            last_list_page=5,
            last_affiliator_index=0,
            scraped_usernames=set(),
            timestamp=datetime.now(),
        )

        async def fake_loop():
            return ScrapingResult(
                total_scraped=0,
                unique_affiliators=0,
                duplicates_found=0,
                errors=0,
                captchas_encountered=0,
                duration=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
            )

        orchestrator._run_scraping_loop = fake_loop
        await orchestrator.resume(checkpoint)

        assert orchestrator._current_page == 5


# ---------------------------------------------------------------------------
# 20.9 – Stop method
# ---------------------------------------------------------------------------

class TestStop:
    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        orchestrator._running = True

        # Patch browser close and data store save to avoid real I/O
        orchestrator._browser_engine.close = AsyncMock()
        orchestrator._data_store.save = MagicMock()
        orchestrator._deduplicator.add(_make_affiliator("user1"))

        with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
            await orchestrator.stop()

        assert orchestrator._running is False

    @pytest.mark.asyncio
    async def test_stop_saves_partial_results(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        orchestrator._running = True

        orchestrator._deduplicator.add(_make_affiliator("user1"))
        orchestrator._deduplicator.add(_make_affiliator("user2"))

        save_mock = MagicMock()
        orchestrator._data_store.save = save_mock
        orchestrator._browser_engine.close = AsyncMock()

        with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
            await orchestrator.stop()

        save_mock.assert_called_once()
        saved_data = save_mock.call_args[0][0]
        assert len(saved_data) == 2


# ---------------------------------------------------------------------------
# 20.7 – Checkpoint saving
# ---------------------------------------------------------------------------

class TestCheckpointSaving:
    @pytest.mark.asyncio
    async def test_save_checkpoint_creates_file(self, tmp_path):
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)
        orchestrator._current_page = 3
        orchestrator._deduplicator.add(_make_affiliator("user1"))

        await orchestrator._save_checkpoint()

        checkpoint_path = output_path.replace(".json", "_checkpoint.json")
        loaded = Checkpoint.load(checkpoint_path)
        assert loaded.last_list_page == 3
        assert "user1" in loaded.scraped_usernames

    @pytest.mark.asyncio
    async def test_save_checkpoint_includes_all_usernames(self, tmp_path):
        output_path = str(tmp_path / "affiliators.json")
        config = _make_config(output_path=output_path)
        orchestrator = ScraperOrchestrator(config)

        for i in range(5):
            orchestrator._deduplicator.add(_make_affiliator(f"user{i}"))

        await orchestrator._save_checkpoint()

        checkpoint_path = output_path.replace(".json", "_checkpoint.json")
        loaded = Checkpoint.load(checkpoint_path)
        assert len(loaded.scraped_usernames) == 5


# ---------------------------------------------------------------------------
# 20.3 / 20.4 / 20.5 – Main loop (mocked browser)
# ---------------------------------------------------------------------------

class TestStartWithMockedBrowser:
    @pytest.mark.asyncio
    async def test_start_returns_scraping_result(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        # Patch _run_scraping_loop to avoid real browser
        async def fake_loop():
            return ScrapingResult(
                total_scraped=5,
                unique_affiliators=5,
                duplicates_found=0,
                errors=0,
                captchas_encountered=0,
                duration=1.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
            )

        orchestrator._run_scraping_loop = fake_loop
        result = await orchestrator.start()

        assert isinstance(result, ScrapingResult)
        assert result.total_scraped == 5

    @pytest.mark.asyncio
    async def test_start_resets_state(self):
        config = _make_config()
        orchestrator = ScraperOrchestrator(config)
        orchestrator._current_page = 99
        orchestrator._errors = 10

        async def fake_loop():
            return ScrapingResult(
                total_scraped=0,
                unique_affiliators=0,
                duplicates_found=0,
                errors=0,
                captchas_encountered=0,
                duration=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
            )

        orchestrator._run_scraping_loop = fake_loop
        await orchestrator.start()

        assert orchestrator._current_page == 1
        assert orchestrator._errors == 0


# ---------------------------------------------------------------------------
# 20.5 – Data merging
# ---------------------------------------------------------------------------

class TestMergeData:
    def test_merge_uses_detail_values_over_entry(self):
        from src.core.affiliator_extractor import AffiliatorDetail, AffiliatorEntry

        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        entry = AffiliatorEntry(
            username="entry_user",
            kategori="Fashion",
            pengikut=100,
            gmv=1000.0,
            produk_terjual=10,
            rata_rata_tayangan=500,
            tingkat_interaksi=2.0,
            detail_url="https://example.com/entry_user",
        )
        detail = AffiliatorDetail(
            username="detail_user",
            kategori="Beauty",
            pengikut=200,
            gmv=2000.0,
            produk_terjual=20,
            rata_rata_tayangan=1000,
            tingkat_interaksi=4.0,
            nomor_kontak="081234567890",
        )

        result = orchestrator._merge_data(entry, detail, "https://example.com/detail_user")

        assert result is not None
        assert result.username == "detail_user"
        assert result.kategori == "Beauty"
        assert result.pengikut == 200
        assert result.nomor_kontak == "081234567890"

    def test_merge_falls_back_to_entry_when_detail_missing(self):
        from src.core.affiliator_extractor import AffiliatorDetail, AffiliatorEntry

        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        entry = AffiliatorEntry(
            username="entry_user",
            kategori="Fashion",
            pengikut=100,
            gmv=1000.0,
            produk_terjual=10,
            rata_rata_tayangan=500,
            tingkat_interaksi=2.0,
            detail_url="https://example.com/entry_user",
        )
        detail = AffiliatorDetail(
            username=None,
            kategori=None,
            pengikut=None,
            gmv=None,
            produk_terjual=None,
            rata_rata_tayangan=None,
            tingkat_interaksi=None,
            nomor_kontak=None,
        )

        result = orchestrator._merge_data(entry, detail, "https://example.com/entry_user")

        assert result is not None
        assert result.username == "entry_user"
        assert result.kategori == "Fashion"
        assert result.pengikut == 100

    def test_merge_returns_none_when_no_username(self):
        from src.core.affiliator_extractor import AffiliatorDetail, AffiliatorEntry

        config = _make_config()
        orchestrator = ScraperOrchestrator(config)

        entry = AffiliatorEntry(
            username=None,
            kategori=None,
            pengikut=None,
            gmv=None,
            produk_terjual=None,
            rata_rata_tayangan=None,
            tingkat_interaksi=None,
            detail_url="https://example.com/unknown",
        )
        detail = AffiliatorDetail(
            username=None,
            kategori=None,
            pengikut=None,
            gmv=None,
            produk_terjual=None,
            rata_rata_tayangan=None,
            tingkat_interaksi=None,
            nomor_kontak=None,
        )

        result = orchestrator._merge_data(entry, detail, "https://example.com/unknown")
        assert result is None
