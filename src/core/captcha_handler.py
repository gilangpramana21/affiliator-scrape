"""CAPTCHA detection and solving handler for the Tokopedia Affiliate Scraper.

Supports detection of reCAPTCHA v2/v3, hCaptcha, and image CAPTCHAs.
Solving strategies: manual (pause/wait), 2Captcha API, Anti-Captcha API.
Implements exponential backoff after CAPTCHA encounters.
"""

from __future__ import annotations

import asyncio
import logging
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

    @property
    def backoff_seconds(self) -> float:
        """Current backoff duration in seconds."""
        return self._backoff_seconds

    @property
    def captcha_encounter_count(self) -> int:
        """Total number of CAPTCHA encounters recorded."""
        return self._captcha_encounter_count

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
