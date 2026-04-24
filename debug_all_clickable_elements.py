#!/usr/bin/env python3
"""
Debug script untuk mencari semua elemen yang bisa diklik di halaman detail creator
dan menguji apakah ada yang menampilkan informasi kontak.
"""

import asyncio
import logging
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_all_clickable_elements():
    """Debug semua elemen yang bisa diklik untuk mencari kontak tersembunyi."""
    
    print("🔍 DEBUGGING ALL CLICKABLE ELEMENTS")
    print("=" * 60)
    
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
                
                print(f"\n🔍 ANALYZING ALL CLICKABLE ELEMENTS:")
                
                # Get baseline phone numbers before any clicks
                initial_content = await detail_page.content()
                initial_phones = extract_phone_numbers(initial_content)
                print(f"   📱 Initial phone numbers found: {initial_phones}")
                
                # Find all potentially clickable elements
                clickable_selectors = [
                    "button",
                    "a",
                    "[role='button']",
                    "[onclick]",
                    "img[src*='icon']",
                    "svg",
                    ".icon",
                    "[class*='btn']",
                    "[class*='button']",
                    "[data-testid]",
                    "[class*='social']",
                    "[class*='contact']"
                ]
                
                all_clickable = []
                
                for selector in clickable_selectors:
                    try:
                        elements = await detail_page.query_selector_all(selector)
                        for element in elements:
                            try:
                                # Get element info
                                tag_name = await element.evaluate("el => el.tagName")
                                class_name = await element.get_attribute("class") or ""
                                text = await element.text_content() or ""
                                src = await element.get_attribute("src") or ""
                                alt = await element.get_attribute("alt") or ""
                                title = await element.get_attribute("title") or ""
                                data_testid = await element.get_attribute("data-testid") or ""
                                
                                # Check if element is visible and clickable
                                is_visible = await element.is_visible()
                                is_enabled = await element.is_enabled()
                                
                                if is_visible and is_enabled:
                                    element_info = {
                                        'element': element,
                                        'tag': tag_name,
                                        'class': class_name,
                                        'text': text.strip()[:50],
                                        'src': src,
                                        'alt': alt,
                                        'title': title,
                                        'data_testid': data_testid,
                                        'selector': selector
                                    }
                                    
                                    # Score element based on likelihood of containing contact info
                                    score = score_element_for_contact(element_info)
                                    if score > 0:
                                        element_info['score'] = score
                                        all_clickable.append(element_info)
                                        
                            except Exception as e:
                                continue
                                
                    except Exception as e:
                        continue
                
                # Sort by score (highest first)
                all_clickable.sort(key=lambda x: x['score'], reverse=True)
                
                print(f"   🎯 Found {len(all_clickable)} potentially relevant clickable elements")
                
                # Test top scoring elements
                tested_count = 0
                max_tests = 10  # Limit to top 10 elements
                
                for i, elem_info in enumerate(all_clickable[:max_tests]):
                    tested_count += 1
                    print(f"\n   Testing element {tested_count}/{min(max_tests, len(all_clickable))}:")
                    print(f"      Score: {elem_info['score']}")
                    print(f"      Tag: {elem_info['tag']}")
                    print(f"      Class: {elem_info['class'][:50]}...")
                    print(f"      Text: {elem_info['text']}")
                    
                    try:
                        # Get current content before click
                        before_content = await detail_page.content()
                        before_phones = extract_phone_numbers(before_content)
                        
                        # Click the element
                        await elem_info['element'].click()
                        print(f"         ✅ Clicked")
                        
                        # Wait for potential changes
                        await asyncio.sleep(2)
                        
                        # Check for new content
                        after_content = await detail_page.content()
                        after_phones = extract_phone_numbers(after_content)
                        
                        # Check for new phone numbers
                        new_phones = set(after_phones) - set(before_phones)
                        if new_phones:
                            print(f"         🎉 NEW PHONE NUMBERS FOUND: {list(new_phones)}")
                            
                            # Save this successful interaction
                            print(f"         💾 SUCCESSFUL ELEMENT INFO:")
                            print(f"            Tag: {elem_info['tag']}")
                            print(f"            Class: {elem_info['class']}")
                            print(f"            Text: {elem_info['text']}")
                            print(f"            Selector: {elem_info['selector']}")
                        
                        # Check for modals/popups
                        modal_selectors = [
                            "[class*='modal']",
                            "[class*='popup']", 
                            "[class*='dialog']",
                            "[role='dialog']",
                            "[class*='overlay']"
                        ]
                        
                        modal_found = False
                        for modal_sel in modal_selectors:
                            modals = await detail_page.query_selector_all(modal_sel)
                            for modal in modals:
                                if await modal.is_visible():
                                    modal_text = await modal.text_content()
                                    modal_phones = extract_phone_numbers(modal_text)
                                    if modal_phones:
                                        print(f"         🪟 PHONE IN MODAL: {modal_phones}")
                                        modal_found = True
                                    
                                    # Close modal if found
                                    close_buttons = await modal.query_selector_all("button, [class*='close'], [aria-label*='close']")
                                    for close_btn in close_buttons:
                                        try:
                                            await close_btn.click()
                                            await asyncio.sleep(1)
                                            break
                                        except:
                                            continue
                        
                        if not new_phones and not modal_found:
                            print(f"         ℹ️ No new contact info found")
                        
                        # Small delay between tests
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"         ❌ Error clicking: {e}")
                
                # Final summary
                final_content = await detail_page.content()
                final_phones = extract_phone_numbers(final_content)
                all_new_phones = set(final_phones) - set(initial_phones)
                
                print(f"\n📊 FINAL SUMMARY:")
                print(f"   Initial phones: {initial_phones}")
                print(f"   Final phones: {final_phones}")
                print(f"   New phones discovered: {list(all_new_phones)}")
                print(f"   Elements tested: {tested_count}")
                
                if all_new_phones:
                    print(f"   🎉 SUCCESS: Found hidden contact information!")
                else:
                    print(f"   ℹ️ No hidden contact info found in tested elements")
                
                print(f"\n👀 MANUAL INSPECTION:")
                print("   Browser window is open for manual inspection")
                print("   Try clicking on icons, buttons, or social media elements")
                print("   Look for any elements that might reveal contact info")
                
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


def extract_phone_numbers(text):
    """Extract phone numbers from text."""
    if not text:
        return []
    
    patterns = [
        r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',
        r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}',
        r'62\d{9,13}',
        r'\d{4}[\s-]?\d{4}[\s-]?\d{3,4}',
        r'wa\.me/(\d+)',
        r'whatsapp.*?(\d{10,15})'
    ]
    
    phones = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        phones.extend(matches)
    
    # Clean and deduplicate
    clean_phones = []
    for phone in phones:
        clean = re.sub(r'[\s-]', '', str(phone))
        if len(clean) >= 8 and clean not in clean_phones:
            clean_phones.append(clean)
    
    return clean_phones


def score_element_for_contact(elem_info):
    """Score element based on likelihood of containing contact info."""
    score = 0
    
    # Text content scoring
    text = elem_info['text'].lower()
    class_name = elem_info['class'].lower()
    alt = elem_info['alt'].lower()
    title = elem_info['title'].lower()
    data_testid = elem_info['data_testid'].lower()
    
    # High priority keywords
    high_keywords = ['whatsapp', 'wa', 'contact', 'kontak', 'hubungi', 'phone', 'telepon']
    for keyword in high_keywords:
        if keyword in text or keyword in class_name or keyword in alt or keyword in title:
            score += 10
    
    # Medium priority keywords  
    medium_keywords = ['social', 'icon', 'btn', 'button', 'link']
    for keyword in medium_keywords:
        if keyword in class_name or keyword in data_testid:
            score += 3
    
    # Icon/image elements
    if elem_info['tag'].lower() in ['img', 'svg']:
        score += 2
    
    # Button elements
    if elem_info['tag'].lower() == 'button' or 'btn' in class_name:
        score += 2
    
    # Short text (likely icons or buttons)
    if len(text) <= 20 and len(text) > 0:
        score += 1
    
    return score


if __name__ == "__main__":
    asyncio.run(debug_all_clickable_elements())