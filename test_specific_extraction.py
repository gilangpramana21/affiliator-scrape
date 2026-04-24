#!/usr/bin/env python3
"""Test specific data extraction based on discovered structure."""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser

def parse_creator_data(text):
    """Parse creator data from the full text string."""
    # Example: "aliyanida7Lv. 7Lv. 7Aliya12🐣Pakaian & Pakaian Dalam Wanita, +2140,2 rb, Perempuan 58%, 25-34"
    
    # Extract username (before first "Lv.")
    username_match = re.match(r'^([^L]+?)Lv\.', text)
    username = username_match.group(1) if username_match else None
    
    # Extract follower count (pattern like "140,2 rb" or "1,7 jt")
    follower_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(rb|jt|k)', text, re.IGNORECASE)
    followers = None
    if follower_match:
        num_str = follower_match.group(1).replace(',', '.')
        suffix = follower_match.group(2).lower()
        num = float(num_str)
        if suffix == 'rb':
            followers = int(num * 1000)
        elif suffix == 'jt':
            followers = int(num * 1000000)
        elif suffix == 'k':
            followers = int(num * 1000)
    
    # Extract category - improved parsing to remove "Lv. X" noise
    # Pattern: find text after display name but before follower count
    # Remove "Lv. X" patterns and clean up
    category_pattern = r'Lv\.\s*\d+.*?([A-Za-z][^,+]+?)(?:,\s*\+|\s*,\s*\d)'
    category_match = re.search(category_pattern, text)
    category = None
    if category_match:
        category = category_match.group(1).strip()
        # Clean up category by removing common noise patterns
        category = re.sub(r'^Lv\.\s*\d+\s*', '', category)  # Remove leading Lv. X
        category = re.sub(r'\s*Lv\.\s*\d+\s*', ' ', category)  # Remove middle Lv. X
        category = re.sub(r'[🐣🌟🚀]+', '', category)  # Remove emojis
        category = re.sub(r'\s+', ' ', category).strip()  # Normalize whitespace
        
        # Additional cleanup: remove display names that got mixed in
        # Look for pattern where display name is repeated in category
        if username and username.lower() in category.lower():
            # Try to extract just the category part after the display name
            parts = category.split()
            # Find parts that don't match username
            clean_parts = []
            for part in parts:
                if part.lower() not in username.lower() and len(part) > 2:
                    clean_parts.append(part)
            if clean_parts:
                category = ' '.join(clean_parts)
    
    # Fallback: try a different pattern if first one didn't work well
    if not category or len(category) < 3:
        # Look for category pattern: after display name, before comma and numbers
        alt_pattern = r'[A-Za-z][^,]*?([A-Za-z&\s]+?)(?:,\s*\+\d|,\s*\d)'
        alt_match = re.search(alt_pattern, text)
        if alt_match:
            category = alt_match.group(1).strip()
            # Clean up
            category = re.sub(r'[🐣🌟🚀]+', '', category)
            category = re.sub(r'\s+', ' ', category).strip()
    
    return {
        'username': username,
        'followers': followers,
        'category': category,
        'raw_text': text
    }

async def test_specific_extraction():
    """Test specific data extraction."""
    
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
        
        # Find data rows (skip header row)
        rows = parser.select(doc, "tr")
        data_rows = rows[1:]  # Skip header
        
        print(f"Found {len(data_rows)} data rows")
        
        creators = []
        
        for i, row in enumerate(data_rows):
            # Get the main data cell (usually second cell)
            cells = parser.select(row, "td")
            if len(cells) < 2:
                continue
                
            # Look for the main data span
            main_spans = parser.select(cells[1], "span.arco-table-cell-wrap-value")
            if not main_spans:
                continue
                
            main_text = parser.get_text(main_spans[0])
            creator_data = parse_creator_data(main_text)
            
            # Get GMV data (usually in later cells)
            gmv_spans = parser.select(row, "span[class*='text-body-m-regular'][class*='text-neutral-text1']")
            gmv_values = []
            for span in gmv_spans:
                text = parser.get_text(span)
                if 'Rp' in text or 'M' in text or 'JT' in text:
                    gmv_values.append(text)
            
            # Extract detail URL from first cell
            detail_url = None
            if cells:
                links = parser.select(cells[0], "a")
                if links:
                    detail_url = parser.get_attribute(links[0], "href")
                    print(f"    Found detail URL: {detail_url}")
                else:
                    print(f"    No links found in first cell")
                    # Try other cells
                    for j, cell in enumerate(cells):
                        cell_links = parser.select(cell, "a")
                        if cell_links:
                            detail_url = parser.get_attribute(cell_links[0], "href")
                            print(f"    Found detail URL in cell {j}: {detail_url}")
                            break
            
            creator_data['gmv_data'] = gmv_values
            creator_data['detail_url'] = detail_url
            creators.append(creator_data)
            
            print(f"\nCreator {i+1}:")
            print(f"  Username: {creator_data['username']}")
            print(f"  Category: {creator_data['category']}")
            print(f"  Followers: {creator_data['followers']}")
            print(f"  GMV Data: {creator_data['gmv_data']}")
            print(f"  Detail URL: {creator_data['detail_url']}")
            print(f"  Raw: {creator_data['raw_text'][:100]}...")
        
        print(f"\n=== SUMMARY ===")
        print(f"Successfully extracted {len(creators)} creators")
        
        # Save to simple JSON for inspection
        import json
        with open('extracted_creators.json', 'w') as f:
            json.dump(creators, f, indent=2, ensure_ascii=False)
        print("Data saved to extracted_creators.json")
        
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(test_specific_extraction())