#!/usr/bin/env python3
"""
Debug script untuk melihat struktur halaman detail creator dan mencari kontak info.
"""

import asyncio
import logging
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_contact_extraction():
    """Debug contact extraction dari halaman detail creator."""
    
    print("📞 DEBUGGING CONTACT EXTRACTION")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        
        if cookies:
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
            
            await browser_engine.context.add_cookies(cookie_list)
            print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page first
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to list page: {url}")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        # Click on first creator to get detail page
        print("🖱️ Clicking on first creator...")
        rows = await page.query_selector_all("tbody tr")
        if len(rows) > 0:
            # Listen for new page
            new_page_promise = browser_engine.context.wait_for_event("page")
            
            # Click first row
            await rows[0].click()
            print("   ✅ Row clicked")
            
            try:
                # Wait for detail page
                detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                print(f"   🆕 Detail page opened: {detail_page.url}")
                
                # Wait for page to load
                await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                
                # Check for puzzle and handle it
                puzzle_indicators = await detail_page.query_selector_all("[class*='puzzle'], [class*='loading'], [id*='puzzle']")
                if puzzle_indicators:
                    print("   🧩 Puzzle detected, refreshing...")
                    await detail_page.reload()
                    await asyncio.sleep(5)
                
                print(f"\n📋 ANALYZING DETAIL PAGE STRUCTURE:")
                
                # Look for contact-related elements
                contact_selectors = [
                    # WhatsApp patterns
                    "a[href*='wa.me']",
                    "a[href*='whatsapp']", 
                    "a[href*='api.whatsapp.com']",
                    "[class*='whatsapp']",
                    "[data-testid*='whatsapp']",
                    
                    # Phone patterns
                    "a[href^='tel:']",
                    "[class*='phone']",
                    "[class*='contact']",
                    
                    # Email patterns
                    "a[href^='mailto:']",
                    "[class*='email']",
                    
                    # Social media
                    "a[href*='instagram.com']",
                    "a[href*='tiktok.com']",
                    "a[href*='youtube.com']",
                    
                    # General contact sections
                    "[class*='contact']",
                    "[class*='info']",
                    "[class*='profile']",
                    "[data-testid*='contact']"
                ]
                
                found_contacts = {}
                
                for selector in contact_selectors:
                    elements = await detail_page.query_selector_all(selector)
                    if elements:
                        print(f"   ✅ Found {len(elements)} elements for: {selector}")
                        
                        for i, element in enumerate(elements[:3]):  # Show first 3
                            try:
                                href = await element.get_attribute("href")
                                text = await element.text_content()
                                class_name = await element.get_attribute("class")
                                
                                print(f"      Element {i+1}:")
                                if href:
                                    print(f"         href: {href}")
                                if text and text.strip():
                                    print(f"         text: {text.strip()[:50]}")
                                if class_name:
                                    print(f"         class: {class_name}")
                                
                                # Store potential contacts
                                if href:
                                    if 'wa.me' in href or 'whatsapp' in href:
                                        found_contacts['whatsapp'] = href
                                    elif href.startswith('tel:'):
                                        found_contacts['phone'] = href
                                    elif href.startswith('mailto:'):
                                        found_contacts['email'] = href
                                    elif 'instagram.com' in href:
                                        found_contacts['instagram'] = href
                                        
                            except Exception as e:
                                print(f"         Error reading element: {e}")
                    else:
                        print(f"   ❌ Not found: {selector}")
                
                # Look for text patterns that might contain contact info
                print(f"\n🔍 SEARCHING FOR CONTACT PATTERNS IN TEXT:")
                
                html_content = await detail_page.content()
                
                # Phone number patterns
                import re
                phone_patterns = [
                    r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',  # Indonesian format
                    r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}',         # Local format
                    r'\d{4}[\s-]?\d{4}[\s-]?\d{3,4}'              # General format
                ]
                
                for pattern in phone_patterns:
                    matches = re.findall(pattern, html_content)
                    if matches:
                        print(f"   📱 Phone pattern found: {matches[:3]}")  # Show first 3
                
                # Email patterns
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_matches = re.findall(email_pattern, html_content)
                if email_matches:
                    print(f"   📧 Email pattern found: {email_matches[:3]}")
                
                # WhatsApp number patterns
                wa_patterns = [
                    r'wa\.me/(\d+)',
                    r'whatsapp.*?(\+?\d{10,15})',
                    r'WA.*?(\+?\d{10,15})'
                ]
                
                for pattern in wa_patterns:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    if matches:
                        print(f"   💬 WhatsApp pattern found: {matches[:3]}")
                
                # Summary of found contacts
                print(f"\n📞 CONTACT SUMMARY:")
                if found_contacts:
                    for contact_type, contact_value in found_contacts.items():
                        print(f"   {contact_type}: {contact_value}")
                else:
                    print("   ❌ No direct contact links found")
                
                # Look for buttons or interactive elements
                print(f"\n🔘 INTERACTIVE ELEMENTS:")
                
                button_selectors = [
                    "button",
                    "[role='button']",
                    ".btn",
                    "[class*='button']"
                ]
                
                for selector in button_selectors:
                    buttons = await detail_page.query_selector_all(selector)
                    if buttons:
                        print(f"   Found {len(buttons)} {selector} elements")
                        
                        for i, button in enumerate(buttons[:5]):  # Show first 5
                            try:
                                text = await button.text_content()
                                onclick = await button.get_attribute("onclick")
                                data_attrs = await button.evaluate("el => Object.keys(el.dataset)")
                                
                                if text and text.strip():
                                    print(f"      Button {i+1}: {text.strip()[:30]}")
                                    if onclick:
                                        print(f"         onclick: {onclick[:50]}")
                                    if data_attrs:
                                        print(f"         data attrs: {data_attrs}")
                            except:
                                pass
                
                print(f"\n👀 MANUAL INSPECTION:")
                print("   Browser window is open for manual inspection")
                print("   Look for:")
                print("   - Contact buttons or links")
                print("   - WhatsApp/phone icons")
                print("   - Social media links")
                print("   - Profile information sections")
                
                input("\nPress Enter when done inspecting...")
                
                # Close detail page
                await detail_page.close()
                
            except asyncio.TimeoutError:
                print("   ⚠️ No detail page opened")
        else:
            print("   ❌ No table rows found")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(debug_contact_extraction())