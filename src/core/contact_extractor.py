"""Contact extractor untuk mengambil WhatsApp, email, dan social media dari detail pages."""

import re
import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContactInfo:
    """Contact information extracted from creator detail page."""
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    instagram: Optional[str] = None
    tiktok: Optional[str] = None
    line: Optional[str] = None
    telegram: Optional[str] = None

class ContactExtractor:
    """Extractor untuk mengambil contact data dari halaman detail creator."""
    
    def __init__(self):
        self.whatsapp_patterns = [
            r'(?:whatsapp|wa)[^\d]*(\+?62\d{8,13})',
            r'(?:hp|phone|telp)[^\d]*(\+?62\d{8,13})',
            r'(\+62\d{8,13})',
            r'(08\d{8,11})',
            r'(62\d{8,13})'
        ]
        
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        self.instagram_patterns = [
            r'instagram\.com/([a-zA-Z0-9_.]+)',
            r'ig[:\s]*@?([a-zA-Z0-9_.]+)',
            r'@([a-zA-Z0-9_.]+)'
        ]
        
        self.tiktok_patterns = [
            r'tiktok\.com/@([a-zA-Z0-9_.]+)',
            r'tiktok[:\s]*@?([a-zA-Z0-9_.]+)',
            r'tt[:\s]*@?([a-zA-Z0-9_.]+)'
        ]
        
        self.excluded_email_domains = [
            'tokopedia.com', 'example.com', 'test.com', 'noreply.com',
            'no-reply.com', 'donotreply.com', 'support.com'
        ]
    
    async def extract_contact_info(self, page, creator_username: str) -> ContactInfo:
        """Extract contact information from creator detail page."""
        
        contact_info = ContactInfo()
        
        try:
            logger.info(f"Extracting contact info for {creator_username}")
            
            # Wait for page to load completely
            await asyncio.sleep(3)
            
            # Get page content
            html = await page.content()
            
            # Extract WhatsApp
            contact_info.whatsapp = self._extract_whatsapp(html)
            
            # Extract email
            contact_info.email = self._extract_email(html)
            
            # Extract Instagram
            contact_info.instagram = self._extract_instagram(html)
            
            # Extract TikTok
            contact_info.tiktok = self._extract_tiktok(html)
            
            # Extract Line ID
            contact_info.line = self._extract_line(html)
            
            # Extract Telegram
            contact_info.telegram = self._extract_telegram(html)
            
            # Log results
            found_contacts = []
            if contact_info.whatsapp:
                found_contacts.append(f"WhatsApp: {contact_info.whatsapp}")
            if contact_info.email:
                found_contacts.append(f"Email: {contact_info.email}")
            if contact_info.instagram:
                found_contacts.append(f"Instagram: {contact_info.instagram}")
            if contact_info.tiktok:
                found_contacts.append(f"TikTok: {contact_info.tiktok}")
            if contact_info.line:
                found_contacts.append(f"Line: {contact_info.line}")
            if contact_info.telegram:
                found_contacts.append(f"Telegram: {contact_info.telegram}")
            
            if found_contacts:
                logger.info(f"Found contacts for {creator_username}: {', '.join(found_contacts)}")
            else:
                logger.warning(f"No contact info found for {creator_username}")
            
            return contact_info
            
        except Exception as e:
            logger.error(f"Error extracting contact info for {creator_username}: {e}")
            return contact_info
    
    def _extract_whatsapp(self, html: str) -> Optional[str]:
        """Extract WhatsApp number from HTML."""
        
        for pattern in self.whatsapp_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                phone = matches[0]
                if isinstance(phone, tuple):
                    phone = phone[0]
                
                # Clean phone number
                phone = re.sub(r'[^\d+]', '', phone)
                
                # Normalize Indonesian phone numbers
                if phone.startswith('08'):
                    phone = '+62' + phone[1:]
                elif phone.startswith('62') and not phone.startswith('+62'):
                    phone = '+' + phone
                elif not phone.startswith('+') and len(phone) >= 10:
                    # Assume Indonesian number if no country code
                    if phone.startswith('8'):
                        phone = '+62' + phone
                
                # Validate phone number length
                if len(phone) >= 12 and len(phone) <= 16:  # Valid international phone length
                    return phone
        
        return None
    
    def _extract_email(self, html: str) -> Optional[str]:
        """Extract email address from HTML."""
        
        matches = re.findall(self.email_pattern, html, re.IGNORECASE)
        
        if matches:
            # Filter out excluded domains
            valid_emails = []
            
            for email in matches:
                domain = email.split('@')[1].lower()
                if not any(excluded in domain for excluded in self.excluded_email_domains):
                    valid_emails.append(email.lower())
            
            if valid_emails:
                # Return the first valid email
                return valid_emails[0]
        
        return None
    
    def _extract_instagram(self, html: str) -> Optional[str]:
        """Extract Instagram handle from HTML."""
        
        for pattern in self.instagram_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                handle = matches[0]
                
                # Clean handle
                handle = re.sub(r'[^\w.]', '', handle)
                
                # Validate handle
                if len(handle) > 2 and not handle.isdigit() and '.' not in handle[:3]:
                    return f"@{handle}"
        
        return None
    
    def _extract_tiktok(self, html: str) -> Optional[str]:
        """Extract TikTok handle from HTML."""
        
        for pattern in self.tiktok_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                handle = matches[0]
                
                # Clean handle
                handle = re.sub(r'[^\w.]', '', handle)
                
                # Validate handle
                if len(handle) > 2 and not handle.isdigit():
                    return f"@{handle}"
        
        return None
    
    def _extract_line(self, html: str) -> Optional[str]:
        """Extract Line ID from HTML."""
        
        line_patterns = [
            r'line[:\s]*@?([a-zA-Z0-9_.]+)',
            r'line\.me/ti/p/([a-zA-Z0-9_.]+)',
            r'line id[:\s]*@?([a-zA-Z0-9_.]+)'
        ]
        
        for pattern in line_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                line_id = matches[0]
                
                # Clean Line ID
                line_id = re.sub(r'[^\w.]', '', line_id)
                
                # Validate Line ID
                if len(line_id) > 2 and not line_id.isdigit():
                    return line_id
        
        return None
    
    def _extract_telegram(self, html: str) -> Optional[str]:
        """Extract Telegram handle from HTML."""
        
        telegram_patterns = [
            r't\.me/([a-zA-Z0-9_.]+)',
            r'telegram[:\s]*@?([a-zA-Z0-9_.]+)',
            r'tg[:\s]*@?([a-zA-Z0-9_.]+)'
        ]
        
        for pattern in telegram_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                handle = matches[0]
                
                # Clean handle
                handle = re.sub(r'[^\w.]', '', handle)
                
                # Validate handle
                if len(handle) > 2 and not handle.isdigit():
                    return f"@{handle}"
        
        return None
    
    async def find_detail_page_url(self, page, creator_username: str, base_url: str) -> Optional[str]:
        """Find the detail page URL for a creator."""
        
        # Common URL patterns for creator profiles
        url_patterns = [
            f"{base_url}/creator/{creator_username}",
            f"{base_url}/profile/{creator_username}",
            f"{base_url}/user/{creator_username}",
            f"https://www.tokopedia.com/{creator_username}",
            f"{base_url}/affiliate/{creator_username}",
            f"{base_url}/influencer/{creator_username}"
        ]
        
        # Try to find clickable elements first
        clickable_selectors = [
            f"a[href*='{creator_username}']",
            f"[data-username='{creator_username}']",
            f"[data-creator='{creator_username}']",
            "tr td:first-child a",
            "tr td a",
            ".creator-name a",
            ".username a",
            "[data-testid*='creator'] a"
        ]
        
        # Look for clickable elements
        for selector in clickable_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    href = await elements[0].get_attribute('href')
                    if href and href not in ('#', 'javascript:void(0)', ''):
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            href = base_url + href
                        return href
            except:
                continue
        
        # Try common URL patterns
        for url in url_patterns:
            try:
                # Test if URL exists by making a quick navigation
                response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                if response and response.status < 400:
                    return url
            except:
                continue
        
        return None
    
    async def navigate_to_detail_page(self, page, creator_username: str, base_url: str) -> bool:
        """Navigate to creator detail page."""
        
        try:
            # First try to find and click a link on current page
            clickable_selectors = [
                f"a[href*='{creator_username}']",
                "tr td:first-child a",
                "tr td a",
                ".creator-name a",
                ".username a"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Clicking element: {selector}")
                        await elements[0].click()
                        await asyncio.sleep(3)
                        return True
                except Exception as e:
                    logger.debug(f"Could not click {selector}: {e}")
                    continue
            
            # If clicking failed, try direct navigation
            detail_url = await self.find_detail_page_url(page, creator_username, base_url)
            if detail_url:
                logger.info(f"Navigating to: {detail_url}")
                await page.goto(detail_url)
                await asyncio.sleep(3)
                return True
            
            logger.warning(f"Could not find detail page for {creator_username}")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to detail page for {creator_username}: {e}")
            return False