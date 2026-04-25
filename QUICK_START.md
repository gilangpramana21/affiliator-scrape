# Quick Start Guide

## 🚀 Langkah Cepat (5 Menit)

### 1. Update Cookies (WAJIB!)

```bash
# 1. Login ke https://affiliate.tokopedia.com di browser
# 2. Install extension: EditThisCookie (Chrome) atau Cookie-Editor (Firefox)
# 3. Export cookies → Copy JSON
# 4. Paste ke config/cookies.json
```

### 2. Test Scraper (10 Affiliators)

```bash
python3 test_original_scraper.py
```

**Expected**: Success rate > 80%, CAPTCHA rate < 30%

### 3. Production Run (1000 Affiliators)

```bash
python3 production_scraper_enhanced.py --max-affiliators 1000
```

## ⚠️ Jika Menggunakan Public WiFi

Public WiFi = CAPTCHA rate 70-90% = **WAJIB pakai proxy!**

### Setup Bright Data Proxy:

1. **Login**: https://brightdata.com
2. **Create Zone**: Residential → Indonesia → Port 22225
3. **Get Credentials**: Copy username & password
4. **Update Config**: `config/config_with_proxy.json`
   ```json
   {
     "proxies": [{
       "server": "http://brd.superproxy.io:22225",
       "username": "brd-customer-xxx-zone-xxx-country-id",
       "password": "your_password"
     }]
   }
   ```
5. **Run with Proxy**:
   ```bash
   python3 production_scraper_enhanced.py \
     --config config/config_with_proxy.json \
     --max-affiliators 1000
   ```

## 📊 Expected Results

- **Metrics (GMV, GMP, dll)**: 95%+ success
- **Contact (WhatsApp, Email)**: 40-60% success
- **Speed**: ~8 hours for 1000 affiliators
- **Output**: `output/affiliators_production.xlsx`

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Low success rate (<80%) | Update cookies |
| High CAPTCHA rate (>50%) | Enable proxy + CapSolver |
| Bright Data error | Refresh page, wait 5 min, retry |
| Wrong data extracted | Check logs, update selectors |

## 📖 Full Documentation

Lihat `SETUP_GUIDE.md` untuk dokumentasi lengkap.
