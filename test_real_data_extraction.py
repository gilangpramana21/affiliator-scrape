#!/usr/bin/env python3
"""
Real Data Extraction Test untuk Tokopedia Affiliate Scraper.

Test lengkap untuk:
1. Navigate ke Tokopedia Affiliate Center
2. Handle Tokopedia puzzle dengan auto-refresh
3. Extract data affiliator dari list page
4. Navigate ke detail pages dengan new tab workflow
5. Handle premium CAPTCHA solving
6. Extract contact data (WhatsApp, Email)
7. Save hasil ke file

Usage: python test_real_data_extraction.py
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captcha_handler import CAPTCHAHandler
from src.core.premium_captcha_handler import create_premium_captcha_handler
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


class RealDataExtractionTest:
    """Test real data extraction dengan semua enhancements."""
    
    def __init__(self, use_premium_captcha: bool = True, max_creators: int = 10):
        self.use_premium_captcha = use_premium_captcha
        self.max_creators = max_creators
        
        # Load configs
        self.config = Configuration.from_file("config/config_jelajahi.json")
        
        # Setup components
        self.fingerprint_gen = FingerprintGenerator()
        self.browser_engine = BrowserEngine()
        self.parser = HTMLParser()
        self.extractor = TokopediaExtractor(self.parser)
        self.session_manager = SessionManager()
        
        # Setup CAPTCHA handler
        if use_premium_captcha:
            try:
                with open("config/premium_captcha_config.json", 'r') as f:
                    captcha_config = json.load(f)['captcha_config']
                self.captcha_handler = create_premium_captcha_handler(captcha_config)
                print("✅ Using Premium CAPTCHA Handler")
            except Exception as e:
                print(f"⚠️ Premium CAPTCHA config error: {e}")
                print("   Falling back to standard CAPTCHA handler")
                self.captcha_handler = CAPTCHAHandler(solver_type="manual")
        else:
            self.captcha_handler = CAPTCHAHandler(solver_type="manual")
            print("✅ Using Standard CAPTCHA Handler (manual)")
        
        # Results storage
        self.extracted_data = []
        self.extraction_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'puzzles_encountered': 0,
            'puzzles_solved': 0,
            'captchas_encountered': 0,
            'captchas_solved': 0,
            'contacts_found': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def run_extraction_test(self) -> Dict:
        """Run complete data extraction test."""
        
        print("🚀 REAL DATA EXTRACTION TEST")
        print("=" * 60)
        print(f"Target: Extract data from {self.max_creators} creators")
        print(f"CAPTCHA Handler: {'Premium' if self.use_premium_captcha else 'Standard'}")
        print(f"Base URL: {self.config.base_url}")
        
        self.extraction_stats['start_time'] = datetime.now()
        
        try:
            # Phase 1: Setup Browser
            await self._setup_browser()
            
            # Phase 2: Navigate to List Page
            await self._navigate_to_list_page()
            
            # Phase 3: Extract Creator List
            creators = await self._extract_creator_list()
            
            if not creators:
                print("❌ No creators found! Check configuration or cookies.")
                return self._generate_final_report()
            
            # Phase 4: Process Each Creator
            await self._process_creators(creators[:self.max_creators])
            
            # Phase 5: Generate Report
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Extraction test error: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_final_report()
        
        finally:
            self.extraction_stats['end_time'] = datetime.now()
            await self._cleanup()
    
    async def _setup_browser(self):
        """Setup browser dengan optimal fingerprint."""
        
        print("\n🌐 Setting up browser...")
        
        # Generate realistic fingerprint
        fingerprint = self.fingerprint_gen.generate()
        print(f"   Generated fingerprint: {fingerprint.browser} {fingerprint.browser_version}")
        
        # Launch browser (visible untuk monitoring)
        await self.browser_engine.launch(fingerprint, headless=False)
        print("   ✅ Browser launched (visible mode)")
        
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
            
            await self.browser_engine.context.add_cookies(cookie_list)
            print(f"   ✅ Loaded {len(cookies)} cookies")
        else:
            print("   ⚠️ No cookies loaded - may need authentication")
    
    async def _navigate_to_list_page(self):
        """Navigate ke Tokopedia Affiliate list page."""
        
        print("\n📋 Navigating to creator list page...")
        
        url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
        print(f"   URL: {url}")
        
        # Navigate
        main_page = await self.browser_engine.navigate(url)
        await asyncio.sleep(3)
        
        # Check for puzzle on main page
        puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(main_page)
        
        if puzzle_detected:
            print("   🧩 Tokopedia puzzle detected on list page")
            self.extraction_stats['puzzles_encountered'] += 1
            
            success = await self.captcha_handler.solve_tokopedia_puzzle(main_page)
            if success:
                print("   ✅ Puzzle solved successfully")
                self.extraction_stats['puzzles_solved'] += 1
            else:
                print("   ❌ Failed to solve puzzle")
                raise Exception("Cannot access list page due to puzzle")
        
        # Check for standard CAPTCHAs
        captcha_type = await self.captcha_handler.detect(main_page)
        if captcha_type:
            print(f"   🔒 CAPTCHA detected: {captcha_type}")
            self.extraction_stats['captchas_encountered'] += 1
            
            success = await self.captcha_handler.solve(main_page, captcha_type)
            if success:
                print("   ✅ CAPTCHA solved successfully")
                self.extraction_stats['captchas_solved'] += 1
            else:
                print("   ❌ Failed to solve CAPTCHA")
                raise Exception("Cannot access list page due to CAPTCHA")
        
        print("   ✅ List page loaded successfully")
        self.main_page = main_page
    
    async def _extract_creator_list(self):
        """Extract list of creators dari main page."""
        
        print("\n👥 Extracting creator list...")
        
        try:
            # Get page HTML
            html = await self.browser_engine.get_html(self.main_page)
            
            # Parse and extract
            doc = self.parser.parse(html)
            result = self.extractor.extract_list_page(doc)
            
            creators = result.affiliators
            print(f"   ✅ Found {len(creators)} creators")
            
            # Show sample creators
            if creators:
                print("   📋 Sample creators:")
                for i, creator in enumerate(creators[:3], 1):
                    print(f"      {i}. {creator.username}")
                    print(f"         Followers: {creator.pengikut:,}" if creator.pengikut else "         Followers: N/A")
                    print(f"         GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "         GMV: N/A")
            
            return creators
            
        except Exception as e:
            print(f"   ❌ Error extracting creator list: {e}")
            return []
    
    async def _process_creators(self, creators: List):
        """Process each creator dengan new tab workflow."""
        
        print(f"\n🔄 Processing {len(creators)} creators...")
        print("=" * 50)
        
        for i, creator in enumerate(creators, 1):
            print(f"\n👤 Creator {i}/{len(creators)}: {creator.username}")
            print(f"   Detail URL: {creator.detail_url}")
            
            self.extraction_stats['total_processed'] += 1
            
            try:
                # Process creator dengan new tab workflow
                extracted_data = await self._process_single_creator(creator)
                
                if extracted_data:
                    self.extracted_data.append(extracted_data)
                    self.extraction_stats['successful_extractions'] += 1
                    
                    # Check for contact data
                    if extracted_data.get('whatsapp') or extracted_data.get('email'):
                        self.extraction_stats['contacts_found'] += 1
                        print(f"   ✅ Contact data found!")
                    
                    print(f"   ✅ Extraction successful")
                else:
                    print(f"   ❌ Extraction failed")
                    self.extraction_stats['errors'] += 1
                
                # Small delay between creators
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error processing creator: {e}")
                self.extraction_stats['errors'] += 1
                continue
        
        print(f"\n✅ Finished processing {len(creators)} creators")
    
    async def _process_single_creator(self, creator) -> Optional[Dict]:
        """Process single creator dengan enhanced workflow."""
        
        detail_page = None
        
        try:
            # Check consecutive puzzle pause
            if self.captcha_handler.should_pause_for_puzzles():
                print("   ⏸️ Pausing due to consecutive puzzles...")
                await self.captcha_handler.wait_puzzle_pause()
            
            # Open detail page in new tab
            detail_page = await self.browser_engine.context.new_page()
            print("   📂 Opened new tab")
            
            # Navigate to detail page
            await detail_page.goto(creator.detail_url)
            await asyncio.sleep(3)
            print("   🌐 Navigated to detail page")
            
            # Handle Tokopedia puzzle
            puzzle_detected = await self.captcha_handler.detect_tokopedia_puzzle(detail_page)
            
            if puzzle_detected:
                print("   🧩 Tokopedia puzzle detected")
                self.extraction_stats['puzzles_encountered'] += 1
                
                success = await self.captcha_handler.solve_tokopedia_puzzle(detail_page)
                if success:
                    print("   ✅ Puzzle solved")
                    self.extraction_stats['puzzles_solved'] += 1
                else:
                    print("   ❌ Puzzle solving failed")
                    return None
            
            # Handle standard CAPTCHAs
            captcha_type = await self.captcha_handler.detect(detail_page)
            if captcha_type:
                print(f"   🔒 CAPTCHA detected: {captcha_type}")
                self.extraction_stats['captchas_encountered'] += 1
                
                success = await self.captcha_handler.solve(detail_page, captcha_type)
                if success:
                    print("   ✅ CAPTCHA solved")
                    self.extraction_stats['captchas_solved'] += 1
                else:
                    print("   ❌ CAPTCHA solving failed")
                    return None
            
            # Extract data from detail page
            html = await detail_page.content()
            doc = self.parser.parse(html)
            
            # Extract profile data
            detail_data = self.extractor.extract_detail_page(doc, page_url=creator.detail_url)
            
            # Extract contact data (WhatsApp, Email)
            contact_data = await self._extract_contact_data(detail_page, html)
            
            # Combine all data
            extracted_data = {
                'username': detail_data.username or creator.username,
                'kategori': detail_data.kategori or creator.kategori,
                'pengikut': detail_data.pengikut if detail_data.pengikut is not None else creator.pengikut,
                'gmv': detail_data.gmv if detail_data.gmv is not None else creator.gmv,
                'produk_terjual': detail_data.produk_terjual if detail_data.produk_terjual is not None else creator.produk_terjual,
                'rata_rata_tayangan': detail_data.rata_rata_tayangan if detail_data.rata_rata_tayangan is not None else creator.rata_rata_tayangan,
                'tingkat_interaksi': detail_data.tingkat_interaksi if detail_data.tingkat_interaksi is not None else creator.tingkat_interaksi,
                'nomor_kontak': detail_data.nomor_kontak,
                'whatsapp': contact_data.get('whatsapp'),
                'email': contact_data.get('email'),
                'detail_url': creator.detail_url,
                'scraped_at': datetime.now().isoformat(),
                'extraction_method': 'enhanced_new_tab_workflow'
            }
            
            # Show extracted data summary
            print(f"   📊 Data extracted:")
            print(f"      Username: {extracted_data['username']}")
            print(f"      Followers: {extracted_data['pengikut']:,}" if extracted_data['pengikut'] else "      Followers: N/A")
            print(f"      GMV: Rp{extracted_data['gmv']:,.0f}" if extracted_data['gmv'] else "      GMV: N/A")
            if extracted_data['whatsapp']:
                print(f"      📱 WhatsApp: {extracted_data['whatsapp']}")
            if extracted_data['email']:
                print(f"      📧 Email: {extracted_data['email']}")
            
            return extracted_data
            
        except Exception as e:
            print(f"   ❌ Error in single creator processing: {e}")
            return None
        
        finally:
            # Always close detail tab
            if detail_page:
                try:
                    await detail_page.close()
                    print("   🗑️ Tab closed")
                except Exception as e:
                    print(f"   ⚠️ Error closing tab: {e}")
    
    async def _extract_contact_data(self, page, html: str) -> Dict[str, Optional[str]]:
        """Extract contact data (WhatsApp, Email) dari detail page."""
        
        contact_data = {
            'whatsapp': None,
            'email': None
        }
        
        try:
            # Extract WhatsApp number
            import re
            
            whatsapp_patterns = [
                r'WhatsApp[:\s]*(\+?62\d{8,13})',
                r'WhatsApp[:\s]*(\d{8,13})',
                r'wa[:\s]*(\+?62\d{8,13})',
                r'wa[:\s]*(\d{8,13})',
                r'(8\d{9,12})',  # Indonesian mobile format
                r'(\+62\d{8,13})',
                r'(08\d{8,11})'
            ]
            
            for pattern in whatsapp_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    phone = matches[0]
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    # Normalize Indonesian phone
                    if phone.startswith('8') and len(phone) >= 10 and not phone.startswith('+'):
                        phone = '+62' + phone
                    elif phone.startswith('08'):
                        phone = '+62' + phone[1:]
                    elif phone.startswith('62') and not phone.startswith('+62'):
                        phone = '+' + phone
                    
                    if len(phone) >= 12 and len(phone) <= 16:
                        contact_data['whatsapp'] = phone
                        break
            
            # Extract Email
            email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
            matches = re.findall(email_pattern, html, re.IGNORECASE)
            
            if matches:
                exclude_domains = ['tokopedia.com', 'example.com', 'noreply', 'no-reply']
                
                for email in matches:
                    domain = email.split('@')[1].lower()
                    if not any(excluded in domain for excluded in exclude_domains):
                        contact_data['email'] = email.lower()
                        break
            
            return contact_data
            
        except Exception as e:
            logger.warning(f"Error extracting contact data: {e}")
            return contact_data
    
    def _generate_final_report(self) -> Dict:
        """Generate comprehensive final report."""
        
        # Calculate duration
        if self.extraction_stats['start_time'] and self.extraction_stats['end_time']:
            duration = self.extraction_stats['end_time'] - self.extraction_stats['start_time']
            duration_seconds = duration.total_seconds()
        else:
            duration_seconds = 0
        
        # Calculate success rates
        total_processed = self.extraction_stats['total_processed']
        successful = self.extraction_stats['successful_extractions']
        success_rate = (successful / total_processed * 100) if total_processed > 0 else 0
        
        puzzles_encountered = self.extraction_stats['puzzles_encountered']
        puzzles_solved = self.extraction_stats['puzzles_solved']
        puzzle_solve_rate = (puzzles_solved / puzzles_encountered * 100) if puzzles_encountered > 0 else 0
        
        captchas_encountered = self.extraction_stats['captchas_encountered']
        captchas_solved = self.extraction_stats['captchas_solved']
        captcha_solve_rate = (captchas_solved / captchas_encountered * 100) if captchas_encountered > 0 else 0
        
        contacts_found = self.extraction_stats['contacts_found']
        contact_rate = (contacts_found / successful * 100) if successful > 0 else 0
        
        # Generate report
        report = {
            'extraction_summary': {
                'total_processed': total_processed,
                'successful_extractions': successful,
                'success_rate': f"{success_rate:.1f}%",
                'contacts_found': contacts_found,
                'contact_rate': f"{contact_rate:.1f}%",
                'errors': self.extraction_stats['errors'],
                'duration_seconds': duration_seconds,
                'duration_formatted': str(duration) if duration_seconds > 0 else "N/A"
            },
            'puzzle_handling': {
                'puzzles_encountered': puzzles_encountered,
                'puzzles_solved': puzzles_solved,
                'puzzle_solve_rate': f"{puzzle_solve_rate:.1f}%"
            },
            'captcha_handling': {
                'captchas_encountered': captchas_encountered,
                'captchas_solved': captchas_solved,
                'captcha_solve_rate': f"{captcha_solve_rate:.1f}%",
                'handler_type': 'Premium' if self.use_premium_captcha else 'Standard'
            },
            'extracted_data': self.extracted_data,
            'performance_metrics': {
                'creators_per_minute': (successful / (duration_seconds / 60)) if duration_seconds > 0 else 0,
                'average_time_per_creator': (duration_seconds / total_processed) if total_processed > 0 else 0
            }
        }
        
        return report
    
    async def _cleanup(self):
        """Cleanup resources."""
        
        print(f"\n🧹 Cleaning up...")
        
        try:
            await self.browser_engine.close()
            print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")


async def main():
    """Main test function dengan options."""
    
    print("🚀 TOKOPEDIA AFFILIATE DATA EXTRACTION TEST")
    print("=" * 60)
    
    # Configuration options
    print("Configuration Options:")
    print("1. CAPTCHA Handler:")
    print("   p = Premium (CapSolver + 2Captcha + failover)")
    print("   s = Standard (manual solving)")
    
    print("2. Number of creators to test:")
    print("   Enter number (1-50, recommended: 5-10)")
    
    # Get user preferences
    captcha_choice = input("\nCAPTCHA Handler (p/s): ").strip().lower()
    use_premium = captcha_choice == 'p'
    
    try:
        max_creators = int(input("Number of creators (default 5): ").strip() or "5")
        max_creators = min(max(max_creators, 1), 50)  # Limit 1-50
    except ValueError:
        max_creators = 5
    
    print(f"\n📋 Test Configuration:")
    print(f"   CAPTCHA Handler: {'Premium' if use_premium else 'Standard'}")
    print(f"   Max Creators: {max_creators}")
    
    confirm = input("\nProceed with test? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Test cancelled.")
        return
    
    # Run extraction test
    test_runner = RealDataExtractionTest(
        use_premium_captcha=use_premium,
        max_creators=max_creators
    )
    
    try:
        results = await test_runner.run_extraction_test()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'real_extraction_results_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # Print final summary
        print(f"\n🎯 FINAL EXTRACTION RESULTS:")
        print("=" * 50)
        
        summary = results['extraction_summary']
        puzzle = results['puzzle_handling']
        captcha = results['captcha_handling']
        
        print(f"✅ Successful Extractions: {summary['successful_extractions']}/{summary['total_processed']} ({summary['success_rate']})")
        print(f"📱 Contact Data Found: {summary['contacts_found']} ({summary['contact_rate']})")
        print(f"🧩 Puzzles Solved: {puzzle['puzzles_solved']}/{puzzle['puzzles_encountered']} ({puzzle['puzzle_solve_rate']})")
        print(f"🔒 CAPTCHAs Solved: {captcha['captchas_solved']}/{captcha['captchas_encountered']} ({captcha['captcha_solve_rate']})")
        print(f"⏱️ Duration: {summary['duration_formatted']}")
        
        # Show sample extracted data
        if results['extracted_data']:
            print(f"\n📊 Sample Extracted Data:")
            for i, data in enumerate(results['extracted_data'][:3], 1):
                print(f"   {i}. {data['username']}")
                if data['pengikut']:
                    print(f"      Followers: {data['pengikut']:,}")
                if data['whatsapp']:
                    print(f"      📱 {data['whatsapp']}")
                if data['email']:
                    print(f"      📧 {data['email']}")
        
        print(f"\n💾 Full results saved: {output_file}")
        
        # Success assessment
        success_rate = float(summary['success_rate'].replace('%', ''))
        if success_rate >= 80:
            print(f"\n🎉 EXTRACTION TEST PASSED!")
            print(f"   High success rate indicates implementation is working well")
        elif success_rate >= 60:
            print(f"\n⚠️ EXTRACTION TEST PARTIAL SUCCESS")
            print(f"   Some issues detected, review logs for improvements")
        else:
            print(f"\n❌ EXTRACTION TEST NEEDS ATTENTION")
            print(f"   Low success rate indicates configuration or implementation issues")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())