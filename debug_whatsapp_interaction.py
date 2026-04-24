#!/usr/bin/env python3
"""
Debug script untuk mencari dan mengklik logo WhatsApp di halaman detail creator.
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


async def debug_whatsapp_interaction():
    """Debug interaksi dengan logo/tombol WhatsApp."""
    
    print("💬 DEBUGGING WHATSAPP INTERACTION")
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
        print(f"\n🌐 Navigating to list page...")
        
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
                
                # Handle puzzle if present
                puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                if puzzle_indicators:
                    print("   🧩 Puzzle detected, refreshing...")
                    await detail_page.reload()
                    await asyncio.sleep(5)
                
                print(f"\n💬 SEARCHING FOR WHATSAPP ELEMENTS:")
                
                # Look for WhatsApp-related elements
                whatsapp_selectors = [
                    # WhatsApp icons/logos
                    "[class*='whatsapp']",
                    "[data-testid*='whatsapp']",
                    "[alt*='whatsapp' i]",
                    "[title*='whatsapp' i]",
                    
                    # Images that might be WhatsApp logos
                    "img[src*='whatsapp']",
                    "img[alt*='wa']",
                    "img[alt*='whatsapp']",
                    
                    # Buttons or links with WhatsApp text
                    "button:has-text('WhatsApp')",
                    "button:has-text('WA')",
                    "a:has-text('WhatsApp')",
                    "a:has-text('WA')",
                    
                    # Generic contact buttons
                    "[class*='contact']",
                    "button[class*='contact']",
                    "[data-testid*='contact']",
                    
                    # Social media icons
                    "[class*='social']",
                    "[class*='icon']"
                ]
                
                found_elements = []
                
                for selector in whatsapp_selectors:
                    try:
                        elements = await detail_page.query_selector_all(selector)
                        if elements:
                            print(f"   ✅ Found {len(elements)} elements for: {selector}")
                            
                            for i, element in enumerate(elements[:3]):  # Show first 3
                                try:
                                    # Get element info
                                    tag_name = await element.evaluate("el => el.tagName")
                                    class_name = await element.get_attribute("class")
                                    text = await element.text_content()
                                    src = await element.get_attribute("src")
                                    alt = await element.get_attribute("alt")
                                    title = await element.get_attribute("title")
                                    onclick = await element.get_attribute("onclick")
                                    
                                    print(f"      Element {i+1} ({tag_name}):")
                                    if class_name:
                                        print(f"         class: {class_name}")
                                    if text and text.strip():
                                        print(f"         text: {text.strip()[:50]}")
                                    if src:
                                        print(f"         src: {src}")
                                    if alt:
                                        print(f"         alt: {alt}")
                                    if title:
                                        print(f"         title: {title}")
                                    if onclick:
                                        print(f"         onclick: {onclick[:50]}")
                                    
                                    # Store potential WhatsApp elements
                                    element_info = {
                                        'element': element,
                                        'selector': selector,
                                        'tag': tag_name,
                                        'class': class_name,
                                        'text': text,
                                        'src': src,
                                        'alt': alt,
                                        'title': title
                                    }
                                    
                                    # Check if this looks like WhatsApp
                                    is_whatsapp = any([
                                        'whatsapp' in str(class_name or '').lower(),
                                        'whatsapp' in str(text or '').lower(),
                                        'whatsapp' in str(src or '').lower(),
                                        'whatsapp' in str(alt or '').lower(),
                                        'whatsapp' in str(title or '').lower(),
                                        'wa' in str(text or '').lower() and len(str(text or '').strip()) <= 10
                                    ])
                                    
                                    if is_whatsapp:
                                        found_elements.append(element_info)
                                        print(f"         🎯 POTENTIAL WHATSAPP ELEMENT!")
                                        
                                except Exception as e:
                                    print(f"         Error reading element: {e}")
                        else:
                            print(f"   ❌ Not found: {selector}")
                    except Exception as e:
                        print(f"   ⚠️ Error with selector {selector}: {e}")
                
                # Test clicking on potential WhatsApp elements
                print(f"\n🖱️ TESTING WHATSAPP ELEMENT INTERACTIONS:")
                
                if found_elements:
                    for i, elem_info in enumerate(found_elements[:3], 1):  # Test first 3
                        print(f"\n   Testing element {i}: {elem_info['selector']}")
                        print(f"      Tag: {elem_info['tag']}")
                        print(f"      Text: {elem_info['text']}")
                        
                        try:
                            # Get current page content before click
                            before_content = await detail_page.content()
                            
                            # Click the element
                            await elem_info['element'].click()
                            print(f"      ✅ Clicked element")
                            
                            # Wait for potential changes
                            await asyncio.sleep(3)
                            
                            # Check for changes in page content
                            after_content = await detail_page.content()
                            
                            if before_content != after_content:
                                print(f"      🔄 Page content changed after click!")
                                
                                # Look for newly appeared phone numbers
                                import re
                                phone_patterns = [
                                    r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',
                                    r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}',
                                    r'62\d{9,13}',
                                    r'\d{10,15}'
                                ]
                                
                                for pattern in phone_patterns:
                                    matches = re.findall(pattern, after_content)
                                    if matches:
                                        print(f"      📱 Found phone numbers: {matches[:3]}")
                                
                                # Look for WhatsApp-specific content
                                if 'whatsapp' in after_content.lower() or 'wa.me' in after_content.lower():
                                    print(f"      💬 WhatsApp content detected!")
                            else:
                                print(f"      ℹ️ No content change detected")
                            
                            # Check for popups or modals
                            modal_selectors = [
                                "[class*='modal']",
                                "[class*='popup']",
                                "[class*='dialog']",
                                "[role='dialog']"
                            ]
                            
                            for modal_sel in modal_selectors:
                                modals = await detail_page.query_selector_all(modal_sel)
                                if modals:
                                    print(f"      🪟 Modal/popup detected: {modal_sel}")
                                    
                                    # Get modal content
                                    for modal in modals[:1]:  # Check first modal
                                        modal_text = await modal.text_content()
                                        if modal_text and len(modal_text.strip()) > 0:
                                            print(f"         Modal text: {modal_text[:100]}...")
                                            
                                            # Look for phone numbers in modal
                                            for pattern in phone_patterns:
                                                modal_matches = re.findall(pattern, modal_text)
                                                if modal_matches:
                                                    print(f"         📱 Phone in modal: {modal_matches}")
                            
                        except Exception as e:
                            print(f"      ❌ Error clicking element: {e}")
                else:
                    print("   ❌ No potential WhatsApp elements found")
                
                # Manual inspection
                print(f"\n👀 MANUAL INSPECTION:")
                print("   Browser window is open for manual inspection")
                print("   Look for:")
                print("   - WhatsApp logos or icons")
                print("   - Contact buttons")
                print("   - Social media icons")
                print("   - Try clicking them to see if phone numbers appear")
                
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
    asyncio.run(debug_whatsapp_interaction())