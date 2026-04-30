# ✅ "Coba Lagi" Detection - Implementation Summary

## 📋 Overview

Implementasi deteksi "Coba lagi" blocking page dengan auto-refresh di `scrape_full_data.py`.

---

## 🔧 Changes Made

### 1. Import ErrorAnalyzer

```python
from src.core.error_analyzer import ErrorAnalyzer
```

### 2. Initialize ErrorAnalyzer in Constructor

```python
def __init__(self, cookie_file: str = "config/cookies.json"):
    # ... existing code ...
    self.error_analyzer = ErrorAnalyzer()  # Add error analyzer
```

### 3. New Method: `check_and_handle_coba_lagi()`

**Location**: After `setup_browser()` method

**Purpose**: Detect "coba lagi" blocking page and **click the "Coba lagi" button** to retry

**Parameters**:
- `page`: Playwright page object
- `location`: Description of where we are (for logging)
- `max_retries`: Maximum number of retry attempts (default: 3)

**Returns**:
- `True`: Page is OK (no blocking)
- `False`: Still blocked after max retries

**Logic**:
1. Get page HTML content
2. Check for "coba lagi" using `error_analyzer.detect_coba_lagi()`
3. If detected:
   - Print warning message
   - **Try to find and click "Coba lagi" button** using multiple selectors:
     - `button:has-text("Coba lagi")`
     - `button:has-text("Try again")`
     - `button:has-text("Coba Lagi")`
     - `button:has-text("COBA LAGI")`
     - `a:has-text("Coba lagi")`
     - `a:has-text("Try again")`
     - `[class*="retry"]`
     - `[class*="coba-lagi"]`
   - Wait for page to reload after clicking
   - If button not found, fallback to page reload
   - Retry up to max_retries times
4. If still blocked after max retries:
   - Print error message with possible causes
   - Return False
5. If page is OK:
   - Print success message (if retries were needed)
   - Return True

**Patterns Detected**:
- "coba lagi" (Indonesian: "try again")
- "try again" (English)
- "silakan coba lagi" (Indonesian: "please try again")
- "please try again" (English)
- "terjadi kesalahan" (Indonesian: "an error occurred")
- "something went wrong" (English)

### 4. Integration in `scrape()` Method

**List Page Check** (after navigation):
```python
# Check for "coba lagi" blocking page
if not await self.check_and_handle_coba_lagi(page, "LIST PAGE"):
    print("\n❌ Cannot proceed - list page is blocked")
    print("   Please check your cookies or try again later")
    return
```

**Detail Page Check** (after CAPTCHA solving):
```python
# Check for "coba lagi" blocking page on detail page
if not await self.check_and_handle_coba_lagi(detail_page, "DETAIL PAGE"):
    print(f"   ⚠️  Detail page is blocked - skipping this creator")
    return list_data
```

---

## 🎯 How It Works

### Scenario 1: List Page Blocked

```
1. Navigate to list page
2. Detect "coba lagi" blocking page
3. Find and click "Coba lagi" button (attempt 1/3)
4. Wait for page to reload
5. Still blocked → Click button again (attempt 2/3)
6. Still blocked → Click button again (attempt 3/3)
7. Still blocked → Stop scraping, show error message
```

### Scenario 2: Detail Page Blocked

```
1. Click on creator row
2. Detail page opens
3. Solve CAPTCHA manually
4. Detect "coba lagi" blocking page
5. Find and click "Coba lagi" button (attempt 1/3)
6. Wait for page to reload
7. Page loads successfully
8. Continue extracting data
```

### Scenario 3: No Blocking

```
1. Navigate to page
2. Check for "coba lagi" → Not detected
3. Continue normally (no button click needed)
```

### Scenario 4: Button Not Found (Fallback)

```
1. Detect "coba lagi" blocking page
2. Try to find button with 8 different selectors
3. Button not found → Fallback to page reload
4. Continue retry logic
```

---

## 📊 User Experience

### Before (Without Detection):
```
❌ Scraper continues with blocked page
❌ Extracts empty/invalid data
❌ User doesn't know what went wrong
```

### After (With Detection):
```
✅ Detects blocking page immediately
✅ Auto-refreshes up to 3 times
✅ Clear error messages if still blocked
✅ Suggests possible causes and solutions
```

---

## 🔍 Example Output

### Success After Retry:
```
⚠️  'Coba lagi' blocking page detected at LIST PAGE
   🔄 Clicking 'Coba lagi' button... (attempt 1/3)
   ✓ Found button with selector: button:has-text("Coba lagi")
   ✅ Page loaded successfully after 1 retry(ies)
```

### Button Not Found (Fallback):
```
⚠️  'Coba lagi' blocking page detected at DETAIL PAGE
   🔄 Clicking 'Coba lagi' button... (attempt 1/3)
   ⚠️  'Coba lagi' button not found, trying page reload...
   ✅ Page loaded successfully after 1 retry(ies)
```

### Failed After Max Retries:
```
⚠️  'Coba lagi' blocking page detected at DETAIL PAGE
   🔄 Clicking 'Coba lagi' button... (attempt 1/3)
   ✓ Found button with selector: button:has-text("Coba lagi")
⚠️  'Coba lagi' blocking page detected at DETAIL PAGE
   🔄 Clicking 'Coba lagi' button... (attempt 2/3)
   ✓ Found button with selector: button:has-text("Coba lagi")
⚠️  'Coba lagi' blocking page detected at DETAIL PAGE
   ❌ Still blocked after 3 attempts
   💡 Possible causes:
      - Cookies expired or invalid
      - IP blocked or low reputation
      - Too many requests
   ⚠️  Detail page is blocked - skipping this creator
```

---

## ⚙️ Configuration

### Max Retries

Default: 3 attempts

To change, modify the method call:
```python
# 5 retries instead of 3
if not await self.check_and_handle_coba_lagi(page, "LIST PAGE", max_retries=5):
    # handle error
```

### Retry Delay

Default: 3 seconds after clicking button, then wait for networkidle

To change, modify the sleep duration in `check_and_handle_coba_lagi()`:
```python
await asyncio.sleep(3)  # Change to desired seconds
```

### Button Selectors

The method tries 8 different selectors to find the "Coba lagi" button:

1. `button:has-text("Coba lagi")` - Standard button with Indonesian text
2. `button:has-text("Try again")` - Standard button with English text
3. `button:has-text("Coba Lagi")` - Title case
4. `button:has-text("COBA LAGI")` - Uppercase
5. `a:has-text("Coba lagi")` - Link styled as button (Indonesian)
6. `a:has-text("Try again")` - Link styled as button (English)
7. `[class*="retry"]` - Element with "retry" in class name
8. `[class*="coba-lagi"]` - Element with "coba-lagi" in class name

If none found, falls back to page reload.

---

## 🧪 Testing

### Manual Test:

1. Run scraper with expired cookies:
   ```bash
   python scrape_full_data.py --max-creators 5
   ```

2. Expected behavior:
   - Detects "coba lagi" on list page
   - Auto-refreshes 3 times
   - Shows error message if still blocked

### Test with Valid Cookies:

1. Run scraper with valid cookies:
   ```bash
   python scrape_full_data.py --max-creators 5
   ```

2. Expected behavior:
   - No "coba lagi" detected
   - Continues normally
   - No unnecessary refreshes

---

## 🔗 Related Files

- **`src/core/error_analyzer.py`**: Contains `detect_coba_lagi()` method
- **`src/core/scraper_orchestrator.py`**: Original implementation (reference)
- **`tests/unit/test_error_analyzer.py`**: Unit tests for detection logic
- **`tests/unit/test_cookie_expiration_handling.py`**: Integration tests

---

## 📝 Notes

### Why Click Button Instead of Refresh?

1. **Proper flow**: Clicking "Coba lagi" button follows Tokopedia's intended user flow
2. **Better success rate**: Button click may trigger proper retry logic on server side
3. **Avoid detection**: Page reload might look more bot-like
4. **Fallback available**: If button not found, still falls back to page reload

### Why Multiple Selectors?

1. **Flexibility**: Tokopedia might change button styling or text
2. **Language support**: Handles both Indonesian and English versions
3. **Case variations**: Handles different text cases (lowercase, uppercase, title case)
4. **Element types**: Handles both `<button>` and `<a>` elements
5. **Class-based**: Handles custom styled elements with specific class names

### Why Max 3 Retries?

1. **Balance**: Enough attempts to handle temporary issues
2. **Avoid loops**: Prevent infinite retry loops
3. **User feedback**: Quick feedback if there's a real problem
4. **Resource efficient**: Don't waste time on persistent blocks

### When to Update Cookies?

If you see this error repeatedly:
```
❌ Still blocked after 3 attempts
   💡 Possible causes:
      - Cookies expired or invalid
```

**Solution**:
1. Open browser and login to Tokopedia Affiliate Center
2. Export new cookies using browser extension
3. Save to `config/cookies.json`
4. Run scraper again

---

## ✅ Status

**Implementation**: ✅ COMPLETE

**Testing**: ⏳ PENDING (needs manual testing with expired cookies)

**Integration**: ✅ COMPLETE (integrated in both list page and detail page)

**Documentation**: ✅ COMPLETE (this file)

---

## 🚀 Next Steps

1. Test with expired cookies to verify detection works
2. Test with valid cookies to ensure no false positives
3. Monitor logs during scraping to see if auto-refresh is triggered
4. Adjust max_retries or delay if needed based on real-world usage

---

**Happy Scraping! 🎉**
