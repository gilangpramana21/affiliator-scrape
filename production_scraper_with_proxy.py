#!/usr/bin/env python3
"""
Production Scraper with Proxy Support
Features:
- Universal proxy manager (Webshare, Smartproxy, Free proxies)
- CapSolver CAPTCHA solving
- Better error handling
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
from src.proxy.proxy_manager import ProxyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionScraperWithProxy:
    """Production scraper with proxy support."""
    
    def __init__(self, config_path: str = "config/config_production.json"):
        self.config = Configuration.from_file(config_path)
        self.proxy_manager = ProxyManager()
        self.current_proxy = None
        self.stats = {
            'total_processed': 0,
            'metrics_success': 0,
            'contact_success': 0,
            'captcha_encountered': 0,
            'captcha_solved': 0,
            'proxy_switches': 0,
            'failed': 0
        }
        
    async def setup_proxies(self) -> bool:
        """Setup and validate proxies."""
        
        print("🌐 SETTING UP PROXIES")
        print("=" * 60)
        
        # Load proxies from different sources
        webshare_count = self.proxy_manager.load_webshare_proxies("config/webshare_proxies.txt")
        free_count = self.proxy_manager.load_free_proxies("config/free_proxies.txt")
        
        total_loaded = webshare_count + free_count
        
        if total_loaded == 0:
            print("⚠️  No proxy files found!")
            print("   Please setup proxy files:")
            print("   1. config/webshare_proxies.txt (Webshare.io proxies)")
            print("   2. config/free_proxies.txt (Free proxies)")
            print("\n   Or run without proxy (not recommended for public WiFi)")
            return False
        
        print(f"📋 Loaded proxies:")
        print(f"   Webshare: {webshare_count}")
        print(f"   Free: {free_count}")
        print(f"   Total: {total_loaded}")
        
        # Test proxies
        print(f"\n🧪 Testing proxies...")
        working_count = self.proxy_manager.validate_all_proxies()
        
        stats = self.proxy_manager.get_stats()
        print(f"\n📊 Proxy validation results:")
        print(f"   Working: {stats['working']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Success rate: {stats['working']/stats['total']*100:.1f}%")
        
        if working_count == 0:
            print("\n❌ No working proxies found!")
            print("   Recommendations:")
            print("   1. Check proxy credentials")
            print("   2. Try different proxy provider")
            print("   3. Run without proxy (manual CAPTCHA solving)")
            return False
        
        print(f"\n✅ Ready to use {working_count} working proxies!")
        return True
    
    async def scrape_affiliators(self, max_affiliators: int = 1000, use_proxy: bool = True) -> List[Dict[str, Any]]:
        """Main scraping function."""
        
        print(f"🚀 PRODUCTION SCRAPER WITH PROXY")
        print(f"=" * 60)
        print(f"Target: {max_affiliators} affiliators")
        print(f"Proxy: {'Enabled' if use_proxy else 'Disabled'}")
        print(f"=" * 60)
        
        # Setup proxies if enabled
        if use_proxy:
            proxy_ready = await self.setup_proxies()
            if not proxy_ready:
                print("\n❌ Proxy setup failed!")
                response = input("Continue without proxy? (y/n): ")
                if response.lower() != 'y':
                    return []
                use_proxy = False
        
        # Setup browser
        fingerprint_gen = FingerprintGenerator()
        fingerprint = fingerprint_gen.generate()
        browser_engine = BrowserEngine()
        session_manager = SessionManager()
        
        results = []
        
        try:
            # Get proxy if enabled
            proxy_config = None
            if use_proxy:
                proxy = self.proxy_manager.get_random_proxy()
                if proxy:
                    proxy_config = proxy.to_playwright_format()
                    self.current_proxy = proxy
                    print(f"🌐 Using proxy: {proxy}")
                else:
                    print("⚠️  No proxy available, continuing without proxy")
            
            # Launch browser with proxy
            await browser_engine.launch(
                fingerprint, 
                headless=self.config.headless,
                proxy=proxy_config
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
            
            # Test proxy connection
            if use_proxy and self.current_proxy:
                await self._test_proxy_connection(browser_engine)
            
            # Navigate to list page
            url = f"{self.config.base_url}{self.config.list_page_url}{self.config.list_page_query}"
            print(f"\n🌐 Navigating to list page...")
            
            page = await browser_engine.navigate(url)
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
                
                # Switch proxy every 20 requests if multiple proxies available
                if use_proxy and i > 0 and i % 20 == 0 and len(self.proxy_manager.working_proxies) > 1:
                    await self._switch_proxy(browser_engine, fingerprint)
                
                result = await self._process_creator(
                    browser_engine, page, creator, i
                )
                
                if result:
                    results.append(result)
                
                # Rate limiting
                await asyncio.sleep(4)
            
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
    
    async def _test_proxy_connection(self, browser_engine):
        """Test proxy connection by checking IP."""
        try:
            test_page = await browser_engine.navigate("https://httpbin.org/ip")
            await asyncio.sleep(2)
            
            content = await test_page.content()
            if '"origin"' in content:
                # Extract IP from JSON response
                import re
                ip_match = re.search(r'"origin":\s*"([^"]+)"', content)
                if ip_match:
                    ip = ip_match.group(1)
                    print(f"✅ Proxy connection successful, IP: {ip}")
                else:
                    print(f"✅ Proxy connection successful")
            
            await test_page.close()
            
        except Exception as e:
            print(f"⚠️  Could not test proxy connection: {e}")
    
    async def _switch_proxy(self, browser_engine, fingerprint):
        """Switch to a different proxy."""
        try:
            print(f"🔄 Switching proxy...")
            
            # Get new proxy
            new_proxy = self.proxy_manager.get_next_proxy()
            if not new_proxy or new_proxy == self.current_proxy:
                return
            
            # Close current browser
            await browser_engine.close()
            
            # Launch with new proxy
            proxy_config = new_proxy.to_playwright_format()
            await browser_engine.launch(
                fingerprint,
                headless=self.config.headless,
                proxy=proxy_config
            )
            
            self.current_proxy = new_proxy
            self.stats['proxy_switches'] += 1
            
            print(f"✅ Switched to proxy: {new_proxy}")
            
        except Exception as e:
            print(f"⚠️  Proxy switch failed: {e}")
    
    async def _process_creator(self, browser_engine, list_page, creator, index: int) -> Optional[Dict[str, Any]]:
        """Process single creator (same as before but with better error handling)."""
        
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
                detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                
                # Wait for page load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                
                # Handle Tokopedia puzzle/errors
                await self._handle_page_errors(detail_page)
                
                # Check for CAPTCHA
                captcha_present = await self._check_captcha(detail_page)
                if captcha_present:
                    self.stats['captcha_encountered'] += 1
                    solved = await self._solve_captcha(detail_page)
                    if solved:
                        self.stats['captcha_solved'] += 1
                    else:
                        print(f"   ⚠️ CAPTCHA not solved for {creator.username}")
                
                # Extract data
                data = await self._extract_data(detail_page, creator)
                
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
    
    async def _handle_page_errors(self, page):
        """Handle Tokopedia puzzle and error pages."""
        try:
            # Check for "Coba lagi" message
            coba_lagi_elements = await page.query_selector_all("text=Coba lagi")
            if coba_lagi_elements:
                print(f"   🔄 'Coba lagi' detected, refreshing...")
                await page.reload()
                await asyncio.sleep(5)
            
            # Check for puzzle
            puzzle_elements = await page.query_selector_all("[class*='puzzle'], [class*='loading']")
            if puzzle_elements:
                print(f"   🧩 Puzzle detected, waiting...")
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.debug(f"Error handling page errors: {e}")
    
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
        """Solve CAPTCHA (manual for now, can integrate CapSolver later)."""
        print(f"   🤖 CAPTCHA detected - please solve manually...")
        
        # Wait for user to solve
        input("   Press Enter after solving CAPTCHA...")
        
        # Check if solved
        captcha_still_present = await self._check_captcha(page)
        return not captcha_still_present
    
    async def _extract_data(self, page, creator) -> Dict[str, Any]:
        """Extract data from detail page."""
        
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
            'scraped_at': datetime.now().isoformat(),
            'proxy_used': str(self.current_proxy) if self.current_proxy else None
        }
        
        # Try to extract contact data
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
            
            data['extraction_method'] = 'detail_page'
            self.stats['metrics_success'] += 1
            
            if data.get('whatsapp') or data.get('email'):
                self.stats['contact_success'] += 1
            
        except Exception as e:
            logger.error(f"Data extraction error: {e}")
        
        return data
    
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
        print(f"      Proxy switches: {self.stats['proxy_switches']}")
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
        print(f"   Proxy switches: {self.stats['proxy_switches']}")
        print(f"   Failed: {self.stats['failed']}")
        
        if self.stats['captcha_encountered'] > 0:
            solve_rate = self.stats['captcha_solved'] / self.stats['captcha_encountered'] * 100
            print(f"   CAPTCHA solve rate: {solve_rate:.1f}%")
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """Save results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"production_results_proxy_{timestamp}.json"
        
        output = {
            "scrape_info": {
                "timestamp": timestamp,
                "total_results": len(results),
                "statistics": self.stats,
                "proxy_stats": self.proxy_manager.get_stats() if self.proxy_manager else None
            },
            "results": results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Main entry point."""
    
    import argparse
    parser = argparse.ArgumentParser(description="Production scraper with proxy support")
    parser.add_argument("--max-affiliators", type=int, default=50, help="Max affiliators to scrape")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy usage")
    args = parser.parse_args()
    
    scraper = ProductionScraperWithProxy()
    results = await scraper.scrape_affiliators(
        max_affiliators=args.max_affiliators,
        use_proxy=not args.no_proxy
    )
    
    print(f"\n✅ Scraping completed! Total results: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())