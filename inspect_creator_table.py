#!/usr/bin/env python3
"""Script untuk inspect struktur tabel creator secara detail"""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager

async def inspect_creator_table():
    print("🔍 Inspecting creator table structure in detail...")
    
    # Generate fingerprint
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    
    # Setup browser
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=False)
    
    # Load cookies
    session_manager = SessionManager()
    session_manager.load_session("config/cookies.json")
    
    # Navigate to creator page
    url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
    page = await engine.navigate(url, wait_for="networkidle")
    
    # Apply cookies
    cookies = session_manager.get_cookies()
    for cookie in cookies:
        await page.context.add_cookies([{
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
            'httpOnly': cookie.http_only,
            'secure': cookie.secure
        }])
    
    await page.reload(wait_until="networkidle")
    
    print("✅ Page loaded")
    
    # Find the table
    tables = await page.query_selector_all("table")
    print(f"\n📊 Found {len(tables)} tables")
    
    for table_idx, table in enumerate(tables):
        print(f"\n{'='*60}")
        print(f"TABLE {table_idx + 1}")
        print('='*60)
        
        # Get headers
        headers = await table.query_selector_all("thead th")
        if headers:
            header_texts = []
            for h in headers:
                text = await h.inner_text()
                header_texts.append(text.strip())
            print(f"📋 Headers ({len(header_texts)}): {header_texts}")
        
        # Get data rows
        rows = await table.query_selector_all("tbody tr")
        print(f"📝 Data rows: {len(rows)}")
        
        if rows:
            # Inspect first 3 rows in detail
            for row_idx, row in enumerate(rows[:3]):
                print(f"\n  🔍 ROW {row_idx + 1}:")
                
                # Get all cells
                cells = await row.query_selector_all("td")
                print(f"    Cells: {len(cells)}")
                
                for cell_idx, cell in enumerate(cells):
                    # Get cell text
                    text = await cell.inner_text()
                    text_clean = text.strip().replace('\n', ' ')[:80]
                    print(f"    Cell {cell_idx + 1}: {text_clean}")
                    
                    # Check for links in this cell
                    links = await cell.query_selector_all("a")
                    if links:
                        for link in links:
                            href = await link.get_attribute("href")
                            link_text = await link.inner_text()
                            print(f"      🔗 Link: '{link_text.strip()[:30]}' -> {href}")
                    
                    # Check for buttons
                    buttons = await cell.query_selector_all("button")
                    if buttons:
                        for btn in buttons:
                            btn_text = await btn.inner_text()
                            print(f"      🔘 Button: '{btn_text.strip()[:30]}'")
                
                # Get row HTML for analysis
                row_html = await row.inner_html()
                print(f"    HTML length: {len(row_html)} chars")
    
    # Also check for card-based layout
    print(f"\n{'='*60}")
    print("CHECKING FOR CARD LAYOUT")
    print('='*60)
    
    cards = await page.query_selector_all("div[class*='card']")
    print(f"📦 Found {len(cards)} card elements")
    
    if cards:
        # Inspect first card
        first_card = cards[0]
        print("\n🔍 First card structure:")
        
        # Get all text content
        card_text = await first_card.inner_text()
        print(f"  Text: {card_text[:200]}...")
        
        # Look for links
        card_links = await first_card.query_selector_all("a")
        print(f"  Links: {len(card_links)}")
        for link in card_links[:3]:
            href = await link.get_attribute("href")
            link_text = await link.inner_text()
            print(f"    🔗 '{link_text.strip()[:30]}' -> {href}")
        
        # Look for common data elements
        data_elements = await first_card.query_selector_all("span, div, p")
        print(f"  Data elements: {len(data_elements)}")
        
        # Try to find username/name
        for elem in data_elements[:10]:
            text = await elem.inner_text()
            if text and 10 < len(text.strip()) < 50:
                print(f"    📝 {text.strip()}")
    
    # Save page HTML for offline analysis
    html_content = await page.content()
    with open("creator_page.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("\n💾 Page HTML saved to: creator_page.html")
    
    # Take screenshot
    await page.screenshot(path="creator_table.png", full_page=True)
    print("📸 Screenshot saved to: creator_table.png")
    
    print("\n⏳ Browser window open for manual inspection...")
    print("   Inspect the page structure and elements...")
    print("   Press Enter when done...")
    input()
    
    await engine.close()
    print("✅ Inspection completed")

if __name__ == "__main__":
    asyncio.run(inspect_creator_table())