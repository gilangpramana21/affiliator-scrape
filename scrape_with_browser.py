#!/usr/bin/env python3
"""
Tokopedia Affiliator Scraper - Browser Version
Handles CAPTCHA and Shadow DOM for contact extraction
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from playwright.async_api import async_playwright, Page, Browser
from src.anti_detection.browser_engine import BrowserEngine
from src.models.models import BrowserFingerprint


class TokopediaScraperWithBrowser:
    """Scraper using Playwright to handle CAPTCHA and Shadow DOM"""
    
    def __init__(self, cookie_file: str = "config/cookies.json", headless: bool = False):
        self.cookie_file = cookie_file
        self.headless = headless
        self.base_url = "https://affiliate-id.tokopedia.com"
        self.list_url = f"{self.base_url}/connection/creator"
        self.results = []
        self.browser_engine = None
        self.browser = None
        self.context = None
    
    async def setup_browser(self):
        """Setup browser with stealth and cookies"""
        print("🌐 Launching browser...")
        
        # Create simple fingerprint
        fingerprint = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            platform="MacIntel",
            browser="Chrome",
            browser_version="120.0.0.0",
            screen_resolution=(1920, 1080),
            viewport_size=(1400, 900),
            timezone="Asia/Jakarta",
            timezone_offset=-420,
            language="id-ID",
            languages=["id-ID", "id", "en-US", "en"],
            color_depth=24,
            pixel_ratio=2.0,
            hardware_concurrency=8,
            device_memory=8,
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"macOS"',
            plugins=["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
            webgl_vendor="Google Inc. (Apple)",
            webgl_renderer="ANGLE (Apple, Apple M1, OpenGL 4.1)"
        )
        
        # Launch browser
        self.browser_engine = BrowserEngine()
        self.browser = await self.browser_engine.launch(
            fingerprint=fingerprint,
            headless=self.headless
        )
        self.context = self.browser_engine.context
        
        # Load cookies if exists
        if Path(self.cookie_file).exists():
            print(f"🍪 Loading cookies from {self.cookie_file}...")
            await self.browser_engine.load_cookies_from_file(self.cookie_file)
        else:
            print("⚠️  No cookies file found, will need to login manually")
        
        print("✅ Browser ready!\n")
    
    async def wait_for_captcha(self, page: Page):
        """Wait for user to solve CAPTCHA manually"""
        print("\n" + "="*80)
        print("🔐 CAPTCHA DETECTED!")
        print("="*80)
        print("Silakan solve CAPTCHA secara manual di browser.")
        print("Script akan menunggu sampai CAPTCHA selesai...")
        print("="*80 + "\n")
        
        # Wait for CAPTCHA to disappear (check for specific elements)
        try:
            # Wait for page to be ready (adjust selector based on actual page)
            await page.wait_for_selector("div[class*='creator'], table[class*='creator']", timeout=300000)  # 5 min timeout
            print("✅ CAPTCHA solved! Continuing...\n")
        except Exception as e:
            print(f"⚠️  Timeout waiting for CAPTCHA: {e}")
            print("Continuing anyway...\n")
    
    async def extract_shadow_dom_contacts(self, page: Page) -> Dict[str, Optional[str]]:
        """Extract contacts from DOM - contacts are in a popover that needs to be opened"""
        print("      🔍 Extracting contacts from page...")
        
        # Try to click "Mengerti" button if exists (to reveal contacts)
        try:
            mengerti_button = await page.query_selector('button:has-text("Mengerti")')
            if mengerti_button:
                print("         📌 Clicking 'Mengerti' button...")
                await mengerti_button.click()
                await asyncio.sleep(2)
        except:
            pass
        
        # CRITICAL: Find and click ALL elements that might trigger contact info
        # The contacts are in a popover/modal that needs to be opened
        try:
            print("         🔍 Looking for contact info triggers...")
            
            # Strategy 1: Click any element containing "Info" or "Kontak"
            trigger_found = False
            
            # Try clicking elements with these texts
            trigger_texts = ["Info Kontak", "Kontak", "Info", "Contact"]
            
            for text in trigger_texts:
                try:
                    # Try different element types
                    selectors = [
                        f'button:has-text("{text}")',
                        f'div:has-text("{text}")',
                        f'span:has-text("{text}")',
                        f'a:has-text("{text}")',
                        f'[aria-label*="{text}"]',
                        f'[title*="{text}"]'
                    ]
                    
                    for selector in selectors:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            try:
                                # Check if element is visible
                                is_visible = await element.is_visible()
                                if is_visible:
                                    print(f"         📌 Found and clicking: {selector}")
                                    await element.click()
                                    trigger_found = True
                                    # Wait for popover to appear
                                    await asyncio.sleep(3)
                                    break
                            except:
                                continue
                        if trigger_found:
                            break
                except:
                    continue
                if trigger_found:
                    break
            
            if not trigger_found:
                print("         ⚠️  No contact info trigger found, trying to find by class...")
                
                # Strategy 2: Find elements with contact-related classes
                contact_classes = [
                    '[class*="contact"]',
                    '[class*="info"]',
                    '[class*="kontak"]',
                    '[data-testid*="contact"]',
                    '[data-testid*="info"]'
                ]
                
                for selector in contact_classes:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            try:
                                is_visible = await element.is_visible()
                                is_clickable = await element.evaluate("el => el.tagName === 'BUTTON' || el.tagName === 'A' || el.onclick !== null")
                                if is_visible and is_clickable:
                                    print(f"         📌 Found clickable element: {selector}")
                                    await element.click()
                                    trigger_found = True
                                    await asyncio.sleep(3)
                                    break
                            except:
                                continue
                        if trigger_found:
                            break
                    except:
                        continue
            
            if trigger_found:
                print("         ✅ Clicked contact info trigger, waiting for data...")
            else:
                print("         ⚠️  Could not find contact info trigger")
                
        except Exception as e:
            print(f"         ⚠️  Error finding contact trigger: {e}")
        
        # Scroll to make sure everything is loaded
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
        except:
            pass
        
        # Save HTML for debugging AFTER clicking
        try:
            html = await page.content()
            timestamp = datetime.now().strftime('%H%M%S')
            with open(f"debug_contact_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"         💾 Saved HTML to debug_contact_{timestamp}.html")
        except:
            pass
        
        # Take screenshot for debugging
        try:
            timestamp = datetime.now().strftime('%H%M%S')
            await page.screenshot(path=f"debug_contact_{timestamp}.png", full_page=True)
            print(f"         📸 Saved screenshot to debug_contact_{timestamp}.png")
        except:
            pass
        
        # JavaScript to extract contacts - VERY AGGRESSIVE approach
        js_extract = """
        () => {
            const results = { whatsapp: null, email: null, debug: '' };
            
            // Get ALL text from page
            const allText = document.body.innerText;
            results.debug = 'Page text length: ' + allText.length;
            
            // Strategy 1: Regex search in all text
            // WhatsApp patterns
            const waPatterns = [
                /WhatsApp[:\\s]+([0-9]{10,13})/gi,
                /WA[:\\s]+([0-9]{10,13})/gi,
                /wa[:\\s]+([0-9]{10,13})/gi,
                /([0-9]{10,13})/g  // Any 10-13 digit number
            ];
            
            for (const pattern of waPatterns) {
                const matches = allText.matchAll(pattern);
                for (const match of matches) {
                    if (match[1]) {
                        let phone = match[1].trim().replace(/[\\s-]/g, '');
                        // Only accept if starts with 8 or 0 (Indonesian numbers)
                        if (phone.startsWith('8') || phone.startsWith('0')) {
                            if (phone.startsWith('0')) {
                                phone = '+62' + phone.substring(1);
                            } else if (phone.startsWith('8')) {
                                phone = '+62' + phone;
                            }
                            results.whatsapp = phone;
                            break;
                        }
                    }
                }
                if (results.whatsapp) break;
            }
            
            // Email patterns
            const emailPattern = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/gi;
            const emailMatches = allText.matchAll(emailPattern);
            for (const match of emailMatches) {
                if (match[1]) {
                    const email = match[1].trim().toLowerCase();
                    // Skip common non-contact emails
                    if (!email.includes('example.com') && 
                        !email.includes('test.com') &&
                        !email.includes('tokopedia.com')) {
                        results.email = email;
                        break;
                    }
                }
            }
            
            return results;
        }
        """
        
        try:
            contacts = await page.evaluate(js_extract)
            
            if contacts.get('debug'):
                print(f"         🐛 Debug: {contacts['debug']}")
            
            if contacts.get('whatsapp'):
                print(f"         ✅ WhatsApp: {contacts['whatsapp']}")
            else:
                print(f"         ⚠️  WhatsApp not found")
                
            if contacts.get('email'):
                print(f"         ✅ Email: {contacts['email']}")
            else:
                print(f"         ⚠️  Email not found")
            
            # Remove debug from results
            if 'debug' in contacts:
                del contacts['debug']
            
            return contacts
        except Exception as e:
            print(f"         ❌ Error extracting contacts: {e}")
            return {'whatsapp': None, 'email': None}
    
    async def get_creator_count(self, page: Page) -> int:
        """Get number of creator rows"""
        try:
            # Wait for table to load
            await page.wait_for_selector("tbody tr", timeout=10000)
            rows = await page.query_selector_all("tbody tr")
            return len(rows)
        except:
            return 0
    
    async def scrape_list_page(self, page: Page) -> int:
        """Navigate to list page and return number of creators"""
        print("📄 Navigating to list page...")
        
        try:
            await page.goto(self.list_url, wait_until="networkidle", timeout=60000)
            
            # Check for CAPTCHA
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                'div[class*="captcha"]',
                'div[class*="puzzle"]'
            ]
            
            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    await self.wait_for_captcha(page)
                    break
            
            # Wait for content to load
            await asyncio.sleep(3)
            
            # Count creator rows
            count = await self.get_creator_count(page)
            
            print(f"   ✅ Found {count} creators\n")
            return count
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            return 0
    
    async def scrape_creator_by_index(self, page: Page, index: int) -> Dict:
        """Scrape creator by clicking on row index"""
        print(f"   📱 Clicking on creator row {index+1}...")
        
        try:
            # Get all rows
            rows = await page.query_selector_all("tbody tr")
            
            if index >= len(rows):
                print(f"      ❌ Row index {index} out of range")
                return {'whatsapp': None, 'email': None}
            
            # Click the row and wait for new page
            try:
                async with asyncio.timeout(10):  # 10 second timeout
                    async with page.context.expect_page() as new_page_info:
                        await rows[index].click()
                    detail_page = await new_page_info.value
            except asyncio.TimeoutError:
                print(f"      ⚠️  No new page opened (timeout)")
                return {'whatsapp': None, 'email': None}
            
            try:
                # Wait for page to load
                await detail_page.wait_for_load_state("networkidle", timeout=15000)
                
                # Wait a bit more for any delayed AJAX
                await asyncio.sleep(3)
                
                # Check for CAPTCHA
                captcha_selectors = [
                    'iframe[src*="recaptcha"]',
                    'iframe[src*="hcaptcha"]',
                    'div[class*="captcha"]',
                    'div[class*="puzzle"]'
                ]
                
                for selector in captcha_selectors:
                    if await detail_page.query_selector(selector):
                        await self.wait_for_captcha(detail_page)
                        break
                
                # Extract contacts
                contacts = await self.extract_shadow_dom_contacts(detail_page)
                
                return contacts
                
            finally:
                await detail_page.close()
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return {'whatsapp': None, 'email': None}
    
    async def scrape(self, max_creators: int = 3):
        """Main scraping function"""
        print("\n" + "="*80)
        print("🚀 TOKOPEDIA AFFILIATOR SCRAPER (BROWSER VERSION)")
        print("="*80)
        print("Features:")
        print("  ✅ Handles CAPTCHA (manual solving)")
        print("  ✅ Extracts from DOM")
        print("  ✅ Stealth mode enabled")
        print("="*80 + "\n")
        
        await self.setup_browser()
        
        # Create first page
        page = await self.context.new_page()
        
        total_scraped = 0
        total_with_contact = 0
        
        try:
            # Navigate to list page and get count
            creator_count = await self.scrape_list_page(page)
            
            if creator_count == 0:
                print("⚠️  No creators found\n")
                return
            
            # Limit to max_creators
            to_scrape = min(creator_count, max_creators)
            print(f"📊 Will scrape {to_scrape} out of {creator_count} creators\n")
            
            # Scrape each creator by index
            for i in range(to_scrape):
                print(f"\n[{i+1}/{to_scrape}] Creator #{i+1}")
                
                # Delay between requests
                if i > 0:
                    await asyncio.sleep(3)
                
                # Scrape by clicking row
                contacts = await self.scrape_creator_by_index(page, i)
                
                # Merge data
                result = {
                    'index': i,
                    **contacts,
                    'scraped_at': datetime.now().isoformat()
                }
                
                self.results.append(result)
                total_scraped += 1
                
                if contacts.get('whatsapp') or contacts.get('email'):
                    total_with_contact += 1
            
            # Save results
            self.save_results()
            
            # Summary
            print("\n" + "="*80)
            print("✅ SCRAPING COMPLETED")
            print("="*80)
            print(f"Total scraped: {total_scraped}")
            print(f"With contacts: {total_with_contact} ({total_with_contact/total_scraped*100:.1f}%)")
            print(f"Results: output/affiliators_browser.json")
            print("="*80 + "\n")
            
        finally:
            await page.close()
    
    def save_results(self):
        """Save results to JSON"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / "affiliators_browser.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(self.results)} results")
    
    async def cleanup(self):
        """Cleanup browser"""
        if self.browser_engine:
            await self.browser_engine.close()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape Tokopedia with Browser (CAPTCHA + Shadow DOM)')
    parser.add_argument(
        '--cookie-file',
        default='config/cookies.json',
        help='Path to cookies file (optional)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (default: visible browser for CAPTCHA)'
    )
    parser.add_argument(
        '--max-creators',
        type=int,
        default=3,
        help='Max creators to scrape'
    )
    
    args = parser.parse_args()
    
    scraper = TokopediaScraperWithBrowser(
        cookie_file=args.cookie_file,
        headless=args.headless
    )
    
    try:
        await scraper.scrape(max_creators=args.max_creators)
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
