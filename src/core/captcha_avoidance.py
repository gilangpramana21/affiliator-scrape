"""Free techniques to avoid captchas altogether."""

import asyncio
import random
import logging
from typing import List, Dict, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class CAPTCHAAvoidance:
    """Free techniques to minimize captcha encounters."""
    
    def __init__(self):
        self.session_rotation_enabled = True
        self.smart_timing_enabled = True
        self.behavior_randomization_enabled = True
        
    async def apply_avoidance_techniques(self, page: Page) -> bool:
        """Apply all avoidance techniques before making requests."""
        
        try:
            # Technique 1: Randomize behavior patterns
            if self.behavior_randomization_enabled:
                await self._randomize_behavior(page)
            
            # Technique 2: Smart timing delays
            if self.smart_timing_enabled:
                await self._apply_smart_timing()
            
            # Technique 3: Rotate user agents and headers
            await self._rotate_session_data(page)
            
            return True
            
        except Exception as e:
            logger.warning(f"Avoidance techniques failed: {e}")
            return False
    
    async def _randomize_behavior(self, page: Page):
        """Randomize human-like behavior patterns."""
        
        # Random mouse movements
        viewport = page.viewport_size
        if viewport:
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Random scrolling
        scroll_distance = random.randint(100, 500)
        await page.mouse.wheel(0, scroll_distance)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Random clicks on non-interactive elements
        try:
            body = await page.query_selector("body")
            if body:
                box = await body.bounding_box()
                if box:
                    x = random.uniform(box['x'], box['x'] + box['width'])
                    y = random.uniform(box['y'], box['y'] + box['height'])
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(0.2, 0.8))
        except:
            pass
    
    async def _apply_smart_timing(self):
        """Apply smart timing delays to appear human."""
        
        # Random delay between 2-8 seconds
        delay = random.uniform(2.0, 8.0)
        
        # Add extra delay during peak hours (more likely to trigger captcha)
        import datetime
        current_hour = datetime.datetime.now().hour
        
        if 9 <= current_hour <= 17:  # Business hours
            delay += random.uniform(1.0, 3.0)
        
        logger.debug(f"Applying smart timing delay: {delay:.1f}s")
        await asyncio.sleep(delay)
    
    async def _rotate_session_data(self, page: Page):
        """Rotate session data to avoid detection."""
        
        # This would be implemented with the browser engine
        # For now, just add some randomization
        
        # Random viewport size changes
        viewports = [
            {'width': 1366, 'height': 768},
            {'width': 1920, 'height': 1080},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
        ]
        
        viewport = random.choice(viewports)
        await page.set_viewport_size(viewport['width'], viewport['height'])


class SessionManager:
    """Manage multiple sessions to avoid captchas."""
    
    def __init__(self):
        self.sessions: List[Dict[str, Any]] = []
        self.current_session_index = 0
        self.max_requests_per_session = 10
        self.current_requests = 0
    
    def should_rotate_session(self) -> bool:
        """Check if we should rotate to a new session."""
        return self.current_requests >= self.max_requests_per_session
    
    async def rotate_session_if_needed(self, page: Page) -> bool:
        """Rotate session if needed."""
        
        if self.should_rotate_session():
            logger.info("Rotating session to avoid captcha")
            
            # Clear cookies and storage
            await page.context.clear_cookies()
            await page.evaluate("localStorage.clear()")
            await page.evaluate("sessionStorage.clear()")
            
            # Reset counter
            self.current_requests = 0
            
            # Add delay before continuing
            await asyncio.sleep(random.uniform(5.0, 15.0))
            
            return True
        
        self.current_requests += 1
        return False


class CAPTCHAPredictor:
    """Predict when captchas are likely to appear."""
    
    def __init__(self):
        self.request_count = 0
        self.captcha_history = []
        self.high_risk_patterns = [
            "too many requests",
            "rate limit",
            "suspicious activity",
            "verify you're human"
        ]
    
    def predict_captcha_risk(self, page_content: str, request_count: int) -> float:
        """Predict captcha risk (0.0 to 1.0)."""
        
        risk = 0.0
        
        # Risk increases with request count
        if request_count > 20:
            risk += 0.3
        elif request_count > 10:
            risk += 0.1
        
        # Check for warning patterns in page content
        content_lower = page_content.lower()
        for pattern in self.high_risk_patterns:
            if pattern in content_lower:
                risk += 0.4
                break
        
        # Time-based risk (peak hours)
        import datetime
        current_hour = datetime.datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            risk += 0.1
        
        return min(risk, 1.0)
    
    async def should_take_break(self, page: Page) -> bool:
        """Determine if we should take a break to avoid captcha."""
        
        try:
            content = await page.content()
            risk = self.predict_captcha_risk(content, self.request_count)
            
            if risk > 0.7:
                logger.info(f"High captcha risk ({risk:.1f}) - taking preventive break")
                return True
                
        except Exception as e:
            logger.warning(f"Risk prediction failed: {e}")
        
        return False
    
    async def take_preventive_break(self):
        """Take a break to reduce captcha risk."""
        
        break_time = random.uniform(30, 120)  # 30s to 2min break
        logger.info(f"Taking preventive break: {break_time:.0f}s")
        await asyncio.sleep(break_time)