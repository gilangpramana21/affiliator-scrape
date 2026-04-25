# 🚀 Production Scraper V2 - Quick Start

## 📦 What You Need

1. **Bright Data Account** (Proxy)
   - Sign up: https://brightdata.com/
   - Free $5 credit
   - Cost: $15-20 for 1000 affiliators

2. **CapSolver Account** (CAPTCHA Solver)
   - Sign up: https://www.capsolver.com/
   - Free $1 credit
   - Cost: $0.20-0.50 for 1000 affiliators

**Total Cost**: ~$15-20 for 1000 affiliators

---

## ⚡ Quick Start (3 Steps)

### Step 1: Configure Proxy & CAPTCHA Solver
Edit `config/config_production.json`:
```json
{
  "proxy_enabled": true,
  "proxy_username": "YOUR_BRIGHTDATA_USERNAME",
  "proxy_password": "YOUR_BRIGHTDATA_PASSWORD",
  "captcha_api_key": "YOUR_CAPSOLVER_API_KEY"
}
```

### Step 2: Test with 10 Affiliators
```bash
python3 quick_test.py
```

Expected output:
```
✅ EXCELLENT! Ready for production run
Total processed: 10/10
Metrics success: 9/10 (90.0%)
Contact success: 4/10 (40.0%)
```

### Step 3: Run Production (1000+ Affiliators)
```bash
python3 production_scraper_v2.py
```

**Time**: 2-3 hours
**Success Rate**: 95%+ for metrics data

---

## 📊 What You Get

### Data Extracted:
- ✅ Username
- ✅ Kategori
- ✅ Pengikut
- ✅ GMV (Gross Merchandise Value)
- ✅ GMP
- ✅ GMV Per Pembeli
- ✅ Produk Terjual
- ✅ Rata-rata Tayangan
- ✅ Tingkat Interaksi
- ⚠️ WhatsApp (40-60% success)
- ⚠️ Email (40-60% success)

### Output Format:
```json
{
  "scrape_info": {
    "timestamp": "20260424_120000",
    "total_results": 1000,
    "statistics": {
      "metrics_success": 950,
      "contact_success": 450
    }
  },
  "results": [
    {
      "username": "creator123",
      "gmv": 1500000,
      "gmv_per_pembeli": 150000,
      "whatsapp": "081234567890",
      "email": "creator@email.com"
    }
  ]
}
```

---

## 🔧 Troubleshooting

### High CAPTCHA Rate (>50%)
→ Enable proxy in config

### Low Success Rate (<80%)
→ Check proxy credentials and CAPTCHA API key

### "Coba Lagi" Messages
→ This is IP reputation issue, proxy will fix it

---

## 📅 Daily Scraping

### Manual:
```bash
python3 production_scraper_v2.py
```

### Automated (Cron):
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python3 production_scraper_v2.py
```

---

## 💰 Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Bright Data Proxy | $15-20 | For 1000 affiliators |
| CapSolver CAPTCHA | $0.20-0.50 | ~300 CAPTCHAs |
| **Total** | **$15-20** | Per 1000 affiliators |

**Daily cost** (if scraping 1000/day): ~$15-20/day

---

## ✅ Success Checklist

Before running:
- [ ] Bright Data proxy configured
- [ ] CapSolver API key configured
- [ ] Cookies loaded (`config/cookies.json`)
- [ ] Test run successful (`quick_test.py`)
- [ ] Credits topped up

---

## 📖 Full Documentation

See `PRODUCTION_SETUP.md` for detailed setup guide.

---

**Ready?** Run `python3 quick_test.py` to start! 🚀
