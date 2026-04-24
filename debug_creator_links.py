#!/usr/bin/env python3
"""
Debug script to understand how creator links work in Tokopedia.
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


async def debug_creator_links():
    """Debug how creator links work."""
    
    print("🔗 DEBUGGING CREATOR LINKS")
    print("=" * 40)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    session_manager = SessionManager()
    
    try:
        # Launch browser
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
        
        # Wait for dynamic content
        print("⏳ Waiting for dynamic content...")
        await asyncio.sleep(5)
        
        # Check for clickable elements
        print(f"\n🔍 ANALYZING CLICKABLE ELEMENTS:")
        
        # Method 1: Look for table rows that are clickable
        clickable_rows = await page.query_selector_all("tr[onclick], tr[data-href], tr.clickable")
        print(f"   Clickable rows: {len(clickable_rows)}")
        
        # Method 2: Look for links within table cells
        table_links = await page.query_selector_all("tbody tr a")
        print(f"   Links in table rows: {len(table_links)}")
        
        # Method 3: Look for buttons or clickable elements
        clickable_elements = await page.query_selector_all("tbody tr button, tbody tr [role='button']")
        print(f"   Clickable buttons: {len(clickable_elements)}")
        
        # Method 4: Check for JavaScript event handlers
        rows_with_events = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('tbody tr');
                let count = 0;
                rows.forEach(row => {
                    // Check for various event handlers
                    if (row.onclick || row.getAttribute('data-href') || 
                        row.style.cursor === 'pointer' || 
                        row.classList.contains('clickable')) {
                        count++;
                    }
                });
                return count;
            }
        """)
        print(f"   Rows with event handlers: {rows_with_events}")
        
        # Method 5: Check first few rows for detailed analysis
        print(f"\n📋 DETAILED ROW ANALYSIS:")
        
        first_rows = await page.query_selector_all("tbody tr")
        for i, row in enumerate(first_rows[:3]):
            print(f"\n   Row {i+1}:")
            
            # Check onclick
            onclick = await row.get_attribute("onclick")
            if onclick:
                print(f"      onclick: {onclick[:100]}...")
            
            # Check data attributes
            data_href = await row.get_attribute("data-href")
            if data_href:
                print(f"      data-href: {data_href}")
            
            # Check cursor style
            cursor = await row.evaluate("el => getComputedStyle(el).cursor")
            print(f"      cursor: {cursor}")
            
            # Check for links in cells
            links = await row.query_selector_all("a")
            if links:
                for j, link in enumerate(links):
                    href = await link.get_attribute("href")
                    text = await link.text_content()
                    print(f"      Link {j+1}: {href} (text: {text[:30]}...)")
            
            # Check for buttons
            buttons = await row.query_selector_all("button")
            if buttons:
                for j, button in enumerate(buttons):
                    text = await button.text_content()
                    onclick_btn = await button.get_attribute("onclick")
                    print(f"      Button {j+1}: {text[:30]}... (onclick: {onclick_btn})")
        
        # Method 6: Try to simulate a click on the first row
        print(f"\n🖱️ TESTING CLICK BEHAVIOR:")
        
        first_row = await page.query_selector("tbody tr")
        if first_row:
            print("   Attempting to click first row...")
            
            # Listen for new pages/tabs
            new_page_promise = browser_engine.context.wait_for_event("page")
            
            try:
                await first_row.click()
                print("   ✅ Row clicked")
                
                # Wait for new page (with timeout)
                try:
                    new_page = await asyncio.wait_for(new_page_promise, timeout=5.0)
                    print(f"   🆕 New page opened: {new_page.url}")
                    
                    # Wait a bit for the new page to load
                    await asyncio.sleep(3)
                    
                    # Check if there's a puzzle
                    puzzle_elements = await new_page.query_selector_all("[class*='puzzle'], [class*='captcha'], [id*='puzzle']")
                    if puzzle_elements:
                        print(f"   🧩 Puzzle detected: {len(puzzle_elements)} elements")
                    else:
                        print(f"   ✅ No puzzle detected")
                    
                    # Close the new page
                    await new_page.close()
                    
                except asyncio.TimeoutError:
                    print("   ⚠️ No new page opened within 5 seconds")
                
            except Exception as e:
                print(f"   ❌ Click failed: {e}")
        
        print(f"\n👀 MANUAL INSPECTION:")
        print("   Browser window is open for manual inspection")
        print("   Try clicking on creators to see the behavior")
        
        input("\nPress Enter when done inspecting...")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(debug_creator_links())