#!/usr/bin/env python3
"""
Bright Data Setup Helper
Membantu setup credentials dengan mudah
"""

import json
import os


def setup_brightdata():
    print("🔧 BRIGHT DATA SETUP HELPER")
    print("=" * 60)
    print()
    
    print("Silakan masukkan credentials dari Bright Data:")
    print("(Lihat di: My Proxies → Click zone → Access Parameters)")
    print()
    
    # Get credentials from user
    host = input("Host (default: brd.superproxy.io): ").strip() or "brd.superproxy.io"
    port = input("Port (default: 22225): ").strip() or "22225"
    
    print()
    print("Username format: brd-customer-hl_xxxxx-zone-xxxxx")
    base_username = input("Username (tanpa -country-id): ").strip()
    
    print()
    password = input("Password: ").strip()
    
    # Create optimized username for Indonesia
    username = f"{base_username}-country-id"
    
    print()
    print("=" * 60)
    print("✅ CREDENTIALS RECEIVED")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print()
    
    # Update config files
    config_files = [
        "config/config_production.json",
        "config/config_jelajahi.json"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                config['proxy_enabled'] = True
                config['proxy_server'] = f"http://{host}:{port}"
                config['proxy_username'] = username
                config['proxy_password'] = password
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ Updated: {config_file}")
            except Exception as e:
                print(f"⚠️ Error updating {config_file}: {e}")
    
    # Update test_proxy.py
    try:
        test_proxy_content = f'''#!/usr/bin/env python3
"""
Test Bright Data Proxy Connection
"""

import asyncio
from playwright.async_api import async_playwright


async def test_proxy():
    print("🧪 Testing Bright Data Proxy Connection")
    print("=" * 60)
    
    PROXY_SERVER = "http://{host}:{port}"
    PROXY_USERNAME = "{username}"
    PROXY_PASSWORD = "{password}"
    
    print(f"Proxy: {{PROXY_SERVER}}")
    print(f"Username: {{PROXY_USERNAME[:30]}}...")
    print()
    
    try:
        async with async_playwright() as p:
            # Launch browser with proxy
            browser = await p.chromium.launch(
                headless=False,
                proxy={{
                    "server": PROXY_SERVER,
                    "username": PROXY_USERNAME,
                    "password": PROXY_PASSWORD
                }}
            )
            
            print("✅ Browser launched with proxy")
            
            # Create page
            page = await browser.new_page()
            
            # Test 1: Check IP and location
            print("\\n📍 Test 1: Checking IP and location...")
            await page.goto("https://geo.brdtest.com/mygeo.json")
            await asyncio.sleep(2)
            
            content = await page.content()
            print(f"   Response: {{content[:300]}}...")
            
            # Test 2: Access Tokopedia
            print("\\n🏪 Test 2: Accessing Tokopedia...")
            await page.goto("https://www.tokopedia.com/")
            await asyncio.sleep(3)
            
            title = await page.title()
            print(f"   Page title: {{title}}")
            
            if "Tokopedia" in title:
                print("   ✅ Successfully accessed Tokopedia!")
            else:
                print("   ⚠️ Unexpected page title")
            
            await browser.close()
            
            print("\\n" + "=" * 60)
            print("✅ PROXY TEST SUCCESSFUL!")
            print("=" * 60)
            print("\\nProxy is working correctly with Indonesia IP!")
            print("\\nNext steps:")
            print("1. Run: python3 quick_test.py")
            print("2. If successful, run: python3 production_scraper_v2.py")
            
    except Exception as e:
        print(f"\\n❌ PROXY TEST FAILED!")
        print(f"Error: {{e}}")
        print("\\nTroubleshooting:")
        print("1. Check username and password are correct")
        print("2. Check you have credits in Bright Data account")
        print("3. Check proxy zone is active")
        print("4. Try running setup_brightdata.py again")


if __name__ == "__main__":
    asyncio.run(test_proxy())
'''
        
        with open('test_proxy.py', 'w') as f:
            f.write(test_proxy_content)
        
        print(f"✅ Updated: test_proxy.py")
    except Exception as e:
        print(f"⚠️ Error updating test_proxy.py: {e}")
    
    print()
    print("=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Test proxy: python3 test_proxy.py")
    print("2. If successful: python3 quick_test.py")
    print("3. If test OK: python3 production_scraper_v2.py")
    print()
    print("Your proxy is configured to use Indonesia IPs only!")
    print("This will minimize CAPTCHA and look natural to Tokopedia.")
    print()


if __name__ == "__main__":
    setup_brightdata()
