#!/usr/bin/env python3
"""Test script untuk halaman Jelajahi affiliator"""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_jelajahi():
    print("🔍 Testing Jelajahi (Creator Discovery) page...")
    
    # Load config and cookies
    config = Configuration.from_file("config/config_jelajahi.json")
    
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
    
    # Navigate to Jelajahi page
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
    
    # Get page info
    title = await page.title()
    current_url = page.url
    print(f"📄 Page title: {title}")
    print(f"🔗 Current URL: {current_url}")
    
    # Take screenshot
    await page.screenshot(path="jelajahi_page.png")
    print("📸 Screenshot saved as jelajahi_page.png")
    
    # Check for creator cards/items
    print("\n🔍 Looking for creator elements:")
    
    creator_selectors = [
        "div.creator-card",
        "div[data-testid*='creator']",
        "div.affiliate-card", 
        "div.creator-item",
        ".creator-list-item",
        "div[class*='creator']",
        "div[class*='affiliate']",
        "div[class*='card']",
        "article",
        ".grid-item",
        ".list-item"
    ]
    
    found_creators = []
    
    for selector in creator_selectors:
        try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  ✅ Found {len(elements)} elements with: {selector}")
                found_creators.append((selector, len(elements)))
                
                # Get sample content from first element
                if elements:
                    sample_text = await elements[0].inner_text()
                    print(f"    Sample text: {sample_text[:100]}...")
                    
                    # Check for links in first element
                    links = await elements[0].query_selector_all("a")
                    if links:
                        for link in links[:2]:  # First 2 links
                            href = await link.get_attribute("href")
                            link_text = await link.inner_text()
                            print(f"    🔗 Link: '{link_text.strip()[:30]}' -> {href}")
            else:
                print(f"  ❌ No elements found with: {selector}")
        except Exception as e:
            print(f"  ⚠️  Error with {selector}: {e}")
    
    # If we found creators, inspect the first one in detail
    if found_creators:
        best_selector = found_creators[0][0]  # Selector with most elements
        print(f"\n🔍 Detailed inspection of: {best_selector}")
        
        elements = await page.query_selector_all(best_selector)
        first_element = elements[0]
        
        # Look for common data fields
        data_selectors = {
            "username": ["h1", "h2", "h3", ".name", ".username", ".title", "[data-testid*='name']"],
            "followers": [".followers", ".pengikut", "[data-testid*='follower']", "span:contains('pengikut')", "span:contains('follower')"],
            "category": [".category", ".kategori", ".tag", "[data-testid*='category']"],
            "stats": [".stats", ".metrics", ".numbers", "[data-testid*='stat']"]
        }
        
        for field, selectors in data_selectors.items():
            print(f"  🔍 Looking for {field}:")
            for sel in selectors:
                try:
                    field_elements = await first_element.query_selector_all(sel)
                    if field_elements:
                        for elem in field_elements[:2]:  # First 2 matches
                            text = await elem.inner_text()
                            if text.strip():
                                print(f"    ✅ {sel}: {text.strip()[:50]}")
                except:
                    pass
    
    # Check for pagination
    print("\n🔍 Looking for pagination:")
    pagination_selectors = [
        "a[rel='next']",
        ".pagination a",
        "button[aria-label*='next']",
        "a:contains('Selanjutnya')",
        "button:contains('Selanjutnya')",
        ".next-page",
        "[data-testid*='next']"
    ]
    
    for selector in pagination_selectors:
        try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  ✅ Found pagination: {selector}")
                for elem in elements:
                    text = await elem.inner_text()
                    href = await elem.get_attribute("href")
                    print(f"    Text: '{text.strip()}' -> {href}")
        except:
            pass
    
    print("\n⏳ Browser window open for manual inspection...")
    print("   Navigate around and check the page structure...")
    print("   Press Enter when done...")
    input()
    
    await engine.close()
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_jelajahi())