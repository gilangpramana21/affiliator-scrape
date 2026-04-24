#!/usr/bin/env python3
"""
Debug script untuk handle dynamic/JavaScript-loaded content.

Akan:
1. Wait untuk content loading
2. Check untuk AJAX requests
3. Inspect dynamic table data
4. Find navigation patterns
"""

import asyncio
import logging
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_dynamic_content():
    """Debug dynamic content loading."""
    
    print("🔄 DEBUGGING DYNAMIC CONTENT LOADING")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    session_manager = SessionManager()
    
    try:
        # Launch browser (visible)
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        
        if cookies:
            cookie_list = []
            for cookie in cookies:
                cookie_list.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'httpOnly': cookie.http_only,
                    'secure': cookie.secure
                })
            
            await browser_engine.context.add_cookies(cookie_list)
            print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url)
        
        # Wait for initial load
        print("⏳ Waiting for initial page load...")
        await asyncio.sleep(5)
        
        # Check for loading indicators
        print("\n🔍 Checking for loading indicators...")
        
        loading_selectors = [
            "[class*='loading']",
            "[class*='spinner']",
            "[class*='skeleton']",
            "[data-testid*='loading']"
        ]
        
        for selector in loading_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"   ✅ Found loading indicator: {selector} ({len(elements)} elements)")
            else:
                print(f"   ❌ Not found: {selector}")
        
        # Wait for content to load (longer wait)
        print("\n⏳ Waiting for dynamic content (15 seconds)...")
        await asyncio.sleep(15)
        
        # Check table data again
        print("\n📊 CHECKING TABLE DATA AFTER WAIT:")
        
        # Method 1: Query selector
        table_rows = await page.query_selector_all("tbody tr")
        print(f"   Table rows (querySelector): {len(table_rows)}")
        
        # Method 2: Check for specific data
        creator_elements = await page.query_selector_all("[data-testid*='creator'], [class*='creator']")
        print(f"   Creator elements: {len(creator_elements)}")
        
        # Method 3: Look for any clickable items
        clickable_elements = await page.query_selector_all("tr[onclick], tr[data-href], a[href*='creator'], button[data-creator]")
        print(f"   Clickable elements: {len(clickable_elements)}")
        
        # Method 4: Check current HTML
        html = await page.content()
        doc = parser.parse(html)
        
        tables = parser.select(doc, "table")
        if tables:
            rows = parser.select(tables[0], "tbody tr")
            print(f"   HTML parser rows: {len(rows)}")
            
            # Show first few rows if any
            if rows:
                print(f"\n   📋 SAMPLE ROW DATA:")
                for i, row in enumerate(rows[:2], 1):
                    cells = parser.select(row, "td")
                    print(f"      Row {i}: {len(cells)} cells")
                    
                    for j, cell in enumerate(cells[:3], 1):  # First 3 cells
                        text = parser.get_text(cell)[:50]
                        print(f"         Cell {j}: {text}")
        
        # Check for AJAX/API calls
        print(f"\n🌐 CHECKING FOR API PATTERNS:")
        
        # Look for API endpoints in HTML
        api_patterns = [
            "api/creator",
            "api/affiliate", 
            "/creator/list",
            "/connection/",
            "graphql"
        ]
        
        for pattern in api_patterns:
            if pattern in html:
                print(f"   ✅ Found API pattern: {pattern}")
            else:
                print(f"   ❌ Not found: {pattern}")
        
        # Try to trigger data loading
        print(f"\n🔄 TRYING TO TRIGGER DATA LOADING:")
        
        # Method 1: Scroll to trigger lazy loading
        print("   📜 Scrolling to trigger lazy loading...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)
        
        # Method 2: Look for pagination or load more buttons
        load_buttons = await page.query_selector_all("button[class*='load'], button[class*='more'], [data-testid*='load']")
        if load_buttons:
            print(f"   🔘 Found {len(load_buttons)} load buttons, clicking first...")
            try:
                await load_buttons[0].click()
                await asyncio.sleep(5)
            except Exception as e:
                print(f"      ⚠️ Click failed: {e}")
        
        # Method 3: Check for filter/search that might trigger loading
        search_inputs = await page.query_selector_all("input[type='search'], input[placeholder*='search'], input[placeholder*='cari']")
        if search_inputs:
            print(f"   🔍 Found {len(search_inputs)} search inputs")
        
        # Final check
        print(f"\n📊 FINAL DATA CHECK:")
        
        table_rows_final = await page.query_selector_all("tbody tr")
        print(f"   Final table rows: {len(table_rows_final)}")
        
        # If still no data, check for error messages
        if len(table_rows_final) == 0:
            print(f"\n❌ NO DATA FOUND - CHECKING FOR ISSUES:")
            
            # Check for error messages
            error_selectors = [
                "[class*='error']",
                "[class*='empty']", 
                "[class*='no-data']",
                "[data-testid*='error']",
                "[data-testid*='empty']"
            ]
            
            for selector in error_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip():
                            print(f"   ⚠️ {selector}: {text.strip()}")
            
            # Check page title and URL for clues
            title = await page.title()
            current_url = page.url
            print(f"   📄 Page title: {title}")
            print(f"   🔗 Current URL: {current_url}")
            
            # Check if we're redirected or need authentication
            if "login" in current_url.lower() or "auth" in current_url.lower():
                print(f"   🔐 Possible authentication issue")
            
            if "error" in current_url.lower() or "404" in current_url.lower():
                print(f"   💥 Possible page error")
        
        # Interactive inspection
        print(f"\n👀 INTERACTIVE INSPECTION:")
        print("   Browser window is open for manual inspection")
        print("   Check:")
        print("   - Network tab for failed requests")
        print("   - Console for JavaScript errors") 
        print("   - Elements tab for dynamic content")
        
        input("\nPress Enter when done inspecting...")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(debug_dynamic_content())