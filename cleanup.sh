#!/bin/bash
# Cleanup script untuk hapus file-file yang tidak terpakai

echo "🧹 Cleaning up unused files..."

# 1. Hapus semua file debug HTML/PNG/JSON/TXT
echo "📄 Removing debug files..."
rm -f after_email_click_*.html after_email_click_*.png after_email_click_*.txt
rm -f before_email_click_*.html before_email_click_*.png
rm -f analysis_creator_*.html analysis_creator_*.png analysis_creator_*.json analysis_creator_*.txt
rm -f debug_*.html debug_*.png debug_*.py
rm -f test_detail_*.html test_detail_*.png test_detail_*.txt

# 2. Hapus file test yang tidak terpakai
echo "🧪 Removing old test files..."
rm -f test_*.py
rm -f quick_test.py
rm -f analyze_page_structure.py
rm -f check_email_icon.py
rm -f extract_email_context.py
rm -f inspect_detail_page.py

# 3. Hapus scraper lama yang sudah tidak terpakai
echo "🗑️  Removing old scrapers..."
rm -f scrape_affiliators.py
rm -f scrape_with_browser.py
rm -f scrape_with_browser_v2.py
rm -f scrape_manual_captcha.py
rm -f scrape_with_email_click.py
rm -f production_scraper_*.py

# 4. Hapus file setup/config lama
echo "⚙️  Removing old setup files..."
rm -f setup_brightdata.py
rm -f setup_proxy_quick.py
rm -f extract_cookies.py
rm -f normalize_cookies.py
rm -f validate_cookies.py
rm -f login_and_save_cookies.py

# 5. Hapus dokumentasi lama
echo "📚 Removing old documentation..."
rm -f CURRENT_STATUS.md
rm -f FINAL_SUMMARY.md
rm -f IMPLEMENTATION_SUMMARY.md
rm -f PRODUCTION_SETUP.md
rm -f PROXY_SETUP_WEBSHARE.md
rm -f QUICK_START.md
rm -f QUICK_START_MANUAL_COOKIES.md
rm -f README_PRODUCTION.md
rm -f README_SIMPLE.md
rm -f SETUP_GUIDE.md
rm -f SHADOW_DOM_ANALYSIS.md
rm -f manual_browser_guide.md

# 6. Hapus hasil scraping lama
echo "📊 Removing old scraping results..."
rm -f production_results_*.json
rm -f test_output.log

# 7. Hapus file HTML detail page lama
echo "🌐 Removing old HTML files..."
rm -f detail_page*.html
rm -f debug_list_page*.html

# 8. Hapus Docker files (jika tidak dipakai)
echo "🐳 Removing Docker files..."
rm -f Dockerfile
rm -f docker-compose.yml

# 9. Hapus folder yang tidak terpakai
echo "📁 Removing unused directories..."
rm -rf captcha_helper_extension/
rm -rf captchasonic_config/
rm -rf docs/
rm -rf htmlcov/
rm -rf logs/
rm -rf scripts/
rm -rf tools/

# 10. Hapus pytest cache
echo "🧹 Cleaning pytest cache..."
rm -rf .pytest_cache/
rm -rf .hypothesis/
rm -f .coverage

# 11. Hapus __pycache__
echo "🗑️  Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📁 Files yang TETAP ADA (yang masih dipakai):"
echo "  - scrape_full_data.py      (Main scraper)"
echo "  - dashboard.py             (Dashboard)"
echo "  - README_SCRAPER.md        (Documentation)"
echo "  - main.py                  (Entry point)"
echo "  - requirements.txt         (Dependencies)"
echo "  - src/                     (Core modules)"
echo "  - tests/                   (Unit tests)"
echo "  - config/                  (Cookies & config)"
echo "  - output/                  (Scraping results)"
echo "  - venv/                    (Virtual environment)"
echo ""
