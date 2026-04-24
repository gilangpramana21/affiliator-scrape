#!/usr/bin/env python3
"""Debug script to inspect actual HTML structure and update selectors."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser

async def debug_page_structure():
    """Debug the actual HTML structure of Tokopedia affiliate page."""
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)  # Non-headless for debugging
        
        # Load cookies
        await browser_engine.load_cookies_from_file("config/cookies.json")
        
        # Navigate to the page
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        page = await browser_engine.navigate(url)
        
        # Wait a bit for page to load
        await asyncio.sleep(5)
        
        # Get HTML
        html = await browser_engine.get_html(page)
        
        # Parse with our parser
        parser = HTMLParser()
        doc = parser.parse(html)
        
        # Save HTML for inspection
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print("HTML saved to debug_page.html")
        
        # Try to find table rows or cards
        possible_selectors = [
            "table tbody tr",
            "tr",
            "div[class*='card']",
            "div[class*='creator']",
            "div[class*='affiliate']",
            "li",
            "[data-testid*='creator']",
            "[data-testid*='card']"
        ]
        
        print("\n=== DEBUGGING SELECTORS ===")
        for selector in possible_selectors:
            elements = parser.select(doc, selector)
            print(f"{selector}: {len(elements)} elements found")
            
            if elements and len(elements) > 1:  # Skip header rows
                # Show first few elements' text content
                for i, elem in enumerate(elements[:3]):
                    text = parser.get_text(elem)[:100]
                    print(f"  [{i}]: {text}...")
        
        # Look for specific text patterns that might indicate creator data
        print("\n=== LOOKING FOR CREATOR DATA PATTERNS ===")
        
        # Search for elements containing numbers that look like follower counts
        import re
        all_text_elements = parser.xpath(doc, "//*[text()]")
        
        for elem in all_text_elements:
            text = parser.get_text(elem)
            # Look for patterns like "1.2K", "500rb", "1JT", etc.
            if re.search(r'\d+[.,]?\d*\s*(rb|jt|k|m|b)', text.lower()):
                print(f"Found metric: '{text}' in <{elem.tag}> with classes: {elem.get('class', 'none')}")
        
        print("\nPress Enter to close browser...")
        input()
        
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(debug_page_structure())