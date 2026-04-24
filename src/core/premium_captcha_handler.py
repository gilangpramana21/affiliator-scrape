#!/usr/bin/env python3
"""
Premium CAPTCHA Handler dengan solver terbaik untuk TikTok/Tokopedia Affiliate.

Menggunakan multiple premium services untuk maximum success rate:
1. CapSolver (terbaik untuk TikTok/ByteDance CAPTCHAs)
2. 2Captcha (backup, reliable)
3. AntiCaptcha (backup, fast)
4. NoCaptcha (specialized untuk complex CAPTCHAs)

Features:
- Automatic service failover
- TikTok-specific CAPTCHA handling
- Advanced puzzle detection
- High success rate optimization
"""

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Union
import aiohttp
import json

from playwright.async_api import Page
from src.core.captcha_handler import CAPTCHAHandler, CAPTCHAType

logger = logging.getLogger(__name__)


class PremiumCAPTCHAService(Enum):
    """Premium CAPTCHA solving services."""
    CAPSOLVER = "capsolver"      # Best for TikTok/ByteDance
    TWOCAPTCHA = "2captcha"      # Reliable backup
    ANTICAPTCHA = "anticaptcha"  # Fast backup
    NOCAPTCHA = "nocaptcha"      # Complex CAPTCHAs


class TikTokCAPTCHAType(Enum):
    """TikTok-specific CAPTCHA types."""
    TIKTOK_ROTATE = "tiktok_rotate"           # Rotate puzzle
    TIKTOK_SLIDE = "tiktok_slide"             # Slide puzzle  
    TIKTOK_JIGSAW = "tiktok_jigsaw"           # Jigsaw puzzle
    TIKTOK_SHAPE_MATCH = "tiktok_shape_match" # Shape matching
    TIKTOK_SEQUENCE = "tiktok_sequence"       # Sequence puzzle
    BYTEDANCE_GEETEST = "bytedance_geetest"   # ByteDance GeeTest


class PremiumCAPTCHAHandler(CAPTCHAHandler):
    """Premium CAPTCHA handler dengan multiple services dan TikTok optimization."""
    
    def __init__(self, 
                 primary_service: str = "capsolver",
                 api_keys: Dict[str, str] = None,
                 enable_failover: bool = True,
                 max_solve_time: int = 120):
        """
        Initialize premium CAPTCHA handler.
        
        Args:
            primary_service: Primary service to use
            api_keys: Dict of service_name -> api_key
            enable_failover: Enable automatic failover to backup services
            max_solve_time: Maximum time to spend solving (seconds)
        """
        super().__init__(solver_type="premium", api_key=None)
        
        self.primary_service = primary_service
        self.api_keys = api_keys or {}
        self.enable_failover = enable_failover
        self.max_solve_time = max_solve_time
        
        # Service priority order (best to worst for TikTok)
        self.service_priority = [
            PremiumCAPTCHAService.CAPSOLVER,     # Best for TikTok
            PremiumCAPTCHAService.NOCAPTCHA,     # Good for complex puzzles
            PremiumCAPTCHAService.ANTICAPTCHA,   # Fast and reliable
            PremiumCAPTCHAService.TWOCAPTCHA,    # Reliable backup
        ]
        
        # Service endpoints
        self.service_endpoints = {
            PremiumCAPTCHAService.CAPSOLVER: {
                'submit': 'https://api.capsolver.com/createTask',
                'result': 'https://api.capsolver.com/getTaskResult'
            },
            PremiumCAPTCHAService.TWOCAPTCHA: {
                'submit': 'https://2captcha.com/in.php',
                'result': 'https://2captcha.com/res.php'
            },
            PremiumCAPTCHAService.ANTICAPTCHA: {
                'submit': 'https://api.anti-captcha.com/createTask',
                'result': 'https://api.anti-captcha.com/getTaskResult'
            },
            PremiumCAPTCHAService.NOCAPTCHA: {
                'submit': 'https://nocaptcha.io/api/createTask',
                'result': 'https://nocaptcha.io/api/getTaskResult'
            }
        }
        
        # Success tracking
        self.service_stats = {service: {'success': 0, 'total': 0} for service in self.service_priority}
        
        # TikTok-specific detection patterns
        self.tiktok_patterns = {
            TikTokCAPTCHAType.TIKTOK_ROTATE: [
                'div[class*="captcha_verify_container"]',
                'div[class*="verify-captcha"]',
                'div[class*="rotate-verify"]',
                'canvas[class*="captcha"]'
            ],
            TikTokCAPTCHAType.TIKTOK_SLIDE: [
                'div[class*="slide-verify"]',
                'div[class*="slider-captcha"]',
                'div[class*="captcha-slider"]'
            ],
            TikTokCAPTCHAType.TIKTOK_JIGSAW: [
                'div[class*="jigsaw"]',
                'div[class*="puzzle-captcha"]',
                'canvas[class*="jigsaw"]'
            ],
            TikTokCAPTCHAType.BYTEDANCE_GEETEST: [
                'div[class*="geetest"]',
                'div[class*="gt_"]',
                'div[id*="geetest"]'
            ]
        }
    
    async def detect(self, page: Page) -> Optional[Union[CAPTCHAType, TikTokCAPTCHAType]]:
        """Enhanced detection including TikTok-specific CAPTCHAs."""
        
        # First check for TikTok-specific CAPTCHAs
        tiktok_type = await self._detect_tiktok_captcha(page)
        if tiktok_type:
            return tiktok_type
        
        # Then check standard CAPTCHAs
        return await super().detect(page)
    
    async def _detect_tiktok_captcha(self, page: Page) -> Optional[TikTokCAPTCHAType]:
        """Detect TikTok-specific CAPTCHA types."""
        
        try:
            # Check page URL for TikTok domains
            url = page.url.lower()
            is_tiktok_domain = any(domain in url for domain in [
                'tiktok.com', 'bytedance.com', 'musical.ly', 
                'tokopedia.com', 'affiliate.tokopedia.com'
            ])
            
            if not is_tiktok_domain:
                return None
            
            # Check for TikTok CAPTCHA patterns
            for captcha_type, selectors in self.tiktok_patterns.items():
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            logger.info(f"TikTok CAPTCHA detected: {captcha_type.value}")
                            return captcha_type
                    except Exception:
                        continue
            
            # Check for ByteDance/TikTok specific scripts
            content = await page.content()
            tiktok_indicators = [
                'captcha.bytedance.com',
                'verify.bytedance.com', 
                'captcha-verify',
                'tiktok-captcha',
                'secsdk-captcha'
            ]
            
            for indicator in tiktok_indicators:
                if indicator in content:
                    logger.info(f"TikTok CAPTCHA detected via script: {indicator}")
                    return TikTokCAPTCHAType.BYTEDANCE_GEETEST
            
            return None
            
        except Exception as exc:
            logger.warning(f"Error detecting TikTok CAPTCHA: {exc}")
            return None
    
    async def solve(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> bool:
        """Enhanced solving with premium services and failover."""
        
        logger.info(f"Solving CAPTCHA type: {captcha_type}")
        
        # Determine which services to try
        services_to_try = self._get_services_for_captcha_type(captcha_type)
        
        for service in services_to_try:
            if service.value not in self.api_keys:
                logger.warning(f"No API key for {service.value}, skipping")
                continue
            
            logger.info(f"Attempting solve with {service.value}")
            
            try:
                success = await self._solve_with_service(page, captcha_type, service)
                
                # Update stats
                self.service_stats[service]['total'] += 1
                if success:
                    self.service_stats[service]['success'] += 1
                    logger.info(f"CAPTCHA solved successfully with {service.value}")
                    return True
                else:
                    logger.warning(f"CAPTCHA solve failed with {service.value}")
                    
            except Exception as exc:
                logger.error(f"Error solving with {service.value}: {exc}")
                self.service_stats[service]['total'] += 1
            
            # If failover disabled, only try primary service
            if not self.enable_failover:
                break
        
        logger.error("All CAPTCHA solving services failed")
        return False
    
    def _get_services_for_captcha_type(self, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> List[PremiumCAPTCHAService]:
        """Get optimal service order for CAPTCHA type."""
        
        # TikTok CAPTCHAs - use specialized order
        if isinstance(captcha_type, TikTokCAPTCHAType):
            return [
                PremiumCAPTCHAService.CAPSOLVER,    # Best for TikTok
                PremiumCAPTCHAService.NOCAPTCHA,    # Good for complex puzzles
                PremiumCAPTCHAService.ANTICAPTCHA,  # Fast backup
            ]
        
        # Standard CAPTCHAs - use general order
        elif captcha_type == CAPTCHAType.RECAPTCHA_V2:
            return [
                PremiumCAPTCHAService.ANTICAPTCHA,  # Fast for reCAPTCHA
                PremiumCAPTCHAService.TWOCAPTCHA,   # Reliable
                PremiumCAPTCHAService.CAPSOLVER,    # Good quality
            ]
        
        elif captcha_type == CAPTCHAType.RECAPTCHA_V3:
            return [
                PremiumCAPTCHAService.CAPSOLVER,    # Best for v3
                PremiumCAPTCHAService.ANTICAPTCHA,  # Good support
                PremiumCAPTCHAService.TWOCAPTCHA,   # Backup
            ]
        
        elif captcha_type == CAPTCHAType.HCAPTCHA:
            return [
                PremiumCAPTCHAService.CAPSOLVER,    # Excellent hCaptcha support
                PremiumCAPTCHAService.TWOCAPTCHA,   # Good support
                PremiumCAPTCHAService.ANTICAPTCHA,  # Backup
            ]
        
        else:
            # Default order
            return self.service_priority
    
    async def _solve_with_service(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType], 
                                 service: PremiumCAPTCHAService) -> bool:
        """Solve CAPTCHA with specific service."""
        
        if service == PremiumCAPTCHAService.CAPSOLVER:
            return await self._solve_with_capsolver(page, captcha_type)
        elif service == PremiumCAPTCHAService.TWOCAPTCHA:
            return await self._solve_with_2captcha(page, captcha_type)
        elif service == PremiumCAPTCHAService.ANTICAPTCHA:
            return await self._solve_with_anticaptcha(page, captcha_type)
        elif service == PremiumCAPTCHAService.NOCAPTCHA:
            return await self._solve_with_nocaptcha(page, captcha_type)
        else:
            return False
    
    async def _solve_with_capsolver(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> bool:
        """Solve with CapSolver (best for TikTok)."""
        
        try:
            api_key = self.api_keys[PremiumCAPTCHAService.CAPSOLVER.value]
            
            # Prepare task based on CAPTCHA type
            if isinstance(captcha_type, TikTokCAPTCHAType):
                task_data = await self._prepare_tiktok_task_capsolver(page, captcha_type)
            else:
                task_data = await self._prepare_standard_task_capsolver(page, captcha_type)
            
            if not task_data:
                return False
            
            # Submit task
            submit_payload = {
                "clientKey": api_key,
                "task": task_data
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit
                async with session.post(
                    self.service_endpoints[PremiumCAPTCHAService.CAPSOLVER]['submit'],
                    json=submit_payload
                ) as response:
                    result = await response.json()
                    
                    if result.get('errorId') != 0:
                        logger.error(f"CapSolver submit error: {result.get('errorDescription')}")
                        return False
                    
                    task_id = result.get('taskId')
                    if not task_id:
                        return False
                
                # Poll for result
                start_time = time.time()
                while time.time() - start_time < self.max_solve_time:
                    await asyncio.sleep(3)
                    
                    async with session.post(
                        self.service_endpoints[PremiumCAPTCHAService.CAPSOLVER]['result'],
                        json={"clientKey": api_key, "taskId": task_id}
                    ) as response:
                        result = await response.json()
                        
                        if result.get('errorId') != 0:
                            logger.error(f"CapSolver result error: {result.get('errorDescription')}")
                            return False
                        
                        status = result.get('status')
                        if status == 'ready':
                            solution = result.get('solution', {})
                            return await self._apply_solution(page, captcha_type, solution)
                        elif status == 'failed':
                            logger.error("CapSolver task failed")
                            return False
                
                logger.error("CapSolver timeout")
                return False
                
        except Exception as exc:
            logger.error(f"CapSolver error: {exc}")
            return False
    
    async def _prepare_tiktok_task_capsolver(self, page: Page, captcha_type: TikTokCAPTCHAType) -> Optional[Dict]:
        """Prepare CapSolver task for TikTok CAPTCHA."""
        
        try:
            if captcha_type == TikTokCAPTCHAType.BYTEDANCE_GEETEST:
                # ByteDance GeeTest
                gt_key = await self._extract_geetest_params(page)
                if not gt_key:
                    return None
                
                return {
                    "type": "GeetestTaskProxyless",
                    "websiteURL": page.url,
                    "gt": gt_key.get('gt'),
                    "challenge": gt_key.get('challenge'),
                    "geetestApiServerSubdomain": gt_key.get('api_server', 'api.geetest.com')
                }
            
            elif captcha_type in [TikTokCAPTCHAType.TIKTOK_ROTATE, TikTokCAPTCHAType.TIKTOK_SLIDE]:
                # TikTok puzzle CAPTCHAs
                puzzle_data = await self._extract_tiktok_puzzle_data(page)
                if not puzzle_data:
                    return None
                
                return {
                    "type": "ImageToCoordinatesTask",
                    "websiteURL": page.url,
                    "body": puzzle_data['image_base64'],
                    "comment": f"TikTok {captcha_type.value} puzzle"
                }
            
            else:
                # Generic TikTok CAPTCHA
                screenshot = await page.screenshot(type='png')
                import base64
                image_base64 = base64.b64encode(screenshot).decode()
                
                return {
                    "type": "ImageToCoordinatesTask", 
                    "websiteURL": page.url,
                    "body": image_base64,
                    "comment": f"TikTok CAPTCHA: {captcha_type.value}"
                }
                
        except Exception as exc:
            logger.error(f"Error preparing TikTok task: {exc}")
            return None
    
    async def _prepare_standard_task_capsolver(self, page: Page, captcha_type: CAPTCHAType) -> Optional[Dict]:
        """Prepare CapSolver task for standard CAPTCHA."""
        
        try:
            if captcha_type == CAPTCHAType.RECAPTCHA_V2:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    return None
                
                return {
                    "type": "ReCaptchaV2TaskProxyless",
                    "websiteURL": page.url,
                    "websiteKey": site_key
                }
            
            elif captcha_type == CAPTCHAType.RECAPTCHA_V3:
                site_key = await self._get_recaptcha_site_key(page)
                if not site_key:
                    return None
                
                return {
                    "type": "ReCaptchaV3TaskProxyless",
                    "websiteURL": page.url,
                    "websiteKey": site_key,
                    "pageAction": "verify",
                    "minScore": 0.3
                }
            
            elif captcha_type == CAPTCHAType.HCAPTCHA:
                site_key = await self._get_hcaptcha_site_key(page)
                if not site_key:
                    return None
                
                return {
                    "type": "HCaptchaTaskProxyless",
                    "websiteURL": page.url,
                    "websiteKey": site_key
                }
            
            else:
                return None
                
        except Exception as exc:
            logger.error(f"Error preparing standard task: {exc}")
            return None
    
    async def _solve_with_2captcha(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> bool:
        """Solve with 2Captcha service."""
        
        try:
            # Use existing 2captcha implementation from parent class
            return await super()._solve_2captcha(page, captcha_type)
            
        except Exception as exc:
            logger.error(f"2Captcha error: {exc}")
            return False
    
    async def _solve_with_anticaptcha(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> bool:
        """Solve with AntiCaptcha service."""
        
        try:
            # Use existing anticaptcha implementation from parent class
            return await super()._solve_anticaptcha(page, captcha_type)
            
        except Exception as exc:
            logger.error(f"AntiCaptcha error: {exc}")
            return False
    
    async def _solve_with_nocaptcha(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType]) -> bool:
        """Solve with NoCaptcha service (specialized for complex CAPTCHAs)."""
        
        try:
            api_key = self.api_keys[PremiumCAPTCHAService.NOCAPTCHA.value]
            
            # NoCaptcha specializes in complex puzzles
            if isinstance(captcha_type, TikTokCAPTCHAType):
                # Take screenshot for puzzle solving
                screenshot = await page.screenshot(type='png')
                import base64
                image_base64 = base64.b64encode(screenshot).decode()
                
                task_data = {
                    "type": "ImageToCoordinatesTask",
                    "body": image_base64,
                    "comment": f"TikTok puzzle: {captcha_type.value}",
                    "websiteURL": page.url
                }
            else:
                # Standard CAPTCHA handling
                return False  # NoCaptcha specializes in puzzles
            
            # Submit and poll (similar to CapSolver)
            submit_payload = {
                "clientKey": api_key,
                "task": task_data
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit task
                async with session.post(
                    self.service_endpoints[PremiumCAPTCHAService.NOCAPTCHA]['submit'],
                    json=submit_payload
                ) as response:
                    result = await response.json()
                    
                    if not result.get('success'):
                        logger.error(f"NoCaptcha submit error: {result.get('error')}")
                        return False
                    
                    task_id = result.get('taskId')
                    if not task_id:
                        return False
                
                # Poll for result
                start_time = time.time()
                while time.time() - start_time < self.max_solve_time:
                    await asyncio.sleep(5)
                    
                    async with session.post(
                        self.service_endpoints[PremiumCAPTCHAService.NOCAPTCHA]['result'],
                        json={"clientKey": api_key, "taskId": task_id}
                    ) as response:
                        result = await response.json()
                        
                        if result.get('status') == 'ready':
                            solution = result.get('solution', {})
                            return await self._apply_solution(page, captcha_type, solution)
                        elif result.get('status') == 'failed':
                            logger.error("NoCaptcha task failed")
                            return False
                
                logger.error("NoCaptcha timeout")
                return False
                
        except Exception as exc:
            logger.error(f"NoCaptcha error: {exc}")
            return False
    
    async def _apply_solution(self, page: Page, captcha_type: Union[CAPTCHAType, TikTokCAPTCHAType], 
                            solution: Dict) -> bool:
        """Apply CAPTCHA solution to page."""
        
        try:
            if isinstance(captcha_type, TikTokCAPTCHAType):
                return await self._apply_tiktok_solution(page, captcha_type, solution)
            else:
                return await self._apply_standard_solution(page, captcha_type, solution)
                
        except Exception as exc:
            logger.error(f"Error applying solution: {exc}")
            return False
    
    async def _apply_tiktok_solution(self, page: Page, captcha_type: TikTokCAPTCHAType, solution: Dict) -> bool:
        """Apply TikTok CAPTCHA solution."""
        
        try:
            if captcha_type == TikTokCAPTCHAType.BYTEDANCE_GEETEST:
                # Apply GeeTest solution
                validate = solution.get('validate')
                seccode = solution.get('seccode')
                
                if validate and seccode:
                    await page.evaluate(f"""
                        () => {{
                            if (window.geetest_validate) {{
                                window.geetest_validate('{validate}', '{seccode}');
                            }}
                        }}
                    """)
                    return True
            
            elif captcha_type in [TikTokCAPTCHAType.TIKTOK_ROTATE, TikTokCAPTCHAType.TIKTOK_SLIDE]:
                # Apply coordinate-based solution
                coordinates = solution.get('coordinates', [])
                if coordinates:
                    for coord in coordinates:
                        x, y = coord.get('x', 0), coord.get('y', 0)
                        await page.mouse.click(x, y)
                        await asyncio.sleep(0.5)
                    return True
            
            return False
            
        except Exception as exc:
            logger.error(f"Error applying TikTok solution: {exc}")
            return False
    
    async def _apply_standard_solution(self, page: Page, captcha_type: CAPTCHAType, solution: Dict) -> bool:
        """Apply standard CAPTCHA solution."""
        
        try:
            token = solution.get('gRecaptchaResponse') or solution.get('token')
            
            if not token:
                return False
            
            if captcha_type in [CAPTCHAType.RECAPTCHA_V2, CAPTCHAType.RECAPTCHA_V3]:
                await self._inject_recaptcha_token(page, token)
                return True
            elif captcha_type == CAPTCHAType.HCAPTCHA:
                await self._inject_hcaptcha_token(page, token)
                return True
            
            return False
            
        except Exception as exc:
            logger.error(f"Error applying standard solution: {exc}")
            return False
    
    async def _extract_geetest_params(self, page: Page) -> Optional[Dict]:
        """Extract GeeTest parameters from page."""
        
        try:
            # Look for GeeTest initialization
            geetest_data = await page.evaluate("""
                () => {
                    // Look for GeeTest global variables
                    if (window.gt && window.challenge) {
                        return {
                            gt: window.gt,
                            challenge: window.challenge,
                            api_server: window.api_server || 'api.geetest.com'
                        };
                    }
                    
                    // Look in script tags
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const text = script.textContent || script.innerText;
                        const gtMatch = text.match(/gt['"\\s]*:['"\\s]*([a-f0-9]{32})/i);
                        const challengeMatch = text.match(/challenge['"\\s]*:['"\\s]*([a-f0-9]{32})/i);
                        
                        if (gtMatch && challengeMatch) {
                            return {
                                gt: gtMatch[1],
                                challenge: challengeMatch[1],
                                api_server: 'api.geetest.com'
                            };
                        }
                    }
                    
                    return null;
                }
            """)
            
            return geetest_data
            
        except Exception as exc:
            logger.error(f"Error extracting GeeTest params: {exc}")
            return None
    
    async def _extract_tiktok_puzzle_data(self, page: Page) -> Optional[Dict]:
        """Extract TikTok puzzle image data."""
        
        try:
            # Look for puzzle canvas or image
            puzzle_element = await page.query_selector('canvas[class*="captcha"], img[class*="captcha"]')
            
            if puzzle_element:
                # Take screenshot of puzzle element
                screenshot = await puzzle_element.screenshot(type='png')
                import base64
                image_base64 = base64.b64encode(screenshot).decode()
                
                return {
                    'image_base64': image_base64,
                    'element_bounds': await puzzle_element.bounding_box()
                }
            
            return None
            
        except Exception as exc:
            logger.error(f"Error extracting TikTok puzzle data: {exc}")
            return None
    
    def get_service_stats(self) -> Dict:
        """Get success statistics for all services."""
        
        stats = {}
        for service, data in self.service_stats.items():
            total = data['total']
            success = data['success']
            success_rate = (success / total * 100) if total > 0 else 0
            
            stats[service.value] = {
                'total_attempts': total,
                'successful': success,
                'success_rate': f"{success_rate:.1f}%"
            }
        
        return stats
    
    def get_recommended_service(self) -> PremiumCAPTCHAService:
        """Get currently best performing service."""
        
        best_service = self.service_priority[0]  # Default
        best_rate = 0
        
        for service, data in self.service_stats.items():
            if data['total'] >= 5:  # Minimum attempts for reliable stats
                rate = data['success'] / data['total']
                if rate > best_rate:
                    best_rate = rate
                    best_service = service
        
        return best_service


# Factory function for easy initialization
def create_premium_captcha_handler(config: Dict) -> PremiumCAPTCHAHandler:
    """Create premium CAPTCHA handler from config."""
    
    api_keys = {}
    
    # Extract API keys from config
    if config.get('capsolver_api_key'):
        api_keys['capsolver'] = config['capsolver_api_key']
    if config.get('2captcha_api_key'):
        api_keys['2captcha'] = config['2captcha_api_key']
    if config.get('anticaptcha_api_key'):
        api_keys['anticaptcha'] = config['anticaptcha_api_key']
    if config.get('nocaptcha_api_key'):
        api_keys['nocaptcha'] = config['nocaptcha_api_key']
    
    return PremiumCAPTCHAHandler(
        primary_service=config.get('primary_captcha_service', 'capsolver'),
        api_keys=api_keys,
        enable_failover=config.get('enable_captcha_failover', True),
        max_solve_time=config.get('max_captcha_solve_time', 120)
    )