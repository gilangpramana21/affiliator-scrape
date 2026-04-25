#!/usr/bin/env python3
"""
Test scraper with proxy - Manual CAPTCHA solving
Browser will be visible for you to solve CAPTCHA
"""

import asyncio
import json
from datetime import datetime
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.proxy.proxy_manager import ProxyManager


async def main():
    print("🧪 TEST SCRAPER WITH PROXY - MANUAL CAPTCHA")
    print("=" * 60)
    print("⚠️  IMPORTANT:")
    print("   - Browser will open and stay visible")
    print("   - If CAPTCHA appears, solve it manually")
    print("   - If puzzle appears, wait or refresh manually")
    print("=" * 60)
    
    # Setup proxy
    print("\n🌐 Setting up proxy...")
    proxy_manager = ProxyManager()
    proxy_manager.load_webshare_proxies("config/webshare_proxies.txt")
    
    if not proxy_manager.proxies:
        print("❌ No proxies found!")
        return
    
    # Test proxy
    print(f"Testing {len(proxy_manager.proxies)} proxies...")
    working = proxy_manager.validate_all_proxies()
    
    if working == 0:
        print("❌ No working proxies!")
        return
    
    print(f"✅ {working} working proxies")
    
    # Get proxy
    proxy = proxy_manager.get_random_proxy()
    proxy_config = proxy.to_playwright_format()
    print(f"🌐 Using proxy: {proxy}")
    
    # Setup browser
    print("\n🚀 Launching browser...")
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    results = []
    
    try:
        # Launch browser with proxy - NOT HEADLESS
        await browser_engine.launch(
            fingerprint, 
            headless=False,  # Browser will be visible!
            proxy=proxy_config
        )
        print("✅ Browser launched (should be visible now!)")
        print("   Check your screen for the browser window")
        
        # Load cookies
        session_manager.load_session("config/cookies.json")
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
        
        # Test proxy
        print("\n🧪 Testing proxy connection...")
        test_page = await browser_engine.navigate("https://httpbin.org/ip")
        await asyncio.sleep(2)
        content = await test_page.content()
        
        import re
        ip_match = re.search(r'"origin":\s*"([^"]+)"', content)
        if ip_match:
            ip = ip_match.group(1)
            print(f"✅ Proxy working! Your IP: {ip}")
        
        await test_page.close()
        
        # Navigate to list page
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        print(f"\n🌐 Navigating to Tokopedia...")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        print("\n⏸️  Browser is now open!")
        print("   Check the browser window:")
        print("   - If you see CAPTCHA, solve it now")
        print("   - If you see 'Coba lagi', click it")
        print("   - If page loads normally, great!")
        
        input("\nPress Enter after page loads successfully...")
        
        # Get list of creators
        parser = HTMLParser()
        extractor = TokopediaExtractor(parser)
        
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        list_result = extractor.extract_list_page(doc)
        
        total_found = len(list_result.affiliators)
        print(f"\n📋 Found {total_found} creators")
        
        if total_found == 0:
            print("❌ No creators found - page might not have loaded correctly")
            print("   Check the browser window")
            input("Press Enter to close...")
            return
        
        # Process first 5 creators
        to_process = min(5, total_found)
        print(f"Processing first {to_process} creators...")
        
        for i in range(to_process):
            creator = list_result.affiliators[i]
            print(f"\n{i+1}. Processing: {creator.username}")
            
            # Click on creator row
            rows = await page.query_selector_all("tbody tr")
            if i >= len(rows):
                continue
            
            # Listen for new page
            new_page_promise = browser_engine.context.wait_for_event("page")
            
            # Click row
            await rows[i].click()
            
            try:
                # Wait for detail page
                detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                print(f"   ✅ Detail page opened")
                
                # Wait for page load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                
                # Check for CAPTCHA or puzzle
                page_text = await detail_page.text_content("body")
                
                if "captcha" in page_text.lower() or "puzzle" in page_text.lower():
                    print(f"   ⚠️  CAPTCHA or puzzle detected!")
                    print(f"   Please solve it in the browser window")
                    input("   Press Enter after solving...")
                
                # Extract data
                detail_html = await detail_page.content()
                detail_doc = parser.parse(detail_html)
                detail_data = extractor.extract_detail_page(detail_doc, page_url=detail_page.url)
                
                result = {
                    'username': creator.username,
                    'kategori': creator.kategori,
                    'pengikut': creator.pengikut,
                    'gmv': detail_data.gmv or creator.gmv,
                    'gmv_per_pembeli': detail_data.gmv_per_pembeli,
                    'whatsapp': detail_data.nomor_whatsapp,
                    'email': detail_data.nomor_kontak,
                    'scraped_at': datetime.now().isoformat()
                }
                
                results.append(result)
                
                print(f"   📊 Data extracted:")
                print(f"      GMV: {result['gmv']}")
                print(f"      WhatsApp: {result['whatsapp']}")
                print(f"      Email: {result['email']}")
                
                # Close detail page
                await detail_page.close()
                
            except asyncio.TimeoutError:
                print(f"   ❌ Detail page did not open")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Delay between requests
            await asyncio.sleep(4)
        
        # Save results
        if results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_proxy_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {filename}")
            
            # Summary
            print(f"\n📊 SUMMARY:")
            print(f"   Total processed: {len(results)}")
            
            whatsapp_count = sum(1 for r in results if r.get('whatsapp'))
            email_count = sum(1 for r in results if r.get('email'))
            
            print(f"   WhatsApp found: {whatsapp_count}")
            print(f"   Email found: {email_count}")
        
        print("\n✅ Test completed!")
        input("Press Enter to close browser...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
