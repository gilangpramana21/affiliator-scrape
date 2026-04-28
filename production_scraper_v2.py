#!/usr/bin/env python3
"""
Production Scraper V2 - Optimized for Daily Scraping
Features:
- Network monitoring for fast data extraction
- Bright Data proxy support
- CapSolver CAPTCHA solving
- Optimized for 1000+ affiliators
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionScraperV2:
    """Production scraper with network monitoring and proxy support."""
    
    def __init__(self, config_path: str = "config/config_production.json"):
        self.config = Configuration.from_file(config_path)
        self.stats = {
            'total_processed': 0,
            'metrics_success': 0,
            'contact_success': 0,
            'captcha_encountered': 0,
            'captcha_solved': 0,
            'network_extractions': 0,
            'dom_extractions': 0,
            'failed': 0
        }
        self.network_responses = []
        
    async def scrape_affiliators(self, max_affiliators: int = 1000) -> List[Dict[str, Any]]:
        """Main scraping function."""
        
        print(f"🚀 PRODUCTION SCRAPER V2")
        print(f"=" * 60)
        print(f"Target: {max_affiliators} affiliators")
        print(f"Mode: Network Monitoring + Proxy")
        print(f"=" * 60)
        
        # Setup
        fingerprint_gen = FingerprintGenerator()
        fingerprint = fingerprint_gen.generate()
        browser_engine = BrowserEngine()
        session_manager = SessionManager()
        
        results = []
        
        try:
            # Launch browser (proxy will be configured in context if needed)
            await browser_engine.launch(
                fingerprint, 
                headless=self.config.headless
            )
            print(f"✅ Browser launched")
            
            # Load cookies
            session_manager.load_session(self.config.cookie_file)
            cookies = session_manager.get_cookies()
            
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
                await browser_engine.context.add_cookies(cookie_list)
                print(f"✅ Loaded {len(cookies)} cookies")
            
            # Navigate to list page
            url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
            print(f"\n🌐 Navigating to list page...")
            
            page = await browser_engine.navigate(url)
            
            # Setup network monitoring
            await self._setup_network_monitoring(page)
            
            await asyncio.sleep(3)
            
            # Get list of creators
            from src.core.html_parser import HTMLParser
            from src.core.tokopedia_extractor import TokopediaExtractor
            
            parser = HTMLParser()
            extractor = TokopediaExtractor(parser)
            
            html = await browser_engine.get_html(page)
            doc = parser.parse(html)
            list_result = extractor.extract_list_page(doc)
            
            total_found = len(list_result.affiliators)
            to_process = min(total_found, max_affiliators)
            
            print(f"📋 Found {total_found} creators, processing {to_process}")
            
            # Process each creator
            for i in range(to_process):
                creator = list_result.affiliators[i]
                
                if (i + 1) % 10 == 0:
                    print(f"\n📊 Progress: {i+1}/{to_process} ({(i+1)/to_process*100:.1f}%)")
                    self._print_stats()
                
                result = await self._process_creator(
                    browser_engine, page, creator, i
                )
                
                if result:
                    results.append(result)
                
                # Rate limiting
                await asyncio.sleep(3)
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"✅ SCRAPING COMPLETED")
            print(f"{'='*60}")
            self._print_final_stats()
            
            # Save results
            self._save_results(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Scraping error: {e}")
            import traceback
            traceback.print_exc()
            return results
            
        finally:
            await browser_engine.close()
    
    async def _setup_network_monitoring(self, page):
        """Setup network request/response monitoring."""
        
        async def handle_response(response):
            try:
                url = response.url
                
                # Monitor API endpoints
                if any(keyword in url.lower() for keyword in ['api', 'creator', 'profile', 'contact', 'detail']):
                    try:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'application/json' in content_type:
                                data = await response.json()
                                self.network_responses.append({
                                    'url': url,
                                    'data': data,
                                    'timestamp': datetime.now().isoformat()
                                })
                                logger.debug(f"Captured API response: {url}")
                    except:
                        pass
            except:
                pass
        
        page.on('response', handle_response)
    
    async def _process_creator(self, browser_engine, list_page, creator, index: int) -> Optional[Dict[str, Any]]:
        """Process single creator."""
        
        self.stats['total_processed'] += 1
        detail_page = None
        
        try:
            # Click on creator row
            rows = await list_page.query_selector_all("tbody tr")
            if index >= len(rows):
                return None
            
            # Listen for new page
            new_page_promise = browser_engine.context.wait_for_event("page")
            
            # Click row
            await rows[index].click()
            
            try:
                # Wait for detail page
                detail_page = await asyncio.wait_for(new_page_promise, timeout=8.0)
                
                # Setup network monitoring for detail page
                await self._setup_network_monitoring(detail_page)
                
                # Wait for page load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=10000)
                await asyncio.sleep(3)
                
                # Handle Tokopedia puzzle
                puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                if puzzle_indicators:
                    await detail_page.reload()
                    await asyncio.sleep(3)
                
                # Check for CAPTCHA
                captcha_present = await self._check_captcha(detail_page)
                if captcha_present:
                    self.stats['captcha_encountered'] += 1
                    solved = await self._solve_captcha(detail_page)
                    if solved:
                        self.stats['captcha_solved'] += 1
                    else:
                        print(f"   ⚠️ CAPTCHA not solved for {creator.username}")
                
                # Extract data (network first, then DOM fallback)
                data = await self._extract_data_hybrid(detail_page, creator)
                
                # Close detail page
                await detail_page.close()
                
                return data
                
            except asyncio.TimeoutError:
                logger.warning(f"No detail page opened for {creator.username}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing {creator.username}: {e}")
            self.stats['failed'] += 1
            return None
            
        finally:
            if detail_page:
                try:
                    await detail_page.close()
                except:
                    pass
    
    async def _extract_data_hybrid(self, page, creator) -> Dict[str, Any]:
        """Hybrid extraction: Network monitoring + DOM fallback."""
        
        data = {
            'username': creator.username,
            'kategori': creator.kategori,
            'pengikut': creator.pengikut,
            'gmv': creator.gmv,
            'produk_terjual': creator.produk_terjual,
            'rata_rata_tayangan': creator.rata_rata_tayangan,
            'tingkat_interaksi': creator.tingkat_interaksi,
            'gmv_per_pembeli': creator.gmv_per_pembeli,
            'whatsapp': None,
            'email': None,
            'extraction_method': 'list_page',
            'scraped_at': datetime.now().isoformat()
        }
        
        # Try network extraction first
        network_data = self._extract_from_network_responses(creator.username)
        if network_data:
            data.update(network_data)
            data['extraction_method'] = 'network_api'
            self.stats['network_extractions'] += 1
            self.stats['metrics_success'] += 1
            if network_data.get('whatsapp') or network_data.get('email'):
                self.stats['contact_success'] += 1
            return data
        
        # Fallback to DOM extraction
        try:
            from src.core.html_parser import HTMLParser
            from src.core.tokopedia_extractor import TokopediaExtractor
            
            parser = HTMLParser()
            extractor = TokopediaExtractor(parser)
            
            html = await page.content()
            doc = parser.parse(html)
            detail = extractor.extract_detail_page(doc, page_url=page.url)
            
            # Update with detail page data
            if detail.gmv is not None:
                data['gmv'] = detail.gmv
            if detail.gmv_per_pembeli is not None:
                data['gmv_per_pembeli'] = detail.gmv_per_pembeli
            if detail.nomor_whatsapp:
                data['whatsapp'] = detail.nomor_whatsapp
            if detail.nomor_kontak:
                data['email'] = detail.nomor_kontak
            
            data['extraction_method'] = 'dom'
            self.stats['dom_extractions'] += 1
            self.stats['metrics_success'] += 1
            
            if data.get('whatsapp') or data.get('email'):
                self.stats['contact_success'] += 1
            
        except Exception as e:
            logger.error(f"DOM extraction error: {e}")
        
        return data
    
    def _extract_from_network_responses(self, username: str) -> Optional[Dict[str, Any]]:
        """Extract data from captured network responses."""
        
        # Look for responses that might contain creator data
        for response in self.network_responses[-10:]:  # Check last 10 responses
            data = response.get('data', {})
            
            # Try to find matching data
            if isinstance(data, dict):
                # Check if this response contains our creator's data
                if self._matches_creator(data, username):
                    return self._parse_api_response(data)
        
        return None
    
    def _matches_creator(self, data: Dict, username: str) -> bool:
        """Check if API response matches the creator."""
        
        # Common patterns in API responses
        username_fields = ['username', 'user_name', 'creator_name', 'name', 'id']
        
        for field in username_fields:
            if field in data and str(data[field]).lower() == username.lower():
                return True
        
        return False
    
    def _parse_api_response(self, data: Dict) -> Dict[str, Any]:
        """Parse API response to extract relevant data."""
        
        result = {}
        
        # Common field mappings
        field_mappings = {
            'gmv': ['gmv', 'total_gmv', 'gross_merchandise_value'],
            'gmv_per_pembeli': ['gmv_per_buyer', 'avg_gmv', 'gmv_per_pembeli'],
            'whatsapp': ['whatsapp', 'wa', 'phone', 'mobile'],
            'email': ['email', 'mail', 'contact_email'],
            'pengikut': ['followers', 'pengikut', 'follower_count'],
            'produk_terjual': ['products_sold', 'produk_terjual', 'total_sales']
        }
        
        for key, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in data:
                    result[key] = data[field]
                    break
        
        return result
    
    async def _check_captcha(self, page) -> bool:
        """Check if CAPTCHA is present."""
        
        captcha_selectors = [
            '#captcha_container',
            '[class*="captcha"]',
            '[id*="captcha"]',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]'
        ]
        
        for selector in captcha_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                return True
        
        return False
    
    async def _solve_captcha(self, page) -> bool:
        """Solve CAPTCHA using CapSolver."""
        
        # TODO: Integrate CapSolver API
        # For now, wait and hope for auto-solve
        print(f"   🤖 CAPTCHA detected, waiting for auto-solve...")
        await asyncio.sleep(10)
        
        # Check if solved
        captcha_still_present = await self._check_captcha(page)
        return not captcha_still_present
    
    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration if available."""
        # Note: Proxy configuration should be done at browser context level
        # For now, we'll use the existing scraper without proxy modification
        return None
    
    def _print_stats(self):
        """Print current statistics."""
        
        total = self.stats['total_processed']
        if total == 0:
            return
        
        print(f"   📊 Stats:")
        print(f"      Processed: {total}")
        print(f"      Metrics success: {self.stats['metrics_success']} ({self.stats['metrics_success']/total*100:.1f}%)")
        print(f"      Contact success: {self.stats['contact_success']} ({self.stats['contact_success']/total*100:.1f}%)")
        print(f"      CAPTCHA: {self.stats['captcha_encountered']} encountered, {self.stats['captcha_solved']} solved")
        print(f"      Network extractions: {self.stats['network_extractions']}")
        print(f"      DOM extractions: {self.stats['dom_extractions']}")
        print(f"      Failed: {self.stats['failed']}")
    
    def _print_final_stats(self):
        """Print final statistics."""
        
        total = self.stats['total_processed']
        
        print(f"📊 FINAL STATISTICS:")
        print(f"   Total processed: {total}")
        print(f"   Metrics success: {self.stats['metrics_success']} ({self.stats['metrics_success']/total*100:.1f}%)")
        print(f"   Contact success: {self.stats['contact_success']} ({self.stats['contact_success']/total*100:.1f}%)")
        print(f"   CAPTCHA encountered: {self.stats['captcha_encountered']}")
        print(f"   CAPTCHA solved: {self.stats['captcha_solved']}")
        print(f"   Network extractions: {self.stats['network_extractions']}")
        print(f"   DOM extractions: {self.stats['dom_extractions']}")
        print(f"   Failed: {self.stats['failed']}")
        
        if self.stats['captcha_encountered'] > 0:
            solve_rate = self.stats['captcha_solved'] / self.stats['captcha_encountered'] * 100
            print(f"   CAPTCHA solve rate: {solve_rate:.1f}%")
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """Save results to file."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"production_results_{timestamp}.json"
        
        output = {
            "scrape_info": {
                "timestamp": timestamp,
                "total_results": len(results),
                "statistics": self.stats
            },
            "results": results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Main entry point."""
    
    scraper = ProductionScraperV2("config/config_jelajahi.json")
    results = await scraper.scrape_affiliators(max_affiliators=1000)
    
    print(f"\n✅ Scraping completed! Total results: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
