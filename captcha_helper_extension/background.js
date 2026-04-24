
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
