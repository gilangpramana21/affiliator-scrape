"""Error Analyzer for detecting bot detection signals and adjusting scraper behavior."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from src.core.http_client import Response

logger = logging.getLogger(__name__)


class Action(Enum):
    """Recommended actions based on error analysis."""
    CONTINUE = "continue"
    SLOW_DOWN = "slow_down"
    PAUSE = "pause"
    ABORT = "abort"
    USE_BROWSER = "use_browser"
    RETRY = "retry"


@dataclass
class ErrorAnalysis:
    """Result of analyzing an HTTP response for bot detection signals."""
    status_code: int
    is_bot_detection: bool = False
    is_rate_limit: bool = False
    is_redirect_loop: bool = False
    has_captcha: bool = False
    response_time: float = 0.0
    recommended_action: Action = Action.CONTINUE


class ErrorAnalyzer:
    """
    Analyzes HTTP responses for bot detection signals and adjusts scraper behavior.

    Maintains state across requests to detect patterns like consecutive errors
    and response time trends.
    """

    # Thresholds
    CONSECUTIVE_ERROR_THRESHOLD = 3
    REDIRECT_LOOP_THRESHOLD = 3
    RESPONSE_TIME_MULTIPLIER = 2.0
    ROLLING_WINDOW = 10

    # Patterns for JS challenge detection
    JS_CHALLENGE_PATTERNS = [
        r"cloudflare",
        r"cf-browser-verification",
        r"checking your browser",
        r"ddos-guard",
        r"just a moment",
        r"enable javascript",
        r"please wait",
    ]

    # Patterns for CAPTCHA detection
    CAPTCHA_PATTERNS = [
        r"recaptcha",
        r"hcaptcha",
        r"captcha",
        r"are you a robot",
        r"verify you are human",
    ]

    # Honeypot CSS patterns
    HONEYPOT_PATTERNS = [
        r'display\s*:\s*none',
        r'visibility\s*:\s*hidden',
        r'opacity\s*:\s*0',
        r'width\s*:\s*0',
        r'height\s*:\s*0',
        r'font-size\s*:\s*0',
        r'overflow\s*:\s*hidden.*width\s*:\s*1px',
        r'position\s*:\s*absolute.*left\s*:\s*-\d+',
        r'clip\s*:\s*rect\s*\(\s*0',
    ]

    def __init__(self) -> None:
        self.consecutive_errors: List[int] = []  # list of error status codes
        self.response_times: List[float] = []    # rolling window of response times
        self._url_visit_counts: dict[str, int] = {}

    def analyze(self, response: Response, response_time: float = 0.0) -> ErrorAnalysis:
        """
        Analyze an HTTP response for bot detection signals.

        Args:
            response: The HTTP response to analyze.
            response_time: Time taken for the request in seconds.

        Returns:
            ErrorAnalysis with detected signals and recommended action.
        """
        status = response.status
        content = response.text.lower() if response.text else ""

        # Track response time
        self._record_response_time(response_time)

        # Detect signals
        is_bot_detection = self._is_bot_detection(status, content)
        is_rate_limit = status == 429
        is_redirect_loop = self._check_redirect_loop(response.url)
        has_captcha = self._has_captcha(content)
        has_js_challenge = self._has_js_challenge(content)
        is_empty = self._is_empty_content(content)
        is_slow = self._is_slow_response(response_time)

        # Track consecutive errors
        if status in (403, 429):
            self.consecutive_errors.append(status)
        else:
            self.consecutive_errors.clear()

        # Log significant events
        if is_bot_detection:
            logger.warning("Potential bot detection event: HTTP %d at %s", status, response.url)
        if is_rate_limit:
            logger.warning("Rate limit hit (429) at %s", response.url)
        if is_redirect_loop:
            logger.error("Redirect loop detected at %s", response.url)
        if has_captcha:
            logger.warning("CAPTCHA detected at %s", response.url)

        # Determine recommended action
        action = self._determine_action(
            status=status,
            is_bot_detection=is_bot_detection,
            is_rate_limit=is_rate_limit,
            is_redirect_loop=is_redirect_loop,
            has_captcha=has_captcha,
            has_js_challenge=has_js_challenge,
            is_empty=is_empty,
            is_slow=is_slow,
        )

        return ErrorAnalysis(
            status_code=status,
            is_bot_detection=is_bot_detection,
            is_rate_limit=is_rate_limit,
            is_redirect_loop=is_redirect_loop,
            has_captcha=has_captcha,
            response_time=response_time,
            recommended_action=action,
        )

    def should_slow_down(self) -> bool:
        """
        Check if the scraper should slow down.

        Returns True if the last 3 responses had elevated response times
        or if a 429 was recently encountered.
        """
        # Check for recent 429
        recent = self.consecutive_errors[-3:] if self.consecutive_errors else []
        if 429 in recent:
            return True

        # Check for elevated response times in last 3 responses
        if len(self.response_times) >= 3:
            last_three = self.response_times[-3:]
            avg = self._rolling_average(exclude_last=3)
            if avg > 0 and all(t > avg * self.RESPONSE_TIME_MULTIPLIER for t in last_three):
                return True

        return False

    def should_pause(self) -> bool:
        """
        Check if the scraper should pause.

        Returns True if there are 3+ consecutive 403/429 responses.
        """
        if len(self.consecutive_errors) >= self.CONSECUTIVE_ERROR_THRESHOLD:
            return True
        return False

    def get_recommended_action(self) -> Action:
        """
        Get the recommended action based on current error state.

        Returns:
            Action enum value representing the recommended action.
        """
        if self.should_pause():
            return Action.PAUSE
        if self.should_slow_down():
            return Action.SLOW_DOWN
        return Action.CONTINUE

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _is_bot_detection(self, status: int, content: str) -> bool:
        """Return True if the response indicates bot detection."""
        if status == 403:
            return True
        if self._has_js_challenge(content):
            return True
        return False

    def _has_js_challenge(self, content: str) -> bool:
        """Detect JavaScript challenges (Cloudflare, etc.)."""
        for pattern in self.JS_CHALLENGE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _has_captcha(self, content: str) -> bool:
        """Detect CAPTCHA presence in page content."""
        for pattern in self.CAPTCHA_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _is_empty_content(self, content: str) -> bool:
        """Return True if the page content is empty or minimal."""
        return len(content.strip()) < 100

    def _check_redirect_loop(self, url: str) -> bool:
        """
        Track URL visits and detect redirect loops.

        A redirect loop is detected when the same URL is visited 3+ times.
        """
        self._url_visit_counts[url] = self._url_visit_counts.get(url, 0) + 1
        return self._url_visit_counts[url] >= self.REDIRECT_LOOP_THRESHOLD

    def _is_slow_response(self, response_time: float) -> bool:
        """Return True if response time is significantly above the rolling average."""
        if response_time <= 0:
            return False
        avg = self._rolling_average()
        if avg <= 0:
            return False
        return response_time > avg * self.RESPONSE_TIME_MULTIPLIER

    def _record_response_time(self, response_time: float) -> None:
        """Record a response time, maintaining a rolling window."""
        if response_time > 0:
            self.response_times.append(response_time)
            if len(self.response_times) > self.ROLLING_WINDOW:
                self.response_times = self.response_times[-self.ROLLING_WINDOW:]

    def _rolling_average(self, exclude_last: int = 0) -> float:
        """Compute rolling average of response times, optionally excluding last N."""
        times = self.response_times
        if exclude_last > 0:
            times = times[:-exclude_last] if len(times) > exclude_last else []
        if not times:
            return 0.0
        return sum(times) / len(times)

    def _determine_action(
        self,
        status: int,
        is_bot_detection: bool,
        is_rate_limit: bool,
        is_redirect_loop: bool,
        has_captcha: bool,
        has_js_challenge: bool,
        is_empty: bool,
        is_slow: bool,
    ) -> Action:
        """Determine the recommended action based on all signals."""
        # Highest priority: abort on redirect loop
        if is_redirect_loop:
            return Action.ABORT

        # Pause on 3+ consecutive errors
        if self.should_pause():
            return Action.PAUSE

        # CAPTCHA or JS challenge → use browser engine
        if has_captcha or has_js_challenge:
            return Action.USE_BROWSER

        # Empty content → retry with browser engine
        if is_empty and status == 200:
            return Action.USE_BROWSER

        # Rate limit → slow down
        if is_rate_limit:
            return Action.SLOW_DOWN

        # Bot detection (403) → slow down
        if is_bot_detection:
            return Action.SLOW_DOWN

        # Slow response → slow down
        if is_slow:
            return Action.SLOW_DOWN

        # Non-200 but not a special case → retry
        if status >= 400:
            return Action.RETRY

        return Action.CONTINUE

    def detect_coba_lagi(self, html: str) -> bool:
        """
        Detect "Coba lagi" blocking page from Tokopedia.

        This blocking page appears when:
        - Cookies are expired or invalid
        - IP is blocked or has low reputation
        - Tokopedia detects suspicious activity

        Args:
            html: Raw HTML string to analyze.

        Returns:
            True if "Coba lagi" blocking page is detected, False otherwise.
        """
        if not html:
            return False

        # Convert to lowercase for case-insensitive matching
        content = html.lower()

        # Patterns that indicate "Coba lagi" blocking page
        coba_lagi_patterns = [
            "coba lagi",           # Indonesian: "Try again"
            "try again",           # English version
            "silakan coba lagi",   # Indonesian: "Please try again"
            "please try again",    # English: "Please try again"
            "terjadi kesalahan",   # Indonesian: "An error occurred"
            "something went wrong" # English: "Something went wrong"
        ]

        # Check if any pattern exists in the content
        for pattern in coba_lagi_patterns:
            if pattern in content:
                logger.warning(f"'Coba lagi' blocking page detected (pattern: '{pattern}')")
                return True

        return False

    def detect_cookie_expiration(self, response: Response) -> bool:
        """
        Detect cookie expiration by checking for redirects to login page
        or session expired messages.

        Cookie expiration is indicated by:
        - Redirect to login page (URL contains /login, /signin, /auth)
        - Session expired messages in content
        - Authentication required messages

        Args:
            response: HTTP response to analyze.

        Returns:
            True if cookie expiration is detected, False otherwise.
        """
        if not response:
            return False

        # Check for redirect to login page
        url = response.url.lower()
        login_url_patterns = [
            "/login",
            "/signin",
            "/sign-in",
            "/auth",
            "/authenticate",
            "/masuk",  # Indonesian: "login"
        ]

        for pattern in login_url_patterns:
            if pattern in url:
                logger.warning(f"Cookie expiration detected: redirect to login page ({response.url})")
                return True

        # Check for session expired messages in content
        if response.text:
            content = response.text.lower()

            session_expired_patterns = [
                "session expired",
                "session has expired",
                "sesi berakhir",        # Indonesian: "session expired"
                "sesi telah berakhir",  # Indonesian: "session has expired"
                "login required",
                "please login",
                "silakan login",        # Indonesian: "please login"
                "authentication required",
                "autentikasi diperlukan",  # Indonesian: "authentication required"
                "unauthorized",
                "tidak terotorisasi",   # Indonesian: "unauthorized"
                "access denied",
                "akses ditolak",        # Indonesian: "access denied"
            ]

            for pattern in session_expired_patterns:
                if pattern in content:
                    logger.warning(f"Cookie expiration detected: session expired message (pattern: '{pattern}')")
                    return True

        return False

    @staticmethod
    def detect_honeypot_links(html: str) -> List[str]:
        """
        Detect honeypot links in HTML content.

        Honeypot links are hidden links used to trap bots. They are typically
        hidden via CSS (display:none, visibility:hidden, opacity:0, tiny dimensions).

        Args:
            html: Raw HTML string to analyze.

        Returns:
            List of href values from detected honeypot links.
        """
        honeypot_hrefs: List[str] = []

        # Find all <a> tags with inline style or within hidden containers
        # Pattern: <a ... style="...hidden..." href="...">
        anchor_pattern = re.compile(
            r'<a\b([^>]*)>',
            re.IGNORECASE | re.DOTALL,
        )

        honeypot_css_patterns = [
            r'display\s*:\s*none',
            r'visibility\s*:\s*hidden',
            r'opacity\s*:\s*0(?:[^.]|$)',
            r'width\s*:\s*0(?:px)?(?:\s*;|\s*")',
            r'height\s*:\s*0(?:px)?(?:\s*;|\s*")',
            r'font-size\s*:\s*0(?:px)?',
            r'position\s*:\s*absolute[^"]*left\s*:\s*-\d+',
            r'clip\s*:\s*rect\s*\(\s*0',
        ]

        for match in anchor_pattern.finditer(html):
            attrs = match.group(1)
            style_match = re.search(r'style\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
            if style_match:
                style = style_match.group(1)
                for css_pattern in honeypot_css_patterns:
                    if re.search(css_pattern, style, re.IGNORECASE):
                        href_match = re.search(r'href\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
                        if href_match:
                            honeypot_hrefs.append(href_match.group(1))
                        break

        return honeypot_hrefs
