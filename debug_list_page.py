#!/usr/bin/env python3
"""
Debug script to capture list page HTML and check what's happening
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from playwright.async_api import async_playwright
from src.anti_detection.browser_engine import BrowserEngine
from src.models.models import BrowserFingerprint


async def main():
    print("🔍 DEBUG: Capturing list page HTML...")
    
    # Create fingerprint
    fingerprint = BrowserFingerprint(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        platform="MacIntel",
        browser="Chrome",
        browser_version="120.0.0.0",
        screen_resolution=(1920, 1080),
        viewport_size=(1400, 900),
        timezone="Asia/Jakarta",
        timezone_offset=-420,
        language="id-ID",
        languages=["id-ID", "id", "en-US", "en"],
        color_depth=24,
        pixel_ratio=2.0,
        hardware_concurrency=8,
        device_memory=8,
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        sec_ch_ua_mobile="?0",
        sec_ch_ua_platform='"macOS"',
        plugins=["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        webgl_vendor="Google Inc. (Apple)",
        webgl_renderer="ANGLE (Apple, Apple M1, OpenGL 4.1)"
    )
    
    # Launch browser
    browser_engine = BrowserEngine()
    await browser_engine.launch(fingerprint=fingerprint, headless=False)
    
    # Load cookies
    print("🍪 Loading cookies...")
    await browser_engine.load_cookies_from_file("config/cookies.json")
    
    # Navigate
    url = "https://affiliate-id.tokopedia.com/connection/creator"
    print(f"🌐 Navigating to: {url}")
    
    page = await browser_engine.context.new_page()
    await page.goto(url, wait_until="networkidle", timeout=60000)
    
    print("⏳ Waiting 5 seconds for page to fully load...")
    await asyncio.sleep(5)
    
    # Get page title
    title = await page.title()
    print(f"📄 Page title: {title}")
    
    # Get current URL (check for redirects)
    current_url = page.url
    print(f"🔗 Current URL: {current_url}")
    
    # Save HTML
    html = await page.content()
    with open("debug_list_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"💾 Saved HTML to: debug_list_page.html")
    
    # Try to find table rows
    print("\n🔍 Looking for creator rows...")
    
    # Try different selectors
    selectors = [
        "tbody tr",
        "table tr",
        "tr",
        "[class*='creator']",
        "[class*='table']",
        "a[href*='/creator/']"
    ]
    
    for selector in selectors:
        elements = await page.query_selector_all(selector)
        print(f"   {selector}: {len(elements)} elements")
    
    # Check for error messages or blocking
    print("\n🚨 Checking for errors/blocking...")
    
    error_texts = [
        "Coba lagi",
        "blocked",
        "captcha",
        "login",
        "sign in",
        "masuk"
    ]
    
    body_text = await page.evaluate("() => document.body.textContent")
    for text in error_texts:
        if text.lower() in body_text.lower():
            print(f"   ⚠️  Found: '{text}'")
    
    print("\n✅ Debug complete. Check debug_list_page.html for full HTML.")
    print("Press Ctrl+C to close browser...")
    
    # Keep browser open for manual inspection
    await asyncio.sleep(300)  # 5 minutes
    
    await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
