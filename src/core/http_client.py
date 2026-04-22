"""HTTP Client with anti-detection capabilities for the Tokopedia Affiliate Scraper"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import aiohttp
import yarl

from src.models.config import ProxyConfig
from src.models.models import BrowserFingerprint

logger = logging.getLogger(__name__)


# Realistic User-Agent strings for Chrome, Firefox, Safari on Windows/Mac/Linux
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


@dataclass
class Response:
    """HTTP response dataclass"""
    status: int
    url: str
    headers: Dict[str, str]
    body: bytes
    text: str = ""
    json_data: Optional[Any] = None

    def json(self) -> Any:
        """Return parsed JSON data"""
        import json
        if self.json_data is not None:
            return self.json_data
        return json.loads(self.text)


@dataclass
class Cookie:
    """HTTP cookie dataclass"""
    name: str
    value: str
    domain: str = ""
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    expires: Optional[int] = None


class HTTPClientError(Exception):
    """Base exception for HTTP client errors"""


class TimeoutError(HTTPClientError):
    """Raised when a request times out"""


class MaxRetriesExceeded(HTTPClientError):
    """Raised when max retries are exceeded"""


class HTTPClient:
    """
    Async HTTP client with anti-detection capabilities.

    Features:
    - Realistic browser headers (User-Agent, Accept, Accept-Language, etc.)
    - Cookie management across requests
    - Retry logic with exponential backoff
    - 30-second timeout
    - Redirect following (max 5 hops)
    - Proxy support
    - Indonesian locale headers
    - Optional TLS fingerprint mimicry via tls-client (set tls_profile)
    """

    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    MAX_REDIRECTS = 5

    def __init__(
        self,
        fingerprint: Optional[BrowserFingerprint] = None,
        proxy: Optional[ProxyConfig] = None,
        tls_profile: Optional[str] = None,
    ):
        """Initialize HTTP client with optional fingerprint, proxy, and TLS profile.

        Args:
            fingerprint: Browser fingerprint for header generation.
            proxy: Proxy configuration.
            tls_profile: tls-client browser preset name (e.g. "chrome_120",
                         "firefox_120", "safari_16_0"). When set, requests are
                         made via TLSClient instead of aiohttp, providing
                         realistic TLS handshakes with browser cipher suites
                         and HTTP/2 SETTINGS frames.
        """
        self._fingerprint = fingerprint
        self._proxy = proxy
        self._tls_profile = tls_profile
        self._cookies: List[Cookie] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_url: Optional[str] = None

        # Lazily initialised TLS client (only when tls_profile is set)
        self._tls_client: Optional[Any] = None
        if tls_profile is not None:
            self._init_tls_client(tls_profile)

    def _init_tls_client(self, tls_profile: str) -> None:
        """Initialise the TLSClient, falling back gracefully if unavailable."""
        try:
            from src.core.tls_client import TLSClient
            self._tls_client = TLSClient(browser_preset=tls_profile)
            logger.info("TLS fingerprinting enabled with preset: %s", tls_profile)
        except ImportError:
            logger.warning(
                "tls-client not available; falling back to aiohttp for TLS. "
                "Install with: pip install tls-client"
            )
            self._tls_client = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
            # Apply stored cookies
            if self._cookies:
                for cookie in self._cookies:
                    domain = cookie.domain or "tokopedia.com"
                    self._session.cookie_jar.update_cookies(
                        {cookie.name: cookie.value},
                        response_url=yarl.URL(f"https://{domain}"),
                    )
        return self._session

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build realistic browser headers with optional extras"""
        # Select user agent from fingerprint or rotate randomly
        if self._fingerprint:
            user_agent = self._fingerprint.user_agent
            sec_ch_ua = self._fingerprint.sec_ch_ua
            sec_ch_ua_mobile = self._fingerprint.sec_ch_ua_mobile
            sec_ch_ua_platform = self._fingerprint.sec_ch_ua_platform
            viewport_width = str(self._fingerprint.viewport_size[0])
        else:
            user_agent = random.choice(USER_AGENTS)
            sec_ch_ua = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            sec_ch_ua_mobile = "?0"
            sec_ch_ua_platform = '"Windows"'
            viewport_width = str(random.choice([1280, 1366, 1440, 1920]))

        # Build referer from last URL
        referer = self._last_url or "https://affiliate-id.tokopedia.com/"

        base_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": referer,
            "sec-ch-ua": sec_ch_ua,
            "sec-ch-ua-mobile": sec_ch_ua_mobile,
            "sec-ch-ua-platform": sec_ch_ua_platform,
            "sec-ch-viewport-width": viewport_width,
            "Upgrade-Insecure-Requests": "1",
        }

        if extra_headers:
            base_headers.update(extra_headers)

        # Randomize header order for anti-detection
        items = list(base_headers.items())
        random.shuffle(items)
        return dict(items)

    def _get_proxy_url(self) -> Optional[str]:
        """Get proxy URL string if proxy is configured"""
        if self._proxy:
            return self._proxy.to_url()
        return None

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Response:
        """Internal method to make a single HTTP request with retry logic"""
        session = await self._get_session()
        merged_headers = self._build_headers(headers)
        proxy_url = self._get_proxy_url()

        last_exception: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "headers": merged_headers,
                    "allow_redirects": True,
                    "max_redirects": self.MAX_REDIRECTS,
                }
                if proxy_url:
                    kwargs["proxy"] = proxy_url
                if data is not None:
                    kwargs["data"] = data
                if json is not None:
                    kwargs["json"] = json

                async with session.request(method, url, **kwargs) as resp:
                    # Handle 429 Too Many Requests
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                        await asyncio.sleep(retry_after)
                        last_exception = HTTPClientError(f"429 Too Many Requests for {url}")
                        continue

                    body = await resp.read()
                    try:
                        text = body.decode("utf-8")
                    except UnicodeDecodeError:
                        text = body.decode("latin-1", errors="replace")

                    # Update last URL for referer tracking
                    self._last_url = str(resp.url)

                    # Sync cookies back from session
                    self._sync_cookies_from_session(session)

                    return Response(
                        status=resp.status,
                        url=str(resp.url),
                        headers=dict(resp.headers),
                        body=body,
                        text=text,
                    )

            except aiohttp.ServerTimeoutError as e:
                last_exception = TimeoutError(f"Request timed out after {self.TIMEOUT_SECONDS}s: {url}")
                if attempt < self.MAX_RETRIES:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)

            except aiohttp.TooManyRedirects as e:
                raise HTTPClientError(f"Too many redirects (max {self.MAX_REDIRECTS}) for {url}") from e

            except (aiohttp.ClientConnectionError, aiohttp.ClientError) as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)

        if isinstance(last_exception, TimeoutError):
            raise last_exception
        raise MaxRetriesExceeded(
            f"Max retries ({self.MAX_RETRIES}) exceeded for {url}"
        ) from last_exception

    def _sync_cookies_from_session(self, session: aiohttp.ClientSession) -> None:
        """Sync cookies from aiohttp session cookie jar to internal list"""
        new_cookies: List[Cookie] = []
        for morsel in session.cookie_jar:
            new_cookies.append(
                Cookie(
                    name=morsel.key,
                    value=morsel.value,
                    domain=morsel.get("domain", ""),
                    path=morsel.get("path", "/"),
                    secure=bool(morsel.get("secure", False)),
                    http_only=bool(morsel.get("httponly", False)),
                )
            )
        self._cookies = new_cookies

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """Send GET request"""
        if self._tls_client is not None:
            # Sync cookies into TLS client before request
            self._tls_client.set_cookies(self._cookies)
            response = self._tls_client.get(url, headers=headers)
            # Sync cookies back
            self._cookies = self._tls_client.get_cookies()
            return response
        return await self._make_request("GET", url, headers=headers)

    async def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict] = None,
    ) -> Response:
        """Send POST request"""
        if self._tls_client is not None:
            self._tls_client.set_cookies(self._cookies)
            response = self._tls_client.post(url, data=data, headers=headers, json=json)
            self._cookies = self._tls_client.get_cookies()
            return response
        return await self._make_request("POST", url, headers=headers, data=data, json=json)

    def set_cookies(self, cookies: List[Cookie]) -> None:
        """Set cookies for requests"""
        self._cookies = list(cookies)
        # If session exists, update it
        if self._session and not self._session.closed:
            for cookie in cookies:
                domain = cookie.domain or "tokopedia.com"
                self._session.cookie_jar.update_cookies(
                    {cookie.name: cookie.value},
                    response_url=yarl.URL(f"https://{domain}"),
                )
        # Sync to TLS client if active
        if self._tls_client is not None:
            self._tls_client.set_cookies(cookies)

    def get_cookies(self) -> List[Cookie]:
        """Get current cookies"""
        return list(self._cookies)

    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "HTTPClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
