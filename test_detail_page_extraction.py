#!/usr/bin/env python3
"""Test extraction dari halaman detail creator untuk mendapatkan WhatsApp dan email."""

import asyncio
import json
import re
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.html_parser import HTMLParser
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def test_detail_page_extraction():
    """Test extraction data kontak dari halaman detail creator."""
    
    print("📱 Testing Detail Page Contact Extraction")
    print("=" * 50)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup browser
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    parser = HTMLParser()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)  # Visible untuk debugging
        print("✅ Browser launched (visible mode)")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
        print(f"🌐 Navigating to list page: {url}")
        
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
        print("✅ List page loaded with cookies")
        
        # Get HTML and find creator rows
        html = await browser_engine.get_html(page)
        doc = parser.parse(html)
        
        # Find table rows (skip header)
        rows = parser.select(doc, "tr")
        data_rows = rows[1:3] if len(rows) > 1 else []  # Test first 2 creators only
        
        print(f"🔍 Found {len(data_rows)} creator rows to test")
        
        extracted_contacts = []
        
        for i, row in enumerate(data_rows, 1):
            print(f"\n👤 Processing Creator {i}...")
            
            try:
                # Extract username from row first
                cells = parser.select(row, "td")
                if len(cells) < 2:
                    print(f"   ❌ Not enough cells in row {i}")
                    continue
                
                # Get creator data from main span
                main_spans = parser.select(cells[1], "span.arco-table-cell-wrap-value")
                if not main_spans:
                    print(f"   ❌ No main data span in row {i}")
                    continue
                
                main_text = parser.get_text(main_spans[0])
                username_match = re.match(r'^([^L]+?)Lv\.', main_text)
                username = username_match.group(1) if username_match else f"creator_{i}"
                
                print(f"   📝 Username: {username}")
                
                # Look for clickable elements in the row
                clickable_elements = []
                
                # Try different approaches to find clickable elements
                for cell in cells:
                    # Look for any clickable elements
                    links = parser.select(cell, "a")
                    buttons = parser.select(cell, "button")
                    clickable = parser.select(cell, "[onclick]")
                    
                    clickable_elements.extend(links)
                    clickable_elements.extend(buttons)
                    clickable_elements.extend(clickable)
                
                print(f"   🔗 Found {len(clickable_elements)} clickable elements")
                
                # Try to click the first clickable element or the row itself
                clicked = False
                
                # Method 1: Try clicking clickable elements
                for elem_index, elem in enumerate(clickable_elements):
                    try:
                        # Convert to Playwright element
                        elem_text = parser.get_text(elem)[:20]
                        print(f"   🖱️  Trying to click element {elem_index}: '{elem_text}'")
                        
                        # Find the element on the page and click it
                        # This is tricky - we need to find the element by its content or position
                        # For now, let's try clicking the row itself
                        break
                    except Exception as e:
                        print(f"   ⚠️  Failed to click element {elem_index}: {e}")
                        continue
                
                # Method 2: Try clicking the row itself
                if not clicked:
                    try:
                        print(f"   🖱️  Trying to click row {i} directly...")
                        
                        # Get all rows on the page
                        page_rows = await page.query_selector_all("tr")
                        if len(page_rows) > i:  # i is 1-based, but we need 0-based + 1 for header
                            target_row = page_rows[i]  # Skip header row
                            await target_row.click()
                            clicked = True
                            print(f"   ✅ Clicked row {i}")
                        
                    except Exception as e:
                        print(f"   ⚠️  Failed to click row {i}: {e}")
                
                if not clicked:
                    print(f"   ❌ Could not click creator {i}, skipping...")
                    continue
                
                # Wait for navigation or modal to appear
                await asyncio.sleep(3)
                
                # Check if we're on a detail page or if a modal appeared
                current_url = page.url
                print(f"   🌐 Current URL: {current_url}")
                
                # Get the new page content
                detail_html = await browser_engine.get_html(page)
                detail_doc = parser.parse(detail_html)
                
                # Extract contact information
                contact_info = await extract_contact_info(detail_doc, parser)
                
                if contact_info['whatsapp'] or contact_info['email']:
                    print(f"   ✅ Contact info found!")
                    print(f"      WhatsApp: {contact_info['whatsapp']}")
                    print(f"      Email: {contact_info['email']}")
                    
                    extracted_contacts.append({
                        'username': username,
                        'whatsapp': contact_info['whatsapp'],
                        'email': contact_info['email'],
                        'detail_url': current_url
                    })
                else:
                    print(f"   ❌ No contact info found")
                
                # Go back to list page if we navigated away
                if current_url != url:
                    print(f"   ⬅️  Going back to list page...")
                    await page.go_back()
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error processing creator {i}: {e}")
                continue
        
        # Save results
        if extracted_contacts:
            with open('creator_contacts.json', 'w', encoding='utf-8') as f:
                json.dump(extracted_contacts, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Saved {len(extracted_contacts)} contacts to creator_contacts.json")
        
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   Total creators processed: {len(data_rows)}")
        print(f"   Contacts extracted: {len(extracted_contacts)}")
        print(f"   Success rate: {len(extracted_contacts)/len(data_rows)*100:.1f}%" if data_rows else "0%")
        
        print("\n⏳ Browser window open for manual inspection...")
        print("   Check the results and page behavior...")
        print("   Press Enter when done...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error during detail extraction: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_engine.close()

async def extract_contact_info(doc, parser):
    """Extract WhatsApp and email from detail page."""
    
    contact_info = {
        'whatsapp': None,
        'email': None
    }
    
    # Look for WhatsApp
    whatsapp_selectors = [
        "span:contains('WhatsApp')",
        "div:contains('WhatsApp')",
        "*[data-testid*='whatsapp']",
        "span:contains('085')",  # Indonesian phone pattern
        "span:contains('08')",
        "div:contains('08')"
    ]
    
    for selector in whatsapp_selectors:
        try:
            elements = parser.select(doc, selector)
            for elem in elements:
                text = parser.get_text(elem)
                # Look for phone number pattern
                phone_match = re.search(r'(08\d{8,12}|\+62\d{8,12}|62\d{8,12})', text)
                if phone_match:
                    contact_info['whatsapp'] = phone_match.group(1)
                    break
            if contact_info['whatsapp']:
                break
        except:
            continue
    
    # Look for Email
    email_selectors = [
        "span:contains('Email')",
        "div:contains('Email')",
        "*[data-testid*='email']",
        "span:contains('@')",
        "div:contains('@')"
    ]
    
    for selector in email_selectors:
        try:
            elements = parser.select(doc, selector)
            for elem in elements:
                text = parser.get_text(elem)
                # Look for email pattern
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                if email_match:
                    contact_info['email'] = email_match.group(0)
                    break
            if contact_info['email']:
                break
        except:
            continue
    
    return contact_info

if __name__ == "__main__":
    asyncio.run(test_detail_page_extraction())