#!/usr/bin/env python3
"""
Production-ready test for complete contact extraction system.
Tests both phone and WhatsApp extraction with static and interactive methods.
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


async def test_production_contact_extraction():
    """Production-ready test for complete contact extraction system."""
    
    print("🏭 PRODUCTION CONTACT EXTRACTION TEST")
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
    stats = {
        'total_tested': 0,
        'phone_static': 0,
        'whatsapp_static': 0,
        'whatsapp_interactive': 0,
        'total_phone': 0,
        'total_whatsapp': 0,
        'total_contact': 0,
        'success_rate': 0.0
    }
    
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
        
        # Test contact extraction on multiple creators
        creators_to_test = min(5, len(result.affiliators))  # Test up to 5 creators
        
        for i in range(creators_to_test):
            creator = result.affiliators[i]
            print(f"\n👤 Testing creator {i+1}/{creators_to_test}: {creator.username}")
            
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
                        print(f"   🆕 Detail page opened")
                        
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
                        
                        print(f"   📝 Static extraction:")
                        print(f"      Phone: {detail_data.nomor_kontak or 'Not found'}")
                        print(f"      WhatsApp: {detail_data.nomor_whatsapp or 'Not found'}")
                        
                        # Test interactive WhatsApp extraction if static didn't find WhatsApp
                        interactive_whatsapp = None
                        if not detail_data.nomor_whatsapp:
                            print(f"   🔍 Testing interactive WhatsApp extraction...")
                            interactive_whatsapp = await orchestrator._extract_whatsapp_interactive(detail_page, detail_page.url)
                            print(f"      Interactive WhatsApp: {interactive_whatsapp or 'Not found'}")
                        
                        # Combine results
                        final_phone = detail_data.nomor_kontak
                        final_whatsapp = detail_data.nomor_whatsapp or interactive_whatsapp
                        
                        # Update statistics
                        stats['total_tested'] += 1
                        if final_phone:
                            stats['phone_static'] += 1
                            stats['total_phone'] += 1
                        if detail_data.nomor_whatsapp:
                            stats['whatsapp_static'] += 1
                            stats['total_whatsapp'] += 1
                        elif interactive_whatsapp:
                            stats['whatsapp_interactive'] += 1
                            stats['total_whatsapp'] += 1
                        if final_phone or final_whatsapp:
                            stats['total_contact'] += 1
                        
                        # Store results
                        test_result = {
                            'creator_index': i + 1,
                            'username': creator.username,
                            'detail_username': detail_data.username,
                            'phone': final_phone,
                            'whatsapp_static': detail_data.nomor_whatsapp,
                            'whatsapp_interactive': interactive_whatsapp,
                            'whatsapp_final': final_whatsapp,
                            'has_contact': bool(final_phone or final_whatsapp),
                            'extraction_methods': {
                                'phone': 'static' if final_phone else 'none',
                                'whatsapp': 'static' if detail_data.nomor_whatsapp else 'interactive' if interactive_whatsapp else 'none'
                            },
                            'url': detail_page.url
                        }
                        
                        results.append(test_result)
                        
                        # Show summary for this creator
                        contact_status = "✅ HAS CONTACT" if test_result['has_contact'] else "❌ NO CONTACT"
                        print(f"   {contact_status}")
                        if final_phone:
                            print(f"      📞 Phone: {final_phone}")
                        if final_whatsapp:
                            print(f"      📱 WhatsApp: {final_whatsapp}")
                        
                        # Close detail page
                        await detail_page.close()
                        print(f"   ✅ Detail page closed")
                        
                        # Wait between requests
                        await asyncio.sleep(3)
                        
                    except asyncio.TimeoutError:
                        print(f"   ⚠️ No detail page opened for {creator.username}")
                        stats['total_tested'] += 1
                        results.append({
                            'creator_index': i + 1,
                            'username': creator.username,
                            'error': 'No detail page opened',
                            'has_contact': False
                        })
                        
                else:
                    print(f"   ❌ Row {i} not found")
                    
            except Exception as e:
                print(f"   ❌ Error testing {creator.username}: {e}")
                stats['total_tested'] += 1
                results.append({
                    'creator_index': i + 1,
                    'username': creator.username,
                    'error': str(e),
                    'has_contact': False
                })
        
        # Calculate final statistics
        if stats['total_tested'] > 0:
            stats['success_rate'] = (stats['total_contact'] / stats['total_tested']) * 100
            phone_rate = (stats['total_phone'] / stats['total_tested']) * 100
            whatsapp_rate = (stats['total_whatsapp'] / stats['total_tested']) * 100
        else:
            phone_rate = whatsapp_rate = 0
        
        # Comprehensive summary
        print(f"\n📊 PRODUCTION CONTACT EXTRACTION RESULTS:")
        print(f"=" * 60)
        print(f"   Creators tested: {stats['total_tested']}")
        print(f"   Creators with contact info: {stats['total_contact']}")
        print(f"   Overall success rate: {stats['success_rate']:.1f}%")
        print()
        print(f"📞 PHONE EXTRACTION:")
        print(f"   Phone numbers found: {stats['total_phone']}/{stats['total_tested']} ({phone_rate:.1f}%)")
        print(f"   Method: Static extraction")
        print()
        print(f"📱 WHATSAPP EXTRACTION:")
        print(f"   WhatsApp numbers found: {stats['total_whatsapp']}/{stats['total_tested']} ({whatsapp_rate:.1f}%)")
        print(f"   Static method: {stats['whatsapp_static']}")
        print(f"   Interactive method: {stats['whatsapp_interactive']}")
        print()
        
        # Detailed results
        if results:
            print(f"📋 DETAILED RESULTS:")
            for result in results:
                if 'error' in result:
                    print(f"   {result['creator_index']}. {result['username']} - ERROR: {result['error']}")
                else:
                    contact_info = []
                    if result['phone']:
                        contact_info.append(f"📞 {result['phone']}")
                    if result['whatsapp_final']:
                        method = result['extraction_methods']['whatsapp']
                        contact_info.append(f"📱 {result['whatsapp_final']} ({method})")
                    
                    contact_str = " | ".join(contact_info) if contact_info else "No contact info"
                    print(f"   {result['creator_index']}. {result['username']} - {contact_str}")
        
        # Performance assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT:")
        if stats['success_rate'] >= 80:
            print(f"   ✅ EXCELLENT - {stats['success_rate']:.1f}% success rate")
            print(f"   🚀 Ready for production deployment!")
        elif stats['success_rate'] >= 60:
            print(f"   ✅ GOOD - {stats['success_rate']:.1f}% success rate")
            print(f"   ✅ Suitable for production with monitoring")
        elif stats['success_rate'] >= 40:
            print(f"   ⚠️ MODERATE - {stats['success_rate']:.1f}% success rate")
            print(f"   ⚠️ Consider improvements before production")
        else:
            print(f"   ❌ POOR - {stats['success_rate']:.1f}% success rate")
            print(f"   ❌ Needs significant improvements")
        
        # Interactive extraction effectiveness
        if stats['whatsapp_interactive'] > 0:
            improvement = (stats['whatsapp_interactive'] / stats['total_tested']) * 100
            print(f"\n🔍 INTERACTIVE EXTRACTION IMPACT:")
            print(f"   Additional WhatsApp numbers found: {stats['whatsapp_interactive']}")
            print(f"   Improvement: +{improvement:.1f}% WhatsApp extraction rate")
            print(f"   🎉 Interactive extraction is working!")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"production_contact_test_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "production_contact_extraction",
                "timestamp": timestamp,
                "creators_tested": stats['total_tested'],
                "success_rate": stats['success_rate']
            },
            "statistics": stats,
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Final recommendation
        if stats['success_rate'] >= 70:
            print(f"\n🎉 RECOMMENDATION: DEPLOY TO PRODUCTION")
            print(f"   The contact extraction system is performing well!")
            print(f"   Both phone and WhatsApp extraction are working effectively.")
        else:
            print(f"\n⚠️ RECOMMENDATION: NEEDS IMPROVEMENT")
            print(f"   Consider testing more creators or improving extraction methods.")
        
        print(f"\n✅ Production contact extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_production_contact_extraction())