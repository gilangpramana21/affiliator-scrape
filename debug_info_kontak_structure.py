#!/usr/bin/env python3
"""
Debug script untuk menganalisis struktur DOM area "Info Kontak" secara detail.
"""

import asyncio
import logging
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_info_kontak_structure():
    """Analisis detail struktur DOM area Info Kontak."""
    
    print("🔍 DEBUGGING INFO KONTAK STRUCTURE")
    print("=" * 60)
    
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
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to list page...")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        # Click on first creator (nuruluyunhasanahhh)
        print("🖱️ Clicking on nuruluyunhasanahhh...")
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
                await asyncio.sleep(5)
                
                # Handle puzzle if present
                puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                if puzzle_indicators:
                    print("   🧩 Puzzle detected, refreshing...")
                    await detail_page.reload()
                    await asyncio.sleep(5)
                
                print(f"\n🔍 ANALYZING INFO KONTAK STRUCTURE:")
                
                # Strategy 1: Look for "Info Kontak" text
                print("\n📋 Strategy 1: Search for 'Info Kontak' text")
                info_kontak_elements = await detail_page.query_selector_all("text=Info Kontak")
                print(f"   Found {len(info_kontak_elements)} 'Info Kontak' elements")
                
                # Strategy 2: Look for WhatsApp related elements
                print("\n📱 Strategy 2: Search for WhatsApp elements")
                whatsapp_selectors = [
                    "text=WhatsApp",
                    "[class*='whatsapp']",
                    "text=8136819154",
                    "[href*='wa.me']",
                    "[href*='whatsapp']"
                ]
                
                for selector in whatsapp_selectors:
                    try:
                        elements = await detail_page.query_selector_all(selector)
                        print(f"   {selector}: {len(elements)} elements")
                        
                        for i, element in enumerate(elements[:3]):  # Max 3 elements
                            try:
                                text = await element.text_content()
                                tag = await element.evaluate("el => el.tagName")
                                classes = await element.get_attribute("class") or ""
                                print(f"      Element {i+1}: {tag} - '{text}' - classes: {classes[:50]}")
                            except:
                                continue
                    except:
                        print(f"   {selector}: Error querying")
                
                # Strategy 3: Look for email elements
                print("\n📧 Strategy 3: Search for Email elements")
                email_selectors = [
                    "text=Email",
                    "text=N.hasanah73@gmail.com",
                    "[href*='mailto']",
                    "[class*='email']"
                ]
                
                for selector in email_selectors:
                    try:
                        elements = await detail_page.query_selector_all(selector)
                        print(f"   {selector}: {len(elements)} elements")
                        
                        for i, element in enumerate(elements[:3]):
                            try:
                                text = await element.text_content()
                                tag = await element.evaluate("el => el.tagName")
                                href = await element.get_attribute("href") or ""
                                print(f"      Element {i+1}: {tag} - '{text}' - href: {href}")
                            except:
                                continue
                    except:
                        print(f"   {selector}: Error querying")
                
                # Strategy 4: Extract all text content and search for patterns
                print("\n🔍 Strategy 4: Full page text analysis")
                page_content = await detail_page.content()
                
                # Search for phone patterns
                import re
                phone_patterns = [
                    r'8136819154',
                    r'WhatsApp[:\s]*([0-9]+)',
                    r'WA[:\s]*([0-9]+)',
                    r'(\+62|62|08)[0-9]{8,12}'
                ]
                
                print("   Phone number patterns found:")
                for pattern in phone_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        print(f"      {pattern}: {matches}")
                
                # Search for email patterns
                email_patterns = [
                    r'N\.hasanah73@gmail\.com',
                    r'Email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                    r'([a-zA-Z0-9._%+-]+@gmail\.com)'
                ]
                
                print("   Email patterns found:")
                for pattern in email_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        print(f"      {pattern}: {matches}")
                
                # Strategy 5: DOM structure analysis around contact info
                print("\n🏗️ Strategy 5: DOM structure analysis")
                
                # Try to find parent containers
                container_selectors = [
                    "[class*='contact']",
                    "[class*='info']", 
                    "[class*='kontak']",
                    "div:has-text('Info Kontak')",
                    "section:has-text('WhatsApp')"
                ]
                
                for selector in container_selectors:
                    try:
                        containers = await detail_page.query_selector_all(selector)
                        print(f"   {selector}: {len(containers)} containers")
                        
                        for i, container in enumerate(containers[:2]):
                            try:
                                inner_text = await container.text_content()
                                if 'whatsapp' in inner_text.lower() or '8136819154' in inner_text:
                                    print(f"      Container {i+1} (RELEVANT): {inner_text[:100]}...")
                                    
                                    # Get all child elements
                                    children = await container.query_selector_all("*")
                                    print(f"         Has {len(children)} child elements")
                                    
                                    # Look for specific contact elements
                                    for child in children[:5]:
                                        child_text = await child.text_content()
                                        child_tag = await child.evaluate("el => el.tagName")
                                        if child_text and ('8136819154' in child_text or 'whatsapp' in child_text.lower()):
                                            print(f"         CONTACT CHILD: {child_tag} - '{child_text}'")
                            except:
                                continue
                    except:
                        print(f"   {selector}: Error querying")
                
                # Strategy 6: Screenshot analysis area
                print("\n📸 Strategy 6: Screenshot for manual analysis")
                try:
                    # Take full page screenshot
                    screenshot_path = "debug_info_kontak_full.png"
                    await detail_page.screenshot(path=screenshot_path, full_page=True)
                    print(f"   Full page screenshot saved: {screenshot_path}")
                    
                    # Try to screenshot specific area if found
                    info_elements = await detail_page.query_selector_all("text=Info Kontak")
                    if info_elements:
                        # Get parent of "Info Kontak" text
                        parent = await info_elements[0].evaluate("el => el.parentElement")
                        if parent:
                            screenshot_area_path = "debug_info_kontak_area.png"
                            await parent.screenshot(path=screenshot_area_path)
                            print(f"   Info Kontak area screenshot saved: {screenshot_area_path}")
                    
                except Exception as e:
                    print(f"   Screenshot error: {e}")
                
                print(f"\n📊 SUMMARY:")
                print(f"   Target WhatsApp: 8136819154")
                print(f"   Target Email: N.hasanah73@gmail.com")
                print(f"   Page URL: {detail_page.url}")
                
                print(f"\n💡 RECOMMENDATIONS:")
                print(f"   1. Use regex patterns to find exact numbers in page content")
                print(f"   2. Look for parent containers with 'Info Kontak' text")
                print(f"   3. Use OCR on screenshot if DOM extraction fails")
                print(f"   4. Target specific selectors based on structure analysis")
                
                print(f"\n👀 MANUAL INSPECTION:")
                print("   Browser window is open for manual inspection")
                print("   Check the 'Info Kontak' section structure")
                print("   Look for WhatsApp: 8136819154 and Email elements")
                
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
    asyncio.run(debug_info_kontak_structure())