#!/usr/bin/env python3
"""Simple test untuk melihat apakah contact data bisa diekstrak."""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_simple_contact():
    """Simple test untuk contact extraction."""
    
    print("📞 SIMPLE CONTACT TEST")
    print("=" * 40)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
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
        
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded")
        
        print("\n🎯 INSTRUCTIONS:")
        print("1. Browser window is open with creator list")
        print("2. Click on any creator to see their detail page")
        print("3. Look for contact information (WhatsApp, Email)")
        print("4. Check if there's an 'Info Kontak' section")
        print("5. Note where the contact data appears")
        
        print("\n⏳ Manual inspection time...")
        print("   Click on creators and explore their pages")
        print("   Look for WhatsApp numbers and email addresses")
        print("   Press Enter when you find contact info or are done exploring...")
        input()
        
        # Get current page content for analysis
        current_url = page.url
        print(f"\n📊 Current URL: {current_url}")
        
        # Check if we're on a detail page
        if 'creator' in current_url or 'profile' in current_url:
            print("✅ Looks like you're on a creator detail page")
            
            # Scan for contact data
            page_content = await page.content()
            
            # Look for phone numbers
            phone_patterns = [
                r'\+62\d{8,13}',
                r'08\d{8,11}',
                r'62\d{8,13}'
            ]
            
            found_phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_content)
                found_phones.extend(matches)
            
            unique_phones = list(set(found_phones))
            
            if unique_phones:
                print(f"📱 Found {len(unique_phones)} phone numbers:")
                for phone in unique_phones[:5]:
                    print(f"   {phone}")
            else:
                print("📱 No phone numbers found")
            
            # Look for emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found_emails = re.findall(email_pattern, page_content, re.IGNORECASE)
            unique_emails = list(set(found_emails))
            
            # Filter out common system emails
            filtered_emails = []
            exclude_domains = ['tokopedia.com', 'example.com', 'noreply']
            for email in unique_emails:
                if not any(domain in email.lower() for domain in exclude_domains):
                    filtered_emails.append(email)
            
            if filtered_emails:
                print(f"📧 Found {len(filtered_emails)} email addresses:")
                for email in filtered_emails[:5]:
                    print(f"   {email}")
            else:
                print("📧 No email addresses found")
            
            # Look for social media
            instagram_matches = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', page_content, re.IGNORECASE)
            tiktok_matches = re.findall(r'tiktok\.com/@([a-zA-Z0-9_.]+)', page_content, re.IGNORECASE)
            
            if instagram_matches:
                print(f"📸 Found Instagram: @{instagram_matches[0]}")
            if tiktok_matches:
                print(f"🎵 Found TikTok: @{tiktok_matches[0]}")
            
            # Summary
            if unique_phones or filtered_emails:
                print(f"\n✅ SUCCESS! Contact data found on this page")
                print(f"   This means contact extraction is possible")
            else:
                print(f"\n⚠️  No contact data found on this page")
                print(f"   Try different creators or look for hidden sections")
        
        else:
            print("ℹ️  Still on list page - try clicking on a creator")
        
        print(f"\n⏳ Browser stays open for more exploration...")
        print("   Press Enter to close...")
        input()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()
        print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(test_simple_contact())