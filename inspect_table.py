#!/usr/bin/env python3
"""Script untuk inspect struktur tabel affiliator"""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def inspect_table():
    print("🔍 Inspecting table structure...")
    
    # Load config and cookies
    config = Configuration.from_file("config/config.safe.json")
    
    # Generate fingerprint
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    
    # Setup browser
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=False)
    
    # Load cookies
    session_manager = SessionManager()
    session_manager.load_session(config.cookie_file)
    
    # Navigate to page
    url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
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
    
    print("✅ Page loaded, inspecting table structure...")
    
    # Find all tables
    tables = await page.query_selector_all("table")
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"\n🔍 Table {i+1}:")
        
        # Get table headers
        headers = await table.query_selector_all("th")
        if headers:
            header_texts = []
            for header in headers:
                text = await header.inner_text()
                header_texts.append(text.strip())
            print(f"  📋 Headers: {header_texts}")
        
        # Get table rows
        rows = await table.query_selector_all("tbody tr")
        print(f"  📝 Data rows: {len(rows)}")
        
        if rows:
            # Inspect first few rows
            for j, row in enumerate(rows[:3]):  # First 3 rows
                cells = await row.query_selector_all("td")
                cell_texts = []
                for cell in cells:
                    text = await cell.inner_text()
                    cell_texts.append(text.strip()[:50])  # First 50 chars
                print(f"    Row {j+1}: {cell_texts}")
                
                # Check for links in this row
                links = await row.query_selector_all("a")
                if links:
                    for link in links:
                        href = await link.get_attribute("href")
                        link_text = await link.inner_text()
                        print(f"      🔗 Link: '{link_text.strip()}' -> {href}")
    
    # Check for other potential containers
    print("\n🔍 Checking other potential containers:")
    
    containers = [
        "div[class*='creator']",
        "div[class*='affiliate']", 
        "div[class*='table']",
        "div[data-testid*='creator']",
        "div[data-testid*='affiliate']",
        ".data-table",
        ".creator-list",
        ".affiliate-list"
    ]
    
    for selector in containers:
        elements = await page.query_selector_all(selector)
        if elements:
            print(f"  ✅ Found {len(elements)} elements: {selector}")
            # Get sample text from first element
            if elements:
                sample_text = await elements[0].inner_text()
                print(f"    Sample: {sample_text[:100]}...")
    
    print("\n⏳ Browser window open for manual inspection...")
    print("   Press Enter when done...")
    input()
    
    await engine.close()
    print("✅ Inspection completed")

if __name__ == "__main__":
    asyncio.run(inspect_table())