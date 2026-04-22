#!/usr/bin/env python3
"""Script untuk mencari URL halaman Jelajahi yang benar"""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager

async def find_jelajahi_url():
    print("🔍 Finding correct Jelajahi URL...")
    
    # Generate fingerprint
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    
    # Setup browser
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=False)
    
    # Load cookies
    session_manager = SessionManager()
    session_manager.load_session("config/cookies.json")
    
    # Start from main affiliate page
    base_url = "https://affiliate-id.tokopedia.com"
    print(f"🌐 Starting from: {base_url}")
    
    page = await engine.navigate(base_url, wait_for="networkidle")
    
    # Apply cookies
    cookies = session_manager.get_cookies()
    for cookie in cookies:
        await page.context.add_cookies([{
            'name': cookie.name,
            'value': cookie.value,
            'domain': cookie.domain,
            'path': cookie.path,
            'httpOnly': cookie.http_only,
            'secure': cookie.secure
        }])
    
    await page.reload(wait_until="networkidle")
    
    print("✅ Main page loaded")
    print(f"📄 Current URL: {page.url}")
    print(f"📄 Page title: {await page.title()}")
    
    # Look for navigation links
    print("\n🔍 Looking for navigation links...")
    
    # Common selectors for navigation
    nav_selectors = [
        "nav a",
        ".navigation a", 
        ".menu a",
        ".sidebar a",
        "a[href*='jelajahi']",
        "a[href*='explore']",
        "a[href*='discover']",
        "a[href*='creator']",
        "a[href*='browse']",
        "a:contains('Jelajahi')",
        "a:contains('Explore')",
        "a:contains('Discover')",
        "a:contains('Browse')",
        "a:contains('Cari')",
        "a:contains('Find')"
    ]
    
    found_links = []
    
    for selector in nav_selectors:
        try:
            links = await page.query_selector_all(selector)
            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and text:
                    text = text.strip()
                    if text and len(text) < 50:  # Reasonable link text length
                        found_links.append((text, href))
                        print(f"  🔗 '{text}' -> {href}")
        except:
            pass
    
    # Try some common URLs
    print("\n🔍 Testing common URLs...")
    
    test_urls = [
        "/connection/creator-discovery",
        "/creator/discovery", 
        "/creator/explore",
        "/creator/browse",
        "/jelajahi",
        "/explore",
        "/discover",
        "/browse",
        "/creator",
        "/creators",
        "/connection/explore",
        "/connection/browse",
        "/connection/search",
        "/search/creator"
    ]
    
    working_urls = []
    
    for test_url in test_urls:
        try:
            full_url = f"{base_url}{test_url}"
            print(f"  Testing: {full_url}")
            
            # Try to navigate
            response = await page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
            
            if response and response.status < 400:
                title = await page.title()
                print(f"    ✅ SUCCESS: {response.status} - {title}")
                working_urls.append((test_url, title))
            else:
                print(f"    ❌ Failed: {response.status if response else 'No response'}")
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:50]}...")
    
    # Show results
    print(f"\n📋 Found {len(working_urls)} working URLs:")
    for url, title in working_urls:
        print(f"  ✅ {url} -> {title}")
    
    print(f"\n📋 Found {len(found_links)} navigation links:")
    for text, href in found_links[:10]:  # Show first 10
        print(f"  🔗 '{text}' -> {href}")
    
    print("\n⏳ Browser window open for manual exploration...")
    print("   Navigate to find the correct Jelajahi/Explore page...")
    print("   Look for pages with creator cards or affiliate listings...")
    print("   Press Enter when you find the right page...")
    input()
    
    # Get final URL
    final_url = page.url
    final_title = await page.title()
    print(f"\n✅ Final URL: {final_url}")
    print(f"✅ Final title: {final_title}")
    
    await engine.close()
    print("✅ URL discovery completed")

if __name__ == "__main__":
    asyncio.run(find_jelajahi_url())