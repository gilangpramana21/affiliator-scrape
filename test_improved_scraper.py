#!/usr/bin/env python3
"""
Test improved scraper with better puzzle handling
"""

import asyncio
import sys
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.utils.logging_setup import configure_logging


async def main():
    print("🧪 TESTING IMPROVED SCRAPER")
    print("=" * 60)
    print("Improvements:")
    print("  ✅ Better puzzle handling")
    print("  ✅ Improved delays")
    print("  ✅ Fixed phone number validation")
    print("  ✅ Manual CAPTCHA solving")
    print("=" * 60)
    print("\nTarget: 20 affiliators")
    print("Expected CAPTCHA: ~2 (8% rate)")
    print("Expected success: 80%+ (16+ affiliators)")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Override for testing
    config.max_pages_per_run = 2  # 2 pages = ~20 affiliators
    config.headless = False  # Show browser for manual CAPTCHA
    config.max_captchas_before_stop = 10  # Allow more CAPTCHAs
    config.max_errors_before_stop = 15  # Allow more errors
    
    # Increase delays for better stealth
    config.min_delay = 4.0
    config.max_delay = 8.0
    
    # Validate
    errors = config.validate()
    if errors:
        print("\n❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return 1
    
    # Setup logging
    configure_logging(config.log_level, config.log_file)
    
    # Run scraper
    print("\n🚀 Starting scraper...")
    print("=" * 60)
    print("⚠️  IMPORTANT:")
    print("   - Browser will open (not headless)")
    print("   - If CAPTCHA appears, solve it manually")
    print("   - If 'Coba lagi' appears, scraper will auto-refresh")
    print("=" * 60)
    
    input("\nPress Enter to start...")
    
    orchestrator = ScraperOrchestrator(config)
    result = await orchestrator.start()
    
    # Print results
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETED")
    print("=" * 60)
    print(f"📊 STATISTICS:")
    print(f"   Total scraped: {result.total_scraped}")
    print(f"   Unique affiliators: {result.unique_affiliators}")
    print(f"   Duplicates: {result.duplicates_found}")
    print(f"   Errors: {result.errors}")
    print(f"   CAPTCHAs encountered: {result.captchas_encountered}")
    print(f"   Duration: {result.duration:.2f}s ({result.duration/60:.1f} minutes)")
    
    # Calculate rates
    if result.total_scraped > 0:
        success_rate = (result.unique_affiliators / result.total_scraped) * 100
        error_rate = (result.errors / result.total_scraped) * 100
        captcha_rate = (result.captchas_encountered / result.total_scraped) * 100
        
        print(f"\n📈 RATES:")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Error rate: {error_rate:.1f}%")
        print(f"   CAPTCHA rate: {captcha_rate:.1f}%")
    
    print(f"\n💾 Output saved to: {config.output_path}")
    
    # Check output file
    try:
        import pandas as pd
        df = pd.read_excel(config.output_path)
        
        print(f"\n📋 OUTPUT FILE ANALYSIS:")
        print(f"   Total rows: {len(df)}")
        
        # Count contact data
        whatsapp_count = df['nomor_whatsapp'].notna().sum()
        email_count = df['nomor_kontak'].notna().sum()
        
        print(f"   WhatsApp found: {whatsapp_count} ({whatsapp_count/len(df)*100:.1f}%)")
        print(f"   Email/Contact found: {email_count} ({email_count/len(df)*100:.1f}%)")
        
        # Show sample data
        if len(df) > 0:
            print(f"\n📄 SAMPLE DATA (first row):")
            first_row = df.iloc[0]
            print(f"   Username: {first_row['username']}")
            print(f"   Kategori: {first_row['kategori']}")
            print(f"   Pengikut: {first_row['pengikut']}")
            print(f"   GMV: {first_row['gmv']}")
            print(f"   WhatsApp: {first_row['nomor_whatsapp']}")
            print(f"   Email: {first_row['nomor_kontak']}")
        
    except Exception as e:
        print(f"\n⚠️  Could not analyze output file: {e}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if result.captchas_encountered > result.total_scraped * 0.3:
        print(f"   ⚠️  High CAPTCHA rate ({captcha_rate:.1f}%)")
        print(f"      → Consider using CapSolver for auto-solving")
        print(f"      → Or setup proxy to reduce CAPTCHA rate")
    else:
        print(f"   ✅ CAPTCHA rate is acceptable ({captcha_rate:.1f}%)")
        print(f"      → Manual solving is feasible for now")
    
    if result.errors > result.total_scraped * 0.2:
        print(f"   ⚠️  High error rate ({error_rate:.1f}%)")
        print(f"      → Check logs for specific errors")
        print(f"      → May need to improve puzzle handling")
    else:
        print(f"   ✅ Error rate is acceptable ({error_rate:.1f}%)")
    
    if success_rate >= 80:
        print(f"   ✅ SUCCESS! Ready for production run")
        print(f"      → Can scale to 1000+ affiliators")
        print(f"      → Consider CapSolver for automation")
    elif success_rate >= 60:
        print(f"   ⚠️  Moderate success rate")
        print(f"      → Need improvements before scaling")
        print(f"      → Consider proxy + CapSolver")
    else:
        print(f"   ❌ Low success rate")
        print(f"      → Must fix issues before scaling")
        print(f"      → Proxy + CapSolver required")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
