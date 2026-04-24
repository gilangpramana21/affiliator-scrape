#!/usr/bin/env python3
"""
Test contact extraction specifically designed for public WiFi conditions.
Handles increased CAPTCHA frequency, "Coba Lagi" messages, and rate limiting.
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


async def test_public_wifi_extraction():
    """Test contact extraction optimized for public WiFi conditions."""
    
    print("📶 PUBLIC WIFI CONTACT EXTRACTION TEST")
    print("=" * 60)
    print("🔧 Optimized for:")
    print("   - Increased CAPTCHA frequency")
    print("   - 'Coba Lagi' messages")
    print("   - Rate limiting")
    print("   - IP reputation issues")
    print("=" * 60)
    
    # Load config optimized for public WiFi
    try:
        config = Configuration.from_file("config/config_public_wifi.json")
        print("✅ Using public WiFi optimized config")
    except:
        config = Configuration.from_file("config/config_jelajahi.json")
        print("⚠️ Using default config (public WiFi config not found)")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    orchestrator = ScraperOrchestrator(config)
    
    results = []
    stats = {
        'total_attempted': 0,
        'coba_lagi_encountered': 0,
        'captcha_encountered': 0,
        'detail_pages_opened': 0,
        'contact_extracted': 0,
        'phone_found': 0,
        'whatsapp_found': 0
    }
    
    try:
        # Launch browser with extra stealth for public WiFi
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched with stealth mode")
        
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
        
        # Navigate to list page with extra patience
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to list page (public WiFi mode)...")
        
        page = await browser_engine.navigate(url)
        
        # Extra wait for public WiFi
        print("⏳ Waiting for page load (public WiFi delay)...")
        await asyncio.sleep(8)
        
        # Check for "Coba Lagi" on list page
        await check_and_handle_coba_lagi(page, stats)
        
        # Get list of creators
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        print(f"📋 Found {len(result.affiliators)} creators")
        
        # Test fewer creators for public WiFi to avoid rate limiting
        creators_to_test = min(3, len(result.affiliators))
        print(f"🎯 Testing {creators_to_test} creators (reduced for public WiFi)")
        
        for i in range(creators_to_test):
            creator = result.affiliators[i]
            print(f"\n👤 Testing creator {i+1}/{creators_to_test}: {creator.username}")
            stats['total_attempted'] += 1
            
            try:
                # Extra delay between requests for public WiFi
                if i > 0:
                    print("⏳ Public WiFi delay between requests...")
                    await asyncio.sleep(10)
                
                # Refresh page to get fresh elements
                print("🔄 Refreshing page for fresh elements...")
                await page.reload()
                await asyncio.sleep(5)
                
                # Check for "Coba Lagi" after refresh
                await check_and_handle_coba_lagi(page, stats)
                
                # Get fresh row elements
                rows = await page.query_selector_all("tbody tr")
                
                if i < len(rows):
                    target_row = rows[i]
                    
                    # Click with public WiFi patience
                    print(f"🖱️ Clicking row with public WiFi patience...")
                    new_page_promise = browser_engine.context.wait_for_event("page")
                    await target_row.click()
                    
                    try:
                        # Longer timeout for public WiFi
                        detail_page = await asyncio.wait_for(new_page_promise, timeout=15.0)
                        stats['detail_pages_opened'] += 1
                        print(f"✅ Detail page opened")
                        
                        # Wait for page load with public WiFi patience
                        await detail_page.wait_for_load_state("domcontentloaded", timeout=20000)
                        await asyncio.sleep(8)
                        
                        # Check for "Coba Lagi" on detail page
                        await check_and_handle_coba_lagi(detail_page, stats)
                        
                        # Handle puzzle with extra patience
                        puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                        if puzzle_indicators:
                            print(f"🧩 Puzzle detected, refreshing with public WiFi patience...")
                            await detail_page.reload()
                            await asyncio.sleep(8)
                        
                        # Check for CAPTCHA
                        page_content = await detail_page.content()
                        if any(term in page_content.lower() for term in ['captcha', 'recaptcha', 'hcaptcha']):
                            stats['captcha_encountered'] += 1
                            print(f"🤖 CAPTCHA detected - manual solving required")
                            print(f"   Please solve the CAPTCHA manually...")
                            
                            # Wait for manual CAPTCHA solving
                            input("   Press Enter after solving CAPTCHA...")
                        
                        # Extract contact information
                        detail_html = await detail_page.content()
                        detail_doc = parser.parse(detail_html)
                        detail_data = extractor.extract_detail_page(detail_doc, detail_page.url)
                        
                        # Interactive WhatsApp extraction with public WiFi patience
                        interactive_whatsapp = None
                        if not detail_data.nomor_whatsapp:
                            print(f"🔍 Interactive WhatsApp extraction (public WiFi mode)...")
                            interactive_whatsapp = await orchestrator._extract_whatsapp_interactive(detail_page, detail_page.url)
                        
                        # Results
                        final_phone = detail_data.nomor_kontak
                        final_whatsapp = detail_data.nomor_whatsapp or interactive_whatsapp
                        
                        if final_phone:
                            stats['phone_found'] += 1
                        if final_whatsapp:
                            stats['whatsapp_found'] += 1
                        if final_phone or final_whatsapp:
                            stats['contact_extracted'] += 1
                        
                        # Store results
                        test_result = {
                            'creator_index': i + 1,
                            'username': creator.username,
                            'phone': final_phone,
                            'whatsapp': final_whatsapp,
                            'has_contact': bool(final_phone or final_whatsapp),
                            'coba_lagi_encountered': False,  # Will be updated if encountered
                            'captcha_encountered': False,    # Will be updated if encountered
                            'status': 'success'
                        }
                        
                        results.append(test_result)
                        
                        # Show results
                        print(f"📝 Extraction results:")
                        print(f"   Phone: {final_phone or 'Not found'}")
                        print(f"   WhatsApp: {final_whatsapp or 'Not found'}")
                        
                        contact_status = "✅ HAS CONTACT" if test_result['has_contact'] else "❌ NO CONTACT"
                        print(f"   {contact_status}")
                        
                        # Close detail page
                        await detail_page.close()
                        print(f"✅ Detail page closed")
                        
                    except asyncio.TimeoutError:
                        print(f"⚠️ Detail page timeout (common with public WiFi)")
                        results.append({
                            'creator_index': i + 1,
                            'username': creator.username,
                            'error': 'Page timeout',
                            'has_contact': False,
                            'status': 'timeout'
                        })
                
                else:
                    print(f"❌ Row {i} not found")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    'creator_index': i + 1,
                    'username': creator.username,
                    'error': str(e),
                    'has_contact': False,
                    'status': 'error'
                })
        
        # Calculate success rates
        success_rate = (stats['contact_extracted'] / stats['detail_pages_opened'] * 100) if stats['detail_pages_opened'] > 0 else 0
        page_success_rate = (stats['detail_pages_opened'] / stats['total_attempted'] * 100) if stats['total_attempted'] > 0 else 0
        
        # Summary
        print(f"\n📊 PUBLIC WIFI EXTRACTION RESULTS:")
        print(f"=" * 60)
        print(f"📈 SUCCESS RATES:")
        print(f"   Page opening: {page_success_rate:.1f}%")
        print(f"   Contact extraction: {success_rate:.1f}%")
        print()
        print(f"📞 CONTACT RESULTS:")
        print(f"   Phone numbers: {stats['phone_found']}")
        print(f"   WhatsApp numbers: {stats['whatsapp_found']}")
        print(f"   Total with contact: {stats['contact_extracted']}")
        print()
        print(f"🚫 PUBLIC WIFI CHALLENGES:")
        print(f"   'Coba Lagi' messages: {stats['coba_lagi_encountered']}")
        print(f"   CAPTCHAs encountered: {stats['captcha_encountered']}")
        
        # Assessment
        print(f"\n🎯 PUBLIC WIFI ASSESSMENT:")
        if success_rate >= 70:
            print(f"   ✅ EXCELLENT performance despite public WiFi!")
        elif success_rate >= 50:
            print(f"   ✅ GOOD performance for public WiFi conditions")
        elif success_rate >= 30:
            print(f"   ⚠️ MODERATE performance - expected for public WiFi")
        else:
            print(f"   ❌ POOR performance - public WiFi causing issues")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS FOR PUBLIC WIFI:")
        if stats['coba_lagi_encountered'] > 2:
            print(f"   🔄 High 'Coba Lagi' frequency - consider longer delays")
        if stats['captcha_encountered'] > 1:
            print(f"   🤖 High CAPTCHA frequency - consider premium CAPTCHA solver")
        if page_success_rate < 50:
            print(f"   📶 Poor page opening - WiFi connection may be unstable")
        
        print(f"\n✅ Use private WiFi/mobile data for better performance")
        print(f"✅ Consider VPN with good IP reputation")
        print(f"✅ Use premium CAPTCHA solving service")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"public_wifi_test_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "public_wifi_extraction",
                "timestamp": timestamp,
                "wifi_type": "public",
                "success_rate": success_rate
            },
            "statistics": stats,
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        print(f"✅ Public WiFi extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


async def check_and_handle_coba_lagi(page, stats):
    """Check for and handle 'Coba Lagi' messages."""
    try:
        page_content = await page.content()
        page_text = page_content.lower()
        
        coba_lagi_patterns = [
            "coba lagi",
            "try again", 
            "silakan coba lagi",
            "terjadi kesalahan"
        ]
        
        if any(pattern in page_text for pattern in coba_lagi_patterns):
            stats['coba_lagi_encountered'] += 1
            print(f"🔄 'Coba Lagi' detected - refreshing...")
            
            await page.reload()
            await asyncio.sleep(8)  # Extra wait for public WiFi
            
            print(f"✅ Page refreshed")
    
    except Exception as e:
        print(f"⚠️ Error checking 'Coba Lagi': {e}")


if __name__ == "__main__":
    asyncio.run(test_public_wifi_extraction())