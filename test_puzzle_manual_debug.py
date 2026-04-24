#!/usr/bin/env python3
"""
Manual debug script untuk inspect Tokopedia puzzle behavior.

Script ini membuka browser dan memungkinkan manual inspection:
1. Navigate ke creator detail page
2. Observe puzzle behavior
3. Test detection methods
4. Manual refresh testing

Usage: python test_puzzle_manual_debug.py
"""

import asyncio
import logging
from typing import Dict, List

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.captcha_handler import CAPTCHAHandler
from src.core.html_parser import HTMLParser
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.session_manager import SessionManager
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def manual_puzzle_debug():
    """Manual debug session untuk observe puzzle behavior."""
    
    print("🔍 MANUAL TOKOPEDIA PUZZLE DEBUG SESSION")
    print("=" * 50)
    print("This will open a browser for manual inspection of puzzle behavior")
    print("You can manually navigate and observe how puzzles appear/disappear")
    
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
        # Launch browser (visible)
        print("\n🚀 Launching browser (visible mode)...")
        await browser_engine.launch(fingerprint, headless=False)
        
        # Load cookies
        print("🍪 Loading cookies...")
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
        print("\n📋 Navigating to creator list...")
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        main_page = await browser_engine.navigate(url)
        await asyncio.sleep(3)
        
        # Extract creators for testing
        print("👥 Extracting creators...")
        html = await browser_engine.get_html(main_page)
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        
        if not result.affiliators:
            print("❌ No creators found!")
            return
        
        creators = result.affiliators[:5]  # First 5 for testing
        print(f"   ✅ Found {len(creators)} creators for testing")
        
        # Show available creators
        print(f"\n📋 Available creators for testing:")
        for i, creator in enumerate(creators, 1):
            print(f"   {i}. {creator.username} - {creator.detail_url}")
        
        # Interactive debug loop
        while True:
            print(f"\n" + "="*60)
            print("🔧 DEBUG COMMANDS:")
            print("   1-5: Test creator by number")
            print("   'detect': Test puzzle detection on current page")
            print("   'solve': Test puzzle solving on current page")
            print("   'refresh': Refresh current page")
            print("   'content': Show page content summary")
            print("   'new': Open new tab to creator detail")
            print("   'close': Close current detail tab")
            print("   'quit': Exit debug session")
            
            command = input("\nEnter command: ").strip().lower()
            
            if command == 'quit':
                break
            
            elif command in ['1', '2', '3', '4', '5']:
                try:
                    creator_idx = int(command) - 1
                    if 0 <= creator_idx < len(creators):
                        creator = creators[creator_idx]
                        await debug_creator(browser_engine, captcha_handler, parser, extractor, creator)
                    else:
                        print("❌ Invalid creator number")
                except ValueError:
                    print("❌ Invalid number")
            
            elif command == 'detect':
                await debug_detection(browser_engine, captcha_handler)
            
            elif command == 'solve':
                await debug_solving(browser_engine, captcha_handler)
            
            elif command == 'refresh':
                await debug_refresh(browser_engine)
            
            elif command == 'content':
                await debug_content_summary(browser_engine, parser)
            
            elif command == 'new':
                print("Enter creator number (1-5) or URL:")
                target = input().strip()
                
                if target.isdigit() and 1 <= int(target) <= 5:
                    creator = creators[int(target) - 1]
                    await debug_new_tab(browser_engine, creator.detail_url)
                elif target.startswith('http'):
                    await debug_new_tab(browser_engine, target)
                else:
                    print("❌ Invalid input")
            
            elif command == 'close':
                await debug_close_tab(browser_engine)
            
            else:
                print("❌ Unknown command")
        
    except Exception as e:
        print(f"\n❌ Debug session error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n🧹 Closing browser...")
        await browser_engine.close()


async def debug_creator(browser_engine, captcha_handler, parser, extractor, creator):
    """Debug specific creator."""
    
    print(f"\n🔍 DEBUGGING CREATOR: {creator.username}")
    print(f"   URL: {creator.detail_url}")
    
    try:
        # Open in new tab
        detail_page = await browser_engine.context.new_page()
        
        print("   📂 Opening detail page...")
        await detail_page.goto(creator.detail_url)
        await asyncio.sleep(3)
        
        # Test detection
        print("   🧩 Testing puzzle detection...")
        puzzle_detected = await captcha_handler.detect_tokopedia_puzzle(detail_page)
        print(f"      Result: {'🧩 PUZZLE DETECTED' if puzzle_detected else '✅ No puzzle'}")
        
        # Show page info
        title = await detail_page.title()
        content = await detail_page.content()
        
        print(f"   📄 Page info:")
        print(f"      Title: {title}")
        print(f"      Content length: {len(content):,} chars")
        
        # Test extraction
        print("   📊 Testing data extraction...")
        try:
            doc = parser.parse(content)
            detail_data = extractor.extract_detail_page(doc, page_url=creator.detail_url)
            
            print(f"      Username: {detail_data.username or 'Not found'}")
            print(f"      Contact: {detail_data.nomor_kontak or 'Not found'}")
            print(f"      Kategori: {detail_data.kategori or 'Not found'}")
            
        except Exception as e:
            print(f"      ❌ Extraction error: {e}")
        
        # Keep tab open for manual inspection
        print(f"   👀 Tab opened for manual inspection")
        print(f"      You can manually inspect the page in the browser")
        print(f"      Use 'close' command to close this tab")
        
    except Exception as e:
        print(f"   ❌ Error debugging creator: {e}")


async def debug_detection(browser_engine, captcha_handler):
    """Debug puzzle detection on current page."""
    
    print(f"\n🔍 TESTING PUZZLE DETECTION...")
    
    try:
        # Get current page (assume last opened)
        pages = browser_engine.context.pages
        if not pages:
            print("   ❌ No pages open")
            return
        
        current_page = pages[-1]  # Last page
        
        # Test detection
        puzzle_detected = await captcha_handler.detect_tokopedia_puzzle(current_page)
        
        print(f"   Result: {'🧩 PUZZLE DETECTED' if puzzle_detected else '✅ No puzzle detected'}")
        
        # Show detection details
        url = current_page.url
        title = await current_page.title()
        
        print(f"   Page: {title}")
        print(f"   URL: {url}")
        
        # Test individual detection methods
        print(f"\n   🔬 Detailed detection analysis:")
        
        # Check for puzzle indicators
        puzzle_indicators = [
            'div[class*="puzzle"]',
            'div[class*="challenge"]',
            'div[class*="verification"]',
            'div[class*="captcha-container"]',
            'div[class*="anti-bot"]',
        ]
        
        for selector in puzzle_indicators:
            try:
                element = await current_page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    print(f"      {selector}: {'✅ Found (visible)' if is_visible else '⚠️ Found (hidden)'}")
                else:
                    print(f"      {selector}: ❌ Not found")
            except Exception:
                print(f"      {selector}: ❌ Query failed")
        
        # Check profile indicators
        profile_indicators = [
            'div[class*="creator-profile"]',
            'span[class*="follower"]',
            'div[class*="contact"]',
        ]
        
        profile_count = 0
        for selector in profile_indicators:
            try:
                element = await current_page.query_selector(selector)
                if element and await element.is_visible():
                    profile_count += 1
            except Exception:
                pass
        
        print(f"      Profile elements found: {profile_count}")
        
    except Exception as e:
        print(f"   ❌ Detection test error: {e}")


async def debug_solving(browser_engine, captcha_handler):
    """Debug puzzle solving on current page."""
    
    print(f"\n🔄 TESTING PUZZLE SOLVING...")
    
    try:
        pages = browser_engine.context.pages
        if not pages:
            print("   ❌ No pages open")
            return
        
        current_page = pages[-1]
        
        # Test solving
        success = await captcha_handler.solve_tokopedia_puzzle(current_page)
        
        print(f"   Result: {'✅ SOLVED' if success else '❌ FAILED'}")
        
        # Show consecutive count
        consecutive = captcha_handler.consecutive_puzzle_count
        print(f"   Consecutive puzzle count: {consecutive}")
        
    except Exception as e:
        print(f"   ❌ Solving test error: {e}")


async def debug_refresh(browser_engine):
    """Debug page refresh."""
    
    print(f"\n🔄 REFRESHING CURRENT PAGE...")
    
    try:
        pages = browser_engine.context.pages
        if not pages:
            print("   ❌ No pages open")
            return
        
        current_page = pages[-1]
        
        print(f"   Before refresh: {current_page.url}")
        
        await current_page.reload(wait_until="networkidle")
        await asyncio.sleep(3)
        
        print(f"   ✅ Page refreshed")
        
    except Exception as e:
        print(f"   ❌ Refresh error: {e}")


async def debug_content_summary(browser_engine, parser):
    """Debug page content summary."""
    
    print(f"\n📄 PAGE CONTENT SUMMARY...")
    
    try:
        pages = browser_engine.context.pages
        if not pages:
            print("   ❌ No pages open")
            return
        
        current_page = pages[-1]
        
        # Get content
        content = await current_page.content()
        title = await current_page.title()
        url = current_page.url
        
        print(f"   Title: {title}")
        print(f"   URL: {url}")
        print(f"   Content length: {len(content):,} chars")
        
        # Check for keywords
        keywords = ['puzzle', 'challenge', 'verification', 'creator', 'profile', 'follower', 'contact']
        
        print(f"   Keyword analysis:")
        for keyword in keywords:
            count = content.lower().count(keyword)
            print(f"      '{keyword}': {count} occurrences")
        
        # Parse and check elements
        doc = parser.parse(content)
        
        # Count common elements
        tables = parser.select(doc, "table")
        divs = parser.select(doc, "div")
        spans = parser.select(doc, "span")
        
        print(f"   Element counts:")
        print(f"      Tables: {len(tables)}")
        print(f"      Divs: {len(divs)}")
        print(f"      Spans: {len(spans)}")
        
    except Exception as e:
        print(f"   ❌ Content analysis error: {e}")


async def debug_new_tab(browser_engine, url):
    """Debug opening new tab."""
    
    print(f"\n📂 OPENING NEW TAB...")
    print(f"   URL: {url}")
    
    try:
        new_page = await browser_engine.context.new_page()
        await new_page.goto(url)
        await asyncio.sleep(3)
        
        title = await new_page.title()
        print(f"   ✅ New tab opened: {title}")
        
    except Exception as e:
        print(f"   ❌ New tab error: {e}")


async def debug_close_tab(browser_engine):
    """Debug closing current tab."""
    
    print(f"\n🗑️ CLOSING CURRENT TAB...")
    
    try:
        pages = browser_engine.context.pages
        if len(pages) <= 1:
            print("   ❌ Cannot close last page")
            return
        
        current_page = pages[-1]
        title = await current_page.title()
        
        await current_page.close()
        
        print(f"   ✅ Closed tab: {title}")
        
    except Exception as e:
        print(f"   ❌ Close tab error: {e}")


if __name__ == "__main__":
    print("🔍 MANUAL TOKOPEDIA PUZZLE DEBUG")
    print("This will open an interactive debug session")
    print("You can manually test puzzle detection and solving")
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    
    if confirm == 'y':
        asyncio.run(manual_puzzle_debug())
    else:
        print("Debug session cancelled")