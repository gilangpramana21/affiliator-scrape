#!/usr/bin/env python3
"""
Production-Ready Test untuk Tokopedia Affiliate Scraper.

Comprehensive test yang simulate production environment:
1. Full orchestrator workflow
2. Premium CAPTCHA handling
3. Real data extraction dengan contact info
4. Performance monitoring
5. Error handling validation
6. Success rate measurement

Usage: python test_production_ready.py
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.core.premium_captcha_handler import create_premium_captcha_handler
from src.models.config import Configuration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionReadyTest:
    """Production-ready test dengan full orchestrator."""
    
    def __init__(self, use_premium_captcha: bool = True, max_pages: int = 2):
        self.use_premium_captcha = use_premium_captcha
        self.max_pages = max_pages
        
        # Load configuration
        self.config = Configuration.from_file("config/config_jelajahi.json")
        
        # Override some settings for testing
        self.config.max_pages_per_run = max_pages
        self.config.incremental_save = True
        self.config.save_interval = 5  # Save every 5 creators
        
        # Setup premium CAPTCHA if requested
        if use_premium_captcha:
            try:
                with open("config/premium_captcha_config.json", 'r') as f:
                    captcha_config = json.load(f)['captcha_config']
                
                # Validate API keys
                api_keys = captcha_config.get('api_keys', {})
                valid_keys = sum(1 for key in api_keys.values() 
                               if key and not key.startswith('YOUR_'))
                
                if valid_keys >= 1:
                    self.captcha_config = captcha_config
                    print(f"✅ Premium CAPTCHA enabled ({valid_keys} services configured)")
                else:
                    print("⚠️ No valid premium CAPTCHA keys found, using standard handler")
                    self.captcha_config = None
            except Exception as e:
                print(f"⚠️ Premium CAPTCHA config error: {e}")
                self.captcha_config = None
        else:
            self.captcha_config = None
        
        # Test results
        self.test_results = {
            'orchestrator_performance': {},
            'captcha_performance': {},
            'extraction_performance': {},
            'error_handling': {},
            'production_readiness': {}
        }
    
    async def run_production_test(self) -> Dict:
        """Run comprehensive production readiness test."""
        
        print("🏭 PRODUCTION READINESS TEST")
        print("=" * 60)
        print(f"Testing full orchestrator workflow with real data extraction")
        print(f"CAPTCHA: {'Premium' if self.captcha_config else 'Standard'}")
        print(f"Max Pages: {self.max_pages}")
        
        try:
            # Phase 1: Setup Orchestrator
            orchestrator = await self._setup_orchestrator()
            
            # Phase 2: Run Scraping Operation
            results = await self._run_scraping_operation(orchestrator)
            
            # Phase 3: Analyze Results
            analysis = await self._analyze_results(results)
            
            # Phase 4: Generate Production Assessment
            assessment = self._generate_production_assessment(analysis)
            
            return {
                'scraping_results': results,
                'performance_analysis': analysis,
                'production_assessment': assessment,
                'test_results': self.test_results
            }
            
        except Exception as e:
            logger.error(f"Production test error: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'test_results': self.test_results}
    
    async def _setup_orchestrator(self) -> ScraperOrchestrator:
        """Setup orchestrator dengan premium enhancements."""
        
        print("\n🔧 Setting up orchestrator...")
        
        # Create orchestrator
        orchestrator = ScraperOrchestrator(self.config)
        
        # Replace CAPTCHA handler with premium version if available
        if self.captcha_config:
            try:
                premium_handler = create_premium_captcha_handler(self.captcha_config)
                orchestrator._captcha_handler = premium_handler
                print("   ✅ Premium CAPTCHA handler integrated")
            except Exception as e:
                print(f"   ⚠️ Premium CAPTCHA setup failed: {e}")
        
        print("   ✅ Orchestrator configured")
        return orchestrator
    
    async def _run_scraping_operation(self, orchestrator: ScraperOrchestrator) -> Dict:
        """Run actual scraping operation."""
        
        print("\n🚀 Starting scraping operation...")
        
        start_time = time.time()
        
        try:
            # Start scraping
            result = await orchestrator.start()
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   ✅ Scraping completed in {duration:.1f} seconds")
            
            # Convert result to dict for analysis
            result_dict = {
                'total_scraped': result.total_scraped,
                'unique_affiliators': result.unique_affiliators,
                'duplicates_found': result.duplicates_found,
                'errors': result.errors,
                'captchas_encountered': result.captchas_encountered,
                'duration': result.duration,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat()
            }
            
            return result_dict
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   ❌ Scraping failed after {duration:.1f} seconds: {e}")
            
            return {
                'error': str(e),
                'duration': duration,
                'partial_results': True
            }
    
    async def _analyze_results(self, results: Dict) -> Dict:
        """Analyze scraping results untuk production assessment."""
        
        print("\n📊 Analyzing results...")
        
        analysis = {
            'performance_metrics': {},
            'success_rates': {},
            'error_analysis': {},
            'captcha_analysis': {}
        }
        
        try:
            # Performance metrics
            total_scraped = results.get('total_scraped', 0)
            duration = results.get('duration', 0)
            
            if duration > 0:
                creators_per_minute = (total_scraped / duration) * 60
                analysis['performance_metrics'] = {
                    'total_scraped': total_scraped,
                    'duration_seconds': duration,
                    'creators_per_minute': creators_per_minute,
                    'average_time_per_creator': duration / total_scraped if total_scraped > 0 else 0
                }
            
            # Success rates
            unique_affiliators = results.get('unique_affiliators', 0)
            duplicates = results.get('duplicates_found', 0)
            errors = results.get('errors', 0)
            
            total_processed = unique_affiliators + duplicates + errors
            success_rate = (unique_affiliators / total_processed * 100) if total_processed > 0 else 0
            
            analysis['success_rates'] = {
                'unique_affiliators': unique_affiliators,
                'duplicates_found': duplicates,
                'errors': errors,
                'total_processed': total_processed,
                'success_rate': success_rate,
                'error_rate': (errors / total_processed * 100) if total_processed > 0 else 0
            }
            
            # CAPTCHA analysis
            captchas_encountered = results.get('captchas_encountered', 0)
            
            analysis['captcha_analysis'] = {
                'captchas_encountered': captchas_encountered,
                'captcha_rate': (captchas_encountered / total_processed * 100) if total_processed > 0 else 0,
                'handler_type': 'Premium' if self.captcha_config else 'Standard'
            }
            
            print(f"   📈 Performance: {creators_per_minute:.1f} creators/minute")
            print(f"   ✅ Success Rate: {success_rate:.1f}%")
            print(f"   🔒 CAPTCHA Rate: {analysis['captcha_analysis']['captcha_rate']:.1f}%")
            
        except Exception as e:
            print(f"   ⚠️ Analysis error: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _generate_production_assessment(self, analysis: Dict) -> Dict:
        """Generate production readiness assessment."""
        
        print("\n🎯 Generating production assessment...")
        
        assessment = {
            'overall_score': 0,
            'readiness_level': 'Not Ready',
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'deployment_ready': False
        }
        
        try:
            score = 0
            max_score = 100
            
            # Performance scoring (30 points)
            performance = analysis.get('performance_metrics', {})
            creators_per_minute = performance.get('creators_per_minute', 0)
            
            if creators_per_minute >= 10:
                score += 30
                assessment['strengths'].append("Excellent performance (10+ creators/min)")
            elif creators_per_minute >= 5:
                score += 20
                assessment['strengths'].append("Good performance (5+ creators/min)")
            elif creators_per_minute >= 2:
                score += 10
                assessment['weaknesses'].append("Moderate performance (2+ creators/min)")
            else:
                assessment['weaknesses'].append("Low performance (<2 creators/min)")
                assessment['recommendations'].append("Optimize scraping speed and reduce delays")
            
            # Success rate scoring (40 points)
            success_rates = analysis.get('success_rates', {})
            success_rate = success_rates.get('success_rate', 0)
            
            if success_rate >= 90:
                score += 40
                assessment['strengths'].append(f"Excellent success rate ({success_rate:.1f}%)")
            elif success_rate >= 80:
                score += 30
                assessment['strengths'].append(f"Good success rate ({success_rate:.1f}%)")
            elif success_rate >= 70:
                score += 20
                assessment['weaknesses'].append(f"Moderate success rate ({success_rate:.1f}%)")
            else:
                assessment['weaknesses'].append(f"Low success rate ({success_rate:.1f}%)")
                assessment['recommendations'].append("Improve error handling and retry logic")
            
            # CAPTCHA handling scoring (20 points)
            captcha_analysis = analysis.get('captcha_analysis', {})
            captcha_rate = captcha_analysis.get('captcha_rate', 0)
            handler_type = captcha_analysis.get('handler_type', 'Standard')
            
            if handler_type == 'Premium' and captcha_rate < 10:
                score += 20
                assessment['strengths'].append("Premium CAPTCHA handling with low encounter rate")
            elif handler_type == 'Premium':
                score += 15
                assessment['strengths'].append("Premium CAPTCHA handling configured")
            elif captcha_rate < 5:
                score += 10
                assessment['strengths'].append("Low CAPTCHA encounter rate")
            else:
                assessment['weaknesses'].append("High CAPTCHA encounter rate")
                assessment['recommendations'].append("Configure premium CAPTCHA solving services")
            
            # Error handling scoring (10 points)
            error_rate = success_rates.get('error_rate', 0)
            
            if error_rate < 5:
                score += 10
                assessment['strengths'].append("Excellent error handling")
            elif error_rate < 10:
                score += 7
                assessment['strengths'].append("Good error handling")
            elif error_rate < 20:
                score += 3
                assessment['weaknesses'].append("Moderate error rate")
            else:
                assessment['weaknesses'].append("High error rate")
                assessment['recommendations'].append("Improve error handling and resilience")
            
            # Determine readiness level
            assessment['overall_score'] = score
            
            if score >= 85:
                assessment['readiness_level'] = 'Production Ready'
                assessment['deployment_ready'] = True
            elif score >= 70:
                assessment['readiness_level'] = 'Nearly Ready'
                assessment['recommendations'].append("Address minor issues before production deployment")
            elif score >= 50:
                assessment['readiness_level'] = 'Needs Improvement'
                assessment['recommendations'].append("Significant improvements needed before production")
            else:
                assessment['readiness_level'] = 'Not Ready'
                assessment['recommendations'].append("Major issues must be resolved before production")
            
            # Additional recommendations
            if not assessment['recommendations']:
                assessment['recommendations'].append("System is ready for production deployment")
            
            print(f"   🏆 Overall Score: {score}/100")
            print(f"   📊 Readiness Level: {assessment['readiness_level']}")
            print(f"   🚀 Deployment Ready: {'Yes' if assessment['deployment_ready'] else 'No'}")
            
        except Exception as e:
            print(f"   ⚠️ Assessment error: {e}")
            assessment['error'] = str(e)
        
        return assessment


async def main():
    """Main production test function."""
    
    print("🏭 TOKOPEDIA AFFILIATE SCRAPER - PRODUCTION READINESS TEST")
    print("=" * 70)
    
    # Configuration
    print("Test Configuration:")
    print("1. CAPTCHA Handler:")
    print("   p = Premium (recommended for production)")
    print("   s = Standard (manual solving)")
    
    print("2. Test scope:")
    print("   Enter number of pages to test (1-5, recommended: 2)")
    
    # Get user preferences
    captcha_choice = input("\nCAPTCHA Handler (p/s): ").strip().lower()
    use_premium = captcha_choice == 'p'
    
    try:
        max_pages = int(input("Number of pages (default 2): ").strip() or "2")
        max_pages = min(max(max_pages, 1), 5)  # Limit 1-5
    except ValueError:
        max_pages = 2
    
    print(f"\n📋 Production Test Configuration:")
    print(f"   CAPTCHA Handler: {'Premium' if use_premium else 'Standard'}")
    print(f"   Test Scope: {max_pages} pages")
    print(f"   Full Orchestrator: Yes")
    print(f"   Real Data Extraction: Yes")
    
    confirm = input("\nProceed with production test? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Production test cancelled.")
        return
    
    # Run production test
    test_runner = ProductionReadyTest(
        use_premium_captcha=use_premium,
        max_pages=max_pages
    )
    
    try:
        print(f"\n🚀 Starting production readiness test...")
        results = await test_runner.run_production_test()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'production_test_results_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # Print final assessment
        assessment = results.get('production_assessment', {})
        
        print(f"\n🎯 PRODUCTION READINESS ASSESSMENT:")
        print("=" * 60)
        
        print(f"🏆 Overall Score: {assessment.get('overall_score', 0)}/100")
        print(f"📊 Readiness Level: {assessment.get('readiness_level', 'Unknown')}")
        print(f"🚀 Deployment Ready: {'✅ YES' if assessment.get('deployment_ready') else '❌ NO'}")
        
        # Show strengths
        strengths = assessment.get('strengths', [])
        if strengths:
            print(f"\n✅ Strengths:")
            for strength in strengths:
                print(f"   • {strength}")
        
        # Show weaknesses
        weaknesses = assessment.get('weaknesses', [])
        if weaknesses:
            print(f"\n⚠️ Areas for Improvement:")
            for weakness in weaknesses:
                print(f"   • {weakness}")
        
        # Show recommendations
        recommendations = assessment.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for recommendation in recommendations:
                print(f"   • {recommendation}")
        
        print(f"\n💾 Full results saved: {output_file}")
        
        # Final verdict
        if assessment.get('deployment_ready'):
            print(f"\n🎉 PRODUCTION DEPLOYMENT APPROVED!")
            print(f"   The scraper is ready for production use.")
            print(f"   Expected performance: High success rate with reliable data extraction.")
        else:
            print(f"\n⚠️ PRODUCTION DEPLOYMENT NOT RECOMMENDED")
            print(f"   Please address the identified issues before deploying to production.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Production test interrupted by user")
    except Exception as e:
        print(f"\n❌ Production test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())