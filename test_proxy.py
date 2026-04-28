#!/usr/bin/env python3
"""
Test Bright Data Proxy Connection
"""

import asyncio
from playwright.async_api import async_playwright


async def test_proxy():
    print("🧪 Testing Bright Data Proxy Connection")
    print("=" * 60)
    
    # GANTI INI DENGAN CREDENTIALS KAMU
    PROXY_SERVER = "http://brd.superproxy.io:22225"
    PROXY_USERNAME = "YOUR_USERNAME_HERE"  # ← GANTI INI
    PROXY_PASSWORD = "YOUR_PASSWORD_HERE"  # ← GANTI INI
    
    print(f"Proxy: {PROXY_SERVER}")
    print(f"Username: {PROXY_USERNAME[:20]}...")
    print()
    
    try:
        async with async_playwright() as p:
            # Launch browser with proxy
            browser = await p.chromium.launch(
                headless=False,
                proxy={
                    "server": PROXY_SERVER,
                    "username": PROXY_USERNAME,
                    "password": PROXY_PASSWORD
                }
            )
            
            print("✅ Browser launched with proxy")
            
            # Create page
            page = await browser.new_page()
            
            # Test 1: Check IP
            print("\n📍 Test 1: Checking IP address...")
            await page.goto("https://api.ipify.org?format=json")
            await asyncio.sleep(2)
            
            content = await page.content()
            print(f"   Response: {content}")
            
            # Test 2: Check location
            print("\n🌍 Test 2: Checking location...")
            await page.goto("https://ipapi.co/json/")
            await asyncio.sleep(2)
            
            content = await page.content()
            print(f"   Response: {content[:200]}...")
            
            # Test 3: Access Tokopedia
            print("\n🏪 Test 3: Accessing Tokopedia...")
            await page.goto("https://affiliate.tokopedia.com/")
            await asyncio.sleep(3)
            
            title = await page.title()
            print(f"   Page title: {title}")
            
            if "Tokopedia" in title:
                print("   ✅ Successfully accessed Tokopedia!")
            else:
                print("   ⚠️ Unexpected page title")
            
            await browser.close()
            
            print("\n" + "=" * 60)
            print("✅ PROXY TEST SUCCESSFUL!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Copy your credentials to config/config_production.json")
            print("2. Run quick_test.py to test scraper")
            
    except Exception as e:
        print(f"\n❌ PROXY TEST FAILED!")
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check username and password are correct")
        print("2. Check you have credits in Bright Data account")
        print("3. Check proxy zone is active")
        print("4. Try creating a new zone")


if __name__ == "__main__":
    asyncio.run(test_proxy())
