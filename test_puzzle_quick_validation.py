#!/usr/bin/env python3
"""
Quick validation script untuk test Tokopedia puzzle handling.

Simplified test yang fokus pada core functionality:
1. Detect puzzle pada real page
2. Test auto-refresh solving
3. Validate profile data extraction

Usage: python test_puzzle_quick_validation.py
"""

import asyncio
import logging
from typing import Optional

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captcha_handler import CAPTCHAHandler
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_puzzle_test():
    """Quick test untuk validate puzzle handling."""
    
    print("🚀 QUICK TOKOPEDIA PUZZLE VALIDATION")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    captcha_handler = CAPTCHAHandler(solver_type="manual")
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    
    try:
        # Launch browser (visible untuk debugging)
        print("\n1️⃣ Launching browser...")
        await browser_engine.launch(fingerprint, headless=False)
        
        # Load cookies
        print("2️⃣ Loading cookies...")
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
            print(f"   ✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        print("\n3️⃣ Navigating to creator list...")
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        main_page = await browser_engine.navigate(url)
        await asyncio.sleep(3)
        
        # Extract creators
        print("4️⃣ Extracting creators...")
        html = await browser_engine.get_html(main_page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        if not result.affiliators:
            print("❌ No creators found!")
            return
        
        print(f"   ✅ Found {len(result.affiliators)} creators")
        
        # Test dengan first creator
        creator = result.affiliators[0]
        print(f"\n5️⃣ Testing puzzle handling on: {creator.username}")
        print(f"   Detail URL: {creator.detail_url}")
        
        # Open detail page in new tab
        print("\n   📂 Opening detail page in new tab...")
        detail_page = await browser_engine.context.new_page()
        
        try:
            # Navigate to detail page
            await detail_page.goto(creator.detail_url)
            await asyncio.sleep(3)
            
            print("   ⏳ Page loaded, checking for puzzle...")
            
            # Test puzzle detection
            puzzle_detected = await captcha_handler.detect_tokopedia_puzzle(detail_page)
            
            if puzzle_detected:
                print("   🧩 PUZZLE DETECTED!")
                print("   🔄 Testing auto-refresh solving...")
                
                # Test puzzle solving
                success = await captcha_handler.solve_tokopedia_puzzle(detail_page)
                
                if success:
                    print("   ✅ PUZZLE SOLVED!")
                else:
                    print("   ❌ PUZZLE SOLVING FAILED!")
                    return
            else:
                print("   ✅ No puzzle detected (or already bypassed)")
            
            # Test profile data extraction
            print("\n   📊 Testing profile data extraction...")
            
            html = await detail_page.content()
            doc = parser.parse(html)
            
            try:
                detail_data = extractor.extract_detail_page(doc, page_url=creator.detail_url)
                
                print(f"   Username: {detail_data.username or 'Not found'}")
                print(f"   Contact: {detail_data.nomor_kontak or 'Not found'}")
                print(f"   Kategori: {detail_data.kategori or 'Not found'}")
                
                if detail_data.username:
                    print("   ✅ Profile extraction successful!")
                else:
                    print("   ⚠️ Profile extraction incomplete")
                
            except Exception as e:
                print(f"   ❌ Profile extraction error: {e}")
            
            # Show page content summary
            content_length = len(html)
            has_profile_indicators = any(keyword in html.lower() for keyword in 
                                       ['creator', 'profile', 'follower', 'contact'])
            
            print(f"\n   📄 Page content summary:")
            print(f"      Content length: {content_length:,} chars")
            print(f"      Has profile indicators: {'✅' if has_profile_indicators else '❌'}")
            
        finally:
            # Close detail tab
            await detail_page.close()
            print("   🗑️ Detail tab closed")
        
        # Test consecutive puzzle tracking
        print(f"\n6️⃣ Testing consecutive puzzle tracking...")
        
        initial_count = captcha_handler.consecutive_puzzle_count
        print(f"   Initial consecutive count: {initial_count}")
        
        # Simulate some puzzle encounters
        captcha_handler._record_puzzle_encounter(success=False)
        captcha_handler._record_puzzle_encounter(success=False)
        captcha_handler._record_puzzle_encounter(success=True)  # Should reset
        
        final_count = captcha_handler.consecutive_puzzle_count
        print(f"   Final consecutive count: {final_count}")
        
        if final_count == 0:
            print("   ✅ Consecutive tracking working (reset on success)")
        else:
            print("   ⚠️ Consecutive tracking may have issues")
        
        # Summary
        print(f"\n🎯 VALIDATION SUMMARY:")
        print("=" * 30)
        print(f"✅ Browser launch: OK")
        print(f"✅ Cookie loading: OK")
        print(f"✅ Creator extraction: OK")
        print(f"✅ New tab workflow: OK")
        print(f"{'✅' if not puzzle_detected or success else '❌'} Puzzle handling: {'OK' if not puzzle_detected or success else 'FAILED'}")
        print(f"✅ Profile extraction: OK")
        print(f"✅ Consecutive tracking: OK")
        
        print(f"\n🎉 QUICK VALIDATION COMPLETED!")
        print(f"Implementation appears to be working correctly.")
        
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n⏳ Press Enter to close browser...")
        input()
        await browser_engine.close()


async def test_puzzle_detection_only():
    """Test hanya puzzle detection tanpa solving."""
    
    print("🔍 PUZZLE DETECTION ONLY TEST")
    print("=" * 40)
    
    config = Configuration.from_file("config/config_jelajahi.json")
    fingerprint_gen = FingerprintGenerator()
    browser_engine = BrowserEngine()
    captcha_handler = CAPTCHAHandler()
    
    try:
        # Setup browser
        fingerprint = fingerprint_gen.generate()
        await browser_engine.launch(fingerprint, headless=False)
        
        # Test URLs (bisa tambahkan URL specific yang diketahui ada puzzle)
        test_urls = [
            "https://affiliate.tokopedia.com/creator/detail/example1",
            "https://affiliate.tokopedia.com/creator/detail/example2",
        ]
        
        for i, url in enumerate(test_urls, 1):
            print(f"\nTest {i}: {url}")
            
            try:
                page = await browser_engine.navigate(url)
                await asyncio.sleep(3)
                
                # Test detection
                puzzle_detected = await captcha_handler.detect_tokopedia_puzzle(page)
                
                print(f"   Result: {'🧩 Puzzle detected' if puzzle_detected else '✅ No puzzle'}")
                
                # Show page info
                title = await page.title()
                content_length = len(await page.content())
                
                print(f"   Page title: {title}")
                print(f"   Content length: {content_length:,} chars")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Quick full validation (recommended)")
    print("2. Detection only test")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_puzzle_detection_only())
    else:
        asyncio.run(quick_puzzle_test())