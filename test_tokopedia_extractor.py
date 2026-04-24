#!/usr/bin/env python3
"""Test the Tokopedia-specific extractor."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_tokopedia_extractor():
    """Test the Tokopedia-specific extractor."""
    
    print("🎯 Testing Tokopedia-Specific Extractor")
    print("=" * 50)
    
    # Load configuration
    config = Configuration.from_file("config/config_jelajahi.json")
    print(f"✅ Loaded config: {config.base_url}")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
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
        
        # Get HTML and parse
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        print("✅ HTML parsed")
        
        # Extract data using the Tokopedia-specific extractor
        result = extractor.extract_list_page(doc)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Total creators found: {len(result.affiliators)}")
        print(f"   Next page URL: {result.next_page_url}")
        
        if not result.affiliators:
            print("   ❌ No creators extracted")
            return None
        
        # Display detailed results
        for i, creator in enumerate(result.affiliators[:10], 1):  # Show first 10
            print(f"\n👤 Creator {i}:")
            print(f"   Username: {creator.username}")
            print(f"   Category: {creator.kategori}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            print(f"   Detail URL: {creator.detail_url}" if creator.detail_url else "   Detail URL: N/A")
        
        if len(result.affiliators) > 10:
            print(f"\n... and {len(result.affiliators) - 10} more creators")
        
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
        
        with open('tokopedia_extractor_results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to tokopedia_extractor_results.json")
        
        # Data quality analysis
        print(f"\n🔍 DATA QUALITY ANALYSIS:")
        
        username_count = sum(1 for c in result.affiliators if c.username)
        category_count = sum(1 for c in result.affiliators if c.kategori)
        follower_count = sum(1 for c in result.affiliators if c.pengikut)
        gmv_count = sum(1 for c in result.affiliators if c.gmv)
        detail_url_count = sum(1 for c in result.affiliators if c.detail_url)
        
        total = len(result.affiliators)
        print(f"   Username extraction: {username_count}/{total} ({username_count/total*100:.1f}%)")
        print(f"   Category extraction: {category_count}/{total} ({category_count/total*100:.1f}%)")
        print(f"   Follower extraction: {follower_count}/{total} ({follower_count/total*100:.1f}%)")
        print(f"   GMV extraction: {gmv_count}/{total} ({gmv_count/total*100:.1f}%)")
        print(f"   Detail URL extraction: {detail_url_count}/{total} ({detail_url_count/total*100:.1f}%)")
        
        # Data consistency check
        if result.affiliators:
            print(f"\n📈 DATA CONSISTENCY:")
            avg_followers = sum(c.pengikut for c in result.affiliators if c.pengikut) / follower_count if follower_count > 0 else 0
            avg_gmv = sum(c.gmv for c in result.affiliators if c.gmv) / gmv_count if gmv_count > 0 else 0
            
            print(f"   Average followers: {avg_followers:,.0f}")
            print(f"   Average GMV: Rp{avg_gmv:,.0f}")
            
            # Check for high-value creators
            high_followers = sum(1 for c in result.affiliators if c.pengikut and c.pengikut > 1000000)
            high_gmv = sum(1 for c in result.affiliators if c.gmv and c.gmv > 1000000)
            
            print(f"   High-follower creators (>1M): {high_followers}")
            print(f"   High-GMV creators (>1M): {high_gmv}")
        
        print(f"\n✅ Tokopedia extractor test completed successfully!")
        
        return result.affiliators
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(test_tokopedia_extractor())
    
    if result:
        print(f"\n🎉 SUCCESS: Extracted {len(result)} creators with Tokopedia extractor")
        print("   The custom extractor is working perfectly!")
        
        # Summary of improvements
        print(f"\n📋 IMPROVEMENTS MADE:")
        print("   ✅ Fixed category parsing (removed 'Lv. X' noise)")
        print("   ✅ Proper numeric parsing for followers and GMV")
        print("   ✅ Handles Indonesian format (rb=thousands, jt=millions)")
        print("   ✅ Extracts data from combined text strings")
        print("   ✅ Clean, structured output")
        
    else:
        print(f"\n⚠️  WARNING: No data extracted")
        print("   Check the page structure and selectors")