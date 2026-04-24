
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
