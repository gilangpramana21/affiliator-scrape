#!/usr/bin/env python3
"""Manual test script for CreepJS fingerprint detection.

This script launches a browser with our fingerprint randomization and navigates
to the CreepJS fingerprint detection tool to verify our anti-detection measures.

Usage:
    python tests/manual/test_creepjs_fingerprint.py [--headless]
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator


CREEPJS_URL = "https://abrahamjuliot.github.io/creepjs/"


async def main(headless: bool = False):
    """Run the CreepJS fingerprint test."""
    print("=" * 80)
    print("CreepJS Fingerprint Detection Test")
    print("=" * 80)
    print()
    
    # Generate fingerprint
    print("1. Generating browser fingerprint...")
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    
    print(f"   Browser: {fingerprint.browser} {fingerprint.browser_version}")
    print(f"   Platform: {fingerprint.platform}")
    print(f"   User-Agent: {fingerprint.user_agent}")
    print(f"   Screen: {fingerprint.screen_resolution}")
    print(f"   Viewport: {fingerprint.viewport_size}")
    print(f"   Timezone: {fingerprint.timezone} (offset: {fingerprint.timezone_offset})")
    print(f"   WebGL: {fingerprint.webgl_vendor} / {fingerprint.webgl_renderer}")
    print()
    
    # Launch browser
    print(f"2. Launching browser (headless={headless})...")
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=headless)
    print("   Browser launched successfully")
    print()
    
    # Navigate to CreepJS
    print("3. Navigating to CreepJS...")
    print(f"   URL: {CREEPJS_URL}")
    page = await engine.navigate(CREEPJS_URL, wait_for="networkidle")
    print("   Page loaded")
    print()
    
    # Wait for CreepJS to complete analysis
    print("4. Waiting for CreepJS analysis to complete...")
    print("   (This may take 10-30 seconds)")
    
    try:
        # Wait for the trust score element to appear
        await page.wait_for_selector(".trust-score", timeout=60000)
        await asyncio.sleep(5)  # Extra time for all checks to complete
        print("   Analysis complete")
    except Exception as e:
        print(f"   Warning: Could not detect completion: {e}")
        print("   Waiting 30 seconds anyway...")
        await asyncio.sleep(30)
    
    print()
    
    # Extract results
    print("5. Extracting results...")
    try:
        # Get trust score
        trust_score_elem = await page.query_selector(".trust-score")
        if trust_score_elem:
            trust_score = await trust_score_elem.inner_text()
            print(f"   Trust Score: {trust_score}")
        else:
            print("   Trust Score: Not found")
        
        # Get lies detected
        lies_elem = await page.query_selector(".lies")
        if lies_elem:
            lies = await lies_elem.inner_text()
            print(f"   Lies Detected: {lies}")
        else:
            print("   Lies Detected: Not found")
        
        # Get bot probability
        bot_elem = await page.query_selector(".bot-detection")
        if bot_elem:
            bot_prob = await bot_elem.inner_text()
            print(f"   Bot Detection: {bot_prob}")
        else:
            print("   Bot Detection: Not found")
            
    except Exception as e:
        print(f"   Error extracting results: {e}")
    
    print()
    print("6. Manual inspection required:")
    print("   - Review the CreepJS page in the browser window")
    print("   - Check the trust score (should be > 70%)")
    print("   - Verify no major inconsistencies are flagged")
    print("   - Look for any red flags or warnings")
    print()
    
    if not headless:
        print("   Browser window is open. Press Enter when done reviewing...")
        input()
    else:
        print("   Running in headless mode. Waiting 60 seconds for review...")
        await asyncio.sleep(60)
    
    # Cleanup
    print()
    print("7. Cleaning up...")
    await engine.close()
    print("   Browser closed")
    print()
    
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review the results above")
    print("2. Consult docs/manual_tests/creepjs_guide.md for interpretation")
    print("3. If trust score < 70%, investigate flagged issues")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test browser fingerprint with CreepJS")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: headed for manual inspection)"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(headless=args.headless))
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
