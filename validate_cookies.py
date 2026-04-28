#!/usr/bin/env python3
"""
Script untuk validasi cookies sebelum scraping
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.cookie_validator import CookieValidator


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validasi cookies Tokopedia')
    parser.add_argument(
        '--cookie-file',
        default='config/cookies.json',
        help='Path ke file cookies (default: config/cookies.json)'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.cookie_file).exists():
        print(f"\n❌ File tidak ditemukan: {args.cookie_file}")
        print("\n💡 Jalankan dulu: python extract_cookies.py")
        print("   untuk membuat file template dan melihat panduan\n")
        sys.exit(1)
    
    # Validate cookies
    validator = CookieValidator()
    result = validator.validate_all(args.cookie_file)
    
    if result.is_valid:
        print("="*80)
        print("✅ COOKIES VALID DAN SIAP DIGUNAKAN!")
        print("="*80)
        print("\n🚀 Langkah selanjutnya:")
        print("   python scrape_affiliators.py")
        print("\n")
        sys.exit(0)
    else:
        print("="*80)
        print("❌ COOKIES TIDAK VALID")
        print("="*80)
        print("\n🔧 Yang perlu dilakukan:")
        print("1. Buka Chrome dan login ke Tokopedia Affiliate Center")
        print("2. Extract cookies baru dari DevTools")
        print("3. Simpan ke config/cookies.json")
        print("4. Jalankan lagi: python validate_cookies.py")
        print("\n💡 Lihat panduan lengkap: python extract_cookies.py\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
