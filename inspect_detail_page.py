#!/usr/bin/env python3
"""
Inspect detail page HTML to find where contact info is hidden
"""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager


async def inspect_page():
    """Inspect detail page to find contact elements."""
    
    print("🔍 INSPECTING DETAIL PAGE HTML")
    print("=" * 60)
    
    # Setup
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session("config/cookies.json")
        cookies = session_manager.get_cookies()
        
        if cookies:
            cookie_list = []
            for cookie in cookies:
                cookie_list.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'httpOnly': cookie.http_only,
                    'secure': cookie.secure
                })
            await browser_engine.context.add_cookies(cookie_list)
            print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        list_url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        
        print(f"\n🌐 Navigating to list page...")
        page = await browser_engine.navigate(list_url)
        await asyncio.sleep(3)
        
        # Click first row
        print(f"\n🖱️  Clicking first creator...")
        rows = await page.query_selector_all("tbody tr")
        
        if not rows:
            print("❌ No rows found")
            return
        
        # Listen for new page
        new_page_promise = browser_engine.context.wait_for_event("page")
        await rows[0].click()
        
        try:
            # Wait for detail page
            detail_page = await asyncio.wait_for(new_page_promise, timeout=10.0)
            print(f"✅ Detail page opened")
            
            await detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            print(f"\n📄 Detail URL: {detail_page.url}")
            
            # Save HTML for inspection
            html = await detail_page.content()
            with open("detail_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"💾 HTML saved to: detail_page.html")
            
            # Search for all clickable elements
            print(f"\n🔍 SEARCHING FOR CLICKABLE ELEMENTS...")
            
            # All buttons
            buttons = await detail_page.query_selector_all("button")
            print(f"   Found {len(buttons)} buttons")
            for i, btn in enumerate(buttons[:10]):
                text = await btn.text_content()
                class_name = await btn.get_attribute("class")
                print(f"   Button {i+1}: text='{text[:30]}', class='{class_name[:50] if class_name else 'None'}'")
            
            # All images
            images = await detail_page.query_selector_all("img")
            print(f"\n   Found {len(images)} images")
            for i, img in enumerate(images[:10]):
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                print(f"   Image {i+1}: src='{src[:50] if src else 'None'}', alt='{alt}'")
            
            # All links
            links = await detail_page.query_selector_all("a")
            print(f"\n   Found {len(links)} links")
            for i, link in enumerate(links[:10]):
                href = await link.get_attribute("href")
                text = await link.text_content()
                print(f"   Link {i+1}: href='{href[:50] if href else 'None'}', text='{text[:30]}'")
            
            # All SVG (icons)
            svgs = await detail_page.query_selector_all("svg")
            print(f"\n   Found {len(svgs)} SVG icons")
            
            # All divs with specific classes
            contact_divs = await detail_page.query_selector_all("[class*='contact'], [class*='social'], [class*='info']")
            print(f"\n   Found {len(contact_divs)} divs with contact/social/info classes")
            for i, div in enumerate(contact_divs[:5]):
                class_name = await div.get_attribute("class")
                text = await div.text_content()
                print(f"   Div {i+1}: class='{class_name[:50]}', text='{text[:50]}'")
            
            # Search for text containing "WhatsApp", "Kontak", "Hubungi"
            print(f"\n🔍 SEARCHING FOR CONTACT-RELATED TEXT...")
            page_text = await detail_page.text_content("body")
            
            keywords = ["WhatsApp", "whatsapp", "WA", "Kontak", "kontak", "Hubungi", "hubungi", "Telepon", "telepon", "Email", "email"]
            for keyword in keywords:
                if keyword in page_text:
                    print(f"   ✅ Found keyword: '{keyword}'")
                    # Find context around keyword
                    idx = page_text.find(keyword)
                    context = page_text[max(0, idx-50):min(len(page_text), idx+100)]
                    print(f"      Context: ...{context}...")
            
            print(f"\n⏸️  Browser will stay open for 60 seconds...")
            print(f"   Please manually inspect the page and look for:")
            print(f"   1. WhatsApp icon/button")
            print(f"   2. Contact information section")
            print(f"   3. Social media icons")
            print(f"   4. Any clickable elements that might reveal contact info")
            print(f"\n   Then check detail_page.html file for HTML structure")
            
            await asyncio.sleep(60)
            
            await detail_page.close()
            
        except asyncio.TimeoutError:
            print("❌ Detail page did not open (timeout)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(inspect_page())
