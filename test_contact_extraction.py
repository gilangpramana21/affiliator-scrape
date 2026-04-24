#!/usr/bin/env python3
"""
Test ekstraksi kontak dari halaman detail creator.
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


async def test_contact_extraction():
    """Test ekstraksi kontak dari beberapa creator."""
    
    print("📞 TESTING CONTACT EXTRACTION")
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
        print(f"\n🌐 Navigating to list page...")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        # Get list of creators
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        print(f"📋 Found {len(result.affiliators)} creators")
        
        # Test contact extraction on first few creators
        creators_to_test = min(3, len(result.affiliators))
        contact_results = []
        
        for i in range(creators_to_test):
            creator = result.affiliators[i]
            print(f"\n👤 Testing creator {i+1}: {creator.username}")
            
            try:
                # Click on creator row
                rows = await page.query_selector_all("tbody tr")
                if i < len(rows):
                    # Listen for new page
                    new_page_promise = browser_engine.context.wait_for_event("page")
                    
                    # Click row
                    await rows[i].click()
                    print(f"   🖱️ Clicked row {i}")
                    
                    try:
                        # Wait for detail page
                        detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                        print(f"   🆕 Detail page opened: {detail_page.url}")
                        
                        # Wait for page to load
                        await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        await asyncio.sleep(3)
                        
                        # Handle puzzle if present
                        puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                        if puzzle_indicators:
                            print(f"   🧩 Puzzle detected, refreshing...")
                            await detail_page.reload()
                            await asyncio.sleep(5)
                        
                        # Extract contact information
                        detail_html = await detail_page.content()
                        detail_doc = parser.parse(detail_html)
                        detail_data = extractor.extract_detail_page(detail_doc, detail_page.url)
                        
                        # Show results
                        print(f"   📝 Contact extraction results:")
                        print(f"      Username: {detail_data.username}")
                        print(f"      Phone: {detail_data.nomor_kontak}")
                        print(f"      WhatsApp: {detail_data.nomor_whatsapp}")
                        
                        # Store results
                        contact_results.append({
                            'username': creator.username,
                            'detail_username': detail_data.username,
                            'phone': detail_data.nomor_kontak,
                            'whatsapp': detail_data.nomor_whatsapp,
                            'url': detail_page.url
                        })
                        
                        # Close detail page
                        await detail_page.close()
                        print(f"   ✅ Detail page closed")
                        
                        # Wait between requests
                        await asyncio.sleep(2)
                        
                    except asyncio.TimeoutError:
                        print(f"   ⚠️ No detail page opened for {creator.username}")
                        
                else:
                    print(f"   ❌ Row {i} not found")
                    
            except Exception as e:
                print(f"   ❌ Error testing {creator.username}: {e}")
        
        # Summary
        print(f"\n📊 CONTACT EXTRACTION SUMMARY:")
        print(f"   Creators tested: {len(contact_results)}")
        
        phone_found = sum(1 for r in contact_results if r['phone'])
        whatsapp_found = sum(1 for r in contact_results if r['whatsapp'])
        
        print(f"   Phone numbers found: {phone_found}/{len(contact_results)}")
        print(f"   WhatsApp numbers found: {whatsapp_found}/{len(contact_results)}")
        
        if contact_results:
            print(f"\n📋 DETAILED RESULTS:")
            for i, result in enumerate(contact_results, 1):
                print(f"   {i}. {result['username']}")
                print(f"      Phone: {result['phone'] or 'Not found'}")
                print(f"      WhatsApp: {result['whatsapp'] or 'Not found'}")
                print(f"      URL: {result['url']}")
                print()
        
        # Assessment
        success_rate = ((phone_found + whatsapp_found) / (len(contact_results) * 2) * 100) if contact_results else 0
        
        print(f"🎯 ASSESSMENT:")
        if success_rate >= 70:
            print(f"   ✅ EXCELLENT - {success_rate:.1f}% contact extraction success")
        elif success_rate >= 50:
            print(f"   ✅ GOOD - {success_rate:.1f}% contact extraction success")
        elif success_rate >= 30:
            print(f"   ⚠️ MODERATE - {success_rate:.1f}% contact extraction success")
        else:
            print(f"   ❌ POOR - {success_rate:.1f}% contact extraction success")
        
        print(f"\n✅ Contact extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_contact_extraction())