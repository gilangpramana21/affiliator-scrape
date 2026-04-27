#!/usr/bin/env python3
"""
Debug cookies loading - test apakah cookies bisa di-load dengan benar
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🔍 DEBUG COOKIES LOADING")
    print("=" * 60)
    
    # Load cookies from file
    print("\n📂 Loading cookies from config/cookies.json...")
    with open('config/cookies.json', 'r') as f:
        cookies = json.load(f)
    
    print(f"✅ Loaded {len(cookies)} cookies")
    
    # Show important cookies
    important = ['sessionid', 'SELLER_TOKEN', 'UNIFIED_SELLER_TOKEN', 'SHOP_ID']
    print("\n🔑 Important cookies:")
    for cookie in cookies:
        if cookie['name'] in important:
            print(f"   ✅ {cookie['name']}: {cookie['value'][:30]}...")
    
    async with async_playwright() as p:
        # Launch browser dengan proxy
        proxy_config = {
            "server": "http://31.59.20.176:6754",
            "username": "freacnou",
            "password": "l8393t8tb2ux"
        }
        
        print("\n🌐 Launching browser...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with proxy
        context = await browser.new_context(
            proxy=proxy_config,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        print("✅ Browser launched")
        
        # Add cookies BEFORE navigating
        print("\n🍪 Adding cookies to browser context...")
        await context.add_cookies(cookies)
        print("✅ Cookies added")
        
        # Navigate to affiliate page directly
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        print(f"\n🌐 Navigating to: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("✅ Page loaded")
        except Exception as e:
            print(f"⚠️  Navigation error: {e}")
        
        await asyncio.sleep(5)
        
        # Check current URL
        current_url = page.url
        print(f"\n📍 Current URL: {current_url}")
        
        # Check if we're logged in
        if "login" in current_url.lower():
            print("❌ REDIRECTED TO LOGIN PAGE - Cookies tidak bekerja")
            print("\n🔍 Possible issues:")
            print("   1. Cookies expired")
            print("   2. Cookie domain mismatch")
            print("   3. Tokopedia requires fresh login from this IP")
            print("   4. Proxy IP berbeda dengan IP saat login")
        elif "affiliate" in current_url.lower():
            print("✅ BERHASIL! Sudah di halaman affiliate")
            
            # Check for creator table
            await asyncio.sleep(3)
            rows = await page.query_selector_all("tbody tr")
            print(f"\n📊 Found {len(rows)} creator rows")
            
            if len(rows) > 0:
                print("✅ Creator list loaded successfully!")
            else:
                print("⚠️  No creators found - might need to wait longer or solve CAPTCHA")
        else:
            print(f"⚠️  Unexpected URL: {current_url}")
        
        # Get current cookies from browser
        print("\n🍪 Checking cookies in browser...")
        browser_cookies = await context.cookies()
        print(f"   Browser has {len(browser_cookies)} cookies")
        
        # Check if important cookies are present
        browser_cookie_names = [c['name'] for c in browser_cookies]
        for imp in important:
            if imp in browser_cookie_names:
                print(f"   ✅ {imp} present")
            else:
                print(f"   ❌ {imp} MISSING")
        
        print("\n⏸️  Browser will stay open for inspection")
        print("   Check:")
        print("   1. Are you on the affiliate page?")
        print("   2. Do you see creator list?")
        print("   3. Or are you on login page?")
        
        input("\nPress Enter to close browser...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
