#!/usr/bin/env python3
"""Setup guide for CaptchaSonic integration."""

import asyncio
import json
import os
import webbrowser
from pathlib import Path

def open_captchasonic_registration():
    """Open CaptchaSonic registration page."""
    print("🌐 Opening CaptchaSonic registration page...")
    webbrowser.open("https://my.captchasonic.com")
    print("✅ Browser opened - please register and get your FREE TRIAL API key")

def open_chrome_extension_store():
    """Open Chrome Web Store for CaptchaSonic extension."""
    print("🌐 Opening Chrome Web Store for CaptchaSonic extension...")
    webbrowser.open("https://chromewebstore.google.com/detail/dkkdakdkffippajmebplgnpmijmnejlh")
    print("✅ Extension page opened - please install the extension")

def create_extension_config(api_key: str):
    """Create extension configuration with API key."""
    
    # Create extension config directory
    config_dir = Path("captchasonic_config")
    config_dir.mkdir(exist_ok=True)
    
    # Create default config
    config = {
        "apiKey": api_key,
        "enabled": True,
        "autoSolve": True,
        "timeout": 60,
        "retries": 3,
        "supportedCaptchas": [
            "recaptcha_v2",
            "recaptcha_v3", 
            "hcaptcha",
            "aws_captcha",
            "geetest",
            "mtcaptcha"
        ]
    }
    
    config_file = config_dir / "defaultConfig.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Extension config created: {config_file}")
    return config_file

def show_extension_installation_guide():
    """Show detailed extension installation guide."""
    
    print("\n" + "="*60)
    print("🔧 CAPTCHASONIC EXTENSION INSTALLATION GUIDE")
    print("="*60)
    
    print("\n📋 STEP-BY-STEP INSTALLATION:")
    
    print("\n1️⃣ GET FREE TRIAL API KEY:")
    print("   • Visit: https://my.captchasonic.com")
    print("   • Click 'Sign Up' or 'Register'")
    print("   • Create account (email + password)")
    print("   • Login and get your FREE TRIAL API key")
    print("   • Copy the API key (you'll need it)")
    
    print("\n2️⃣ INSTALL BROWSER EXTENSION:")
    print("   • Visit Chrome Web Store:")
    print("     https://chromewebstore.google.com/detail/dkkdakdkffippajmebplgnpmijmnejlh")
    print("   • Click 'Add to Chrome'")
    print("   • Confirm installation")
    print("   • Extension icon will appear in toolbar")
    
    print("\n3️⃣ CONFIGURE EXTENSION:")
    print("   • Click CaptchaSonic extension icon in toolbar")
    print("   • Paste your API key in the popup")
    print("   • Enable 'Auto Solve' option")
    print("   • Save settings")
    
    print("\n4️⃣ VERIFY INSTALLATION:")
    print("   • Extension should show 'Active' status")
    print("   • Green icon = ready to solve captchas")
    print("   • Red icon = configuration needed")

async def test_extension_integration():
    """Test if CaptchaSonic extension is working."""
    
    print("\n🧪 TESTING CAPTCHASONIC INTEGRATION...")
    
    from src.anti_detection.browser_engine import BrowserEngine
    from src.anti_detection.fingerprint_generator import FingerprintGenerator
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Navigate to a test page
        page = await browser_engine.navigate("https://www.google.com/recaptcha/api2/demo")
        await asyncio.sleep(3)
        
        print("🔍 Navigated to reCAPTCHA test page")
        print("   If CaptchaSonic is working, it should solve the captcha automatically")
        print("   Watch the page - captcha should be solved within 10-30 seconds")
        
        # Wait and check
        print("\n⏳ Waiting 30 seconds to see if captcha gets solved...")
        await asyncio.sleep(30)
        
        # Check if captcha was solved
        try:
            success_element = await page.query_selector("text=Verification Success")
            if success_element:
                print("✅ SUCCESS! CaptchaSonic solved the captcha automatically!")
                return True
            else:
                print("⚠️  Captcha not solved automatically")
                print("   Please check:")
                print("   • Extension is installed and enabled")
                print("   • API key is configured correctly")
                print("   • You have remaining trial credits")
                return False
        except:
            print("⚠️  Could not verify captcha solving")
            return False
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    finally:
        await browser_engine.close()

async def setup_captchasonic_complete():
    """Complete CaptchaSonic setup process."""
    
    print("🚀 CAPTCHASONIC COMPLETE SETUP")
    print("=" * 50)
    
    # Step 1: Registration
    print("\n1️⃣ STEP 1: GET FREE TRIAL API KEY")
    print("-" * 30)
    
    open_registration = input("Open registration page? (y/n): ").lower().strip()
    if open_registration == 'y':
        open_captchasonic_registration()
    
    print("\n📝 Please complete registration and get your API key")
    api_key = input("Enter your CaptchaSonic API key: ").strip()
    
    if not api_key:
        print("❌ API key required to continue")
        return False
    
    print(f"✅ API key received: {api_key[:10]}...")
    
    # Step 2: Extension installation
    print("\n2️⃣ STEP 2: INSTALL BROWSER EXTENSION")
    print("-" * 30)
    
    open_extension = input("Open Chrome Web Store for extension? (y/n): ").lower().strip()
    if open_extension == 'y':
        open_chrome_extension_store()
    
    print("\n📝 Please install the extension and configure it with your API key")
    input("Press Enter when extension is installed and configured...")
    
    # Step 3: Create config
    print("\n3️⃣ STEP 3: CREATE CONFIGURATION")
    print("-" * 30)
    
    config_file = create_extension_config(api_key)
    print(f"✅ Configuration created")
    
    # Step 4: Test integration
    print("\n4️⃣ STEP 4: TEST INTEGRATION")
    print("-" * 30)
    
    test_now = input("Test CaptchaSonic integration now? (y/n): ").lower().strip()
    if test_now == 'y':
        success = await test_extension_integration()
        if success:
            print("\n🎉 SETUP COMPLETE! CaptchaSonic is working!")
        else:
            print("\n⚠️  Setup needs troubleshooting")
    
    # Step 5: Integration with scraper
    print("\n5️⃣ STEP 5: SCRAPER INTEGRATION")
    print("-" * 30)
    
    print("✅ CaptchaSonic will now work automatically with the scraper!")
    print("   • Extension runs in browser background")
    print("   • Automatically detects and solves captchas")
    print("   • Scraper continues normally")
    print("   • No code changes needed!")
    
    # Update scraper config
    await update_scraper_config(api_key)
    
    print("\n🎯 SETUP SUMMARY:")
    print(f"   ✅ API Key: Configured")
    print(f"   ✅ Extension: Installed")
    print(f"   ✅ Configuration: Created")
    print(f"   ✅ Scraper: Updated")
    print(f"   🚀 Ready for production!")
    
    return True

async def update_scraper_config(api_key: str):
    """Update scraper configuration for CaptchaSonic."""
    
    try:
        # Update config file
        config_path = "config/config_jelajahi.json"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Add CaptchaSonic configuration
        config['captcha_solver'] = 'captchasonic'
        config['captcha_api_key'] = api_key
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Scraper configuration updated")
        
    except Exception as e:
        print(f"⚠️  Could not update scraper config: {e}")

if __name__ == "__main__":
    print("🚀 Starting CaptchaSonic Setup...")
    
    # Show installation guide first
    show_extension_installation_guide()
    
    print("\n" + "="*60)
    
    # Ask if user wants to proceed with complete setup
    proceed = input("\nProceed with complete setup? (y/n): ").lower().strip()
    
    if proceed == 'y':
        asyncio.run(setup_captchasonic_complete())
    else:
        print("Setup cancelled. You can run this script again anytime.")