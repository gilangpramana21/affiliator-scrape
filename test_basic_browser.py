#!/usr/bin/env python3
"""
Test paling basic - just open browser and navigate
"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    print("🧪 BASIC BROWSER TEST")
    print("=" * 60)
    
    async with async_playwright() as p:
        print("\n🌐 Launching browser...")
        
        # Launch browser - paling simple
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000  # Slow down by 1 second per action
        )
        
        print("✅ Browser launched")
        
        # Create page
        page = await browser.new_page()
        print("✅ Page created")
        
        # Navigate to Google first (simple test)
        print("\n🌐 Testing navigation to Google...")
        try:
            await page.goto("https://www.google.com", timeout=30000)
            print(f"✅ Google loaded: {page.url}")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"❌ Google failed: {e}")
        
        # Navigate to Tokopedia
        print("\n🌐 Testing navigation to Tokopedia...")
        try:
            await page.goto("https://www.tokopedia.com", timeout=30000)
            print(f"✅ Tokopedia loaded: {page.url}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"❌ Tokopedia failed: {e}")
        
        print(f"\n📍 Final URL: {page.url}")
        
        print("\n⏸️  Browser will stay open")
        print("   Check what you see in the browser")
        
        input("\nPress Enter to close...")
        
        await browser.close()
        print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
