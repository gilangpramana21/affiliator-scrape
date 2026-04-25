#!/usr/bin/env python3
"""
Simple browser test - just open browser and navigate to the page
"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    print("🧪 SIMPLE BROWSER TEST")
    print("=" * 60)
    print("This will:")
    print("  1. Open a visible browser")
    print("  2. Navigate to Tokopedia affiliate page")
    print("  3. Wait for you to solve CAPTCHA manually")
    print("  4. Let you inspect the page")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch browser with proxy
        proxy_config = {
            "server": "http://31.59.20.176:6754",
            "username": "freacnou",
            "password": "l8393t8tb2ux"
        }
        
        print("\n🌐 Launching browser with proxy...")
        browser = await p.chromium.launch(
            headless=False,  # Visible browser
            proxy=proxy_config
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        print("✅ Browser launched")
        
        # Navigate to the page
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        print(f"\n🌐 Navigating to: {url}")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("✅ Page loaded")
        
        print("\n⏸️  Browser is now open!")
        print("   Please:")
        print("   1. Solve any CAPTCHA if it appears")
        print("   2. Wait for the creator list to load")
        print("   3. Check if you can see the creators")
        
        input("\nPress Enter when ready to continue...")
        
        # Try to find rows
        print("\n🔍 Looking for creator rows...")
        rows = await page.query_selector_all("tbody tr")
        print(f"   Found {len(rows)} rows")
        
        if rows:
            print("\n✅ Creators found! Clicking first one...")
            
            # Wait for new page to open
            async with context.expect_page() as new_page_info:
                await rows[0].click()
                detail_page = await new_page_info.value
            
            print("✅ Detail page opened!")
            
            # Wait for page to load
            await detail_page.wait_for_load_state("domcontentloaded")
            print("✅ Detail page loaded")
            
            # Wait for lazy loading
            print("\n⏳ Waiting 15 seconds for lazy-loaded content...")
            await asyncio.sleep(15)
            
            print("\n⏸️  Detail page should be fully loaded now")
            print("   Please check:")
            print("   1. Can you see WhatsApp icon?")
            print("   2. Can you see Email icon?")
            print("   3. Try clicking them manually")
            
            input("\nPress Enter to close browser...")
            
            await detail_page.close()
        else:
            print("\n❌ No rows found - might need to solve CAPTCHA")
            input("Press Enter to close browser...")
        
        await browser.close()
        print("\n✅ Browser closed")


if __name__ == "__main__":
    asyncio.run(main())
