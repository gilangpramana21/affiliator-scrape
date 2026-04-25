#!/usr/bin/env python3
"""
Test original scraper with 10 affiliators
"""

import asyncio
import sys
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.utils.logging_setup import configure_logging


async def main():
    print("🧪 TESTING ORIGINAL SCRAPER")
    print("=" * 60)
    print("This will test the proven working scraper")
    print("Target: 10 affiliators")
    print("=" * 60)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Override for testing
    config.max_pages_per_run = 1  # Only 1 page = ~10 affiliators
    config.headless = False  # Show browser for debugging
    
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
    orchestrator = ScraperOrchestrator(config)
    result = await orchestrator.start()
    
    # Print results
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETED")
    print("=" * 60)
    print(f"Total scraped: {result.total_scraped}")
    print(f"Unique affiliators: {result.unique_affiliators}")
    print(f"Duplicates: {result.duplicates_found}")
    print(f"Errors: {result.errors}")
    print(f"CAPTCHAs encountered: {result.captchas_encountered}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"\n💾 Output saved to: {config.output_path}")
    
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
