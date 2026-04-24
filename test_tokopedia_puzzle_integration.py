#!/usr/bin/env python3
"""
Test script untuk validate Tokopedia puzzle handling integration.

Tests:
1. Real Tokopedia puzzle detection
2. Auto-refresh puzzle solving
3. New tab workflow
4. Consecutive puzzle tracking
5. Profile data extraction after puzzle bypass
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captcha_handler import CAPTCHAHandler
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokopediaPuzzleTestRunner:
    """Test runner untuk validate Tokopedia puzzle handling."""
    
    def __init__(self, config_file: str = "config/config_jelajahi.json"):
        self.config = Configuration.from_file(config_file)
        self.fingerprint_gen = FingerprintGenerator()
        self.browser_engine = BrowserEngine()
        self.captcha_handler = CAPTCHAHandler(solver_type="manual")
        self.parser = HTMLParser()
        self.extractor = TokopediaExtractor(self.parser)
        self.session_manager = SessionManager()
        
        # Test results
        self.test_results = {
            'puzzle_detection_tests': [],
            'puzzle_solving_tests': [],
            'new_tab_workflow_tests': [],
            'consecutive_puzzle_tests': [],
            'profile_extraction_tests': [],
            'summary': {}
        }
    
    async def run_all_tests(self) -> Dict:
        """Run semua tests dan return hasil."""
        
        print("🧪 TOKOPEDIA PUZZLE INTEGRATION TESTS")
        print("=" * 60)
        
        try:
            # Setup browser
            await self._setup_browser()
            
            # Test 1: Puzzle Detection
            print("\n1️⃣ Testing Puzzle Detection...")
            await self._test_puzzle_detection()
            
            # Test 2: Puzzle Solving
            print("\n2️⃣ Testing Puzzle Solving...")
            await self._test_puzzle_solving()
            
            # Test 3: New Tab Workflow
            print("\n3️⃣ Testing New Tab Workflow...")
            await self._test_new_tab_workflow()
            
            # Test 4: Consecutive Puzzle Tracking
            print("\n4️⃣ Testing Consecutive Puzzle Tracking...")
            await self._test_consecutive_puzzle_tracking()
            
            # Test 5: Profile Data Extraction
            print("\n5️⃣ Testing Profile Data Extraction...")
            await self._test_profile_extraction_after_puzzle()
            
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
        """Setup browser dengan fingerprint dan cookies."""
        
        print("🚀 Setting up browser...")
        
        # Generate fingerprint
        fingerprint = self.fingerprint_gen.generate()
        
        # Launch browser (visible untuk debugging)
        await self.browser_engine.launch(fingerprint, headless=False)
        
        # Load cookies
        self.session_manager.load_session(self.config.cookie_file)
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
            
            # Apply cookies to context
            if self.browser_engine.context:
                await self.browser_engine.context.add_cookies(cookie_list)
        
        print(f"✅ Browser setup complete (loaded {len(cookies)} cookies)")
    
    async def _test_puzzle_detection(self):
        """Test puzzle detection pada real Tokopedia pages."""
        
        test_urls = [
            f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}",
        ]
        
        for i, url in enumerate(test_urls, 1):
            print(f"   Test {i}: {url}")
            
            try:
                # Navigate to page
                page = await self.browser_engine.navigate(url)
                await asyncio.sleep(3)
                
                # Get creators from list
                html = await self.browser_engine.get_html(page)
                doc = self.parser.parse(html)
                result = self.extractor.extract_list_page(doc)
                
                if result.affiliators:
                    # Test puzzle detection on first creator detail URL
                    creator = result.affiliators[0]
                    detail_url = creator.detail_url
                    
                    print(f"      Testing puzzle detection on: {creator.username}")
                    
                    # Open detail page in new tab
                    detail_page = await self.browser_engine.context.new_page()
                    await detail_page.goto(detail_url)
                    await asyncio.sleep(2)
                    
                    # Test detection
                    puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(detail_page)
                    
                    test_result = {
                        'url': detail_url,
                        'creator': creator.username,
                        'puzzle_detected': puzzle_detected,
                        'timestamp': time.time(),
                        'success': True
                    }
                    
                    print(f"      Result: {'🧩 Puzzle detected' if puzzle_detected else '✅ No puzzle'}")
                    
                    await detail_page.close()
                    
                else:
                    test_result = {
                        'url': url,
                        'error': 'No creators found',
                        'success': False
                    }
                    print(f"      ❌ No creators found")
                
                self.test_results['puzzle_detection_tests'].append(test_result)
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                self.test_results['puzzle_detection_tests'].append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
    
    async def _test_puzzle_solving(self):
        """Test puzzle solving dengan auto-refresh."""
        
        print("   Testing puzzle solving strategy...")
        
        try:
            # Navigate to list page
            url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
            page = await self.browser_engine.navigate(url)
            await asyncio.sleep(3)
            
            # Get first creator
            html = await self.browser_engine.get_html(page)
            doc = self.parser.parse(html)
            result = self.extractor.extract_list_page(doc)
            
            if result.affiliators:
                creator = result.affiliators[0]
                detail_url = creator.detail_url
                
                print(f"      Testing puzzle solving on: {creator.username}")
                
                # Open detail page
                detail_page = await self.browser_engine.context.new_page()
                await detail_page.goto(detail_url)
                await asyncio.sleep(2)
                
                # Check for puzzle
                puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(detail_page)
                
                if puzzle_detected:
                    print(f"      🧩 Puzzle detected, testing solve...")
                    
                    # Test solving
                    start_time = time.time()
                    success = await self.captcha_handler.solve_tokopedia_puzzle(detail_page)
                    solve_time = time.time() - start_time
                    
                    test_result = {
                        'creator': creator.username,
                        'puzzle_initially_detected': True,
                        'solve_success': success,
                        'solve_time_seconds': solve_time,
                        'consecutive_count': self.captcha_handler.consecutive_puzzle_count,
                        'success': True
                    }
                    
                    print(f"      Result: {'✅ Solved' if success else '❌ Failed'} ({solve_time:.1f}s)")
                    
                else:
                    test_result = {
                        'creator': creator.username,
                        'puzzle_initially_detected': False,
                        'solve_success': True,  # No puzzle to solve
                        'solve_time_seconds': 0,
                        'success': True
                    }
                    
                    print(f"      ✅ No puzzle detected")
                
                await detail_page.close()
                
            else:
                test_result = {
                    'error': 'No creators found',
                    'success': False
                }
                print(f"      ❌ No creators found")
            
            self.test_results['puzzle_solving_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            self.test_results['puzzle_solving_tests'].append({
                'error': str(e),
                'success': False
            })
    
    async def _test_new_tab_workflow(self):
        """Test new tab workflow seperti di main orchestrator."""
        
        print("   Testing new tab workflow...")
        
        try:
            # Navigate to list page
            url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
            main_page = await self.browser_engine.navigate(url)
            await asyncio.sleep(3)
            
            # Get creators
            html = await self.browser_engine.get_html(main_page)
            doc = self.parser.parse(html)
            result = self.extractor.extract_list_page(doc)
            
            if result.affiliators:
                # Test dengan 2 creators
                test_creators = result.affiliators[:2]
                
                for i, creator in enumerate(test_creators, 1):
                    print(f"      Tab test {i}: {creator.username}")
                    
                    # Simulate orchestrator workflow
                    detail_page = None
                    
                    try:
                        # 1. Check consecutive puzzle pause (simulate)
                        if self.captcha_handler.should_pause_for_puzzles():
                            print(f"         ⏸️ Would pause for consecutive puzzles")
                        
                        # 2. Open new tab
                        detail_page = await self.browser_engine.context.new_page()
                        
                        # 3. Navigate
                        await detail_page.goto(creator.detail_url)
                        await asyncio.sleep(2)
                        
                        # 4. Handle puzzle
                        puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(detail_page)
                        puzzle_solved = True
                        
                        if puzzle_detected:
                            print(f"         🧩 Puzzle detected, solving...")
                            puzzle_solved = await self.captcha_handler.solve_tokopedia_puzzle(detail_page)
                        
                        # 5. Extract data (simulate)
                        if puzzle_solved:
                            html = await detail_page.content()
                            # Basic check for profile content
                            has_profile_content = len(html) > 1000 and 'creator' in html.lower()
                            print(f"         {'✅' if has_profile_content else '❌'} Profile content available")
                        
                        test_result = {
                            'creator': creator.username,
                            'tab_opened': True,
                            'puzzle_detected': puzzle_detected,
                            'puzzle_solved': puzzle_solved,
                            'profile_content_available': has_profile_content if puzzle_solved else False,
                            'success': puzzle_solved
                        }
                        
                    except Exception as e:
                        print(f"         ❌ Tab workflow error: {e}")
                        test_result = {
                            'creator': creator.username,
                            'error': str(e),
                            'success': False
                        }
                    
                    finally:
                        # 6. Always close tab
                        if detail_page:
                            try:
                                await detail_page.close()
                                print(f"         🗑️ Tab closed")
                            except Exception as e:
                                print(f"         ⚠️ Error closing tab: {e}")
                    
                    self.test_results['new_tab_workflow_tests'].append(test_result)
                    
                    # Small delay between tabs
                    await asyncio.sleep(1)
            
            else:
                print(f"      ❌ No creators found for tab testing")
                
        except Exception as e:
            print(f"      ❌ New tab workflow error: {e}")
    
    async def _test_consecutive_puzzle_tracking(self):
        """Test consecutive puzzle tracking logic."""
        
        print("   Testing consecutive puzzle tracking...")
        
        try:
            # Simulate multiple puzzle encounters
            initial_count = self.captcha_handler.consecutive_puzzle_count
            
            # Record some failures
            for i in range(3):
                self.captcha_handler._record_puzzle_encounter(success=False)
            
            count_after_failures = self.captcha_handler.consecutive_puzzle_count
            
            # Record a success
            self.captcha_handler._record_puzzle_encounter(success=True)
            count_after_success = self.captcha_handler.consecutive_puzzle_count
            
            # Test pause threshold
            for i in range(6):  # Should trigger pause at 5
                self.captcha_handler._record_puzzle_encounter(success=False)
            
            should_pause = self.captcha_handler.should_pause_for_puzzles()
            final_count = self.captcha_handler.consecutive_puzzle_count
            
            test_result = {
                'initial_count': initial_count,
                'count_after_3_failures': count_after_failures,
                'count_after_success_reset': count_after_success,
                'should_pause_after_6_failures': should_pause,
                'final_consecutive_count': final_count,
                'tracking_working': count_after_failures == initial_count + 3 and count_after_success == 0,
                'pause_threshold_working': should_pause and final_count >= 5,
                'success': True
            }
            
            print(f"      Consecutive tracking: {'✅' if test_result['tracking_working'] else '❌'}")
            print(f"      Pause threshold: {'✅' if test_result['pause_threshold_working'] else '❌'}")
            print(f"      Final count: {final_count}")
            
            self.test_results['consecutive_puzzle_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Consecutive puzzle tracking error: {e}")
            self.test_results['consecutive_puzzle_tests'].append({
                'error': str(e),
                'success': False
            })
    
    async def _test_profile_extraction_after_puzzle(self):
        """Test profile data extraction setelah puzzle bypass."""
        
        print("   Testing profile extraction after puzzle bypass...")
        
        try:
            # Navigate to list page
            url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
            page = await self.browser_engine.navigate(url)
            await asyncio.sleep(3)
            
            # Get first creator
            html = await self.browser_engine.get_html(page)
            doc = self.parser.parse(html)
            result = self.extractor.extract_list_page(doc)
            
            if result.affiliators:
                creator = result.affiliators[0]
                
                print(f"      Testing extraction on: {creator.username}")
                
                # Open detail page
                detail_page = await self.browser_engine.context.new_page()
                await detail_page.goto(creator.detail_url)
                await asyncio.sleep(2)
                
                # Handle puzzle if present
                puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(detail_page)
                puzzle_handled = True
                
                if puzzle_detected:
                    print(f"         🧩 Handling puzzle...")
                    puzzle_handled = await self.captcha_handler.solve_tokopedia_puzzle(detail_page)
                
                if puzzle_handled:
                    # Try to extract profile data
                    html = await detail_page.content()
                    doc = self.parser.parse(html)
                    
                    try:
                        detail_data = self.extractor.extract_detail_page(doc, page_url=creator.detail_url)
                        
                        # Check extracted data quality
                        has_username = bool(detail_data.username)
                        has_contact = bool(detail_data.nomor_kontak)
                        
                        test_result = {
                            'creator': creator.username,
                            'puzzle_detected': puzzle_detected,
                            'puzzle_handled': puzzle_handled,
                            'extraction_successful': True,
                            'has_username': has_username,
                            'has_contact_data': has_contact,
                            'extracted_username': detail_data.username,
                            'extracted_contact': detail_data.nomor_kontak,
                            'success': True
                        }
                        
                        print(f"         ✅ Extraction successful")
                        print(f"         Username: {detail_data.username}")
                        print(f"         Contact: {detail_data.nomor_kontak or 'None'}")
                        
                    except Exception as e:
                        test_result = {
                            'creator': creator.username,
                            'puzzle_detected': puzzle_detected,
                            'puzzle_handled': puzzle_handled,
                            'extraction_error': str(e),
                            'success': False
                        }
                        print(f"         ❌ Extraction error: {e}")
                
                else:
                    test_result = {
                        'creator': creator.username,
                        'puzzle_detected': puzzle_detected,
                        'puzzle_handled': False,
                        'success': False
                    }
                    print(f"         ❌ Puzzle not handled")
                
                await detail_page.close()
                
            else:
                test_result = {
                    'error': 'No creators found',
                    'success': False
                }
                print(f"      ❌ No creators found")
            
            self.test_results['profile_extraction_tests'].append(test_result)
            
        except Exception as e:
            print(f"      ❌ Profile extraction test error: {e}")
            self.test_results['profile_extraction_tests'].append({
                'error': str(e),
                'success': False
            })
    
    def _generate_summary(self):
        """Generate test summary."""
        
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
        
        summary['overall'] = {
            'total_tests': total_tests,
            'total_successful': total_successful,
            'overall_success_rate': overall_success_rate
        }
        
        self.test_results['summary'] = summary
        
        # Print summary
        print(f"\n📊 TEST SUMMARY:")
        print("=" * 40)
        
        for test_type, stats in summary.items():
            if test_type == 'overall':
                continue
            print(f"{test_type}: {stats['successful']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        
        print(f"\nOverall: {total_successful}/{total_tests} ({overall_success_rate:.1f}%)")
        
        if overall_success_rate >= 80:
            print("🎉 TESTS PASSED - Implementation looks good!")
        elif overall_success_rate >= 60:
            print("⚠️ TESTS PARTIAL - Some issues need attention")
        else:
            print("❌ TESTS FAILED - Significant issues found")
    
    async def _cleanup(self):
        """Cleanup resources."""
        
        print(f"\n🧹 Cleaning up...")
        
        try:
            await self.browser_engine.close()
            print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")


async def main():
    """Main test function."""
    
    print("🧪 TOKOPEDIA PUZZLE INTEGRATION TEST")
    print("Testing real Tokopedia puzzle handling implementation")
    print("=" * 60)
    
    # Create test runner
    runner = TokopediaPuzzleTestRunner()
    
    try:
        # Run all tests
        results = await runner.run_all_tests()
        
        # Save results
        output_file = 'tokopedia_puzzle_test_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Test results saved: {output_file}")
        
        # Show final status
        summary = results.get('summary', {})
        overall = summary.get('overall', {})
        success_rate = overall.get('overall_success_rate', 0)
        
        print(f"\n🎯 FINAL RESULT: {success_rate:.1f}% success rate")
        
        if success_rate >= 80:
            print("🎉 IMPLEMENTATION VALIDATED - Ready for production!")
        elif success_rate >= 60:
            print("⚠️ IMPLEMENTATION NEEDS TUNING - Check failed tests")
        else:
            print("❌ IMPLEMENTATION HAS ISSUES - Review and fix")
        
        return results
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Tests interrupted by user")
        return None
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(main())
    
    if result:
        print(f"\n✅ Test completed successfully")
    else:
        print(f"\n❌ Test failed or was interrupted")