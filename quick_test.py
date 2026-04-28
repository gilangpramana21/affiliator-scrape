#!/usr/bin/env python3
"""
Quick Test Script - Test with 10 affiliators
Use this to validate setup before production run
"""

import asyncio
from production_scraper_v2 import ProductionScraperV2


async def main():
    print("🧪 QUICK TEST - 10 Affiliators")
    print("=" * 60)
    print("This will test:")
    print("  ✅ Proxy connection")
    print("  ✅ CAPTCHA solving")
    print("  ✅ Network monitoring")
    print("  ✅ Data extraction")
    print("=" * 60)
    print()
    
    scraper = ProductionScraperV2("config/config_jelajahi.json")
    results = await scraper.scrape_affiliators(max_affiliators=10)
    
    print()
    print("=" * 60)
    print("🎯 TEST RESULTS")
    print("=" * 60)
    
    total = len(results)
    metrics_success = sum(1 for r in results if r.get('gmv') is not None)
    contact_success = sum(1 for r in results if r.get('whatsapp') or r.get('email'))
    
    print(f"Total processed: {total}/10")
    if total > 0:
        print(f"Metrics success: {metrics_success}/{total} ({metrics_success/total*100:.1f}%)")
        print(f"Contact success: {contact_success}/{total} ({contact_success/total*100:.1f}%)")
    else:
        print(f"Metrics success: 0/10 (0.0%)")
        print(f"Contact success: 0/10 (0.0%)")
    print()
    
    if metrics_success >= 9:
        print("✅ EXCELLENT! Ready for production run")
        print("   Next step: Run production_scraper_v2.py with 1000+ affiliators")
    elif metrics_success >= 7:
        print("⚠️ GOOD, but can be improved")
        print("   Suggestions:")
        print("   - Enable proxy if not already enabled")
        print("   - Check CAPTCHA solver configuration")
        print("   - Increase delays in config")
    else:
        print("❌ NEEDS IMPROVEMENT")
        print("   Issues to fix:")
        print("   - Check proxy configuration")
        print("   - Verify CAPTCHA solver API key")
        print("   - Check cookies are valid")
        print("   - Review error logs")
    
    print()
    print(f"📄 Detailed results saved to production_results_*.json")


if __name__ == "__main__":
    asyncio.run(main())
