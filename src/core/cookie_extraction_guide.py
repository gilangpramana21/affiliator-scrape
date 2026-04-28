"""
Cookie Extraction Guide - Interactive guide for manual cookie extraction from Chrome
"""
import json
from pathlib import Path
from typing import List, Dict


class CookieExtractionGuide:
    """Interactive guide to help users extract cookies from Chrome DevTools"""
    
    def __init__(self, cookie_file_path: str = "config/cookies.json"):
        self.cookie_file_path = cookie_file_path
    
    def show_guide(self):
        """Display step-by-step cookie extraction instructions"""
        print("\n" + "="*80)
        print("🍪 PANDUAN EKSTRAKSI COOKIE TOKOPEDIA AFFILIATE CENTER")
        print("="*80)
        print("\nKenapa perlu manual? Karena Tokopedia mendeteksi SEMUA browser automation.")
        print("Solusi: Gunakan browser asli untuk login, lalu copy cookies-nya.\n")
        
        print("📋 LANGKAH-LANGKAH:\n")
        
        print("1️⃣  Buka Google Chrome (browser ASLI, bukan automation)")
        print("    ⚠️  PENTING: Jangan gunakan browser yang dibuka oleh script!\n")
        
        print("2️⃣  Navigasi ke halaman Affiliate Center:")
        print("    URL: https://affiliate-id.tokopedia.com/connection/creator\n")
        
        print("3️⃣  Login dengan akun Tokopedia kamu")
        print("    - Masukkan email/phone dan password")
        print("    - Selesaikan CAPTCHA jika ada")
        print("    - Pastikan berhasil masuk ke halaman affiliator\n")
        
        print("4️⃣  Buka Chrome DevTools:")
        print("    - Tekan F12 (atau Cmd+Option+I di Mac)")
        print("    - Atau klik kanan → Inspect\n")
        
        print("5️⃣  Pergi ke tab 'Application':")
        print("    - Di DevTools, klik tab 'Application' (paling kanan)")
        print("    - Jika tidak terlihat, klik ikon >> untuk melihat tab tersembunyi\n")
        
        print("6️⃣  Buka Cookies:")
        print("    - Di sidebar kiri, expand 'Cookies'")
        print("    - Klik 'https://affiliate-id.tokopedia.com'\n")
        
        print("7️⃣  Copy semua cookies:")
        print("    - Klik kanan di area cookies → 'Show Requests With This Cookie'")
        print("    - ATAU gunakan extension 'EditThisCookie' atau 'Cookie-Editor'")
        print("    - Export cookies dalam format JSON\n")
        
        print("8️⃣  Simpan cookies ke file:")
        print(f"    - Simpan ke: {self.cookie_file_path}")
        print("    - Format: JSON array dengan fields: name, value, domain, path\n")
        
        print("📝 CONTOH FORMAT COOKIES.JSON:\n")
        example = [
            {
                "name": "_SID_Tokopedia_",
                "value": "your_session_id_here",
                "domain": ".tokopedia.com",
                "path": "/",
                "httpOnly": True,
                "secure": True
            },
            {
                "name": "DID",
                "value": "your_device_id_here",
                "domain": ".tokopedia.com",
                "path": "/",
                "httpOnly": False,
                "secure": True
            }
        ]
        print(json.dumps(example, indent=2))
        
        print("\n" + "="*80)
        print("✅ SETELAH COOKIES TERSIMPAN:")
        print("="*80)
        print("1. Jalankan scraper dengan: python main.py")
        print("2. Script akan otomatis load cookies dari file")
        print("3. Scraping akan berjalan tanpa browser automation\n")
        
        print("⚠️  CATATAN PENTING:")
        print("- Cookies akan expired setelah beberapa hari")
        print("- Jika scraper error 'cookie expired', ulangi proses ini")
        print("- Jangan share cookies ke orang lain (security risk)\n")
        
        print("="*80 + "\n")
    
    def validate_cookie_format(self, cookie_file: str) -> bool:
        """Validate cookie file format"""
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            
            if not isinstance(cookies, list):
                print("❌ Error: Cookies harus berupa array/list")
                return False
            
            if len(cookies) == 0:
                print("❌ Error: Cookies kosong")
                return False
            
            required_fields = ['name', 'value', 'domain']
            for i, cookie in enumerate(cookies):
                if not isinstance(cookie, dict):
                    print(f"❌ Error: Cookie #{i+1} bukan object/dict")
                    return False
                
                for field in required_fields:
                    if field not in cookie:
                        print(f"❌ Error: Cookie #{i+1} tidak punya field '{field}'")
                        return False
                
                # Check domain
                domain = cookie.get('domain', '')
                if 'tokopedia.com' not in domain:
                    print(f"⚠️  Warning: Cookie #{i+1} domain bukan Tokopedia: {domain}")
            
            print(f"✅ Format cookies valid! Total: {len(cookies)} cookies")
            return True
            
        except FileNotFoundError:
            print(f"❌ Error: File tidak ditemukan: {cookie_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Error: Format JSON tidak valid: {e}")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def check_cookie_expiration(self, cookies: List[Dict]) -> bool:
        """Check if cookies are expired"""
        import time
        
        current_time = int(time.time())
        expired_count = 0
        
        for cookie in cookies:
            if 'expirationDate' in cookie:
                expiry = cookie['expirationDate']
                if expiry < current_time:
                    expired_count += 1
        
        if expired_count > 0:
            print(f"⚠️  Warning: {expired_count} cookies sudah expired")
            print("    Sebaiknya extract cookies baru dari browser")
            return False
        
        print("✅ Cookies belum expired")
        return True
    
    def create_example_file(self):
        """Create example cookies.json file"""
        example = [
            {
                "name": "_SID_Tokopedia_",
                "value": "GANTI_DENGAN_SESSION_ID_ASLI",
                "domain": ".tokopedia.com",
                "path": "/",
                "httpOnly": True,
                "secure": True
            },
            {
                "name": "DID",
                "value": "GANTI_DENGAN_DEVICE_ID_ASLI",
                "domain": ".tokopedia.com",
                "path": "/",
                "httpOnly": False,
                "secure": True
            }
        ]
        
        # Create config directory if not exists
        Path(self.cookie_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.cookie_file_path, 'w') as f:
            json.dump(example, f, indent=2)
        
        print(f"✅ File contoh dibuat: {self.cookie_file_path}")
        print("⚠️  GANTI nilai 'value' dengan cookies asli dari browser!")


if __name__ == "__main__":
    # Test the guide
    guide = CookieExtractionGuide()
    guide.show_guide()
    
    # Create example file
    guide.create_example_file()
