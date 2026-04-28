#!/usr/bin/env python3
"""
Enhanced Production Scraper - Based on proven working scraper
Features:
- Uses proven ScraperOrchestrator
- Bright Data proxy support (when configured)
- CapSolver CAPTCHA solving
- Optimized for 1000+ affiliators
- Daily scraping capability
"""

import asyncio
import sys
import logging
from datetime import datetime
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.utils.logging_setup import configure_logging


class EnhancedProductionScraper:
    """Production scraper with proxy and CAPTCHA solving."""
    
    def __init__(self, config_path: str = "config/config_production.json"):
        self.config = Configuration.from_file(config_path)
        self.logger = logging.getLogger(__name__)
    
    async def run(self, max_affiliators: int = 1000) -> int:
        """Run production scraping."""
        
        print("🚀 ENHANCED PRODUCTION SCRAPER")
        print("=" * 60)
        print(f"Target: {max_affiliators} affiliators")
        print(f"Proxy: {'Enabled' if self.config.proxies else 'Disabled'}")
        print(f"CAPTCHA Solver: {self.config.captcha_solver}")
        print("=" * 60)
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            print("\n❌ Configuration errors:")
            for error in errors:
                print(f"   - {error}")
            return 2
        
        # Setup logging
        configure_logging(self.config.log_level, self.config.log_file)
        
        # Calculate pages needed (assuming ~10 affiliators per page)
        pages_needed = (max_affiliators + 9) // 10
        self.config.max_pages_per_run = pages_needed
        
        print(f"\n📄 Will process approximately {pages_needed} pages")
        print(f"⏱️  Estimated time: {pages_needed * 30 / 60:.1f} minutes")
        print(f"💾 Output: {self.config.output_path}")
        
        # Check proxy configuration
        if self.config.proxies:
            print(f"\n🌐 Proxy Configuration:")
            for i, proxy in enumerate(self.config.proxies, 1):
                print(f"   {i}. {proxy.get('server', 'N/A')}")
        else:
            print("\n⚠️  WARNING: No proxy configured!")
            print("   Public WiFi may trigger many CAPTCHAs")
            print("   Recommendation: Configure Bright Data proxy")
        
        # Check CAPTCHA solver
        if self.config.captcha_solver == "capsolver":
            if not self.config.captcha_api_key or self.config.captcha_api_key == "YOUR_CAPSOLVER_API_KEY":
                print("\n⚠️  WARNING: CapSolver API key not configured!")
                print("   CAPTCHAs will not be solved automatically")
        
        # Confirm start
        print("\n" + "=" * 60)
        response = input("Start scraping? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled by user")
            return 0
        
        # Run scraper
        print("\n🚀 Starting scraper...")
        print("=" * 60)
        
        start_time = datetime.now()
        orchestrator = ScraperOrchestrator(self.config)
        result = await orchestrator.start()
        end_time = datetime.now()
        
        # Print results
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ SCRAPING COMPLETED")
        print("=" * 60)
        print(f"📊 STATISTICS:")
        print(f"   Total scraped: {result.total_scraped}")
        print(f"   Unique affiliators: {result.unique_affiliators}")
        print(f"   Duplicates: {result.duplicates_found}")
        print(f"   Errors: {result.errors}")
        print(f"   CAPTCHAs encountered: {result.captchas_encountered}")
        print(f"   Duration: {duration:.2f}s ({duration/60:.1f} minutes)")
        
        # Calculate success rate
        if result.total_scraped > 0:
            success_rate = (result.unique_affiliators / result.total_scraped) * 100
            print(f"   Success rate: {success_rate:.1f}%")
        
        # Calculate CAPTCHA rate
        if result.total_scraped > 0:
            captcha_rate = (result.captchas_encountered / result.total_scraped) * 100
            print(f"   CAPTCHA rate: {captcha_rate:.1f}%")
        
        print(f"\n💾 Output saved to: {self.config.output_path}")
        
        # Recommendations
        if result.captchas_encountered > result.total_scraped * 0.3:
            print("\n⚠️  HIGH CAPTCHA RATE DETECTED!")
            print("   Recommendations:")
            print("   1. Configure Bright Data proxy")
            print("   2. Use residential proxy with Indonesia location")
            print("   3. Enable CapSolver for automatic solving")
        
        if result.errors > result.total_scraped * 0.1:
            print("\n⚠️  HIGH ERROR RATE DETECTED!")
            print("   Recommendations:")
            print("   1. Check cookies are valid (login and export new cookies)")
            print("   2. Check internet connection")
            print("   3. Review logs for specific errors")
        
        return 0


async def main():
    """Main entry point."""
    
    import argparse
    parser = argparse.ArgumentParser(description="Enhanced production scraper")
    parser.add_argument(
        "--config",
        default="config/config_production.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--max-affiliators",
        type=int,
        default=1000,
        help="Maximum number of affiliators to scrape"
    )
    args = parser.parse_args()
    
    scraper = EnhancedProductionScraper(args.config)
    return await scraper.run(args.max_affiliators)


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
