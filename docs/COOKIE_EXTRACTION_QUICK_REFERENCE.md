# Cookie Extraction Quick Reference Card

**Quick guide for extracting Tokopedia cookies - Print or bookmark this page!**

---

## 🚀 Quick Start (5 Minutes)

### 1. Open Chrome & Login
```
URL: https://affiliate-id.tokopedia.com/connection/creator
```
- Login with your Tokopedia account
- Ensure you reach the affiliator list page

### 2. Open DevTools
- **Windows/Linux:** Press `F12`
- **Mac:** Press `Cmd + Option + I`

### 3. Navigate to Cookies
1. Click **"Application"** tab (top of DevTools)
2. Expand **"Cookies"** in left sidebar
3. Click **`https://affiliate-id.tokopedia.com`**

### 4. Export Cookies

**Option A: Using Extension (RECOMMENDED)**
1. Install [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/) (Chrome)
2. Click extension icon
3. Click "Export" button
4. Copy JSON

**Option B: Manual Copy**
- Copy each cookie's name, value, domain, path
- Format as JSON array (see template below)

### 5. Save to File
```bash
# Save to this location:
config/cookies.json
```

### 6. Validate
```bash
python validate_cookies.py
```

Expected: `✅ COOKIES VALID DAN SIAP DIGUNAKAN!`

---

## 📋 Cookie JSON Template

```json
[
  {
    "name": "_SID_Tokopedia_",
    "value": "YOUR_SESSION_ID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": true,
    "secure": true
  },
  {
    "name": "DID",
    "value": "YOUR_DEVICE_ID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": false,
    "secure": true
  },
  {
    "name": "_UUID_CAS_",
    "value": "YOUR_UUID_HERE",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": false,
    "secure": true
  }
]
```

⚠️ Replace `YOUR_*_HERE` with actual values from Chrome!

---

## 🔧 Quick Commands

```bash
# Show extraction guide
python extract_cookies.py

# Validate cookies
python validate_cookies.py

# Test scraping (1 page)
python scrape_affiliators.py --max-pages 1

# Run full scraper
python main.py
```

---

## ⚠️ Common Issues

### "Cookies tidak valid"
→ Check JSON format, ensure all required fields present

### "Coba lagi" page
→ Cookies expired, extract fresh cookies

### "File tidak ditemukan"
→ Save to `config/cookies.json` (check path)

### JSON syntax error
→ Use [JSONLint](https://jsonlint.com/) to validate

---

## 🔒 Security Reminders

- ❌ Never share cookies with others
- ❌ Don't commit cookies to Git
- ✅ Add `config/cookies.json` to `.gitignore`
- ✅ Use file permissions: `chmod 600 config/cookies.json`

---

## 📅 Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Refresh cookies | Every 7 days | `python extract_cookies.py` |
| Validate cookies | Before scraping | `python validate_cookies.py` |
| Check logs | After scraping | `tail logs/scraper.log` |
| Backup output | Weekly | `cp output/affiliators.json backup/` |

---

## 🆘 Emergency Troubleshooting

```bash
# 1. Validate cookies
python validate_cookies.py

# 2. If invalid, re-extract
python extract_cookies.py

# 3. Test with single page
python scrape_affiliators.py --max-pages 1

# 4. Check logs
tail -n 50 logs/scraper.log

# 5. Verify output
cat output/affiliators.json | python -m json.tool
```

---

## 📞 Need Help?

1. Check full documentation: `README.md`
2. Check troubleshooting: `README.md` → Troubleshooting section
3. Check logs: `logs/scraper.log`
4. Open GitHub issue with logs and error messages

---

## ✅ Pre-Flight Checklist

Before running scraper:

- [ ] Chrome installed
- [ ] Logged in to Tokopedia Affiliate Center
- [ ] Cookies extracted and saved to `config/cookies.json`
- [ ] Cookies validated with `python validate_cookies.py`
- [ ] Configuration file exists: `config/config.json`
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip install -r requirements.txt`

---

## 🎯 Success Indicators

After running scraper, you should see:

- ✅ No "cookies invalid" errors
- ✅ No "Coba lagi" blocking pages
- ✅ Affiliator data in `output/affiliators.json`
- ✅ Success rate > 80% in logs
- ✅ Contact info extracted (40-60% of affiliators)

---

**Last Updated:** 2024  
**Version:** 1.0  
**For:** Tokopedia Affiliate Scraper (Manual Cookie Approach)
