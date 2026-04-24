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
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.affiliator_extractor import AffiliatorEntry
from src.core.captcha_handler import CAPTCHAHandler
from src.core.contact_extractor import ContactExtractor
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
        self._extractor = TokopediaExtractor(self._html_parser)

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
    # Internal – dynamic content handling
    # ------------------------------------------------------------------

    async def _wait_for_dynamic_content(self, page) -> None:
        """Wait for dynamic content to load on list pages."""
        try:
            # Wait for loading indicators to disappear
            loading_selectors = [
                "[class*='loading']",
                "[class*='spinner']", 
                "[class*='skeleton']"
            ]
            
            for selector in loading_selectors:
                try:
                    # Wait for loading elements to be hidden or removed (max 10 seconds)
                    await page.wait_for_selector(selector, state="hidden", timeout=10000)
                    logger.debug(f"Loading indicator {selector} disappeared")
                except Exception:
                    # Loading indicator might not exist, continue
                    pass
            
            # Wait for table rows to appear (max 15 seconds)
            try:
                await page.wait_for_selector("tbody tr", timeout=15000)
                logger.debug("Table rows detected")
            except Exception:
                logger.warning("No table rows found after waiting")
            
            # Additional wait for JavaScript to populate data
            await asyncio.sleep(3)
            
            # Check if we have actual data rows
            row_count = await page.evaluate("document.querySelectorAll('tbody tr').length")
            logger.debug(f"Found {row_count} table rows after dynamic loading")
            
            if row_count == 0:
                # Try scrolling to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                # Check again
                row_count = await page.evaluate("document.querySelectorAll('tbody tr').length")
                logger.debug(f"Found {row_count} table rows after scroll trigger")
                
        except Exception as e:
            logger.warning(f"Error waiting for dynamic content: {e}")

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

            # Wait for dynamic content to load
            await self._wait_for_dynamic_content(page)
            
            # Simulate human behavior
            await self._behavioral_simulator.scroll_page(page)
            await self._behavioral_simulator.idle_behavior(page, duration=2.0)

            # CAPTCHA handling with CaptchaSonic integration
            captcha_type = await self._captcha_handler.detect(page)
            if captcha_type:
                logger.info(f"CAPTCHA detected: {captcha_type.value}")
                
                # If using CaptchaSonic, wait for automatic solving
                if self._config.captcha_api_key and "sonic" in self._config.captcha_api_key:
                    logger.info("Using CaptchaSonic for automatic captcha solving...")
                    # Wait longer for CaptchaSonic to solve
                    await asyncio.sleep(10)  # Give CaptchaSonic time to work
                    
                    # Check if captcha is solved
                    captcha_still_present = await self._captcha_handler.detect(page)
                    if not captcha_still_present:
                        logger.info("CAPTCHA solved by CaptchaSonic!")
                        solved = True
                    else:
                        # Wait a bit more and try again
                        await asyncio.sleep(20)
                        captcha_still_present = await self._captcha_handler.detect(page)
                        solved = not captcha_still_present
                        if solved:
                            logger.info("CAPTCHA solved by CaptchaSonic (delayed)!")
                        else:
                            logger.error("CaptchaSonic failed to solve CAPTCHA")
                else:
                    # Use original solving method
                    solved = await self._captcha_handler.solve(page, captcha_type)
                
                if not solved:
                    logger.error("Failed to solve CAPTCHA on list page %d", self._current_page)
                    self._errors += 1
                    return []
                await self._captcha_handler.wait_backoff()
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

            # Handle Tokopedia's clickable row system
            if entry.detail_url == "CLICKABLE_ROW":
                # We need to click on the row to get the actual detail URL
                # This will be handled in _scrape_single_detail by clicking the row
                pass
            elif not entry.detail_url:
                # Skip entries without detail URLs for now
                logger.warning(f"Skipping {entry.username} - no detail URL available")
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

            await self._scrape_single_detail(entry, row_index=idx)

            # Progress reporting every 5 affiliators (reduced for testing)
            total = self._deduplicator.get_unique_count() + self._deduplicator.get_duplicate_count()
            if total > 0 and total % 5 == 0:
                self._log_progress()

            # Periodic checkpoint save
            unique = self._deduplicator.get_unique_count()
            if unique > 0 and unique % self._config.save_interval == 0:
                await self._save_checkpoint()
                if self._config.incremental_save:
                    self._data_store.save(self._deduplicator.get_all())

    async def _scrape_single_detail(self, entry: AffiliatorEntry, row_index: int = None) -> None:
        """Scrape a single affiliator detail page using new tab strategy.
        
        Opens detail page in a new tab to mimic natural user behavior and
        handle Tokopedia's custom puzzle CAPTCHA that appears on profile links.
        """
        detail_url = entry.detail_url
        detail_page = None
        
        try:
            # Check if we should pause due to consecutive puzzles
            if self._captcha_handler.should_pause_for_puzzles():
                await self._captcha_handler.wait_puzzle_pause()
            
            # Handle Tokopedia's clickable row system
            if detail_url == "CLICKABLE_ROW":
                detail_page = await self._handle_clickable_row(entry, row_index)
                if not detail_page:
                    logger.warning(f"Failed to open detail page for {entry.username} via row click, skipping")
                    return
                # Get the actual URL after clicking
                detail_url = detail_page.url
                logger.debug(f"Opened detail page via row click: {detail_url}")
            else:
                # Standard URL navigation
                if self._browser_engine.context is None:
                    raise RuntimeError("Browser context not available")
                    
                detail_page = await self._browser_engine.context.new_page()
                logger.debug(f"Opened new tab for detail page: {detail_url}")
                
                # Navigate to detail page
                await detail_page.goto(detail_url, wait_until="networkidle", timeout=30000)
                self._traffic_controller.record_request()
            
            # Wait for dynamic content to load with longer delay for public WiFi
            await asyncio.sleep(5)  # Increased from 2 to 5 seconds for public WiFi
            
            # Handle "Coba Lagi" message and public WiFi conditions
            await self._handle_coba_lagi_message(detail_page)
            await self._handle_public_wifi_conditions(detail_page)
            
            # Handle "Coba Lagi" message and Tokopedia puzzle
            await self._handle_coba_lagi_message(detail_page)
            
            # Handle Tokopedia puzzle if present
            if await self._captcha_handler.detect_tokopedia_puzzle(detail_page):
                logger.info(f"Tokopedia puzzle detected on {detail_url}")
                success = await self._captcha_handler.solve_tokopedia_puzzle(detail_page)
                if not success:
                    logger.error(f"Failed to bypass Tokopedia puzzle on {detail_url}")
                    self._errors += 1
                    return
            
            # Simulate human behavior
            await self._behavioral_simulator.scroll_page(detail_page)

            # Standard CAPTCHA check (reCAPTCHA, hCaptcha, etc.)
            captcha_type = await self._captcha_handler.detect(detail_page)
            if captcha_type:
                solved = await self._captcha_handler.solve(detail_page, captcha_type)
                if not solved:
                    logger.error("Failed to solve CAPTCHA on detail page %s", detail_url)
                    self._errors += 1
                    return
                await self._captcha_handler.wait_backoff()

            # Extract data from the page
            html = await detail_page.content()
            doc = self._html_parser.parse(html)
            detail = self._extractor.extract_detail_page(doc, page_url=detail_url)
            
            # Try interactive WhatsApp extraction if static extraction didn't find anything
            if not detail.nomor_whatsapp:
                interactive_whatsapp = await self._extract_whatsapp_interactive(detail_page, detail_url)
                if interactive_whatsapp:
                    detail.nomor_whatsapp = interactive_whatsapp
                    logger.info(f"Found WhatsApp via interactive extraction: {interactive_whatsapp}")

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
                logger.info("Stored affiliator: %s", affiliator.username)
            else:
                logger.info("Duplicate skipped: %s", affiliator.username)

        except Exception as exc:
            logger.error("Error scraping detail page %s: %s", detail_url, exc)
            self._errors += 1
        finally:
            # Always close the detail page tab
            if detail_page:
                try:
                    await detail_page.close()
                    logger.debug(f"Closed tab for detail page: {detail_url}")
                except Exception as exc:
                    logger.warning(f"Error closing tab: {exc}")

    async def _handle_clickable_row(self, entry: AffiliatorEntry, row_index: int) -> Optional:
        """Handle clicking on a table row to open creator detail page."""
        try:
            # Get the current active page
            current_page = None
            if self._browser_engine.context:
                pages = self._browser_engine.context.pages
                if pages:
                    current_page = pages[0]  # Use the first (main) page
            
            if not current_page:
                logger.error("No active page available for row clicking")
                return None
            
            # Ensure we're on the list page with fresh data
            try:
                rows = await current_page.query_selector_all("tbody tr")
                if len(rows) == 0:
                    # Navigate back to list page
                    list_url = (
                        f"{self._config.base_url}"
                        f"{self._config.list_page_url}"
                        f"{self._config.list_page_query}"
                        f"{'&' if '?' in self._config.list_page_query else '?'}page={self._current_page}"
                    )
                    
                    await current_page.goto(list_url, wait_until="domcontentloaded", timeout=20000)
                    await self._wait_for_dynamic_content(current_page)
                    rows = await current_page.query_selector_all("tbody tr")
                
            except Exception as e:
                logger.warning(f"Error ensuring list page state: {e}")
                return None
            
            # Validate row index
            if row_index is None or row_index >= len(rows):
                logger.error(f"Row index {row_index} out of range (found {len(rows)} rows)")
                return None
            
            target_row = rows[row_index]
            
            # Check if row is actually clickable
            cursor = await target_row.evaluate("el => getComputedStyle(el).cursor")
            if cursor != "pointer":
                logger.warning(f"Row {row_index} for {entry.username} doesn't appear clickable (cursor: {cursor})")
                return None
            
            # Listen for new page opening with shorter timeout
            new_page_promise = self._browser_engine.context.wait_for_event("page")
            
            # Click the row
            await target_row.click()
            logger.debug(f"Clicked row {row_index} for {entry.username}")
            
            # Wait for new page to open with shorter timeout
            try:
                detail_page = await asyncio.wait_for(new_page_promise, timeout=3.0)
                logger.debug(f"New page opened: {detail_page.url}")
                
                # Wait for the page to load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                return detail_page
                
            except asyncio.TimeoutError:
                logger.warning(f"No new page opened after clicking row for {entry.username}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling clickable row for {entry.username}: {e}")
            return None

    async def _extract_whatsapp_interactive(self, page, page_url: str) -> Optional[str]:
        """Extract WhatsApp number by interacting with clickable elements on the page.
        
        This method looks for WhatsApp icons, buttons, or social media elements
        that need to be clicked to reveal hidden contact information.
        """
        try:
            logger.debug(f"Starting interactive WhatsApp extraction on {page_url}")
            
            # Get baseline content before any interactions
            initial_content = await page.content()
            initial_phones = self._extract_phone_numbers_from_text(initial_content)
            
            # Find potentially clickable WhatsApp elements
            whatsapp_selectors = [
                # WhatsApp specific selectors
                "img[src*='whatsapp']",
                "img[alt*='whatsapp']", 
                "img[title*='whatsapp']",
                "[class*='whatsapp']",
                "[data-testid*='whatsapp']",
                
                # Social media and contact selectors
                "img[src*='social']",
                "img[src*='contact']", 
                "[class*='social']",
                "[class*='contact']",
                
                # Generic clickable elements that might contain contact info
                "button[class*='btn']",
                "a[class*='btn']",
                "[role='button']",
                "img[src*='icon']",
                "svg",
                ".icon"
            ]
            
            clickable_elements = []
            
            # Collect all potentially relevant clickable elements
            for selector in whatsapp_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            # Check if element is visible and enabled
                            is_visible = await element.is_visible()
                            is_enabled = await element.is_enabled()
                            
                            if is_visible and is_enabled:
                                # Get element attributes for scoring
                                tag_name = await element.evaluate("el => el.tagName")
                                class_name = await element.get_attribute("class") or ""
                                text = await element.text_content() or ""
                                src = await element.get_attribute("src") or ""
                                alt = await element.get_attribute("alt") or ""
                                title = await element.get_attribute("title") or ""
                                
                                # Score element for WhatsApp relevance
                                score = self._score_element_for_whatsapp({
                                    'tag': tag_name,
                                    'class': class_name.lower(),
                                    'text': text.lower(),
                                    'src': src.lower(),
                                    'alt': alt.lower(),
                                    'title': title.lower()
                                })
                                
                                if score > 0:
                                    clickable_elements.append({
                                        'element': element,
                                        'score': score,
                                        'info': f"{tag_name} - {class_name[:30]} - {text[:20]}"
                                    })
                                    
                        except Exception:
                            continue
                            
                except Exception:
                    continue
            
            # Sort by score (highest first) and test top candidates
            clickable_elements.sort(key=lambda x: x['score'], reverse=True)
            
            max_tests = min(5, len(clickable_elements))  # Test top 5 elements max
            logger.debug(f"Found {len(clickable_elements)} clickable elements, testing top {max_tests}")
            
            for i, elem_info in enumerate(clickable_elements[:max_tests]):
                try:
                    logger.debug(f"Testing element {i+1}: {elem_info['info']} (score: {elem_info['score']})")
                    
                    # Get content before click
                    before_content = await page.content()
                    before_phones = self._extract_phone_numbers_from_text(before_content)
                    
                    # Click the element
                    await elem_info['element'].click()
                    
                    # Wait for potential changes
                    await asyncio.sleep(2)
                    
                    # Check for new content
                    after_content = await page.content()
                    after_phones = self._extract_phone_numbers_from_text(after_content)
                    
                    # Look for new WhatsApp numbers
                    new_phones = set(after_phones) - set(before_phones)
                    if new_phones:
                        # Validate and normalize the new numbers
                        for phone in new_phones:
                            normalized = self._normalize_phone_number_interactive(phone)
                            if normalized:
                                logger.info(f"Found WhatsApp number via clicking: {normalized}")
                                return normalized
                    
                    # Check for modals/popups that might contain contact info
                    modal_selectors = [
                        "[class*='modal']",
                        "[class*='popup']", 
                        "[class*='dialog']",
                        "[role='dialog']",
                        "[class*='overlay']"
                    ]
                    
                    for modal_sel in modal_selectors:
                        try:
                            modals = await page.query_selector_all(modal_sel)
                            for modal in modals:
                                if await modal.is_visible():
                                    modal_text = await modal.text_content()
                                    if modal_text:
                                        modal_phones = self._extract_phone_numbers_from_text(modal_text)
                                        for phone in modal_phones:
                                            normalized = self._normalize_phone_number_interactive(phone)
                                            if normalized:
                                                logger.info(f"Found WhatsApp in modal: {normalized}")
                                                # Close modal before returning
                                                close_buttons = await modal.query_selector_all("button, [class*='close'], [aria-label*='close']")
                                                for close_btn in close_buttons:
                                                    try:
                                                        await close_btn.click()
                                                        await asyncio.sleep(1)
                                                        break
                                                    except:
                                                        continue
                                                return normalized
                        except Exception:
                            continue
                    
                    # Small delay between tests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Error clicking element {i+1}: {e}")
                    continue
            
            logger.debug(f"No WhatsApp number found via interactive extraction on {page_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error in interactive WhatsApp extraction: {e}")
            return None

    def _score_element_for_whatsapp(self, elem_info: dict) -> int:
        """Score element based on likelihood of containing WhatsApp contact info."""
        score = 0
        
        # High priority WhatsApp keywords
        whatsapp_keywords = ['whatsapp', 'wa']
        for keyword in whatsapp_keywords:
            if (keyword in elem_info['text'] or 
                keyword in elem_info['class'] or 
                keyword in elem_info['alt'] or 
                keyword in elem_info['title'] or
                keyword in elem_info['src']):
                score += 15
        
        # Medium priority contact keywords
        contact_keywords = ['contact', 'kontak', 'hubungi', 'social']
        for keyword in contact_keywords:
            if (keyword in elem_info['text'] or 
                keyword in elem_info['class'] or 
                keyword in elem_info['alt'] or 
                keyword in elem_info['title']):
                score += 8
        
        # Button/clickable indicators
        button_keywords = ['btn', 'button', 'click']
        for keyword in button_keywords:
            if keyword in elem_info['class']:
                score += 3
        
        # Icon elements (likely to be social media icons)
        if elem_info['tag'].lower() in ['img', 'svg'] or 'icon' in elem_info['class']:
            score += 2
        
        # Short text (likely buttons or icons)
        if len(elem_info['text']) <= 15 and len(elem_info['text']) > 0:
            score += 1
        
        return score

    def _extract_phone_numbers_from_text(self, text: str) -> List[str]:
        """Extract phone numbers from text content."""
        if not text:
            return []
        
        import re
        patterns = [
            r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',
            r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}',
            r'62\d{9,13}',
            r'\d{4}[\s-]?\d{4}[\s-]?\d{3,4}',
            r'wa\.me/(\d+)',
            r'whatsapp.*?(\d{10,15})'
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phones.extend(matches)
        
        # Clean and deduplicate
        clean_phones = []
        for phone in phones:
            clean = re.sub(r'[\s-]', '', str(phone))
            if len(clean) >= 8 and clean not in clean_phones:
                clean_phones.append(clean)
        
        return clean_phones

    async def _handle_coba_lagi_message(self, page) -> None:
        """Handle 'Coba Lagi' message by refreshing the page.
        
        This message appears when Tokopedia detects suspicious activity,
        especially common when using public WiFi or when IP reputation is low.
        """
        try:
            # Check for "Coba Lagi" text in various forms
            coba_lagi_patterns = [
                "coba lagi",
                "try again", 
                "silakan coba lagi",
                "please try again",
                "terjadi kesalahan",
                "something went wrong"
            ]
            
            page_content = await page.content()
            page_text = page_content.lower()
            
            # Check if any "coba lagi" pattern exists
            coba_lagi_detected = any(pattern in page_text for pattern in coba_lagi_patterns)
            
            if coba_lagi_detected:
                logger.info("'Coba Lagi' message detected - refreshing page")
                
                # Refresh the page
                await page.reload(wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                
                # Check again after refresh
                page_content_after = await page.content()
                page_text_after = page_content_after.lower()
                
                still_has_coba_lagi = any(pattern in page_text_after for pattern in coba_lagi_patterns)
                
                if still_has_coba_lagi:
                    logger.warning("'Coba Lagi' message still present after refresh - may need longer delay")
                    # Wait longer for public WiFi conditions
                    await asyncio.sleep(5)
                    
                    # Try one more refresh
                    await page.reload(wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(3)
                else:
                    logger.info("'Coba Lagi' message resolved after refresh")
            
        except Exception as e:
            logger.warning(f"Error handling 'Coba Lagi' message: {e}")

    async def _handle_public_wifi_conditions(self, page) -> None:
        """Handle conditions specific to public WiFi usage.
        
        Public WiFi often triggers more aggressive anti-bot measures:
        - More frequent CAPTCHAs
        - Rate limiting
        - "Coba Lagi" messages
        - IP reputation issues
        """
        try:
            # Longer delays for public WiFi
            base_delay = 3.0
            public_wifi_delay = base_delay * 1.5  # 50% longer delays
            
            await asyncio.sleep(public_wifi_delay)
            
            # Check for common public WiFi detection indicators
            indicators = [
                "[class*='rate-limit']",
                "[class*='blocked']", 
                "[class*='suspicious']",
                "text:coba lagi",
                "text:try again"
            ]
            
            for indicator in indicators:
                try:
                    elements = await page.query_selector_all(indicator)
                    if elements:
                        logger.info(f"Public WiFi restriction detected: {indicator}")
                        # Longer wait for public WiFi restrictions
                        await asyncio.sleep(10)
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error handling public WiFi conditions: {e}")

    def _normalize_phone_number_interactive(self, phone: str) -> Optional[str]:
        """Normalize phone number found via interactive extraction."""
        if not phone:
            return None
        
        import re
        # Remove all non-digit characters except +
        clean = re.sub(r'[^\d+]', '', phone)
        
        # Remove leading zeros and spaces
        clean = clean.lstrip('0')
        
        # Handle different formats
        if clean.startswith('+62'):
            # Already in +62 format
            if len(clean) >= 12:  # +62 + at least 9 digits
                return clean
        elif clean.startswith('62'):
            # Convert 62xxx to +62xxx
            if len(clean) >= 11:  # 62 + at least 9 digits
                return '+' + clean
        elif clean.startswith('8') and len(clean) >= 9:
            # Convert 8xxx to 08xxx (Indonesian mobile format)
            return '08' + clean
        elif len(clean) >= 10:
            # For other formats, try to convert to 08xxx if it looks like mobile
            # Indonesian mobile numbers typically start with 8 after country code
            if clean[0] in '8':
                return '08' + clean
            # Otherwise try +62 format
            elif clean[0] in '1234567':
                return '+62' + clean
        
        # If we can't normalize it properly, return None
        logger.debug(f"Could not normalize phone number from interactive extraction: {phone}")
        return None

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
