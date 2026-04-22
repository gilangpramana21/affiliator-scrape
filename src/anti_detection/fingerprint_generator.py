"""Browser fingerprint generator for anti-detection"""

from __future__ import annotations

import json
import os
import random
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.models.models import BrowserFingerprint


# ── Browser distribution ──────────────────────────────────────────────────────

BROWSER_WEIGHTS = [("Chrome", 0.70), ("Firefox", 0.20), ("Safari", 0.10)]

# Chrome versions (major, minor, build, patch)
CHROME_VERSIONS = [
    ("120", "120.0.6099.130"),
    ("119", "119.0.6045.199"),
    ("118", "118.0.5993.117"),
    ("121", "121.0.6167.85"),
]

FIREFOX_VERSIONS = ["121.0", "120.0", "119.0", "118.0"]

SAFARI_VERSIONS = [
    ("17.2", "605.1.15"),
    ("17.1", "605.1.15"),
    ("16.6", "605.1.15"),
]

# ── OS / Platform distribution ────────────────────────────────────────────────

# Chrome can run on Windows, macOS, Linux
CHROME_OS_WEIGHTS = [("Windows", 0.65), ("macOS", 0.25), ("Linux", 0.10)]

# Firefox can run on Windows, macOS, Linux
FIREFOX_OS_WEIGHTS = [("Windows", 0.60), ("macOS", 0.25), ("Linux", 0.15)]

# Safari only runs on macOS
SAFARI_OS = "macOS"

OS_PLATFORM_MAP = {
    "Windows": "Win32",
    "macOS": "MacIntel",
    "Linux": "Linux x86_64",
}

# Windows versions for UA strings
WINDOWS_NT_VERSIONS = ["10.0", "10.0"]  # Win10/11 both report 10.0
MACOS_VERSIONS = ["10_15_7", "11_0_0", "12_0_0", "13_0_0", "14_0_0"]
LINUX_ARCHS = ["x86_64"]

# ── Screen resolutions ────────────────────────────────────────────────────────

SCREEN_RESOLUTIONS: List[Tuple[int, int]] = [
    (1920, 1080),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1280, 720),
    (1600, 900),
    (2560, 1440),
    (1280, 800),
]

# Browser chrome height (taskbar + browser UI) subtracted from screen height
BROWSER_CHROME_HEIGHT = 120  # pixels

# ── Timezones ─────────────────────────────────────────────────────────────────

TIMEZONE_WEIGHTS = [
    ("Asia/Jakarta", -420, 0.60),   # WIB UTC+7
    ("Asia/Makassar", -480, 0.25),  # WITA UTC+8
    ("Asia/Jayapura", -540, 0.15),  # WIT UTC+9
]

# ── WebGL vendors / renderers ─────────────────────────────────────────────────

WEBGL_CONFIGS: List[Tuple[str, str]] = [
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Intel Inc.", "Intel(R) UHD Graphics 620"),
    ("NVIDIA Corporation", "NVIDIA GeForce GTX 1650/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
    ("AMD", "AMD Radeon RX 580 OpenGL Engine"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Apple Inc.", "Apple M1"),
    ("Apple Inc.", "Apple M2"),
]

# ── Plugins ───────────────────────────────────────────────────────────────────

CHROME_PLUGINS = [
    "Chrome PDF Plugin",
    "Chrome PDF Viewer",
    "Native Client",
]

FIREFOX_PLUGINS: List[str] = []  # Firefox typically has no plugins

SAFARI_PLUGINS: List[str] = []

# ── Hardware profiles ─────────────────────────────────────────────────────────

HARDWARE_CONCURRENCY_OPTIONS = [2, 4, 4, 8, 8, 8, 16]  # weighted toward 4/8
DEVICE_MEMORY_OPTIONS = [2, 4, 4, 8, 8, 16]
PIXEL_RATIO_OPTIONS = [1.0, 1.0, 1.5, 2.0]


def _weighted_choice(choices: List[Tuple]) -> Tuple:
    """Pick from a list of (value, weight) or (v1, v2, weight) tuples."""
    weights = [c[-1] for c in choices]
    return random.choices(choices, weights=weights, k=1)[0]


class FingerprintGenerator:
    """Generates realistic, internally-consistent browser fingerprints."""

    def __init__(self, fingerprint_dir: str = "config/fingerprints"):
        self._dir = Path(fingerprint_dir)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self) -> BrowserFingerprint:
        """Generate a new random fingerprint."""
        browser = self._select_browser()
        platform, os_name = self._select_os(browser)
        browser_version, ua = self._build_user_agent(browser, os_name)
        screen = self._select_screen_resolution()
        viewport = self._calculate_viewport(screen)
        tz, tz_offset = self._select_timezone()
        sec_ch_ua, sec_ch_ua_mobile, sec_ch_ua_platform = self._build_sec_ch_ua(
            browser, browser_version, os_name
        )
        webgl_vendor, webgl_renderer = self._select_webgl()
        plugins = self._select_plugins(browser)

        return BrowserFingerprint(
            user_agent=ua,
            platform=platform,
            browser=browser,
            browser_version=browser_version,
            screen_resolution=screen,
            viewport_size=viewport,
            timezone=tz,
            timezone_offset=tz_offset,
            language="id-ID",
            languages=["id-ID", "id", "en-US", "en"],
            color_depth=24,
            pixel_ratio=random.choice(PIXEL_RATIO_OPTIONS),
            hardware_concurrency=random.choice(HARDWARE_CONCURRENCY_OPTIONS),
            device_memory=random.choice(DEVICE_MEMORY_OPTIONS),
            sec_ch_ua=sec_ch_ua,
            sec_ch_ua_mobile=sec_ch_ua_mobile,
            sec_ch_ua_platform=sec_ch_ua_platform,
            plugins=plugins,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
        )

    def save(self, fingerprint: BrowserFingerprint) -> str:
        """Persist fingerprint to disk and return its ID."""
        self._dir.mkdir(parents=True, exist_ok=True)
        fingerprint_id = str(uuid.uuid4())
        path = self._dir / f"{fingerprint_id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(fingerprint.to_dict(), fh, ensure_ascii=False, indent=2)
        return fingerprint_id

    def load(self, fingerprint_id: str) -> BrowserFingerprint:
        """Load a previously saved fingerprint by ID."""
        path = self._dir / f"{fingerprint_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Fingerprint not found: {fingerprint_id}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return BrowserFingerprint.from_dict(data)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _select_browser(self) -> str:
        browsers = [b for b, _ in BROWSER_WEIGHTS]
        weights = [w for _, w in BROWSER_WEIGHTS]
        return random.choices(browsers, weights=weights, k=1)[0]

    def _select_os(self, browser: str) -> Tuple[str, str]:
        """Return (platform string, OS name)."""
        if browser == "Safari":
            os_name = SAFARI_OS
        elif browser == "Chrome":
            choices = [o for o, _ in CHROME_OS_WEIGHTS]
            weights = [w for _, w in CHROME_OS_WEIGHTS]
            os_name = random.choices(choices, weights=weights, k=1)[0]
        else:  # Firefox
            choices = [o for o, _ in FIREFOX_OS_WEIGHTS]
            weights = [w for _, w in FIREFOX_OS_WEIGHTS]
            os_name = random.choices(choices, weights=weights, k=1)[0]
        return OS_PLATFORM_MAP[os_name], os_name

    def _build_user_agent(self, browser: str, os_name: str) -> Tuple[str, str]:
        """Return (browser_version, user_agent_string)."""
        if browser == "Chrome":
            major, full = random.choice(CHROME_VERSIONS)
            os_token = self._os_token_for_chrome(os_name)
            ua = (
                f"Mozilla/5.0 ({os_token}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full} Safari/537.36"
            )
            return major, ua

        elif browser == "Firefox":
            version = random.choice(FIREFOX_VERSIONS)
            os_token = self._os_token_for_firefox(os_name)
            ua = f"Mozilla/5.0 ({os_token}; rv:{version}) Gecko/20100101 Firefox/{version}"
            return version, ua

        else:  # Safari
            major, webkit = random.choice(SAFARI_VERSIONS)
            macos = random.choice(MACOS_VERSIONS)
            ua = (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X {macos}) "
                f"AppleWebKit/{webkit} (KHTML, like Gecko) "
                f"Version/{major} Safari/{webkit}"
            )
            return major, ua

    def _os_token_for_chrome(self, os_name: str) -> str:
        if os_name == "Windows":
            nt = random.choice(WINDOWS_NT_VERSIONS)
            return f"Windows NT {nt}; Win64; x64"
        elif os_name == "macOS":
            mac = random.choice(MACOS_VERSIONS)
            return f"Macintosh; Intel Mac OS X {mac}"
        else:  # Linux
            return "X11; Linux x86_64"

    def _os_token_for_firefox(self, os_name: str) -> str:
        if os_name == "Windows":
            nt = random.choice(WINDOWS_NT_VERSIONS)
            return f"Windows NT {nt}; Win64; x64"
        elif os_name == "macOS":
            mac = random.choice(MACOS_VERSIONS)
            return f"Macintosh; Intel Mac OS X {mac}"
        else:
            return "X11; Linux x86_64"

    def _select_screen_resolution(self) -> Tuple[int, int]:
        return random.choice(SCREEN_RESOLUTIONS)

    def _calculate_viewport(self, screen: Tuple[int, int]) -> Tuple[int, int]:
        width, height = screen
        viewport_height = max(height - BROWSER_CHROME_HEIGHT, 400)
        return width, viewport_height

    def _select_timezone(self) -> Tuple[str, int]:
        """Return (timezone_name, offset_minutes)."""
        choice = _weighted_choice(TIMEZONE_WEIGHTS)
        return choice[0], choice[1]

    def _build_sec_ch_ua(
        self, browser: str, browser_version: str, os_name: str
    ) -> Tuple[str, str, str]:
        """Return (sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform)."""
        platform_map = {
            "Windows": '"Windows"',
            "macOS": '"macOS"',
            "Linux": '"Linux"',
        }
        platform = platform_map.get(os_name, '"Unknown"')

        if browser == "Chrome":
            major = browser_version.split(".")[0]
            sec_ch_ua = (
                f'"Not_A Brand";v="8", '
                f'"Chromium";v="{major}", '
                f'"Google Chrome";v="{major}"'
            )
        elif browser == "Firefox":
            # Firefox does not send sec-ch-ua
            sec_ch_ua = ""
        else:  # Safari
            # Safari does not send sec-ch-ua
            sec_ch_ua = ""

        return sec_ch_ua, "?0", platform

    def _select_webgl(self) -> Tuple[str, str]:
        vendor, renderer = random.choice(WEBGL_CONFIGS)
        return vendor, renderer

    def _select_plugins(self, browser: str) -> List[str]:
        if browser == "Chrome":
            return list(CHROME_PLUGINS)
        elif browser == "Firefox":
            return list(FIREFOX_PLUGINS)
        else:
            return list(SAFARI_PLUGINS)

    # ── Consistency validation ────────────────────────────────────────────────

    def validate_consistency(self, fp: BrowserFingerprint) -> bool:
        """Return True if the fingerprint is internally consistent."""
        # Safari must be macOS
        if fp.browser == "Safari" and fp.platform != "MacIntel":
            return False

        # Platform must match a known OS
        valid_platforms = set(OS_PLATFORM_MAP.values())
        if fp.platform not in valid_platforms:
            return False

        # Timezone must be Indonesian
        valid_timezones = {tz for tz, _, _ in TIMEZONE_WEIGHTS}
        if fp.timezone not in valid_timezones:
            return False

        # Timezone offset must match timezone name
        tz_offset_map = {tz: off for tz, off, _ in TIMEZONE_WEIGHTS}
        if fp.timezone_offset != tz_offset_map.get(fp.timezone):
            return False

        # sec-ch-ua must be non-empty for Chrome, empty for others
        if fp.browser == "Chrome" and not fp.sec_ch_ua:
            return False
        if fp.browser in ("Firefox", "Safari") and fp.sec_ch_ua:
            return False

        # sec-ch-ua-platform must match platform
        platform_to_sec = {
            "Win32": '"Windows"',
            "MacIntel": '"macOS"',
            "Linux x86_64": '"Linux"',
        }
        expected_platform = platform_to_sec.get(fp.platform)
        if expected_platform and fp.sec_ch_ua_platform != expected_platform:
            return False

        # Screen resolution must be one of the known ones
        if fp.screen_resolution not in SCREEN_RESOLUTIONS:
            return False

        # Viewport must be smaller than screen
        if fp.viewport_size[0] != fp.screen_resolution[0]:
            return False
        if fp.viewport_size[1] >= fp.screen_resolution[1]:
            return False

        return True
