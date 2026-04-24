#!/usr/bin/env python3
"""Verify and troubleshoot CaptchaSonic setup."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator

async def verify_captchasonic_setup():
    """Verify CaptchaSonic setup and troubleshoot issues."""
    
    print("🔍 VERIFYING CAPTCHASONIC SETUP")
    print("=" * 50)
    
    # Check configuration
    print("\n1️⃣ CHECKING CONFIGURATION...")
    
    try:
        with open("config/config_jelajahi.json", 'r') as f:
            config = json.load(f)
        
        if 'captchasonic_api_key' in config:
            api_key = config['captchasonic_api_key']
            print(f"✅ API Key found: {api_key[:10]}...")
        else:
            print("❌ API Key not found in config")
            return False
            
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False
    
    # Launch browser and test
    print("\n2️⃣ TESTING BROWSER INTEGRATION...")
    
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Navigate to extension management page
        page = await browser_engine.navigate("chrome://extensions/")
        await asyncio.sleep(2)
        
        print("🔍 Checking installed extensions...")
        print("   Look for 'CaptchaSonic: Automatic Captcha Solver' in the list")
        print("   Make sure it's ENABLED (toggle switch is ON)")
        
        input("Press Enter after verifying extension is installed and enabled...")
        
        # Test on actual captcha
        print("\n3️⃣ TESTING ON REAL CAPTCHA...")
        
        # Navigate to reCAPTCHA demo
        await page.goto("https://www.google.com/recaptcha/api2/demo")
        await asyncio.sleep(3)
        
        print("🎯 Testing on Google reCAPTCHA demo page")
        print("   Watch carefully:")
        print("   • CaptchaSonic should detect the captcha")
        print("   • Extension icon might show activity")
        print("   • Captcha should be solved automatically")
        
        # Wait longer for solving
        print("\n⏳ Waiting 60 seconds for automatic solving...")
        
        for i in range(60, 0, -5):
            print(f"   {i} seconds remaining...", end="\r")
            await asyncio.sleep(5)
            
            # Check if solved
            try:
                success_elements = await page.query_selector_all("text=Verification Success")
                if success_elements:
                    print("\n✅ SUCCESS! CaptchaSonic solved the captcha!")
                    return True
            except:
                pass
        
        print("\n⚠️  Captcha not solved automatically")
        
        # Troubleshooting steps
        print("\n🔧 TROUBLESHOOTING STEPS:")
        
        print("\n4️⃣ COMMON ISSUES & SOLUTIONS:")
        
        print("\n🔍 Issue 1: Extension not working")
        print("   Solutions:")
        print("   • Check extension is installed and enabled")
        print("   • Click extension icon and verify API key")
        print("   • Make sure 'Auto Solve' is enabled")
        print("   • Try refreshing the page")
        
        print("\n🔍 Issue 2: API key problems")
        print("   Solutions:")
        print("   • Verify API key is correct (no extra spaces)")
        print("   • Check you have remaining trial credits")
        print("   • Try logging into my.captchasonic.com to verify account")
        
        print("\n🔍 Issue 3: Extension permissions")
        print("   Solutions:")
        print("   • Go to chrome://extensions/")
        print("   • Click 'Details' on CaptchaSonic extension")
        print("   • Enable 'Allow in incognito' if needed")
        print("   • Enable 'Allow access to file URLs' if needed")
        
        # Manual verification
        print("\n5️⃣ MANUAL VERIFICATION:")
        print("   Try solving the captcha manually to test the page")
        print("   Then we'll test with our scraper")
        
        manual_test = input("\nDid you manage to solve the captcha manually? (y/n): ").lower().strip()
        
        if manual_test == 'y':
            print("✅ Page is working - issue is with CaptchaSonic configuration")
        else:
            print("❌ Page itself has issues")
        
        # Test with our scraper
        print("\n6️⃣ TESTING WITH OUR SCRAPER...")
        
        from src.core.session_manager import SessionManager
        from src.models.config import Configuration
        
        # Load our scraper config
        scraper_config = Configuration.from_file("config/config_jelajahi.json")
        session_manager = SessionManager()
        session_manager.load_session(scraper_config.cookie_file)
        cookies = session_manager.get_cookies()
        
        # Navigate to our target page
        url = f"{scraper_config.base_url}{scraper_config.list_page_url}{scraper_config.list_page_query}"
        print(f"🌐 Testing on our target page: {url}")
        
        await page.goto(url)
        
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
        
        await page.reload()
        await asyncio.sleep(5)
        
        print("🔍 Checking for captcha on our target page...")
        
        # Check for captcha elements
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '.h-captcha'
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                captcha_found = True
                print(f"🚨 CAPTCHA found: {selector}")
                break
        
        if not captcha_found:
            print("✅ No captcha on target page - scraper should work normally!")
        else:
            print("⚠️  Captcha present - CaptchaSonic should solve it")
            print("   Waiting 30 seconds for automatic solving...")
            await asyncio.sleep(30)
            
            # Check again
            captcha_still_present = False
            for selector in captcha_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    captcha_still_present = True
                    break
            
            if not captcha_still_present:
                print("✅ Captcha solved by CaptchaSonic!")
            else:
                print("❌ Captcha still present")
        
        print("\n📊 VERIFICATION SUMMARY:")
        print(f"   🔑 API Key: {'✅ Configured' if api_key else '❌ Missing'}")
        print(f"   🔌 Extension: {'⚠️ Needs verification' if not captcha_found else '✅ Working'}")
        print(f"   🎯 Target Page: {'✅ Accessible' if not captcha_found else '⚠️ Has captcha'}")
        
        print("\n💡 NEXT STEPS:")
        if not captcha_found:
            print("   ✅ Ready to run scraper - no captcha blocking")
        else:
            print("   🔧 Fix CaptchaSonic configuration")
            print("   📞 Contact CaptchaSonic support if needed")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await browser_engine.close()
    
    return True

if __name__ == "__main__":
    asyncio.run(verify_captchasonic_setup())