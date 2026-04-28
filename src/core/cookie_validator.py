"""
Cookie Validator - Validates cookie format and tests cookie validity
"""
import json
import time
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of cookie validation"""
    is_valid: bool
    message: str
    errors: List[str]


class CookieValidator:
    """Validates cookie format and checks if cookies are still valid"""
    
    def __init__(self, test_url: str = "https://affiliate-id.tokopedia.com/connection/creator"):
        self.test_url = test_url
    
    def validate_format(self, cookie_file: str) -> ValidationResult:
        """Validate cookie file format"""
        errors = []
        
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                message=f"File tidak ditemukan: {cookie_file}",
                errors=[f"File {cookie_file} tidak ada"]
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                message="Format JSON tidak valid",
                errors=[f"JSON error: {str(e)}"]
            )
        
        # Check if cookies is a list
        if not isinstance(cookies, list):
            errors.append("Cookies harus berupa array/list")
            return ValidationResult(
                is_valid=False,
                message="Format cookies salah",
                errors=errors
            )
        
        # Check if cookies is not empty
        if len(cookies) == 0:
            errors.append("Cookies kosong, tidak ada cookie yang ditemukan")
            return ValidationResult(
                is_valid=False,
                message="Cookies kosong",
                errors=errors
            )
        
        # Validate each cookie
        required_fields = ['name', 'value', 'domain']
        tokopedia_cookie_found = False
        
        for i, cookie in enumerate(cookies):
            if not isinstance(cookie, dict):
                errors.append(f"Cookie #{i+1} bukan object/dict")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in cookie:
                    errors.append(f"Cookie #{i+1} ({cookie.get('name', 'unknown')}) tidak punya field '{field}'")
            
            # Check domain
            domain = cookie.get('domain', '')
            if 'tokopedia.com' in domain:
                tokopedia_cookie_found = True
            
            # Check if value is not empty
            value = cookie.get('value', '')
            if not value or value == 'GANTI_DENGAN_SESSION_ID_ASLI' or value == 'GANTI_DENGAN_DEVICE_ID_ASLI':
                errors.append(f"Cookie #{i+1} ({cookie.get('name', 'unknown')}) value masih placeholder, belum diganti dengan value asli")
        
        if not tokopedia_cookie_found:
            errors.append("Tidak ada cookie Tokopedia yang ditemukan (domain harus mengandung 'tokopedia.com')")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                message=f"Ditemukan {len(errors)} error dalam format cookies",
                errors=errors
            )
        
        return ValidationResult(
            is_valid=True,
            message=f"Format cookies valid! Total: {len(cookies)} cookies",
            errors=[]
        )
    
    def check_expiration(self, cookies: List[Dict]) -> bool:
        """Check if cookies are expired"""
        current_time = int(time.time())
        expired_count = 0
        expiring_soon_count = 0
        
        for cookie in cookies:
            if 'expirationDate' in cookie or 'expires' in cookie:
                # Handle both expirationDate (timestamp) and expires (date string)
                expiry = cookie.get('expirationDate') or cookie.get('expires')
                
                if isinstance(expiry, str):
                    # Try to parse date string
                    try:
                        from datetime import datetime
                        expiry = int(datetime.fromisoformat(expiry.replace('Z', '+00:00')).timestamp())
                    except:
                        continue
                
                if expiry < current_time:
                    expired_count += 1
                elif expiry < current_time + (24 * 3600):  # Expires in less than 24 hours
                    expiring_soon_count += 1
        
        if expired_count > 0:
            print(f"⚠️  Warning: {expired_count} cookies sudah expired")
            print("    Sebaiknya extract cookies baru dari browser")
            return False
        
        if expiring_soon_count > 0:
            print(f"⚠️  Warning: {expiring_soon_count} cookies akan expired dalam 24 jam")
            print("    Pertimbangkan untuk extract cookies baru")
        
        return True
    
    def test_cookies(self, cookies: List[Dict]) -> ValidationResult:
        """Test cookies by making request to Tokopedia"""
        print(f"\n🔍 Testing cookies dengan request ke: {self.test_url}")
        
        # Convert cookies to requests format
        cookie_dict = {}
        for cookie in cookies:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookie_dict[name] = value
        
        # Make test request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://affiliate-id.tokopedia.com/',
        }
        
        try:
            response = requests.get(
                self.test_url,
                cookies=cookie_dict,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            
            print(f"   Status code: {response.status_code}")
            print(f"   Final URL: {response.url}")
            
            # Check if redirected to login
            if 'login' in response.url.lower() or 'accounts.tokopedia.com' in response.url:
                return ValidationResult(
                    is_valid=False,
                    message="Cookies expired atau invalid - redirect ke login page",
                    errors=["Redirect ke login page detected", "Cookies mungkin sudah expired atau invalid"]
                )
            
            # Check for "Coba lagi" blocking page
            if 'coba lagi' in response.text.lower() or 'try again' in response.text.lower():
                return ValidationResult(
                    is_valid=False,
                    message="Tokopedia blocking page detected ('Coba lagi')",
                    errors=["Halaman 'Coba lagi' terdeteksi", "Mungkin IP kamu di-block atau cookies invalid"]
                )
            
            # Check if we got the affiliate page
            if response.status_code == 200:
                # Check for indicators of successful page load
                if 'creator' in response.text.lower() or 'affiliate' in response.text.lower():
                    return ValidationResult(
                        is_valid=True,
                        message="✅ Cookies valid! Berhasil akses halaman affiliate",
                        errors=[]
                    )
                else:
                    return ValidationResult(
                        is_valid=False,
                        message="Response 200 tapi konten tidak sesuai",
                        errors=["Halaman tidak mengandung konten affiliate yang diharapkan"]
                    )
            else:
                return ValidationResult(
                    is_valid=False,
                    message=f"HTTP error: {response.status_code}",
                    errors=[f"Status code: {response.status_code}"]
                )
        
        except requests.exceptions.Timeout:
            return ValidationResult(
                is_valid=False,
                message="Request timeout (30 detik)",
                errors=["Timeout - koneksi terlalu lama"]
            )
        except requests.exceptions.ConnectionError as e:
            return ValidationResult(
                is_valid=False,
                message="Connection error",
                errors=[f"Tidak bisa connect ke Tokopedia: {str(e)}"]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                message=f"Error: {str(e)}",
                errors=[str(e)]
            )
    
    def validate_all(self, cookie_file: str) -> ValidationResult:
        """Run all validations"""
        print("\n" + "="*80)
        print("🔍 VALIDASI COOKIES")
        print("="*80 + "\n")
        
        # Step 1: Validate format
        print("1️⃣  Validasi format file...")
        format_result = self.validate_format(cookie_file)
        
        if not format_result.is_valid:
            print(f"   ❌ {format_result.message}")
            for error in format_result.errors:
                print(f"      - {error}")
            return format_result
        
        print(f"   ✅ {format_result.message}\n")
        
        # Step 2: Load cookies
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        
        # Step 3: Check expiration
        print("2️⃣  Cek expiration...")
        self.check_expiration(cookies)
        print()
        
        # Step 4: Test cookies
        print("3️⃣  Test cookies dengan request ke Tokopedia...")
        test_result = self.test_cookies(cookies)
        
        if not test_result.is_valid:
            print(f"   ❌ {test_result.message}")
            for error in test_result.errors:
                print(f"      - {error}")
        else:
            print(f"   {test_result.message}")
        
        print("\n" + "="*80 + "\n")
        
        return test_result


if __name__ == "__main__":
    # Test the validator
    validator = CookieValidator()
    result = validator.validate_all("config/cookies.json")
    
    if result.is_valid:
        print("✅ Cookies siap digunakan untuk scraping!")
    else:
        print("❌ Cookies tidak valid. Silakan extract cookies baru dari browser.")
