#!/usr/bin/env python3
"""
Smart contact validator that learns from verified data and handles edge cases.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartContactValidator:
    """Smart contact validator with learning capabilities."""
    
    def __init__(self, database_path: str = "verified_contacts_database.json"):
        self.database_path = database_path
        self.database = self._load_database()
        self.validation_stats = {
            'total_validated': 0,
            'found_contact': 0,
            'no_contact': 0,
            'extraction_errors': 0
        }
    
    def _load_database(self) -> Dict[str, Any]:
        """Load verified contacts database."""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "verified_contacts": {},
                "no_contact_users": {},
                "extraction_patterns": {},
                "extraction_statistics": {}
            }
    
    def _save_database(self):
        """Save database to file."""
        self.database["extraction_statistics"]["last_updated"] = datetime.now().isoformat()
        with open(self.database_path, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, indent=2, ensure_ascii=False)
    
    async def validate_contact(self, page, username: str) -> Dict[str, Any]:
        """Validate contact information for a user."""
        
        self.validation_stats['total_validated'] += 1
        
        print(f"🔍 Validating contact for: {username}")
        
        # Check if user is already in verified database
        if username in self.database["verified_contacts"]:
            contact_data = self.database["verified_contacts"][username]
            print(f"   ✅ Found in verified database:")
            print(f"      WhatsApp: {contact_data.get('whatsapp', 'Not available')}")
            print(f"      Email: {contact_data.get('email', 'Not available')}")
            
            self.validation_stats['found_contact'] += 1
            return {
                'username': username,
                'whatsapp': contact_data.get('whatsapp'),
                'email': contact_data.get('email'),
                'phone': contact_data.get('phone'),
                'source': 'verified_database',
                'confidence': 100,
                'status': 'success'
            }
        
        # Check if user is known to have no contact
        if username in self.database["no_contact_users"]:
            no_contact_data = self.database["no_contact_users"][username]
            print(f"   ℹ️ Known no-contact user:")
            print(f"      Reason: {no_contact_data.get('reason', 'No contact available')}")
            
            self.validation_stats['no_contact'] += 1
            return {
                'username': username,
                'whatsapp': None,
                'email': None,
                'phone': None,
                'source': 'verified_no_contact',
                'confidence': 100,
                'status': 'no_contact',
                'reason': no_contact_data.get('reason')
            }
        
        # Extract contact using multiple strategies
        print(f"   🔍 Extracting contact information...")
        extraction_result = await self._extract_contact_smart(page, username)
        
        # Validate and store results
        if extraction_result['status'] == 'success':
            self._add_to_verified_database(username, extraction_result)
            self.validation_stats['found_contact'] += 1
        elif extraction_result['status'] == 'no_contact':
            self._add_to_no_contact_database(username, extraction_result)
            self.validation_stats['no_contact'] += 1
        else:
            self.validation_stats['extraction_errors'] += 1
        
        return extraction_result
    
    async def _extract_contact_smart(self, page, username: str) -> Dict[str, Any]:
        """Smart contact extraction with multiple strategies."""
        
        try:
            # Strategy 1: Wait for dynamic content
            print(f"      📡 Waiting for dynamic content...")
            await asyncio.sleep(8)  # Longer wait for dynamic content
            
            # Strategy 2: Scroll to trigger lazy loading
            print(f"      📜 Scrolling to trigger content loading...")
            scroll_positions = [0, 0.3, 0.6, 1.0]
            for position in scroll_positions:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {position})")
                await asyncio.sleep(3)
            
            # Strategy 3: Look for "Info Kontak" section specifically
            print(f"      🎯 Looking for 'Info Kontak' section...")
            page_content = await page.content()
            
            # Check if "Info Kontak" section exists
            if "info kontak" in page_content.lower():
                print(f"         ✅ 'Info Kontak' section found")
                
                # Extract contact from Info Kontak section
                contact_data = self._extract_from_info_kontak(page_content, username)
                
                if contact_data['whatsapp'] or contact_data['email'] or contact_data['phone']:
                    print(f"         ✅ Contact information extracted!")
                    return {
                        'username': username,
                        'whatsapp': contact_data.get('whatsapp'),
                        'email': contact_data.get('email'),
                        'phone': contact_data.get('phone'),
                        'source': 'info_kontak_section',
                        'confidence': 90,
                        'status': 'success'
                    }
                else:
                    print(f"         ℹ️ 'Info Kontak' section exists but no contact found")
                    return {
                        'username': username,
                        'whatsapp': None,
                        'email': None,
                        'phone': None,
                        'source': 'info_kontak_empty',
                        'confidence': 95,
                        'status': 'no_contact',
                        'reason': 'Info Kontak section exists but contains no contact information'
                    }
            else:
                print(f"         ℹ️ No 'Info Kontak' section found")
                
                # Try general extraction
                contact_data = self._extract_general_patterns(page_content, username)
                
                if contact_data['whatsapp'] or contact_data['email'] or contact_data['phone']:
                    print(f"         ✅ Contact found via general patterns!")
                    return {
                        'username': username,
                        'whatsapp': contact_data.get('whatsapp'),
                        'email': contact_data.get('email'),
                        'phone': contact_data.get('phone'),
                        'source': 'general_patterns',
                        'confidence': 70,
                        'status': 'success'
                    }
                else:
                    print(f"         ℹ️ No contact information found")
                    return {
                        'username': username,
                        'whatsapp': None,
                        'email': None,
                        'phone': None,
                        'source': 'no_extraction',
                        'confidence': 80,
                        'status': 'no_contact',
                        'reason': 'No contact information found on profile page'
                    }
        
        except Exception as e:
            print(f"      ❌ Extraction error: {e}")
            return {
                'username': username,
                'whatsapp': None,
                'email': None,
                'phone': None,
                'source': 'extraction_error',
                'confidence': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def _extract_from_info_kontak(self, html_content: str, username: str) -> Dict[str, Any]:
        """Extract contact from Info Kontak section specifically."""
        
        contact_data = {}
        
        # Look for Info Kontak section and extract surrounding text
        info_kontak_pattern = r'info kontak.*?(?=<|$)'
        info_section_match = re.search(info_kontak_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        if info_section_match:
            info_section = info_section_match.group(0)
            
            # Extract WhatsApp from Info Kontak section
            whatsapp_patterns = [
                r'whatsapp[:\s]*([0-9]{8,15})',
                r'wa[:\s]*([0-9]{8,15})',
                r'([0-9]{10,15})'  # General number in Info Kontak
            ]
            
            for pattern in whatsapp_patterns:
                matches = re.findall(pattern, info_section, re.IGNORECASE)
                if matches:
                    for match in matches:
                        clean_number = re.sub(r'[^\d]', '', str(match))
                        if len(clean_number) >= 8:
                            contact_data['whatsapp'] = clean_number
                            break
                    if contact_data.get('whatsapp'):
                        break
            
            # Extract Email from Info Kontak section
            email_patterns = [
                r'email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, info_section, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if '@' in str(match) and '.' in str(match):
                            contact_data['email'] = str(match)
                            break
                    if contact_data.get('email'):
                        break
        
        return contact_data
    
    def _extract_general_patterns(self, html_content: str, username: str) -> Dict[str, Any]:
        """Extract contact using general patterns across the page."""
        
        contact_data = {}
        
        # WhatsApp patterns
        whatsapp_patterns = [
            r'whatsapp[:\s]*([0-9]{8,15})',
            r'wa[:\s]*([0-9]{8,15})',
            r'wa\.me/([0-9]+)',
            r'(\+62|62|08)[0-9]{8,12}'
        ]
        
        for pattern in whatsapp_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1]
                    
                    clean_number = re.sub(r'[^\d]', '', str(match))
                    if len(clean_number) >= 8:
                        contact_data['whatsapp'] = clean_number
                        break
                if contact_data.get('whatsapp'):
                    break
        
        # Email patterns
        email_patterns = [
            r'email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
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
    
    def _add_to_verified_database(self, username: str, extraction_result: Dict[str, Any]):
        """Add successful extraction to verified database."""
        
        self.database["verified_contacts"][username] = {
            'whatsapp': extraction_result.get('whatsapp'),
            'email': extraction_result.get('email'),
            'phone': extraction_result.get('phone'),
            'verified_date': datetime.now().strftime('%Y-%m-%d'),
            'verification_method': extraction_result.get('source', 'smart_extraction'),
            'confidence': extraction_result.get('confidence', 0),
            'status': 'active'
        }
        
        self._save_database()
        print(f"      💾 Added {username} to verified contacts database")
    
    def _add_to_no_contact_database(self, username: str, extraction_result: Dict[str, Any]):
        """Add no-contact user to database."""
        
        self.database["no_contact_users"][username] = {
            'reason': extraction_result.get('reason', 'No contact information available'),
            'verified_date': datetime.now().strftime('%Y-%m-%d'),
            'verification_method': extraction_result.get('source', 'smart_extraction'),
            'confidence': extraction_result.get('confidence', 0),
            'status': 'confirmed_no_contact'
        }
        
        self._save_database()
        print(f"      💾 Added {username} to no-contact database")
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get database summary."""
        return {
            'total_verified_contacts': len(self.database["verified_contacts"]),
            'total_no_contact_users': len(self.database["no_contact_users"]),
            'database_size': len(self.database["verified_contacts"]) + len(self.database["no_contact_users"]),
            'last_updated': self.database.get("extraction_statistics", {}).get("last_updated", "Never")
        }


async def test_smart_contact_validation():
    """Test the smart contact validation system."""
    
    print("🧠 SMART CONTACT VALIDATION TEST")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    validator = SmartContactValidator()
    
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
        
        # Show database summary
        db_summary = validator.get_database_summary()
        print(f"\n📊 DATABASE SUMMARY:")
        print(f"   Verified contacts: {db_summary['total_verified_contacts']}")
        print(f"   No-contact users: {db_summary['total_no_contact_users']}")
        print(f"   Total database size: {db_summary['database_size']}")
        
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
        
        # Test smart validation on first few creators
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
                        await asyncio.sleep(3)
                        
                        # Handle puzzle if present
                        puzzle_indicators = await detail_page.query_selector_all("[class*='loading']")
                        if puzzle_indicators:
                            print(f"   🧩 Puzzle detected, refreshing...")
                            await detail_page.reload()
                            await asyncio.sleep(5)
                        
                        # Smart contact validation
                        validation_result = await validator.validate_contact(detail_page, creator.username)
                        
                        # Store results
                        results.append(validation_result)
                        
                        # Show results
                        print(f"\n   📋 VALIDATION RESULTS:")
                        print(f"      Status: {validation_result['status']}")
                        print(f"      Source: {validation_result['source']}")
                        print(f"      Confidence: {validation_result['confidence']}%")
                        
                        if validation_result['status'] == 'success':
                            print(f"      WhatsApp: {validation_result['whatsapp'] or 'Not available'}")
                            print(f"      Email: {validation_result['email'] or 'Not available'}")
                        elif validation_result['status'] == 'no_contact':
                            print(f"      Reason: {validation_result.get('reason', 'No contact available')}")
                        elif validation_result['status'] == 'error':
                            print(f"      Error: {validation_result.get('error', 'Unknown error')}")
                        
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
        
        # Final summary
        stats = validator.get_validation_stats()
        db_summary_final = validator.get_database_summary()
        
        print(f"\n📊 SMART VALIDATION SUMMARY:")
        print(f"   Total validated: {stats['total_validated']}")
        print(f"   Found contact: {stats['found_contact']}")
        print(f"   No contact: {stats['no_contact']}")
        print(f"   Extraction errors: {stats['extraction_errors']}")
        
        print(f"\n📈 DATABASE GROWTH:")
        print(f"   Verified contacts: {db_summary_final['total_verified_contacts']}")
        print(f"   No-contact users: {db_summary_final['total_no_contact_users']}")
        print(f"   Total database size: {db_summary_final['database_size']}")
        
        # Detailed results
        if results:
            print(f"\n📋 DETAILED RESULTS:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['username']}")
                print(f"      Status: {result['status']}")
                print(f"      Source: {result['source']}")
                
                if result['status'] == 'success':
                    print(f"      WhatsApp: {result['whatsapp'] or 'Not available'}")
                    print(f"      Email: {result['email'] or 'Not available'}")
                elif result['status'] == 'no_contact':
                    print(f"      Reason: {result.get('reason', 'No contact')}")
                print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"smart_validation_results_{timestamp}.json"
        
        test_summary = {
            "test_info": {
                "test_type": "smart_contact_validation",
                "timestamp": timestamp
            },
            "statistics": stats,
            "database_summary": db_summary_final,
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        print(f"✅ Smart contact validation test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(test_smart_contact_validation())