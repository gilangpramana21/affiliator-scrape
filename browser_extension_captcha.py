#!/usr/bin/env python3
"""Free browser extension approach for captcha handling."""

import asyncio
import json
from pathlib import Path

# Create a simple browser extension that can help with captchas
EXTENSION_MANIFEST = {
    "manifest_version": 3,
    "name": "Captcha Helper",
    "version": "1.0",
    "description": "Helps with captcha detection and notification",
    "permissions": ["activeTab", "storage"],
    "content_scripts": [{
        "matches": ["<all_urls>"],
        "js": ["content.js"]
    }],
    "background": {
        "service_worker": "background.js"
    }
}

CONTENT_SCRIPT = """
// Content script to detect and help with captchas
(function() {
    'use strict';
    
    // Captcha detection patterns
    const captchaSelectors = [
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
        '.g-recaptcha',
        '.h-captcha',
        'img[src*="captcha"]',
        'input[name*="captcha"]'
    ];
    
    // Check for captchas
    function detectCaptcha() {
        for (const selector of captchaSelectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                return {
                    found: true,
                    type: selector,
                    count: elements.length,
                    elements: Array.from(elements).map(el => ({
                        tagName: el.tagName,
                        className: el.className,
                        src: el.src || '',
                        visible: el.offsetParent !== null
                    }))
                };
            }
        }
        return { found: false };
    }
    
    // Monitor for captcha appearance
    function monitorCaptcha() {
        const result = detectCaptcha();
        
        if (result.found) {
            // Notify the extension
            chrome.runtime.sendMessage({
                type: 'CAPTCHA_DETECTED',
                data: result,
                url: window.location.href,
                timestamp: Date.now()
            });
            
            // Add visual indicator
            addCaptchaIndicator(result);
        }
        
        return result;
    }
    
    // Add visual indicator for detected captcha
    function addCaptchaIndicator(captchaInfo) {
        // Remove existing indicator
        const existing = document.getElementById('captcha-helper-indicator');
        if (existing) existing.remove();
        
        // Create new indicator
        const indicator = document.createElement('div');
        indicator.id = 'captcha-helper-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #ff4444;
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 10000;
            font-family: Arial, sans-serif;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        indicator.innerHTML = `
            🚨 CAPTCHA DETECTED<br>
            Type: ${captchaInfo.type}<br>
            Count: ${captchaInfo.count}<br>
            <button onclick="this.parentElement.remove()" style="margin-top:5px;">Close</button>
        `;
        
        document.body.appendChild(indicator);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (indicator.parentElement) {
                indicator.remove();
            }
        }, 10000);
    }
    
    // Monitor for captcha completion
    function monitorCompletion() {
        const observer = new MutationObserver(() => {
            const result = detectCaptcha();
            if (!result.found) {
                chrome.runtime.sendMessage({
                    type: 'CAPTCHA_SOLVED',
                    url: window.location.href,
                    timestamp: Date.now()
                });
                
                // Remove indicator
                const indicator = document.getElementById('captcha-helper-indicator');
                if (indicator) indicator.remove();
                
                observer.disconnect();
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true
        });
    }
    
    // Initialize
    function init() {
        // Initial check
        const result = monitorCaptcha();
        
        if (result.found) {
            monitorCompletion();
        }
        
        // Periodic checks
        setInterval(monitorCaptcha, 2000);
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose functions for external access
    window.captchaHelper = {
        detect: detectCaptcha,
        monitor: monitorCaptcha
    };
})();
"""

BACKGROUND_SCRIPT = """
// Background script for captcha helper extension
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'CAPTCHA_DETECTED') {
        console.log('Captcha detected:', message.data);
        
        // Store captcha info
        chrome.storage.local.set({
            lastCaptcha: {
                ...message.data,
                url: message.url,
                timestamp: message.timestamp
            }
        });
        
        // Show notification
        chrome.action.setBadgeText({
            text: '!',
            tabId: sender.tab.id
        });
        
        chrome.action.setBadgeBackgroundColor({
            color: '#ff4444',
            tabId: sender.tab.id
        });
    }
    
    if (message.type === 'CAPTCHA_SOLVED') {
        console.log('Captcha solved:', message.url);
        
        // Clear notification
        chrome.action.setBadgeText({
            text: '',
            tabId: sender.tab.id
        });
        
        // Store solve info
        chrome.storage.local.set({
            lastSolved: {
                url: message.url,
                timestamp: message.timestamp
            }
        });
    }
});
"""

async def create_captcha_helper_extension():
    """Create a browser extension to help with captcha detection."""
    
    print("🔧 Creating Captcha Helper Browser Extension")
    print("=" * 50)
    
    # Create extension directory
    ext_dir = Path("captcha_helper_extension")
    ext_dir.mkdir(exist_ok=True)
    
    # Create manifest.json
    with open(ext_dir / "manifest.json", "w") as f:
        json.dump(EXTENSION_MANIFEST, f, indent=2)
    
    # Create content script
    with open(ext_dir / "content.js", "w") as f:
        f.write(CONTENT_SCRIPT)
    
    # Create background script
    with open(ext_dir / "background.js", "w") as f:
        f.write(BACKGROUND_SCRIPT)
    
    # Create installation instructions
    instructions = """
# Captcha Helper Extension Installation

## How to Install:
1. Open Chrome/Edge browser
2. Go to chrome://extensions/ (or edge://extensions/)
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the 'captcha_helper_extension' folder
6. Extension will be installed and active

## How it Works:
- Automatically detects captchas on any page
- Shows visual indicator when captcha is found
- Monitors for captcha completion
- Provides notifications and logging

## Integration with Scraper:
- Extension runs in browser alongside scraper
- Provides real-time captcha detection
- Can be used to pause/resume scraper automatically
- Helps with manual captcha solving workflow

## Benefits:
- ✅ Completely FREE
- ✅ Works with any website
- ✅ Real-time detection
- ✅ Visual feedback
- ✅ No API keys needed
- ✅ Privacy-friendly (local only)
"""
    
    with open(ext_dir / "README.md", "w") as f:
        f.write(instructions)
    
    print(f"✅ Extension created in: {ext_dir.absolute()}")
    print("\n📋 Files created:")
    print("   📄 manifest.json - Extension configuration")
    print("   📄 content.js - Captcha detection script")
    print("   📄 background.js - Background processing")
    print("   📄 README.md - Installation instructions")
    
    print(f"\n🚀 Next Steps:")
    print("   1. Install the extension in your browser")
    print("   2. Extension will automatically detect captchas")
    print("   3. Use with scraper for better captcha handling")
    
    return ext_dir

if __name__ == "__main__":
    asyncio.run(create_captcha_helper_extension())