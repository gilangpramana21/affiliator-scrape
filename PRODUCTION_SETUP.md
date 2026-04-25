# 🚀 Production Scraper V2 - Setup Guide

## ✅ Requirements Confirmed
- Budget: $10-20
- Frequency: Daily scraping
- Target: 1000+ affiliators
- Success rate target: 95%+

---

## 📋 Step 1: Bright Data Proxy Setup (REQUIRED)

### 1.1 Sign Up for Bright Data
1. Go to: https://brightdata.com/
2. Click "Start Free Trial"
3. Sign up with email
4. Get **$5 free credit** (no credit card required)

### 1.2 Create Residential Proxy
1. Login to dashboard
2. Go to "Proxies & Scraping Infrastructure"
3. Click "Add" → "Residential Proxies"
4. Select:
   - **Country**: Indonesia (for best results)
   - **Type**: Rotating
5. Click "Create"

### 1.3 Get Credentials
1. Click on your proxy zone
2. Copy:
   - **Host**: `brd.superproxy.io`
   - **Port**: `22225`
   - **Username**: `brd-customer-xxxxx-zone-xxxxx`
   - **Password**: `xxxxx`

### 1.4 Update Config
Edit `config/config_production.json`:
```json
{
  "proxy_enabled": true,
  "proxy_server": "http://brd.superproxy.io:22225",
  "proxy_username": "YOUR_USERNAME_HERE",
  "proxy_password": "YOUR_PASSWORD_HERE"
}
```

**Cost**: $5 free credit = ~300-500 requests = enough for testing!

---

## 🤖 Step 2: CapSolver Setup (REQUIRED)

### 2.1 Sign Up for CapSolver
1. Go to: https://www.capsolver.com/
2. Click "Sign Up"
3. Verify email
4. Get **$1 free credit**

### 2.2 Get API Key
1. Login to dashboard
2. Go to "API Key" section
3. Copy your API key

### 2.3 Update Config
Edit `config/config_production.json`:
```json
{
  "captcha_solver": "capsolver",
  "captcha_api_key": "YOUR_CAPSOLVER_API_KEY_HERE"
}
```

**Cost**: $1 free credit = ~1000 CAPTCHAs = enough for testing!

---

## 🧪 Step 3: Test Run (IMPORTANT!)

### 3.1 Test with 10 Affiliators
```bash
python3 production_scraper_v2.py
```

Edit `production_scraper_v2.py` line 45:
```python
# Change from:
results = await scraper.scrape_affiliators(max_affiliators=1000)

# To:
results = await scraper.scrape_affiliators(max_affiliators=10)
```

### 3.2 Monitor Results
Check:
- ✅ Metrics success rate: Should be >90%
- ✅ CAPTCHA solve rate: Should be >85%
- ✅ Network extractions: Should be >0 (means API monitoring works)
- ✅ No errors or crashes

### 3.3 Validate Data
Check `production_results_XXXXXX.json`:
```json
{
  "scrape_info": {
    "total_results": 10,
    "statistics": {
      "metrics_success": 9,  // Should be 9-10
      "captcha_solved": 2    // Should be >80% of encountered
    }
  },
  "results": [...]
}
```

---

## 🚀 Step 4: Production Run (1000+ Affiliators)

### 4.1 Top Up Credits
**Bright Data**:
- Go to dashboard → Billing
- Add $15-20 (enough for 1000+ affiliators)

**CapSolver**:
- Go to dashboard → Recharge
- Add $5 (enough for 1000+ CAPTCHAs)

**Total cost**: ~$20-25

### 4.2 Update Config for Production
Edit `production_scraper_v2.py` line 45:
```python
results = await scraper.scrape_affiliators(max_affiliators=1000)
```

### 4.3 Run Production Scraper
```bash
python3 production_scraper_v2.py
```

**Expected time**: 2-3 hours for 1000 affiliators

### 4.4 Monitor Progress
The scraper will print progress every 10 affiliators:
```
📊 Progress: 10/1000 (1.0%)
   📊 Stats:
      Processed: 10
      Metrics success: 9 (90.0%)
      Contact success: 4 (40.0%)
      CAPTCHA: 3 encountered, 3 solved
```

---

## 📊 Expected Results for 1000 Affiliators

### Success Rates:
```
✅ Metrics data (GMV, GMP, etc): 950-980 (95-98%)
⚠️ Contact data (WhatsApp, Email): 400-600 (40-60%)
❌ Failed completely: 20-50 (2-5%)
```

### Cost Breakdown:
```
Bright Data Proxy: $15-20
CapSolver CAPTCHA: $0.20-0.50
Total: ~$15-20
```

### Time:
```
With proxy: 2-3 hours
Without proxy: 8-12 hours (not recommended)
```

---

## 🔧 Troubleshooting

### Problem: High CAPTCHA Rate (>50%)
**Solution**:
1. Check proxy is enabled and working
2. Increase delays in config:
   ```json
   "min_delay": 5,
   "max_delay": 8
   ```
3. Use Indonesia proxy location

### Problem: Low Success Rate (<80%)
**Solution**:
1. Check cookies are valid
2. Check proxy credentials
3. Check CapSolver API key
4. Run test with 10 affiliators first

### Problem: "Coba Lagi" Messages
**Solution**:
1. Enable proxy (this is IP reputation issue)
2. Increase delays
3. Use residential proxy (not datacenter)

### Problem: Network Extraction Not Working
**Solution**:
1. Check browser console for API calls
2. Update `_matches_creator()` function
3. Add more field mappings in `_parse_api_response()`

---

## 📅 Daily Scraping Setup

### Option 1: Manual Daily Run
```bash
# Run every day
python3 production_scraper_v2.py
```

### Option 2: Cron Job (Automated)
```bash
# Edit crontab
crontab -e

# Add this line (run daily at 2 AM)
0 2 * * * cd /path/to/project && /path/to/venv/bin/python3 production_scraper_v2.py
```

### Option 3: Python Scheduler
Create `daily_scheduler.py`:
```python
import schedule
import time
import asyncio
from production_scraper_v2 import ProductionScraperV2

def run_daily_scrape():
    scraper = ProductionScraperV2()
    asyncio.run(scraper.scrape_affiliators(max_affiliators=1000))

# Run every day at 2 AM
schedule.every().day.at("02:00").do(run_daily_scrape)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 💰 Cost Optimization Tips

### 1. Use Free Credits First
- Bright Data: $5 free
- CapSolver: $1 free
- Total free: $6 (enough for 200-300 affiliators)

### 2. Optimize Proxy Usage
- Only enable proxy when CAPTCHA rate >30%
- Use WiFi rumah when possible
- Rotate between proxy and no-proxy

### 3. Optimize CAPTCHA Solving
- Increase delays to reduce CAPTCHA rate
- Use good IP reputation (residential proxy)
- Skip affiliators with persistent CAPTCHAs

### 4. Batch Processing
- Process 100-200 affiliators per session
- Take breaks between sessions
- Spread across multiple days if needed

---

## ✅ Success Checklist

Before production run, ensure:
- [ ] Bright Data proxy configured and tested
- [ ] CapSolver API key configured and tested
- [ ] Cookies are valid and loaded
- [ ] Test run with 10 affiliators successful
- [ ] Success rate >90% in test run
- [ ] Credits topped up for production
- [ ] Monitoring setup (check progress every hour)

---

## 🆘 Support

If you encounter issues:
1. Check logs in console output
2. Check `production_results_*.json` for errors
3. Run test with 10 affiliators first
4. Check proxy and CAPTCHA solver status
5. Verify cookies are still valid

---

## 📈 Next Steps After First Run

1. **Analyze results**:
   - Check success rates
   - Identify patterns in failures
   - Optimize config based on results

2. **Improve extraction**:
   - Add more API field mappings
   - Improve network monitoring
   - Add fallback strategies

3. **Scale up**:
   - Increase to 2000+ affiliators
   - Setup automated daily runs
   - Add data validation and deduplication

---

**Ready to start?** Follow Step 1-3 for testing, then Step 4 for production! 🚀
