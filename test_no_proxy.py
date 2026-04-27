#!/usr/bin/env python3
"""
Test TANPA proxy - untuk testing di WiFi rumah
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🧪 TEST TANPA PROXY (WiFi Rumah)")
    print("=" * 60)
    print("Ini akan test scraping tanpa proxy")
    print("Cocok untuk testing di WiFi rumah")
    print("=" * 60)
    
    # Load cookies
    print("\n📂 Loading cookies...")
    try:
        with open('config/cookies.json', 'r') as f:
            cookies = json.load(f)
        print(f"✅ Loaded {len(cookies)} cookies")
    except:
        print("⚠️  No cookies found, will need manual login")
        cookies = []
    
    async with async_playwright() as p:
        # Launch browser TANPA proxy
        print("\n🌐 Launching browser (NO PROXY)...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        print("✅ Browser launched")
        
        # Add cookies if available
        if cookies:
            print("\n🍪 Adding cookies...")
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        # Navigate to affiliate page
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        print(f"\n🌐 Navigating to: {url}")
        
        try:
            # Try with longer timeout and less strict wait condition
            await page.goto(url, wait_until="commit", timeout=120000)
            print("✅ Page navigation started")
            
            # Wait for page to be interactive
            await asyncio.sleep(10)
        except Exception as e:
            print(f"⚠️  Navigation warning: {e}")
            print("   Continuing anyway...")
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        if "login" in current_url.lower():
            print("\n❌ Redirected to login page")
            print("\n📝 MANUAL LOGIN REQUIRED:")
            print("   1. Login dengan akun Tokopedia kamu")
            print("   2. Tunggu sampai masuk Seller Center")
            print("   3. Script akan save cookies baru")
            
            input("\nPress Enter setelah login berhasil...")
            
            # Save new cookies
            new_cookies = await context.cookies()
            with open('config/cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2)
            print(f"\n✅ Saved {len(new_cookies)} fresh cookies!")
            
            # Navigate again
            try:
                await page.goto(url, wait_until="commit", timeout=120000)
                await asyncio.sleep(10)
            except Exception as e:
                print(f"⚠️  Navigation warning: {e}")
                print("   Continuing anyway...")
        
        print("\n✅ Checking for creator list...")
        await asyncio.sleep(3)
        
        rows = await page.query_selector_all("tbody tr")
        print(f"📊 Found {len(rows)} creator rows")
        
        if len(rows) > 0:
            print("\n✅ SUCCESS! Creator list loaded")
            print(f"   Found {len(rows)} creators")
            
            # Click first creator
            print("\n🖱️  Clicking first creator...")
            
            # Wait for new page
            async with context.expect_page() as new_page_info:
                await rows[0].click()
                detail_page = await new_page_info.value
            
            print("✅ Detail page opened!")
            
            # Wait for page load
            await detail_page.wait_for_load_state("domcontentloaded")
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
        else:
            print("\n⚠️  No creators found")
            print("   Might need to:")
            print("   1. Solve CAPTCHA")
            print("   2. Wait longer for page load")
            print("   3. Check if you're on correct page")
            
            input("\nPress Enter to close browser...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
