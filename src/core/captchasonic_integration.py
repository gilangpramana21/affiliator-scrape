"""Integration with CaptchaSonic browser extension for automatic captcha solving."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import Page, BrowserContext

logger = logging.getLogger(__name__)


class CaptchaSonicIntegration:
    """Integration with CaptchaSonic browser extension."""
    
    def __init__(self, api_key: Optional[str] = None, extension_path: Optional[str] = None):
        self.api_key = api_key
        self.extension_path = extension_path or self._get_default_extension_path()
        self.extension_loaded = False
        
    def _get_default_extension_path(self) -> str:
        """Get default CaptchaSonic extension path."""
        # Default path where extension might be extracted
        return os.path.join(os.getcwd(), "captchasonic_extension")
    
    async def setup_extension(self, context: BrowserContext) -> bool:
        """Setup CaptchaSonic extension in browser context."""
        
        try:
            # Check if extension path exists
            if not os.path.exists(self.extension_path):
                logger.warning(f"CaptchaSonic extension not found at: {self.extension_path}")
                return False
            
            # Configure extension with API key
            if self.api_key:
                await self._configure_extension_api_key()
            
            logger.info("CaptchaSonic extension setup completed")
            self.extension_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup CaptchaSonic extension: {e}")
            return False
    
    async def _configure_extension_api_key(self):
        """Configure extension with API key."""
        
        config_path = os.path.join(self.extension_path, "config", "defaultConfig.json")
        
        try:
            # Read existing config
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update with API key
            config['apiKey'] = self.api_key
            config['enabled'] = True
            config['autoSolve'] = True
            
            # Ensure config directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Write updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("CaptchaSonic API key configured")
            
        except Exception as e:
            logger.error(f"Failed to configure CaptchaSonic API key: {e}")
    
    async def wait_for_captcha_solve(self, page: Page, timeout: int = 60) -> bool:
        """Wait for CaptchaSonic to solve captcha automatically."""
        
        if not self.extension_loaded:
            logger.warning("CaptchaSonic extension not loaded")
            return False
        
        logger.info("Waiting for CaptchaSonic to solve captcha...")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                # Check if time limit exceeded
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"CaptchaSonic timeout after {timeout}s")
                    return False
                
                # Check if captcha elements are gone
                captcha_selectors = [
                    'iframe[src*="recaptcha"]',
                    'iframe[src*="hcaptcha"]',
                    '.g-recaptcha',
                    '.h-captcha',
                    'img[src*="captcha"]'
                ]
                
                captcha_found = False
                for selector in captcha_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        captcha_found = True
                        break
                
                if not captcha_found:
                    logger.info("CaptchaSonic solved captcha successfully!")
                    return True
                
                # Check for success indicators
                if await self._check_page_loaded_successfully(page):
                    logger.info("Page loaded successfully - captcha likely solved")
                    return True
                
                # Show progress
                remaining = timeout - elapsed
                print(f"⏳ CaptchaSonic working... ({remaining:.0f}s remaining)", end="\r")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error while waiting for CaptchaSonic: {e}")
                await asyncio.sleep(2)
    
    async def _check_page_loaded_successfully(self, page: Page) -> bool:
        """Check if page loaded successfully (captcha solved)."""
        
        try:
            # Check for data content
            data_indicators = [
                "table tbody tr",
                ".creator-card",
                "[data-testid]",
                ".content"
            ]
            
            for indicator in data_indicators:
                elements = await page.query_selector_all(indicator)
                if len(elements) > 0:
                    return True
            
            # Check page title
            title = await page.title()
            if title and "error" not in title.lower() and "captcha" not in title.lower():
                return True
                
        except Exception:
            pass
        
        return False
    
    async def get_extension_status(self, page: Page) -> Dict[str, Any]:
        """Get CaptchaSonic extension status."""
        
        try:
            # Try to get extension status via JavaScript
            status = await page.evaluate("""
                () => {
                    // Check if CaptchaSonic is loaded
                    if (typeof window.captchaSonic !== 'undefined') {
                        return {
                            loaded: true,
                            version: window.captchaSonic.version || 'unknown',
                            enabled: window.captchaSonic.enabled || false,
                            apiKeyConfigured: !!window.captchaSonic.apiKey
                        };
                    }
                    return { loaded: false };
                }
            """)
            
            return status
            
        except Exception as e:
            logger.warning(f"Failed to get CaptchaSonic status: {e}")
            return {"loaded": False, "error": str(e)}


class CaptchaSonicHandler:
    """CAPTCHA handler that uses CaptchaSonic extension."""
    
    def __init__(self, api_key: Optional[str] = None, extension_path: Optional[str] = None):
        self.integration = CaptchaSonicIntegration(api_key, extension_path)
        self.solve_timeout = 60  # 1 minute timeout
    
    async def detect_and_solve(self, page: Page) -> bool:
        """Detect captcha and solve using CaptchaSonic."""
        
        # Check if captcha is present
        captcha_present = await self._detect_captcha(page)
        
        if not captcha_present:
            return True  # No captcha, success
        
        logger.info("CAPTCHA detected - using CaptchaSonic to solve")
        
        # Wait for CaptchaSonic to solve
        solved = await self.integration.wait_for_captcha_solve(page, self.solve_timeout)
        
        if solved:
            logger.info("CAPTCHA solved by CaptchaSonic")
            return True
        else:
            logger.error("CaptchaSonic failed to solve CAPTCHA")
            return False
    
    async def _detect_captcha(self, page: Page) -> bool:
        """Detect if captcha is present on page."""
        
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '.h-captcha',
            'img[src*="captcha"]',
            'input[name*="captcha"]'
        ]
        
        for selector in captcha_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    return True
            except:
                continue
        
        return False


# Helper function to download and setup CaptchaSonic extension
async def setup_captchasonic_extension():
    """Helper to setup CaptchaSonic extension."""
    
    print("🔧 CaptchaSonic Extension Setup Guide")
    print("=" * 50)
    
    print("📋 Steps to setup CaptchaSonic:")
    print("1. 🌐 Visit: https://my.captchasonic.com")
    print("2. 📝 Create account and get FREE TRIAL")
    print("3. 🔑 Copy your API key")
    print("4. 🔽 Download extension from Chrome Web Store:")
    print("   https://chromewebstore.google.com/detail/dkkdakdkffippajmebplgnpmijmnejlh")
    print("5. ⚙️  Configure API key in extension")
    
    print("\n🤖 For Automation Integration:")
    print("1. 📦 Extract extension ZIP file")
    print("2. 📝 Edit config/defaultConfig.json with your API key")
    print("3. 🔧 Load unpacked extension in Chrome")
    print("4. ✅ Extension will work with Playwright automatically")
    
    print("\n💡 Benefits:")
    print("   ✅ AI-powered solving (higher success rate)")
    print("   ✅ Supports all captcha types")
    print("   ✅ Works with Playwright/Puppeteer")
    print("   ✅ FREE TRIAL available")
    print("   ✅ No code changes needed in scraper")
    
    print("\n🎯 Integration with our scraper:")
    print("   1. Install and configure CaptchaSonic extension")
    print("   2. Extension runs automatically in browser")
    print("   3. Scraper continues normally - captchas solved automatically")
    print("   4. No manual intervention needed!")
    
    return True