#!/usr/bin/env python3
"""Test script untuk melihat halaman affiliate center"""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_page():
    print("🔍 Testing connection to Tokopedia Affiliate Center...")
    
    # Load config and cookies
    config = Configuration.from_file("config/config.safe.json")
    
    # Generate fingerprint
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    print(f"✅ Generated fingerprint: {fingerprint.browser} {fingerprint.browser_version}")
    
    # Setup browser
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=False)  # Visible browser
    print("✅ Browser launched")
    
    # Load cookies
    session_manager = SessionManager()
    session_manager.load_session(config.cookie_file)
    print(f"✅ Loaded {len(session_manager.get_cookies())} cookies")
    
    # Navigate to page
    url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
    print(f"🌐 Navigating to: {url}")
    
    page = await engine.navigate(url, wait_for="networkidle")
    
    # Apply cookies to page
    cookies = session_manager.get_cookies()
    for cookie in cookies:
        await page.context.add_cookies([{
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
            'httpOnly': cookie.http_only,
            'secure': cookie.secure
        }])
    
    # Reload page with cookies
    await page.reload(wait_until="networkidle")
    print("✅ Page loaded with cookies")
    
    # Get page title and URL
    title = await page.title()
    current_url = page.url
    print(f"📄 Page title: {title}")
    print(f"🔗 Current URL: {current_url}")
    
    # Take screenshot
    await page.screenshot(path="debug_page.png")
    print("📸 Screenshot saved as debug_page.png")
    
    # Get page content sample
    content = await page.content()
    print(f"📝 Page content length: {len(content)} characters")
    
    # Check for common elements
    elements_to_check = [
        "div[data-testid='creator-card']",
        ".creator-card",
        "[data-testid*='creator']",
        ".affiliator-card",
        ".creator-item",
        "table tr",
        ".list-item"
    ]
    
    print("\n🔍 Checking for affiliator elements:")
    for selector in elements_to_check:
        try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  ✅ Found {len(elements)} elements with selector: {selector}")
            else:
                print(f"  ❌ No elements found with selector: {selector}")
        except Exception as e:
            print(f"  ⚠️  Error with selector {selector}: {e}")
    
    # Wait for manual inspection
    print("\n⏳ Browser window is open for manual inspection...")
    print("   Check the page and press Enter when done...")
    input()
    
    await engine.close()
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_page())