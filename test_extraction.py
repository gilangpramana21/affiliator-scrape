#!/usr/bin/env python3
"""Simple test to extract data manually and see what we get."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.affiliator_extractor import AffiliatorExtractor

async def test_extraction():
    """Test data extraction manually."""
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=True)
        
        # Load cookies
        await browser_engine.load_cookies_from_file("config/cookies.json")
        
        # Navigate to the page
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        page = await browser_engine.navigate(url)
        
        # Wait a bit for page to load
        await asyncio.sleep(3)
        
        # Get HTML
        html = await browser_engine.get_html(page)
        
        # Parse with our parser
        parser = HTMLParser()
        doc = parser.parse(html)
        
        # Try to find table rows
        rows = parser.select(doc, "tr")
        print(f"Found {len(rows)} table rows")
        
        # Look at first few rows
        for i, row in enumerate(rows[:5]):
            print(f"\n=== ROW {i} ===")
            cells = parser.select(row, "td")
            spans = parser.select(row, "span")
            links = parser.select(row, "a")
            
            print(f"Cells: {len(cells)}")
            print(f"Spans: {len(spans)}")
            print(f"Links: {len(links)}")
            
            # Print first few spans content
            for j, span in enumerate(spans[:10]):
                text = parser.get_text(span)
                classes = parser.get_attribute(span, "class") or "no-class"
                print(f"  Span {j}: '{text}' (class: {classes})")
            
            # Print links
            for j, link in enumerate(links[:3]):
                href = parser.get_attribute(link, "href") or "no-href"
                text = parser.get_text(link)
                print(f"  Link {j}: '{text}' -> {href}")
        
        # Test extractor
        extractor = AffiliatorExtractor(parser=parser)
        result = extractor.extract_list_page(doc)
        
        print(f"\n=== EXTRACTOR RESULTS ===")
        print(f"Found {len(result.affiliators)} affiliators")
        
        for i, aff in enumerate(result.affiliators[:3]):
            print(f"\nAffiliator {i}:")
            print(f"  Username: {aff.username}")
            print(f"  Kategori: {aff.kategori}")
            print(f"  Pengikut: {aff.pengikut}")
            print(f"  GMV: {aff.gmv}")
            print(f"  Detail URL: {aff.detail_url}")
        
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(test_extraction())