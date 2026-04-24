#!/usr/bin/env python3
"""Test extraction untuk section 'Info Kontak' dengan WhatsApp dan Email."""

import asyncio
import json
import re
from typing import List, Dict, Optional
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

class InfoKontakExtractor:
    """Extractor khusus untuk section 'Info Kontak'."""
    
    def __init__(self):
        pass
    
    async def extract_info_kontak(self, page) -> Dict[str, Optional[str]]:
        """Extract contact info dari section 'Info Kontak'."""
        
        contact_data = {
            'whatsapp': None,
            'email': None
        }
        
        try:
            print("      🔍 Looking for 'Info Kontak' section...")
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Look for "Info Kontak" section specifically
            info_kontak_selectors = [
                'div:has-text("Info Kontak")',
                'section:has-text("Info Kontak")',
                '[data-testid*="contact"]',
                '.info-kontak',
                'div[class*="contact"]'
            ]
            
            info_kontak_section = None
            
            # Try to find Info Kontak section using text content
            try:
                # Get all divs and check their text content
                all_divs = await page.query_selector_all('div')
                for div in all_divs:
                    try:
                        text = await div.inner_text()
                        if 'Info Kontak' in text:
                            info_kontak_section = div
                            print("      ✅ Found 'Info Kontak' section")
                            break
                    except:
                        continue
            except:
                pass
            
            if not info_kontak_section:
                print("      ⚠️  'Info Kontak' section not found, scanning whole page...")
            
            # Get page content for pattern matching
            page_content = await page.content()
            
            # Extract WhatsApp number
            # Look for patterns like "WhatsApp: 82164218187" or just the number near WhatsApp
            whatsapp_patterns = [
                r'WhatsApp[:\s]*(\+?62\d{8,13})',
                r'WhatsApp[:\s]*(\d{8,13})',
                r'wa[:\s]*(\+?62\d{8,13})',
                r'wa[:\s]*(\d{8,13})',
                # Pattern from screenshot: number after WhatsApp text
                r'WhatsApp[^0-9]*(\d{8,13})',
                # General Indonesian phone patterns
                r'(\+?62\d{8,13})',
                r'(08\d{8,11})',
                r'(8\d{8,12})'  # Pattern like 82164218187
            ]
            
            for pattern in whatsapp_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    phone = matches[0]
                    if isinstance(phone, tuple):
                        phone = phone[0]
                    
                    # Clean phone number
                    phone = re.sub(r'[^\d+]', '', phone)
                    
                    # Normalize Indonesian phone numbers
                    if phone.startswith('8') and len(phone) >= 10:  # Like 82164218187
                        phone = '+62' + phone
                    elif phone.startswith('08'):
                        phone = '+62' + phone[1:]
                    elif phone.startswith('62') and not phone.startswith('+62'):
                        phone = '+' + phone
                    
                    # Validate phone number length
                    if len(phone) >= 12 and len(phone) <= 16:
                        contact_data['whatsapp'] = phone
                        print(f"      📱 WhatsApp found: {phone}")
                        break
            
            # Extract Email
            # Look for email patterns, especially near "Email:" text
            email_patterns = [
                r'Email[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                r'email[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                # General email pattern
                r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    # Filter out system emails
                    exclude_domains = ['tokopedia.com', 'example.com', 'noreply', 'no-reply']
                    valid_emails = []
                    
                    for email in matches:
                        if isinstance(email, tuple):
                            email = email[0]
                        
                        domain = email.split('@')[1].lower()
                        if not any(excluded in domain for excluded in exclude_domains):
                            valid_emails.append(email.lower())
                    
                    if valid_emails:
                        contact_data['email'] = valid_emails[0]
                        print(f"      📧 Email found: {valid_emails[0]}")
                        break
            
            # Alternative approach: Look for clickable WhatsApp and Email elements
            if not contact_data['whatsapp'] or not contact_data['email']:
                print("      🔍 Looking for clickable contact elements...")
                
                # Look for WhatsApp logo/button
                whatsapp_selectors = [
                    'img[alt*="whatsapp" i]',
                    'img[src*="whatsapp" i]',
                    'svg[class*="whatsapp" i]',
                    'div[class*="whatsapp" i]',
                    'button[class*="whatsapp" i]',
                    'a[href*="whatsapp" i]',
                    'a[href*="wa.me"]'
                ]
                
                for selector in whatsapp_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"      🔗 Found WhatsApp element: {selector}")
                            
                            # Try to get phone number from nearby text or href
                            for element in elements:
                                try:
                                    # Check href attribute
                                    href = await element.get_attribute('href')
                                    if href and 'wa.me' in href:
                                        phone_match = re.search(r'wa\.me/(\+?\d+)', href)
                                        if phone_match:
                                            phone = phone_match.group(1)
                                            if not phone.startswith('+'):
                                                phone = '+' + phone
                                            contact_data['whatsapp'] = phone
                                            print(f"      📱 WhatsApp from href: {phone}")
                                            break
                                    
                                    # Check parent element text
                                    parent = await element.query_selector('..')
                                    if parent:
                                        parent_text = await parent.inner_text()
                                        phone_match = re.search(r'(\+?62\d{8,13}|\d{8,13})', parent_text)
                                        if phone_match:
                                            phone = phone_match.group(1)
                                            if phone.startswith('8') and len(phone) >= 10:
                                                phone = '+62' + phone
                                            elif phone.startswith('08'):
                                                phone = '+62' + phone[1:]
                                            contact_data['whatsapp'] = phone
                                            print(f"      📱 WhatsApp from parent: {phone}")
                                            break
                                except:
                                    continue
                            
                            if contact_data['whatsapp']:
                                break
                    except:
                        continue
                
                # Look for Email logo/button
                email_selectors = [
                    'img[alt*="email" i]',
                    'img[src*="email" i]',
                    'img[src*="mail" i]',
                    'svg[class*="email" i]',
                    'svg[class*="mail" i]',
                    'div[class*="email" i]',
                    'button[class*="email" i]',
                    'a[href*="mailto"]'
                ]
                
                for selector in email_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"      🔗 Found Email element: {selector}")
                            
                            # Try to get email from nearby text or href
                            for element in elements:
                                try:
                                    # Check href attribute
                                    href = await element.get_attribute('href')
                                    if href and 'mailto:' in href:
                                        email = href.replace('mailto:', '')
                                        if '@' in email:
                                            contact_data['email'] = email.lower()
                                            print(f"      📧 Email from href: {email}")
                                            break
                                    
                                    # Check parent element text
                                    parent = await element.query_selector('..')
                                    if parent:
                                        parent_text = await parent.inner_text()
                                        email_match = re.search(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', parent_text)
                                        if email_match:
                                            email = email_match.group(1)
                                            domain = email.split('@')[1].lower()
                                            exclude_domains = ['tokopedia.com', 'example.com']
                                            if not any(excluded in domain for excluded in exclude_domains):
                                                contact_data['email'] = email.lower()
                                                print(f"      📧 Email from parent: {email}")
                                                break
                                except:
                                    continue
                            
                            if contact_data['email']:
                                break
                    except:
                        continue
            
            return contact_data
            
        except Exception as e:
            print(f"      ⚠️  Error extracting Info Kontak: {e}")
            return contact_data
    
    async def navigate_to_creator_detail(self, page, creator_username: str, base_url: str) -> bool:
        """Navigate ke halaman detail creator."""
        
        try:
            # Try clicking on creator name/link in the table
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
                        await asyncio.sleep(4)  # Wait longer for page load
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
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    if response and response.status < 400:
                        await asyncio.sleep(4)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"      ⚠️  Navigation error: {e}")
            return False

async def test_info_kontak_extraction():
    """Test extraction untuk Info Kontak section."""
    
    print("📞 INFO KONTAK EXTRACTION TEST")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    info_kontak_extractor = InfoKontakExtractor()
    
    print("✅ Components initialized")
    print(f"   Info Kontak extraction: ✅ Enabled")
    
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
        
        # Extract creators from list page
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        print(f"✅ Found {len(result.affiliators)} creators on list page")
        
        if not result.affiliators:
            print("❌ No creators found")
            return
        
        # Test Info Kontak extraction for first 3 creators
        test_creators = result.affiliators[:3]
        all_creator_data = []
        
        print(f"\n📞 EXTRACTING INFO KONTAK FOR {len(test_creators)} CREATORS:")
        print("-" * 60)
        
        for i, creator in enumerate(test_creators, 1):
            print(f"\n👤 Creator {i}: {creator.username}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            
            # Navigate to detail page
            success = await info_kontak_extractor.navigate_to_creator_detail(page, creator.username, config.base_url)
            
            if success:
                print(f"   ✅ Navigated to detail page")
                
                # Extract Info Kontak
                contact_data = await info_kontak_extractor.extract_info_kontak(page)
                
                # Combine data
                creator_with_contact = {
                    'username': creator.username,
                    'kategori': creator.kategori,
                    'pengikut': creator.pengikut,
                    'gmv': creator.gmv,
                    'whatsapp': contact_data['whatsapp'],
                    'email': contact_data['email'],
                    'produk_terjual': creator.produk_terjual,
                    'rata_rata_tayangan': creator.rata_rata_tayangan,
                    'tingkat_interaksi': creator.tingkat_interaksi,
                    'detail_url': creator.detail_url
                }
                
                # Show results
                if contact_data['whatsapp'] or contact_data['email']:
                    print(f"   ✅ Contact data extracted!")
                    if contact_data['whatsapp']:
                        print(f"      📱 WhatsApp: {contact_data['whatsapp']}")
                    if contact_data['email']:
                        print(f"      📧 Email: {contact_data['email']}")
                else:
                    print(f"   ⚠️  No contact data found")
                
                all_creator_data.append(creator_with_contact)
                
                # Go back to list page
                await page.go_back()
                await asyncio.sleep(3)
                
            else:
                print(f"   ❌ Could not access detail page")
                
                # Add without contact data
                creator_with_contact = {
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
                
                all_creator_data.append(creator_with_contact)
        
        # Save results
        output_file = 'info_kontak_extraction_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_creator_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Summary
        print(f"\n📊 INFO KONTAK EXTRACTION SUMMARY:")
        print("-" * 40)
        
        total = len(all_creator_data)
        whatsapp_count = sum(1 for c in all_creator_data if c['whatsapp'])
        email_count = sum(1 for c in all_creator_data if c['email'])
        
        print(f"   Total creators processed: {total}")
        print(f"   WhatsApp numbers found: {whatsapp_count}/{total} ({whatsapp_count/total*100:.1f}%)")
        print(f"   Email addresses found: {email_count}/{total} ({email_count/total*100:.1f}%)")
        
        # Show extracted data
        print(f"\n📋 EXTRACTED DATA WITH INFO KONTAK:")
        for i, creator in enumerate(all_creator_data, 1):
            print(f"\n{i}. {creator['username']}")
            print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
            print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
            if creator['whatsapp']:
                print(f"   📱 WhatsApp: {creator['whatsapp']}")
            if creator['email']:
                print(f"   📧 Email: {creator['email']}")
        
        return all_creator_data
        
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
    result = asyncio.run(test_info_kontak_extraction())
    
    if result:
        contact_found = sum(1 for c in result if c['whatsapp'] or c['email'])
        print(f"\n🎊 SUCCESS! Processed {len(result)} creators")
        print(f"   Contact data found for {contact_found} creators")
        print(f"   Info Kontak extraction is working!")
    else:
        print(f"\n⚠️  Extraction failed")