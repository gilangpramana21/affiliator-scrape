#!/usr/bin/env python3
"""Debug script untuk melihat struktur tabel dan link creator."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def debug_table_structure():
    """Debug struktur tabel untuk menemukan link creator."""
    
    print("🔍 DEBUG TABLE STRUCTURE")
    print("=" * 40)
    
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
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
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
        
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded")
        
        print("\n🔍 ANALYZING TABLE STRUCTURE:")
        
        # Get all table rows
        rows = await page.query_selector_all("tr")
        print(f"   Total rows: {len(rows)}")
        
        # Analyze first few data rows (skip header)
        for i, row in enumerate(rows[1:4], 1):  # Check first 3 data rows
            print(f"\n   📋 Row {i}:")
            
            # Get all cells in this row
            cells = await row.query_selector_all("td")
            print(f"      Cells: {len(cells)}")
            
            # Check each cell for links
            for j, cell in enumerate(cells, 1):
                # Look for links in this cell
                links = await cell.query_selector_all("a")
                
                if links:
                    print(f"      Cell {j} has {len(links)} link(s):")
                    
                    for k, link in enumerate(links, 1):
                        try:
                            href = await link.get_attribute('href')
                            text = await link.inner_text()
                            
                            print(f"         Link {k}:")
                            print(f"            href: {href}")
                            print(f"            text: {text[:30] if text else 'N/A'}")
                        except:
                            pass
        
        # Try to find all links in the table
        print(f"\n🔍 ALL LINKS IN TABLE:")
        all_links = await page.query_selector_all("table a")
        print(f"   Total links found: {len(all_links)}")
        
        if all_links:
            print(f"\n   First 5 links:")
            for i, link in enumerate(all_links[:5], 1):
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    target = await link.get_attribute('target')
                    
                    print(f"\n   {i}. {text[:30] if text else 'N/A'}")
                    print(f"      href: {href}")
                    print(f"      target: {target}")
                except:
                    pass
        
        # Check if links open in new tab
        print(f"\n🔍 CHECKING LINK BEHAVIOR:")
        print("   Looking for links with target='_blank'...")
        
        new_tab_links = await page.query_selector_all("a[target='_blank']")
        print(f"   Found {len(new_tab_links)} links with target='_blank'")
        
        # Interactive testing
        print(f"\n🖱️  INTERACTIVE TESTING:")
        print("   You can now manually click on a creator in the browser")
        print("   to see how it behaves (new tab, same tab, etc.)")
        print("   Press Enter when done...")
        input()
        
        # Check how many tabs are open
        context = page.context
        pages = context.pages
        print(f"\n   Current tabs open: {len(pages)}")
        
        if len(pages) > 1:
            print(f"   ✅ New tab was opened!")
            print(f"   Tab URLs:")
            for i, p in enumerate(pages, 1):
                print(f"      {i}. {p.url}")
        else:
            print(f"   ⚠️  No new tab opened")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n⏳ Press Enter to close...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(debug_table_structure())