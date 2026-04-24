#!/usr/bin/env python3
"""Manual inspection untuk melihat struktur halaman detail creator dan mencari contact info."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def manual_contact_inspection():
    """Manual inspection untuk melihat struktur contact info di halaman detail."""
    
    print("🔍 MANUAL CONTACT INSPECTION")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser (visible mode for manual inspection)
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
        
        print("\n📋 MANUAL INSPECTION INSTRUCTIONS:")
        print("-" * 50)
        print("1. Browser window is now open")
        print("2. You can see the creator list page")
        print("3. Click on any creator to go to their detail page")
        print("4. Look for 'Info Kontak' or contact information section")
        print("5. Check if WhatsApp numbers and email addresses are visible")
        print("6. Note the HTML structure and CSS selectors")
        print("\n🔍 WHAT TO LOOK FOR:")
        print("- Section with title 'Info Kontak' or similar")
        print("- WhatsApp numbers (format: +62xxx or 08xxx)")
        print("- Email addresses")
        print("- Social media links (Instagram, TikTok)")
        print("\n⚠️  IMPORTANT:")
        print("- Some contact info might be hidden behind buttons/modals")
        print("- You might need to click 'Show Contact' or similar buttons")
        print("- Contact info might be in different tabs or sections")
        
        # Wait for manual inspection
        print(f"\n⏳ Take your time to inspect the pages...")
        print("   Navigate to different creators and check their contact info")
        print("   Press Enter when you're done inspecting...")
        input()
        
        # Get current page info for analysis
        current_url = page.url
        title = await page.title()
        
        print(f"\n📊 CURRENT PAGE INFO:")
        print(f"   URL: {current_url}")
        print(f"   Title: {title}")
        
        # Try to detect contact sections
        print(f"\n🔍 SCANNING FOR CONTACT SECTIONS:")
        
        contact_section_selectors = [
            'div[class*="contact"]',
            'div[class*="info"]',
            'section[class*="contact"]',
            '.contact-info',
            '.info-kontak',
            '[data-testid*="contact"]',
            'div:contains("Info Kontak")',
            'div:contains("Contact")',
            'div:contains("WhatsApp")',
            'div:contains("Email")',
            'div:contains("Hubungi")'
        ]
        
        found_sections = []
        
        for selector in contact_section_selectors:
            try:
                if 'contains' in selector:
                    # Skip contains selectors for now (not supported in playwright)
                    continue
                    
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"   ✅ Found section: {selector} ({len(elements)} elements)")
                    found_sections.append(selector)
                    
                    # Get sample text from first element
                    sample_text = await elements[0].inner_text()
                    if sample_text.strip():
                        print(f"      Sample text: {sample_text[:100]}...")
            except Exception as e:
                print(f"   ⚠️  Error with {selector}: {e}")
        
        # Look for phone numbers and emails in page content
        print(f"\n🔍 SCANNING PAGE CONTENT FOR CONTACT DATA:")
        
        page_content = await page.content()
        
        # Look for phone patterns
        import re
        phone_patterns = [
            r'\+62\d{8,13}',
            r'08\d{8,11}',
            r'62\d{8,13}'
        ]
        
        found_phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, page_content)
            if matches:
                found_phones.extend(matches)
        
        if found_phones:
            print(f"   📱 Phone numbers found: {len(set(found_phones))}")
            for phone in set(found_phones)[:5]:  # Show first 5 unique
                print(f"      {phone}")
        else:
            print(f"   📱 No phone numbers found in page content")
        
        # Look for email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, page_content, re.IGNORECASE)
        
        if found_emails:
            print(f"   📧 Email addresses found: {len(set(found_emails))}")
            for email in set(found_emails)[:5]:  # Show first 5 unique
                print(f"      {email}")
        else:
            print(f"   📧 No email addresses found in page content")
        
        # Look for social media patterns
        social_patterns = {
            'Instagram': r'instagram\.com/([a-zA-Z0-9_.]+)',
            'TikTok': r'tiktok\.com/@([a-zA-Z0-9_.]+)',
            'Line': r'line\.me/ti/p/([a-zA-Z0-9_.]+)',
            'Telegram': r't\.me/([a-zA-Z0-9_.]+)'
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                print(f"   📱 {platform} handles found: {len(set(matches))}")
                for handle in set(matches)[:3]:  # Show first 3 unique
                    print(f"      @{handle}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if found_sections:
            print("   ✅ Contact sections detected - contact extraction should work")
            print("   📝 Use these selectors for contact extraction:")
            for selector in found_sections[:3]:
                print(f"      - {selector}")
        else:
            print("   ⚠️  No obvious contact sections found")
            print("   📝 Contact info might be:")
            print("      - Hidden behind buttons/modals")
            print("      - In different page sections")
            print("      - Loaded dynamically with JavaScript")
            print("      - Only visible to logged-in users")
        
        if found_phones or found_emails:
            print("   ✅ Contact data is present in page content")
            print("   📝 Extraction patterns should work")
        else:
            print("   ⚠️  No contact data found in current page")
            print("   📝 Try navigating to different creator pages")
        
        print(f"\n⏳ Browser will stay open for further inspection...")
        print("   You can continue exploring different creators")
        print("   Press Enter to close when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during inspection: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()
        print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(manual_contact_inspection())