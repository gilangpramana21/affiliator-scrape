# Tokopedia Affiliate Scraper

Web scraper untuk mengambil data affiliator dari Tokopedia Affiliate Center menggunakan **Manual Browser + HTTP Requests** approach untuk 100% reliability.

## 🎯 Why Manual Cookies?

**SEMUA browser automation (Playwright, Selenium, Undetected ChromeDriver) GAGAL** karena Tokopedia memiliki anti-bot detection yang sangat kuat:
- ❌ Browser automation langsung terdeteksi dan di-block
- ❌ Muncul halaman "Coba lagi" yang mencegah scraping
- ❌ Interaksi dengan elemen gagal

**Solusi: Manual Browser + HTTP Requests**
- ✅ User login manual di Chrome asli (tidak terdeteksi)
- ✅ Copy cookies dari DevTools
- ✅ Script menggunakan cookies untuk HTTP requests
- ✅ 100% reliability, no detection!

## Features

- ✅ **Manual Cookie Extraction**: Interactive guide untuk extract cookies dari Chrome
- ✅ **Cookie Validation**: Automatic validation untuk format dan expiration
- ✅ **Smart Rate Limiting**: Random delays dengan jitter untuk menghindari detection
- ✅ **Proxy Rotation**: Support HTTP/HTTPS/SOCKS5 dengan multiple rotation strategies
- ✅ **Contact Extraction**: Extract WhatsApp dan Email dari detail pages
- ✅ **Data Validation**: Comprehensive validation untuk data quality
- ✅ **Checkpoint & Resume**: Graceful interruption handling
- ✅ **Multiple Output Formats**: JSON dan CSV

## Installation

### Prerequisites

- Python 3.10 atau lebih tinggi
- pip (Python package manager)
- Google Chrome browser (untuk extract cookies)
- Akun Tokopedia dengan akses ke Affiliate Center

### Setup

1. Clone repository:
```bash
git clone <repository-url>
cd tokopedia-affiliate-scraper
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy configuration template:
```bash
cp config/config.template.json config/config.json
```

5. Edit `config/config.json` sesuai kebutuhan

## 🍪 Cookie Extraction Guide

### Why Manual Cookie Extraction?

Tokopedia's anti-bot system detects ALL browser automation tools. The only reliable way to scrape is:
1. Login manually in real Chrome browser
2. Extract cookies from DevTools
3. Use cookies with HTTP requests (no browser automation)

### Step-by-Step Cookie Extraction

#### Step 1: Open Chrome and Login

1. **Open Google Chrome** (the real browser, NOT automated!)
   - ⚠️ IMPORTANT: Do NOT use browsers opened by automation scripts

2. **Navigate to Tokopedia Affiliate Center**:
   ```
   https://affiliate-id.tokopedia.com/connection/creator
   ```

3. **Login with your Tokopedia account**:
   - Enter your email/phone and password
   - Complete CAPTCHA if prompted
   - Ensure you successfully reach the affiliator list page

#### Step 2: Open Chrome DevTools

**Method 1: Keyboard Shortcut**
- Windows/Linux: Press `F12`
- Mac: Press `Cmd + Option + I`

**Method 2: Right-click Menu**
- Right-click anywhere on the page
- Select "Inspect" or "Inspect Element"

![DevTools Opening](docs/images/devtools-open.png)

#### Step 3: Navigate to Application Tab

1. In DevTools, click the **"Application"** tab at the top
   - If you don't see it, click the `>>` icon to show hidden tabs

2. In the left sidebar, expand **"Cookies"**

3. Click on **`https://affiliate-id.tokopedia.com`**

![Application Tab](docs/images/devtools-application-tab.png)

#### Step 4: View and Copy Cookies

You'll see a table with all cookies. Important cookies include:
- `_SID_Tokopedia_` - Session ID (most important!)
- `DID` - Device ID
- `_UUID_CAS_` - User UUID
- And others...

![Cookies View](docs/images/devtools-cookies-view.png)

#### Step 5: Export Cookies

**Option A: Using Browser Extension (RECOMMENDED)**

1. Install a cookie extension:
   - Chrome: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/)
   - Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

2. Click the extension icon

3. Click "Export" button

4. Copy the JSON output

**Option B: Manual Copy (Advanced)**

For each cookie, manually create JSON entries with these fields:
- `name`: Cookie name
- `value`: Cookie value
- `domain`: Cookie domain (usually `.tokopedia.com`)
- `path`: Cookie path (usually `/`)
- `httpOnly`: Boolean (check the HttpOnly column)
- `secure`: Boolean (check the Secure column)

#### Step 6: Save to cookies.json

1. Create/open file: `config/cookies.json`

2. Paste the cookies in this format:

```json
[
  {
    "name": "_SID_Tokopedia_",
    "value": "YOUR_ACTUAL_SESSION_ID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": true,
    "secure": true
  },
  {
    "name": "DID",
    "value": "YOUR_ACTUAL_DEVICE_ID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": false,
    "secure": true
  },
  {
    "name": "_UUID_CAS_",
    "value": "YOUR_ACTUAL_UUID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": false,
    "secure": true
  }
]
```

⚠️ **IMPORTANT**: Replace the `value` fields with your ACTUAL cookie values from Chrome!

#### Step 7: Validate Cookies

Run the validation script to ensure cookies are correct:

```bash
python -m src.core.cookie_extraction_guide
```

Or use the validator:

```bash
python validate_cookies.py
```

Expected output:
```
✅ Format cookies valid! Total: X cookies
✅ Cookies belum expired
✅ COOKIES VALID DAN SIAP DIGUNAKAN!
```

### Cookie Extraction Helper Script

For an interactive guide, run:

```bash
python extract_cookies.py
```

This will display step-by-step instructions in your terminal.

### Troubleshooting Cookie Extraction

#### Problem: "Cookies tidak valid"

**Symptoms:**
- Validation script fails
- Error: "Cookie tidak punya field 'name'"

**Solutions:**
1. Check JSON format - must be an array `[...]`
2. Ensure each cookie has `name`, `value`, and `domain` fields
3. Check for syntax errors (missing commas, brackets)
4. Use a JSON validator: https://jsonlint.com/

#### Problem: "Domain bukan Tokopedia"

**Symptoms:**
- Warning: "Cookie domain bukan Tokopedia"

**Solutions:**
1. Only copy cookies from `https://affiliate-id.tokopedia.com`
2. Ensure domain is `.tokopedia.com` or `affiliate-id.tokopedia.com`
3. Don't copy cookies from other websites

#### Problem: "Cookies sudah expired"

**Symptoms:**
- Warning: "X cookies sudah expired"
- Scraper returns "Coba lagi" page

**Solutions:**
1. Extract fresh cookies from Chrome
2. Make sure you're logged in when extracting
3. Cookies typically expire after 7-14 days
4. Re-extract cookies regularly

#### Problem: Can't find Application tab in DevTools

**Solutions:**
1. Look for `>>` icon in DevTools tabs - click it to show hidden tabs
2. Try resizing DevTools window (make it wider)
3. Use keyboard shortcut: `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows), type "Application", press Enter

#### Problem: Extension not exporting cookies

**Solutions:**
1. Make sure you're on the correct page (`affiliate-id.tokopedia.com`)
2. Try a different extension (EditThisCookie vs Cookie-Editor)
3. Refresh the page and try again
4. Use manual copy method instead

#### Problem: "File tidak ditemukan: config/cookies.json"

**Solutions:**
1. Create the `config` directory if it doesn't exist:
   ```bash
   mkdir -p config
   ```
2. Save cookies to the correct path: `config/cookies.json`
3. Check you're in the project root directory

### Cookie Security Notes

⚠️ **IMPORTANT SECURITY WARNINGS:**

1. **Never share your cookies** - they contain your session credentials
2. **Don't commit cookies to Git** - add `config/cookies.json` to `.gitignore`
3. **Cookies expire** - typically after 7-14 days, you'll need to re-extract
4. **Logout invalidates cookies** - if you logout from Tokopedia, cookies become invalid
5. **One device at a time** - using cookies on multiple devices may trigger security alerts

### Cookie Lifespan

- **Typical lifespan**: 7-14 days
- **Signs of expiration**:
  - Scraper redirects to login page
  - "Coba lagi" blocking page appears
  - HTTP 401/403 errors
- **Refresh frequency**: Extract new cookies every week for best results

## Configuration

Edit `config/config.json` untuk mengkonfigurasi scraper:

### Cookie Settings (REQUIRED)
```json
{
  "cookie_file": "config/cookies.json",
  "require_cookie_file": true
}
```

### Basic Settings
- `base_url`: Base URL Tokopedia Affiliate Center
- `list_page_url`: Path ke halaman list kreator

### Rate Limiting
- `min_delay`: Minimum delay antar request (detik) - default: 2.0
- `max_delay`: Maximum delay antar request (detik) - default: 5.0
- `jitter`: Random jitter percentage (0-1) - default: 0.2

### Traffic Control
- `hourly_limit`: Maximum requests per jam - default: 50
- `daily_limit`: Maximum requests per hari - default: 500
- `quiet_hours`: Jam-jam dimana scraping tidak dilakukan

### Proxy Settings (Optional)
```json
"proxies": [
  {
    "protocol": "http",
    "host": "proxy.example.com",
    "port": 8080,
    "username": "user",
    "password": "pass"
  }
],
"proxy_rotation_strategy": "per_session"
```

### Output Settings
- `output_format`: "json" atau "csv"
- `output_path`: Path untuk output file
- `incremental_save`: Enable incremental saving
- `save_interval`: Save setiap N affiliators

## Usage

### Step 1: Extract and Validate Cookies

```bash
# Show interactive cookie extraction guide
python extract_cookies.py

# Validate cookies after extraction
python validate_cookies.py
```

### Step 2: Run Scraper

**Basic Usage:**

```bash
python main.py
```

**With Custom Config:**

```bash
python main.py --config config/custom_config.json
```

**Scrape Specific Number of Pages:**

```bash
python scrape_affiliators.py --max-pages 5
```

**Resume from Checkpoint:**

```bash
python main.py --resume checkpoint.json
```

### What Gets Scraped

✅ **Affiliator Data:**
- Username
- Kategori (category)
- Jumlah pengikut (followers)
- GMV (Gross Merchandise Value)
- Produk terjual (products sold)
- Rata-rata tayangan (average views)
- Tingkat interaksi (engagement rate)

✅ **Contact Information:**
- **WhatsApp** number (format: +62xxx or 08xxx)
- **Email** address

### Output Format

Results are saved to `output/affiliators.json`:

```json
[
  {
    "username": "creator123",
    "kategori": "Fashion",
    "pengikut": 50000,
    "gmv": 15000000,
    "produk_terjual": 1250,
    "rata_rata_tayangan": 25000,
    "tingkat_interaksi": 4.5,
    "nomor_kontak": "+628123456789",
    "email": "creator@example.com",
    "detail_url": "https://affiliate-id.tokopedia.com/creator/creator123",
    "scraped_at": "2026-04-27T10:30:00"
  }
]
```

## Project Structure

```
tokopedia-affiliate-scraper/
├── src/
│   ├── core/              # Core scraping components
│   │   ├── http_client.py           # HTTP client with cookies
│   │   ├── html_parser.py           # HTML parsing
│   │   ├── affiliator_extractor.py  # Data extraction
│   │   ├── contact_extractor.py     # WhatsApp/Email extraction
│   │   ├── cookie_extraction_guide.py # Cookie guide
│   │   └── cookie_validator.py      # Cookie validation
│   ├── models/            # Data models
│   │   ├── affiliator_data.py       # Affiliator data model
│   │   ├── configuration.py         # Configuration model
│   │   └── proxy_config.py          # Proxy configuration
│   ├── control/           # Rate limiting & traffic control
│   │   ├── rate_limiter.py          # Request rate limiting
│   │   ├── traffic_controller.py    # Traffic management
│   │   └── proxy_rotator.py         # Proxy rotation
│   └── utils/             # Utility functions
│       ├── data_store.py            # Data persistence
│       ├── data_validator.py        # Data validation
│       └── error_analyzer.py        # Error analysis
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── property/          # Property-based tests
│   └── fixtures/          # Test fixtures
├── config/                # Configuration files
│   ├── config.json              # Main configuration
│   ├── cookies.json             # Extracted cookies (DO NOT COMMIT!)
│   ├── selectors.json           # CSS/XPath selectors
│   └── config.template.json     # Configuration template
├── logs/                  # Log files
├── output/                # Output data files
├── docs/                  # Documentation
│   └── images/            # Screenshots for guides
├── requirements.txt       # Python dependencies
├── extract_cookies.py     # Cookie extraction helper
├── validate_cookies.py    # Cookie validation script
├── scrape_affiliators.py  # Main scraper script
└── README.md             # This file
```

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     MANUAL PHASE (User)                      │
│  1. User opens Chrome                                        │
│  2. User logs in to Tokopedia                               │
│  3. User extracts cookies from DevTools                     │
│  4. User saves to config/cookies.json                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  AUTOMATED PHASE (Script)                    │
│                                                              │
│  ┌──────────────┐                                           │
│  │ Load Cookies │ → Validate → Test with HTTP Request       │
│  └──────────────┘                                           │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  HTTP Client (requests library)                       │  │
│  │  - Uses cookies for authentication                    │  │
│  │  - No browser automation                              │  │
│  │  - Simple HTTP GET/POST requests                      │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Scraping Loop                                        │  │
│  │  1. GET list page → Parse HTML → Extract affiliators │  │
│  │  2. For each affiliator:                             │  │
│  │     - GET detail page → Parse HTML                   │  │
│  │     - Extract contact (WhatsApp, Email)              │  │
│  │     - Validate data                                   │  │
│  │     - Save to output                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Rate Limiting & Traffic Control                      │  │
│  │  - Random delays (2-5 seconds)                        │  │
│  │  - Hourly/daily limits                                │  │
│  │  - Proxy rotation (optional)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Output                                               │  │
│  │  - JSON: output/affiliators.json                      │  │
│  │  - CSV: output/affiliators.csv                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Cookie Extraction Guide** (`src/core/cookie_extraction_guide.py`)
   - Interactive CLI guide for users
   - Step-by-step instructions
   - Format validation

2. **Cookie Validator** (`src/core/cookie_validator.py`)
   - Validates JSON format
   - Checks expiration
   - Tests cookies with HTTP request

3. **HTTP Client** (`src/core/http_client.py`)
   - Uses Python `requests` library
   - Loads cookies from file
   - Handles retries and timeouts
   - No browser automation!

4. **HTML Parser** (`src/core/html_parser.py`)
   - Parses HTML with lxml/BeautifulSoup
   - CSS selector and XPath support
   - Handles malformed HTML

5. **Affiliator Extractor** (`src/core/affiliator_extractor.py`)
   - Extracts data from list pages
   - Extracts data from detail pages
   - Multiple fallback selectors

6. **Contact Extractor** (`src/core/contact_extractor.py`)
   - Extracts WhatsApp numbers
   - Extracts email addresses
   - Validates phone number formats

7. **Rate Limiter** (`src/control/rate_limiter.py`)
   - Random delays with jitter
   - Prevents detection
   - Adjustable based on errors

8. **Traffic Controller** (`src/control/traffic_controller.py`)
   - Hourly/daily request limits
   - Quiet hours enforcement
   - Session break management

## Why This Approach Works

### ✅ Advantages

1. **100% Reliability**
   - No browser automation detection
   - Real browser cookies bypass all anti-bot measures
   - Works consistently

2. **Simplicity**
   - No complex browser automation setup
   - No Playwright/Selenium dependencies
   - Just HTTP requests with cookies

3. **Performance**
   - Faster than browser automation
   - Lower memory usage (<500 MB)
   - No browser overhead

4. **Maintainability**
   - Simple codebase
   - Easy to debug
   - No brittle automation scripts

### ⚠️ Limitations

1. **Manual Cookie Extraction**
   - User must extract cookies manually
   - Cookies expire after 7-14 days
   - Requires re-extraction periodically

2. **No JavaScript Execution**
   - Can't handle dynamic content that requires JS
   - (But Tokopedia serves fully-rendered HTML, so this is OK)

3. **Session Management**
   - One session per cookie set
   - Can't run multiple sessions simultaneously with same cookies

## Testing

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
```

### Run Property-Based Tests
```bash
pytest tests/property/ -v
```

### Test Cookie Extraction
```bash
# Show guide
python extract_cookies.py

# Validate cookies
python validate_cookies.py

# Test with single page
python scrape_affiliators.py --max-pages 1
```

## Deployment

### Single Machine Deployment

1. **Setup environment**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Extract cookies**:
```bash
python extract_cookies.py
# Follow guide to extract cookies from Chrome
```

3. **Configure**:
```bash
cp config/config.template.json config/config.json
# Edit config.json as needed
```

4. **Run scraper**:
```bash
python main.py
```

### Docker Deployment

```bash
# Build image
docker build -t tokopedia-scraper .

# Run container (mount cookies from host)
docker run -v $(pwd)/config:/app/config \
           -v $(pwd)/output:/app/output \
           tokopedia-scraper
```

**Note**: You still need to extract cookies on your host machine and mount them into the container.

### Scheduled Scraping (Cron)

```bash
# Edit crontab
crontab -e

# Add entry (run daily at 2 AM)
0 2 * * * cd /path/to/scraper && /path/to/venv/bin/python main.py

# Remember to refresh cookies weekly!
```

## Best Practices

### Cookie Management

1. **Extract fresh cookies weekly**
   - Set a reminder to refresh cookies every 7 days
   - Don't wait for cookies to expire

2. **Keep cookies secure**
   - Add `config/cookies.json` to `.gitignore`
   - Don't share cookies with others
   - Use file permissions: `chmod 600 config/cookies.json`

3. **Validate before scraping**
   ```bash
   python validate_cookies.py && python main.py
   ```

### Rate Limiting

1. **Start conservative**
   - Use default delays (2-5 seconds)
   - Monitor for blocking

2. **Adjust based on results**
   - If blocked: increase delays
   - If stable: can slightly decrease delays

3. **Respect limits**
   - Don't scrape 24/7
   - Use quiet hours
   - Take breaks

### Data Quality

1. **Validate output regularly**
   ```bash
   python -c "import json; data = json.load(open('output/affiliators.json')); print(f'Total: {len(data)}, With contact: {sum(1 for d in data if d.get(\"nomor_kontak\"))}')"
   ```

2. **Check for duplicates**
   - Scraper handles deduplication automatically
   - But verify output if needed

3. **Monitor success rate**
   - Check logs for extraction failures
   - Update selectors if Tokopedia changes HTML

### Troubleshooting Workflow

```bash
# 1. Validate cookies
python validate_cookies.py

# 2. If cookies invalid, re-extract
python extract_cookies.py

# 3. Test with single page
python scrape_affiliators.py --max-pages 1

# 4. Check logs
tail -f logs/scraper.log

# 5. If successful, run full scrape
python main.py
```

## Distributed Mode

⚠️ **Note**: Distributed mode is not implemented in the current version. It can be added later if needed.

For now, to scale:
1. Run multiple instances with different cookie sets
2. Partition affiliator list manually
3. Merge results afterward

## Troubleshooting

### Cookie-Related Issues

#### 1. "Cookies tidak valid" or "Cookie file not found"

**Symptoms:**
- Error when starting scraper
- Validation fails

**Solutions:**
```bash
# 1. Check if cookie file exists
ls -la config/cookies.json

# 2. Validate cookie format
python validate_cookies.py

# 3. Re-extract cookies from Chrome
python extract_cookies.py
# Follow the guide and extract fresh cookies
```

#### 2. "Coba lagi" Blocking Page

**Symptoms:**
- Scraper detects "Coba lagi" page
- No data extracted
- HTTP responses show blocking message

**Solutions:**
1. **Cookies expired** - Extract fresh cookies:
   ```bash
   python extract_cookies.py
   ```
2. **IP blocked** - Wait a few hours or use proxy
3. **Rate limit hit** - Increase delays in config:
   ```json
   {
     "min_delay": 5.0,
     "max_delay": 10.0
   }
   ```

#### 3. Cookies Expired After Few Days

**Symptoms:**
- Scraper worked before, now fails
- Redirect to login page
- Session expired errors

**Solutions:**
1. **Normal behavior** - Tokopedia cookies expire after 7-14 days
2. **Re-extract cookies**:
   ```bash
   # 1. Login to Tokopedia in Chrome
   # 2. Extract fresh cookies
   python extract_cookies.py
   # 3. Validate
   python validate_cookies.py
   # 4. Resume scraping
   python main.py
   ```

#### 4. Low Success Rate (<80%)

**Symptoms:**
- Many affiliators have null/missing data
- Contact extraction fails frequently

**Solutions:**
1. **Update cookies** - Always try this first
2. **Check selectors** - Tokopedia may have changed HTML:
   ```bash
   # Inspect HTML manually
   # Update selectors in config/selectors.json
   ```
3. **Slow down** - Reduce scraping speed:
   ```json
   {
     "min_delay": 3.0,
     "max_delay": 7.0,
     "hourly_limit": 30
   }
   ```

#### 5. No Contact Information Extracted

**Symptoms:**
- `nomor_kontak` is always null
- `email` is always null

**Solutions:**
1. **This is normal** - Not all creators share contact info (40-60% share rate)
2. **Check detail pages manually** - Verify contact info exists on Tokopedia
3. **Update selectors** - If Tokopedia changed HTML structure:
   ```python
   # Edit src/core/contact_extractor.py
   # Update CSS selectors for WhatsApp and Email
   ```

#### 6. Scraper Kena Block / Rate Limited

**Symptoms:**
- Multiple 403 Forbidden errors
- 429 Too Many Requests
- Scraper pauses frequently

**Solutions:**
1. **Increase delays**:
   ```json
   {
     "min_delay": 5.0,
     "max_delay": 10.0,
     "jitter": 0.3
   }
   ```
2. **Reduce limits**:
   ```json
   {
     "hourly_limit": 30,
     "daily_limit": 300
   }
   ```
3. **Enable proxy rotation**:
   ```json
   {
     "proxies": [...],
     "proxy_rotation_strategy": "per_request"
   }
   ```
4. **Add quiet hours**:
   ```json
   {
     "quiet_hours": [[1, 6], [13, 14]]
   }
   ```

#### 7. Memory Usage Tinggi

**Symptoms:**
- Scraper uses >500 MB RAM
- System becomes slow

**Solutions:**
1. **Enable incremental save**:
   ```json
   {
     "incremental_save": true,
     "save_interval": 10
   }
   ```
2. **Reduce batch size** - Scrape fewer pages per run
3. **Restart periodically** - Use checkpoints to resume

#### 8. JSON Decode Error

**Symptoms:**
- Error: "Expecting value: line 1 column 1"
- Cookie validation fails

**Solutions:**
1. **Check JSON syntax**:
   ```bash
   # Validate JSON online
   # https://jsonlint.com/
   ```
2. **Common mistakes**:
   - Missing commas between objects
   - Missing brackets `[` or `]`
   - Unescaped quotes in values
   - Trailing commas (not allowed in JSON)

3. **Use cookie extension** - Easier than manual copy:
   - Install EditThisCookie (Chrome)
   - Export cookies directly to JSON

### General Issues

#### Scraper Stops Unexpectedly

**Solutions:**
1. **Check logs** - Look in `logs/scraper.log`
2. **Resume from checkpoint**:
   ```bash
   python main.py --resume checkpoint.json
   ```
3. **Enable SIGINT handler** - Saves partial results on Ctrl+C

#### Wrong Data Extracted

**Solutions:**
1. **Inspect HTML** - Check if Tokopedia changed structure
2. **Update selectors** - Edit `config/selectors.json`
3. **Check logs** - Look for parsing errors
4. **Test with single page**:
   ```bash
   python scrape_affiliators.py --max-pages 1
   ```

### Getting Help

If issues persist:

1. **Check logs**: `logs/scraper.log`
2. **Validate cookies**: `python validate_cookies.py`
3. **Test with minimal config**: Use default settings
4. **Inspect HTML manually**: Check if Tokopedia changed structure
5. **Open GitHub issue**: Include logs and error messages

### Quick Diagnostic Commands

```bash
# 1. Validate cookies
python validate_cookies.py

# 2. Test single page scrape
python scrape_affiliators.py --max-pages 1

# 3. Check configuration
python -c "from src.models.configuration import Configuration; c = Configuration.from_file('config/config.json'); print(c.validate())"

# 4. View recent logs
tail -n 50 logs/scraper.log

# 5. Check output
cat output/affiliators.json | python -m json.tool
```

## Performance Targets

- ✅ Scrape 100 affiliators dalam < 30 menit
- ✅ Success rate > 95% (with valid cookies)
- ✅ Memory usage < 500 MB
- ✅ Contact extraction rate: 40-60% (depends on creators sharing contact)
- ✅ No browser automation overhead

## FAQ

### Q: Why manual cookie extraction instead of automation?

**A:** Tokopedia's anti-bot system detects ALL browser automation tools (Playwright, Selenium, Undetected ChromeDriver). The only reliable way is to use real browser cookies with HTTP requests.

### Q: How often do I need to refresh cookies?

**A:** Tokopedia cookies typically expire after 7-14 days. Set a weekly reminder to extract fresh cookies.

### Q: Can I run multiple scrapers simultaneously?

**A:** Not with the same cookies. Each cookie set represents one session. You can run multiple instances with different cookie sets (different Tokopedia accounts).

### Q: Why is contact extraction rate only 40-60%?

**A:** Not all creators share their contact information publicly on Tokopedia. This is normal and expected.

### Q: What if Tokopedia changes their HTML structure?

**A:** You'll need to update the CSS selectors in `config/selectors.json` or in the extractor code. Check logs for parsing errors.

### Q: Is this legal?

**A:** Web scraping legality varies by jurisdiction and use case. Review Tokopedia's Terms of Service and consult legal counsel if needed. This tool is for educational purposes.

### Q: Can I use a proxy?

**A:** Yes! Configure proxies in `config/config.json`. Proxies can help avoid IP-based rate limiting.

### Q: What happens if scraper is interrupted?

**A:** The scraper saves checkpoints periodically. You can resume from the last checkpoint using `--resume checkpoint.json`.

### Q: How do I convert JSON output to CSV/Excel?

**A:** Set `output_format: "csv"` in config, or use a JSON-to-CSV converter tool.

### Q: Can I scrape specific affiliators only?

**A:** Currently, the scraper processes all affiliators sequentially. You can modify the code to filter by criteria (category, followers, etc.).

## Legal & Ethical Considerations

⚠️ **IMPORTANT**: Web scraping may violate Terms of Service. Users must:
- Review Tokopedia's Terms of Service
- Ensure compliance with local laws (Indonesia)
- Obtain necessary permissions if required
- Use for legitimate purposes only
- Protect scraped personal data

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
