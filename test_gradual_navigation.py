#!/usr/bin/env python3
"""
Test dengan navigasi bertahap - mimic user behavior
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🧪 TEST GRADUAL NAVIGATION")
    print("=" * 60)
    print("Strategy: Navigate seperti user normal")
    print("  1. Buka Tokopedia homepage")
    print("  2. Navigate ke Seller Center")
    print("  3. Navigate ke Affiliate page")
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
        # Launch browser TANPA proxy
        print("\n🌐 Launching browser (NO PROXY)...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
            timezone_id='Asia/Jakarta'
        )
        
        # Remove webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        print("✅ Browser launched")
        
        # Add cookies if available
        if cookies:
            print("\n🍪 Adding cookies...")
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        # STEP 1: Navigate ke Tokopedia homepage dulu
        print("\n🌐 STEP 1: Opening Tokopedia homepage...")
        try:
            await page.goto("https://www.tokopedia.com", wait_until="commit", timeout=120000)
            print("✅ Homepage loaded")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️  Homepage error: {e}")
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Check if we need to login
        if "login" in current_url.lower():
            print("\n❌ Need to login first")
            print("\n📝 MANUAL LOGIN:")
            print("   1. Login dengan akun Tokopedia")
            print("   2. Tunggu sampai masuk homepage")
            
            input("\nPress Enter setelah login berhasil...")
            
            # Save new cookies
            new_cookies = await context.cookies()
            with open('config/cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2)
            print(f"\n✅ Saved {len(new_cookies)} fresh cookies!")
        
        # STEP 2: Navigate ke Seller Center
        print("\n🌐 STEP 2: Opening Seller Center...")
        try:
            await page.goto("https://seller.tokopedia.com/", wait_until="commit", timeout=120000)
            print("✅ Seller Center loaded")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️  Seller Center error: {e}")
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Check for "Coba lagi" message
        page_text = await page.text_content("body")
        if "coba lagi" in page_text.lower():
            print("\n⚠️  'Coba lagi' detected!")
            print("   Tokopedia is blocking automation")
            print("\n💡 MANUAL INTERVENTION:")
            print("   1. Click 'Coba lagi' button manually in browser")
            print("   2. Or navigate manually to Seller Center")
            print("   3. Wait until you see Seller dashboard")
            
            input("\nPress Enter setelah berhasil masuk Seller Center...")
        
        # STEP 3: Navigate ke Affiliate page
        print("\n🌐 STEP 3: Opening Affiliate page...")
        affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        
        try:
            await page.goto(affiliate_url, wait_until="commit", timeout=120000)
            print("✅ Affiliate page loaded")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"⚠️  Affiliate page error: {e}")
            print("   Continuing anyway...")
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Check for "Coba lagi" again
        page_text = await page.text_content("body")
        if "coba lagi" in page_text.lower():
            print("\n⚠️  'Coba lagi' detected on Affiliate page!")
            print("\n💡 MANUAL INTERVENTION:")
            print("   1. Click 'Coba lagi' button manually")
            print("   2. Or type the affiliate URL manually in browser")
            print("   3. Wait until you see creator list")
            
            input("\nPress Enter setelah berhasil masuk Affiliate page...")
        
        # Check for creator list
        print("\n✅ Checking for creator list...")
        await asyncio.sleep(5)
        
        rows = await page.query_selector_all("tbody tr")
        print(f"📊 Found {len(rows)} creator rows")
        
        if len(rows) > 0:
            print("\n✅ SUCCESS! Creator list loaded")
            print(f"   Found {len(rows)} creators")
            
            # Save cookies after successful navigation
            final_cookies = await context.cookies()
            with open('config/cookies.json', 'w') as f:
                json.dump(final_cookies, f, indent=2)
            print(f"\n💾 Saved {len(final_cookies)} cookies for future use")
            
            # Click first creator
            print("\n🖱️  Clicking first creator...")
            
            try:
                # Wait for new page
                async with context.expect_page(timeout=10000) as new_page_info:
                    await rows[0].click()
                    detail_page = await new_page_info.value
                
                print("✅ Detail page opened!")
                
                # Wait for page load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=30000)
                print("✅ Page loaded")
                
                # Wait for lazy loading
                print("\n⏳ Waiting 15 seconds for lazy-loaded content...")
                await asyncio.sleep(15)
                
                print("\n⏸️  Detail page ready!")
                print("   Check browser:")
                print("   1. Can you see WhatsApp icon?")
                print("   2. Can you see Email icon?")
                print("   3. Try clicking them manually")
                
                input("\nPress Enter to close browser...")
                
                await detail_page.close()
            except Exception as e:
                print(f"⚠️  Error clicking creator: {e}")
                input("\nPress Enter to close browser...")
        else:
            print("\n⚠️  No creators found")
            print("   Browser will stay open for manual inspection")
            
            input("\nPress Enter to close browser...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
