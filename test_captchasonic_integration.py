#!/usr/bin/env python3
"""Test CaptchaSonic integration with our scraper."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captchasonic_integration import CaptchaSonicHandler, setup_captchasonic_extension
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_captchasonic_integration():
    """Test CaptchaSonic integration."""
    
    print("🚀 Testing CaptchaSonic Integration")
    print("=" * 50)
    
    # Show setup guide first
    await setup_captchasonic_extension()
    
    print("\n" + "="*50)
    print("🧪 TESTING INTEGRATION")
    print("="*50)
    
    # Check if user has setup CaptchaSonic
    api_key = input("\n🔑 Enter your CaptchaSonic API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⏭️  Skipping integration test - no API key provided")
        print("   You can still test manually by installing the extension")
        return
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    # Initialize CaptchaSonic handler
    captcha_handler = CaptchaSonicHandler(api_key=api_key)
    
    print(f"✅ CaptchaSonic handler initialized with API key")
    
    try:
        # Launch browser with extension support
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode for extension)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to target page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        # Test CaptchaSonic integration
        print("\n🤖 Testing CaptchaSonic CAPTCHA detection and solving...")
        
        # Check extension status
        status = await captcha_handler.integration.get_extension_status(page)
        print(f"📊 CaptchaSonic Status: {status}")
        
        if not status.get('loaded'):
            print("⚠️  CaptchaSonic extension not detected in browser")
            print("   Make sure you have installed and enabled the extension")
            print("   Extension should be loaded automatically with the browser")
        
        # Test captcha detection and solving
        solved = await captcha_handler.detect_and_solve(page)
        
        if solved:
            print("✅ Page accessible - no captcha or captcha solved by CaptchaSonic!")
        else:
            print("❌ CAPTCHA present and not solved")
        
        # Test on multiple pages
        print(f"\n🔄 Testing CaptchaSonic on multiple pages...")
        
        test_urls = [
            f"{config.base_url}/connection/creator?page=1",
            f"{config.base_url}/connection/creator?page=2",
            f"{config.base_url}/dashboard"
        ]
        
        for i, test_url in enumerate(test_urls, 1):
            print(f"\n   📄 Test {i}: {test_url}")
            
            try:
                await page.goto(test_url)
                await asyncio.sleep(2)
                
                # Test CaptchaSonic on this page
                solved = await captcha_handler.detect_and_solve(page)
                
                if solved:
                    print(f"      ✅ Page accessible")
                else:
                    print(f"      ❌ CAPTCHA blocking access")
                    
            except Exception as e:
                print(f"      ⚠️  Error: {e}")
        
        # Summary
        print(f"\n📊 CAPTCHASONIC INTEGRATION SUMMARY:")
        print(f"   🔑 API Key: {'Configured' if api_key else 'Not configured'}")
        print(f"   🔌 Extension: {'Loaded' if status.get('loaded') else 'Not detected'}")
        print(f"   🤖 Auto-solving: {'Enabled' if status.get('enabled') else 'Disabled'}")
        print(f"   💰 Cost: FREE TRIAL + paid plans")
        
        print(f"\n🎯 BENEFITS:")
        print(f"   ✅ 99%+ success rate (AI-powered)")
        print(f"   ✅ Fully automatic (no manual intervention)")
        print(f"   ✅ Works with all captcha types")
        print(f"   ✅ Seamless integration with scraper")
        print(f"   ✅ FREE TRIAL available")
        
        print(f"\n⚠️  REQUIREMENTS:")
        print(f"   🔑 CaptchaSonic API key (get from my.captchasonic.com)")
        print(f"   🔌 Browser extension installed and configured")
        print(f"   💰 Paid service after free trial")
        
        print("\n⏳ Browser window open for manual testing...")
        print("   Try navigating to pages that might have captcha")
        print("   CaptchaSonic should solve them automatically")
        print("   Press Enter when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during CaptchaSonic test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(test_captchasonic_integration())