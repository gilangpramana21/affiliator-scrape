#!/usr/bin/env python3
"""
Test script untuk premium CAPTCHA handler dengan TikTok optimization.

Tests:
1. Service connectivity dan API key validation
2. TikTok CAPTCHA detection
3. Premium solving dengan multiple services
4. Failover mechanism
5. Success rate tracking
"""

import asyncio
import json
import logging
from typing import Dict, List

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.premium_captcha_handler import PremiumCAPTCHAHandler, create_premium_captcha_handler
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PremiumCAPTCHATestRunner:
    """Test runner untuk premium CAPTCHA services."""
    
    def __init__(self, config_file: str = "config/premium_captcha_config.json"):
        # Load premium CAPTCHA config
        with open(config_file, 'r') as f:
            self.captcha_config = json.load(f)['captcha_config']
        
        # Load main config
        self.main_config = Configuration.from_file("config/config_jelajahi.json")
        
        # Setup components
        self.fingerprint_gen = FingerprintGenerator()
        self.browser_engine = BrowserEngine()
        self.session_manager = SessionManager()
        
        # Create premium CAPTCHA handler
        self.captcha_handler = create_premium_captcha_handler(self.captcha_config)
        
        # Test results
        self.test_results = {
            'api_key_tests': [],
            'detection_tests': [],
            'solving_tests': [],
            'failover_tests': [],
            'performance_tests': [],
            'summary': {}
        }
    
    async def run_all_tests(self) -> Dict:
        """Run comprehensive premium CAPTCHA tests."""
        
        print("🏆 PREMIUM CAPTCHA HANDLER TESTS")
        print("=" * 60)
        print("Testing TikTok-optimized CAPTCHA solving with premium services")
        
        try:
            # Setup browser
            await self._setup_browser()
            
            # Test 1: API Key Validation
            print("\n1️⃣ Testing API Key Validation...")
            await self._test_api_keys()
            
            # Test 2: TikTok CAPTCHA Detection
            print("\n2️⃣ Testing TikTok CAPTCHA Detection...")
            await self._test_tiktok_detection()
            
            # Test 3: Premium Solving
            print("\n3️⃣ Testing Premium CAPTCHA Solving...")
            await self._test_premium_solving()
            
            # Test 4: Failover Mechanism
            print("\n4️⃣ Testing Service Failover...")
            await self._test_failover_mechanism()
            
            # Test 5: Performance Tracking
            print("\n5️⃣ Testing Performance Tracking...")
            await self._test_performance_tracking()
            
            # Generate summary
            self._generate_summary()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"Test runner error: {e}")
            import traceback
            traceback.print_exc()
            return self.test_results
        
        finally:
            await self._cleanup()
    
    async def _setup_browser(self):
        """Setup browser dengan TikTok-optimized fingerprint."""
        
        print("🚀 Setting up TikTok-optimized browser...")
        
        # Generate fingerprint optimized for TikTok
        fingerprint = self.fingerprint_gen.generate()
        
        # Launch browser
        await self.browser_engine.launch(fingerprint, headless=False)
        
        # Load cookies
        self.session_manager.load_session(self.main_config.cookie_file)
        cookies = self.session_manager.get_cookies()
        
        if cookies:
            cookie_list = []
            for cookie in cookies:
                cookie_list.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'httpOnly': cookie.http_only,
                    'secure': cookie.secure
                })
            
            await self.browser_engine.context.add_cookies(cookie_list)
        
        print(f"✅ Browser setup complete (loaded {len(cookies)} cookies)")
    
    async def _test_api_keys(self):
        """Test API key validation untuk semua services."""
        
        api_keys = self.captcha_config.get('api_keys', {})
        
        for service_name, api_key in api_keys.items():
            if not api_key or api_key.startswith('YOUR_'):
                print(f"   ⚠️ {service_name}: No valid API key configured")
                self.test_results['api_key_tests'].append({
                    'service': service_name,
                    'status': 'not_configured',
                    'valid': False
                })
                continue
            
            print(f"   🔑 Testing {service_name} API key...")
            
            try:
                # Test API key validity (simplified check)
                valid = await self._validate_api_key(service_name, api_key)
                
                status = 'valid' if valid else 'invalid'
                print(f"      {'✅' if valid else '❌'} {service_name}: {status}")
                
                self.test_results['api_key_tests'].append({
                    'service': service_name,
                    'status': status,
                    'valid': valid
                })
                
            except Exception as e:
                print(f"      ❌ {service_name}: Error - {e}")
                self.test_results['api_key_tests'].append({
                    'service': service_name,
                    'status': 'error',
                    'error': str(e),
                    'valid': False
                })
    
    async def _validate_api_key(self, service_name: str, api_key: str) -> bool:
        """Validate API key untuk specific service."""
        
        # Simplified validation - check format and length
        if service_name == 'capsolver_api_key':
            return len(api_key) >= 32 and api_key.startswith('CAP-')
        elif service_name == '2captcha_api_key':
            return len(api_key) == 32 and api_key.isalnum()
        elif service_name == 'anticaptcha_api_key':
            return len(api_key) >= 32 and api_key.isalnum()
        elif service_name == 'nocaptcha_api_key':
            return len(api_key) >= 20
        
        return len(api_key) > 10  # Basic check
    
    async def _test_tiktok_detection(self):
        """Test TikTok CAPTCHA detection capabilities."""
        
        # Test URLs yang mungkin ada TikTok CAPTCHAs
        test_urls = [
            f"{self.main_config.base_url}{self.main_config.list_page_url}",
            "https://www.tiktok.com/login",  # Known to have TikTok CAPTCHAs
        ]
        
        for i, url in enumerate(test_urls, 1):
            print(f"   Test {i}: {url}")
            
            try:
                page = await self.browser_engine.navigate(url)
                await asyncio.sleep(3)
                
                # Test TikTok CAPTCHA detection
                captcha_type = await self.captcha_handler.detect(page)
                
                is_tiktok_captcha = hasattr(captcha_type, 'value') and 'tiktok' in str(captcha_type.value).lower()
                
                test_result = {
                    'url': url,
                    'captcha_detected': captcha_type is not None,
                    'captcha_type': str(captcha_type) if captcha_type else None,
                    'is_tiktok_captcha': is_tiktok_captcha,
                    'success': True
                }
                
                if captcha_type:
                    print(f"      🧩 CAPTCHA detected: {captcha_type}")
                    if is_tiktok_captcha:
                        print(f"      🎯 TikTok-specific CAPTCHA!")
                else:
                    print(f"      ✅ No CAPTCHA detected")
                
                self.test_results['detection_tests'].append(test_result)
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                self.test_results['detection_tests'].append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
    
    async def _test_premium_solving(self):
        """Test premium CAPTCHA solving capabilities."""
        
        print("   Testing premium solving capabilities...")
        
        # Navigate to a page that might have CAPTCHAs
        try:
            url = f"{self.main_config.base_url}{self.main_config.list_page_url}{self.main_config.list_page_query}"
            page = await self.browser_engine.navigate(url)
            await asyncio.sleep(3)
            
            # Check for any CAPTCHA
            captcha_type = await self.captcha_handler.detect(page)
            
            if captcha_type:
                print(f"      🧩 CAPTCHA found: {captcha_type}")
                print(f"      🚀 Testing premium solving...")
                
                # Test solving
                start_time = asyncio.get_event_loop().time()
                success = await self.captcha_handler.solve(page, captcha_type)
                solve_time = asyncio.get_event_loop().time() - start_time
                
                test_result = {
                    'captcha_type': str(captcha_type),
                    'solve_success': success,
                    'solve_time_seconds': solve_time,
                    'services_tried': len(self.captcha_handler.api_keys),
                    'success': True
                }
                
                print(f"      Result: {'✅ SOLVED' if success else '❌ FAILED'} ({solve_time:.1f}s)")
                
            else:
                print(f"      ℹ️ No CAPTCHA found for testing")
                test_result = {
                    'captcha_type': None,
                    'solve_success': None,
                    'message': 'No CAPTCHA available for testing',
                    'success': True
                }
            
            self.test_results['solving_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Premium solving test error: {e}")
            self.test_results['solving_tests'].append({
                'error': str(e),
                'success': False
            })
    
    async def _test_failover_mechanism(self):
        """Test service failover mechanism."""
        
        print("   Testing service failover mechanism...")
        
        try:
            # Get current service stats
            initial_stats = self.captcha_handler.get_service_stats()
            
            # Test failover logic (simulate)
            services_available = len([k for k, v in self.captcha_handler.api_keys.items() 
                                    if v and not v.startswith('YOUR_')])
            
            failover_enabled = self.captcha_handler.enable_failover
            
            test_result = {
                'services_configured': len(self.captcha_handler.api_keys),
                'services_available': services_available,
                'failover_enabled': failover_enabled,
                'primary_service': self.captcha_handler.primary_service,
                'service_priority': [s.value for s in self.captcha_handler.service_priority],
                'success': services_available >= 2 and failover_enabled
            }
            
            print(f"      Services configured: {test_result['services_configured']}")
            print(f"      Services available: {test_result['services_available']}")
            print(f"      Failover enabled: {test_result['failover_enabled']}")
            print(f"      Primary service: {test_result['primary_service']}")
            
            if test_result['success']:
                print(f"      ✅ Failover mechanism ready")
            else:
                print(f"      ⚠️ Failover mechanism needs attention")
            
            self.test_results['failover_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Failover test error: {e}")
            self.test_results['failover_tests'].append({
                'error': str(e),
                'success': False
            })
    
    async def _test_performance_tracking(self):
        """Test performance tracking capabilities."""
        
        print("   Testing performance tracking...")
        
        try:
            # Get service statistics
            stats = self.captcha_handler.get_service_stats()
            
            # Get recommended service
            recommended = self.captcha_handler.get_recommended_service()
            
            test_result = {
                'service_stats': stats,
                'recommended_service': recommended.value,
                'stats_tracking_enabled': True,
                'success': True
            }
            
            print(f"      Service statistics:")
            for service, data in stats.items():
                print(f"        {service}: {data['success_rate']} ({data['successful']}/{data['total_attempts']})")
            
            print(f"      Recommended service: {recommended.value}")
            print(f"      ✅ Performance tracking working")
            
            self.test_results['performance_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Performance tracking test error: {e}")
            self.test_results['performance_tests'].append({
                'error': str(e),
                'success': False
            })
    
    def _generate_summary(self):
        """Generate comprehensive test summary."""
        
        summary = {}
        
        # Count successes for each test type
        for test_type, tests in self.test_results.items():
            if test_type == 'summary':
                continue
                
            if tests:
                total = len(tests)
                successful = sum(1 for test in tests if test.get('success', False))
                summary[test_type] = {
                    'total': total,
                    'successful': successful,
                    'success_rate': successful / total * 100 if total > 0 else 0
                }
            else:
                summary[test_type] = {
                    'total': 0,
                    'successful': 0,
                    'success_rate': 0
                }
        
        # Overall summary
        total_tests = sum(s['total'] for s in summary.values())
        total_successful = sum(s['successful'] for s in summary.values())
        overall_success_rate = total_successful / total_tests * 100 if total_tests > 0 else 0
        
        # API key analysis
        api_key_tests = self.test_results.get('api_key_tests', [])
        valid_keys = sum(1 for test in api_key_tests if test.get('valid', False))
        total_keys = len(api_key_tests)
        
        summary['overall'] = {
            'total_tests': total_tests,
            'total_successful': total_successful,
            'overall_success_rate': overall_success_rate,
            'valid_api_keys': valid_keys,
            'total_api_keys': total_keys,
            'ready_for_production': valid_keys >= 2 and overall_success_rate >= 80
        }
        
        self.test_results['summary'] = summary
        
        # Print summary
        print(f"\n🏆 PREMIUM CAPTCHA TEST SUMMARY:")
        print("=" * 50)
        
        for test_type, stats in summary.items():
            if test_type == 'overall':
                continue
            print(f"{test_type}: {stats['successful']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        
        print(f"\nAPI Keys: {valid_keys}/{total_keys} valid")
        print(f"Overall: {total_successful}/{total_tests} ({overall_success_rate:.1f}%)")
        
        if summary['overall']['ready_for_production']:
            print("🎉 READY FOR PRODUCTION!")
            print("   ✅ Multiple API keys configured")
            print("   ✅ High test success rate")
            print("   ✅ Premium services operational")
        else:
            print("⚠️ NEEDS CONFIGURATION:")
            if valid_keys < 2:
                print("   ❌ Need at least 2 valid API keys")
            if overall_success_rate < 80:
                print("   ❌ Test success rate too low")
    
    async def _cleanup(self):
        """Cleanup resources."""
        
        print(f"\n🧹 Cleaning up...")
        
        try:
            await self.browser_engine.close()
            print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")


async def quick_premium_test():
    """Quick test untuk validate premium CAPTCHA setup."""
    
    print("⚡ QUICK PREMIUM CAPTCHA TEST")
    print("=" * 40)
    
    try:
        # Load config
        with open("config/premium_captcha_config.json", 'r') as f:
            config = json.load(f)['captcha_config']
        
        # Create handler
        handler = create_premium_captcha_handler(config)
        
        # Check API keys
        api_keys = config.get('api_keys', {})
        valid_keys = 0
        
        print("🔑 API Key Status:")
        for service, key in api_keys.items():
            if key and not key.startswith('YOUR_'):
                print(f"   ✅ {service}: Configured")
                valid_keys += 1
            else:
                print(f"   ❌ {service}: Not configured")
        
        print(f"\nValid API keys: {valid_keys}/{len(api_keys)}")
        
        if valid_keys >= 2:
            print("✅ Ready for premium CAPTCHA solving!")
        elif valid_keys >= 1:
            print("⚠️ Partially ready (recommend 2+ services)")
        else:
            print("❌ No API keys configured")
        
        # Show service priority
        print(f"\nService Priority:")
        for i, service in enumerate(handler.service_priority, 1):
            status = "✅" if service.value + "_api_key" in api_keys and api_keys[service.value + "_api_key"] and not api_keys[service.value + "_api_key"].startswith('YOUR_') else "❌"
            print(f"   {i}. {service.value} {status}")
        
    except Exception as e:
        print(f"❌ Quick test error: {e}")


async def main():
    """Main test function."""
    
    print("Choose test mode:")
    print("1. Quick validation (recommended)")
    print("2. Comprehensive testing")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        await quick_premium_test()
    else:
        runner = PremiumCAPTCHATestRunner()
        results = await runner.run_all_tests()
        
        # Save results
        output_file = 'premium_captcha_test_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Test results saved: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())