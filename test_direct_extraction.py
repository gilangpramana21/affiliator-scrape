#!/usr/bin/env python3
"""Direct test of the extraction components with improved selectors."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.affiliator_extractor import AffiliatorExtractor
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_direct_extraction():
    """Test the extraction components directly."""
    
    print("🔧 Testing Direct Extraction with Improved Selectors")
    print("=" * 60)
    
    # Load configuration
    config = Configuration.from_file("config/config_jelajahi.json")
    print(f"✅ Loaded config: {config.base_url}")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = AffiliatorExtractor()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=True)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url)
        
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
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        print("✅ Page loaded with cookies")
        
        # Get HTML and parse
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        print("✅ HTML parsed")
        
        # Extract data using the improved extractor
        result = extractor.extract_list_page(doc)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Total creators found: {len(result.affiliators)}")
        print(f"   Next page URL: {result.next_page_url}")
        
        if not result.affiliators:
            print("   ❌ No creators extracted")
            
            # Debug: check what elements we can find
            print("\n🔍 DEBUG: Looking for table elements...")
            rows = parser.select(doc, "tr")
            print(f"   Found {len(rows)} table rows")
            
            if rows:
                print("   Sample row content:")
                for i, row in enumerate(rows[:3]):
                    text = parser.get_text(row)[:100]
                    print(f"     Row {i}: {text}...")
            
            return None
        
        # Display detailed results
        for i, creator in enumerate(result.affiliators[:5], 1):  # Show first 5
            print(f"\n👤 Creator {i}:")
            print(f"   Username: {creator.username}")
            print(f"   Category: {creator.kategori}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            print(f"   Products Sold: {creator.produk_terjual:,}" if creator.produk_terjual else "   Products Sold: N/A")
            print(f"   Avg Views: {creator.rata_rata_tayangan:,}" if creator.rata_rata_tayangan else "   Avg Views: N/A")
            print(f"   Engagement: {creator.tingkat_interaksi}%" if creator.tingkat_interaksi else "   Engagement: N/A")
            print(f"   Detail URL: {creator.detail_url}" if creator.detail_url else "   Detail URL: N/A")
        
        if len(result.affiliators) > 5:
            print(f"\n... and {len(result.affiliators) - 5} more creators")
        
        # Save results
        output_data = []
        for creator in result.affiliators:
            output_data.append({
                'username': creator.username,
                'kategori': creator.kategori,
                'pengikut': creator.pengikut,
                'gmv': creator.gmv,
                'produk_terjual': creator.produk_terjual,
                'rata_rata_tayangan': creator.rata_rata_tayangan,
                'tingkat_interaksi': creator.tingkat_interaksi,
                'detail_url': creator.detail_url
            })
        
        with open('direct_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to direct_extraction_results.json")
        
        # Data quality analysis
        print(f"\n🔍 DATA QUALITY ANALYSIS:")
        
        username_count = sum(1 for c in result.affiliators if c.username)
        category_count = sum(1 for c in result.affiliators if c.kategori)
        follower_count = sum(1 for c in result.affiliators if c.pengikut)
        gmv_count = sum(1 for c in result.affiliators if c.gmv)
        
        total = len(result.affiliators)
        print(f"   Username extraction: {username_count}/{total} ({username_count/total*100:.1f}%)")
        print(f"   Category extraction: {category_count}/{total} ({category_count/total*100:.1f}%)")
        print(f"   Follower extraction: {follower_count}/{total} ({follower_count/total*100:.1f}%)")
        print(f"   GMV extraction: {gmv_count}/{total} ({gmv_count/total*100:.1f}%)")
        
        print(f"\n✅ Direct extraction test completed successfully!")
        
        return result.affiliators
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(test_direct_extraction())
    
    if result:
        print(f"\n🎉 SUCCESS: Extracted {len(result)} creators")
        print("   The improved selectors are working!")
    else:
        print(f"\n⚠️  WARNING: No data extracted")
        print("   Check the selectors and page structure")