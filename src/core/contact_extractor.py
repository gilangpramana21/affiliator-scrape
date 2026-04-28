"""
Contact Extractor - Specialized extractor for WhatsApp and Email contacts
"""
import re
from typing import Optional, Dict
from lxml import html as lxml_html


class ContactExtractor:
    """Extracts WhatsApp and Email contact information from HTML"""
    
    # Multiple selector strategies for WhatsApp
    WHATSAPP_SELECTORS = [
        # Common patterns for WhatsApp display
        "//a[contains(@href, 'wa.me')]",
        "//a[contains(@href, 'whatsapp')]",
        "//a[contains(@href, 'api.whatsapp.com')]",
        "//span[contains(text(), 'WhatsApp')]/..//a",
        "//div[contains(@class, 'whatsapp')]//a",
        "//div[contains(@class, 'contact')]//a[contains(@href, 'tel:')]",
        # Text patterns
        "//span[contains(text(), 'WA:')]",
        "//span[contains(text(), 'WhatsApp:')]",
        "//div[contains(text(), 'WhatsApp')]",
        # Phone number patterns
        "//a[starts-with(@href, 'tel:')]",
        "//span[contains(@class, 'phone')]",
        "//div[contains(@class, 'phone')]",
    ]
    
    # Multiple selector strategies for Email
    EMAIL_SELECTORS = [
        # Common patterns for email display
        "//a[contains(@href, 'mailto:')]",
        "//span[contains(text(), 'Email')]/..//a",
        "//div[contains(@class, 'email')]//a",
        "//span[contains(@class, 'email')]",
        "//div[contains(@class, 'contact')]//a[contains(@href, 'mailto:')]",
        # Text patterns
        "//span[contains(text(), 'Email:')]",
        "//div[contains(text(), 'Email:')]",
        "//span[contains(text(), '@')]",
    ]
    
    # Indonesian phone number patterns
    PHONE_PATTERNS = [
        r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4}',  # +62 xxx-xxxx-xxxx
        r'62\d{9,13}',  # 62xxxxxxxxxx
        r'08\d{8,12}',  # 08xxxxxxxxxx
        r'0\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',  # 0xxx-xxxx-xxxx
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    def __init__(self):
        self.phone_regex = re.compile('|'.join(self.PHONE_PATTERNS))
        self.email_regex = re.compile(self.EMAIL_PATTERN)
    
    def extract_whatsapp(self, html_content: str) -> Optional[str]:
        """
        Extract WhatsApp number from HTML content
        
        Args:
            html_content: HTML string to parse
            
        Returns:
            WhatsApp number in standardized format, or None if not found
        """
        try:
            doc = lxml_html.fromstring(html_content)
        except Exception as e:
            print(f"Error parsing HTML for WhatsApp extraction: {e}")
            return None
        
        # Try each selector strategy
        for selector in self.WHATSAPP_SELECTORS:
            try:
                elements = doc.xpath(selector)
                
                for element in elements:
                    # Extract from href attribute
                    if element.tag == 'a':
                        href = element.get('href', '')
                        
                        # Extract from wa.me links
                        if 'wa.me' in href or 'whatsapp' in href:
                            # Extract number from URL
                            number = self._extract_number_from_url(href)
                            if number:
                                return self._normalize_phone_number(number)
                        
                        # Extract from tel: links
                        if href.startswith('tel:'):
                            number = href.replace('tel:', '').strip()
                            return self._normalize_phone_number(number)
                    
                    # Extract from text content
                    text = element.text_content().strip()
                    number = self._extract_phone_from_text(text)
                    if number:
                        return number
                    
            except Exception as e:
                # Continue to next selector if this one fails
                continue
        
        # Fallback: Search entire HTML for phone patterns
        number = self._extract_phone_from_text(html_content)
        return number
    
    def extract_email(self, html_content: str) -> Optional[str]:
        """
        Extract email address from HTML content
        
        Args:
            html_content: HTML string to parse
            
        Returns:
            Email address, or None if not found
        """
        try:
            doc = lxml_html.fromstring(html_content)
        except Exception as e:
            print(f"Error parsing HTML for email extraction: {e}")
            return None
        
        # Try each selector strategy
        for selector in self.EMAIL_SELECTORS:
            try:
                elements = doc.xpath(selector)
                
                for element in elements:
                    # Extract from href attribute
                    if element.tag == 'a':
                        href = element.get('href', '')
                        
                        # Extract from mailto: links
                        if href.startswith('mailto:'):
                            email = href.replace('mailto:', '').strip()
                            # Remove query parameters
                            email = email.split('?')[0]
                            if self._validate_email(email):
                                return email.lower()
                    
                    # Extract from text content
                    text = element.text_content().strip()
                    email = self._extract_email_from_text(text)
                    if email:
                        return email
                    
            except Exception as e:
                # Continue to next selector if this one fails
                continue
        
        # Fallback: Search entire HTML for email patterns
        email = self._extract_email_from_text(html_content)
        return email
    
    def extract_contacts(self, html_content: str) -> Dict[str, Optional[str]]:
        """
        Extract both WhatsApp and Email from HTML content
        
        Args:
            html_content: HTML string to parse
            
        Returns:
            Dictionary with 'whatsapp' and 'email' keys
        """
        return {
            'whatsapp': self.extract_whatsapp(html_content),
            'email': self.extract_email(html_content)
        }
    
    def _extract_number_from_url(self, url: str) -> Optional[str]:
        """Extract phone number from WhatsApp URL"""
        # wa.me/62812345678
        # api.whatsapp.com/send?phone=62812345678
        
        # Try to extract from wa.me
        if 'wa.me/' in url:
            parts = url.split('wa.me/')
            if len(parts) > 1:
                number = parts[1].split('?')[0].split('/')[0]
                return number
        
        # Try to extract from phone parameter
        if 'phone=' in url:
            parts = url.split('phone=')
            if len(parts) > 1:
                number = parts[1].split('&')[0]
                return number
        
        return None
    
    def _extract_phone_from_text(self, text: str) -> Optional[str]:
        """Extract phone number from text using regex"""
        # Remove common separators for better matching
        clean_text = text.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        match = self.phone_regex.search(clean_text)
        if match:
            number = match.group(0)
            return self._normalize_phone_number(number)
        
        return None
    
    def _extract_email_from_text(self, text: str) -> Optional[str]:
        """Extract email from text using regex"""
        match = self.email_regex.search(text)
        if match:
            email = match.group(0).lower()
            if self._validate_email(email):
                return email
        
        return None
    
    def _normalize_phone_number(self, number: str) -> str:
        """
        Normalize phone number to Indonesian format
        
        Converts various formats to +62 format:
        - 08xxx -> +628xxx
        - 62xxx -> +62xxx
        - 0xxx -> +62xxx
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', number)
        
        # Handle different formats
        if digits.startswith('62'):
            return f"+{digits}"
        elif digits.startswith('08'):
            return f"+62{digits[1:]}"
        elif digits.startswith('8'):
            return f"+62{digits}"
        elif digits.startswith('0'):
            return f"+62{digits[1:]}"
        else:
            return f"+{digits}"
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or '@' not in email:
            return False
        
        # Basic validation
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        # Check domain has at least one dot
        if '.' not in domain:
            return False
        
        # Check for common invalid patterns (only for obvious test emails)
        invalid_patterns = [
            'test@test.com',
            'email@email.com',
            'noreply@',
            'no-reply@',
        ]
        
        for pattern in invalid_patterns:
            if pattern in email.lower():
                return False
        
        return True


if __name__ == "__main__":
    # Test the extractor
    extractor = ContactExtractor()
    
    # Test HTML with WhatsApp
    test_html_wa = """
    <div class="contact-info">
        <span>WhatsApp:</span>
        <a href="https://wa.me/628123456789">+62 812-3456-789</a>
    </div>
    """
    
    wa = extractor.extract_whatsapp(test_html_wa)
    print(f"WhatsApp: {wa}")
    
    # Test HTML with Email
    test_html_email = """
    <div class="contact-info">
        <span>Email:</span>
        <a href="mailto:creator@example.com">creator@example.com</a>
    </div>
    """
    
    email = extractor.extract_email(test_html_email)
    print(f"Email: {email}")
    
    # Test both
    test_html_both = """
    <div class="profile">
        <div class="contact">
            <p>Hubungi saya:</p>
            <p>WA: 0812-3456-7890</p>
            <p>Email: affiliator@gmail.com</p>
        </div>
    </div>
    """
    
    contacts = extractor.extract_contacts(test_html_both)
    print(f"Contacts: {contacts}")
