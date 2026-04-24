"""Enhanced CAPTCHA handler with better manual mode and free alternatives."""

import asyncio
import logging
from typing import Optional
from playwright.async_api import Page

from src.core.captcha_handler import CAPTCHAHandler, CAPTCHAType

logger = logging.getLogger(__name__)


class EnhancedCAPTCHAHandler(CAPTCHAHandler):
    """Enhanced CAPTCHA handler with better manual experience and free alternatives."""
    
    def __init__(self, solver_type: str = "manual", api_key: Optional[str] = None, 
                 auto_retry: bool = True, max_wait_time: int = 300):
        super().__init__(solver_type, api_key)
        self.auto_retry = auto_retry
        self.max_wait_time = max_wait_time  # 5 minutes max wait
        
    async def _solve_manual(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Enhanced manual solving with better UX and auto-detection."""
        
        print(f"\n" + "="*60)
        print(f"🚨 CAPTCHA DETECTED: {captcha_type.value.upper()}")
        print(f"📍 URL: {page.url}")
        print("="*60)
        
        # Provide specific instructions based on captcha type
        await self._show_captcha_instructions(captcha_type)
        
        # Auto-monitor for captcha completion
        return await self._auto_monitor_captcha_completion(page, captcha_type)
    
    async def _show_captcha_instructions(self, captcha_type: CAPTCHAType):
        """Show detailed instructions for each captcha type."""
        
        if captcha_type == CAPTCHAType.RECAPTCHA_V2:
            print("🤖 reCAPTCHA v2 Instructions:")
            print("   1. ✅ Look for 'I'm not a robot' checkbox")
            print("   2. 🖱️  Click the checkbox")
            print("   3. 🖼️  If images appear, select the correct ones")
            print("   4. ✅ Wait for green checkmark")
            
        elif captcha_type == CAPTCHAType.RECAPTCHA_V3:
            print("🤖 reCAPTCHA v3 Instructions:")
            print("   1. ⏳ This runs automatically in background")
            print("   2. 🔄 Just wait 5-10 seconds")
            print("   3. ✅ Page should load by itself")
            
        elif captcha_type == CAPTCHAType.HCAPTCHA:
            print("🤖 hCaptcha Instructions:")
            print("   1. 🖼️  Look for image selection challenge")
            print("   2. 🖱️  Click on correct images (e.g., 'Select all cars')")
            print("   3. ✅ Click 'Verify' button when done")
            
        elif captcha_type == CAPTCHAType.IMAGE:
            print("🤖 Image CAPTCHA Instructions:")
            print("   1. 🔤 Look for distorted text/numbers")
            print("   2. ⌨️  Type what you see in the input field")
            print("   3. ✅ Click submit/continue button")
        
        print(f"\n⏳ Auto-monitoring enabled - I'll detect when it's solved!")
        print(f"   Maximum wait time: {self.max_wait_time} seconds")
        print(f"   You can also press Ctrl+C to skip this page")
    
    async def _auto_monitor_captcha_completion(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Auto-monitor for captcha completion without user input."""
        
        start_time = asyncio.get_event_loop().time()
        check_interval = 2  # Check every 2 seconds
        
        print(f"🔍 Monitoring captcha completion...")
        
        while True:
            try:
                # Check if time limit exceeded
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.max_wait_time:
                    print(f"⏰ Time limit exceeded ({self.max_wait_time}s)")
                    return False
                
                # Check if captcha is still present
                current_captcha = await self.detect(page)
                
                if not current_captcha:
                    print("✅ CAPTCHA SOLVED! Continuing...")
                    return True
                
                # Check if page URL changed (might indicate success)
                current_url = page.url
                if "captcha" not in current_url.lower() and "challenge" not in current_url.lower():
                    # Additional verification - check for success indicators
                    if await self._check_success_indicators(page):
                        print("✅ CAPTCHA SOLVED! Page loaded successfully")
                        return True
                
                # Show progress
                remaining = self.max_wait_time - elapsed
                print(f"⏳ Still waiting... ({remaining:.0f}s remaining)", end="\r")
                
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                print(f"\n⏭️  User requested skip (Ctrl+C)")
                return False
            except Exception as e:
                logger.warning(f"Error during captcha monitoring: {e}")
                await asyncio.sleep(check_interval)
    
    async def _check_success_indicators(self, page: Page) -> bool:
        """Check for indicators that the page loaded successfully."""
        
        try:
            # Check for common success indicators
            success_indicators = [
                "table",  # Data tables
                "tbody tr",  # Table rows with data
                ".creator-card",  # Creator cards
                "[data-testid]",  # Test IDs indicating loaded content
                ".content",  # Main content areas
            ]
            
            for indicator in success_indicators:
                elements = await page.query_selector_all(indicator)
                if len(elements) > 0:
                    return True
            
            # Check if page title indicates success
            title = await page.title()
            if title and "error" not in title.lower() and "captcha" not in title.lower():
                return True
                
        except Exception:
            pass
        
        return False


class SmartCAPTCHAHandler(EnhancedCAPTCHAHandler):
    """Smart CAPTCHA handler with advanced free techniques."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_reuse_enabled = True
        self.smart_delay_enabled = True
    
    async def solve(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Smart solving with multiple free techniques."""
        
        # Technique 1: Try session reuse first
        if self.session_reuse_enabled:
            if await self._try_session_reuse(page):
                print("✅ CAPTCHA bypassed using session reuse!")
                return True
        
        # Technique 2: Try smart delays and retries
        if self.smart_delay_enabled:
            if await self._try_smart_delay_bypass(page, captcha_type):
                print("✅ CAPTCHA bypassed using smart delay!")
                return True
        
        # Technique 3: Fall back to enhanced manual mode
        return await super().solve(page, captcha_type)
    
    async def _try_session_reuse(self, page: Page) -> bool:
        """Try to reuse existing session to bypass captcha."""
        
        try:
            print("🔄 Trying session reuse technique...")
            
            # Go back and forward to refresh session
            await page.go_back()
            await asyncio.sleep(2)
            await page.go_forward()
            await asyncio.sleep(3)
            
            # Check if captcha is gone
            captcha_type = await self.detect(page)
            return captcha_type is None
            
        except Exception as e:
            logger.debug(f"Session reuse failed: {e}")
            return False
    
    async def _try_smart_delay_bypass(self, page: Page, captcha_type: CAPTCHAType) -> bool:
        """Try smart delays to bypass captcha."""
        
        try:
            print("⏳ Trying smart delay technique...")
            
            if captcha_type == CAPTCHAType.RECAPTCHA_V3:
                # reCAPTCHA v3 often resolves itself with patience
                print("   Waiting for reCAPTCHA v3 to resolve...")
                await asyncio.sleep(10)
                
                captcha_type = await self.detect(page)
                return captcha_type is None
            
            # For other types, try page refresh after delay
            await asyncio.sleep(5)
            await page.reload()
            await asyncio.sleep(3)
            
            captcha_type = await self.detect(page)
            return captcha_type is None
            
        except Exception as e:
            logger.debug(f"Smart delay failed: {e}")
            return False