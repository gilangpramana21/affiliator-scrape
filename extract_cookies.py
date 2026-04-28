#!/usr/bin/env python3
"""
Script untuk menampilkan panduan ekstraksi cookies dan membuat file template
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.cookie_extraction_guide import CookieExtractionGuide


def main():
    guide = CookieExtractionGuide()
    
    # Show the guide
    guide.show_guide()
    
    # Ask if user wants to create example file
    print("Apakah kamu ingin membuat file contoh cookies.json? (y/n): ", end='')
    response = input().strip().lower()
    
    if response in ['y', 'yes', 'ya']:
        guide.create_example_file()
        print("\n✅ File contoh sudah dibuat!")
        print("📝 Sekarang edit file config/cookies.json dan ganti dengan cookies asli dari browser")
    else:
        print("\n👍 Oke, silakan buat file cookies.json secara manual")
    
    print("\n" + "="*80)
    print("LANGKAH SELANJUTNYA:")
    print("="*80)
    print("1. Extract cookies dari Chrome (ikuti panduan di atas)")
    print("2. Simpan cookies ke config/cookies.json")
    print("3. Validasi cookies dengan: python validate_cookies.py")
    print("4. Jalankan scraper dengan: python scrape_affiliators.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
