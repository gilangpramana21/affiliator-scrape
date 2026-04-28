#!/usr/bin/env python3
"""
Test dengan Undetected ChromeDriver - bypass Tokopedia detection
"""

import time
import json

try:
    import undetected_chromedriver as uc
except ImportError:
    print("❌ undetected-chromedriver not installed!")
    print("\nInstall dengan:")
    print("   pip install undetected-chromedriver")
    exit(1)


def main():
    print("🥷 UNDETECTED CHROMEDRIVER TEST")
    print("=" * 60)
    print("This uses undetected-chromedriver to bypass detection")
    print("=" * 60)
    
    # Setup Chrome options
    options = uc.ChromeOptions()
    # options.add_argument('--headless')  # Uncomment untuk headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    print("\n🌐 Launching Chrome...")
    
    # Create driver - let it auto-detect Chrome version
    try:
        driver = uc.Chrome(options=options, version_main=147)
    except Exception as e:
        print(f"⚠️  Error with version 147, trying auto-detect...")
        driver = uc.Chrome(options=options, use_subprocess=True)
    
    print("✅ Chrome launched")
    
    try:
        # Load cookies if available
        print("\n🍪 Loading cookies...")
        try:
            with open('config/cookies.json', 'r') as f:
                cookies = json.load(f)
            
            # Navigate to domain first
            driver.get("https://www.tokopedia.com")
            time.sleep(2)
            
            # Add cookies
            for cookie in cookies:
                try:
                    # Convert to Selenium format
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.tokopedia.com'),
                        'path': cookie.get('path', '/'),
                    }
                    if 'httpOnly' in cookie:
                        cookie_dict['httpOnly'] = cookie['httpOnly']
                    if 'secure' in cookie:
                        cookie_dict['secure'] = cookie['secure']
                    
                    driver.add_cookie(cookie_dict)
                except Exception as e:
                    print(f"   ⚠️  Cookie error: {e}")
            
            print(f"✅ Loaded {len(cookies)} cookies")
        except FileNotFoundError:
            print("⚠️  No cookies found, will need to login")
        
        # Navigate to Affiliate Center
        print("\n🌐 Navigating to Affiliate Center...")
        affiliate_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        
        driver.get(affiliate_url)
        print("✅ Page loaded")
        
        # Wait for page to load
        time.sleep(5)
        
        # Check current URL
        current_url = driver.current_url
        print(f"\n📍 Current URL: {current_url}")
        
        # Check page content
        page_source = driver.page_source
        
        if "coba lagi" in page_source.lower():
            print("\n⚠️  'Coba lagi' detected!")
            print("   Even undetected-chromedriver got blocked")
            print("   Try refreshing manually or wait longer")
        elif "login" in current_url.lower():
            print("\n⚠️  Need to login")
            print("   Please login manually in the browser")
            input("\nPress Enter after login...")
            
            # Save cookies after login
            cookies = driver.get_cookies()
            with open('config/cookies.json', 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"✅ Saved {len(cookies)} cookies")
            
            # Navigate again
            driver.get(affiliate_url)
            time.sleep(5)
        else:
            print("✅ Page loaded successfully!")
        
        # Check for creator table
        print("\n🔍 Checking for creator list...")
        try:
            rows = driver.find_elements("css selector", "tbody tr")
            print(f"📊 Found {len(rows)} creator rows")
            
            if len(rows) > 0:
                print("\n✅ SUCCESS! Creator list loaded")
                print(f"   Found {len(rows)} creators")
                
                # Try clicking first creator
                print("\n🖱️  Trying to click first creator...")
                first_row = rows[0]
                
                # Get current window handles
                original_window = driver.current_window_handle
                original_windows = driver.window_handles
                
                # Click row
                first_row.click()
                time.sleep(3)
                
                # Check for new window
                new_windows = driver.window_handles
                if len(new_windows) > len(original_windows):
                    print("✅ New window opened!")
                    
                    # Switch to new window
                    for window in new_windows:
                        if window != original_window:
                            driver.switch_to.window(window)
                            break
                    
                    print(f"📍 Detail page URL: {driver.current_url}")
                    
                    # Wait for page to load
                    time.sleep(10)
                    
                    print("\n⏸️  Detail page opened!")
                    print("   Check browser:")
                    print("   1. Can you see creator profile?")
                    print("   2. Can you see WhatsApp/Email icons?")
                    print("   3. Try clicking them manually")
                    
                else:
                    print("⚠️  No new window opened")
                    print("   Row click might not work")
            else:
                print("\n⚠️  No creators found")
                print("   Page might still be loading or blocked")
        
        except Exception as e:
            print(f"❌ Error checking creators: {e}")
        
        print("\n⏸️  Browser will stay open")
        print("   Press Ctrl+C to close")
        
        # Keep browser open
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n\n🛑 Closing browser...")
    
    finally:
        driver.quit()
        print("✅ Done!")


if __name__ == "__main__":
    main()
