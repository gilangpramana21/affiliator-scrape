#!/usr/bin/env python3
"""
Tokopedia Scraper - Full Data Extraction with Excel Export
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import re

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from playwright.async_api import Page
from src.anti_detection.browser_engine import BrowserEngine
from src.models.models import BrowserFingerprint
from src.core.error_analyzer import ErrorAnalyzer


class FullDataScraper:
    """Scraper lengkap dengan export ke Excel"""
    
    def __init__(self, cookie_file: str = "config/cookies.json"):
        self.cookie_file = cookie_file
        self.base_url = "https://affiliate-id.tokopedia.com"
        self.list_url = f"{self.base_url}/connection/creator"
        self.results = []
        self.browser_engine = None
        self.error_analyzer = ErrorAnalyzer()  # Add error analyzer
    
    async def setup_browser(self):
        """Setup browser"""
        print("🌐 Launching browser (visible mode)...")
        
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
        
        self.browser_engine = BrowserEngine()
        self.browser = await self.browser_engine.launch(
            fingerprint=fingerprint,
            headless=False
        )
        self.context = self.browser_engine.context
        
        if Path(self.cookie_file).exists():
            print(f"🍪 Loading cookies from {self.cookie_file}...")
            await self.browser_engine.load_cookies_from_file(self.cookie_file)
        
        print("✅ Browser ready!\n")
    
    async def check_and_handle_coba_lagi(self, page: Page, location: str, max_retries: int = 3) -> bool:
        """
        Check for 'Coba lagi' blocking page and click the button to retry.
        
        Args:
            page: Playwright page object
            location: Description of where we are (for logging)
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if page is OK (no blocking), False if still blocked after retries
        """
        for attempt in range(max_retries):
            # Get page HTML
            html = await page.content()
            
            # Check for "coba lagi" blocking page
            if self.error_analyzer.detect_coba_lagi(html):
                print(f"\n⚠️  'Coba lagi' blocking page detected at {location}")
                
                if attempt < max_retries - 1:
                    print(f"   🔄 Clicking 'Coba lagi' button... (attempt {attempt + 1}/{max_retries})")
                    
                    # Try to find and click "Coba lagi" button
                    button_clicked = False
                    
                    # Try different selectors for the button
                    button_selectors = [
                        'button:has-text("Coba lagi")',
                        'button:has-text("Try again")',
                        'button:has-text("Coba Lagi")',
                        'button:has-text("COBA LAGI")',
                        'a:has-text("Coba lagi")',
                        'a:has-text("Try again")',
                        '[class*="retry"]',
                        '[class*="coba-lagi"]',
                    ]
                    
                    for selector in button_selectors:
                        try:
                            button = await page.query_selector(selector)
                            if button:
                                print(f"   ✓ Found button with selector: {selector}")
                                await button.click()
                                button_clicked = True
                                await asyncio.sleep(3)  # Wait for page to reload
                                await page.wait_for_load_state("networkidle", timeout=30000)
                                break
                        except Exception as e:
                            continue
                    
                    # If button not found, try page reload as fallback
                    if not button_clicked:
                        print(f"   ⚠️  'Coba lagi' button not found, trying page reload...")
                        await page.reload(wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(2)
                else:
                    print(f"   ❌ Still blocked after {max_retries} attempts")
                    print(f"   💡 Possible causes:")
                    print(f"      - Cookies expired or invalid")
                    print(f"      - IP blocked or low reputation")
                    print(f"      - Too many requests")
                    return False
            else:
                # Page is OK
                if attempt > 0:
                    print(f"   ✅ Page loaded successfully after {attempt} retry(ies)")
                return True
        
        return False
    
    async def wait_for_manual_captcha(self, page: Page, location: str):
        """Tunggu user solve CAPTCHA manual"""
        print("\n" + "="*80)
        print(f"⏸️  PAUSE - CAPTCHA {location.upper()}")
        print("="*80)
        print(f"Silakan solve CAPTCHA di {location} secara manual.")
        print("Script akan menunggu sampai Anda selesai...")
        print("")
        print("Tekan ENTER di terminal ini setelah CAPTCHA selesai dan halaman sudah load.")
        print("="*80 + "\n")
        
        input(">>> Tekan ENTER setelah CAPTCHA selesai: ")
        
        print("\n✅ Melanjutkan scraping...\n")
        await asyncio.sleep(2)
    
    async def load_more_creators(self, page: Page, target_count: int = 100):
        """Load lebih banyak creator dengan scroll/pagination"""
        print(f"📊 Loading up to {target_count} creators...")
        
        loaded_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        while loaded_count < target_count and scroll_attempts < max_scroll_attempts:
            # Get current count
            rows = await page.query_selector_all("tbody tr")
            current_count = len(rows)
            
            if current_count >= target_count:
                print(f"✅ Loaded {current_count} creators (target: {target_count})")
                break
            
            if current_count > loaded_count:
                print(f"   📈 Loaded {current_count} creators so far...")
                loaded_count = current_count
            
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Check for "Load More" button
            load_more_button = await page.query_selector('button:has-text("Muat lebih banyak"), button:has-text("Load more")')
            if load_more_button:
                try:
                    await load_more_button.click()
                    print(f"   🔄 Clicked 'Load More' button")
                    await asyncio.sleep(3)
                except:
                    pass
            
            scroll_attempts += 1
        
        final_rows = await page.query_selector_all("tbody tr")
        final_count = len(final_rows)
        print(f"✅ Final count: {final_count} creators loaded\n")
        
        return final_count
    
    async def extract_list_data(self, row, index: int) -> Dict:
        """Extract data dari list page (row di table)"""
        try:
            data = {
                'index': index,
                'username': None,
                'shop_name': None,
                'level': None,
                'category': None,
                'followers': None,
                'gmv': None,
                'products_sold': None,
                'avg_views': None,
            }
            
            # Get all text from row
            row_text = await row.text_content()
            
            # Extract username (biasanya di awal)
            username_el = await row.query_selector('[class*="username"], [class*="creator"], .text-body-m-medium')
            if username_el:
                data['username'] = (await username_el.text_content()).strip()
            
            # Extract level (Lv. X)
            level_match = re.search(r'Lv\.\s*(\d+)', row_text)
            if level_match:
                data['level'] = int(level_match.group(1))
            
            # Extract followers (format: 268,1 rb atau 1 jt)
            followers_match = re.search(r'([\d,\.]+)\s*(rb|jt|k|m)', row_text, re.IGNORECASE)
            if followers_match:
                data['followers'] = followers_match.group(0)
            
            # Extract GMV
            gmv_match = re.search(r'Rp([\d,\.]+[KMkm]?)', row_text)
            if gmv_match:
                data['gmv'] = f"Rp{gmv_match.group(1)}"
            
            # Extract products sold
            sold_match = re.search(r'([\d,\.]+)\s*(rb|k)?\s*Produk terjual', row_text, re.IGNORECASE)
            if sold_match:
                data['products_sold'] = sold_match.group(0).replace('Produk terjual', '').strip()
            
            return data
            
        except Exception as e:
            print(f"      ⚠️  Error extracting list data: {e}")
            return {
                'index': index,
                'username': None,
                'shop_name': None,
                'level': None,
                'category': None,
                'followers': None,
                'gmv': None,
                'products_sold': None,
                'avg_views': None,
            }
    
    async def extract_detail_data(self, page: Page) -> Dict:
        """Extract data lengkap dari detail page"""
        try:
            data = {
                'username': None,
                'display_name': None,
                'shop_name': None,
                'level': None,
                'rating': None,
                'category': None,
                'followers': None,
                'bio': None,
                'gmv': None,
                'products_sold': None,
                'avg_views': None,
                'gender_male': None,
                'gender_female': None,
                'age_group': None,
            }
            
            # Get all text
            all_text = await page.evaluate("() => document.body.innerText")
            
            # Extract username
            username_el = await page.query_selector('.text-head-l, [class*="username"]')
            if username_el:
                data['username'] = (await username_el.text_content()).strip()
            
            # Extract display name
            display_name_el = await page.query_selector('.text-grey-10, [class*="display"]')
            if display_name_el:
                data['display_name'] = (await display_name_el.text_content()).strip()
            
            # Extract level
            level_match = re.search(r'Lv\.\s*(\d+)', all_text)
            if level_match:
                data['level'] = int(level_match.group(1))
            
            # Extract rating
            if 'Belum ada rating' in all_text:
                data['rating'] = 'Belum ada rating'
            else:
                rating_match = re.search(r'Rating[:\s]*([\d\.]+)', all_text)
                if rating_match:
                    data['rating'] = rating_match.group(1)
            
            # Extract category
            category_match = re.search(r'Kategori[:\s]*([^\n]+)', all_text)
            if category_match:
                data['category'] = category_match.group(1).strip()
            
            # Extract followers
            followers_match = re.search(r'Pengikut[:\s]*([\d,\.]+\s*(?:rb|jt|k|m)?)', all_text, re.IGNORECASE)
            if followers_match:
                data['followers'] = followers_match.group(1).strip()
            
            # Extract bio
            bio_match = re.search(r'☘️([^\n]+)', all_text)
            if bio_match:
                data['bio'] = bio_match.group(1).strip()
            
            # Extract GMV
            gmv_match = re.search(r'GMV[:\s]*Rp([\d,\.]+[KMkm]?)', all_text)
            if gmv_match:
                data['gmv'] = f"Rp{gmv_match.group(1)}"
            
            # Extract products sold
            sold_match = re.search(r'Produk terjual[:\s]*([\d,\.]+\s*(?:rb|k)?)', all_text, re.IGNORECASE)
            if sold_match:
                data['products_sold'] = sold_match.group(1).strip()
            
            # Extract avg views
            views_match = re.search(r'Rata-rata tayangan[:\s]*([\d,\.]+\s*(?:rb|k)?)', all_text, re.IGNORECASE)
            if views_match:
                data['avg_views'] = views_match.group(1).strip()
            
            # Extract gender distribution
            gender_match = re.search(r'Laki-laki[:\s]*([\d,\.]+)%[^\d]*([\d,\.]+)%', all_text)
            if gender_match:
                data['gender_male'] = f"{gender_match.group(1)}%"
                data['gender_female'] = f"{gender_match.group(2)}%"
            
            # Extract age group (most common)
            age_matches = re.findall(r'(\d+)[-—](\d+)[:\s]*([\d,\.]+)%', all_text)
            if age_matches:
                # Find highest percentage
                max_age = max(age_matches, key=lambda x: float(x[2]))
                data['age_group'] = f"{max_age[0]}-{max_age[1]}"
            
            return data
            
        except Exception as e:
            print(f"      ⚠️  Error extracting detail data: {e}")
            return {}
    
    async def extract_contacts(self, page: Page) -> Dict:
        """Extract email & WhatsApp dengan klik icon"""
        whatsapp = None
        email = None
        
        try:
            # Cari email icon
            email_icon = await page.query_selector('svg.alliance-icon-Email')
            
            if email_icon:
                # Click email icon
                parent_button = await email_icon.evaluate_handle("el => el.parentElement")
                if parent_button:
                    await parent_button.as_element().click()
                    await asyncio.sleep(2)
                    
                    # Get text after click
                    all_text = await page.evaluate("() => document.body.innerText")
                    
                    # Extract email
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    email_matches = re.findall(email_pattern, all_text)
                    
                    if email_matches:
                        for em in email_matches:
                            if all(x not in em.lower() for x in ['tokopedia', 'example', 'test', 'noreply']):
                                email = em.lower()
                                break
                    
                    # Extract WhatsApp
                    phone_patterns = [
                        (r'WhatsApp:\s*\n?\s*(\+?62\s*\d{9,13}|0?8\d{9,12}|\d{10,13})', 'WhatsApp label'),
                        (r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4}', '+62 format'),
                        (r'62\d{9,13}', '62 format'),
                        (r'08\d{8,12}', '08 format'),
                        (r'\b8\d{10,12}\b', '8xxx format'),
                    ]
                    
                    for pattern, name in phone_patterns:
                        matches = re.findall(pattern, all_text, re.MULTILINE)
                        if matches:
                            phone = matches[0].strip().replace(' ', '').replace('-', '').replace('\n', '')
                            
                            # Normalize to +62 format
                            if phone.startswith('08'):
                                whatsapp = f"+62{phone[1:]}"
                            elif phone.startswith('62') and not phone.startswith('+'):
                                whatsapp = f"+{phone}"
                            elif phone.startswith('8') and len(phone) >= 10:
                                whatsapp = f"+62{phone}"
                            elif phone.startswith('+'):
                                whatsapp = phone
                            else:
                                whatsapp = f"+62{phone}"
                            break
        
        except Exception as e:
            pass
        
        return {'whatsapp': whatsapp, 'email': email}
    
    async def scrape_one_creator(self, page: Page, index: int) -> Dict:
        """Scrape satu creator lengkap"""
        print(f"\n{'='*80}")
        print(f"📱 CREATOR #{index + 1}")
        print(f"{'='*80}")
        
        try:
            # Get all rows
            rows = await page.query_selector_all("tbody tr")
            
            if index >= len(rows):
                print(f"   ❌ Row index {index} out of range")
                return None
            
            # Extract data from list first
            list_data = await self.extract_list_data(rows[index], index)
            
            print(f"   📌 Clicking on creator row {index + 1}...")
            
            # Click row and wait for new page
            try:
                async with asyncio.timeout(10):
                    async with page.context.expect_page() as new_page_info:
                        await rows[index].click()
                    detail_page = await new_page_info.value
            except asyncio.TimeoutError:
                print(f"   ⚠️  No new page opened (timeout)")
                return list_data
            
            try:
                print(f"   ✅ Detail page opened")
                
                # Wait for page to load
                await detail_page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(2)
                
                # Check if we're on the detail page
                if "/detail?" not in detail_page.url:
                    print(f"   ⚠️  Not on detail page!")
                    return list_data
                
                # PAUSE untuk CAPTCHA
                await self.wait_for_manual_captcha(detail_page, "PROFIL CREATOR")
                
                # Wait for page to fully load
                await asyncio.sleep(3)
                
                # Check for "coba lagi" blocking page on detail page
                if not await self.check_and_handle_coba_lagi(detail_page, "DETAIL PAGE"):
                    print(f"   ⚠️  Detail page is blocked - skipping this creator")
                    return list_data
                
                # Extract detail data
                print(f"   📊 Extracting detail data...")
                detail_data = await self.extract_detail_data(detail_page)
                
                # Extract contacts
                print(f"   📧 Extracting contacts...")
                contacts = await self.extract_contacts(detail_page)
                
                # Merge all data
                result = {**list_data, **detail_data, **contacts}
                result['scraped_at'] = datetime.now().isoformat()
                
                # Print summary
                print(f"   ✅ Username: {result.get('username', 'N/A')}")
                print(f"   ✅ Followers: {result.get('followers', 'N/A')}")
                print(f"   ✅ Email: {result.get('email', 'N/A')}")
                print(f"   ✅ WhatsApp: {result.get('whatsapp', 'N/A')}")
                
                return result
                
            finally:
                await detail_page.close()
                print(f"   ✅ Detail page closed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return list_data if 'list_data' in locals() else None
    
    async def scrape(self, max_creators: int = 100):
        """Main scraping function"""
        print("\n" + "="*80)
        print("🚀 TOKOPEDIA SCRAPER - FULL DATA EXTRACTION")
        print("="*80)
        print(f"Target: {max_creators} creators")
        print("="*80 + "\n")
        
        await self.setup_browser()
        
        page = await self.context.new_page()
        
        try:
            # Navigate to list page
            print("📄 Navigating to list page...")
            await page.goto(self.list_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)
            
            # Check for "coba lagi" blocking page
            if not await self.check_and_handle_coba_lagi(page, "LIST PAGE"):
                print("\n❌ Cannot proceed - list page is blocked")
                print("   Please check your cookies or try again later")
                return
            
            # PAUSE untuk CAPTCHA pertama
            await self.wait_for_manual_captcha(page, "LIST CREATOR")
            
            # Load more creators
            loaded_count = await self.load_more_creators(page, max_creators)
            
            # Scrape each creator
            to_scrape = min(loaded_count, max_creators)
            print(f"📊 Will scrape {to_scrape} creators\n")
            
            for i in range(to_scrape):
                result = await self.scrape_one_creator(page, i)
                
                if result:
                    self.results.append(result)
                
                # Delay between requests
                if i < to_scrape - 1:
                    print(f"\n⏳ Waiting 3 seconds before next creator...")
                    await asyncio.sleep(3)
            
            # Save results
            self.save_results()
            
            # Summary
            total_with_contact = sum(1 for r in self.results if r.get('whatsapp') or r.get('email'))
            print("\n" + "="*80)
            print("✅ SCRAPING COMPLETED")
            print("="*80)
            print(f"Total scraped: {len(self.results)}")
            print(f"With contacts: {total_with_contact} ({total_with_contact/len(self.results)*100:.1f}%)")
            print(f"Results saved to:")
            print(f"  - output/affiliators_full.json")
            print(f"  - output/affiliators_full.xlsx")
            print("="*80 + "\n")
            
        finally:
            await page.close()
    
    def save_results(self):
        """Save results to JSON and Excel"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Save JSON
        with open(output_dir / "affiliators_full.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(self.results)} results to output/affiliators_full.json")
        
        # Save Excel
        try:
            import pandas as pd
            
            df = pd.DataFrame(self.results)
            
            # Reorder columns
            column_order = [
                'index', 'username', 'display_name', 'shop_name', 'level', 'rating',
                'category', 'followers', 'bio', 'gmv', 'products_sold', 'avg_views',
                'gender_male', 'gender_female', 'age_group',
                'email', 'whatsapp', 'scraped_at'
            ]
            
            # Only include columns that exist
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # Save to Excel
            excel_path = output_dir / "affiliators_full.xlsx"
            df.to_excel(excel_path, index=False, engine='openpyxl')
            
            print(f"📊 Saved to Excel: {excel_path}")
            
        except ImportError:
            print("⚠️  pandas or openpyxl not installed. Skipping Excel export.")
            print("   Install with: pip install pandas openpyxl")
    
    async def cleanup(self):
        """Cleanup"""
        if self.browser_engine:
            await self.browser_engine.close()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Tokopedia Scraper - Full Data Extraction')
    parser.add_argument(
        '--max-creators',
        type=int,
        default=100,
        help='Max creators to scrape (default: 100)'
    )
    parser.add_argument(
        '--cookie-file',
        default='config/cookies.json',
        help='Path to cookies file'
    )
    
    args = parser.parse_args()
    
    scraper = FullDataScraper(cookie_file=args.cookie_file)
    
    try:
        await scraper.scrape(max_creators=args.max_creators)
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
