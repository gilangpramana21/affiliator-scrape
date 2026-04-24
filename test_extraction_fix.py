#!/usr/bin/env python3
"""
Quick test to verify the extraction fixes work.
"""

import asyncio
import logging
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_extraction_fix():
    """Test the extraction fixes."""
    
    print("🧪 TESTING EXTRACTION FIXES")
    print("=" * 40)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
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
        
        # Wait for dynamic content (simulate the orchestrator fix)
        print("⏳ Waiting for dynamic content...")
        
        # Wait for loading indicators to disappear
        loading_selectors = [
            "[class*='loading']",
            "[class*='spinner']", 
            "[class*='skeleton']"
        ]
        
        for selector in loading_selectors:
            try:
                await page.wait_for_selector(selector, state="hidden", timeout=10000)
                print(f"   ✅ Loading indicator {selector} disappeared")
            except Exception:
                pass
        
        # Wait for table rows to appear
        try:
            await page.wait_for_selector("tbody tr", timeout=15000)
            print("   ✅ Table rows detected")
        except Exception:
            print("   ⚠️ No table rows found after waiting")
        
        # Additional wait for JavaScript
        await asyncio.sleep(3)
        
        # Check row count
        row_count = await page.evaluate("document.querySelectorAll('tbody tr').length")
        print(f"   📊 Found {row_count} table rows in browser")
        
        # Get HTML and test extraction
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        
        print(f"\n🔍 Testing extraction...")
        result = extractor.extract_list_page(doc)
        
        print(f"   📋 Extracted {len(result.affiliators)} affiliators")
        
        # Show sample data
        if result.affiliators:
            print(f"\n📝 SAMPLE EXTRACTED DATA:")
            for i, affiliator in enumerate(result.affiliators[:3], 1):
                print(f"   {i}. Username: {affiliator.username}")
                print(f"      Category: {affiliator.kategori}")
                print(f"      Followers: {affiliator.pengikut}")
                print(f"      GMV: {affiliator.gmv}")
                print(f"      Detail URL: {affiliator.detail_url}")
                print()
        else:
            print(f"\n❌ NO DATA EXTRACTED")
            
            # Debug: show what tables we found
            tables = parser.select(doc, "table")
            print(f"   Tables found: {len(tables)}")
            
            if tables:
                for i, table in enumerate(tables):
                    rows = parser.select(table, "tr")
                    print(f"   Table {i+1}: {len(rows)} rows")
                    
                    if rows:
                        for j, row in enumerate(rows[:2]):
                            cells = parser.select(row, "td")
                            print(f"      Row {j+1}: {len(cells)} cells")
                            if cells:
                                text = parser.get_text(cells[0])[:50]
                                print(f"         First cell: {text}")
        
        print(f"\n✅ Test completed!")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_extraction_fix())