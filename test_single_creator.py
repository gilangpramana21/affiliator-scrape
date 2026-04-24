#!/usr/bin/env python3
"""
Test single creator extraction to verify the fixes work.
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


async def test_single_creator():
    """Test extracting and clicking on a single creator."""
    
    print("👤 TESTING SINGLE CREATOR EXTRACTION")
    print("=" * 50)
    
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
        
        # Wait for dynamic content
        print("⏳ Waiting for dynamic content...")
        await asyncio.sleep(5)
        
        # Get HTML and extract
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        print(f"📋 Extracted {len(result.affiliators)} creators")
        
        if not result.affiliators:
            print("❌ No creators found")
            return
        
        # Test clicking on the first creator
        first_creator = result.affiliators[0]
        print(f"\n🖱️ Testing click on first creator: {first_creator.username}")
        print(f"   Detail URL: {first_creator.detail_url}")
        
        if first_creator.detail_url == "CLICKABLE_ROW":
            print("   🔄 Attempting to click row...")
            
            # Get table rows
            rows = await page.query_selector_all("tbody tr")
            if len(rows) > 0:
                # Listen for new page
                new_page_promise = browser_engine.context.wait_for_event("page")
                
                # Click first row
                await rows[0].click()
                print("   ✅ Row clicked")
                
                try:
                    # Wait for new page
                    detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                    print(f"   🆕 New page opened: {detail_page.url}")
                    
                    # Wait for page to load
                    await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    
                    # Test extraction on detail page
                    detail_html = await detail_page.content()
                    detail_doc = parser.parse(detail_html)
                    detail_data = extractor.extract_detail_page(detail_doc, detail_page.url)
                    
                    print(f"   📝 Detail extraction:")
                    print(f"      Username: {detail_data.username}")
                    print(f"      Contact: {detail_data.nomor_kontak}")
                    print(f"      WhatsApp: {detail_data.nomor_whatsapp}")
                    
                    # Close detail page
                    await detail_page.close()
                    print("   ✅ Detail page closed")
                    
                except asyncio.TimeoutError:
                    print("   ⚠️ No new page opened within timeout")
                except Exception as e:
                    print(f"   ❌ Error with detail page: {e}")
            else:
                print("   ❌ No table rows found")
        else:
            print("   ℹ️ Not a clickable row, would use direct URL navigation")
        
        print(f"\n✅ Single creator test completed!")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_single_creator())