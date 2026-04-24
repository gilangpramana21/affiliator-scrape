#!/usr/bin/env python3
"""Script untuk mencari dan mengidentifikasi logo WhatsApp dan Email di halaman detail."""

import asyncio
from src.anti_detection.browser_engine import BrowserEngine
from src.anti_detection.fingerprint_generator import FingerprintGenerator
from src.core.session_manager import SessionManager
from src.models.config import Configuration

async def find_contact_icons():
    """Mencari logo WhatsApp dan Email di halaman detail creator."""
    
    print("🔍 CONTACT ICONS FINDER")
    print("=" * 40)
    
    # Load config
    config = Configuration.from_file("config/config_jelajahi.json")
    
    # Setup components
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate()
    browser_engine = BrowserEngine()
    session_manager = SessionManager()
    
    try:
        # Launch browser
        await browser_engine.launch(fingerprint, headless=False)
        print("✅ Browser launched")
        
        # Load cookies
        session_manager.load_session(config.cookie_file)
        cookies = session_manager.get_cookies()
        print(f"✅ Loaded {len(cookies)} cookies")
        
        # Navigate to list page
        url = f"{config.base_url}{config.list_page_url}{config.list_page_query}"
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
        
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print("✅ Page loaded")
        
        print("\n🎯 INSTRUCTIONS:")
        print("1. Browser window is open")
        print("2. Click on any creator to go to detail page")
        print("3. Look for the green WhatsApp icon and blue Email icon")
        print("4. Note their position (near username, in header, etc.)")
        print("5. Press Enter when you're on a creator detail page...")
        
        input()
        
        # Analyze current page
        current_url = page.url
        print(f"\n📊 Current URL: {current_url}")
        
        # Check if we're on detail page
        if 'creator' not in current_url and 'profile' not in current_url:
            print("⚠️  Not on creator detail page. Please navigate to a creator first.")
            print("   Press Enter to continue...")
            input()
        
        print(f"\n🔍 SCANNING FOR ALL CLICKABLE ELEMENTS:")
        
        # Get all clickable elements
        clickable_selectors = [
            'a', 'button', 'div[onclick]', 'span[onclick]',
            'img[onclick]', 'svg[onclick]', '[role="button"]'
        ]
        
        all_clickables = []
        
        for selector in clickable_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        # Get element info
                        tag_name = await element.evaluate('el => el.tagName')
                        class_name = await element.get_attribute('class') or ''
                        id_attr = await element.get_attribute('id') or ''
                        href = await element.get_attribute('href') or ''
                        onclick = await element.get_attribute('onclick') or ''
                        
                        # Get text content
                        try:
                            text = await element.inner_text()
                            text = text.strip()[:50]
                        except:
                            text = ''
                        
                        # Check if it might be contact-related
                        is_contact_related = any(keyword in (class_name + id_attr + href + onclick + text).lower() 
                                                for keyword in ['whatsapp', 'wa', 'email', 'mail', 'contact', 'kontak'])
                        
                        if is_contact_related:
                            all_clickables.append({
                                'tag': tag_name,
                                'class': class_name,
                                'id': id_attr,
                                'href': href,
                                'text': text,
                                'selector': selector
                            })
                    except:
                        continue
            except:
                continue
        
        if all_clickables:
            print(f"   ✅ Found {len(all_clickables)} contact-related clickable elements:")
            for i, elem in enumerate(all_clickables[:10], 1):  # Show first 10
                print(f"\n   {i}. {elem['tag']}")
                if elem['class']:
                    print(f"      class: {elem['class'][:50]}")
                if elem['id']:
                    print(f"      id: {elem['id']}")
                if elem['href']:
                    print(f"      href: {elem['href'][:50]}")
                if elem['text']:
                    print(f"      text: {elem['text']}")
        else:
            print("   ❌ No contact-related clickable elements found")
        
        # Look for all images and SVGs (icons)
        print(f"\n🔍 SCANNING FOR ICONS (IMG & SVG):")
        
        icon_selectors = ['img', 'svg']
        all_icons = []
        
        for selector in icon_selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"   Found {len(elements)} {selector} elements")
                
                for element in elements[:20]:  # Check first 20
                    try:
                        if selector == 'img':
                            src = await element.get_attribute('src') or ''
                            alt = await element.get_attribute('alt') or ''
                            
                            # Check if it's contact-related
                            if any(keyword in (src + alt).lower() for keyword in ['whatsapp', 'wa', 'email', 'mail', 'contact']):
                                all_icons.append({
                                    'type': 'img',
                                    'src': src[:50],
                                    'alt': alt
                                })
                        else:  # svg
                            class_name = await element.get_attribute('class') or ''
                            
                            if any(keyword in class_name.lower() for keyword in ['whatsapp', 'wa', 'email', 'mail', 'contact']):
                                all_icons.append({
                                    'type': 'svg',
                                    'class': class_name
                                })
                    except:
                        continue
            except:
                continue
        
        if all_icons:
            print(f"   ✅ Found {len(all_icons)} contact-related icons:")
            for i, icon in enumerate(all_icons, 1):
                print(f"\n   {i}. {icon['type']}")
                if icon['type'] == 'img':
                    print(f"      src: {icon['src']}")
                    print(f"      alt: {icon['alt']}")
                else:
                    print(f"      class: {icon['class']}")
        else:
            print("   ❌ No contact-related icons found")
        
        # Look for circular colored elements (like in screenshot)
        print(f"\n🔍 SCANNING FOR COLORED CIRCLES (WhatsApp green, Email blue):")
        
        # Get all elements and check their computed styles
        try:
            # Look for elements with background colors
            colored_elements = await page.evaluate('''() => {
                const elements = document.querySelectorAll('*');
                const results = [];
                
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const bgColor = style.backgroundColor;
                    const borderRadius = style.borderRadius;
                    
                    // Check for green (WhatsApp) or blue (Email) backgrounds
                    if ((bgColor.includes('25, 211, 55') || // WhatsApp green
                         bgColor.includes('rgb(37, 211, 55)') ||
                         bgColor.includes('#25d337') ||
                         bgColor.includes('0, 168, 255') || // Email blue
                         bgColor.includes('rgb(0, 168, 255)') ||
                         bgColor.includes('#00a8ff')) &&
                        borderRadius !== '0px') {
                        
                        results.push({
                            tag: el.tagName,
                            class: el.className,
                            id: el.id,
                            bgColor: bgColor,
                            borderRadius: borderRadius,
                            text: el.innerText ? el.innerText.substring(0, 30) : ''
                        });
                    }
                });
                
                return results;
            }''')
            
            if colored_elements:
                print(f"   ✅ Found {len(colored_elements)} colored circle elements:")
                for i, elem in enumerate(colored_elements, 1):
                    print(f"\n   {i}. {elem['tag']}")
                    print(f"      class: {elem['class']}")
                    print(f"      bgColor: {elem['bgColor']}")
                    print(f"      borderRadius: {elem['borderRadius']}")
                    if elem['text']:
                        print(f"      text: {elem['text']}")
            else:
                print("   ❌ No colored circle elements found")
        except Exception as e:
            print(f"   ⚠️  Error scanning colored elements: {e}")
        
        # Interactive testing
        print(f"\n🖱️  INTERACTIVE TESTING:")
        print("   Now you can manually click on the WhatsApp and Email icons")
        print("   to see what happens and identify the correct selectors.")
        print("   Press Enter when done...")
        input()
        
        # Final recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("   Based on the scan results above:")
        if all_clickables:
            print("   ✅ Use clickable elements with contact-related attributes")
        if all_icons:
            print("   ✅ Use icon elements (img/svg) with contact-related attributes")
        if colored_elements:
            print("   ✅ Use colored circle elements (green for WhatsApp, blue for Email)")
        
        print("\n   📝 Next steps:")
        print("   1. Identify the exact selectors for WhatsApp and Email icons")
        print("   2. Update the scraper to use those selectors")
        print("   3. Test clicking those elements to reveal contact info")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n⏳ Press Enter to close...")
        input()
        await browser_engine.close()

if __name__ == "__main__":
    asyncio.run(find_contact_icons())