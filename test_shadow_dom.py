#!/usr/bin/env python3
"""
Test untuk detect dan extract data dari Shadow DOM
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🔍 SHADOW DOM DETECTOR & EXTRACTOR")
    print("=" * 60)
    print("Script ini akan:")
    print("  1. Buka detail page creator")
    print("  2. Detect Shadow DOM elements")
    print("  3. Extract contact info dari Shadow DOM")
    print("=" * 60)
    
    # Load cookies
    print("\n📂 Loading cookies...")
    try:
        with open('config/cookies.json', 'r') as f:
            cookies = json.load(f)
        print(f"✅ Loaded {len(cookies)} cookies")
    except:
        print("⚠️  No cookies found")
        cookies = []
    
    async with async_playwright() as p:
        print("\n🌐 Launching browser...")
        
        try:
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                args=['--disable-blink-features=AutomationControlled'],
                timeout=0
            )
        except:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                timeout=0
            )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(0)
        
        print("✅ Browser launched")
        
        if cookies:
            await context.add_cookies(cookies)
            print("✅ Cookies added")
        
        print("\n📝 INSTRUCTIONS:")
        print("   1. Navigate manual ke affiliate page")
        print("   2. Click salah satu creator untuk buka detail page")
        print("   3. Tunggu sampai page fully loaded")
        print("   4. Press Enter di terminal untuk analyze Shadow DOM")
        
        input("\nPress Enter when you're on a creator detail page...")
        
        print("\n🔍 Analyzing page structure...")
        
        # Get current URL
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Check for Shadow DOM
        print("\n🌑 Checking for Shadow DOM elements...")
        
        shadow_hosts = await page.evaluate("""
            () => {
                const hosts = [];
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(el => {
                    if (el.shadowRoot) {
                        hosts.push({
                            tagName: el.tagName,
                            className: el.className,
                            id: el.id,
                            innerHTML: el.innerHTML.substring(0, 100)
                        });
                    }
                });
                
                return hosts;
            }
        """)
        
        if len(shadow_hosts) > 0:
            print(f"✅ Found {len(shadow_hosts)} Shadow DOM hosts!")
            for i, host in enumerate(shadow_hosts[:5]):
                print(f"\n   Shadow Host {i+1}:")
                print(f"      Tag: {host['tagName']}")
                print(f"      Class: {host['className']}")
                print(f"      ID: {host['id']}")
        else:
            print("⚠️  No Shadow DOM detected")
        
        # Search for contact-related elements in Shadow DOM
        print("\n📱 Searching for contact info in Shadow DOM...")
        
        contact_data = await page.evaluate("""
            () => {
                const results = {
                    whatsapp: [],
                    email: [],
                    phone: [],
                    shadowElements: []
                };
                
                // Function to search in shadow DOM recursively
                function searchShadowDOM(root, depth = 0) {
                    if (depth > 5) return; // Limit recursion depth
                    
                    const elements = root.querySelectorAll('*');
                    
                    elements.forEach(el => {
                        // Check text content
                        const text = el.textContent || '';
                        const html = el.innerHTML || '';
                        
                        // Search for WhatsApp
                        if (text.match(/whatsapp|wa\\.me|\\+62\\s*8\\d{2}/i) || 
                            html.match(/whatsapp|wa\\.me/i)) {
                            results.whatsapp.push({
                                text: text.substring(0, 100),
                                tag: el.tagName,
                                class: el.className
                            });
                        }
                        
                        // Search for Email
                        if (text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/)) {
                            results.email.push({
                                text: text.substring(0, 100),
                                tag: el.tagName,
                                class: el.className
                            });
                        }
                        
                        // Search for Phone
                        if (text.match(/\\+?62\\s*8\\d{2}[\\s-]?\\d{3,4}[\\s-]?\\d{3,4}/)) {
                            results.phone.push({
                                text: text.substring(0, 100),
                                tag: el.tagName,
                                class: el.className
                            });
                        }
                        
                        // Recurse into shadow DOM
                        if (el.shadowRoot) {
                            searchShadowDOM(el.shadowRoot, depth + 1);
                        }
                    });
                }
                
                // Search in main document
                searchShadowDOM(document);
                
                // Also search in all shadow roots
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.shadowRoot) {
                        searchShadowDOM(el.shadowRoot);
                    }
                });
                
                return results;
            }
        """)
        
        print(f"\n📊 Contact Data Found:")
        print(f"   WhatsApp mentions: {len(contact_data['whatsapp'])}")
        print(f"   Email mentions: {len(contact_data['email'])}")
        print(f"   Phone mentions: {len(contact_data['phone'])}")
        
        if contact_data['whatsapp']:
            print("\n📱 WhatsApp data:")
            for i, wa in enumerate(contact_data['whatsapp'][:3]):
                print(f"   {i+1}. {wa['text'][:50]}...")
                print(f"      Tag: {wa['tag']}, Class: {wa['class']}")
        
        if contact_data['email']:
            print("\n📧 Email data:")
            for i, email in enumerate(contact_data['email'][:3]):
                print(f"   {i+1}. {email['text'][:50]}...")
        
        if contact_data['phone']:
            print("\n📞 Phone data:")
            for i, phone in enumerate(contact_data['phone'][:3]):
                print(f"   {i+1}. {phone['text'][:50]}...")
        
        # Search for clickable contact icons
        print("\n🖱️  Searching for clickable contact icons...")
        
        icons = await page.evaluate("""
            () => {
                const results = [];
                
                // Search for images with WhatsApp/social media
                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    const src = img.src || '';
                    const alt = img.alt || '';
                    
                    if (src.match(/whatsapp|wa|social|contact/i) || 
                        alt.match(/whatsapp|wa|social|contact/i)) {
                        results.push({
                            type: 'image',
                            src: src.substring(0, 100),
                            alt: alt,
                            visible: img.offsetParent !== null,
                            clickable: img.style.cursor === 'pointer' || 
                                      img.parentElement.tagName === 'A' ||
                                      img.parentElement.tagName === 'BUTTON'
                        });
                    }
                });
                
                // Search in Shadow DOM
                function searchShadowIcons(root) {
                    const images = root.querySelectorAll('img');
                    images.forEach(img => {
                        const src = img.src || '';
                        const alt = img.alt || '';
                        
                        if (src.match(/whatsapp|wa|social|contact/i) || 
                            alt.match(/whatsapp|wa|social|contact/i)) {
                            results.push({
                                type: 'shadow-image',
                                src: src.substring(0, 100),
                                alt: alt,
                                visible: img.offsetParent !== null
                            });
                        }
                    });
                    
                    // Recurse
                    root.querySelectorAll('*').forEach(el => {
                        if (el.shadowRoot) {
                            searchShadowIcons(el.shadowRoot);
                        }
                    });
                }
                
                document.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) {
                        searchShadowIcons(el.shadowRoot);
                    }
                });
                
                return results;
            }
        """)
        
        print(f"\n🖼️  Found {len(icons)} contact-related icons")
        for i, icon in enumerate(icons[:5]):
            print(f"\n   Icon {i+1}:")
            print(f"      Type: {icon['type']}")
            print(f"      Src: {icon['src'][:60]}...")
            print(f"      Alt: {icon.get('alt', 'N/A')}")
            print(f"      Visible: {icon['visible']}")
            if 'clickable' in icon:
                print(f"      Clickable: {icon['clickable']}")
        
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        
        if len(shadow_hosts) > 0:
            print(f"✅ Shadow DOM detected: {len(shadow_hosts)} hosts")
        else:
            print("⚠️  No Shadow DOM detected")
        
        if contact_data['whatsapp'] or contact_data['email'] or contact_data['phone']:
            print("✅ Contact data found in page")
        else:
            print("⚠️  No contact data found")
        
        if len(icons) > 0:
            print(f"✅ Contact icons found: {len(icons)}")
        else:
            print("⚠️  No contact icons found")
        
        print("\n💡 Next steps:")
        if len(shadow_hosts) > 0:
            print("   - Contact data is likely in Shadow DOM")
            print("   - Need to pierce Shadow DOM to extract")
            print("   - Use Playwright's piercing selectors")
        else:
            print("   - Contact data might be lazy-loaded")
            print("   - Try clicking icons to reveal data")
            print("   - Or data might be loaded via JavaScript")
        
        input("\nPress Enter to close browser...")
        
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
