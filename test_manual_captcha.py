#!/usr/bin/env python3
"""
Test dengan manual CAPTCHA solving - browser TIDAK akan auto-close
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🔐 MANUAL CAPTCHA SOLVER")
    print("=" * 60)
    print("Browser akan tetap terbuka sampai kamu close manual")
    print("Tidak ada timeout, tidak ada auto-close")
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
        print("\n🌐 Launching browser...")
        
        try:
            # Try to use actual Chrome if available
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                ],
                timeout=0  # No timeout for browser launch
            )
        except:
            # Fallback to chromium
            print("   Chrome not found, using Chromium...")
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                ],
                timeout=0
            )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
            timezone_id='Asia/Jakarta',
        )
        
        # Stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        
        # Set default timeout to 0 (infinite)
        page.set_default_timeout(0)
        page.set_default_navigation_timeout(0)
        
        print("✅ Browser launched")
        
        # Add cookies
        if cookies:
            print("\n🍪 Adding cookies...")
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        print("\n" + "=" * 60)
        print("INSTRUCTIONS:")
        print("=" * 60)
        print("1. Browser akan buka Tokopedia homepage")
        print("2. Kalau ada CAPTCHA, solve dengan tenang")
        print("3. Kalau perlu login, login manual")
        print("4. Navigate manual ke Seller Center")
        print("5. Navigate manual ke Affiliate page")
        print("6. Browser TIDAK akan close otomatis")
        print("7. Tekan Ctrl+C di terminal untuk stop script")
        print("=" * 60)
        
        print("\n🤔 Where do you want to start?")
        print("   1. Tokopedia Homepage (safer, less likely to get blocked)")
        print("   2. Affiliate Center directly (might get 'Coba lagi')")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "2":
            # Navigate directly to affiliate
            print("\n🌐 Opening Affiliate Center directly...")
            affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
            try:
                await page.goto(affiliate_url)
                print("✅ Affiliate page loaded")
            except Exception as e:
                print(f"⚠️  Navigation error (continuing anyway): {e}")
        else:
            # Navigate to homepage first
            print("\n🌐 Opening Tokopedia homepage...")
            try:
                await page.goto("https://www.tokopedia.com")
                print("✅ Homepage loaded")
            except Exception as e:
                print(f"⚠️  Navigation error (continuing anyway): {e}")
        
        print("\n✅ Browser is now open!")
        print("\n📝 What to do now:")
        print("   1. Solve any CAPTCHA if it appears")
        print("   2. Login if needed")
        print("   3. Navigate to: https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259")
        print("   4. Check if you can see creator list")
        print("   5. Try clicking a creator to see detail page")
        print("   6. Check if WhatsApp/Email icons appear")
        
        print("\n⏸️  Browser will stay open indefinitely")
        print("   Press Ctrl+C in terminal to stop and save cookies")
        
        try:
            # Keep script running forever
            while True:
                await asyncio.sleep(10)
                
                # Periodically check if we're on affiliate page
                try:
                    current_url = page.url
                    if "affiliate" in current_url.lower():
                        # Try to count rows
                        rows = await page.query_selector_all("tbody tr")
                        if len(rows) > 0:
                            print(f"\r✅ On affiliate page - {len(rows)} creators found", end="", flush=True)
                except:
                    pass
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping script...")
            
            # Save cookies before closing
            print("\n💾 Saving cookies...")
            try:
                final_cookies = await context.cookies()
                with open('config/cookies.json', 'w') as f:
                    json.dump(final_cookies, f, indent=2)
                print(f"✅ Saved {len(final_cookies)} cookies")
            except Exception as e:
                print(f"⚠️  Could not save cookies: {e}")
            
            print("\n🔍 Final status:")
            try:
                print(f"   Current URL: {page.url}")
                rows = await page.query_selector_all("tbody tr")
                print(f"   Creators found: {len(rows)}")
            except:
                pass
            
            print("\n👋 Closing browser...")
            await browser.close()
            print("✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
