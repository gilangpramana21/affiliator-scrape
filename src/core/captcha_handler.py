"""CAPTCHA detection and solving handler for the Tokopedia Affiliate Scraper.

Supports detection of reCAPTCHA v2/v3, hCaptcha, and image CAPTCHAs.
Solving strategies: manual (pause/wait), 2Captcha API, Anti-Captcha API.
Implements exponential backoff after CAPTCHA encounters.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Optional

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class CAPTCHAType(Enum):
    """Supported CAPTCHA types."""

    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    IMAGE = "image"


# ---------------------------------------------------------------------------
# Selectors / indicators used for detection
# ---------------------------------------------------------------------------

_RECAPTCHA_V2_INDICATORS = [
    'iframe[src*="recaptcha/api2/anchor"]',
    'iframe[src*="recaptcha/api2/bframe"]',
    'div.g-recaptcha',
    '#g-recaptcha',
]

_RECAPTCHA_V3_SCRIPT_PATTERNS = [
    "recaptcha/api.js",
    "recaptcha/enterprise.js",
]

_HCAPTCHA_INDICATORS = [
    'iframe[src*="hcaptcha.com"]',
    'div.h-captcha',
    '#h-captcha',
]

_IMAGE_CAPTCHA_INDICATORS = [
    'img[src*="captcha"]',
    'input[name*="captcha"]',
    'div[class*="captcha"]',
    'form[action*="captcha"]',
]

# Maximum number of solve attempts before skipping the page
MAX_SOLVE_ATTEMPTS = 3

# Initial backoff in seconds; doubles after each CAPTCHA encounter
_INITIAL_BACKOFF = 5.0
_MAX_BACKOFF = 300.0  # 5 minutes cap


class CAPTCHAHandler:
    """Detects and solves CAPTCHAs encountered during scraping.

    Args:
        solver_type: One of ``"manual"``, ``"2captcha"``, or ``"anticaptcha"``.
        api_key: API key required for ``"2captcha"`` and ``"anticaptcha"`` solvers.
    """

    def __init__(self, solver_type: str = "manual", api_key: Optional[str] = None):
        if solver_type not in ("manual", "2captcha", "anticaptcha"):
            raise ValueError(
                f"Invalid solver_type '{solver_type}'. "
                "Must be one of: manual, 2captcha, anticaptcha"
            )
        if solver_type in ("2captcha", "anticaptcha") and not api_key:
            raise ValueError(f"api_key is required for solver_type '{solver_type}'")

        self.solver_type = solver_type
        self.api_key = api_key

        # Exponential backoff state
        self._backoff_seconds: float = _INITIAL_BACKOFF
        self._captcha_encounter_count: int = 0
        
        # Tokopedia puzzle tracking
        self._puzzle_encounter_count: int = 0
        self._consecutive_puzzles: int = 0
        self._last_puzzle_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def detect(self, page: Page) -> Optional[CAPTCHAType]:
        """Detect CAPTCHA type present on *page*.

        Checks page content for known CAPTCHA indicators in priority order:
        reCAPTCHA v2 → hCaptcha → reCAPTCHA v3 → image CAPTCHA.

        Returns the detected :class:`CAPTCHAType` or ``None`` if no CAPTCHA found.
        """
        url = page.url

        # reCAPTCHA v2 – iframe with anchor/bframe src
        if await self._detect_recaptcha_v2(page):
            logger.info("CAPTCHA detected: reCAPTCHA v2 on %s", url)
            return CAPTCHAType.RECAPTCHA_V2

        # hCaptcha – iframe with hcaptcha.com src
        if await self._detect_hcaptcha(page):
            logger.info("CAPTCHA detected: hCaptcha on %s", url)
            return CAPTCHAType.HCAPTCHA

        # reCAPTCHA v3 – script tag (no visible widget)
        if await self._detect_recaptcha_v3(page):
            logger.info("CAPTCHA detected: reCAPTCHA v3 on %s", url)
            return CAPTCHAType.RECAPTCHA_V3

        # Generic image CAPTCHA
        if await self._detect_image_captcha(page):
            logger.info("CAPTCHA detected: image CAPTCHA on %s", url)
            return CAPTCHAType.IMAGE

        return None

    async def solve(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Attempt to solve the CAPTCHA on *page*.

        Tries up to :data:`MAX_SOLVE_ATTEMPTS` times.  On success, saves
        session cookies and resets the backoff counter.  On failure after all
        attempts, applies exponential backoff and returns ``False``.

        Returns:
            ``True`` if the CAPTCHA was solved, ``False`` otherwise.
        """
        for attempt in range(1, MAX_SOLVE_ATTEMPTS + 1):
            logger.info(
                "Attempting CAPTCHA solve (attempt %d/%d) type=%s url=%s",
                attempt,
                MAX_SOLVE_ATTEMPTS,
                captcha_type.value,
                page.url,
            )
            try:
                success = await self._solve_once(page, captcha_type)
            except Exception as exc:  # noqa: BLE001
                logger.warning("CAPTCHA solve attempt %d raised: %s", attempt, exc)
                success = False

            if success:
                logger.info("CAPTCHA solved successfully on %s", page.url)
                await self._save_cookies(page)
                self._reset_backoff()
                return True

            logger.warning(
                "CAPTCHA solve attempt %d/%d failed on %s",
                attempt,
                MAX_SOLVE_ATTEMPTS,
                page.url,
            )

        # All attempts exhausted
        logger.error(
            "CAPTCHA could not be solved after %d attempts on %s – skipping page",
            MAX_SOLVE_ATTEMPTS,
            page.url,
        )
        self._increase_backoff()
        return False

    async def wait_backoff(self) -> None:
        """Sleep for the current backoff duration.

        Call this after a CAPTCHA encounter to implement exponential backoff
        before the next request.
        """
        if self._backoff_seconds > _INITIAL_BACKOFF:
            logger.info(
                "Exponential backoff: waiting %.1f seconds after CAPTCHA encounter",
                self._backoff_seconds,
            )
            await asyncio.sleep(self._backoff_seconds)

    async def detect_tokopedia_puzzle(self, page: Page) -> bool:
        """Detect Tokopedia's custom puzzle CAPTCHA.
        
        Tokopedia shows a custom puzzle when users click on affiliator profile links.
        This puzzle is different from standard CAPTCHAs and can be bypassed by refreshing.
        
        Returns:
            True if Tokopedia puzzle is detected, False otherwise.
        """
        try:
            # Wait for page to fully load and dynamic content to render
            await asyncio.sleep(2)
            
            # Check for puzzle-specific indicators
            puzzle_indicators = [
                # Common puzzle-related selectors
                'div[class*="puzzle"]',
                'div[class*="challenge"]',
                'div[class*="verification"]',
                'div[id*="puzzle"]',
                'div[id*="challenge"]',
                # Tokopedia-specific puzzle patterns
                'div[class*="captcha-container"]',
                'div[class*="anti-bot"]',
                'div[class*="security-check"]',
            ]
            
            for selector in puzzle_indicators:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # Check if element is visible
                        is_visible = await element.is_visible()
                        if is_visible:
                            logger.info(f"Tokopedia puzzle detected via selector: {selector}")
                            return True
                except Exception:
                    continue
            
            # Check page content for puzzle-related text (only if page content is accessible)
            try:
                content = await page.content()
                puzzle_text_patterns = [
                    "verifikasi",
                    "puzzle",
                    "challenge",
                    "security check",
                    "anti-bot",
                    "please wait",
                    "loading",
                ]
                
                content_lower = content.lower()
                for pattern in puzzle_text_patterns:
                    if pattern in content_lower:
                        logger.info(f"Tokopedia puzzle detected via text pattern: {pattern}")
                        return True
                        
            except Exception:
                # If we can't access content, skip text-based detection
                pass
            
            # Check for absence of expected profile data (indicates puzzle page)
            # Only do this if we can successfully query selectors
            try:
                profile_indicators = [
                    'div[class*="creator-profile"]',
                    'div[class*="profile-header"]',
                    'span[class*="follower"]',
                    'div[class*="contact"]',
                    'div[class*="stats"]',
                    'div[class*="gmv"]',
                ]
                
                profile_elements_found = 0
                successful_queries = 0
                
                for selector in profile_indicators:
                    try:
                        element = await page.query_selector(selector)
                        successful_queries += 1  # Count successful queries
                        if element and await element.is_visible():
                            profile_elements_found += 1
                    except Exception:
                        continue
                
                # Only consider insufficient profile data if we could actually query selectors
                # If all queries failed, we can't make a determination
                if successful_queries > 0 and profile_elements_found < 2:
                    logger.info("Tokopedia puzzle suspected: insufficient profile data visible")
                    return True
                    
            except Exception:
                # If we can't query selectors at all, assume no puzzle
                pass
            
            return False
            
        except Exception as exc:
            logger.warning(f"Error detecting Tokopedia puzzle: {exc}")
            return False

    async def solve_tokopedia_puzzle(self, page: Page) -> bool:
        """Solve Tokopedia puzzle by refreshing the page.
        
        Tokopedia's custom puzzle can usually be bypassed by simply refreshing
        the page. This method attempts up to 3 refreshes before giving up.
        
        Returns:
            True if puzzle was successfully bypassed, False otherwise.
        """
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Wait for page to fully load
                await asyncio.sleep(2)
                
                # Check if puzzle is still present
                if not await self.detect_tokopedia_puzzle(page):
                    if attempt == 0:
                        logger.info("Tokopedia puzzle already bypassed")
                    else:
                        logger.info("Tokopedia puzzle bypassed successfully")
                    self._record_puzzle_encounter(success=True)
                    return True
                
                logger.info(f"Tokopedia puzzle detected, refreshing page (attempt {attempt + 1}/{max_attempts})")
                
                # Refresh the page
                await page.reload(wait_until="networkidle", timeout=30000)
                
                # Wait for content to load after refresh
                await asyncio.sleep(3)
                
                # After refresh, verify that profile data is now visible
                if await self._verify_profile_data_visible(page):
                    logger.info("Tokopedia puzzle bypassed successfully after refresh")
                    self._record_puzzle_encounter(success=True)
                    return True
                    
            except Exception as exc:
                logger.warning(f"Error during Tokopedia puzzle solve attempt {attempt + 1}: {exc}")
                continue
        
        logger.warning("Failed to bypass Tokopedia puzzle after all attempts")
        self._record_puzzle_encounter(success=False)
        return False

    def _record_puzzle_encounter(self, success: bool = False) -> None:
        """Record a puzzle encounter and track consecutive failures."""
        current_time = time.time()
        self._puzzle_encounter_count += 1
        
        # Reset consecutive count if enough time has passed (5 minutes)
        if (self._last_puzzle_time and 
            current_time - self._last_puzzle_time > 300):
            self._consecutive_puzzles = 0
        
        if success:
            self._consecutive_puzzles = 0  # Reset on success
        else:
            self._consecutive_puzzles += 1
            
        self._last_puzzle_time = current_time
        
        # Log warning if consecutive puzzles are high
        if self._consecutive_puzzles >= 3:
            logger.warning(
                f"High consecutive puzzle count: {self._consecutive_puzzles}. "
                "Consider pausing scraping to avoid enhanced anti-bot measures."
            )

    def should_pause_for_puzzles(self) -> bool:
        """Check if scraper should pause due to consecutive puzzle encounters.
        
        Returns:
            True if 5+ consecutive puzzles encountered, False otherwise.
        """
        return self._consecutive_puzzles >= 5

    async def wait_puzzle_pause(self) -> None:
        """Wait for 5-10 minutes if too many consecutive puzzles encountered."""
        if self.should_pause_for_puzzles():
            pause_duration = random.uniform(300, 600)  # 5-10 minutes
            logger.warning(
                f"Pausing for {pause_duration:.0f} seconds due to {self._consecutive_puzzles} "
                "consecutive puzzle encounters"
            )
            await asyncio.sleep(pause_duration)
            self._consecutive_puzzles = 0  # Reset after pause

    async def _verify_profile_data_visible(self, page: Page) -> bool:
        """Verify that actual profile data is visible (not puzzle).
        
        Returns:
            True if profile data elements are visible, False otherwise.
        """
        try:
            # Look for expected profile elements with timeout
            profile_indicators = [
                'div[class*="creator-profile"]',
                'div[class*="profile-header"]', 
                'span[class*="follower"]',
                'div[class*="contact"]',
                'div[class*="stats"]',
                'div[class*="gmv"]',
                # Generic profile indicators
                'h1, h2, h3',  # Profile name/title
                'img[src*="avatar"], img[src*="profile"]',  # Profile image
            ]
            
            visible_elements = 0
            for selector in profile_indicators:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element and await element.is_visible():
                        visible_elements += 1
                        if visible_elements >= 2:  # At least 2 profile elements visible
                            return True
                except Exception:
                    continue
            
            # Also check for non-empty text content (indicates loaded page)
            try:
                text_content = await page.evaluate("() => document.body.innerText.trim()")
                if text_content and len(text_content) > 100:  # Reasonable amount of content
                    return True
            except Exception:
                pass
            
            return False
            
        except Exception as exc:
            logger.warning(f"Error verifying profile data visibility: {exc}")
            return False

    @property
    def backoff_seconds(self) -> float:
        """Current backoff duration in seconds."""
        return self._backoff_seconds

    @property
    def captcha_encounter_count(self) -> int:
        """Total number of CAPTCHA encounters recorded."""
        return self._captcha_encounter_count
    
    @property
    def puzzle_encounter_count(self) -> int:
        """Total number of Tokopedia puzzle encounters recorded."""
        return self._puzzle_encounter_count
    
    @property
    def consecutive_puzzle_count(self) -> int:
        """Number of consecutive puzzle encounters."""
        return self._consecutive_puzzles

    # ------------------------------------------------------------------
    # Detection helpers (17.3 – 17.5)
    # ------------------------------------------------------------------

    async def _detect_recaptcha_v2(self, page: Page) -> bool:
        """Return True if reCAPTCHA v2 indicators are found on the page."""
        for selector in _RECAPTCHA_V2_INDICATORS:
            try:
                element = await page.query_selector(selector)
                if element is not None:
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    async def _detect_recaptcha_v3(self, page: Page) -> bool:
        """Return True if reCAPTCHA v3 script is loaded on the page."""
        try:
            content = await page.content()
            return any(pattern in content for pattern in _RECAPTCHA_V3_SCRIPT_PATTERNS)
        except Exception:  # noqa: BLE001
            return False

    async def _detect_hcaptcha(self, page: Page) -> bool:
        """Return True if hCaptcha indicators are found on the page."""
        for selector in _HCAPTCHA_INDICATORS:
            try:
                element = await page.query_selector(selector)
                if element is not None:
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    async def _detect_image_captcha(self, page: Page) -> bool:
        """Return True if generic image CAPTCHA indicators are found."""
        for selector in _IMAGE_CAPTCHA_INDICATORS:
            try:
                element = await page.query_selector(selector)
                if element is not None:
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    # ------------------------------------------------------------------
    # Solving helpers (17.6 – 17.8)
    # ------------------------------------------------------------------

    async def _solve_once(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Dispatch to the configured solver strategy."""
        self._captcha_encounter_count += 1

        if self.solver_type == "manual":
            return await self._solve_manual(page, captcha_type)
        elif self.solver_type == "2captcha":
            return await self._solve_2captcha(page, captcha_type)
        elif self.solver_type == "anticaptcha":
            return await self._solve_anticaptcha(page, captcha_type)
        return False

    async def _solve_manual(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Pause execution and wait for the user to solve the CAPTCHA manually.

        Prints a message to stdout and blocks until the user presses Enter.
        """
        print(
            f"\n[CAPTCHA] {captcha_type.value} detected on: {page.url}\n"
            "Please solve the CAPTCHA in the browser window, then press Enter to continue..."
        )
        # Use asyncio to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input)
        logger.info("User confirmed CAPTCHA solved manually on %s", page.url)
        return True

    async def _solve_2captcha(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Solve CAPTCHA using the 2Captcha API service.

        Uses the ``twocaptcha`` (2captcha-python) library.
        """
        try:
            from twocaptcha import TwoCaptcha  # type: ignore[import]
        except ImportError:
            logger.error("2captcha-python library not installed. Run: pip install 2captcha-python")
            return False

        solver = TwoCaptcha(self.api_key)

        try:
            if captcha_type == CAPTCHAType.RECAPTCHA_V2:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    logger.warning("Could not extract reCAPTCHA v2 site key from %s", page.url)
                    return False
                result = solver.recaptcha(sitekey=site_key, url=page.url)
                token = result.get("code", "")
                if token:
                    await self._inject_recaptcha_token(page, token)
                    return True

            elif captcha_type == CAPTCHAType.RECAPTCHA_V3:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    logger.warning("Could not extract reCAPTCHA v3 site key from %s", page.url)
                    return False
                result = solver.recaptcha(sitekey=site_key, url=page.url, version="v3")
                token = result.get("code", "")
                if token:
                    await self._inject_recaptcha_token(page, token)
                    return True

            elif captcha_type == CAPTCHAType.HCAPTCHA:
                site_key = await self._get_hcaptcha_site_key(page)
                if not site_key:
                    logger.warning("Could not extract hCaptcha site key from %s", page.url)
                    return False
                result = solver.hcaptcha(sitekey=site_key, url=page.url)
                token = result.get("code", "")
                if token:
                    await self._inject_hcaptcha_token(page, token)
                    return True

            else:
                logger.warning("2Captcha: unsupported CAPTCHA type %s", captcha_type.value)
                return False

        except Exception as exc:  # noqa: BLE001
            logger.warning("2Captcha solve error: %s", exc)
            return False

        return False

    async def _solve_anticaptcha(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Solve CAPTCHA using the Anti-Captcha API service.

        Uses the ``python-anticaptcha`` library.
        """
        try:
            from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless  # type: ignore[import]
            from anticaptchaofficial.recaptchav3proxyless import recaptchaV3Proxyless  # type: ignore[import]
            from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless  # type: ignore[import]
        except ImportError:
            logger.error(
                "python-anticaptcha library not installed. Run: pip install python-anticaptcha"
            )
            return False

        try:
            if captcha_type == CAPTCHAType.RECAPTCHA_V2:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    return False
                solver = recaptchaV2Proxyless()
                solver.set_verbose(0)
                solver.set_key(self.api_key)
                solver.set_website_url(page.url)
                solver.set_website_key(site_key)
                token = solver.solve_and_return_solution()
                if token:
                    await self._inject_recaptcha_token(page, token)
                    return True

            elif captcha_type == CAPTCHAType.RECAPTCHA_V3:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    return False
                solver = recaptchaV3Proxyless()
                solver.set_verbose(0)
                solver.set_key(self.api_key)
                solver.set_website_url(page.url)
                solver.set_website_key(site_key)
                solver.set_page_action("verify")
                solver.set_min_score(0.3)
                token = solver.solve_and_return_solution()
                if token:
                    await self._inject_recaptcha_token(page, token)
                    return True

            elif captcha_type == CAPTCHAType.HCAPTCHA:
                site_key = await self._get_hcaptcha_site_key(page)
                if not site_key:
                    return False
                solver = hCaptchaProxyless()
                solver.set_verbose(0)
                solver.set_key(self.api_key)
                solver.set_website_url(page.url)
                solver.set_website_key(site_key)
                token = solver.solve_and_return_solution()
                if token:
                    await self._inject_hcaptcha_token(page, token)
                    return True

            else:
                logger.warning("Anti-Captcha: unsupported CAPTCHA type %s", captcha_type.value)
                return False

        except Exception as exc:  # noqa: BLE001
            logger.warning("Anti-Captcha solve error: %s", exc)
            return False

        return False

    # ------------------------------------------------------------------
    # Token injection helpers
    # ------------------------------------------------------------------

    async def _inject_recaptcha_token(self, page: Page, token: str) -> None:
        """Inject a solved reCAPTCHA token into the page."""
        await page.evaluate(
            """(token) => {
                const el = document.getElementById('g-recaptcha-response');
                if (el) { el.value = token; }
                if (typeof ___grecaptcha_cfg !== 'undefined') {
                    Object.entries(___grecaptcha_cfg.clients).forEach(([key, client]) => {
                        const callback = client.l || client.callback;
                        if (typeof callback === 'function') { callback(token); }
                    });
                }
            }""",
            token,
        )

    async def _inject_hcaptcha_token(self, page: Page, token: str) -> None:
        """Inject a solved hCaptcha token into the page."""
        await page.evaluate(
            """(token) => {
                const el = document.querySelector('[name="h-captcha-response"]');
                if (el) { el.value = token; }
            }""",
            token,
        )

    # ------------------------------------------------------------------
    # Site key extraction helpers
    # ------------------------------------------------------------------

    async def _get_recaptcha_site_key(self, page: Page) -> Optional[str]:
        """Extract the reCAPTCHA site key from the page."""
        try:
            # Try data-sitekey attribute on .g-recaptcha div
            key = await page.evaluate(
                """() => {
                    const el = document.querySelector('[data-sitekey]');
                    return el ? el.getAttribute('data-sitekey') : null;
                }"""
            )
            if key:
                return key
            # Try extracting from script src query param
            content = await page.content()
            import re
            match = re.search(r'[?&]render=([A-Za-z0-9_-]+)', content)
            if match:
                return match.group(1)
        except Exception:  # noqa: BLE001
            pass
        return None

    async def _get_hcaptcha_site_key(self, page: Page) -> Optional[str]:
        """Extract the hCaptcha site key from the page."""
        try:
            key = await page.evaluate(
                """() => {
                    const el = document.querySelector('[data-sitekey]');
                    return el ? el.getAttribute('data-sitekey') : null;
                }"""
            )
            return key
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Cookie saving (Requirement 20.6)
    # ------------------------------------------------------------------

    async def _save_cookies(self, page: Page) -> None:
        """Save session cookies after a successful CAPTCHA solve."""
        try:
            context = page.context
            cookies = await context.cookies()
            logger.info(
                "Saved %d session cookies after successful CAPTCHA solve on %s",
                len(cookies),
                page.url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to save cookies after CAPTCHA solve: %s", exc)

    # ------------------------------------------------------------------
    # Backoff management (17.9)
    # ------------------------------------------------------------------

    def _increase_backoff(self) -> None:
        """Double the backoff duration (capped at _MAX_BACKOFF)."""
        self._backoff_seconds = min(self._backoff_seconds * 2, _MAX_BACKOFF)
        logger.debug("Backoff increased to %.1f seconds", self._backoff_seconds)

    def _reset_backoff(self) -> None:
        """Reset backoff to initial value after a successful solve."""
        self._backoff_seconds = _INITIAL_BACKOFF
        logger.debug("Backoff reset to %.1f seconds", self._backoff_seconds)
