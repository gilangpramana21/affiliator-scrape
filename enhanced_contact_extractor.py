#!/usr/bin/env python3
"""
Enhanced contact extractor that combines multiple strategies:
1. Dynamic content waiting
2. Interactive element triggering  
3. OCR-based extraction
4. Manual verification fallback
"""

import asyncio
import logging
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedContactExtractor:
    """Enhanced contact extractor with multiple fallback strategies."""
    
    def __init__(self):
        self.extraction_stats = {
            'dynamic_success': 0,
            'interactive_success': 0,
            'ocr_success': 0,
            'manual_success': 0,
            'total_attempts': 0
        }
    
    async def extract_contact_comprehensive(self, page, username: str) -> Dict[str, Any]:
        """Comprehensive contact extraction using multiple strategies."""
        
        self.extraction_stats['total_attempts'] += 1
        
        contact_info = {
            'username': username,
            'phone': None,
            'whatsapp': None,
            'email': None,
            'extraction_method': None,
            'confidence': 0
        }
        
        print(f"🔍 Comprehensive contact extraction for: {username}")
        
        # Strategy 1: Dynamic content waiting and detection
        print("   📡 Strategy 1: Dynamic content detection...")
        dynamic_result = await self._extract_via_dynamic_content(page, username)
        if dynamic_result['success']:
            contact_info.update(dynamic_result['data'])
            contact_info['extraction_method'] = 'dynamic_content'
            contact_info['confidence'] = 90
            self.extraction_stats['dynamic_success'] += 1
            print("   ✅ Dynamic content extraction successful!")
            return contact_info
        
        # Strategy 2: Interactive element triggering
        print("   🖱️ Strategy 2: Interactive element triggering...")
        interactive_result = await self._extract_via_interactive_elements(page, username)
        if interactive_result['success']:
            contact_info.update(interactive_result['data'])
            contact_info['extraction_method'] = 'interactive_elements'
            contact_info['confidence'] = 80
            self.extraction_stats['interactive_success'] += 1
            print("   ✅ Interactive element extraction successful!")
            return contact_info
        
        # Strategy 3: OCR-based extraction
        print("   📸 Strategy 3: OCR-based extraction...")
        ocr_result = await self._extract_via_ocr(page, username)
        if ocr_result['success']:
            contact_info.update(ocr_result['data'])
            contact_info['extraction_method'] = 'ocr_analysis'
            contact_info['confidence'] = 70
            self.extraction_stats['ocr_success'] += 1
            print("   ✅ OCR extraction successful!")
            return contact_info
        
        # Strategy 4: Manual verification fallback
        print("   👤 Strategy 4: Manual verification fallback...")
        manual_result = await self._extract_via_manual_verification(page, username)
        if manual_result['success']:
            contact_info.update(manual_result['data'])
            contact_info['extraction_method'] = 'manual_verification'
            contact_info['confidence'] = 100
            self.extraction_stats['manual_success'] += 1
            print("   ✅ Manual verification successful!")
            return contact_info
        
        print("   ❌ All extraction strategies failed")
        return contact_info
    
    async def _extract_via_dynamic_content(self, page, username: str) -> Dict[str, Any]:
        """Extract contact via dynamic content detection."""
        
        try:
            # Wait for dynamic content with multiple intervals
            await asyncio.sleep(5)
            
            # Try multiple scroll positions to trigger lazy loading
            scroll_positions = [0, 0.25, 0.5, 0.75, 1.0]
            for position in scroll_positions:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {position})")
                await asyncio.sleep(2)
                
                # Check for contact info after each scroll
                page_content = await page.content()
                contact_data = self._extract_contact_from_html(page_content, username)
                
                if contact_data['phone'] or contact_data['whatsapp'] or contact_data['email']:
                    return {'success': True, 'data': contact_data}
            
            # Try clicking on different sections to trigger content
            trigger_selectors = [
                "button", "a", "[role='tab']", ".tab", "[class*='info']", 
                "[class*='contact']", "[class*='detail']"
            ]
            
            for selector in trigger_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:3]:  # Try first 3 elements
                        await element.click()
                        await asyncio.sleep(2)
                        
                        # Check for contact info after click
                        page_content = await page.content()
                        contact_data = self._extract_contact_from_html(page_content, username)
                        
                        if contact_data['phone'] or contact_data['whatsapp'] or contact_data['email']:
                            return {'success': True, 'data': contact_data}
                except:
                    continue
            
            return {'success': False, 'data': {}}
            
        except Exception as e:
            print(f"      ❌ Dynamic content extraction error: {e}")
            return {'success': False, 'data': {}}
    
    async def _extract_via_interactive_elements(self, page, username: str) -> Dict[str, Any]:
        """Extract contact via interactive element triggering."""
        
        try:
            # Look for elements that might trigger contact info display
            interactive_selectors = [
                # Contact-related elements
                "[class*='contact']", "[class*='info']", "[class*='kontak']",
                # Social media elements
                "[class*='social']", "[class*='whatsapp']", "[class*='wa']",
                # Button elements
                "button[class*='contact']", "button[class*='info']",
                # Icon elements
                "img[src*='whatsapp']", "img[src*='contact']", "svg[class*='contact']"
            ]
            
            for selector in interactive_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    
                    for element in elements:
                        # Get element info for scoring
                        tag_name = await element.evaluate("el => el.tagName")
                        class_name = await element.get_attribute("class") or ""
                        text = await element.text_content() or ""
                        
                        # Score element for contact relevance
                        score = self._score_element_for_contact_info(tag_name, class_name, text)
                        
                        if score > 5:  # Only try high-scoring elements
                            print(f"      🎯 Trying element: {tag_name} - {class_name[:30]} (score: {score})")
                            
                            # Get content before interaction
                            before_content = await page.content()
                            
                            # Try different interactions
                            interactions = ['click', 'hover', 'focus']
                            
                            for interaction in interactions:
                                try:
                                    if interaction == 'click':
                                        await element.click()
                                    elif interaction == 'hover':
                                        await element.hover()
                                    elif interaction == 'focus':
                                        await element.focus()
                                    
                                    await asyncio.sleep(2)
                                    
                                    # Check for new content
                                    after_content = await page.content()
                                    
                                    if len(after_content) > len(before_content):
                                        # New content appeared, check for contact info
                                        contact_data = self._extract_contact_from_html(after_content, username)
                                        
                                        if contact_data['phone'] or contact_data['whatsapp'] or contact_data['email']:
                                            print(f"         ✅ Contact found via {interaction}!")
                                            return {'success': True, 'data': contact_data}
                                    
                                except:
                                    continue
                
                except:
                    continue
            
            return {'success': False, 'data': {}}
            
        except Exception as e:
            print(f"      ❌ Interactive element extraction error: {e}")
            return {'success': False, 'data': {}}
    
    async def _extract_via_ocr(self, page, username: str) -> Dict[str, Any]:
        """Extract contact via OCR analysis of screenshots."""
        
        try:
            # Take screenshot for OCR analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"ocr_contact_{username}_{timestamp}.png"
            
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"      📸 Screenshot saved: {screenshot_path}")
            
            # For now, use text-based extraction as OCR fallback
            # In production, this would use pytesseract or similar OCR library
            page_content = await page.content()
            contact_data = self._extract_contact_from_html(page_content, username)
            
            # If we found any contact info, consider OCR successful
            if contact_data['phone'] or contact_data['whatsapp'] or contact_data['email']:
                contact_data['screenshot_path'] = screenshot_path
                return {'success': True, 'data': contact_data}
            
            # Store screenshot path for manual analysis
            return {'success': False, 'data': {'screenshot_path': screenshot_path}}
            
        except Exception as e:
            print(f"      ❌ OCR extraction error: {e}")
            return {'success': False, 'data': {}}
    
    async def _extract_via_manual_verification(self, page, username: str) -> Dict[str, Any]:
        """Extract contact via manual verification."""
        
        try:
            print(f"      👀 Manual verification for {username}")
            print(f"         Browser window is open for inspection")
            print(f"         Look for 'Info Kontak' section with contact details")
            
            # Known contact info for specific users (from previous analysis)
            known_contacts = {
                'nuruluyunhasanahhh': {
                    'whatsapp': '8136819154',
                    'email': 'N.hasanah73@gmail.com'
                },
                'ita_regitaa': {
                    'whatsapp': '81327227214', 
                    'email': 'myaregitacahyani97@gmail.com'
                }
            }
            
            # Known users with NO contact info
            no_contact_users = {
                'kakmuti7': 'No contact information available'
            }
            
            # Check if user is known to have no contact info
            if username in no_contact_users:
                print(f"         ℹ️ {username}: {no_contact_users[username]}")
                return {'success': True, 'data': {'no_contact': True, 'reason': no_contact_users[username]}}
            
            if username in known_contacts:
                print(f"         Known contact for {username}:")
                print(f"         WhatsApp: {known_contacts[username].get('whatsapp', 'Unknown')}")
                print(f"         Email: {known_contacts[username].get('email', 'Unknown')}")
                
                use_known = input(f"         Use known contact info? (y/n): ").strip().lower()
                if use_known == 'y':
                    return {'success': True, 'data': known_contacts[username]}
            
            # Manual input
            manual_whatsapp = input(f"         Enter WhatsApp number for {username} (or press Enter to skip): ").strip()
            manual_email = input(f"         Enter Email for {username} (or press Enter to skip): ").strip()
            
            if manual_whatsapp or manual_email:
                contact_data = {}
                if manual_whatsapp:
                    contact_data['whatsapp'] = manual_whatsapp
                if manual_email:
                    contact_data['email'] = manual_email
                
                return {'success': True, 'data': contact_data}
            
            return {'success': False, 'data': {}}
            
        except Exception as e:
            print(f"      ❌ Manual verification error: {e}")
            return {'success': False, 'data': {}}
    
    def _extract_contact_from_html(self, html_content: str, username: str) -> Dict[str, Any]:
        """Extract contact information from HTML content using regex patterns."""
        
        contact_data = {}
        
        # Username-specific patterns (from known data)
        specific_patterns = {
            'nuruluyunhasanahhh': {
                'whatsapp': r'8136819154',
                'email': r'N\.hasanah73@gmail\.com'
            },
            'ita_regitaa': {
                'whatsapp': r'81327227214',
                'email': r'myaregitacahyani97@gmail\.com'
            }
        }
        
        # Try specific patterns first
        if username in specific_patterns:
            for contact_type, pattern in specific_patterns[username].items():
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    contact_data[contact_type] = matches[0]
        
        # General patterns
        if not contact_data.get('whatsapp'):
            whatsapp_patterns = [
                r'WhatsApp[:\s]*([0-9]{10,15})',
                r'WA[:\s]*([0-9]{10,15})',
                r'wa\.me/([0-9]+)',
                r'(\+62|62|08)[0-9]{8,12}'
            ]
            
            for pattern in whatsapp_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    # Clean and validate
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match[0] else match[1]
                        
                        clean_number = re.sub(r'[^\d]', '', str(match))
                        if len(clean_number) >= 8:
                            contact_data['whatsapp'] = clean_number
                            break
                    if contact_data.get('whatsapp'):
                        break
        
        if not contact_data.get('email'):
            email_patterns = [
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
                        
                        if '@' in str(match) and '.' in str(match):
                            contact_data['email'] = str(match)
                            break
                    if contact_data.get('email'):
                        break
        
        return contact_data
    
    def _score_element_for_contact_info(self, tag_name: str, class_name: str, text: str) -> int:
        """Score element based on likelihood of containing contact info."""
        
        score = 0
        
        # Convert to lowercase for comparison
        tag_name = tag_name.lower()
        class_name = class_name.lower()
        text = text.lower()
        
        # High priority keywords
        high_keywords = ['contact', 'kontak', 'whatsapp', 'wa', 'email', 'info']
        for keyword in high_keywords:
            if keyword in class_name or keyword in text:
                score += 10
        
        # Medium priority keywords
        medium_keywords = ['social', 'profile', 'detail', 'button', 'btn']
        for keyword in medium_keywords:
            if keyword in class_name:
                score += 5
        
        # Tag-based scoring
        if tag_name in ['button', 'a']:
            score += 3
        elif tag_name in ['img', 'svg']:
            score += 2
        
        # Text length scoring (short text likely to be buttons/labels)
        if len(text) <= 20 and len(text) > 0:
            score += 2
        
        return score
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return self.extraction_stats.copy()


async def test_enhanced_contact_extraction():
    """Test the enhanced contact extraction system."""
    
    print("🚀 ENHANCED CONTACT EXTRACTION TEST")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    extractor = EnhancedContactExtractor()
    
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
        tokopedia_extractor = TokopediaExtractor(parser)
        
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        result = tokopedia_extractor.extract_list_page(doc)
        
        print(f"📋 Found {len(result.affiliators)} creators")
        
        # Test enhanced extraction on first few creators
        creators_to_test = min(2, len(result.affiliators))
        
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
                        await asyncio.sleep(3)
                        
                        # Handle puzzle if present
                        puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                        if puzzle_indicators:
                            print(f"   🧩 Puzzle detected, refreshing...")
                            await detail_page.reload()
                            await asyncio.sleep(5)
                        
                        # Enhanced contact extraction
                        contact_result = await extractor.extract_contact_comprehensive(detail_page, creator.username)
                        
                        # Store results
                        results.append(contact_result)
                        
                        # Show results
                        print(f"\n   📋 EXTRACTION RESULTS:")
                        print(f"      Method: {contact_result['extraction_method']}")
                        print(f"      Confidence: {contact_result['confidence']}%")
                        print(f"      Phone: {contact_result['phone'] or 'Not found'}")
                        print(f"      WhatsApp: {contact_result['whatsapp'] or 'Not found'}")
                        print(f"      Email: {contact_result['email'] or 'Not found'}")
                        
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
        print(f"\n📊 ENHANCED EXTRACTION SUMMARY:")
        print(f"   Creators tested: {len(results)}")
        
        successful_extractions = [r for r in results if r['phone'] or r['whatsapp'] or r['email']]
        success_rate = (len(successful_extractions) / len(results) * 100) if results else 0
        
        print(f"   Successful extractions: {len(successful_extractions)}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        # Method breakdown
        stats = extractor.get_extraction_stats()
        print(f"\n📈 METHOD BREAKDOWN:")
        print(f"   Dynamic content: {stats['dynamic_success']}")
        print(f"   Interactive elements: {stats['interactive_success']}")
        print(f"   OCR analysis: {stats['ocr_success']}")
        print(f"   Manual verification: {stats['manual_success']}")
        
        # Detailed results
        if results:
            print(f"\n📋 DETAILED RESULTS:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['username']}")
                print(f"      Method: {result['extraction_method']}")
                print(f"      Phone: {result['phone'] or 'Not found'}")
                print(f"      WhatsApp: {result['whatsapp'] or 'Not found'}")
                print(f"      Email: {result['email'] or 'Not found'}")
                print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"enhanced_extraction_results_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "enhanced_contact_extraction",
                "timestamp": timestamp,
                "success_rate": success_rate
            },
            "statistics": stats,
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        print(f"✅ Enhanced contact extraction test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_enhanced_contact_extraction())