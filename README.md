# Tokopedia Affiliator Scraper

Scraper untuk mengambil data creator dari Tokopedia Affiliate Center dengan export ke Excel dan dashboard visualisasi.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Playwright browsers
playwright install chromium

# 3. Scrape data (100 creators)
python scrape_full_data.py --max-creators 100

# 4. View dashboard
python dashboard.py
```

## ✨ Features

### Data Extraction
- ✅ Username & Display Name
- ✅ Level (Lv. 7, Lv. 8, dll)
- ✅ Rating
- ✅ Kategori Produk
- ✅ Jumlah Followers
- ✅ Bio
- ✅ GMV (Gross Merchandise Value)
- ✅ Produk Terjual
- ✅ Rata-rata Tayangan
- ✅ Gender Distribution (Male/Female %)
- ✅ Age Group
- ✅ **Email & WhatsApp** (jika tersedia)

### Export & Visualization
- ✅ Export ke Excel (.xlsx)
- ✅ Dashboard sederhana
- ✅ Filter creators dengan contact info
- ✅ Statistics & analytics

## 📁 Project Structure

```
.
├── scrape_full_data.py      # Main scraper
├── dashboard.py             # Dashboard & analytics
├── README_SCRAPER.md        # Detailed documentation
├── requirements.txt         # Python dependencies
├── src/                     # Core modules
│   ├── anti_detection/      # Browser fingerprinting
│   ├── core/                # Scraping logic
│   └── models/              # Data models
├── config/                  # Cookies & configuration
├── output/                  # Scraping results
└── tests/                   # Unit tests
```

## 📊 Output Files

```
output/
├── affiliators_full.json          # Raw JSON data
├── affiliators_full.xlsx          # Full Excel export
└── affiliators_with_contacts.xlsx # Only creators with email/WhatsApp
```

## 🔧 Usage

### Scrape Data

```bash
# Scrape 100 creators (default)
python scrape_full_data.py

# Scrape custom number
python scrape_full_data.py --max-creators 50

# Use custom cookie file
python scrape_full_data.py --cookie-file path/to/cookies.json
```

### View Dashboard

```bash
python dashboard.py
```

Dashboard menampilkan:
- Total creators & contact statistics
- Level distribution
- Top categories
- Followers analysis
- Top creators by followers
- Gender & age distribution

## ⚠️ Important Notes

- **CAPTCHA**: Script akan pause untuk manual CAPTCHA solving
- **Rate Limiting**: Ada delay 3 detik antar creator
- **Contact Info**: ~20-30% creator share email/WhatsApp
- **Cookies**: Pastikan cookies.json valid (login ke Tokopedia Affiliate Center)

## 📖 Documentation

Lihat [README_SCRAPER.md](README_SCRAPER.md) untuk dokumentasi lengkap.

## 🧪 Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## 🧹 Cleanup

Untuk membersihkan file debug/test:

```bash
./cleanup.sh
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

---

**Made with ❤️ for Tokopedia Affiliators**
