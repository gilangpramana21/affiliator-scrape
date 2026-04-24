#!/usr/bin/env python3
"""
Debug script untuk inspect actual Tokopedia page structure.

Akan membuka browser dan inspect:
1. Table structure
2. Link patterns
3. JavaScript navigation
4. Data attributes
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


async def debug_page_structure():
    """Debug actual page structure."""
    
    print("🔍 DEBUGGING TOKOPEDIA PAGE STRUCTURE")
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
        # Launch browser (visible)
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
        print(f"\n🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        # Get page HTML
        html = await page.content()
        doc = parser.parse(html)
        
        print(f"\n📄 Page loaded, HTML length: {len(html):,} chars")
        
        # Analyze table structure
        print(f"\n📊 ANALYZING TABLE STRUCTURE:")
        tables = parser.select(doc, "table")
        print(f"   Tables found: {len(tables)}")
        
        if tables:
            table = tables[0]  # First table
            
            # Headers
            headers = parser.select(table, "thead th")
            print(f"   Headers: {len(headers)}")
            for i, header in enumerate(headers):
                text = parser.get_text(header)
                print(f"      {i+1}. {text}")
            
            # Data rows
            rows = parser.select(table, "tbody tr")
            print(f"   Data rows: {len(rows)}")
            
            if rows:
                # Analyze first few rows
                for i, row in enumerate(rows[:3], 1):
                    print(f"\n   🔍 ROW {i} ANALYSIS:")
                    
                    cells = parser.select(row, "td")
                    print(f"      Cells: {len(cells)}")
                    
                    for j, cell in enumerate(cells):
                        text = parser.get_text(cell)[:100]
                        print(f"         Cell {j+1}: {text}")
                        
                        # Check for links
                        links = parser.select(cell, "a")
                        if links:
                            for k, link in enumerate(links):
                                href = parser.get_attribute(link, "href")
                                onclick = parser.get_attribute(link, "onclick")
                                data_attrs = []
                                
                                # Check for data attributes
                                link_html = str(link)
                                import re
                                data_matches = re.findall(r'data-[\w-]+="[^"]*"', link_html)
                                
                                print(f"            Link {k+1}:")
                                print(f"               href: {href}")
                                print(f"               onclick: {onclick}")
                                if data_matches:
                                    print(f"               data attrs: {data_matches}")
                        
                        # Check for buttons
                        buttons = parser.select(cell, "button")
                        if buttons:
                            for k, button in enumerate(buttons):
                                onclick = parser.get_attribute(button, "onclick")
                                data_attrs = []
                                
                                button_html = str(button)
                                data_matches = re.findall(r'data-[\w-]+="[^"]*"', button_html)
                                
                                print(f"            Button {k+1}:")
                                print(f"               onclick: {onclick}")
                                if data_matches:
                                    print(f"               data attrs: {data_matches}")
        
        # Check for JavaScript navigation patterns
        print(f"\n🔧 CHECKING JAVASCRIPT PATTERNS:")
        
        # Look for common JS navigation patterns
        js_patterns = [
            "window.open",
            "location.href",
            "router.push",
            "navigate",
            "redirect"
        ]
        
        for pattern in js_patterns:
            if pattern in html:
                print(f"   ✅ Found pattern: {pattern}")
            else:
                print(f"   ❌ Not found: {pattern}")
        
        # Check for data attributes that might contain URLs
        print(f"\n📋 CHECKING DATA ATTRIBUTES:")
        
        import re
        
        data_patterns = [
            r'data-url="([^"]*)"',
            r'data-href="([^"]*)"',
            r'data-link="([^"]*)"',
            r'data-creator="([^"]*)"',
            r'data-profile="([^"]*)"'
        ]
        
        for pattern in data_patterns:
            matches = re.findall(pattern, html)
            if matches:
                print(f"   ✅ Found {pattern}: {len(matches)} matches")
                for match in matches[:3]:  # Show first 3
                    print(f"      {match}")
            else:
                print(f"   ❌ Not found: {pattern}")
        
        # Interactive inspection
        print(f"\n👀 INTERACTIVE INSPECTION:")
        print("   Browser window is open for manual inspection")
        print("   You can:")
        print("   - Inspect elements manually")
        print("   - Check network tab for AJAX calls")
        print("   - Look for click handlers")
        
        input("\nPress Enter when done inspecting...")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(debug_page_structure())