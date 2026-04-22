"""TLS Client wrapper for browser TLS fingerprint mimicry.

Wraps the `tls-client` library (which uses a Go-based TLS implementation)
to provide browser-realistic TLS handshakes including:
- Browser-specific cipher suites (automatically selected per preset)
- HTTP/2 with realistic SETTINGS frames
- Randomized TLS extension order
- Browser presets: Chrome 120, Firefox 120, Safari 16

Cipher suite handling:
    tls-client manages cipher suites automatically via browser presets.
    Each preset uses the exact cipher suite order that the real browser
    sends, so no manual randomization is needed. The presets are:

    chrome_120:
        TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384,
        TLS_CHACHA20_POLY1305_SHA256, ECDHE-ECDSA-AES128-GCM-SHA256,
        ECDHE-RSA-AES128-GCM-SHA256, ECDHE-ECDSA-AES256-GCM-SHA384, ...

    firefox_120:
        TLS_AES_128_GCM_SHA256, TLS_CHACHA20_POLY1305_SHA256,
        TLS_AES_256_GCM_SHA384, ECDHE-ECDSA-AES128-GCM-SHA256, ...

    safari_16_0:
        TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384,
        TLS_CHACHA20_POLY1305_SHA256, ECDHE-ECDSA-AES256-GCM-SHA384, ...

Falls back gracefully to aiohttp if tls-client is not available.
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Any

from src.core.http_client import Cookie, Response

logger = logging.getLogger(__name__)

# Browser preset names supported by tls-client
BROWSER_PRESETS = {
    "chrome": "chrome_120",
    "firefox": "firefox_120",
    "safari": "safari_16_0",
}

# All available presets for random selection
ALL_PRESETS = list(BROWSER_PRESETS.values())

# HTTP/2 SETTINGS frames per browser (for documentation / reference).
# tls-client applies these automatically via the preset.
# Format: {SETTINGS_ID: value}
HTTP2_SETTINGS = {
    "chrome_120": {
        # HEADER_TABLE_SIZE=65536, ENABLE_PUSH=0,
        # INITIAL_WINDOW_SIZE=6291456, MAX_HEADER_LIST_SIZE=262144
        "HEADER_TABLE_SIZE": 65536,
        "ENABLE_PUSH": 0,
        "INITIAL_WINDOW_SIZE": 6291456,
        "MAX_HEADER_LIST_SIZE": 262144,
    },
    "firefox_120": {
        # HEADER_TABLE_SIZE=65536, INITIAL_WINDOW_SIZE=131072,
        # MAX_FRAME_SIZE=16384
        "HEADER_TABLE_SIZE": 65536,
        "INITIAL_WINDOW_SIZE": 131072,
        "MAX_FRAME_SIZE": 16384,
    },
    "safari_16_0": {
        # HEADER_TABLE_SIZE=4096, ENABLE_PUSH=1,
        # INITIAL_WINDOW_SIZE=2097152, MAX_HEADER_LIST_SIZE=16384
        "HEADER_TABLE_SIZE": 4096,
        "ENABLE_PUSH": 1,
        "INITIAL_WINDOW_SIZE": 2097152,
        "MAX_HEADER_LIST_SIZE": 16384,
    },
}

try:
    import tls_client as _tls_client
    HAS_TLS_CLIENT = True
except ImportError:
    _tls_client = None  # type: ignore[assignment]
    HAS_TLS_CLIENT = False
    logger.warning(
        "tls-client library not available; TLS fingerprinting disabled. "
        "Install with: pip install tls-client"
    )


class TLSClient:
    """
    HTTP client that uses tls-client for browser TLS fingerprint mimicry.

    Provides the same interface as HTTPClient (get, post, set_cookies,
    get_cookies) so it can be used as a drop-in replacement.

    When tls-client is not installed, raises ImportError on instantiation
    unless allow_fallback=True, in which case it logs a warning.

    Browser presets:
        - "chrome_120"  : Chrome 120 TLS fingerprint
        - "firefox_120" : Firefox 120 TLS fingerprint
        - "safari_16_0" : Safari 16.0 TLS fingerprint
    """

    TIMEOUT_SECONDS = 30

    def __init__(
        self,
        browser_preset: Optional[str] = None,
        random_tls_extension_order: bool = True,
    ):
        """
        Initialize TLS client with a browser preset.

        Args:
            browser_preset: tls-client preset name (e.g. "chrome_120").
                            If None, a random preset is chosen.
            random_tls_extension_order: Randomize TLS extension order to
                                        further evade fingerprinting.
        """
        if not HAS_TLS_CLIENT:
            raise ImportError(
                "tls-client is not installed. Install with: pip install tls-client"
            )

        if browser_preset is None:
            browser_preset = random.choice(ALL_PRESETS)

        self._preset = browser_preset
        self._random_tls_extension_order = random_tls_extension_order
        self._cookies: List[Cookie] = []
        self._session = _tls_client.Session(
            client_identifier=browser_preset,
            random_tls_extension_order=random_tls_extension_order,
        )

    @property
    def browser_preset(self) -> str:
        """Return the active browser preset name."""
        return self._preset

    def _build_headers(
        self, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build browser-realistic headers."""
        base: Dict[str, str] = {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
        if extra_headers:
            base.update(extra_headers)
        return base

    def _apply_cookies_to_session(self) -> None:
        """Push internal cookie list into the tls-client session."""
        for cookie in self._cookies:
            self._session.cookies.set(
                cookie.name,
                cookie.value,
                domain=cookie.domain or "",
            )

    def _sync_cookies_from_session(self) -> None:
        """Pull cookies from tls-client session back into internal list."""
        new_cookies: List[Cookie] = []
        for name, value in self._session.cookies.items():
            new_cookies.append(Cookie(name=name, value=value))
        self._cookies = new_cookies

    def _to_response(self, resp: Any) -> Response:
        """Convert a tls-client response to our Response dataclass."""
        body: bytes = resp.content if hasattr(resp, "content") else b""
        try:
            text = body.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            text = body.decode("latin-1", errors="replace") if body else ""

        headers: Dict[str, str] = {}
        if hasattr(resp, "headers") and resp.headers:
            headers = dict(resp.headers)

        return Response(
            status=resp.status_code,
            url=str(resp.url) if hasattr(resp, "url") else "",
            headers=headers,
            body=body,
            text=text,
        )

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Send a synchronous GET request with browser TLS fingerprint."""
        self._apply_cookies_to_session()
        merged = self._build_headers(headers)
        resp = self._session.get(url, headers=merged, timeout_seconds=self.TIMEOUT_SECONDS)
        self._sync_cookies_from_session()
        return self._to_response(resp)

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict] = None,
    ) -> Response:
        """Send a synchronous POST request with browser TLS fingerprint."""
        self._apply_cookies_to_session()
        merged = self._build_headers(headers)
        kwargs: Dict[str, Any] = {
            "headers": merged,
            "timeout_seconds": self.TIMEOUT_SECONDS,
        }
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        resp = self._session.post(url, **kwargs)
        self._sync_cookies_from_session()
        return self._to_response(resp)

    def set_cookies(self, cookies: List[Cookie]) -> None:
        """Set cookies for subsequent requests."""
        self._cookies = list(cookies)

    def get_cookies(self) -> List[Cookie]:
        """Return current cookies."""
        return list(self._cookies)

    def close(self) -> None:
        """Close the underlying tls-client session."""
        # tls-client sessions don't require explicit closing,
        # but we clear state for cleanliness.
        self._cookies = []


def create_tls_client(browser: str = "random") -> "TLSClient":
    """
    Factory function to create a TLSClient for a specific browser.

    Args:
        browser: One of "chrome", "firefox", "safari", or "random".
                 "random" picks a preset at random.

    Returns:
        TLSClient configured with the appropriate browser preset.

    Raises:
        ImportError: If tls-client library is not installed.
        ValueError: If an unknown browser name is provided.
    """
    if browser == "random":
        preset = random.choice(ALL_PRESETS)
    elif browser in BROWSER_PRESETS:
        preset = BROWSER_PRESETS[browser]
    else:
        raise ValueError(
            f"Unknown browser '{browser}'. "
            f"Choose from: {list(BROWSER_PRESETS.keys()) + ['random']}"
        )
    return TLSClient(browser_preset=preset)
