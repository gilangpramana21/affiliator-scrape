"""Scraper Orchestrator - main controller for the Tokopedia Affiliate Scraper."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set

from src.anti_detection.behavioral_simulator import BehavioralSimulator
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.control.rate_limiter import RateLimiter
from src.control.traffic_controller import TrafficConfig, TrafficController
from src.core.affiliator_extractor import AffiliatorEntry, AffiliatorExtractor
from src.core.captcha_handler import CAPTCHAHandler
from src.core.data_store import DataStore
from src.core.data_validator import DataValidator
from src.core.deduplicator import Deduplicator
from src.core.error_analyzer import Action, ErrorAnalyzer
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration
from src.models.models import AffiliatorData, Checkpoint, ScrapingResult

logger = logging.getLogger(__name__)


@dataclass
class Progress:
    """Current scraping progress snapshot."""
    current_page: int = 0
    total_scraped: int = 0
    unique_count: int = 0
    duplicate_count: int = 0
    errors: int = 0


class ScraperOrchestrator:
    """Main controller that coordinates the entire scraping workflow.

    Implements the main scraping loop:
    1. Iterate list pages with pagination
    2. For each affiliator, scrape the detail page
    3. Validate, deduplicate, and store data
    4. Save checkpoints periodically
    5. Handle errors and adjust behavior dynamically
    6. Respect traffic limits and session breaks
    """

    def __init__(self, config: Configuration) -> None:
        """Initialize scraper with configuration and all sub-components."""
        self._config = config

        # Control components
        self._rate_limiter = RateLimiter(
            min_delay=config.min_delay,
            max_delay=config.max_delay,
            jitter=config.jitter,
        )
        traffic_cfg = TrafficConfig(
            hourly_limit=config.hourly_limit,
            daily_limit=config.daily_limit,
            max_session_duration=config.max_session_duration,
            break_duration_min=config.break_duration_min,
            break_duration_max=config.break_duration_max,
            quiet_hours=list(config.quiet_hours),
        )
        self._traffic_controller = TrafficController(traffic_cfg)
        self._error_analyzer = ErrorAnalyzer()

        # Data components
        self._data_store = DataStore(
            output_format=config.output_format,
            output_path=config.output_path,
        )
        self._deduplicator = Deduplicator()
        self._validator = DataValidator()
        self._html_parser = HTMLParser()
        self._extractor = AffiliatorExtractor(parser=self._html_parser)

        # Session / auth
        self._session_manager = SessionManager()

        # CAPTCHA
        self._captcha_handler = CAPTCHAHandler(
            solver_type=config.captcha_solver,
            api_key=config.captcha_api_key,
        )

        # Anti-detection
        self._fingerprint_generator = FingerprintGenerator()
        self._browser_engine = BrowserEngine(engine_type=config.browser_engine)
        self._behavioral_simulator = BehavioralSimulator()

        # Runtime state
        self._running: bool = False
        self._current_page: int = 1
        self._errors: int = 0
        self._start_time: Optional[datetime] = None

        # Distributed mode components (initialised lazily in start())
        self._coordinator = None
        self._work_queue = None

        # Register SIGINT handler for graceful shutdown
        signal.signal(signal.SIGINT, self._sigint_handler)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> ScrapingResult:
        """Start the scraping operation from the beginning."""
        if self._config.require_cookie_file:
            if not self._config.cookie_file:
                raise ValueError("cookie_file must be configured when require_cookie_file is enabled")
            if not os.path.exists(self._config.cookie_file):
                raise FileNotFoundError(f"Cookie file not found: {self._config.cookie_file}")

        self._start_time = datetime.now()
        self._running = True
        self._current_page = 1
        self._deduplicator.clear()
        self._errors = 0

        # Initialise distributed mode if configured
        if self._config.distributed:
            self._setup_distributed()

        logger.info("Starting scraper from page 1")
        return await self._run_scraping_loop()

    async def resume(self, checkpoint: Checkpoint) -> ScrapingResult:
        """Resume scraping from a saved checkpoint.

        Restores deduplication state from the checkpoint so already-scraped
        usernames are not re-processed.
        """
        self._start_time = datetime.now()
        self._running = True
        self._current_page = checkpoint.last_list_page
        self._errors = 0

        # Restore deduplication state
        self._deduplicator.clear()
        for username in checkpoint.scraped_usernames:
            # Create a minimal placeholder so the deduplicator marks them seen
            placeholder = AffiliatorData(
                username=username,
                kategori="",
                pengikut=0,
                gmv=0.0,
                produk_terjual=0,
                rata_rata_tayangan=0,
                tingkat_interaksi=0.0,
                nomor_kontak=None,
                nomor_whatsapp=None,
                gmv_per_pembeli=0.0,
                gmv_harian=0.0,
                gmv_mingguan=0.0,
                gmv_bulanan=0.0,
                detail_url="",
                scraped_at=checkpoint.timestamp,
            )
            self._deduplicator.add(placeholder)

        logger.info(
            "Resuming scraper from page %d with %d known usernames",
            self._current_page,
            len(checkpoint.scraped_usernames),
        )
        return await self._run_scraping_loop()

    async def stop(self) -> None:
        """Gracefully stop scraping and save partial results."""
        logger.info("Stop requested – saving partial results")
        self._running = False
        await self._save_partial_results()
        await self._browser_engine.close()
        if self._coordinator is not None:
            self._coordinator.deregister_instance()

    def get_progress(self) -> Progress:
        """Return a snapshot of the current scraping progress."""
        return Progress(
            current_page=self._current_page,
            total_scraped=self._deduplicator.get_unique_count() + self._deduplicator.get_duplicate_count(),
            unique_count=self._deduplicator.get_unique_count(),
            duplicate_count=self._deduplicator.get_duplicate_count(),
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Internal – distributed mode setup
    # ------------------------------------------------------------------

    def _setup_distributed(self) -> None:
        """Initialise distributed coordinator and work queue.

        Called from start() when config.distributed is True.  Requires
        config.redis_url to be set.  A unique instance_id is generated
        if not provided in the config.
        """
        import redis as redis_lib
        from src.core.distributed_coordinator import DistributedCoordinator
        from src.core.distributed_queue import DistributedWorkQueue

        redis_client = redis_lib.from_url(self._config.redis_url, decode_responses=True)
        instance_id = self._config.instance_id or str(uuid.uuid4())

        self._coordinator = DistributedCoordinator(redis_client, instance_id)
        self._work_queue = DistributedWorkQueue(redis_client)

        self._coordinator.register_instance()
        # Recover any work left over from previously failed instances
        recovered = self._coordinator.recover_failed_instances(self._work_queue)
        if recovered:
            logger.info("Distributed mode: recovered %d work items from failed instances", recovered)
        logger.info("Distributed mode enabled (instance_id=%s)", instance_id)

    # ------------------------------------------------------------------
    # Internal – main loop
    # ------------------------------------------------------------------

    async def _run_scraping_loop(self) -> ScrapingResult:
        """Core scraping loop: iterate list pages and scrape each detail page."""
        # Generate fingerprint and launch browser
        fingerprint = self._fingerprint_generator.generate()
        await self._browser_engine.launch(fingerprint, headless=self._config.headless)
        if self._config.cookie_file and os.path.exists(self._config.cookie_file):
            await self._browser_engine.load_cookies_from_file(self._config.cookie_file)

        try:
            while self._running:
                # Traffic permission check
                if not await self._traffic_controller.check_permission():
                    logger.info("Traffic limit reached – waiting for window reset")
                    await self._traffic_controller.wait_for_window_reset()
                    if not self._running:
                        break

                # Session break check
                if self._traffic_controller.should_take_break():
                    logger.info("Session break triggered – saving checkpoint")
                    await self._save_checkpoint()
                    await self._traffic_controller.take_break()
                    # Regenerate fingerprint after break
                    fingerprint = self._fingerprint_generator.generate()
                    await self._browser_engine.close()
                    await self._browser_engine.launch(fingerprint, headless=self._config.headless)
                    if self._config.cookie_file and os.path.exists(self._config.cookie_file):
                        await self._browser_engine.load_cookies_from_file(self._config.cookie_file)

                if self._current_page > self._config.max_pages_per_run:
                    logger.warning(
                        "Stopping run due to max_pages_per_run limit (%d)",
                        self._config.max_pages_per_run,
                    )
                    break

                if self._errors >= self._config.max_errors_before_stop:
                    logger.error(
                        "Stopping run due to max_errors_before_stop limit (%d)",
                        self._config.max_errors_before_stop,
                    )
                    break

                if self._captcha_handler.captcha_encounter_count >= self._config.max_captchas_before_stop:
                    logger.error(
                        "Stopping run due to max_captchas_before_stop limit (%d)",
                        self._config.max_captchas_before_stop,
                    )
                    break

                # Rate limiting
                await self._rate_limiter.wait()

                # Build list page URL
                list_url = (
                    f"{self._config.base_url}"
                    f"{self._config.list_page_url}"
                    f"{self._config.list_page_query}"
                    f"{'&' if '?' in self._config.list_page_query else '?'}page={self._current_page}"
                )

                # Scrape the list page
                affiliators = await self._scrape_list_page(list_url)
                if affiliators is None:
                    # Fatal error on this page – stop
                    break

                # Scrape detail pages for each affiliator
                await self._scrape_detail_pages(affiliators)

                # Check for next page
                has_next = await self._has_next_page(list_url)
                if not has_next:
                    logger.info("No more pages – scraping complete")
                    break

                self._current_page += 1

        finally:
            # Final save
            all_data = self._deduplicator.get_all()
            if all_data:
                self._data_store.save(all_data)
                logger.info("Final save: %d unique affiliators", len(all_data))

            await self._browser_engine.close()

        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds()

        return ScrapingResult(
            total_scraped=self._deduplicator.get_unique_count() + self._deduplicator.get_duplicate_count(),
            unique_affiliators=self._deduplicator.get_unique_count(),
            duplicates_found=self._deduplicator.get_duplicate_count(),
            errors=self._errors,
            captchas_encountered=self._captcha_handler.captcha_encounter_count,
            duration=duration,
            start_time=self._start_time,
            end_time=end_time,
        )

    # ------------------------------------------------------------------
    # Internal – list page
    # ------------------------------------------------------------------

    async def _scrape_list_page(self, url: str) -> Optional[List[AffiliatorEntry]]:
        """Navigate to a list page and extract affiliator entries.

        Returns the list of entries, or None on unrecoverable error.
        """
        try:
            page = await self._browser_engine.navigate(url)
            self._traffic_controller.record_request()

            # Simulate human behavior
            await self._behavioral_simulator.scroll_page(page)
            await self._behavioral_simulator.idle_behavior(page, duration=2.0)

            # CAPTCHA check
            captcha_type = await self._captcha_handler.detect(page)
            if captcha_type:
                solved = await self._captcha_handler.solve(page, captcha_type)
                if not solved:
                    logger.error("Failed to solve CAPTCHA on list page %d", self._current_page)
                    self._errors += 1
                    return []
                await self._captcha_handler.wait_backoff()

            html = await self._browser_engine.get_html(page)
            doc = self._html_parser.parse(html)
            list_result = self._extractor.extract_list_page(doc)

            logger.info(
                "List page %d: found %d affiliators",
                self._current_page,
                len(list_result.affiliators),
            )
            return list_result.affiliators

        except Exception as exc:
            logger.error("Error scraping list page %d: %s", self._current_page, exc)
            self._errors += 1
            return []

    async def _has_next_page(self, list_url: str) -> bool:
        """Check if there is a next page by re-using the already-navigated page HTML.

        We re-navigate to avoid keeping stale page references; in practice the
        browser engine caches the last page so this is cheap.
        """
        try:
            page = await self._browser_engine.navigate(list_url)
            html = await self._browser_engine.get_html(page)
            doc = self._html_parser.parse(html)
            next_url = self._extractor.extract_next_page_url(doc)
            return next_url is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal – detail pages
    # ------------------------------------------------------------------

    async def _scrape_detail_pages(self, affiliators: List[AffiliatorEntry]) -> None:
        """Scrape the detail page for each affiliator entry."""
        for idx, entry in enumerate(affiliators):
            if not self._running:
                break

            if not entry.detail_url:
                logger.warning("Affiliator entry has no detail URL – skipping")
                continue

            # Occasionally skip detail page to simulate human behaviour (~7%)
            if random.random() < 0.07:
                logger.debug("Randomly skipping detail page for %s", entry.username)
                continue

            # Think time before navigating
            await self._behavioral_simulator.think_time(3.0, 8.0)

            # Rate limiting
            await self._rate_limiter.wait()

            # Traffic permission
            if not await self._traffic_controller.check_permission():
                await self._traffic_controller.wait_for_window_reset()

            await self._scrape_single_detail(entry)

            # Progress reporting every 10 affiliators
            total = self._deduplicator.get_unique_count() + self._deduplicator.get_duplicate_count()
            if total > 0 and total % 10 == 0:
                self._log_progress()

            # Periodic checkpoint save
            unique = self._deduplicator.get_unique_count()
            if unique > 0 and unique % self._config.save_interval == 0:
                await self._save_checkpoint()
                if self._config.incremental_save:
                    self._data_store.save(self._deduplicator.get_all())

    async def _scrape_single_detail(self, entry: AffiliatorEntry) -> None:
        """Scrape a single affiliator detail page and store the result."""
        detail_url = entry.detail_url
        try:
            page = await self._browser_engine.navigate(detail_url)
            self._traffic_controller.record_request()

            await self._behavioral_simulator.scroll_page(page)

            # CAPTCHA check
            captcha_type = await self._captcha_handler.detect(page)
            if captcha_type:
                solved = await self._captcha_handler.solve(page, captcha_type)
                if not solved:
                    logger.error("Failed to solve CAPTCHA on detail page %s", detail_url)
                    self._errors += 1
                    return
                await self._captcha_handler.wait_backoff()

            html = await self._browser_engine.get_html(page)
            doc = self._html_parser.parse(html)
            detail = self._extractor.extract_detail_page(doc, page_url=detail_url)

            # Merge list entry + detail into AffiliatorData
            affiliator = self._merge_data(entry, detail, detail_url)
            if affiliator is None:
                return

            # Validate
            validation = self._validator.validate(affiliator)
            if not validation.is_valid:
                logger.warning(
                    "Validation failed for %s: %s",
                    affiliator.username,
                    validation.errors,
                )

            # Deduplicate and store
            added = self._deduplicator.add(affiliator)
            if added:
                logger.debug("Stored affiliator: %s", affiliator.username)
            else:
                logger.info("Duplicate skipped: %s", affiliator.username)

        except Exception as exc:
            logger.error("Error scraping detail page %s: %s", detail_url, exc)
            self._errors += 1

    # ------------------------------------------------------------------
    # Internal – data merging
    # ------------------------------------------------------------------

    def _merge_data(
        self,
        entry: AffiliatorEntry,
        detail,
        detail_url: str,
    ) -> Optional[AffiliatorData]:
        """Merge list-page entry and detail-page data into AffiliatorData.

        Detail page values take precedence; list page values are used as
        fallback when the detail page is missing a field.
        """
        username = detail.username or entry.username
        if not username:
            logger.warning("Cannot create AffiliatorData: username is missing for %s", detail_url)
            return None

        return AffiliatorData(
            username=username,
            kategori=detail.kategori or entry.kategori or "",
            pengikut=detail.pengikut if detail.pengikut is not None else (entry.pengikut or 0),
            gmv=detail.gmv if detail.gmv is not None else (entry.gmv or 0.0),
            produk_terjual=(
                detail.produk_terjual
                if detail.produk_terjual is not None
                else (entry.produk_terjual or 0)
            ),
            rata_rata_tayangan=(
                detail.rata_rata_tayangan
                if detail.rata_rata_tayangan is not None
                else (entry.rata_rata_tayangan or 0)
            ),
            tingkat_interaksi=(
                detail.tingkat_interaksi
                if detail.tingkat_interaksi is not None
                else (entry.tingkat_interaksi or 0.0)
            ),
            nomor_kontak=detail.nomor_kontak,
            nomor_whatsapp=detail.nomor_whatsapp,
            gmv_per_pembeli=(
                detail.gmv_per_pembeli
                if detail.gmv_per_pembeli is not None
                else (entry.gmv_per_pembeli or 0.0)
            ),
            gmv_harian=(
                detail.gmv_harian
                if detail.gmv_harian is not None
                else (entry.gmv_harian or 0.0)
            ),
            gmv_mingguan=(
                detail.gmv_mingguan
                if detail.gmv_mingguan is not None
                else (entry.gmv_mingguan or 0.0)
            ),
            gmv_bulanan=(
                detail.gmv_bulanan
                if detail.gmv_bulanan is not None
                else (entry.gmv_bulanan or 0.0)
            ),
            detail_url=detail_url,
            scraped_at=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Internal – checkpoint / progress
    # ------------------------------------------------------------------

    async def _save_checkpoint(self) -> None:
        """Save a checkpoint to disk."""
        checkpoint = Checkpoint(
            last_list_page=self._current_page,
            last_affiliator_index=0,
            scraped_usernames={a.username for a in self._deduplicator.get_all()},
            timestamp=datetime.now(),
        )
        checkpoint_path = self._config.output_path.replace(
            "." + self._config.output_format, "_checkpoint.json"
        )
        try:
            checkpoint.save(checkpoint_path)
            logger.info("Checkpoint saved to %s (page %d)", checkpoint_path, self._current_page)
        except Exception as exc:
            logger.error("Failed to save checkpoint: %s", exc)

    async def _save_partial_results(self) -> None:
        """Save whatever data has been collected so far."""
        all_data = self._deduplicator.get_all()
        if all_data:
            try:
                self._data_store.save(all_data)
                logger.info("Partial results saved: %d affiliators", len(all_data))
            except Exception as exc:
                logger.error("Failed to save partial results: %s", exc)
        await self._save_checkpoint()

    def _log_progress(self) -> None:
        """Log current scraping progress."""
        progress = self.get_progress()
        logger.info(
            "Progress: page=%d scraped=%d unique=%d duplicates=%d errors=%d",
            progress.current_page,
            progress.total_scraped,
            progress.unique_count,
            progress.duplicate_count,
            progress.errors,
        )

    # ------------------------------------------------------------------
    # SIGINT handler
    # ------------------------------------------------------------------

    def _sigint_handler(self, signum, frame) -> None:
        """Handle SIGINT (Ctrl+C) by triggering graceful shutdown."""
        logger.warning("SIGINT received – initiating graceful shutdown")
        self._running = False
        # Schedule stop() in the running event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.stop())
        except RuntimeError:
            pass
