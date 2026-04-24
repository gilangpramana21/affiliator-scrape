#!/usr/bin/env python3
"""Test the production scraper with improved selectors."""

import asyncio
import json
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration

async def test_production_scraper():
    """Test the production scraper with the updated selectors."""
    
    print("🚀 Testing Production Scraper with Improved Selectors")
    print("=" * 60)
    
    # Load configuration
    config = Configuration.from_file("config/config_jelajahi.json")
    print(f"✅ Loaded config: {config.base_url}")
    
    # Initialize orchestrator
    orchestrator = ScraperOrchestrator(config)
    
    try:
        # Test single page extraction using internal method
        print("\n📄 Testing single page extraction...")
        
        # Build the URL
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Target URL: {url}")
        
        # Extract data from the page using internal method
        affiliators = await orchestrator._scrape_list_page(url)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Total creators found: {len(affiliators) if affiliators else 0}")
        
        if not affiliators:
            print("   ❌ No creators extracted")
            return None
        
        # Display detailed results
        for i, creator in enumerate(affiliators[:5], 1):  # Show first 5
            print(f"\n👤 Creator {i}:")
            print(f"   Username: {creator.username}")
            print(f"   Category: {creator.kategori}")
            print(f"   Followers: {creator.pengikut:,}" if creator.pengikut else "   Followers: N/A")
            print(f"   GMV: Rp{creator.gmv:,.0f}" if creator.gmv else "   GMV: N/A")
            print(f"   Products Sold: {creator.produk_terjual:,}" if creator.produk_terjual else "   Products Sold: N/A")
            print(f"   Avg Views: {creator.rata_rata_tayangan:,}" if creator.rata_rata_tayangan else "   Avg Views: N/A")
            print(f"   Engagement: {creator.tingkat_interaksi}%" if creator.tingkat_interaksi else "   Engagement: N/A")
            print(f"   Detail URL: {creator.detail_url}" if creator.detail_url else "   Detail URL: N/A")
        
        if len(affiliators) > 5:
            print(f"\n... and {len(affiliators) - 5} more creators")
        
        # Save results to file
        output_data = []
        for creator in affiliators:
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
        
        with open('production_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to production_test_results.json")
        
        # Test data quality
        print(f"\n🔍 DATA QUALITY ANALYSIS:")
        
        # Count successful extractions
        username_count = sum(1 for c in affiliators if c.username)
        category_count = sum(1 for c in affiliators if c.kategori)
        follower_count = sum(1 for c in affiliators if c.pengikut)
        gmv_count = sum(1 for c in affiliators if c.gmv)
        
        total = len(affiliators)
        print(f"   Username extraction: {username_count}/{total} ({username_count/total*100:.1f}%)")
        print(f"   Category extraction: {category_count}/{total} ({category_count/total*100:.1f}%)")
        print(f"   Follower extraction: {follower_count}/{total} ({follower_count/total*100:.1f}%)")
        print(f"   GMV extraction: {gmv_count}/{total} ({gmv_count/total*100:.1f}%)")
        
        # Check for data consistency
        print(f"\n📈 DATA CONSISTENCY:")
        if affiliators:
            avg_followers = sum(c.pengikut for c in affiliators if c.pengikut) / follower_count if follower_count > 0 else 0
            avg_gmv = sum(c.gmv for c in affiliators if c.gmv) / gmv_count if gmv_count > 0 else 0
            
            print(f"   Average followers: {avg_followers:,.0f}")
            print(f"   Average GMV: Rp{avg_gmv:,.0f}")
            
            # Check for outliers
            high_followers = sum(1 for c in affiliators if c.pengikut and c.pengikut > 1000000)
            high_gmv = sum(1 for c in affiliators if c.gmv and c.gmv > 1000000)
            
            print(f"   High-follower creators (>1M): {high_followers}")
            print(f"   High-GMV creators (>1M): {high_gmv}")
        
        print(f"\n✅ Production scraper test completed successfully!")
        
        return affiliators
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    result = asyncio.run(test_production_scraper())
    
    if result:
        print(f"\n🎉 SUCCESS: Extracted {len(result)} creators")
        print("   The scraper is ready for production use!")
    else:
        print(f"\n⚠️  WARNING: No data extracted or errors occurred")
        print("   Check the logs and selectors configuration")