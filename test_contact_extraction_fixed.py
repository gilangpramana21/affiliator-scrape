#!/usr/bin/env python3
"""
Test contact extraction with proper waiting for lazy-loaded elements
"""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.proxy.proxy_manager import ProxyManager


async def main():
    print("🧪 TEST CONTACT EXTRACTION - LAZY LOADING FIX")
    print("=" * 60)
    print("Strategy:")
    print("  1. Wait for page to fully load")
    print("  2. Wait for WhatsApp/Email icons to appear")
    print("  3. Click icons to reveal contact info")
    print("  4. Extract contact data")
    print("=" * 60)
    
    # Setup proxy
    print("\n🌐 Setting up proxy...")
    proxy_manager = ProxyManager()
    proxy_manager.load_webshare_proxies("config/webshare_proxies.txt")
    proxy_manager.validate_all_proxies()
    
    proxy = proxy_manager.get_random_proxy()
    proxy_config = proxy.to_playwright_format() if proxy else None
    
    if proxy:
        print(f"✅ Using proxy: {proxy}")
    else:
        print("⚠️  No proxy, using direct connection")
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(
            fingerprint, 
            headless=False,
            proxy=proxy_config
        )
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
        url = "https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259"
        print(f"\n🌐 Navigating to list page...")
        
        page = await browser_engine.navigate(url)
        await asyncio.sleep(5)
        
        print("\n⏸️  List page loaded")
        print("   Check browser: Do you see the creator list?")
        input("Press Enter to continue...")
        
        # Get first creator by clicking first row
        print("\n🖱️  Clicking first creator...")
        rows = await page.query_selector_all("tbody tr")
        
        if not rows:
            print("❌ No rows found")
            return
        
        print(f"   Found {len(rows)} rows")
        
        # Listen for new page
        new_page_promise = browser_engine.context.wait_for_event("page")
        
        # Click first row
        await rows[0].click()
        
        try:
            # Wait for detail page
            detail_page = await asyncio.wait_for(new_page_promise, timeout=15.0)
            print(f"✅ Detail page opened")
            
            # Wait for page to load
            await detail_page.wait_for_load_state("domcontentloaded", timeout=20000)
            print(f"✅ Page DOM loaded")
            
            # CRITICAL: Wait for lazy-loaded content
            print(f"\n⏳ Waiting for lazy-loaded content (icons, images, etc.)...")
            await asyncio.sleep(10)  # Give time for lazy loading
            
            # Wait for network to be idle (all resources loaded)
            try:
                await detail_page.wait_for_load_state("networkidle", timeout=15000)
                print(f"✅ Network idle - all resources loaded")
            except:
                print(f"⚠️  Network not idle, but continuing...")
            
            print(f"\n⏸️  Detail page should be fully loaded now")
            print(f"   Check browser: Do you see WhatsApp and Email icons?")
            input("Press Enter to search for contact elements...")
            
            # Search for WhatsApp elements
            print(f"\n🔍 SEARCHING FOR CONTACT ELEMENTS...")
            
            # Strategy 1: Look for images with WhatsApp/social media
            all_images = await detail_page.query_selector_all("img")
            print(f"   Found {len(all_images)} images total")
            
            whatsapp_images = []
            email_images = []
            social_images = []
            
            for img in all_images:
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                title = await img.get_attribute("title") or ""
                
                combined = (src + alt + title).lower()
                
                if "whatsapp" in combined or "wa" in combined:
                    whatsapp_images.append(img)
                    print(f"   ✅ Found WhatsApp image: src={src[:50]}, alt={alt}")
                
                if "email" in combined or "mail" in combined:
                    email_images.append(img)
                    print(f"   ✅ Found Email image: src={src[:50]}, alt={alt}")
                
                if "social" in combined or "contact" in combined:
                    social_images.append(img)
            
            print(f"\n📊 Image Summary:")
            print(f"   WhatsApp images: {len(whatsapp_images)}")
            print(f"   Email images: {len(email_images)}")
            print(f"   Social images: {len(social_images)}")
            
            # Strategy 2: Look for clickable elements (buttons, links)
            all_buttons = await detail_page.query_selector_all("button, a, [role='button']")
            print(f"\n   Found {len(all_buttons)} clickable elements")
            
            # Strategy 3: Look for SVG icons
            all_svgs = await detail_page.query_selector_all("svg")
            print(f"   Found {len(all_svgs)} SVG icons")
            
            # Strategy 4: Search page text for phone numbers
            page_text = await detail_page.text_content("body")
            phone_pattern = r'(\+62|62|0)[\s-]?8[\d\s-]{8,12}'
            phones_in_text = re.findall(phone_pattern, page_text)
            
            print(f"\n📱 Phone numbers in page text: {len(phones_in_text)}")
            for i, phone in enumerate(phones_in_text[:5]):
                print(f"   {i+1}. {phone}")
            
            # Try clicking WhatsApp icon if found
            if whatsapp_images:
                print(f"\n🖱️  Trying to click WhatsApp icon...")
                try:
                    # Get parent element (might be clickable)
                    wa_img = whatsapp_images[0]
                    
                    # Try clicking the image
                    await wa_img.click()
                    print(f"   ✅ Clicked WhatsApp icon")
                    
                    # Wait for modal/popup
                    await asyncio.sleep(3)
                    
                    # Check for new content
                    new_text = await detail_page.text_content("body")
                    new_phones = re.findall(phone_pattern, new_text)
                    
                    print(f"   After click: Found {len(new_phones)} phone numbers")
                    for phone in new_phones[:5]:
                        print(f"      - {phone}")
                    
                except Exception as e:
                    print(f"   ⚠️  Click failed: {e}")
                    
                    # Try clicking parent element
                    try:
                        parent = await wa_img.evaluate_handle("el => el.parentElement")
                        await parent.as_element().click()
                        print(f"   ✅ Clicked parent element")
                        await asyncio.sleep(3)
                    except:
                        print(f"   ⚠️  Parent click also failed")
            
            # Manual inspection
            print(f"\n⏸️  Browser will stay open for manual inspection")
            print(f"   Please:")
            print(f"   1. Look for WhatsApp icon in the browser")
            print(f"   2. Click it manually")
            print(f"   3. See if contact info appears")
            print(f"   4. Note where the contact info is displayed")
            
            input("\nPress Enter after manual inspection...")
            
            # Final text extraction
            final_text = await detail_page.text_content("body")
            final_phones = re.findall(phone_pattern, final_text)
            
            print(f"\n📊 FINAL EXTRACTION:")
            print(f"   Phone numbers found: {len(final_phones)}")
            for i, phone in enumerate(final_phones[:10]):
                print(f"   {i+1}. {phone}")
            
            # Save page HTML for analysis
            html = await detail_page.content()
            with open("detail_page_with_contacts.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n💾 HTML saved to: detail_page_with_contacts.html")
            
            await detail_page.close()
            
        except asyncio.TimeoutError:
            print("❌ Detail page did not open (timeout)")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")
    
    finally:
        await browser_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
