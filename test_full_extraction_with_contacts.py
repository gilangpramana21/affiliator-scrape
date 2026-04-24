#!/usr/bin/env python3
"""Full extraction test dengan contact data (WhatsApp & Email)."""

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

async def extract_contact_from_page(page) -> Dict[str, Optional[str]]:
    """Extract contact info dari halaman saat ini."""
    
    contact_data = {
        'whatsapp': None,
        'email': None,
        'instagram': None,
        'tiktok': None
    }
    
    try:
        # Get page content
        page_content = await page.content()
        
        # Extract phone numbers (WhatsApp)
        phone_patterns = [
            r'\+62\d{8,13}',
            r'08\d{8,11}',
            r'62\d{8,13}'
        ]
        
        found_phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, page_content)
            found_phones.extend(matches)
        
        if found_phones:
            # Clean and normalize phone number
            phone = found_phones[0]  # Take first found
            phone = re.sub(r'[^\d+]', '', phone)
            
            # Normalize Indonesian phone numbers
            if phone.startswith('08'):
                phone = '+62' + phone[1:]
            elif phone.startswith('62') and not phone.startswith('+62'):
                phone = '+' + phone
            
            # Validate length
            if len(phone) >= 12 and len(phone) <= 16:
                contact_data['whatsapp'] = phone
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, page_content, re.IGNORECASE)
        
        if found_emails:
            # Filter out system emails
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
            if len(handle) > 2 and not handle.isdigit():
                contact_data['instagram'] = f"@{handle}"
        
        # Extract TikTok
        tiktok_matches = re.findall(r'tiktok\.com/@([a-zA-Z0-9_.]+)', page_content, re.IGNORECASE)
        if tiktok_matches:
            handle = tiktok_matches[0]
            if len(handle) > 2 and not handle.isdigit():
                contact_data['tiktok'] = f"@{handle}"
        
        return contact_data
        
    except Exception as e:
        print(f"   ⚠️  Error extracting contact: {e}")
        return contact_data

async def navigate_to_creator_detail(page, creator_username: str, base_url: str) -> bool:
    """Navigate ke halaman detail creator."""
    
    try:
        # Try to find clickable elements on current page
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
                    print(f"   🔗 Clicking: {selector}")
                    await elements[0].click()
                    await asyncio.sleep(3)
                    return True
            except:
                continue
        
        # If clicking failed, try direct URL navigation
        profile_urls = [
            f"{base_url}/creator/{creator_username}",
            f"{base_url}/profile/{creator_username}",
            f"https://www.tokopedia.com/{creator_username}"
        ]
        
        for url in profile_urls:
            try:
                print(f"   🌐 Trying: {url}")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                if response and response.status < 400:
                    await asyncio.sleep(3)
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        print(f"   ⚠️  Navigation error: {e}")
        return False

async def test_full_extraction_with_contacts():
    """Test full extraction dengan contact data."""
    
    print("🎯 FULL EXTRACTION WITH CONTACTS")
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
    
    print("✅ Components initialized")
    print(f"   Contact extraction: ✅ Enabled")
    
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
        
        # Test contact extraction for first 2 creators
        test_creators = result.affiliators[:2]
        all_creator_data = []
        
        print(f"\n📞 EXTRACTING CONTACT DATA:")
        print("-" * 40)
        
        for i, creator in enumerate(test_creators, 1):
            print(f"\n👤 Creator {i}: {creator.username}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            
            # Try to navigate to detail page
            success = await navigate_to_creator_detail(page, creator.username, config.base_url)
            
            if success:
                print(f"   ✅ Navigated to detail page")
                
                # Extract contact data
                contact_data = await extract_contact_from_page(page)
                
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
                
                if not found_any:
                    print(f"   ⚠️  No contact data found")
                
                # Combine data
                creator_with_contact = {
                    'username': creator.username,
                    'kategori': creator.kategori,
                    'pengikut': creator.pengikut,
                    'gmv': creator.gmv,
                    'whatsapp': contact_data['whatsapp'],
                    'email': contact_data['email'],
                    'instagram': contact_data['instagram'],
                    'tiktok': contact_data['tiktok'],
                    'produk_terjual': creator.produk_terjual,
                    'rata_rata_tayangan': creator.rata_rata_tayangan,
                    'tingkat_interaksi': creator.tingkat_interaksi,
                    'detail_url': creator.detail_url
                }
                
                all_creator_data.append(creator_with_contact)
                
                # Go back to list page
                await page.go_back()
                await asyncio.sleep(2)
                
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
                    'instagram': None,
                    'tiktok': None,
                    'produk_terjual': creator.produk_terjual,
                    'rata_rata_tayangan': creator.rata_rata_tayangan,
                    'tingkat_interaksi': creator.tingkat_interaksi,
                    'detail_url': creator.detail_url
                }
                
                all_creator_data.append(creator_with_contact)
        
        # Save results
        output_file = 'full_extraction_with_contacts.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_creator_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print("-" * 30)
        
        total = len(all_creator_data)
        whatsapp_count = sum(1 for c in all_creator_data if c['whatsapp'])
        email_count = sum(1 for c in all_creator_data if c['email'])
        instagram_count = sum(1 for c in all_creator_data if c['instagram'])
        tiktok_count = sum(1 for c in all_creator_data if c['tiktok'])
        
        print(f"   Total creators: {total}")
        print(f"   WhatsApp found: {whatsapp_count}/{total} ({whatsapp_count/total*100:.1f}%)")
        print(f"   Email found: {email_count}/{total} ({email_count/total*100:.1f}%)")
        print(f"   Instagram found: {instagram_count}/{total} ({instagram_count/total*100:.1f}%)")
        print(f"   TikTok found: {tiktok_count}/{total} ({tiktok_count/total*100:.1f}%)")
        
        # Show extracted data
        print(f"\n📋 EXTRACTED DATA WITH CONTACTS:")
        for i, creator in enumerate(all_creator_data, 1):
            print(f"\n{i}. {creator['username']}")
            print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
            print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
            if creator['whatsapp']:
                print(f"   📱 WhatsApp: {creator['whatsapp']}")
            if creator['email']:
                print(f"   📧 Email: {creator['email']}")
            if creator['instagram']:
                print(f"   📸 Instagram: {creator['instagram']}")
            if creator['tiktok']:
                print(f"   🎵 TikTok: {creator['tiktok']}")
        
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
    result = asyncio.run(test_full_extraction_with_contacts())
    
    if result:
        contact_found = sum(1 for c in result if c['whatsapp'] or c['email'])
        print(f"\n🎊 SUCCESS! Extracted {len(result)} creators")
        print(f"   Contact data found for {contact_found} creators")
        print(f"   WhatsApp & Email extraction is working!")
    else:
        print(f"\n⚠️  Extraction failed")