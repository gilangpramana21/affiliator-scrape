"""Headless browser engine with stealth capabilities for anti-detection."""

from __future__ import annotations

import asyncio
import json
import random
from typing import Literal, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from src.models.models import BrowserFingerprint


# ---------------------------------------------------------------------------
# Stealth JavaScript snippets
# ---------------------------------------------------------------------------

_STEALTH_WEBDRIVER_JS = """
() => {
    // Patch navigator.webdriver to undefined
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });

    // Override chrome.runtime to undefined so automation is not detected
    if (window.chrome) {
        Object.defineProperty(window.chrome, 'runtime', {
            get: () => undefined,
            configurable: true,
        });
    } else {
        Object.defineProperty(window, 'chrome', {
            get: () => ({ runtime: undefined }),
            configurable: true,
        });
    }
}
"""

_STEALTH_PLUGINS_JS = """
(plugins) => {
    // Patch navigator.plugins with a realistic plugin list
    const pluginData = plugins.map((name, i) => ({
        name,
        filename: name.toLowerCase().replace(/ /g, '-') + '.so',
        description: name,
        length: 0,
    }));

    const pluginArray = Object.create(PluginArray.prototype);
    pluginData.forEach((p, i) => {
        const plugin = Object.create(Plugin.prototype);
        Object.defineProperty(plugin, 'name', { get: () => p.name });
        Object.defineProperty(plugin, 'filename', { get: () => p.filename });
        Object.defineProperty(plugin, 'description', { get: () => p.description });
        Object.defineProperty(plugin, 'length', { get: () => p.length });
        Object.defineProperty(pluginArray, i, { get: () => plugin });
    });
    Object.defineProperty(pluginArray, 'length', { get: () => pluginData.length });
    Object.defineProperty(navigator, 'plugins', {
        get: () => pluginArray,
        configurable: true,
    });
}
"""

_STEALTH_LANGUAGES_JS = """
(languages) => {
    Object.defineProperty(navigator, 'languages', {
        get: () => languages,
        configurable: true,
    });
    Object.defineProperty(navigator, 'language', {
        get: () => languages[0] || 'id-ID',
        configurable: true,
    });
}
"""

_CANVAS_NOISE_JS = """
() => {
    const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
    const _getImageData = CanvasRenderingContext2D.prototype.getImageData;

    function addNoise(data) {
        const noise = Math.floor(Math.random() * 10) - 5;
        for (let i = 0; i < data.length; i += 4) {
            data[i]     = Math.min(255, Math.max(0, data[i]     + noise));
            data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + noise));
            data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + noise));
        }
        return data;
    }

    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imageData = _getImageData.call(ctx, 0, 0, this.width, this.height);
            addNoise(imageData.data);
            ctx.putImageData(imageData, 0, 0);
        }
        return _toDataURL.apply(this, args);
    };

    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        const imageData = _getImageData.apply(this, args);
        addNoise(imageData.data);
        return imageData;
    };
}
"""

_WEBGL_NOISE_JS = """
(vendor, renderer) => {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return vendor;    // UNMASKED_VENDOR_WEBGL
        if (parameter === 37446) return renderer;  // UNMASKED_RENDERER_WEBGL
        return getParameter.call(this, parameter);
    };

    // Also patch WebGL2 if available
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return vendor;
            if (parameter === 37446) return renderer;
            return getParameter2.call(this, parameter);
        };
    }
}
"""

_AUDIO_NOISE_JS = """
() => {
    const _getChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {
        const data = _getChannelData.call(this, channel);
        for (let i = 0; i < data.length; i++) {
            data[i] += (Math.random() - 0.5) * 0.0001;
        }
        return data;
    };
}
"""


class BrowserEngine:
    """Manages headless Playwright browser with stealth capabilities."""

    def __init__(self, engine_type: Literal["playwright", "puppeteer"] = "playwright"):
        if engine_type != "playwright":
            raise ValueError("Only 'playwright' engine is currently supported.")
        self._engine_type = engine_type
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def launch(self, fingerprint: BrowserFingerprint, headless: bool = True) -> Browser:
        """Launch Chromium with the given fingerprint and stealth patches applied."""
        self._playwright = await async_playwright().start()

        width, height = fingerprint.viewport_size
        screen_w, screen_h = fingerprint.screen_resolution

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                f"--window-size={screen_w},{screen_h}",
            ],
        )

        self._context = await self._browser.new_context(
            user_agent=fingerprint.user_agent,
            viewport={"width": width, "height": height},
            locale=fingerprint.language,
            timezone_id=fingerprint.timezone,
            color_scheme="no-preference",
            device_scale_factor=fingerprint.pixel_ratio,
            extra_http_headers=self._build_extra_headers(fingerprint),
        )

        # Inject stealth patches for every new page opened in this context
        await self._inject_stealth_scripts(self._context, fingerprint)

        return self._browser

    async def navigate(self, url: str, wait_for: str = "networkidle") -> Page:
        """Open a new page, navigate to *url*, and wait for the page to settle."""
        if self._context is None:
            raise RuntimeError("Browser not launched. Call launch() first.")

        # Map wait_for string to Playwright's waitUntil values
        wait_map = {
            "networkidle": "networkidle",
            "domcontentloaded": "domcontentloaded",
            "load": "load",
        }
        wait_until = wait_map.get(wait_for, "networkidle")

        page = await self._context.new_page()
        await page.goto(url, wait_until=wait_until, timeout=60_000)
        return page

    async def get_html(self, page: Page) -> str:
        """Return the full HTML content of *page*."""
        return await page.content()

    async def simulate_human_behavior(self, page: Page) -> None:
        """Perform random human-like interactions on the page."""
        # Random scroll
        scroll_amount = random.randint(200, 800)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Random mouse move
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.8))

    async def close(self) -> None:
        """Close the browser and clean up Playwright resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def load_cookies_from_file(self, cookie_file: str) -> None:
        """Load cookies from a JSON file and add them to the browser context."""
        if self._context is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        with open(cookie_file, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        cookies = raw.get("cookies", raw)
        if isinstance(cookies, list) and cookies:
            await self._context.add_cookies(cookies)

    @property
    def context(self) -> Optional[BrowserContext]:
        """Get the browser context for creating new pages/tabs."""
        return self._context

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_extra_headers(self, fingerprint: BrowserFingerprint) -> dict:
        headers: dict = {
            "Accept-Language": ", ".join(fingerprint.languages),
        }
        if fingerprint.sec_ch_ua:
            headers["sec-ch-ua"] = fingerprint.sec_ch_ua
            headers["sec-ch-ua-mobile"] = fingerprint.sec_ch_ua_mobile
            headers["sec-ch-ua-platform"] = fingerprint.sec_ch_ua_platform
        return headers

    async def _inject_stealth_scripts(
        self, context: BrowserContext, fingerprint: BrowserFingerprint
    ) -> None:
        """Register init scripts that run before any page script."""
        # 9.4 – navigator.webdriver + chrome.runtime
        await context.add_init_script(_STEALTH_WEBDRIVER_JS)

        # 9.4 – navigator.plugins
        plugins_json = str(fingerprint.plugins).replace("'", '"')
        await context.add_init_script(
            f"({_STEALTH_PLUGINS_JS})({plugins_json})"
        )

        # 9.4 – navigator.languages
        langs_json = str(fingerprint.languages).replace("'", '"')
        await context.add_init_script(
            f"({_STEALTH_LANGUAGES_JS})({langs_json})"
        )

        # 9.5 – canvas fingerprint randomization
        await context.add_init_script(f"({_CANVAS_NOISE_JS})()")

        # 9.6 – WebGL fingerprint randomization
        vendor = fingerprint.webgl_vendor.replace('"', '\\"')
        renderer = fingerprint.webgl_renderer.replace('"', '\\"')
        await context.add_init_script(
            f'({_WEBGL_NOISE_JS})("{vendor}", "{renderer}")'
        )

        # 9.7 – audio context fingerprint randomization
        await context.add_init_script(f"({_AUDIO_NOISE_JS})()")
