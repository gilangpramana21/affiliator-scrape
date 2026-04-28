#!/usr/bin/env python3
"""
Script utama untuk scraping data affiliator Tokopedia
Termasuk kontak WhatsApp dan Email
"""
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.cookie_validator import CookieValidator
from core.contact_extractor import ContactExtractor
from lxml import html as lxml_html


class TokopediaAffiliatorScraper:
    """Simple scraper untuk data affiliator dengan manual cookies"""
    
    def __init__(self, cookie_file: str = "config/cookies.json"):
        self.cookie_file = cookie_file
        self.base_url = "https://affiliate-id.tokopedia.com"
        self.list_url = f"{self.base_url}/connection/creator"
        self.cookies = {}
        self.session = requests.Session()
        self.contact_extractor = ContactExtractor()
        self.results = []
        
        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': self.base_url,
            'Connection': 'keep-alive',
        }
    
    def load_cookies(self):
        """Load cookies from file"""
        print("📂 Loading cookies...")
        
        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        # Convert to dict
        for cookie in cookies_list:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                self.cookies[name] = value
        
        print(f"   ✅ Loaded {len(self.cookies)} cookies\n")
    
    def validate_cookies(self):
        """Validate cookies before scraping"""
        print("🔍 Validating cookies...")
        
        validator = CookieValidator()
        result = validator.validate_all(self.cookie_file)
        
        if not result.is_valid:
            print("\n❌ Cookies tidak valid!")
            print("   Jalankan: python validate_cookies.py untuk detail\n")
            sys.exit(1)
        
        print()
    
    def scrape_list_page(self, page: int = 1) -> List[Dict]:
        """Scrape list page untuk mendapatkan daftar affiliator"""
        print(f"📄 Scraping list page {page}...")
        
        url = f"{self.list_url}?page={page}"
        
        try:
            response = self.session.get(
                url,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"   ❌ Error: Status code {response.status_code}")
                return []
            
            # Check for blocking
            if 'coba lagi' in response.text.lower():
                print("   ❌ Tokopedia blocking page detected!")
                return []
            
            # Parse HTML
            doc = lxml_html.fromstring(response.content)
            
            # Extract affiliators (adjust selectors based on actual HTML)
            # This is a placeholder - you need to inspect the actual page
            affiliators = []
            
            # Try to find creator rows
            rows = doc.xpath("//div[contains(@class, 'creator')]|//tr[contains(@class, 'creator')]")
            
            print(f"   Found {len(rows)} potential creator elements")
            
            for row in rows:
                try:
                    # Extract basic info (adjust selectors)
                    username = self._extract_text(row, ".//span[contains(@class, 'username')]|.//div[contains(@class, 'name')]")
                    detail_url = self._extract_href(row, ".//a[contains(@href, 'creator')]")
                    
                    if username or detail_url:
                        affiliators.append({
                            'username': username,
                            'detail_url': detail_url,
                            'scraped_at': datetime.now().isoformat()
                        })
                except Exception as e:
                    continue
            
            print(f"   ✅ Extracted {len(affiliators)} affiliators\n")
            return affiliators
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            return []
    
    def scrape_detail_page(self, detail_url: str) -> Dict:
        """Scrape detail page untuk mendapatkan kontak"""
        print(f"   📱 Scraping detail: {detail_url}")
        
        try:
            response = self.session.get(
                detail_url,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"      ❌ Status code {response.status_code}")
                return {}
            
            # Extract contacts
            contacts = self.contact_extractor.extract_contacts(response.text)
            
            whatsapp = contacts.get('whatsapp')
            email = contacts.get('email')
            
            if whatsapp:
                print(f"      ✅ WhatsApp: {whatsapp}")
            if email:
                print(f"      ✅ Email: {email}")
            
            if not whatsapp and not email:
                print(f"      ⚠️  No contact found")
            
            return contacts
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return {}
    
    def scrape(self, max_pages: int = 1):
        """Main scraping function"""
        print("\n" + "="*80)
        print("🚀 TOKOPEDIA AFFILIATOR SCRAPER")
        print("="*80 + "\n")
        
        # Load and validate cookies
        self.load_cookies()
        self.validate_cookies()
        
        print("="*80)
        print("📊 SCRAPING STARTED")
        print("="*80 + "\n")
        
        total_scraped = 0
        total_with_contact = 0
        
        # Scrape pages
        for page in range(1, max_pages + 1):
            affiliators = self.scrape_list_page(page)
            
            if not affiliators:
                print("⚠️  No affiliators found, stopping...\n")
                break
            
            # Scrape detail for each
            for i, affiliator in enumerate(affiliators, 1):
                print(f"\n[{i}/{len(affiliators)}] {affiliator.get('username', 'Unknown')}")
                
                detail_url = affiliator.get('detail_url')
                if detail_url:
                    # Add delay to avoid rate limiting
                    time.sleep(2)
                    
                    contacts = self.scrape_detail_page(detail_url)
                    affiliator.update(contacts)
                    
                    if contacts.get('whatsapp') or contacts.get('email'):
                        total_with_contact += 1
                
                self.results.append(affiliator)
                total_scraped += 1
            
            # Delay between pages
            if page < max_pages:
                print(f"\n⏳ Waiting 5 seconds before next page...")
                time.sleep(5)
        
        # Save results
        self.save_results()
        
        # Summary
        print("\n" + "="*80)
        print("✅ SCRAPING COMPLETED")
        print("="*80)
        print(f"Total affiliators scraped: {total_scraped}")
        print(f"With contact info: {total_with_contact} ({total_with_contact/total_scraped*100:.1f}%)")
        print(f"Results saved to: output/affiliators.json")
        print("="*80 + "\n")
    
    def save_results(self):
        """Save results to JSON file"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / "affiliators.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(self.results)} results to {output_file}")
    
    def _extract_text(self, element, xpath: str) -> Optional[str]:
        """Extract text from element using xpath"""
        try:
            results = element.xpath(xpath)
            if results:
                text = results[0].text_content().strip()
                return text if text else None
        except:
            pass
        return None
    
    def _extract_href(self, element, xpath: str) -> Optional[str]:
        """Extract href from element using xpath"""
        try:
            results = element.xpath(xpath)
            if results:
                href = results[0].get('href')
                if href and not href.startswith('http'):
                    href = self.base_url + href
                return href
        except:
            pass
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape Tokopedia Affiliator Data')
    parser.add_argument(
        '--cookie-file',
        default='config/cookies.json',
        help='Path ke file cookies (default: config/cookies.json)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=1,
        help='Maximum pages to scrape (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Check if cookie file exists
    if not Path(args.cookie_file).exists():
        print("\n❌ Cookie file tidak ditemukan!")
        print("\n💡 Langkah-langkah:")
        print("1. python extract_cookies.py  # Lihat panduan")
        print("2. Extract cookies dari Chrome")
        print("3. python validate_cookies.py  # Validasi cookies")
        print("4. python scrape_affiliators.py  # Mulai scraping\n")
        sys.exit(1)
    
    # Run scraper
    scraper = TokopediaAffiliatorScraper(args.cookie_file)
    scraper.scrape(max_pages=args.max_pages)


if __name__ == "__main__":
    main()
