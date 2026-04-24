#!/usr/bin/env python3
"""
Scraper dengan multi-tab handling:
1. Handle CAPTCHA dan auto-refresh jika error
2. Detect tab baru setelah klik creator
3. Process multiple tabs secara parallel
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

class MultiTabScraper:
    """Scraper dengan multi-tab handling."""
    
    def __init__(self, browser_engine, parser, extractor, config):
        self.browser_engine = browser_engine
        self.parser = parser
        self.extractor = extractor
        self.config = config
        self.processed_creators = set()
    
    async def check_for_error_page(self, page) -> bool:
        """Check jika halaman menunjukkan error 'Kesalahan'."""
        
        try:
            page_content = await page.content()
            
            # Check for error keywords
            error_keywords = ['Kesalahan', 'Gagal memuat data', 'Silakan coba lagi']
            
            for keyword in error_keywords:
                if keyword in page_content:
                    print(f"      ⚠️  Error detected: '{keyword}'")
                    return True
            
            return False
            
        except Exception as e:
            print(f"      ⚠️  Error checking page: {e}")
            return False
    
    async def handle_error_with_refresh(self, page, max_retries: int = 3) -> bool:
        """Handle error page dengan auto-refresh."""
        
        for retry in range(max_retries):
            is_error = await self.check_for_error_page(page)
            
            if is_error:
                print(f"      🔄 Refreshing page (attempt {retry + 1}/{max_retries})...")
                await page.reload(wait_until='domcontentloaded')
                await asyncio.sleep(3)
            else:
                print(f"      ✅ Page loaded successfully")
                return True
        
        print(f"      ❌ Failed to load page after {max_retries} retries")
        return False
    
    async def wait_for_new_tab(self, context, timeout: int = 10) -> Optional[any]:
        """Wait for new tab to open."""
        
        try:
            print(f"      ⏳ Waiting for new tab to open...")
            
            # Get current pages
            initial_pages = context.pages
            initial_count = len(initial_pages)
            
            # Wait for new page to open
            for i in range(timeout):
                await asyncio.sleep(1)
                current_pages = context.pages
                
                if len(current_pages) > initial_count:
                    new_page = current_pages[-1]  # Get the newest page
                    print(f"      ✅ New tab opened!")
                    return new_page
            
            print(f"      ⚠️  No new tab opened after {timeout}s")
            return None
            
        except Exception as e:
            print(f"      ⚠️  Error waiting for new tab: {e}")
            return None
    
    async def extract_contact_from_detail_page(self, page) -> Dict[str, Optional[str]]:
        """Extract contact data dari halaman detail."""
        
        contact_data = {
            'whatsapp': None,
            'email': None
        }
        
        try:
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Check for error and refresh if needed
            success = await self.handle_error_with_refresh(page)
            if not success:
                return contact_data
            
            # Get page content
            page_content = await page.content()
            
            print(f"      🔍 Looking for contact icons...")
            
            # Look for WhatsApp icon and click it
            whatsapp_selectors = [
                'img[alt*="whatsapp" i]',
                'img[src*="whatsapp" i]',
                'svg[class*="whatsapp" i]',
                'a[href*="whatsapp" i]',
                'button[aria-label*="whatsapp" i]',
                # Try finding by color (green circle)
                'div[style*="rgb(37, 211, 55)"]',
                'span[style*="rgb(37, 211, 55)"]'
            ]
            
            whatsapp_clicked = False
            for selector in whatsapp_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      ✅ Found WhatsApp icon: {selector}")
                        await elements[0].click()
                        await asyncio.sleep(2)
                        whatsapp_clicked = True
                        break
                except:
                    continue
            
            # Extract WhatsApp number from page content
            if whatsapp_clicked:
                updated_content = await page.content()
                
                # Look for WhatsApp number patterns
                whatsapp_patterns = [
                    r'WhatsApp[:\s]*(\d{8,13})',
                    r'WhatsApp[:\s]*(\+?62\d{8,13})',
                    r'(8\d{9,12})',  # Like 82164218187
                    r'(\+62\d{8,13})'
                ]
                
                for pattern in whatsapp_patterns:
                    matches = re.findall(pattern, updated_content, re.IGNORECASE)
                    if matches:
                        phone = matches[0]
                        phone = re.sub(r'[^\d+]', '', phone)
                        
                        # Normalize
                        if phone.startswith('8') and len(phone) >= 10:
                            phone = '+62' + phone
                        elif phone.startswith('08'):
                            phone = '+62' + phone[1:]
                        elif phone.startswith('62') and not phone.startswith('+62'):
                            phone = '+' + phone
                        
                        if len(phone) >= 12 and len(phone) <= 16:
                            contact_data['whatsapp'] = phone
                            print(f"      📱 WhatsApp: {phone}")
                            break
            
            # Look for Email icon and click it
            email_selectors = [
                'img[alt*="email" i]',
                'img[alt*="mail" i]',
                'img[src*="email" i]',
                'img[src*="mail" i]',
                'svg[class*="email" i]',
                'a[href*="mailto"]',
                'button[aria-label*="email" i]',
                # Try finding by color (blue circle)
                'div[style*="rgb(0, 168, 255)"]',
                'span[style*="rgb(0, 168, 255)"]'
            ]
            
            email_clicked = False
            for selector in email_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"      ✅ Found Email icon: {selector}")
                        await elements[0].click()
                        await asyncio.sleep(2)
                        email_clicked = True
                        break
                except:
                    continue
            
            # Extract email from page content
            if email_clicked:
                updated_content = await page.content()
                
                email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
                matches = re.findall(email_pattern, updated_content, re.IGNORECASE)
                
                if matches:
                    exclude_domains = ['tokopedia.com', 'example.com', 'noreply']
                    
                    for email in matches:
                        domain = email.split('@')[1].lower()
                        if not any(excluded in domain for excluded in exclude_domains):
                            contact_data['email'] = email.lower()
                            print(f"      📧 Email: {email}")
                            break
            
            # If icons not found, try extracting from page content directly
            if not contact_data['whatsapp'] or not contact_data['email']:
                print(f"      🔍 Trying direct extraction from page content...")
                
                # Extract WhatsApp
                if not contact_data['whatsapp']:
                    for pattern in whatsapp_patterns:
                        matches = re.findall(pattern, page_content, re.IGNORECASE)
                        if matches:
                            phone = matches[0]
                            phone = re.sub(r'[^\d+]', '', phone)
                            
                            if phone.startswith('8') and len(phone) >= 10:
                                phone = '+62' + phone
                            elif phone.startswith('08'):
                                phone = '+62' + phone[1:]
                            
                            if len(phone) >= 12:
                                contact_data['whatsapp'] = phone
                                print(f"      📱 WhatsApp (direct): {phone}")
                                break
                
                # Extract Email
                if not contact_data['email']:
                    matches = re.findall(email_pattern, page_content, re.IGNORECASE)
                    if matches:
                        exclude_domains = ['tokopedia.com', 'example.com', 'noreply']
                        
                        for email in matches:
                            domain = email.split('@')[1].lower()
                            if not any(excluded in domain for excluded in exclude_domains):
                                contact_data['email'] = email.lower()
                                print(f"      📧 Email (direct): {email}")
                                break
            
            return contact_data
            
        except Exception as e:
            print(f"      ⚠️  Error extracting contact: {e}")
            return contact_data
    
    async def process_creator_in_new_tab(self, main_page, context, creator) -> Dict:
        """Process creator yang dibuka di tab baru."""
        
        print(f"\n👤 Creator: {creator['username']}")
        print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
        print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
        
        try:
            # Click creator link (will open in new tab)
            print(f"   🔗 Clicking creator link...")
            
            clickable_selectors = [
                f"a[href*='{creator['username']}']",
                "tr td:first-child a",
                "tr td a"
            ]
            
            clicked = False
            for selector in clickable_selectors:
                try:
                    elements = await main_page.query_selector_all(selector)
                    if elements:
                        # Click with modifier to open in new tab (Ctrl+Click or Cmd+Click)
                        await elements[0].click(modifiers=['Meta'])  # Use 'Control' for Windows/Linux
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                print(f"   ❌ Could not click creator link")
                return creator
            
            # Wait for new tab to open
            new_tab = await self.wait_for_new_tab(context, timeout=10)
            
            if not new_tab:
                print(f"   ❌ New tab did not open")
                return creator
            
            # Wait for new tab to load
            await new_tab.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(3)
            
            print(f"   ✅ New tab opened and loaded")
            
            # Extract contact data from new tab
            contact_data = await self.extract_contact_from_detail_page(new_tab)
            
            # Update creator data
            creator['whatsapp'] = contact_data['whatsapp']
            creator['email'] = contact_data['email']
            
            if contact_data['whatsapp'] or contact_data['email']:
                print(f"   ✅ Contact data extracted!")
            else:
                print(f"   ⚠️  No contact data found")
            
            # Close the new tab
            await new_tab.close()
            print(f"   🗑️  Tab closed")
            
            return creator
            
        except Exception as e:
            print(f"   ⚠️  Error processing creator: {e}")
            return creator

async def main():
    """Main scraper function dengan multi-tab handling."""
    
    print("🚀 TOKOPEDIA AFFILIATE SCRAPER")
    print("   WITH MULTI-TAB HANDLING")
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
    scraper = MultiTabScraper(browser_engine, parser, extractor, config)
    
    print("✅ Components initialized")
    print(f"   Multi-tab handling: ✅")
    print(f"   Auto-refresh on error: ✅")
    print(f"   Contact extraction: ✅")
    
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
        
        main_page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await main_page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await main_page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        # Extract creators from list page
        print(f"\n📊 EXTRACTING CREATORS FROM PAGE...")
        html = await browser_engine.get_html(main_page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        all_creators = []
        for creator in result.affiliators:
            if creator.username not in scraper.processed_creators:
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
                all_creators.append(creator_data)
                scraper.processed_creators.add(creator.username)
        
        print(f"✅ Extracted {len(all_creators)} unique creators")
        
        if not all_creators:
            print("❌ No creators found")
            return
        
        # Process creators with multi-tab handling
        print(f"\n📞 PROCESSING CREATORS WITH MULTI-TAB:")
        print("=" * 60)
        
        creators_with_contacts = []
        success_count = 0
        
        # Get browser context for multi-tab handling
        context = main_page.context
        
        # Limit to first 3 creators for testing
        test_limit = min(3, len(all_creators))
        print(f"   Testing with first {test_limit} creators\n")
        
        for i, creator in enumerate(all_creators[:test_limit], 1):
            print(f"📋 Processing {i}/{test_limit}...")
            
            # Process creator in new tab
            updated_creator = await scraper.process_creator_in_new_tab(main_page, context, creator)
            
            if updated_creator['whatsapp'] or updated_creator['email']:
                success_count += 1
            
            creators_with_contacts.append(updated_creator)
            
            # Save progress
            if i % 3 == 0:
                progress_file = f'multi_tab_progress_{i}.json'
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Progress saved: {progress_file}\n")
        
        # Save final results
        output_file = 'multi_tab_scrape_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Final results saved: {output_file}")
        
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