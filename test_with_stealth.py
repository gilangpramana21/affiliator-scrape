#!/usr/bin/env python3
"""
Test dengan stealth mode yang lebih aggressive
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🥷 TEST WITH STEALTH MODE")
    print("=" * 60)
    print("Using aggressive anti-detection techniques")
    print("=" * 60)
    
    # Load cookies
    print("\n📂 Loading cookies...")
    try:
        with open('config/cookies.json', 'r') as f:
            cookies = json.load(f)
        print(f"✅ Loaded {len(cookies)} cookies")
    except:
        print("⚠️  No cookies found")
        cookies = []
    
    async with async_playwright() as p:
        print("\n🌐 Launching browser with stealth mode...")
        
        # Launch with more stealth arguments
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",  # Use actual Chrome instead of Chromium
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certificate-errors',
                '--ignore-certificate-errors-spki-list',
                '--disable-blink-features',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
            timezone_id='Asia/Jakarta',
            permissions=['geolocation'],
            geolocation={'latitude': -6.2088, 'longitude': 106.8456},  # Jakarta
            color_scheme='light',
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
        )
        
        # Inject stealth scripts
        await context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['id-ID', 'id', 'en-US', 'en']
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override toString
            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === window.navigator.permissions.query) {
                    return 'function query() { [native code] }';
                }
                return originalToString.call(this);
            };
        """)
        
        page = await context.new_page()
        print("✅ Browser launched with stealth mode")
        
        # Add cookies
        if cookies:
            print("\n🍪 Adding cookies...")
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        # Navigate to Tokopedia homepage first
        print("\n🌐 Opening Tokopedia homepage...")
        try:
            await page.goto("https://www.tokopedia.com", timeout=120000)
            print("✅ Homepage loaded")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️  Error: {e}")
        
        print(f"📍 Current URL: {page.url}")
        
        # Check if login needed
        if "login" in page.url.lower():
            print("\n❌ Need to login")
            print("   Please login manually in the browser")
            input("\nPress Enter after login...")
            
            # Save cookies
            new_cookies = await context.cookies()
            with open('config/cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2)
            print(f"✅ Saved {len(new_cookies)} cookies")
        
        # Try to navigate to affiliate page
        print("\n🌐 Navigating to Affiliate page...")
        affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        
        try:
            await page.goto(affiliate_url, timeout=120000)
            print("✅ Page loaded")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"⚠️  Error: {e}")
        
        print(f"📍 Current URL: {page.url}")
        
        # Check page content
        page_text = await page.text_content("body")
        
        if "coba lagi" in page_text.lower():
            print("\n⚠️  'Coba lagi' detected!")
            print("\n🔍 Debugging info:")
            print(f"   Page title: {await page.title()}")
            
            # Try to find and click the button
            print("\n🖱️  Trying to click 'Coba lagi' button...")
            
            # Try multiple selectors
            selectors = [
                "button:has-text('Coba lagi')",
                "button:has-text('Coba Lagi')",
                "a:has-text('Coba lagi')",
                "a:has-text('Coba Lagi')",
                "[class*='button']:has-text('Coba')",
                "button",
                "a[role='button']"
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    print(f"   Found {len(elements)} elements for selector: {selector}")
                    
                    for elem in elements:
                        text = await elem.text_content()
                        if text and "coba" in text.lower():
                            print(f"   Trying to click: {text}")
                            await elem.click(force=True)
                            clicked = True
                            print("   ✅ Clicked!")
                            await asyncio.sleep(5)
                            break
                    
                    if clicked:
                        break
                except Exception as e:
                    print(f"   ⚠️  Selector failed: {e}")
            
            if not clicked:
                print("\n❌ Could not click 'Coba lagi' automatically")
                print("   This means Tokopedia is blocking Playwright completely")
                print("\n💡 ALTERNATIVE SOLUTIONS:")
                print("   1. Use undetected-chromedriver (Python library)")
                print("   2. Use browser extension to bypass detection")
                print("   3. Use residential proxy with real browser")
                print("   4. Use Tokopedia API directly (if available)")
                
                input("\nPress Enter to close...")
        else:
            # Check for creator list
            print("\n✅ Checking for creator list...")
            await asyncio.sleep(5)
            
            rows = await page.query_selector_all("tbody tr")
            print(f"📊 Found {len(rows)} creator rows")
            
            if len(rows) > 0:
                print("\n✅ SUCCESS!")
                input("\nPress Enter to close...")
            else:
                print("\n⚠️  No creators found")
                input("\nPress Enter to close...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
