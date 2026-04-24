#!/usr/bin/env python3
"""Test captcha handling capabilities."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captcha_handler import CAPTCHAHandler
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_captcha_handling():
    """Test captcha detection and handling."""
    
    print("🤖 Testing CAPTCHA Handling Capabilities")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    print(f"✅ Config loaded")
    print(f"   Captcha solver: {config.captcha_solver}")
    print(f"   API key configured: {'Yes' if config.captcha_api_key and config.captcha_api_key != 'YOUR_2CAPTCHA_API_KEY_HERE' else 'No'}")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    # Initialize captcha handler
    captcha_handler = CAPTCHAHandler(
        solver_type=config.captcha_solver,
        api_key=config.captcha_api_key if config.captcha_api_key != "YOUR_2CAPTCHA_API_KEY_HERE" else None
    )
    
    print(f"✅ CAPTCHA handler initialized")
    print(f"   Solver type: {captcha_handler.solver_type}")
    print(f"   Current backoff: {captcha_handler.backoff_seconds}s")
    print(f"   Encounter count: {captcha_handler.captcha_encounter_count}")
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
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
        
        # Test captcha detection
        print("\n🔍 TESTING CAPTCHA DETECTION...")
        
        captcha_type = await captcha_handler.detect(page)
        
        if captcha_type:
            print(f"🚨 CAPTCHA DETECTED: {captcha_type.value}")
            print(f"   Page URL: {page.url}")
            
            # Test captcha solving
            print(f"\n🤖 ATTEMPTING TO SOLVE CAPTCHA...")
            print(f"   Solver: {captcha_handler.solver_type}")
            
            if captcha_handler.solver_type == "manual":
                print("   ⚠️  Manual mode - waiting for user intervention")
                print("   Please solve the captcha manually in the browser")
                print("   Press Enter when captcha is solved...")
                input()
                solved = True
            else:
                print("   🔄 Attempting automatic solve...")
                solved = await captcha_handler.solve(page, captcha_type)
            
            if solved:
                print("   ✅ CAPTCHA SOLVED SUCCESSFULLY!")
                print(f"   New backoff time: {captcha_handler.backoff_seconds}s")
                print(f"   Total encounters: {captcha_handler.captcha_encounter_count}")
                
                # Wait for backoff
                if captcha_handler.backoff_seconds > 5:
                    print(f"   ⏳ Applying backoff: {captcha_handler.backoff_seconds}s")
                    await captcha_handler.wait_backoff()
                
            else:
                print("   ❌ CAPTCHA SOLVE FAILED")
                print(f"   New backoff time: {captcha_handler.backoff_seconds}s")
                print(f"   Total encounters: {captcha_handler.captcha_encounter_count}")
                
        else:
            print("✅ NO CAPTCHA DETECTED")
            print("   Page is accessible without captcha challenge")
        
        # Test different pages that might have captcha
        test_urls = [
            f"{config.base_url}/connection/creator",
            f"{config.base_url}/connection/creator?page=2",
            f"{config.base_url}/dashboard"
        ]
        
        print(f"\n🔍 TESTING CAPTCHA ON DIFFERENT PAGES...")
        
        for i, test_url in enumerate(test_urls, 1):
            try:
                print(f"\n   📄 Test {i}: {test_url}")
                await page.goto(test_url)
                await asyncio.sleep(2)
                
                captcha_type = await captcha_handler.detect(page)
                if captcha_type:
                    print(f"      🚨 CAPTCHA found: {captcha_type.value}")
                else:
                    print(f"      ✅ No captcha")
                    
            except Exception as e:
                print(f"      ⚠️  Error: {e}")
        
        # Summary
        print(f"\n📊 CAPTCHA HANDLING SUMMARY:")
        print(f"   Solver configured: {captcha_handler.solver_type}")
        print(f"   API key available: {'Yes' if captcha_handler.api_key else 'No'}")
        print(f"   Total encounters: {captcha_handler.captcha_encounter_count}")
        print(f"   Current backoff: {captcha_handler.backoff_seconds}s")
        
        if captcha_handler.solver_type == "manual":
            print(f"\n⚠️  RECOMMENDATION:")
            print(f"   - Setup 2Captcha or Anti-Captcha API key for automatic solving")
            print(f"   - Update config: captcha_solver = '2captcha'")
            print(f"   - Add your API key to config: captcha_api_key = 'your_key'")
        
        print("\n⏳ Browser window open for manual testing...")
        print("   Try navigating to different pages to trigger captcha")
        print("   Press Enter when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during captcha test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(test_captcha_handling())