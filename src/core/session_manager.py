"""Session Manager for the Tokopedia Affiliate Scraper.

Manages cookies, localStorage, sessionStorage, and session persistence.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

from src.core.http_client import Cookie


class SessionManager:
    """Manages HTTP session state including cookies and browser storage."""

    def __init__(self, login_url: Optional[str] = None):
        """Initialize empty session.

        Args:
            login_url: URL fragment that indicates a redirect to login page.
                       If the last response URL contains this string, the
                       session is considered expired.
        """
        self._cookies: List[Cookie] = []
        self._local_storage: Dict[str, str] = {}
        self._session_storage: Dict[str, str] = {}
        self._login_url: Optional[str] = login_url
        self._last_response_url: Optional[str] = None

    # ------------------------------------------------------------------
    # Cookie management
    # ------------------------------------------------------------------

    def set_cookies(self, cookies: List[Cookie]) -> None:
        """Set cookies, replacing any existing cookies with the same name+domain."""
        # Build a lookup of existing cookies by (name, domain)
        existing: Dict[tuple, int] = {
            (c.name, c.domain): i for i, c in enumerate(self._cookies)
        }
        for cookie in cookies:
            key = (cookie.name, cookie.domain)
            if key in existing:
                self._cookies[existing[key]] = cookie
            else:
                existing[key] = len(self._cookies)
                self._cookies.append(cookie)

    def get_cookies(self) -> List[Cookie]:
        """Return a copy of the current cookie list."""
        return list(self._cookies)

    # ------------------------------------------------------------------
    # Session expiration
    # ------------------------------------------------------------------

    def is_expired(self) -> bool:
        """Check whether the session has expired.

        A session is considered expired if:
        - Any cookie named "session" or "auth" has an ``expires`` timestamp
          that is in the past, OR
        - The last response URL contains the configured ``login_url`` fragment.
        """
        now = int(time.time())
        for cookie in self._cookies:
            if cookie.name in ("session", "auth"):
                if cookie.expires is not None and cookie.expires < now:
                    return True

        if self._login_url and self._last_response_url:
            if self._login_url in self._last_response_url:
                return True

        return False

    def set_last_response_url(self, url: str) -> None:
        """Record the last response URL (used for login-redirect detection)."""
        self._last_response_url = url

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_session(self, filepath: str) -> None:
        """Serialize session state to a JSON file.

        Args:
            filepath: Path to the output JSON file.
        """
        data = {
            "cookies": [
                {
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path,
                    "secure": c.secure,
                    "http_only": c.http_only,
                    "expires": c.expires,
                }
                for c in self._cookies
            ],
            "local_storage": self._local_storage,
            "session_storage": self._session_storage,
        }
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def load_session(self, filepath: str) -> None:
        """Deserialize session state from a JSON file.

        Args:
            filepath: Path to the JSON file previously created by save_session().
        """
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        self._cookies = [
            Cookie(
                name=c["name"],
                value=c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
                secure=c.get("secure", False),
                http_only=c.get("http_only", False),
                expires=c.get("expires"),
            )
            for c in data.get("cookies", [])
        ]
        self._local_storage = data.get("local_storage", {})
        self._session_storage = data.get("session_storage", {})

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset all session data (cookies, localStorage, sessionStorage)."""
        self._cookies = []
        self._local_storage = {}
        self._session_storage = {}
        self._last_response_url = None

    # ------------------------------------------------------------------
    # localStorage / sessionStorage (browser mode)
    # ------------------------------------------------------------------

    def set_local_storage(self, key: str, value: str) -> None:
        """Store a value in the simulated localStorage."""
        self._local_storage[key] = value

    def get_local_storage(self, key: str) -> Optional[str]:
        """Retrieve a value from the simulated localStorage."""
        return self._local_storage.get(key)

    def set_session_storage(self, key: str, value: str) -> None:
        """Store a value in the simulated sessionStorage."""
        self._session_storage[key] = value

    def get_session_storage(self, key: str) -> Optional[str]:
        """Retrieve a value from the simulated sessionStorage."""
        return self._session_storage.get(key)

    def get_local_storage_all(self) -> Dict[str, str]:
        """Return a copy of the entire localStorage dict."""
        return dict(self._local_storage)

    def get_session_storage_all(self) -> Dict[str, str]:
        """Return a copy of the entire sessionStorage dict."""
        return dict(self._session_storage)
