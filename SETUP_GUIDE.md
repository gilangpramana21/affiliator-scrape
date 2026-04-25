# Setup Guide - Production Scraper

## 🎯 Tujuan
Scraping 1000+ affiliators per hari dengan success rate 95%+ untuk data metrics (GMV, GMP, dll) dan 40-60% untuk contact data (WhatsApp, Email).

## 📋 Prerequisites

### 1. Update Cookies (WAJIB!)

Cookies Anda mungkin sudah expired. Ikuti langkah ini:

1. **Install Cookie Extension**
   - Chrome: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)
   - Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

2. **Login ke Tokopedia Affiliate**
   - Buka: https://affiliate.tokopedia.com
   - Login dengan akun Anda
   - Pastikan berhasil masuk ke dashboard

3. **Export Cookies**
   - Klik icon extension di browser
   - Klik "Export" atau "Export All"
   - Copy JSON yang muncul

4. **Save ke File**
   - Buka file: `config/cookies.json`
   - Paste JSON cookies
   - Save file

### 2. Setup Bright Data Proxy (Untuk Public WiFi)

**PENTING**: Jika menggunakan public WiFi, proxy WAJIB untuk mengurangi CAPTCHA rate dari 70-90% menjadi 20-30%.

#### Langkah Setup:

1. **Login ke Bright Data**
   - Buka: https://brightdata.com
   - Login dengan akun Anda

2. **Create Proxy Zone**
   - Dashboard → Proxies & Scraping Infrastructure → Add Zone
   - Pilih: **Residential Proxies**
   - Zone name: `tokopedia-scraper`
   - Country: **Indonesia** (PENTING!)
   - Port: `22225` (atau custom)
   - Klik "Add"

3. **Get Credentials**
   - Klik zone yang baru dibuat
   - Lihat di "Access Parameters"
   - Copy:
     - Host: `brd.superproxy.io`
     - Port: `22225`
     - Username: `brd-customer-hl_xxxxx-zone-xxxxx`
     - Password: `xxxxxxxxxx`

4. **Test Proxy**
   ```bash
   curl --proxy brd.superproxy.io:22225 \
        --proxy-user USERNAME-country-id:PASSWORD \
        "https://geo.brdtest.com/welcome.txt?product=resi"
   ```
   
   Expected output: IP dari Indonesia

5. **Update Config**
   - Buka: `config/config_production.json`
   - Update:
   ```json
   {
     "proxy_enabled": true,
     "proxy_server": "http://brd.superproxy.io:22225",
     "proxy_username": "brd-customer-hl_xxxxx-zone-xxxxx-country-id",
     "proxy_password": "your_password_here"
   }
   ```

**CATATAN**: Jika masih ada error "Internal server error" di Bright Data:
- Refresh page dan coba lagi
- Tunggu beberapa menit
- Contact Bright Data support
- Alternatif: Gunakan provider lain (Smartproxy, Oxylabs)

### 3. Setup CapSolver (Optional tapi Recommended)

CapSolver akan solve CAPTCHA otomatis.

1. **Register CapSolver**
   - Buka: https://www.capsolver.com
   - Register akun baru
   - Top up balance ($5-10 cukup untuk testing)

2. **Get API Key**
   - Dashboard → API Key
   - Copy API key

3. **Update Config**
   - Buka: `config/config_production.json`
   - Update:
   ```json
   {
     "captcha_solver": "capsolver",
     "captcha_api_key": "CAP-xxxxxxxxxxxxx"
   }
   ```

## 🚀 Running the Scraper

### Test Mode (10 Affiliators)

Test dulu dengan 10 affiliators untuk memastikan setup benar:

```bash
python3 test_original_scraper.py
```

**Expected Output:**
```
🧪 TESTING ORIGINAL SCRAPER
============================================================
Target: 10 affiliators
============================================================
🚀 Starting scraper...
...
✅ TEST COMPLETED
============================================================
Total scraped: 10
Unique affiliators: 9-10
Errors: 0-1
CAPTCHAs encountered: 0-2
💾 Output saved to: output/affiliators_jelajahi.xlsx
```

**Success Criteria:**
- ✅ Success rate > 80%
- ✅ CAPTCHA rate < 30%
- ✅ Data extracted correctly (GMV, GMP, WhatsApp, Email)

### Production Mode (1000+ Affiliators)

Setelah test berhasil, jalankan production mode:

```bash
python3 production_scraper_enhanced.py --max-affiliators 1000
```

**Options:**
- `--config`: Path to config file (default: `config/config_production.json`)
- `--max-affiliators`: Maximum affiliators to scrape (default: 1000)

**Example:**
```bash
# Scrape 500 affiliators
python3 production_scraper_enhanced.py --max-affiliators 500

# Use custom config
python3 production_scraper_enhanced.py --config config/my_config.json
```

## 📊 Expected Results

### Success Metrics:
- **Metrics data (GMV, GMP, dll)**: 95%+ success rate
- **Contact data (WhatsApp, Email)**: 40-60% success rate
- **CAPTCHA rate**: 
  - With proxy: 20-30%
  - Without proxy (public WiFi): 70-90%
- **Speed**: ~30 seconds per affiliator = ~8 hours for 1000 affiliators

### Output Format:

File: `output/affiliators_production_YYYYMMDD_HHMMSS.xlsx`

Columns:
- Username
- Kategori
- Pengikut
- GMV
- GMP (Gross Merchandise Profit)
- Produk Terjual
- Rata-rata Tayangan
- Tingkat Interaksi
- GMV Per Pembeli
- WhatsApp (jika ada)
- Email (jika ada)
- Scraped At

## 🔧 Troubleshooting

### Problem: Low Success Rate (<80%)

**Possible Causes:**
1. Cookies expired
2. IP blocked
3. CAPTCHA not solved

**Solutions:**
1. Update cookies (lihat Prerequisites #1)
2. Enable proxy (lihat Prerequisites #2)
3. Enable CapSolver (lihat Prerequisites #3)

### Problem: High CAPTCHA Rate (>50%)

**Possible Causes:**
1. Using public WiFi without proxy
2. IP flagged as suspicious

**Solutions:**
1. **WAJIB**: Enable Bright Data proxy with Indonesia location
2. Enable CapSolver for automatic solving
3. Reduce scraping speed (increase delays in config)

### Problem: Wrong Data Extracted

**Possible Causes:**
1. Tokopedia changed HTML structure
2. Parser not updated

**Solutions:**
1. Check logs for parsing errors
2. Update selectors in `config/selectors.json`
3. Contact developer for parser update

### Problem: Bright Data "Internal Server Error"

**Possible Causes:**
1. Bright Data server issue
2. Account not verified
3. Payment issue

**Solutions:**
1. Refresh page and try again
2. Wait 5-10 minutes and retry
3. Contact Bright Data support
4. Use alternative proxy provider

## 💰 Cost Estimation

### Bright Data Proxy:
- Residential proxy: $8.40/GB
- Estimated usage: 1000 affiliators = ~500MB = $4.20
- Monthly (30 days): ~$126

### CapSolver:
- reCAPTCHA v2: $0.80/1000 solves
- Estimated: 300 CAPTCHAs/day = $0.24/day
- Monthly (30 days): ~$7.20

### Total Monthly Cost: ~$133

**Budget Optimization:**
- Use proxy only during public WiFi usage
- Use home WiFi when possible (reduces CAPTCHA rate)
- Monitor usage and adjust

## 📅 Daily Scraping Schedule

Recommended schedule untuk scraping harian:

```bash
# Crontab example (run at 2 AM daily)
0 2 * * * cd /path/to/scraper && python3 production_scraper_enhanced.py --max-affiliators 1000
```

## 🆘 Support

Jika ada masalah:
1. Check logs di `logs/scraper_production.log`
2. Review troubleshooting section
3. Contact developer dengan error details
