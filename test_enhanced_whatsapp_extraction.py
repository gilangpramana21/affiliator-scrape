#!/usr/bin/env python3
"""
Test enhanced WhatsApp extraction with interactive clicking functionality.
"""

import asyncio
import logging
import json
from datetime import datetime
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_whatsapp_extraction():
    """Test enhanced WhatsApp extraction with interactive clicking."""
    
    print("📱 TESTING ENHANCED WHATSAPP EXTRACTION")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    orchestrator = ScraperOrchestrator(config)
    
    results = []
    
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
        
        # Test enhanced WhatsApp extraction on first few creators
        creators_to_test = min(3, len(result.affiliators))
        
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
                        
                        # Extract contact information (static)
                        detail_html = await detail_page.content()
                        detail_doc = parser.parse(detail_html)
                        detail_data = extractor.extract_detail_page(detail_doc, detail_page.url)
                        
                        print(f"   📝 Static extraction results:")
                        print(f"      Phone: {detail_data.nomor_kontak}")
                        print(f"      WhatsApp (static): {detail_data.nomor_whatsapp}")
                        
                        # Test interactive WhatsApp extraction
                        print(f"   🔍 Testing interactive WhatsApp extraction...")
                        interactive_whatsapp = await orchestrator._extract_whatsapp_interactive(detail_page, detail_page.url)
                        
                        print(f"   📱 Interactive extraction results:")
                        print(f"      WhatsApp (interactive): {interactive_whatsapp}")
                        
                        # Combine results
                        final_whatsapp = detail_data.nomor_whatsapp or interactive_whatsapp
                        
                        # Store results
                        test_result = {
                            'username': creator.username,
                            'detail_username': detail_data.username,
                            'phone': detail_data.nomor_kontak,
                            'whatsapp_static': detail_data.nomor_whatsapp,
                            'whatsapp_interactive': interactive_whatsapp,
                            'whatsapp_final': final_whatsapp,
                            'url': detail_page.url,
                            'extraction_method': 'interactive' if interactive_whatsapp and not detail_data.nomor_whatsapp else 'static' if detail_data.nomor_whatsapp else 'none'
                        }
                        
                        results.append(test_result)
                        
                        print(f"   ✅ Final WhatsApp: {final_whatsapp or 'Not found'}")
                        
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
        
        # Summary and analysis
        print(f"\n📊 ENHANCED WHATSAPP EXTRACTION SUMMARY:")
        print(f"   Creators tested: {len(results)}")
        
        static_found = sum(1 for r in results if r['whatsapp_static'])
        interactive_found = sum(1 for r in results if r['whatsapp_interactive'])
        total_whatsapp = sum(1 for r in results if r['whatsapp_final'])
        phone_found = sum(1 for r in results if r['phone'])
        
        print(f"   Phone numbers found: {phone_found}/{len(results)}")
        print(f"   WhatsApp (static): {static_found}/{len(results)}")
        print(f"   WhatsApp (interactive): {interactive_found}/{len(results)}")
        print(f"   WhatsApp (total): {total_whatsapp}/{len(results)}")
        
        if results:
            print(f"\n📋 DETAILED RESULTS:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['username']}")
                print(f"      Phone: {result['phone'] or 'Not found'}")
                print(f"      WhatsApp (static): {result['whatsapp_static'] or 'Not found'}")
                print(f"      WhatsApp (interactive): {result['whatsapp_interactive'] or 'Not found'}")
                print(f"      Final WhatsApp: {result['whatsapp_final'] or 'Not found'}")
                print(f"      Method: {result['extraction_method']}")
                print(f"      URL: {result['url']}")
                print()
        
        # Calculate improvement
        improvement = interactive_found
        if improvement > 0:
            print(f"🎉 IMPROVEMENT ANALYSIS:")
            print(f"   Interactive extraction found {improvement} additional WhatsApp numbers!")
            print(f"   This represents a {(improvement/len(results)*100):.1f}% improvement in WhatsApp extraction")
        
        # Assessment
        total_contact_success = ((phone_found + total_whatsapp) / (len(results) * 2) * 100) if results else 0
        whatsapp_success = (total_whatsapp / len(results) * 100) if results else 0
        
        print(f"\n🎯 ASSESSMENT:")
        print(f"   Overall contact success: {total_contact_success:.1f}%")
        print(f"   WhatsApp extraction success: {whatsapp_success:.1f}%")
        
        if whatsapp_success >= 70:
            print(f"   ✅ EXCELLENT WhatsApp extraction performance!")
        elif whatsapp_success >= 50:
            print(f"   ✅ GOOD WhatsApp extraction performance")
        elif whatsapp_success >= 30:
            print(f"   ⚠️ MODERATE WhatsApp extraction performance")
        else:
            print(f"   ❌ POOR WhatsApp extraction performance - needs more work")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"enhanced_whatsapp_test_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "enhanced_whatsapp_extraction",
                "timestamp": timestamp,
                "creators_tested": len(results),
                "phone_found": phone_found,
                "whatsapp_static": static_found,
                "whatsapp_interactive": interactive_found,
                "whatsapp_total": total_whatsapp,
                "improvement_count": improvement,
                "whatsapp_success_rate": whatsapp_success
            },
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        print(f"✅ Enhanced WhatsApp extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_enhanced_whatsapp_extraction())