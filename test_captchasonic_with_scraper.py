#!/usr/bin/env python3
"""Test CaptchaSonic dengan scraper kita langsung."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_captchasonic_with_scraper():
    """Test CaptchaSonic integration dengan scraper kita."""
    
    print("🚀 TESTING CAPTCHASONIC WITH OUR SCRAPER")
    print("=" * 60)
    
    # Check config
    print("1️⃣ CHECKING CONFIGURATION...")
    try:
        with open("config/config_jelajahi.json", 'r') as f:
            config_data = json.load(f)
        
        if 'captcha_api_key' in config_data:
            api_key = config_data['captcha_api_key']
            print(f"✅ CaptchaSonic API Key: {api_key[:15]}...")
        else:
            print("⚠️  CaptchaSonic API key not found in config")
            
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return
    
    # Load scraper config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    print("\n2️⃣ LAUNCHING BROWSER...")
    
    try:
        # Launch browser (visible untuk melihat CaptchaSonic bekerja)
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to target page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n3️⃣ NAVIGATING TO TARGET PAGE...")
        print(f"🌐 URL: {url}")
        
        page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        print("\n4️⃣ CHECKING FOR CAPTCHA...")
        
        # Check for captcha elements
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]', 
            '.g-recaptcha',
            '.h-captcha',
            'img[src*="captcha"]',
            'input[name*="captcha"]'
        ]
        
        captcha_found = False
        captcha_type = None
        
        for selector in captcha_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    captcha_found = True
                    captcha_type = selector
                    print(f"🚨 CAPTCHA DETECTED: {selector}")
                    print(f"   Found {len(elements)} captcha element(s)")
                    break
            except:
                continue
        
        if not captcha_found:
            print("✅ NO CAPTCHA DETECTED - Page is accessible!")
            
            # Check if we can see data
            print("\n5️⃣ CHECKING DATA AVAILABILITY...")
            
            # Look for data indicators
            data_selectors = [
                "table tbody tr",
                "tr:not(:first-child)",
                ".creator-card",
                "[data-testid]"
            ]
            
            data_found = False
            for selector in data_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if len(elements) > 0:
                        data_found = True
                        print(f"✅ Data found: {len(elements)} elements with {selector}")
                        break
                except:
                    continue
            
            if data_found:
                print("🎉 SUCCESS! Scraper can access data without captcha!")
            else:
                print("⚠️  No data found - might need to check page structure")
        
        else:
            print(f"\n5️⃣ CAPTCHA DETECTED - TESTING CAPTCHASONIC...")
            print("🤖 If CaptchaSonic is properly configured, it should solve this automatically")
            print("   Watch the browser window:")
            print("   • CaptchaSonic extension icon might show activity")
            print("   • Captcha should disappear within 10-60 seconds")
            print("   • Page should reload or show content")
            
            # Wait for CaptchaSonic to solve
            print(f"\n⏳ Waiting up to 90 seconds for CaptchaSonic to solve...")
            
            solved = False
            for i in range(18):  # 18 * 5 = 90 seconds
                await asyncio.sleep(5)
                remaining = 90 - (i * 5)
                print(f"   {remaining} seconds remaining...", end="\r")
                
                # Check if captcha is gone
                captcha_still_present = False
                for selector in captcha_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            captcha_still_present = True
                            break
                    except:
                        continue
                
                if not captcha_still_present:
                    print(f"\n✅ CAPTCHA SOLVED by CaptchaSonic! (took {(i+1)*5} seconds)")
                    solved = True
                    break
            
            if not solved:
                print(f"\n❌ Captcha not solved after 90 seconds")
                print("🔧 TROUBLESHOOTING NEEDED:")
                print("   • Check CaptchaSonic extension is installed and enabled")
                print("   • Verify API key is correct in extension popup")
                print("   • Check you have remaining trial credits")
                print("   • Try refreshing the page manually")
            
            # Final check for data
            if solved:
                print("\n6️⃣ CHECKING DATA AFTER CAPTCHA SOLVE...")
                await asyncio.sleep(3)
                
                data_selectors = [
                    "table tbody tr",
                    "tr:not(:first-child)", 
                    ".creator-card"
                ]
                
                for selector in data_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if len(elements) > 0:
                            print(f"✅ Data accessible: {len(elements)} elements found")
                            break
                    except:
                        continue
        
        # Summary
        print(f"\n📊 TEST SUMMARY:")
        print(f"   🔑 API Key: {'✅ Configured' if 'captcha_api_key' in config_data else '❌ Missing'}")
        print(f"   🚨 Captcha: {'🚨 Detected' if captcha_found else '✅ None'}")
        print(f"   🤖 CaptchaSonic: {'✅ Solved' if captcha_found and solved else '⚠️ Not tested' if not captcha_found else '❌ Failed'}")
        print(f"   📊 Data Access: {'✅ Available' if data_found or solved else '❌ Blocked'}")
        
        print(f"\n🎯 RECOMMENDATION:")
        if not captcha_found:
            print("   ✅ Ready to run scraper - no captcha blocking access")
            print("   🚀 CaptchaSonic will handle any captchas that appear later")
        elif solved:
            print("   ✅ CaptchaSonic working perfectly!")
            print("   🚀 Ready for production scraping")
        else:
            print("   🔧 CaptchaSonic needs configuration")
            print("   📞 Check extension setup or contact support")
        
        print(f"\n⏳ Browser window will stay open for manual inspection...")
        print("   You can:")
        print("   • Check CaptchaSonic extension icon/popup")
        print("   • Try navigating to other pages")
        print("   • Test captcha solving manually")
        print("   Press Enter when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()
        print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(test_captchasonic_with_scraper())