#!/usr/bin/env python3
"""
Focused production test - processes fewer creators but validates full workflow.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_focused_production():
    """Run a focused production test with limited scope."""
    
    print("🎯 FOCUSED PRODUCTION TEST")
    print("=" * 50)
    print("Testing with limited scope to validate workflow")
    
    # Load and modify configuration for focused testing
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Limit scope for focused testing
    config.max_pages_per_run = 1  # Only 1 page
    config.save_interval = 2      # Save every 2 creators
    config.incremental_save = True
    
    # Reduce delays for faster testing
    config.min_delay = 1.0
    config.max_delay = 2.0
    
    print(f"📋 Test Configuration:")
    print(f"   Max Pages: {config.max_pages_per_run}")
    print(f"   Save Interval: {config.save_interval}")
    print(f"   Delays: {config.min_delay}-{config.max_delay}s")
    
    try:
        # Create orchestrator
        orchestrator = ScraperOrchestrator(config)
        
        print(f"\n🚀 Starting focused production test...")
        start_time = time.time()
        
        # Run scraping
        result = await orchestrator.start()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        print(f"\n📊 RESULTS ANALYSIS:")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Total Scraped: {result.total_scraped}")
        print(f"   Unique Affiliators: {result.unique_affiliators}")
        print(f"   Duplicates: {result.duplicates_found}")
        print(f"   Errors: {result.errors}")
        print(f"   CAPTCHAs: {result.captchas_encountered}")
        
        # Calculate success metrics
        if result.total_scraped > 0:
            success_rate = (result.unique_affiliators / result.total_scraped) * 100
            creators_per_minute = (result.total_scraped / duration) * 60
            
            print(f"\n📈 PERFORMANCE METRICS:")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Creators/Minute: {creators_per_minute:.1f}")
            print(f"   Error Rate: {(result.errors / result.total_scraped * 100):.1f}%")
            
            # Assessment
            print(f"\n🎯 ASSESSMENT:")
            if success_rate >= 80 and result.errors <= 2:
                print(f"   ✅ EXCELLENT - Ready for production")
                print(f"   High success rate with low errors")
            elif success_rate >= 60 and result.errors <= 5:
                print(f"   ✅ GOOD - Production ready with monitoring")
                print(f"   Acceptable performance, monitor for issues")
            elif success_rate >= 40:
                print(f"   ⚠️ MODERATE - Needs improvement")
                print(f"   Consider optimizing error handling")
            else:
                print(f"   ❌ POOR - Major issues need fixing")
                print(f"   Significant problems detected")
        else:
            print(f"\n❌ NO DATA EXTRACTED")
            print(f"   Check extraction logic and page structure")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'focused_test_results_{timestamp}.json'
        
        results_data = {
            'test_type': 'focused_production',
            'duration': duration,
            'total_scraped': result.total_scraped,
            'unique_affiliators': result.unique_affiliators,
            'duplicates_found': result.duplicates_found,
            'errors': result.errors,
            'captchas_encountered': result.captchas_encountered,
            'success_rate': (result.unique_affiliators / result.total_scraped * 100) if result.total_scraped > 0 else 0,
            'creators_per_minute': (result.total_scraped / duration * 60) if duration > 0 else 0,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved: {output_file}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_focused_production())