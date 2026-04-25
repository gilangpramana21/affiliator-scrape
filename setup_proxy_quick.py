#!/usr/bin/env python3
"""
Quick Proxy Setup Script
Helps user setup proxy quickly
"""

import os
import sys


def main():
    print("🚀 QUICK PROXY SETUP")
    print("=" * 60)
    print("This script will help you setup proxy for the scraper")
    print("=" * 60)
    
    print("\n📋 PROXY OPTIONS:")
    print("1. Webshare.io (Recommended - 10 free proxies)")
    print("2. Smartproxy (3-day trial)")
    print("3. Free proxies (Less reliable)")
    print("4. Skip proxy setup (manual CAPTCHA)")
    
    choice = input("\nChoose option (1-4): ").strip()
    
    if choice == "1":
        setup_webshare()
    elif choice == "2":
        setup_smartproxy()
    elif choice == "3":
        setup_free_proxies()
    elif choice == "4":
        print("\n✅ Skipping proxy setup")
        print("   You can run scraper without proxy (manual CAPTCHA solving)")
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🎯 NEXT STEPS:")
    print("1. Test proxy setup:")
    print("   python3 src/proxy/proxy_manager.py")
    print("\n2. Run scraper with proxy:")
    print("   python3 production_scraper_with_proxy.py --max-affiliators 20")
    print("\n3. Run scraper without proxy:")
    print("   python3 production_scraper_with_proxy.py --no-proxy --max-affiliators 20")


def setup_webshare():
    print("\n🌐 WEBSHARE.IO SETUP")
    print("=" * 40)
    print("1. Go to: https://www.webshare.io/")
    print("2. Click 'Sign Up' (free account)")
    print("3. Verify your email")
    print("4. Login to dashboard: https://proxy.webshare.io/")
    print("5. Go to 'Proxy' → 'Proxy List'")
    print("6. You'll see 10 free proxies")
    print("7. Download or copy the proxy list")
    
    print("\n📝 PROXY FORMAT:")
    print("Each line should be: IP:PORT:USERNAME:PASSWORD")
    print("Example:")
    print("154.16.146.43:80:username123:password456")
    print("45.95.96.132:8080:username123:password456")
    
    print(f"\n📁 SAVE TO FILE:")
    print(f"Save your proxies to: config/webshare_proxies.txt")
    
    # Ask if user wants to input proxies now
    response = input("\nDo you have the proxies ready to input now? (y/n): ")
    if response.lower() == 'y':
        input_webshare_proxies()
    else:
        print("\n⏸️  Setup paused. Please get your proxies and run this script again.")


def input_webshare_proxies():
    print("\n📝 INPUT PROXIES:")
    print("Paste your proxies (one per line, format: IP:PORT:USERNAME:PASSWORD)")
    print("Press Enter twice when done:")
    
    proxies = []
    while True:
        line = input().strip()
        if not line:
            break
        proxies.append(line)
    
    if proxies:
        # Save to file
        os.makedirs("config", exist_ok=True)
        with open("config/webshare_proxies.txt", "w") as f:
            f.write("# Webshare.io Proxy List\n")
            f.write("# Format: IP:PORT:USERNAME:PASSWORD\n\n")
            for proxy in proxies:
                f.write(proxy + "\n")
        
        print(f"\n✅ Saved {len(proxies)} proxies to config/webshare_proxies.txt")
    else:
        print("\n⚠️  No proxies entered")


def setup_smartproxy():
    print("\n🌐 SMARTPROXY SETUP")
    print("=" * 40)
    print("1. Go to: https://smartproxy.com/")
    print("2. Click 'Start Free Trial'")
    print("3. Register (3-day trial, 100MB free)")
    print("4. Choose: Residential Proxies")
    print("5. Select country: Indonesia")
    print("6. Get endpoint and credentials from dashboard")
    
    print("\n📝 SMARTPROXY FORMAT:")
    print("Usually one endpoint with rotating IPs:")
    print("Host: gate.smartproxy.com")
    print("Port: 10000")
    print("Username: your_username")
    print("Password: your_password")
    
    print("\n⚠️  Note: Smartproxy uses rotating residential IPs")
    print("You'll get different IP for each request through same endpoint")


def setup_free_proxies():
    print("\n🆓 FREE PROXY SETUP")
    print("=" * 40)
    print("⚠️  WARNING: Free proxies are often unreliable!")
    print("   - Many don't work")
    print("   - Slow speed")
    print("   - No authentication")
    print("   - May be blocked by websites")
    
    print("\n📋 FREE PROXY SOURCES:")
    print("1. ProxyScrape: https://proxyscrape.com/free-proxy-list")
    print("2. FreeProxyList: https://free-proxy-list.net/")
    print("3. ProxyList: https://www.proxy-list.download/")
    
    print("\n📝 SETUP STEPS:")
    print("1. Visit one of the sites above")
    print("2. Filter by:")
    print("   - Country: Indonesia (if available)")
    print("   - Protocol: HTTP/HTTPS")
    print("   - Anonymity: High/Elite")
    print("3. Download proxy list")
    print("4. Save to: config/free_proxies.txt")
    print("5. Format: IP:PORT (one per line)")
    
    print("\n💡 RECOMMENDATION:")
    print("Use Webshare.io instead - much more reliable!")


if __name__ == "__main__":
    main()