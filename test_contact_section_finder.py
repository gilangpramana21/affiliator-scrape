#!/usr/bin/env python3
"""Script untuk mencari section contact info di halaman detail creator."""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def find_contact_sections():
    """Mencari section contact info di halaman detail creator."""
    
    print("🔍 CONTACT SECTION FINDER")
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
        
        print("\n🎯 MANUAL EXPLORATION:")
        print("1. Browser window is open with creator list")
        print("2. Click on any creator to go to their detail page")
        print("3. Look for 'Info Kontak' or contact section")
        print("4. Try clicking buttons/tabs that might show contact info")
        print("5. Check if contact data is behind modals or dropdowns")
        
        print("\n⏳ Explore the pages manually...")
        print("   When you find contact info, press Enter to analyze the page...")
        input()
        
        # Analyze current page
        current_url = page.url
        print(f"\n📊 Analyzing current page: {current_url}")
        
        # Get page content
        page_content = await page.content()
        
        # Look for contact-related text
        contact_keywords = [
            'info kontak', 'contact', 'whatsapp', 'wa', 'email', 'hubungi',
            'kontak', 'telepon', 'phone', 'nomor', 'alamat email'
        ]
        
        print(f"\n🔍 SEARCHING FOR CONTACT KEYWORDS:")
        found_keywords = []
        for keyword in contact_keywords:
            if keyword.lower() in page_content.lower():
                found_keywords.append(keyword)
                print(f"   ✅ Found: '{keyword}'")
        
        if not found_keywords:
            print("   ❌ No contact keywords found")
        
        # Look for specific contact sections
        print(f"\n🔍 SEARCHING FOR CONTACT SECTIONS:")
        
        contact_selectors = [
            # General contact sections
            'div[class*="contact"]',
            'section[class*="contact"]',
            '.contact-info',
            '.info-kontak',
            '[data-testid*="contact"]',
            
            # Indonesian specific
            'div:has-text("Info Kontak")',
            'div:has-text("Kontak")',
            'div:has-text("Hubungi")',
            
            # Button/tab selectors
            'button:has-text("Kontak")',
            'button:has-text("Info")',
            'tab:has-text("Kontak")',
            
            # Modal selectors
            '.modal',
            '.popup',
            '.overlay',
            
            # Common UI patterns
            '.card',
            '.panel',
            '.section',
            '.info-panel'
        ]
        
        found_sections = []
        
        for selector in contact_selectors:
            try:
                if 'has-text' in selector:
                    # Skip has-text selectors for now (Playwright specific)
                    continue
                    
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"   ✅ Found section: {selector} ({len(elements)} elements)")
                    found_sections.append((selector, len(elements)))
                    
                    # Get sample text from first element
                    try:
                        sample_text = await elements[0].inner_text()
                        if sample_text.strip():
                            # Check if it contains contact-related content
                            sample_lower = sample_text.lower()
                            if any(keyword in sample_lower for keyword in contact_keywords):
                                print(f"      🎯 CONTACT CONTENT: {sample_text[:100]}...")
                            else:
                                print(f"      Sample: {sample_text[:50]}...")
                    except:
                        pass
            except Exception as e:
                print(f"   ⚠️  Error with {selector}: {e}")
        
        # Look for buttons that might reveal contact info
        print(f"\n🔍 SEARCHING FOR CONTACT BUTTONS:")
        
        button_selectors = [
            'button',
            'a[role="button"]',
            '.btn',
            '.button',
            '[data-testid*="button"]'
        ]
        
        contact_buttons = []
        
        for selector in button_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        text = await element.inner_text()
                        text_lower = text.lower().strip()
                        
                        if any(keyword in text_lower for keyword in ['kontak', 'contact', 'hubungi', 'info', 'detail']):
                            contact_buttons.append((text, selector))
                            print(f"   🔘 Found button: '{text}' ({selector})")
                    except:
                        continue
            except:
                continue
        
        # Look for phone numbers and emails in current page
        print(f"\n🔍 SCANNING FOR CONTACT DATA IN CURRENT PAGE:")
        
        # Phone patterns
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
            print(f"   📱 Found {len(unique_phones)} phone numbers:")
            for phone in unique_phones[:5]:
                print(f"      {phone}")
        else:
            print("   📱 No phone numbers found")
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, page_content, re.IGNORECASE)
        unique_emails = list(set(found_emails))
        
        # Filter out system emails
        filtered_emails = []
        exclude_domains = ['tokopedia.com', 'example.com', 'noreply']
        for email in unique_emails:
            if not any(domain in email.lower() for domain in exclude_domains):
                filtered_emails.append(email)
        
        if filtered_emails:
            print(f"   📧 Found {len(filtered_emails)} email addresses:")
            for email in filtered_emails[:5]:
                print(f"      {email}")
        else:
            print("   📧 No email addresses found")
        
        # Interactive testing of contact buttons
        if contact_buttons:
            print(f"\n🔘 TESTING CONTACT BUTTONS:")
            print("   Found contact-related buttons. Let's test them...")
            
            for i, (button_text, selector) in enumerate(contact_buttons[:3], 1):
                print(f"\n   Testing button {i}: '{button_text}'")
                try:
                    # Find and click the button
                    button_elements = await page.query_selector_all(selector)
                    for element in button_elements:
                        element_text = await element.inner_text()
                        if element_text.strip().lower() == button_text.lower():
                            print(f"      🔘 Clicking: '{button_text}'")
                            await element.click()
                            await asyncio.sleep(3)
                            
                            # Check if new content appeared
                            new_content = await page.content()
                            
                            # Look for new phone numbers
                            new_phones = []
                            for pattern in phone_patterns:
                                matches = re.findall(pattern, new_content)
                                new_phones.extend(matches)
                            
                            new_unique_phones = list(set(new_phones))
                            
                            if len(new_unique_phones) > len(unique_phones):
                                print(f"      ✅ NEW PHONES FOUND: {new_unique_phones}")
                            
                            # Look for new emails
                            new_emails = re.findall(email_pattern, new_content, re.IGNORECASE)
                            new_filtered_emails = []
                            for email in set(new_emails):
                                if not any(domain in email.lower() for domain in exclude_domains):
                                    new_filtered_emails.append(email)
                            
                            if len(new_filtered_emails) > len(filtered_emails):
                                print(f"      ✅ NEW EMAILS FOUND: {new_filtered_emails}")
                            
                            if len(new_unique_phones) == len(unique_phones) and len(new_filtered_emails) == len(filtered_emails):
                                print(f"      ⚠️  No new contact data after clicking")
                            
                            break
                except Exception as e:
                    print(f"      ⚠️  Error clicking button: {e}")
        
        # Summary and recommendations
        print(f"\n💡 ANALYSIS SUMMARY:")
        print("-" * 30)
        
        if found_keywords:
            print(f"   ✅ Contact keywords found: {', '.join(found_keywords)}")
        else:
            print(f"   ❌ No contact keywords found")
        
        if found_sections:
            print(f"   ✅ Contact sections found: {len(found_sections)}")
            for selector, count in found_sections[:3]:
                print(f"      - {selector} ({count} elements)")
        else:
            print(f"   ❌ No obvious contact sections found")
        
        if contact_buttons:
            print(f"   ✅ Contact buttons found: {len(contact_buttons)}")
        else:
            print(f"   ❌ No contact buttons found")
        
        if unique_phones or filtered_emails:
            print(f"   ✅ Contact data found in page")
        else:
            print(f"   ❌ No contact data found in page")
        
        print(f"\n📝 RECOMMENDATIONS:")
        if found_sections or contact_buttons:
            print("   ✅ Contact extraction should be possible")
            print("   📝 Focus on these approaches:")
            if found_sections:
                print("      - Use section selectors for direct extraction")
            if contact_buttons:
                print("      - Click contact buttons to reveal hidden data")
        else:
            print("   ⚠️  Contact data might be:")
            print("      - Hidden behind authentication")
            print("      - Loaded dynamically after user interaction")
            print("      - Only visible to certain user types")
            print("      - Located in different page sections")
        
        print(f"\n⏳ Continue exploring or press Enter to close...")
        input()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()
        print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(find_contact_sections())