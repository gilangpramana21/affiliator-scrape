#!/usr/bin/env python3
"""Script untuk navigasi manual mencari halaman creator"""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager

async def manual_navigation():
    print("🔍 Manual navigation to find creator pages...")
    
    # Generate fingerprint
    generator = FingerprintGenerator()
    fingerprint = generator.generate()
    
    # Setup browser
    engine = BrowserEngine()
    await engine.launch(fingerprint, headless=False)
    
    # Load cookies
    session_manager = SessionManager()
    session_manager.load_session("config/cookies.json")
    
    # Start from main page
    base_url = "https://affiliate-id.tokopedia.com"
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
    
    print("✅ Browser ready for manual navigation")
    print(f"📄 Current URL: {page.url}")
    
    while True:
        print("\n" + "="*60)
        print("🔍 MANUAL NAVIGATION HELPER")
        print("="*60)
        
        # Get current page info
        current_url = page.url
        title = await page.title()
        print(f"📄 Current URL: {current_url}")
        print(f"📄 Page title: {title}")
        
        # Check for creator elements on current page
        print("\n🔍 Checking current page for creators...")
        
        creator_selectors = [
            "div[class*='creator']",
            "div[class*='affiliate']", 
            "div[class*='card']",
            ".card",
            "article",
            "[data-testid*='creator']",
            "[data-testid*='card']"
        ]
        
        found_any = False
        for selector in creator_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 2:  # More than just navigation elements
                    print(f"  ✅ Found {len(elements)} elements: {selector}")
                    found_any = True
                    
                    # Sample first element
                    sample_text = await elements[0].inner_text()
                    if len(sample_text.strip()) > 10:
                        print(f"    Sample: {sample_text[:80]}...")
                        
                        # Check for links
                        links = await elements[0].query_selector_all("a")
                        if links:
                            for link in links[:2]:
                                href = await link.get_attribute("href")
                                link_text = await link.inner_text()
                                if href and link_text.strip():
                                    print(f"    🔗 '{link_text.strip()[:30]}' -> {href}")
            except:
                pass
        
        if not found_any:
            print("  ❌ No creator elements found on this page")
        
        # Interactive menu
        print("\n📋 OPTIONS:")
        print("1. ✅ This page has creators - analyze structure")
        print("2. 🔍 Check all links on this page")
        print("3. 🌐 Navigate to specific URL")
        print("4. 📸 Take screenshot")
        print("5. 🔄 Refresh page")
        print("6. ❌ Exit")
        
        choice = input("\nChoose option (1-6): ").strip()
        
        if choice == "1":
            # Analyze current page structure
            print("\n🔍 ANALYZING PAGE STRUCTURE...")
            
            # Find all potential creator containers
            all_selectors = [
                "div", "article", "section", "li", "tr",
                "[class*='creator']", "[class*='affiliate']", "[class*='card']",
                "[data-testid*='creator']", "[data-testid*='card']"
            ]
            
            for selector in all_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if 5 <= len(elements) <= 50:  # Reasonable number for creator list
                        print(f"\n📋 Analyzing {len(elements)} elements: {selector}")
                        
                        # Check first few elements
                        for i, elem in enumerate(elements[:3]):
                            text = await elem.inner_text()
                            if 20 <= len(text.strip()) <= 500:  # Reasonable content length
                                print(f"  Element {i+1}: {text[:100]}...")
                                
                                # Look for profile links
                                links = await elem.query_selector_all("a")
                                for link in links:
                                    href = await link.get_attribute("href")
                                    if href and ('profile' in href or 'creator' in href or 'user' in href):
                                        print(f"    🎯 Profile link: {href}")
                except:
                    pass
            
            # Save current URL as working config
            print(f"\n💾 Current URL can be used as:")
            print(f"   base_url: {base_url}")
            print(f"   list_page_url: {current_url.replace(base_url, '')}")
            
        elif choice == "2":
            # Check all links
            print("\n🔍 CHECKING ALL LINKS...")
            
            links = await page.query_selector_all("a")
            creator_links = []
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    
                    if href and text:
                        text = text.strip()
                        # Look for creator-related links
                        if any(keyword in text.lower() for keyword in ['creator', 'kreator', 'jelajahi', 'explore', 'discover', 'cari', 'temukan']):
                            creator_links.append((text, href))
                        elif any(keyword in href.lower() for keyword in ['creator', 'explore', 'discover', 'browse', 'search']):
                            creator_links.append((text, href))
                except:
                    pass
            
            print(f"Found {len(creator_links)} potential creator links:")
            for i, (text, href) in enumerate(creator_links[:10]):
                print(f"  {i+1}. '{text}' -> {href}")
            
            if creator_links:
                try:
                    choice_num = input(f"\nNavigate to link (1-{min(10, len(creator_links))}) or Enter to skip: ").strip()
                    if choice_num.isdigit():
                        idx = int(choice_num) - 1
                        if 0 <= idx < len(creator_links):
                            _, href = creator_links[idx]
                            if not href.startswith('http'):
                                href = base_url + href
                            print(f"🌐 Navigating to: {href}")
                            await page.goto(href, wait_until="networkidle")
                except:
                    pass
        
        elif choice == "3":
            # Navigate to specific URL
            url = input("Enter URL (or path starting with /): ").strip()
            if url:
                if not url.startswith('http'):
                    url = base_url + url
                try:
                    print(f"🌐 Navigating to: {url}")
                    await page.goto(url, wait_until="networkidle")
                except Exception as e:
                    print(f"❌ Navigation failed: {e}")
        
        elif choice == "4":
            # Take screenshot
            filename = f"manual_nav_{len(current_url.split('/'))}.png"
            await page.screenshot(path=filename)
            print(f"📸 Screenshot saved: {filename}")
        
        elif choice == "5":
            # Refresh page
            print("🔄 Refreshing page...")
            await page.reload(wait_until="networkidle")
        
        elif choice == "6":
            # Exit
            break
        
        else:
            print("❌ Invalid choice")
    
    await engine.close()
    print("✅ Manual navigation completed")

if __name__ == "__main__":
    asyncio.run(manual_navigation())