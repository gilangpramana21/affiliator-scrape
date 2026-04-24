#!/usr/bin/env python3
"""Test sederhana untuk menemukan cara navigasi ke halaman detail creator."""

import asyncio
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_simple_navigation():
    """Test sederhana untuk navigasi ke detail creator."""
    
    print("🔍 Simple Navigation Test to Creator Detail")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Navigating to: {url}")
        
        page = await browser_engine.navigate(url, wait_for="domcontentloaded")
        
        # Apply cookies
        for cookie in cookies:
            await page.context.add_cookies([{
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'httpOnly': cookie.http_only,
                'secure': cookie.secure
            }])
        
        # Reload with cookies
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded with cookies")
        
        print("\n🔍 SIMPLE ANALYSIS...")
        
        # Method 1: Check for any links in the page
        print("\n1️⃣ Looking for all links:")
        links = await page.query_selector_all("a")
        print(f"   Found {len(links)} links total")
        
        detail_links = []
        for i, link in enumerate(links):
            try:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and ("detail" in href or "creator" in href):
                    detail_links.append((href, text))
                    print(f"   🔗 Link {i}: '{text[:30]}' -> {href}")
            except:
                continue
        
        if detail_links:
            print(f"   ✅ Found {len(detail_links)} potential detail links!")
        else:
            print("   ❌ No detail links found")
        
        # Method 2: Look for creator names/usernames that might be clickable
        print("\n2️⃣ Looking for creator names in table:")
        
        rows = await page.query_selector_all("tr")
        print(f"   Found {len(rows)} table rows")
        
        for i, row in enumerate(rows[1:4], 1):  # Check first 3 data rows
            try:
                # Get row text
                row_text = await row.inner_text()
                print(f"\n   📋 Row {i}: {row_text[:100]}...")
                
                # Look for spans with creator data
                spans = await row.query_selector_all("span")
                print(f"      Found {len(spans)} spans")
                
                # Check if any spans are clickable
                for j, span in enumerate(spans[:5]):  # Check first 5 spans
                    try:
                        span_text = await span.inner_text()
                        if len(span_text) > 5 and not span_text.isdigit():  # Likely creator name
                            # Try to click this span
                            print(f"      🖱️  Trying to click span {j}: '{span_text[:20]}'")
                            
                            # Check if span has any click handlers
                            onclick = await span.get_attribute("onclick")
                            if onclick:
                                print(f"         Has onclick: {onclick}")
                            
                            # Try clicking
                            try:
                                await span.click()
                                await asyncio.sleep(2)
                                
                                # Check if URL changed
                                new_url = page.url
                                if new_url != url:
                                    print(f"         ✅ URL changed to: {new_url}")
                                    
                                    if "detail" in new_url:
                                        print("         🎉 Successfully navigated to detail page!")
                                        
                                        # Extract contact info
                                        await extract_contact_from_detail_page(page)
                                        
                                        # Go back
                                        await page.go_back()
                                        await asyncio.sleep(2)
                                        break
                                else:
                                    print(f"         ❌ No navigation occurred")
                            except Exception as e:
                                print(f"         ⚠️  Click failed: {e}")
                    except:
                        continue
                
            except Exception as e:
                print(f"      ❌ Error analyzing row {i}: {e}")
        
        # Method 3: Try direct URL construction
        print("\n3️⃣ Trying to construct detail URLs:")
        
        # From your screenshot, the URL pattern is:
        # /connection/creator/detail?cid=7493996444893472098&pair_source=author_recommend&center_from=affiliate_find_creat...
        
        # Look for creator IDs in page source
        page_content = await page.content()
        
        # Look for long numeric IDs
        id_matches = re.findall(r'\b\d{15,20}\b', page_content)
        unique_ids = list(set(id_matches))[:5]  # Get first 5 unique IDs
        
        print(f"   Found {len(unique_ids)} potential creator IDs:")
        for creator_id in unique_ids:
            print(f"      ID: {creator_id}")
            
            # Try constructing detail URL
            detail_url = f"{config.base_url}/connection/creator/detail?cid={creator_id}"
            print(f"      Trying URL: {detail_url}")
            
            try:
                await page.goto(detail_url)
                await asyncio.sleep(3)
                
                # Check if we got a valid detail page
                current_url = page.url
                page_title = await page.title()
                
                print(f"      Result URL: {current_url}")
                print(f"      Page title: {page_title}")
                
                if "detail" in current_url and "error" not in page_title.lower():
                    print("      ✅ Valid detail page found!")
                    
                    # Extract contact info
                    await extract_contact_from_detail_page(page)
                    
                    # Go back to list
                    await page.goto(url)
                    await asyncio.sleep(2)
                    break
                else:
                    print("      ❌ Invalid or error page")
                    
            except Exception as e:
                print(f"      ⚠️  Navigation failed: {e}")
        
        print("\n⏳ Browser window open for manual testing...")
        print("   Try manually clicking on creator names or any other elements")
        print("   Look for ways to access creator detail pages")
        print("   Press Enter when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during navigation test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()

async def extract_contact_from_detail_page(page):
    """Extract contact info from detail page."""
    
    print("      📱 Extracting contact info...")
    
    try:
        # Look for WhatsApp
        whatsapp_elements = await page.query_selector_all("text=WhatsApp")
        for elem in whatsapp_elements:
            try:
                # Get parent or nearby elements
                parent = await elem.query_selector("xpath=..")
                if parent:
                    text = await parent.inner_text()
                    phone_match = re.search(r'(08\d{8,12}|\+62\d{8,12}|62\d{8,12})', text)
                    if phone_match:
                        print(f"         📱 WhatsApp: {phone_match.group(1)}")
            except:
                continue
        
        # Look for Email
        email_elements = await page.query_selector_all("text=Email")
        for elem in email_elements:
            try:
                # Get parent or nearby elements
                parent = await elem.query_selector("xpath=..")
                if parent:
                    text = await parent.inner_text()
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    if email_match:
                        print(f"         📧 Email: {email_match.group(0)}")
            except:
                continue
        
        # Alternative: look for patterns in all text
        page_text = await page.inner_text("body")
        
        # WhatsApp pattern
        phone_matches = re.findall(r'(08\d{8,12}|\+62\d{8,12}|62\d{8,12})', page_text)
        if phone_matches:
            print(f"         📱 Phone numbers found: {phone_matches[:3]}")
        
        # Email pattern
        email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_text)
        if email_matches:
            print(f"         📧 Emails found: {email_matches[:3]}")
        
    except Exception as e:
        print(f"         ⚠️  Error extracting contact: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_navigation())