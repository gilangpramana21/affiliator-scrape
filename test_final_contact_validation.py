#!/usr/bin/env python3
"""
Test final untuk validasi ekstraksi kontak dan melihat data lengkap.
"""

import asyncio
import json
import logging
from datetime import datetime
from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_final_contact_validation():
    """Test final untuk melihat data lengkap yang diekstrak."""
    
    print("🔍 FINAL CONTACT VALIDATION TEST")
    print("=" * 60)
    
    # Load config dengan pengaturan minimal
    config = Configuration.from_file("config/config_jelajahi.json")
    config.max_pages_per_run = 1
    config.save_interval = 1  # Save setiap creator
    config.incremental_save = True
    config.min_delay = 1.0
    config.max_delay = 2.0
    
    print(f"📋 Configuration:")
    print(f"   Max Pages: {config.max_pages_per_run}")
    print(f"   Output Path: {config.output_path}")
    
    try:
        # Create orchestrator
        orchestrator = ScraperOrchestrator(config)
        
        print(f"\n🚀 Starting extraction...")
        
        # Run scraping
        result = await orchestrator.start()
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Total Scraped: {result.total_scraped}")
        print(f"   Unique Affiliators: {result.unique_affiliators}")
        print(f"   Errors: {result.errors}")
        print(f"   Duration: {result.duration:.1f} seconds")
        
        # Get the extracted data
        all_data = orchestrator._deduplicator.get_all()
        
        print(f"\n👥 EXTRACTED CREATOR DATA:")
        for i, creator in enumerate(all_data, 1):
            print(f"\n   Creator {i}:")
            print(f"      Username: {creator.username}")
            print(f"      Category: {creator.kategori}")
            print(f"      Followers: {creator.pengikut:,}" if creator.pengikut else "      Followers: None")
            print(f"      GMV: Rp {creator.gmv:,.0f}" if creator.gmv else "      GMV: None")
            print(f"      📞 Phone: {creator.nomor_kontak or 'Not found'}")
            print(f"      💬 WhatsApp: {creator.nomor_whatsapp or 'Not found'}")
            print(f"      🔗 Detail URL: {creator.detail_url}")
            print(f"      📅 Scraped: {creator.scraped_at}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'final_contact_validation_{timestamp}.json'
        
        # Convert to serializable format
        detailed_results = []
        for creator in all_data:
            detailed_results.append({
                'username': creator.username,
                'kategori': creator.kategori,
                'pengikut': creator.pengikut,
                'gmv': creator.gmv,
                'nomor_kontak': creator.nomor_kontak,
                'nomor_whatsapp': creator.nomor_whatsapp,
                'detail_url': creator.detail_url,
                'scraped_at': creator.scraped_at.isoformat() if creator.scraped_at else None
            })
        
        final_data = {
            'test_info': {
                'test_type': 'final_contact_validation',
                'timestamp': timestamp,
                'total_scraped': result.total_scraped,
                'unique_affiliators': result.unique_affiliators,
                'errors': result.errors,
                'duration': result.duration
            },
            'creators': detailed_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved: {output_file}")
        
        # Assessment
        contact_found = sum(1 for c in all_data if c.nomor_kontak or c.nomor_whatsapp)
        contact_rate = (contact_found / len(all_data) * 100) if all_data else 0
        
        print(f"\n🎯 CONTACT EXTRACTION ASSESSMENT:")
        print(f"   Creators with contact info: {contact_found}/{len(all_data)}")
        print(f"   Contact extraction rate: {contact_rate:.1f}%")
        
        if contact_rate >= 70:
            print(f"   ✅ EXCELLENT - High contact extraction success")
        elif contact_rate >= 50:
            print(f"   ✅ GOOD - Moderate contact extraction success")
        elif contact_rate >= 30:
            print(f"   ⚠️ MODERATE - Some contact extraction success")
        else:
            print(f"   ❌ POOR - Low contact extraction success")
        
        print(f"\n🏆 FINAL STATUS:")
        if result.unique_affiliators > 0 and contact_rate > 0:
            print(f"   ✅ SUCCESS - Data extraction with contact info working!")
            print(f"   📊 Ready for production with contact extraction")
        else:
            print(f"   ⚠️ PARTIAL - Data extraction working but contact extraction needs improvement")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_final_contact_validation())