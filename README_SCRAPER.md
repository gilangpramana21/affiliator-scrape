# Tokopedia Affiliator Scraper - Full Data Extraction

Scraper lengkap untuk mengambil data creator dari Tokopedia Affiliate Center dengan export ke Excel dan **Web Dashboard**.

## Features

✅ **Full Data Extraction**
- Username & Display Name
- Level (Lv. 7, Lv. 8, dll)
- Rating
- Kategori Produk
- Jumlah Followers
- Bio
- GMV (Gross Merchandise Value)
- Produk Terjual
- Rata-rata Tayangan
- Gender Distribution (Male/Female %)
- Age Group
- **Email & WhatsApp** (jika tersedia)

✅ **Auto Load 100+ Creators**
- Automatic scrolling/pagination
- Load up to 100 creators from list page

✅ **Excel Export**
- Save to `.xlsx` format with nice formatting
- Separate file for creators with contacts
- Easy to analyze in Excel/Google Sheets

✅ **Web Dashboard** 🆕
- Modern web interface
- Real-time scraping progress
- Interactive data table with search
- One-click Excel export
- Duplicate detection & removal
- Statistics overview
- **Ready to deploy!**

✅ **Console Dashboard**
- Overview statistics
- Level distribution
- Top categories
- Followers analysis
- Top creators by followers
- Contact info summary
- Gender & age distribution

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Usage

### Option 1: Web Dashboard (Recommended) 🌟

```bash
# Start web dashboard
python app.py
```

Buka browser: **http://localhost:5000**

**Features:**
- 🎮 **Kontrol Scraping**: Pilih jumlah creator yang ingin di-scrape
- 📊 **Real-time Progress**: Lihat progress scraping secara live
- 🔍 **Search & Filter**: Cari creator berdasarkan username, email, kategori
- 📈 **Statistics**: Overview lengkap (total, dengan email, dengan WhatsApp)
- 📥 **Export**: Download Excel dengan 1 klik
- 🧹 **Remove Duplicates**: Hapus duplikat otomatis
- 📧 **Export Contacts**: Download hanya creator dengan kontak

**Cara Pakai:**
1. Masukkan jumlah creator (misal: 10, 50, 100)
2. Klik "Mulai Scraping"
3. Browser akan terbuka otomatis
4. Solve CAPTCHA secara manual saat diminta
5. Dashboard akan update progress secara real-time
6. Setelah selesai, download Excel atau lihat data di table

### Option 2: Command Line

```bash
# Scrape 100 creators (default)
python scrape_full_data.py

# Scrape custom number of creators
python scrape_full_data.py --max-creators 50

# Use custom cookie file
python scrape_full_data.py --cookie-file path/to/cookies.json
```

**IMPORTANT**: 
- Script akan pause untuk CAPTCHA (2x: list page + setiap detail page)
- Solve CAPTCHA secara manual, lalu tekan ENTER
- Script akan otomatis load 100 creators dengan scroll/pagination
- Setiap creator akan di-scrape detail datanya

### Option 3: Console Dashboard

```bash
python dashboard.py
```

Dashboard akan menampilkan:
- Total creators & contact info statistics
- Level distribution
- Top 10 categories
- Followers analysis (average, median, max)
- Top 10 creators by followers
- List of creators with contact info
- Gender & age distribution

## Output Files

```
output/
├── affiliators_full.json          # Raw JSON data
├── affiliators_full.xlsx          # Full Excel export (formatted)
└── affiliators_with_contacts.xlsx # Only creators with email/WhatsApp
```

## Excel Columns

| Column | Description |
|--------|-------------|
| index | Creator index (0-based) |
| username | TikTok username |
| display_name | Display name |
| shop_name | Shop name (if available) |
| level | Creator level (7, 8, etc) |
| rating | Rating or "Belum ada rating" |
| category | Product category |
| followers | Follower count (268,1 rb, 1 jt, etc) |
| bio | Creator bio |
| gmv | Gross Merchandise Value |
| products_sold | Number of products sold |
| avg_views | Average video views |
| gender_male | Male audience % |
| gender_female | Female audience % |
| age_group | Most common age group |
| email | Email address (if available) |
| whatsapp | WhatsApp number (if available) |
| scraped_at | Timestamp |

## Deployment 🚀

Dashboard siap di-deploy ke cloud platform! Lihat **[DEPLOYMENT.md](DEPLOYMENT.md)** untuk panduan lengkap.

**Supported Platforms:**
- ✅ Railway (Recommended - Free tier available)
- ✅ Heroku (Free tier available)
- ✅ Render (Free tier available)
- ✅ Docker (Self-hosted)

**Quick Deploy ke Railway:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login & deploy
railway login
railway init
railway up
```

## Example Dashboard Output

```
================================================================================
📊 TOKOPEDIA AFFILIATOR DASHBOARD
================================================================================

📈 OVERVIEW
────────────────────────────────────────────────────────────────────────────────
Total Creators:        100
With Email:            20 (20.0%)
With WhatsApp:         18 (18.0%)
With Any Contact:      25 (25.0%)

📊 LEVEL DISTRIBUTION
────────────────────────────────────────────────────────────────────────────────
Level 7:  45 creators (45.0%)
Level 8:  55 creators (55.0%)

🏷️  TOP CATEGORIES
────────────────────────────────────────────────────────────────────────────────
Pakaian & Pakaian Dalam Wanita           25 creators (25.0%)
Perawatan & Kecantikan                   20 creators (20.0%)
Telepon & Elektronik                     15 creators (15.0%)

👥 FOLLOWERS ANALYSIS
────────────────────────────────────────────────────────────────────────────────
Average Followers:     350,000
Median Followers:      250,000
Max Followers:         7,600,000

🌟 TOP 10 CREATORS BY FOLLOWERS
────────────────────────────────────────────────────────────────────────────────
jesicathamrin                  7,6 jt          ❌
arinyanty_luchi                3,9 jt          ✅
ischaindyofc                   3,1 jt          ❌

📧 CREATORS WITH CONTACT INFO
────────────────────────────────────────────────────────────────────────────────

arinyanty_luchi
  Followers: 250,6 rb
  Email:     miftahulardhy573@gmail.com
  WhatsApp:  +6282363624084
```

## Notes

- **CAPTCHA**: Script akan pause untuk manual CAPTCHA solving
- **Rate Limiting**: Ada delay 3 detik antar creator untuk avoid rate limiting
- **Contact Info**: Tidak semua creator share email/WhatsApp (sekitar 20-30%)
- **Data Accuracy**: Data diambil langsung dari Tokopedia Affiliate Center
- **Duplicate Detection**: Web dashboard otomatis detect & remove duplikat berdasarkan username, email, WhatsApp

## Troubleshooting

### "No creators found"
- Pastikan sudah login ke Tokopedia Affiliate Center
- Pastikan cookies.json valid
- Solve CAPTCHA dengan benar

### "Email icon not found"
- Normal, tidak semua creator share contact info
- Script akan tetap save data creator lainnya

### Excel export error
- Install: `pip install pandas openpyxl`

### Web dashboard tidak bisa diakses
- Pastikan port 5000 tidak digunakan aplikasi lain
- Coba port lain: `PORT=8000 python app.py`

### Scraping stuck di web dashboard
- Check terminal untuk error messages
- Pastikan Playwright terinstall: `playwright install chromium`

## Next Steps

Setelah scraping selesai:
1. Buka `output/affiliators_full.xlsx` di Excel
2. Filter creators dengan email/WhatsApp
3. Analyze data (followers, category, GMV, dll)
4. Export contact list: `output/affiliators_with_contacts.xlsx`
5. Deploy dashboard ke cloud untuk akses dari mana saja!
