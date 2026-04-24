#!/usr/bin/env python3
"""Test untuk menemukan cara navigasi ke halaman detail creator."""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_find_detail_navigation():
    """Test untuk menemukan cara navigasi ke halaman detail."""
    
    print("🔍 Testing Detail Page Navigation Methods")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        print("\n🔍 ANALYZING PAGE STRUCTURE...")
        
        # Method 1: Look for any elements with creator IDs or detail URLs
        print("\n1️⃣ Looking for elements with creator IDs or detail URLs:")
        
        # Check all elements for data attributes that might contain creator IDs
        all_elements = await page.query_selector_all("*[data-*]")
        print(f"   Found {len(all_elements)} elements with data attributes")
        
        creator_id_patterns = []
        for i, elem in enumerate(all_elements[:20]):  # Check first 20
            try:
                # Get all data attributes
                data_attrs = await elem.evaluate("el => Object.keys(el.dataset)")
                if data_attrs:
                    for attr in data_attrs:
                        value = await elem.get_attribute(f"data-{attr}")
                        if value and (len(value) > 10 or 'creator' in attr.lower() or 'id' in attr.lower()):
                            creator_id_patterns.append(f"data-{attr}: {value}")
                            print(f"   🔍 Element {i}: data-{attr}='{value}'")
            except:
                continue
        
        # Method 2: Look for JavaScript event handlers
        print("\n2️⃣ Looking for JavaScript event handlers:")
        
        # Check for onclick handlers
        onclick_elements = await page.query_selector_all("*[onclick]")
        print(f"   Found {len(onclick_elements)} elements with onclick")
        
        for i, elem in enumerate(onclick_elements[:10]):
            try:
                onclick = await elem.get_attribute("onclick")
                if onclick:
                    print(f"   🖱️  Element {i}: onclick='{onclick[:100]}...'")
            except:
                continue
        
        # Method 3: Check table structure more carefully
        print("\n3️⃣ Analyzing table structure:")
        
        rows = await page.query_selector_all("tr")
        print(f"   Found {len(rows)} table rows")
        
        for i, row in enumerate(rows[1:4], 1):  # Check first 3 data rows
            try:
                print(f"\n   📋 Row {i} analysis:")
                
                # Get all cells
                cells = await row.query_selector_all("td")
                print(f"      Cells: {len(cells)}")
                
                # Check each cell for clickable elements
                for j, cell in enumerate(cells):
                    # Look for any interactive elements
                    links = await cell.query_selector_all("a")
                    buttons = await cell.query_selector_all("button")
                    clickable = await cell.query_selector_all("[onclick]")
                    
                    if links or buttons or clickable:
                        print(f"      Cell {j}: {len(links)} links, {len(buttons)} buttons, {len(clickable)} onclick")
                        
                        # Check link hrefs
                        for link in links:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            print(f"        🔗 Link: '{text[:20]}' -> {href}")
                        
                        # Check button attributes
                        for button in buttons:
                            text = await button.inner_text()
                            onclick = await button.get_attribute("onclick")
                            data_attrs = await button.evaluate("el => Object.keys(el.dataset)")
                            print(f"        🔘 Button: '{text[:20]}' onclick='{onclick}' data={data_attrs}")
                
                # Check if row itself has any special attributes
                row_attrs = await row.evaluate("el => Array.from(el.attributes).map(attr => attr.name + '=' + attr.value)")
                if row_attrs:
                    print(f"      Row attributes: {row_attrs[:3]}")  # Show first 3
                
            except Exception as e:
                print(f"      ❌ Error analyzing row {i}: {e}")
        
        # Method 4: Look for AJAX/API calls patterns
        print("\n4️⃣ Looking for potential API endpoints:")
        
        # Check page source for API patterns
        page_content = await page.content()
        
        # Look for API endpoints in the page source
        api_patterns = [
            r'/api/[^"\']*creator[^"\']*',
            r'/connection/creator/[^"\']*',
            r'creator[^"\']*detail[^"\']*',
            r'detail[^"\']*creator[^"\']*'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                print(f"   🔍 Pattern '{pattern}' found {len(matches)} matches:")
                for match in matches[:5]:  # Show first 5
                    print(f"      {match}")
        
        # Method 5: Try to find creator IDs in the page
        print("\n5️⃣ Looking for creator IDs in page content:")
        
        # Look for long numeric IDs that might be creator IDs
        id_patterns = [
            r'\b\d{15,20}\b',  # Long numeric IDs
            r'cid[=:]\s*["\']?(\d+)["\']?',  # cid parameter
            r'creator[_-]?id[=:]\s*["\']?(\d+)["\']?'  # creator_id parameter
        ]
        
        for pattern in id_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                print(f"   🆔 Pattern '{pattern}' found {len(matches)} matches:")
                for match in matches[:10]:  # Show first 10
                    print(f"      {match}")
        
        # Method 6: Manual interaction test
        print("\n6️⃣ Manual interaction test:")
        print("   🖱️  Try clicking on different parts of the creator rows manually")
        print("   🔍 Look for any popups, modals, or navigation")
        print("   📝 Check browser developer tools for network requests")
        
        print("\n⏳ Browser window open for manual testing...")
        print("   Try clicking on creator names, avatars, or any other elements")
        print("   Check if any modals or detail pages open")
        print("   Press Enter when done...")
        input()
        
        # After manual testing, check current URL
        final_url = page.url
        print(f"\n🌐 Final URL: {final_url}")
        
        if "detail" in final_url:
            print("✅ Successfully navigated to detail page!")
            
            # Extract contact info from detail page
            print("\n📱 Extracting contact info from detail page...")
            
            # Look for WhatsApp
            whatsapp_elements = await page.query_selector_all("*:has-text('WhatsApp'), *:has-text('085'), *:has-text('08')")
            for elem in whatsapp_elements[:5]:
                text = await elem.inner_text()
                phone_match = re.search(r'(08\d{8,12}|\+62\d{8,12}|62\d{8,12})', text)
                if phone_match:
                    print(f"   📱 WhatsApp found: {phone_match.group(1)}")
            
            # Look for Email
            email_elements = await page.query_selector_all("*:has-text('Email'), *:has-text('@')")
            for elem in email_elements[:5]:
                text = await elem.inner_text()
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    print(f"   📧 Email found: {email_match.group(0)}")
        
    except Exception as e:
        print(f"\n❌ Error during navigation test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(test_find_detail_navigation())