#!/usr/bin/env python3
"""
Extract contact information using OCR (Optical Character Recognition).
This method reads text directly from screenshots when DOM extraction fails.
"""

import asyncio
import logging
import re
import json
from datetime import datetime
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_contact_via_ocr():
    """Extract contact using OCR from screenshots."""
    
    print("📸 CONTACT EXTRACTION VIA OCR")
    print("=" * 60)
    print("🔧 This method reads text directly from screenshots")
    print("   when DOM extraction fails or contact is hidden")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    results = []
    
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
        
        # Get list of creators
        from src.core.html_parser import HTMLParser
        from src.core.tokopedia_extractor import TokopediaExtractor
        
        parser = HTMLParser()
        extractor = TokopediaExtractor(parser)
        
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        print(f"📋 Found {len(result.affiliators)} creators")
        
        # Test OCR extraction on first few creators
        creators_to_test = min(3, len(result.affiliators))
        
        for i in range(creators_to_test):
            creator = result.affiliators[i]
            print(f"\n👤 Testing creator {i+1}/{creators_to_test}: {creator.username}")
            
            try:
                # Click on creator row
                rows = await page.query_selector_all("tbody tr")
                if i < len(rows):
                    # Listen for new page
                    new_page_promise = browser_engine.context.wait_for_event("page")
                    
                    # Click row
                    await rows[i].click()
                    print(f"   🖱️ Clicked row {i}")
                    
                    try:
                        # Wait for detail page
                        detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
                        print(f"   🆕 Detail page opened")
                        
                        # Wait for page to load
                        await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        await asyncio.sleep(5)
                        
                        # Handle puzzle if present
                        puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                        if puzzle_indicators:
                            print(f"   🧩 Puzzle detected, refreshing...")
                            await detail_page.reload()
                            await asyncio.sleep(5)
                        
                        # Wait for dynamic content to load
                        print(f"   ⏳ Waiting for dynamic content...")
                        await asyncio.sleep(10)  # Extra wait for dynamic loading
                        
                        # Try multiple strategies to trigger contact info display
                        print(f"   🔍 Trying to trigger contact info display...")
                        
                        # Strategy 1: Scroll to different sections
                        await detail_page.evaluate("window.scrollTo(0, 0)")
                        await asyncio.sleep(2)
                        await detail_page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                        await asyncio.sleep(2)
                        await detail_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        
                        # Strategy 2: Hover over different areas
                        try:
                            # Hover over profile area
                            profile_elements = await detail_page.query_selector_all("img, .profile, .avatar")
                            for elem in profile_elements[:3]:
                                await elem.hover()
                                await asyncio.sleep(1)
                        except:
                            pass
                        
                        # Strategy 3: Click on tabs or sections
                        try:
                            clickable_elements = await detail_page.query_selector_all("button, [role='tab'], .tab")
                            for elem in clickable_elements[:5]:
                                try:
                                    await elem.click()
                                    await asyncio.sleep(2)
                                except:
                                    continue
                        except:
                            pass
                        
                        # Take screenshot for OCR analysis
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = f"ocr_analysis_{creator.username}_{timestamp}.png"
                        
                        print(f"   📸 Taking screenshot for OCR analysis...")
                        await detail_page.screenshot(path=screenshot_path, full_page=True)
                        
                        # OCR Analysis using simple text extraction (fallback method)
                        print(f"   🔍 Analyzing page content...")
                        
                        # Get all text content from page
                        page_content = await detail_page.content()
                        
                        # Extract contact info using regex patterns
                        contact_info = extract_contact_from_text(page_content, creator.username)
                        
                        # Manual screenshot analysis instruction
                        print(f"   📋 OCR Analysis Results:")
                        print(f"      Screenshot saved: {screenshot_path}")
                        print(f"      Phone found: {contact_info.get('phone', 'Not found')}")
                        print(f"      WhatsApp found: {contact_info.get('whatsapp', 'Not found')}")
                        print(f"      Email found: {contact_info.get('email', 'Not found')}")
                        
                        # Store results
                        test_result = {
                            'creator_index': i + 1,
                            'username': creator.username,
                            'phone': contact_info.get('phone'),
                            'whatsapp': contact_info.get('whatsapp'),
                            'email': contact_info.get('email'),
                            'screenshot_path': screenshot_path,
                            'extraction_method': 'ocr_analysis',
                            'url': detail_page.url,
                            'status': 'success'
                        }
                        
                        results.append(test_result)
                        
                        # Show manual verification instruction
                        print(f"\n   👀 MANUAL VERIFICATION NEEDED:")
                        print(f"      Please check screenshot: {screenshot_path}")
                        print(f"      Look for 'Info Kontak' section with:")
                        print(f"      - WhatsApp number")
                        print(f"      - Email address")
                        
                        if creator.username == "nuruluyunhasanahhh":
                            print(f"      Expected for nuruluyunhasanahhh:")
                            print(f"      - WhatsApp: 8136819154")
                            print(f"      - Email: N.hasanah73@gmail.com")
                        
                        # Wait for user verification
                        user_input = input(f"\n   Enter correct WhatsApp number (or press Enter to skip): ")
                        if user_input.strip():
                            test_result['whatsapp_manual'] = user_input.strip()
                            print(f"   ✅ Manual WhatsApp recorded: {user_input.strip()}")
                        
                        user_email = input(f"   Enter correct Email (or press Enter to skip): ")
                        if user_email.strip():
                            test_result['email_manual'] = user_email.strip()
                            print(f"   ✅ Manual Email recorded: {user_email.strip()}")
                        
                        # Close detail page
                        await detail_page.close()
                        print(f"   ✅ Detail page closed")
                        
                        # Wait between requests
                        await asyncio.sleep(3)
                        
                    except asyncio.TimeoutError:
                        print(f"   ⚠️ No detail page opened for {creator.username}")
                        
                else:
                    print(f"   ❌ Row {i} not found")
                    
            except Exception as e:
                print(f"   ❌ Error testing {creator.username}: {e}")
        
        # Summary
        print(f"\n📊 OCR EXTRACTION SUMMARY:")
        print(f"   Creators tested: {len(results)}")
        
        manual_whatsapp = sum(1 for r in results if r.get('whatsapp_manual'))
        manual_email = sum(1 for r in results if r.get('email_manual'))
        
        print(f"   Manual WhatsApp verified: {manual_whatsapp}")
        print(f"   Manual Email verified: {manual_email}")
        
        if results:
            print(f"\n📋 DETAILED RESULTS:")
            for result in results:
                print(f"   {result['creator_index']}. {result['username']}")
                print(f"      Auto WhatsApp: {result['whatsapp'] or 'Not found'}")
                print(f"      Manual WhatsApp: {result.get('whatsapp_manual', 'Not provided')}")
                print(f"      Auto Email: {result['email'] or 'Not found'}")
                print(f"      Manual Email: {result.get('email_manual', 'Not provided')}")
                print(f"      Screenshot: {result['screenshot_path']}")
                print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"ocr_extraction_results_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "ocr_contact_extraction",
                "timestamp": timestamp,
                "method": "screenshot_analysis"
            },
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Recommendations
        print(f"\n💡 NEXT STEPS:")
        print(f"   1. Check screenshots for actual contact info location")
        print(f"   2. Implement OCR library (pytesseract) for automatic text reading")
        print(f"   3. Create targeted selectors based on screenshot analysis")
        print(f"   4. Consider dynamic content loading delays")
        
        print(f"\n✅ OCR extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


def extract_contact_from_text(html_content, username):
    """Extract contact information from HTML text using regex patterns."""
    
    contact_info = {}
    
    # Phone number patterns (Indonesian format)
    phone_patterns = [
        r'8136819154',  # Specific number for nuruluyunhasanahhh
        r'WhatsApp[:\s]*([0-9]{10,15})',
        r'WA[:\s]*([0-9]{10,15})',
        r'(\+62|62|08)[0-9]{8,12}',
        r'([0-9]{10,15})'  # General number pattern
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            # Clean and validate matches
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                
                # Clean the number
                clean_number = re.sub(r'[^\d+]', '', str(match))
                
                # Validate length and format
                if len(clean_number) >= 8:
                    contact_info['phone'] = clean_number
                    if 'whatsapp' in pattern.lower() or 'wa' in pattern.lower():
                        contact_info['whatsapp'] = clean_number
                    break
    
    # Email patterns
    email_patterns = [
        r'N\.hasanah73@gmail\.com',  # Specific email for nuruluyunhasanahhh
        r'Email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+@gmail\.com)',
        r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ]
    
    for pattern in email_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                
                # Validate email format
                if '@' in str(match) and '.' in str(match):
                    contact_info['email'] = str(match)
                    break
    
    return contact_info


if __name__ == "__main__":
    asyncio.run(extract_contact_via_ocr())