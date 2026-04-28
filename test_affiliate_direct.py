#!/usr/bin/env python3
"""
Test langsung ke Affiliate Center Tokopedia
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🎯 AFFILIATE CENTER DIRECT TEST")
    print("=" * 60)
    print("Target: Tokopedia Affiliate Center")
    print("URL: https://affiliate-id.tokopedia.com/connection/creator")
    print("=" * 60)
    
    # Load cookies
    print("\n📂 Loading cookies...")
    try:
        with open('config/cookies.json', 'r') as f:
            cookies = json.load(f)
        print(f"✅ Loaded {len(cookies)} cookies")
        has_cookies = True
    except:
        print("⚠️  No cookies found - will need to login")
        cookies = []
        has_cookies = False
    
    async with async_playwright() as p:
        print("\n🌐 Launching browser...")
        
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500,  # Slow down actions
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
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
        if has_cookies:
            print("\n🍪 Adding cookies...")
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        # STRATEGY: Navigate step by step
        print("\n" + "=" * 60)
        print("NAVIGATION STRATEGY:")
        print("=" * 60)
        print("Step 1: Tokopedia homepage (establish session)")
        print("Step 2: Seller Center (verify seller access)")
        print("Step 3: Affiliate Center (target page)")
        print("=" * 60)
        
        # STEP 1: Tokopedia Homepage
        print("\n🌐 STEP 1: Opening Tokopedia homepage...")
        try:
            await page.goto("https://www.tokopedia.com", timeout=30000)
            print(f"✅ Homepage loaded: {page.url}")
            await asyncio.sleep(3)
            
            # Check if login needed
            if "login" in page.url.lower():
                print("\n❌ Need to login!")
                print("   Please login manually in the browser")
                input("\nPress Enter after login...")
                
                # Save cookies after login
                new_cookies = await context.cookies()
                with open('config/cookies.json', 'w') as f:
                    json.dump(new_cookies, f, indent=2)
                print(f"✅ Saved {len(new_cookies)} cookies")
        except Exception as e:
            print(f"❌ Homepage error: {e}")
            input("\nPress Enter to continue anyway...")
        
        # STEP 2: Seller Center
        print("\n🌐 STEP 2: Opening Seller Center...")
        try:
            await page.goto("https://seller.tokopedia.com/", timeout=30000)
            print(f"✅ Seller Center loaded: {page.url}")
            await asyncio.sleep(3)
            
            # Check for "Coba lagi"
            page_text = await page.text_content("body")
            if "coba lagi" in page_text.lower():
                print("\n⚠️  'Coba lagi' detected!")
                print("   This means Tokopedia is blocking automation")
                print("\n💡 MANUAL FIX:")
                print("   1. Refresh the page manually (Cmd+R)")
                print("   2. Or click 'Coba lagi' if button appears")
                print("   3. Wait until you see Seller dashboard")
                input("\nPress Enter after you see Seller dashboard...")
        except Exception as e:
            print(f"❌ Seller Center error: {e}")
            input("\nPress Enter to continue anyway...")
        
        # STEP 3: Affiliate Center
        print("\n🌐 STEP 3: Opening Affiliate Center...")
        affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        
        try:
            await page.goto(affiliate_url, timeout=30000)
            print(f"✅ Affiliate Center loaded: {page.url}")
            await asyncio.sleep(5)
            
            # Check for "Coba lagi"
            page_text = await page.text_content("body")
            if "coba lagi" in page_text.lower():
                print("\n⚠️  'Coba lagi' detected on Affiliate page!")
                print("\n💡 MANUAL FIX:")
                print("   1. Refresh the page manually (Cmd+R)")
                print("   2. Or type URL manually in address bar:")
                print(f"      {affiliate_url}")
                print("   3. Wait until you see creator list")
                input("\nPress Enter after you see creator list...")
            
            # Check for creator list
            print("\n🔍 Checking for creator list...")
            await asyncio.sleep(3)
            
            rows = await page.query_selector_all("tbody tr")
            print(f"📊 Found {len(rows)} creator rows")
            
            if len(rows) > 0:
                print("\n✅ SUCCESS! Affiliate Center loaded with data")
                print(f"   Found {len(rows)} creators")
                
                # Save cookies after successful navigation
                final_cookies = await context.cookies()
                with open('config/cookies.json', 'w') as f:
                    json.dump(final_cookies, f, indent=2)
                print(f"\n💾 Saved {len(final_cookies)} cookies for future use")
                
                print("\n📝 What you can do now:")
                print("   1. Click any creator to see detail page")
                print("   2. Check if WhatsApp/Email icons appear")
                print("   3. Try clicking icons to reveal contact info")
                
            else:
                print("\n⚠️  No creators found")
                print("   Possible reasons:")
                print("   1. Page still loading (wait longer)")
                print("   2. Need to solve CAPTCHA")
                print("   3. 'Coba lagi' blocking the page")
                print("   4. Wrong shop_id or no creators available")
                
        except Exception as e:
            print(f"❌ Affiliate Center error: {e}")
            print("\n💡 Try manual navigation:")
            print(f"   Type this URL in browser: {affiliate_url}")
        
        print("\n" + "=" * 60)
        print("CURRENT STATUS:")
        print("=" * 60)
        print(f"URL: {page.url}")
        
        try:
            rows = await page.query_selector_all("tbody tr")
            print(f"Creators: {len(rows)}")
        except:
            print("Creators: Unable to count")
        
        print("\n⏸️  Browser will stay open")
        print("   Press Ctrl+C to stop and save cookies")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
            
            # Save cookies
            try:
                final_cookies = await context.cookies()
                with open('config/cookies.json', 'w') as f:
                    json.dump(final_cookies, f, indent=2)
                print(f"✅ Saved {len(final_cookies)} cookies")
            except:
                pass
            
            await browser.close()
            print("✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
