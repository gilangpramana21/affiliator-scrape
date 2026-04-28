#!/usr/bin/env python3
"""
Test Script for Shadow DOM Scraper
Tests the browser-based approach with CAPTCHA and Shadow DOM handling
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scrape_with_browser import TokopediaScraperWithBrowser


async def main():
    print("\n" + "="*80)
    print("🧪 TESTING SHADOW DOM SCRAPER")
    print("="*80)
    print("This test will:")
    print("  1. Launch browser with stealth mode")
    print("  2. Load cookies from config/cookies.json")
    print("  3. Navigate to Tokopedia Affiliate Center")
    print("  4. Handle CAPTCHA if present (manual solving)")
    print("  5. Extract contacts from Shadow DOM")
    print("  6. Save results to output/affiliators_browser.json")
    print("="*80)
    print()
    
    # Test with 3 affiliators first
    scraper = TokopediaScraperWithBrowser(
        cookie_file="config/cookies.json",
        headless=False  # Visible browser for CAPTCHA solving
    )
    
    try:
        await scraper.scrape(max_creators=3)
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        print("Review the results in output/affiliators_browser.json")
        print()
        print("Next steps:")
        print("  1. Check if contacts were extracted successfully")
        print("  2. Verify DOM JavaScript worked")
        print("  3. If successful, increase max_creators for production run")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
