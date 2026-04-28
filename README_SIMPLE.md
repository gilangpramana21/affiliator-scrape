# 🎯 Tokopedia Affiliator Scraper - Simple Manual Cookies Version

## ✨ Apa yang bisa dilakukan?

Scrape data affiliator dari Tokopedia Affiliate Center, termasuk:
- ✅ Username
- ✅ Kategori
- ✅ Statistik (pengikut, GMV, produk terjual, dll)
- ✅ **WhatsApp** (PENTING!)
- ✅ **Email** (PENTING!)

## 🚀 Quick Start (3 Langkah)

### 1️⃣ Extract Cookies dari Chrome

```bash
python extract_cookies.py
```

Ikuti panduan yang muncul:
1. Buka Chrome
2. Login ke https://affiliate-id.tokopedia.com/connection/creator
3. Buka DevTools (F12) → Application → Cookies
4. Copy cookies ke `config/cookies.json`

### 2️⃣ Validasi Cookies

```bash
python validate_cookies.py
```

Pastikan output: `✅ COOKIES VALID DAN SIAP DIGUNAKAN!`

### 3️⃣ Mulai Scraping

```bash
# Scrape 1 page
python scrape_affiliators.py

# Scrape 5 pages
python scrape_affiliators.py --max-pages 5
```

**Output**: `output/affiliators.json`

---

## 📦 Installation

```bash
# Activate venv
source venv/bin/activate  # Mac/Linux
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 📊 Output Format

```json
[
  {
    "username": "creator123",
    "detail_url": "https://affiliate-id.tokopedia.com/creator/creator123",
    "whatsapp": "+628123456789",
    "email": "creator@example.com",
    "scraped_at": "2026-04-27T10:30:00"
  }
]
```

---

## ❓ FAQ

### Q: Kenapa harus manual cookies?
**A:** Tokopedia mendeteksi SEMUA browser automation (Playwright, Selenium, dll). Manual cookies adalah satu-satunya cara yang work 100%.

### Q: Berapa lama cookies valid?
**A:** Biasanya 7-14 hari. Jika expired, extract cookies baru.

### Q: Berapa success rate contact extraction?
**A:** ~40-60%, tergantung creator yang share kontak.

### Q: Apakah aman?
**A:** Ya, ini hanya HTTP requests biasa dengan cookies kamu sendiri.

### Q: Bisa scrape berapa banyak?
**A:** Tergantung rate limiting. Recommended: max 100-200 affiliators per session.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Cookies tidak valid | Extract cookies baru dari Chrome |
| "Coba lagi" page | Cookies expired atau IP blocked, tunggu beberapa jam |
| No contact found | Normal, tidak semua creator share kontak |
| Script error | Check logs, update selectors jika Tokopedia update HTML |

---

## 📁 File Structure

```
.
├── extract_cookies.py          # Step 1: Panduan extract cookies
├── validate_cookies.py         # Step 2: Validasi cookies
├── scrape_affiliators.py       # Step 3: Main scraper
├── test_contact_extraction.py  # Test contact extractor
├── config/
│   └── cookies.json           # Your cookies here
├── output/
│   └── affiliators.json       # Scraping results
└── src/
    └── core/
        ├── cookie_extraction_guide.py
        ├── cookie_validator.py
        └── contact_extractor.py
```

---

## 🎯 Success Checklist

- [ ] Cookies extracted dari Chrome
- [ ] Cookies validated (✅ valid)
- [ ] Scraper running tanpa error
- [ ] WhatsApp extracted
- [ ] Email extracted
- [ ] Results saved to JSON

---

## 📚 Documentation

- **Quick Start**: `QUICK_START_MANUAL_COOKIES.md`
- **Full Spec**: `.kiro/specs/tokopedia-affiliate-scraper/`

---

## 💡 Tips

1. **Extract cookies baru** setiap 7-14 hari
2. **Gunakan delay** antar request (sudah built-in)
3. **Check output** setelah scraping untuk verify data
4. **Update selectors** jika Tokopedia update HTML
5. **Use proxy** (optional) jika perlu scale up

---

**Happy Scraping! 🚀**

Jika ada masalah, jalankan `python validate_cookies.py` untuk diagnose.
