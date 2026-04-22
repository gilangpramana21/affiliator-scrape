# CreepJS Fingerprint Detection Test Guide

## Overview

This guide explains how to run and interpret the CreepJS fingerprint detection test to verify that our browser fingerprint randomization is working correctly and cannot be easily detected as a bot.

## What is CreepJS?

CreepJS is an advanced browser fingerprinting tool that:
- Analyzes 50+ browser characteristics
- Detects inconsistencies in fingerprints
- Calculates a "trust score" based on how legitimate the browser appears
- Identifies common automation indicators
- Detects "lies" (inconsistent data points)

**Website**: https://abrahamjuliot.github.io/creepjs/

## Running the Test

### Prerequisites

1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Navigate to the project root directory

### Execute the Test

**Option 1: Headed Mode (Recommended for first-time testing)**
```bash
python tests/manual/test_creepjs_fingerprint.py
```

This opens a visible browser window so you can see the CreepJS analysis in real-time.

**Option 2: Headless Mode**
```bash
python tests/manual/test_creepjs_fingerprint.py --headless
```

This runs the browser in headless mode. Useful for automated checks, but you won't see the visual results.

### What the Script Does

1. **Generates a random fingerprint** using our `FingerprintGenerator`
2. **Launches a browser** with our `BrowserEngine` and applies stealth patches
3. **Navigates to CreepJS** and waits for analysis to complete
4. **Extracts key metrics** (trust score, lies detected, bot probability)
5. **Pauses for manual inspection** (in headed mode)

## Interpreting Results

### Trust Score

The trust score is the most important metric. It represents how "trustworthy" or legitimate the browser appears.

| Trust Score | Interpretation | Action Required |
|-------------|----------------|-----------------|
| **90-100%** | Excellent - Appears completely legitimate | ✅ PASS - No action needed |
| **70-89%** | Good - Minor inconsistencies but acceptable | ✅ PASS - Monitor for patterns |
| **50-69%** | Suspicious - Multiple inconsistencies detected | ⚠️ INVESTIGATE - Review flagged issues |
| **< 50%** | High Risk - Likely to be flagged as bot | ❌ FAIL - Fix critical issues |

**Target**: Aim for **70%+** trust score consistently.

### Lies Detected

"Lies" are inconsistencies in the fingerprint where different APIs report conflicting information.

**Examples of lies:**
- Canvas fingerprint doesn't match WebGL renderer
- Timezone offset doesn't match reported timezone
- Screen resolution doesn't match window dimensions
- User-Agent doesn't match platform APIs

| Lies Count | Interpretation | Action Required |
|------------|----------------|-----------------|
| **0-2** | Excellent - Highly consistent fingerprint | ✅ PASS |
| **3-5** | Acceptable - Minor inconsistencies | ⚠️ MONITOR |
| **6+** | Poor - Major inconsistencies | ❌ INVESTIGATE |

**Target**: **0-2 lies** maximum.

### Bot Detection Indicators

CreepJS checks for common automation indicators:

#### ✅ Should NOT be detected:
- `navigator.webdriver` should be `undefined` (not `true`)
- `chrome.runtime` should be `undefined` or properly spoofed
- Canvas/WebGL/Audio fingerprints should have natural variation
- Fonts should match the OS
- Plugins should be realistic for the browser

#### ❌ Red Flags:
- `navigator.webdriver === true` → **CRITICAL** - Stealth patches failed
- Empty plugin list on Chrome → Suspicious
- Identical canvas fingerprint across sessions → Detectable pattern
- Timezone mismatch → Inconsistent fingerprint
- Missing or unrealistic hardware specs → Suspicious

## Common Issues and Fixes

### Issue 1: Low Trust Score (< 70%)

**Symptoms**: Trust score consistently below 70%

**Possible Causes**:
1. Stealth patches not applied correctly
2. Fingerprint inconsistencies (lies detected)
3. Unrealistic hardware/software combination

**Fixes**:
1. Verify stealth scripts are injected: Check `browser_engine.py` → `_inject_stealth_scripts()`
2. Review fingerprint generation logic: Check `fingerprint_generator.py` → `validate_consistency()`
3. Test with different browser/OS combinations

### Issue 2: navigator.webdriver Detected

**Symptoms**: CreepJS shows `navigator.webdriver = true`

**Possible Causes**:
- Stealth patch for webdriver not applied
- Playwright's built-in stealth not working

**Fixes**:
1. Verify `_STEALTH_WEBDRIVER_JS` is injected in `browser_engine.py`
2. Check that `--disable-blink-features=AutomationControlled` is in launch args
3. Ensure `add_init_script()` is called before page navigation

### Issue 3: Canvas/WebGL Fingerprint Identical

**Symptoms**: Same canvas/WebGL fingerprint across multiple test runs

**Possible Causes**:
- Noise injection not working
- Randomization seed not changing

**Fixes**:
1. Verify `_CANVAS_NOISE_JS` and `_WEBGL_NOISE_JS` are injected
2. Check that noise is truly random (not seeded)
3. Test with multiple fingerprint generations

### Issue 4: Timezone Inconsistencies

**Symptoms**: Timezone offset doesn't match timezone name

**Possible Causes**:
- Fingerprint generator has incorrect offset mapping
- Browser context not applying timezone correctly

**Fixes**:
1. Verify `TIMEZONE_WEIGHTS` in `fingerprint_generator.py` has correct offsets
2. Check that `timezone_id` is passed to `browser.new_context()`
3. Validate with `fingerprint_generator.validate_consistency()`

### Issue 5: Platform/User-Agent Mismatch

**Symptoms**: User-Agent says Windows but platform APIs say macOS

**Possible Causes**:
- Fingerprint generation logic inconsistent
- Platform not properly set in browser context

**Fixes**:
1. Review `_build_user_agent()` and `_select_os()` in `fingerprint_generator.py`
2. Ensure `platform` field matches OS in User-Agent
3. Run consistency validation: `generator.validate_consistency(fingerprint)`

## Expected Results (Examples)

### ✅ PASS Example

```
Trust Score: 87%
Lies Detected: 1
Bot Detection: Low Risk

Fingerprint Details:
- navigator.webdriver: undefined ✓
- Canvas: Unique with natural noise ✓
- WebGL: Intel UHD Graphics 620 ✓
- Timezone: Asia/Jakarta (UTC+7) ✓
- Plugins: Chrome PDF Plugin, Chrome PDF Viewer ✓
- Hardware: 8 cores, 8GB RAM ✓
```

**Interpretation**: Excellent result. Fingerprint appears legitimate with only 1 minor inconsistency.

### ⚠️ INVESTIGATE Example

```
Trust Score: 62%
Lies Detected: 4
Bot Detection: Medium Risk

Issues Flagged:
- Timezone offset mismatch (reported +7 but calculated +8)
- Canvas fingerprint too consistent
- Missing expected fonts for Windows 10
- Screen resolution uncommon for reported device
```

**Interpretation**: Multiple inconsistencies detected. Review fingerprint generation logic and fix the flagged issues.

### ❌ FAIL Example

```
Trust Score: 34%
Lies Detected: 8
Bot Detection: High Risk

Critical Issues:
- navigator.webdriver = true ❌
- chrome.runtime exists (automation detected) ❌
- Canvas fingerprint identical to known bot pattern ❌
- No plugins (suspicious for Chrome) ❌
- Timezone: UTC (not Indonesian) ❌
```

**Interpretation**: Critical failures. Stealth patches not working. Fix immediately before using in production.

## Testing Best Practices

### 1. Test Multiple Fingerprints

Run the test 5-10 times with different generated fingerprints to ensure:
- Trust scores are consistently high
- No patterns emerge that could be detected
- Randomization is working correctly

```bash
for i in {1..10}; do
    echo "Test run $i"
    python tests/manual/test_creepjs_fingerprint.py --headless
    sleep 5
done
```

### 2. Test Different Browser Types

If supporting multiple browsers, test each:
```python
# In fingerprint_generator.py, temporarily force browser type
BROWSER_WEIGHTS = [("Chrome", 1.0), ("Firefox", 0.0), ("Safari", 0.0)]
```

Run test, then change to Firefox, then Safari.

### 3. Compare with Real Browser

Run CreepJS in your actual browser (not automated) and compare:
- Trust score should be similar (±10%)
- Lies detected should be comparable
- No obvious differences in fingerprint characteristics

### 4. Test After Code Changes

Always run this test after modifying:
- `browser_engine.py` (stealth patches)
- `fingerprint_generator.py` (fingerprint logic)
- `behavioral_simulator.py` (if it affects page load)

## Troubleshooting

### Test Script Fails to Run

**Error**: `ModuleNotFoundError: No module named 'playwright'`

**Fix**:
```bash
pip install playwright
playwright install chromium
```

### Browser Doesn't Launch

**Error**: `Browser closed unexpectedly`

**Fix**:
1. Check system resources (RAM, CPU)
2. Try headed mode instead of headless
3. Check Playwright installation: `playwright install --force chromium`

### CreepJS Page Doesn't Load

**Error**: `Timeout waiting for page load`

**Fix**:
1. Check internet connection
2. Try increasing timeout in script
3. Verify URL is accessible: https://abrahamjuliot.github.io/creepjs/

### Can't Extract Results

**Error**: `Trust Score: Not found`

**Fix**:
1. CreepJS may have changed its HTML structure
2. Inspect the page manually and update selectors in script
3. Take a screenshot: `await page.screenshot(path="creepjs.png")`

## Success Criteria

The test is considered **PASSED** if:

1. ✅ Trust score ≥ 70% (consistently across multiple runs)
2. ✅ Lies detected ≤ 2
3. ✅ `navigator.webdriver` is `undefined`
4. ✅ No critical bot detection indicators flagged
5. ✅ Fingerprint characteristics are internally consistent
6. ✅ Results vary naturally between test runs (not identical)

## Next Steps After Testing

### If Test Passes ✅
1. Document the successful configuration
2. Run the test periodically (weekly) to catch regressions
3. Proceed with integration testing against real targets

### If Test Fails ❌
1. Review the specific issues flagged by CreepJS
2. Fix the root causes in `browser_engine.py` or `fingerprint_generator.py`
3. Re-run the test to verify fixes
4. Do NOT proceed to production until test passes

## Additional Resources

- **CreepJS GitHub**: https://github.com/abrahamjuliot/creepjs
- **Playwright Stealth**: https://github.com/AtuboDad/playwright_stealth
- **Browser Fingerprinting Guide**: https://pixelprivacy.com/resources/browser-fingerprinting/
- **Anti-Detection Best Practices**: See `docs/anti_detection_best_practices.md`

## Maintenance

This test should be run:
- ✅ Before each production deployment
- ✅ After any changes to anti-detection code
- ✅ Weekly as part of regression testing
- ✅ When CreepJS updates (check for new detection methods)

Keep this guide updated as CreepJS evolves and new detection techniques emerge.
