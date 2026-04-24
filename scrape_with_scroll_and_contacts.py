#!/usr/bin/env python3
"""
Scraper lengkap dengan:
1. Infinite scroll untuk load lebih banyak creator
2. Klik profil setiap creator
3. Klik logo WhatsApp dan Email untuk ambil contact data
"""

import asyncio
import json
import re
from typing import List, Dict, Optional, Set
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

class FullContactScraper:
    """Scraper lengkap dengan scroll dan contact extraction."""
    
    def __init__(self, browser_engine, parser, extractor, config):
        self.browser_engine = browser_engine
        self.parser = parser
        self.extractor = extractor
        self.config = config
        self.processed_creators = set()
    
    async def scroll_to_load_more(self, page, max_scrolls: int = 10) -> int:
        """Scroll halaman untuk load lebih banyak creator."""
        
        print(f"\n🔄 INFINITE SCROLL (max {max_scrolls} scrolls)...")
        
        initial_count = await self.count_visible_creators(page)
        print(f"   Initial creators: {initial_count}")
        
        for scroll_num in range(max_scrolls):
            print(f"   📜 Scroll {scroll_num + 1}/{max_scrolls}...", end=" ")
            
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            
            # Check if new creators loaded
            current_count = await self.count_visible_creators(page)
            
            if current_count > initial_count:
                new_count = current_count - initial_count
                print(f"✅ +{new_count} creators (total: {current_count})")
                initial_count = current_count
            else:
                print(f"⚠️  No new creators")
                # Try one more time
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(2)
                
                final_count = await self.count_visible_creators(page)
                if final_count == current_count:
                    print(f"   🏁 Reached end of scroll")
                    break
        
        final_count = await self.count_visible_creators(page)
        print(f"✅ Scroll completed. Total creators: {final_count}\n")
        return final_count
    
    async def count_visible_creators(self, page) -> int:
        """Count jumlah creator yang terlihat."""
        
        try:
            rows = await page.query_selector_all("tr")
            return len(rows) - 1 if len(rows) > 1 else 0  # Exclude header
        except:
            return 0
    
    async def extract_all_creators(self, page) -> List[Dict]:
        """Extract semua creator dari halaman saat ini."""
        
        html = await self.browser_engine.get_html(page)
        doc = self.parser.parse(html)
        result = self.extractor.extract_list_page(doc)
        
        creators = []
        for creator in result.affiliators:
            if creator.username not in self.processed_creators:
                creator_data = {
                    'username': creator.username,
                    'kategori': creator.kategori,
                    'pengikut': creator.pengikut,
                    'gmv': creator.gmv,
                    'whatsapp': None,
                    'email': None,
                    'produk_terjual': creator.produk_terjual,
                    'rata_rata_tayangan': creator.rata_rata_tayangan,
                    'tingkat_interaksi': creator.tingkat_interaksi,
                    'detail_url': creator.detail_url
                }
                creators.append(creator_data)
                self.processed_creators.add(creator.username)
        
        return creators
    
    async def click_creator_profile(self, page, creator_username: str) -> bool:
        """Klik profil creator untuk buka detail page."""
        
        try:
            # Try to find and click creator link
            clickable_selectors = [
                f"a[href*='{creator_username}']",
                "tr td:first-child a",
                "tr td a"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      🔗 Clicking creator link...")
                        await elements[0].click()
                        await asyncio.sleep(4)
                        return True
                except:
                    continue
            
            # Try direct URL
            detail_url = f"{self.config.base_url}/creator/{creator_username}"
            print(f"      🌐 Navigating to: {detail_url}")
            response = await page.goto(detail_url, wait_until='domcontentloaded', timeout=15000)
            if response and response.status < 400:
                await asyncio.sleep(4)
                return True
            
            return False
            
        except Exception as e:
            print(f"      ⚠️  Error clicking profile: {e}")
            return False
    
    async def click_whatsapp_icon_and_get_number(self, page) -> Optional[str]:
        """Klik logo WhatsApp dan ambil nomor dari modal 'Info Kontak'."""
        
        try:
            print(f"      📱 Looking for WhatsApp icon...")
            
            # Look for WhatsApp icon/button
            whatsapp_selectors = [
                'img[alt*="whatsapp" i]',
                'img[src*="whatsapp" i]',
                'svg[class*="whatsapp" i]',
                'button[class*="whatsapp" i]',
                'div[class*="whatsapp" i]',
                'a[href*="whatsapp" i]',
                # Green circle icon (from screenshot)
                'div[style*="background"][style*="green"]',
                'span[style*="background"][style*="green"]'
            ]
            
            whatsapp_element = None
            
            for selector in whatsapp_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      ✅ Found WhatsApp icon: {selector}")
                        whatsapp_element = elements[0]
                        break
                except:
                    continue
            
            if not whatsapp_element:
                print(f"      ⚠️  WhatsApp icon not found")
                return None
            
            # Click WhatsApp icon
            print(f"      🖱️  Clicking WhatsApp icon...")
            await whatsapp_element.click()
            await asyncio.sleep(2)
            
            # Look for modal "Info Kontak"
            print(f"      🔍 Looking for 'Info Kontak' modal...")
            
            # Wait for modal to appear
            await asyncio.sleep(1)
            
            # Get page content after click
            page_content = await page.content()
            
            # Extract WhatsApp number from modal
            whatsapp_patterns = [
                r'WhatsApp[:\s]*(\d{8,13})',
                r'WhatsApp[:\s]*(\+?62\d{8,13})',
                r'wa[:\s]*(\d{8,13})',
                # Pattern from screenshot: just the number
                r'(\d{10,13})',
                r'(8\d{9,12})'  # Like 82164218187
            ]
            
            for pattern in whatsapp_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    phone = matches[0]
                    
                    # Clean and normalize
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    # Normalize Indonesian phone
                    if phone.startswith('8') and len(phone) >= 10:
                        phone = '+62' + phone
                    elif phone.startswith('08'):
                        phone = '+62' + phone[1:]
                    elif phone.startswith('62') and not phone.startswith('+62'):
                        phone = '+' + phone
                    
                    if len(phone) >= 12 and len(phone) <= 16:
                        print(f"      ✅ WhatsApp: {phone}")
                        return phone
            
            print(f"      ⚠️  WhatsApp number not found in modal")
            return None
            
        except Exception as e:
            print(f"      ⚠️  Error getting WhatsApp: {e}")
            return None
    
    async def click_email_icon_and_get_email(self, page) -> Optional[str]:
        """Klik logo Email dan ambil email dari modal 'Info Kontak'."""
        
        try:
            print(f"      📧 Looking for Email icon...")
            
            # Look for Email icon/button
            email_selectors = [
                'img[alt*="email" i]',
                'img[alt*="mail" i]',
                'img[src*="email" i]',
                'img[src*="mail" i]',
                'svg[class*="email" i]',
                'svg[class*="mail" i]',
                'button[class*="email" i]',
                'button[class*="mail" i]',
                'div[class*="email" i]',
                'a[href*="mailto"]',
                # Blue circle icon (from screenshot)
                'div[style*="background"][style*="blue"]',
                'span[style*="background"][style*="blue"]'
            ]
            
            email_element = None
            
            for selector in email_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      ✅ Found Email icon: {selector}")
                        email_element = elements[0]
                        break
                except:
                    continue
            
            if not email_element:
                print(f"      ⚠️  Email icon not found")
                return None
            
            # Click Email icon
            print(f"      🖱️  Clicking Email icon...")
            await email_element.click()
            await asyncio.sleep(2)
            
            # Get page content after click
            page_content = await page.content()
            
            # Extract email from modal
            email_patterns = [
                r'Email[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                r'email[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    # Filter out system emails
                    exclude_domains = ['tokopedia.com', 'example.com', 'noreply']
                    
                    for email in matches:
                        domain = email.split('@')[1].lower()
                        if not any(excluded in domain for excluded in exclude_domains):
                            print(f"      ✅ Email: {email}")
                            return email.lower()
            
            print(f"      ⚠️  Email not found in modal")
            return None
            
        except Exception as e:
            print(f"      ⚠️  Error getting Email: {e}")
            return None
    
    async def extract_contact_from_detail_page(self, page) -> Dict[str, Optional[str]]:
        """Extract contact data dengan klik logo WhatsApp dan Email."""
        
        contact_data = {
            'whatsapp': None,
            'email': None
        }
        
        # Click WhatsApp icon and get number
        whatsapp = await self.click_whatsapp_icon_and_get_number(page)
        if whatsapp:
            contact_data['whatsapp'] = whatsapp
        
        # Wait a bit before clicking email
        await asyncio.sleep(1)
        
        # Click Email icon and get email
        email = await self.click_email_icon_and_get_email(page)
        if email:
            contact_data['email'] = email
        
        return contact_data

async def main():
    """Main scraper function."""
    
    print("🚀 TOKOPEDIA AFFILIATE SCRAPER")
    print("   WITH INFINITE SCROLL + CONTACT EXTRACTION")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    
    # Create scraper
    scraper = FullContactScraper(browser_engine, parser, extractor, config)
    
    print("✅ Components initialized")
    print(f"   Infinite scroll: ✅")
    print(f"   Contact extraction: ✅")
    print(f"   CaptchaSonic: {'✅' if config.captcha_api_key else '❌'}")
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        # Perform infinite scroll
        total_loaded = await scraper.scroll_to_load_more(page, max_scrolls=5)
        
        # Extract all creators
        print(f"📊 EXTRACTING CREATORS FROM PAGE...")
        all_creators = await scraper.extract_all_creators(page)
        print(f"✅ Extracted {len(all_creators)} unique creators\n")
        
        if not all_creators:
            print("❌ No creators found")
            return
        
        # Extract contact data for each creator
        print(f"📞 EXTRACTING CONTACT DATA:")
        print("=" * 60)
        
        creators_with_contacts = []
        success_count = 0
        
        # Limit to first 5 creators for testing
        test_limit = min(5, len(all_creators))
        print(f"   Testing with first {test_limit} creators\n")
        
        for i, creator in enumerate(all_creators[:test_limit], 1):
            print(f"👤 Creator {i}/{test_limit}: {creator['username']}")
            print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
            print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
            
            # Click creator profile
            success = await scraper.click_creator_profile(page, creator['username'])
            
            if success:
                print(f"   ✅ Opened detail page")
                
                # Extract contact data
                contact_data = await scraper.extract_contact_from_detail_page(page)
                
                # Update creator data
                creator['whatsapp'] = contact_data['whatsapp']
                creator['email'] = contact_data['email']
                
                if contact_data['whatsapp'] or contact_data['email']:
                    success_count += 1
                    print(f"   ✅ Contact data extracted!")
                else:
                    print(f"   ⚠️  No contact data found")
                
                # Go back to list
                await page.go_back()
                await asyncio.sleep(2)
                
            else:
                print(f"   ❌ Could not open detail page")
            
            creators_with_contacts.append(creator)
            print()
            
            # Save progress every 5 creators
            if i % 5 == 0:
                progress_file = f'scrape_progress_{i}.json'
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
                print(f"💾 Progress saved: {progress_file}\n")
        
        # Save final results
        output_file = 'final_scrape_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Final results saved: {output_file}")
        
        # Summary
        print(f"\n📊 SCRAPING SUMMARY:")
        print("=" * 40)
        
        total = len(creators_with_contacts)
        whatsapp_count = sum(1 for c in creators_with_contacts if c['whatsapp'])
        email_count = sum(1 for c in creators_with_contacts if c['email'])
        
        print(f"   Total creators processed: {total}")
        print(f"   Creators with contact: {success_count}/{total} ({success_count/total*100:.1f}%)")
        print(f"   WhatsApp numbers: {whatsapp_count}/{total} ({whatsapp_count/total*100:.1f}%)")
        print(f"   Email addresses: {email_count}/{total} ({email_count/total*100:.1f}%)")
        
        # Show results
        if success_count > 0:
            print(f"\n📋 CREATORS WITH CONTACT DATA:")
            print("-" * 40)
            
            for i, creator in enumerate([c for c in creators_with_contacts if c['whatsapp'] or c['email']], 1):
                print(f"\n{i}. {creator['username']}")
                print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
                print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
                if creator['whatsapp']:
                    print(f"   📱 WhatsApp: {creator['whatsapp']}")
                if creator['email']:
                    print(f"   📧 Email: {creator['email']}")
        
        return creators_with_contacts
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print(f"\n⏳ Browser open for inspection...")
        print("   Press Enter to close...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    
    if result:
        contact_found = sum(1 for c in result if c['whatsapp'] or c['email'])
        print(f"\n🎊 SCRAPING COMPLETED!")
        print(f"   Processed: {len(result)} creators")
        print(f"   Contact data: {contact_found} creators")
    else:
        print(f"\n⚠️  Scraping failed")