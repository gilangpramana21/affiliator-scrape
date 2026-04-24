#!/usr/bin/env python3
"""Test run untuk ambil data creator dengan TokopediaExtractor."""

import asyncio
import json
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.tokopedia_extractor import TokopediaExtractor
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_data_extraction_run():
    """Test run untuk ambil data creator."""
    
    print("🚀 TEST RUN - DATA EXTRACTION")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    extractor = TokopediaExtractor(parser)
    session_manager = SessionManager()
    
    print("✅ Components initialized")
    print(f"   Using TokopediaExtractor (custom)")
    print(f"   CaptchaSonic ready: {'✅' if config.captcha_api_key else '❌'}")
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to target page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"\n🌐 Navigating to: {url}")
        
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
        
        # Check for captcha first
        print("\n🔍 Checking for CAPTCHA...")
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '.h-captcha'
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    captcha_found = True
                    print(f"🚨 CAPTCHA detected: {selector}")
                    break
            except:
                continue
        
        if captcha_found:
            print("⏳ CaptchaSonic should solve this automatically...")
            print("   Waiting 60 seconds for automatic solving...")
            
            # Wait for CaptchaSonic
            for i in range(12):  # 12 * 5 = 60 seconds
                await asyncio.sleep(5)
                remaining = 60 - (i * 5)
                print(f"   {remaining} seconds remaining...", end="\r")
                
                # Check if captcha is gone
                captcha_still_present = False
                for selector in captcha_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            captcha_still_present = True
                            break
                    except:
                        continue
                
                if not captcha_still_present:
                    print(f"\n✅ CAPTCHA solved by CaptchaSonic!")
                    break
            
            if captcha_still_present:
                print(f"\n⚠️  Captcha still present - continuing anyway")
        else:
            print("✅ No CAPTCHA detected")
        
        # Extract data
        print(f"\n📊 EXTRACTING DATA...")
        
        # Get HTML and parse
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        
        # Use TokopediaExtractor
        result = extractor.extract_list_page(doc)
        
        print(f"✅ Extraction completed")
        print(f"   Creators found: {len(result.affiliators)}")
        print(f"   Next page URL: {result.next_page_url}")
        
        if not result.affiliators:
            print("❌ No creators extracted")
            
            # Debug info
            print("\n🔍 DEBUG INFO:")
            rows = parser.select(doc, "tr")
            print(f"   Table rows found: {len(rows)}")
            
            if rows:
                print("   Sample row content:")
                for i, row in enumerate(rows[:3]):
                    text = parser.get_text(row)[:100]
                    print(f"     Row {i}: {text}...")
            
            return None
        
        # Display results
        print(f"\n📋 EXTRACTED DATA:")
        
        all_creators = []
        
        for i, creator in enumerate(result.affiliators, 1):
            print(f"\n👤 Creator {i}:")
            print(f"   Username: {creator.username}")
            print(f"   Category: {creator.kategori}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            
            # Convert to dict for saving
            creator_data = {
                'username': creator.username,
                'kategori': creator.kategori,
                'pengikut': creator.pengikut,
                'gmv': creator.gmv,
                'produk_terjual': creator.produk_terjual,
                'rata_rata_tayangan': creator.rata_rata_tayangan,
                'tingkat_interaksi': creator.tingkat_interaksi,
                'detail_url': creator.detail_url
            }
            all_creators.append(creator_data)
        
        # Save results
        output_file = 'test_extraction_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_creators, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Data quality analysis
        print(f"\n📊 DATA QUALITY ANALYSIS:")
        
        username_count = sum(1 for c in result.affiliators if c.username)
        category_count = sum(1 for c in result.affiliators if c.kategori)
        follower_count = sum(1 for c in result.affiliators if c.pengikut)
        gmv_count = sum(1 for c in result.affiliators if c.gmv)
        
        total = len(result.affiliators)
        print(f"   Username extraction: {username_count}/{total} ({username_count/total*100:.1f}%)")
        print(f"   Category extraction: {category_count}/{total} ({category_count/total*100:.1f}%)")
        print(f"   Follower extraction: {follower_count}/{total} ({follower_count/total*100:.1f}%)")
        print(f"   GMV extraction: {gmv_count}/{total} ({gmv_count/total*100:.1f}%)")
        
        # Statistics
        if result.affiliators:
            print(f"\n📈 STATISTICS:")
            
            # Follower stats
            followers = [c.pengikut for c in result.affiliators if c.pengikut]
            if followers:
                avg_followers = sum(followers) / len(followers)
                max_followers = max(followers)
                min_followers = min(followers)
                print(f"   Followers - Avg: {avg_followers:,.0f}, Max: {max_followers:,}, Min: {min_followers:,}")
            
            # GMV stats
            gmvs = [c.gmv for c in result.affiliators if c.gmv]
            if gmvs:
                avg_gmv = sum(gmvs) / len(gmvs)
                max_gmv = max(gmvs)
                min_gmv = min(gmvs)
                print(f"   GMV - Avg: Rp{avg_gmv:,.0f}, Max: Rp{max_gmv:,.0f}, Min: Rp{min_gmv:,.0f}")
            
            # Category distribution
            categories = [c.kategori for c in result.affiliators if c.kategori]
            if categories:
                from collections import Counter
                category_counts = Counter(categories)
                print(f"   Top categories:")
                for cat, count in category_counts.most_common(5):
                    print(f"     {cat}: {count} creators")
        
        # Test multiple pages
        print(f"\n🔄 TESTING MULTIPLE PAGES...")
        
        test_pages = [
            f"{config.base_url}/connection/creator?page=2&shop_region=ID&shop_id=7495177173399997259",
            f"{config.base_url}/connection/creator?page=3&shop_region=ID&shop_id=7495177173399997259"
        ]
        
        total_creators = len(result.affiliators)
        
        for page_num, test_url in enumerate(test_pages, 2):
            print(f"\n   📄 Testing page {page_num}: {test_url}")
            
            try:
                await page.goto(test_url)
                await asyncio.sleep(3)
                
                # Check for captcha
                captcha_found = False
                for selector in captcha_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            captcha_found = True
                            print(f"      🚨 CAPTCHA on page {page_num}")
                            break
                    except:
                        continue
                
                if captcha_found:
                    print(f"      ⏳ Waiting for CaptchaSonic...")
                    await asyncio.sleep(30)  # Wait for solving
                
                # Extract data from this page
                html = await browser_engine.get_html(page)
                doc = parser.parse(html)
                page_result = extractor.extract_list_page(doc)
                
                print(f"      ✅ Page {page_num}: {len(page_result.affiliators)} creators")
                total_creators += len(page_result.affiliators)
                
                # Add to results
                for creator in page_result.affiliators:
                    creator_data = {
                        'username': creator.username,
                        'kategori': creator.kategori,
                        'pengikut': creator.pengikut,
                        'gmv': creator.gmv,
                        'produk_terjual': creator.produk_terjual,
                        'rata_rata_tayangan': creator.rata_rata_tayangan,
                        'tingkat_interaksi': creator.tingkat_interaksi,
                        'detail_url': creator.detail_url
                    }
                    all_creators.append(creator_data)
                
            except Exception as e:
                print(f"      ⚠️  Error on page {page_num}: {e}")
        
        # Final save with all pages
        if len(all_creators) > len(result.affiliators):
            final_output = 'test_extraction_multi_page.json'
            with open(final_output, 'w', encoding='utf-8') as f:
                json.dump(all_creators, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Multi-page results saved to: {final_output}")
        
        # Final summary
        print(f"\n🎉 TEST RUN COMPLETED!")
        print(f"   Total creators extracted: {len(all_creators)}")
        print(f"   Pages tested: {len(test_pages) + 1}")
        print(f"   Data quality: {'✅ Excellent' if username_count/total > 0.9 else '⚠️ Good' if username_count/total > 0.7 else '❌ Needs improvement'}")
        print(f"   CaptchaSonic: {'✅ Working' if not captcha_found else '⚠️ Encountered captcha'}")
        
        return all_creators
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print(f"\n⏳ Browser window open for inspection...")
        print("   Press Enter to close...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    result = asyncio.run(test_data_extraction_run())
    
    if result:
        print(f"\n🎊 SUCCESS! Extracted {len(result)} creators")
        print("   Data extraction is working perfectly!")
    else:
        print(f"\n⚠️  No data extracted - check configuration")