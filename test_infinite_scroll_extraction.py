#!/usr/bin/env python3
"""Test extraction dengan infinite scroll untuk memuat lebih banyak affiliator dan ambil contact data."""

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

class InfiniteScrollExtractor:
    """Extractor dengan infinite scroll dan contact extraction."""
    
    def __init__(self, browser_engine, parser, extractor):
        self.browser_engine = browser_engine
        self.parser = parser
        self.extractor = extractor
        self.processed_creators = set()  # Track processed creators
    
    async def scroll_and_load_more(self, page, max_scrolls: int = 10) -> int:
        """Scroll halaman untuk memuat lebih banyak creator."""
        
        print(f"🔄 Starting infinite scroll (max {max_scrolls} scrolls)...")
        
        initial_creators = await self.count_creators(page)
        print(f"   Initial creators visible: {initial_creators}")
        
        for scroll_num in range(max_scrolls):
            print(f"   📜 Scroll {scroll_num + 1}/{max_scrolls}...")
            
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new content to load
            await asyncio.sleep(3)
            
            # Check if new creators loaded
            current_creators = await self.count_creators(page)
            
            if current_creators > initial_creators:
                new_creators = current_creators - initial_creators
                print(f"   ✅ Loaded {new_creators} new creators (total: {current_creators})")
                initial_creators = current_creators
            else:
                print(f"   ⚠️  No new creators loaded")
                
                # Try scrolling a bit more to trigger loading
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(2)
                
                # Check again
                final_creators = await self.count_creators(page)
                if final_creators == current_creators:
                    print(f"   🏁 Reached end of scroll (no more creators)")
                    break
        
        final_count = await self.count_creators(page)
        print(f"✅ Scroll completed. Total creators loaded: {final_count}")
        return final_count
    
    async def count_creators(self, page) -> int:
        """Count jumlah creator yang terlihat di halaman."""
        
        # Try different selectors to count creators
        selectors = [
            "tr",  # Table rows
            ".creator-card",
            ".creator-item",
            "[data-testid*='creator']",
            ".affiliate-card"
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 1:  # Exclude header row
                    return len(elements) - 1 if selector == "tr" else len(elements)
            except:
                continue
        
        return 0
    
    async def extract_creators_from_current_page(self, page) -> List[Dict]:
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
                    'instagram': None,
                    'tiktok': None,
                    'produk_terjual': creator.produk_terjual,
                    'rata_rata_tayangan': creator.rata_rata_tayangan,
                    'tingkat_interaksi': creator.tingkat_interaksi,
                    'detail_url': creator.detail_url
                }
                creators.append(creator_data)
                self.processed_creators.add(creator.username)
        
        return creators
    
    async def extract_contact_from_page(self, page) -> Dict[str, Optional[str]]:
        """Extract contact info dari halaman detail."""
        
        contact_data = {
            'whatsapp': None,
            'email': None,
            'instagram': None,
            'tiktok': None
        }
        
        try:
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # Get page content
            page_content = await page.content()
            
            # Extract phone numbers (WhatsApp)
            phone_patterns = [
                r'(?:whatsapp|wa)[^\d]*(\+?62\d{8,13})',
                r'(?:hp|phone|telp)[^\d]*(\+?62\d{8,13})',
                r'(\+62\d{8,13})',
                r'(08\d{8,11})',
                r'(62\d{8,13})'
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    phone = matches[0]
                    if isinstance(phone, tuple):
                        phone = phone[0]
                    
                    # Clean and normalize
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    if phone.startswith('08'):
                        phone = '+62' + phone[1:]
                    elif phone.startswith('62') and not phone.startswith('+62'):
                        phone = '+' + phone
                    
                    if len(phone) >= 12 and len(phone) <= 16:
                        contact_data['whatsapp'] = phone
                        break
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found_emails = re.findall(email_pattern, page_content, re.IGNORECASE)
            
            if found_emails:
                exclude_domains = ['tokopedia.com', 'example.com', 'noreply', 'no-reply']
                valid_emails = []
                
                for email in found_emails:
                    domain = email.split('@')[1].lower()
                    if not any(excluded in domain for excluded in exclude_domains):
                        valid_emails.append(email.lower())
                
                if valid_emails:
                    contact_data['email'] = valid_emails[0]
            
            # Extract Instagram
            instagram_matches = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', page_content, re.IGNORECASE)
            if instagram_matches:
                handle = instagram_matches[0]
                if len(handle) > 2 and not handle.isdigit() and handle not in ['keyframes', 'static', 'login']:
                    contact_data['instagram'] = f"@{handle}"
            
            # Extract TikTok
            tiktok_matches = re.findall(r'tiktok\.com/@([a-zA-Z0-9_.]+)', page_content, re.IGNORECASE)
            if tiktok_matches:
                handle = tiktok_matches[0]
                if len(handle) > 2 and not handle.isdigit() and handle not in ['static', 'login']:
                    contact_data['tiktok'] = f"@{handle}"
            
            return contact_data
            
        except Exception as e:
            print(f"      ⚠️  Error extracting contact: {e}")
            return contact_data
    
    async def navigate_to_creator_profile(self, page, creator_username: str, base_url: str) -> bool:
        """Navigate ke profil creator."""
        
        try:
            # Try to find clickable elements first
            clickable_selectors = [
                f"a[href*='{creator_username}']",
                "tr td:first-child a",
                "tr td a",
                ".creator-name a",
                ".username a"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      🔗 Clicking: {selector}")
                        await elements[0].click()
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
            
            # Try direct URL navigation
            profile_urls = [
                f"{base_url}/creator/{creator_username}",
                f"{base_url}/profile/{creator_username}",
                f"https://www.tokopedia.com/{creator_username}"
            ]
            
            for url in profile_urls:
                try:
                    print(f"      🌐 Trying: {url}")
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    if response and response.status < 400:
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"      ⚠️  Navigation error: {e}")
            return False

async def test_infinite_scroll_extraction():
    """Test extraction dengan infinite scroll dan contact data."""
    
    print("🚀 INFINITE SCROLL EXTRACTION WITH CONTACTS")
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
    
    # Create infinite scroll extractor
    scroll_extractor = InfiniteScrollExtractor(browser_engine, parser, extractor)
    
    print("✅ Components initialized")
    print(f"   Infinite scroll: ✅ Enabled")
    print(f"   Contact extraction: ✅ Enabled")
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
        
        # Perform infinite scroll to load more creators
        total_creators_loaded = await scroll_extractor.scroll_and_load_more(page, max_scrolls=5)
        
        # Extract all creators from the loaded page
        print(f"\n📊 EXTRACTING ALL CREATORS FROM LOADED PAGE...")
        all_creators = await scroll_extractor.extract_creators_from_current_page(page)
        
        print(f"✅ Extracted {len(all_creators)} unique creators")
        
        if not all_creators:
            print("❌ No creators found")
            return
        
        # Extract contact data for each creator
        print(f"\n📞 EXTRACTING CONTACT DATA FOR ALL CREATORS:")
        print("-" * 50)
        
        creators_with_contacts = []
        contact_success_count = 0
        
        for i, creator in enumerate(all_creators, 1):
            print(f"\n👤 Creator {i}/{len(all_creators)}: {creator['username']}")
            print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
            print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
            
            # Navigate to creator profile
            success = await scroll_extractor.navigate_to_creator_profile(page, creator['username'], config.base_url)
            
            if success:
                print(f"   ✅ Navigated to profile")
                
                # Extract contact data
                contact_data = await scroll_extractor.extract_contact_from_page(page)
                
                # Update creator data with contact info
                creator['whatsapp'] = contact_data['whatsapp']
                creator['email'] = contact_data['email']
                creator['instagram'] = contact_data['instagram']
                creator['tiktok'] = contact_data['tiktok']
                
                # Show found contact info
                found_any = False
                if contact_data['whatsapp']:
                    print(f"   📱 WhatsApp: {contact_data['whatsapp']}")
                    found_any = True
                if contact_data['email']:
                    print(f"   📧 Email: {contact_data['email']}")
                    found_any = True
                if contact_data['instagram']:
                    print(f"   📸 Instagram: {contact_data['instagram']}")
                    found_any = True
                if contact_data['tiktok']:
                    print(f"   🎵 TikTok: {contact_data['tiktok']}")
                    found_any = True
                
                if found_any:
                    contact_success_count += 1
                    print(f"   ✅ Contact data found!")
                else:
                    print(f"   ⚠️  No contact data found")
                
                # Go back to list page
                await page.go_back()
                await asyncio.sleep(2)
                
                # Scroll back to current position to maintain context
                scroll_position = i * 100  # Approximate scroll position
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")
                await asyncio.sleep(1)
                
            else:
                print(f"   ❌ Could not access profile")
            
            creators_with_contacts.append(creator)
            
            # Save progress every 5 creators
            if i % 5 == 0:
                progress_file = f'extraction_progress_{i}.json'
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
                print(f"   💾 Progress saved: {progress_file}")
        
        # Save final results
        output_file = 'infinite_scroll_extraction_with_contacts.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Final results saved to: {output_file}")
        
        # Summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print("=" * 40)
        
        total = len(creators_with_contacts)
        whatsapp_count = sum(1 for c in creators_with_contacts if c['whatsapp'])
        email_count = sum(1 for c in creators_with_contacts if c['email'])
        instagram_count = sum(1 for c in creators_with_contacts if c['instagram'])
        tiktok_count = sum(1 for c in creators_with_contacts if c['tiktok'])
        
        print(f"   Total creators processed: {total}")
        print(f"   Creators with contact data: {contact_success_count}/{total} ({contact_success_count/total*100:.1f}%)")
        print(f"   WhatsApp numbers found: {whatsapp_count}/{total} ({whatsapp_count/total*100:.1f}%)")
        print(f"   Email addresses found: {email_count}/{total} ({email_count/total*100:.1f}%)")
        print(f"   Instagram handles found: {instagram_count}/{total} ({instagram_count/total*100:.1f}%)")
        print(f"   TikTok handles found: {tiktok_count}/{total} ({tiktok_count/total*100:.1f}%)")
        
        # Show top creators with contact data
        creators_with_contact = [c for c in creators_with_contacts if c['whatsapp'] or c['email']]
        
        if creators_with_contact:
            print(f"\n📋 TOP CREATORS WITH CONTACT DATA:")
            print("-" * 40)
            
            for i, creator in enumerate(creators_with_contact[:10], 1):  # Show top 10
                print(f"\n{i}. {creator['username']}")
                print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
                print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
                print(f"   Category: {creator['kategori']}")
                if creator['whatsapp']:
                    print(f"   📱 WhatsApp: {creator['whatsapp']}")
                if creator['email']:
                    print(f"   📧 Email: {creator['email']}")
                if creator['instagram']:
                    print(f"   📸 Instagram: {creator['instagram']}")
                if creator['tiktok']:
                    print(f"   🎵 TikTok: {creator['tiktok']}")
        
        return creators_with_contacts
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print(f"\n⏳ Browser window open for inspection...")
        print("   Press Enter to close...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(test_infinite_scroll_extraction())
    
    if result:
        contact_found = sum(1 for c in result if c['whatsapp'] or c['email'])
        print(f"\n🎊 SUCCESS! Processed {len(result)} creators with infinite scroll")
        print(f"   Contact data found for {contact_found} creators")
        print(f"   Infinite scroll + contact extraction is working!")
    else:
        print(f"\n⚠️  Extraction failed")