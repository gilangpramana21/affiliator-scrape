#!/usr/bin/env python3
"""
Login manual ke Tokopedia dan save cookies yang fresh
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🔐 LOGIN MANUAL & SAVE COOKIES")
    print("=" * 60)
    print("Script ini akan:")
    print("  1. Buka browser Tokopedia")
    print("  2. Kamu login manual")
    print("  3. Navigate ke Seller Center Affiliate")
    print("  4. Save cookies yang valid")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch browser dengan proxy
        proxy_config = {
            "server": "http://31.59.20.176:6754",
            "username": "freacnou",
            "password": "l8393t8tb2ux"
        }
        
        print("\n🌐 Launching browser dengan proxy...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            proxy=proxy_config,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        print("✅ Browser launched")
        
        # Navigate ke Tokopedia login page
        print("\n🌐 Navigating ke Tokopedia...")
        await page.goto("https://www.tokopedia.com/login", wait_until="domcontentloaded")
        
        print("\n⏸️  STEP 1: LOGIN")
        print("   Silakan login dengan akun Tokopedia kamu")
        print("   - Masukkan email/phone")
        print("   - Masukkan password")
        print("   - Solve CAPTCHA jika ada")
        print("   - Tunggu sampai berhasil login")
        
        input("\nPress Enter setelah berhasil login...")
        
        # Navigate ke Seller Center
        print("\n🌐 Navigating ke Seller Center...")
        await page.goto("https://seller.tokopedia.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        print("\n⏸️  STEP 2: SELLER CENTER")
        print("   Pastikan kamu sudah masuk ke Seller Center")
        print("   - Lihat dashboard seller")
        print("   - Pastikan tidak ada error")
        
        input("\nPress Enter jika sudah di Seller Center...")
        
        # Navigate ke Affiliate page
        print("\n🌐 Navigating ke Affiliate Connection...")
        affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        await page.goto(affiliate_url, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print("\n⏸️  STEP 3: AFFILIATE PAGE")
        print("   Pastikan kamu bisa lihat:")
        print("   - List creator/affiliator")
        print("   - Table dengan data")
        print("   - Tidak ada error atau redirect")
        
        input("\nPress Enter jika sudah di halaman Affiliate...")
        
        # Save cookies
        print("\n💾 Saving cookies...")
        cookies = await context.cookies()
        
        # Convert to format yang compatible
        cookie_data = []
        for cookie in cookies:
            cookie_data.append({
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie['path'],
                'httpOnly': cookie.get('httpOnly', False),
                'secure': cookie.get('secure', False),
                'sameSite': cookie.get('sameSite', 'Lax')
            })
        
        # Save to file
        with open('config/cookies.json', 'w') as f:
            json.dump(cookie_data, f, indent=2)
        
        print(f"✅ Saved {len(cookie_data)} cookies to config/cookies.json")
        
        # Show cookie summary
        print("\n📊 Cookie Summary:")
        tokopedia_cookies = [c for c in cookie_data if 'tokopedia' in c['domain']]
        print(f"   Total cookies: {len(cookie_data)}")
        print(f"   Tokopedia cookies: {len(tokopedia_cookies)}")
        
        # Show important cookies
        important_cookies = ['_SID_Tokopedia_', 'DID', 'DID_JS']
        print("\n🔑 Important Cookies:")
        for cookie in cookie_data:
            if any(imp in cookie['name'] for imp in important_cookies):
                print(f"   ✅ {cookie['name']}: {cookie['value'][:20]}...")
        
        print("\n✅ DONE!")
        print("   Sekarang kamu bisa jalankan scraper dengan cookies yang fresh")
        print("   Run: python test_simple_browser.py")
        
        input("\nPress Enter to close browser...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
