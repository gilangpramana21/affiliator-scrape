#!/usr/bin/env python3
"""
Final scraper dengan:
1. Multi-tab handling (buka creator di tab baru)
2. Auto-refresh jika error "Kesalahan"
3. Extract contact data (WhatsApp & Email)
"""

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

async def check_and_handle_error(page, max_retries: int = 3) -> bool:
    """Check untuk error 'Kesalahan' dan auto-refresh."""
    
    for retry in range(max_retries):
        try:
            page_content = await page.content()
            
            # Check for error
            if 'Kesalahan' in page_content or 'Gagal memuat data' in page_content:
                print(f"      ⚠️  Error page detected, refreshing... (attempt {retry + 1}/{max_retries})")
                await page.reload(wait_until='domcontentloaded')
                await asyncio.sleep(4)
            else:
                print(f"      ✅ Page loaded successfully")
                return True
        except:
            await asyncio.sleep(2)
    
    return False

async def extract_contact_data(page) -> Dict[str, Optional[str]]:
    """Extract WhatsApp dan Email dari halaman detail."""
    
    contact_data = {
        'whatsapp': None,
        'email': None
    }
    
    try:
        # Wait for page to fully load
        await asyncio.sleep(3)
        
        # Get page content
        page_content = await page.content()
        
        print(f"      🔍 Extracting contact data...")
        
        # Extract WhatsApp number
        whatsapp_patterns = [
            r'WhatsApp[:\s]*(\d{8,13})',
            r'WhatsApp[:\s]*(\+?62\d{8,13})',
            r'wa[:\s]*(\d{8,13})',
            r'(8\d{9,12})',  # Like 82164218187
            r'(\+62\d{8,13})',
            r'(08\d{8,11})'
        ]
        
        for pattern in whatsapp_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
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
                    print(f"      📱 WhatsApp: {phone}")
                    break
        
        # Extract Email
        email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
        matches = re.findall(email_pattern, page_content, re.IGNORECASE)
        
        if matches:
            exclude_domains = ['tokopedia.com', 'example.com', 'noreply', 'no-reply']
            
            for email in matches:
                domain = email.split('@')[1].lower()
                if not any(excluded in domain for excluded in exclude_domains):
                    contact_data['email'] = email.lower()
                    print(f"      📧 Email: {email}")
                    break
        
        return contact_data
        
    except Exception as e:
        print(f"      ⚠️  Error extracting contact: {e}")
        return contact_data

async def process_creator_in_new_tab(context, creator, base_url, cookies) -> Dict:
    """Process creator di tab baru."""
    
    print(f"\n👤 Creator: {creator['username']}")
    print(f"   Followers: {creator['pengikut']:,}" if creator['pengikut'] else "   Followers: N/A")
    print(f"   GMV: Rp{creator['gmv']:,.0f}" if creator['gmv'] else "   GMV: N/A")
    
    try:
        # Create new tab
        print(f"   🆕 Opening new tab...")
        new_page = await context.new_page()
        
        # Apply cookies to new tab
        await new_page.context.add_cookies(cookies)
        
        # Navigate to creator detail page
        detail_url = f"{base_url}/creator/{creator['username']}"
        print(f"   🌐 Navigating to: {detail_url}")
        
        await new_page.goto(detail_url, wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)
        
        # Check for error and refresh if needed
        success = await check_and_handle_error(new_page)
        
        if not success:
            print(f"   ❌ Failed to load page")
            await new_page.close()
            return creator
        
        # Extract contact data
        contact_data = await extract_contact_data(new_page)
        
        # Update creator data
        creator['whatsapp'] = contact_data['whatsapp']
        creator['email'] = contact_data['email']
        
        if contact_data['whatsapp'] or contact_data['email']:
            print(f"   ✅ Contact data extracted!")
        else:
            print(f"   ⚠️  No contact data found")
        
        # Close tab
        await new_page.close()
        print(f"   🗑️  Tab closed")
        
        return creator
        
    except Exception as e:
        print(f"   ⚠️  Error processing creator: {e}")
        try:
            await new_page.close()
        except:
            pass
        return creator

async def main():
    """Main scraper function."""
    
    print("🚀 TOKOPEDIA AFFILIATE SCRAPER - FINAL VERSION")
    print("   ✅ Multi-tab handling")
    print("   ✅ Auto-refresh on error")
    print("   ✅ Contact extraction")
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
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("\n✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to: {url}")
        
        main_page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Prepare cookies for context
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
        
        # Apply cookies
        await main_page.context.add_cookies(cookie_list)
        
        # Reload with cookies
        await main_page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        # Extract creators from list page
        print(f"\n📊 EXTRACTING CREATORS...")
        html = await browser_engine.get_html(main_page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        all_creators = []
        for creator in result.affiliators:
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
        
        print(f"✅ Extracted {len(all_creators)} creators")
        
        if not all_creators:
            print("❌ No creators found")
            return
        
        # Process creators in new tabs
        print(f"\n📞 PROCESSING CREATORS:")
        print("=" * 60)
        
        creators_with_contacts = []
        success_count = 0
        
        # Get browser context
        context = main_page.context
        
        # Test with first 5 creators
        test_limit = min(5, len(all_creators))
        print(f"Processing {test_limit} creators...\n")
        
        for i, creator in enumerate(all_creators[:test_limit], 1):
            print(f"📋 {i}/{test_limit}")
            
            # Process in new tab
            updated_creator = await process_creator_in_new_tab(
                context, 
                creator, 
                config.base_url, 
                cookie_list
            )
            
            if updated_creator['whatsapp'] or updated_creator['email']:
                success_count += 1
            
            creators_with_contacts.append(updated_creator)
            
            # Small delay between creators
            await asyncio.sleep(2)
        
        # Save results
        output_file = 'final_scrape_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(creators_with_contacts, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved: {output_file}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print("=" * 40)
        
        total = len(creators_with_contacts)
        whatsapp_count = sum(1 for c in creators_with_contacts if c['whatsapp'])
        email_count = sum(1 for c in creators_with_contacts if c['email'])
        
        print(f"   Total processed: {total}")
        print(f"   With contact data: {success_count} ({success_count/total*100:.1f}%)")
        print(f"   WhatsApp found: {whatsapp_count} ({whatsapp_count/total*100:.1f}%)")
        print(f"   Email found: {email_count} ({email_count/total*100:.1f}%)")
        
        # Show results with contact data
        if success_count > 0:
            print(f"\n📋 CREATORS WITH CONTACT DATA:")
            print("-" * 40)
            
            for creator in [c for c in creators_with_contacts if c['whatsapp'] or c['email']]:
                print(f"\n• {creator['username']}")
                if creator['pengikut']:
                    print(f"  Followers: {creator['pengikut']:,}")
                if creator['gmv']:
                    print(f"  GMV: Rp{creator['gmv']:,.0f}")
                if creator['whatsapp']:
                    print(f"  📱 {creator['whatsapp']}")
                if creator['email']:
                    print(f"  📧 {creator['email']}")
        
        return creators_with_contacts
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print(f"\n⏳ Press Enter to close browser...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    
    if result:
        contact_found = sum(1 for c in result if c['whatsapp'] or c['email'])
        print(f"\n🎊 COMPLETED!")
        print(f"   {len(result)} creators processed")
        print(f"   {contact_found} with contact data")
    else:
        print(f"\n⚠️  Failed")