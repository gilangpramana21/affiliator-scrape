"""Tokopedia-specific extractor that handles the actual data format."""

import re
import logging
from typing import List, Optional
from dataclasses import dataclass

from src.core.html_parser import Document, Element, HTMLParser
from src.core.affiliator_extractor import AffiliatorEntry, ListPageResult, AffiliatorDetail

logger = logging.getLogger(__name__)


@dataclass
class ParsedCreatorData:
    """Parsed creator data from the combined text string."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[int] = None
    raw_text: Optional[str] = None


class TokopediaExtractor:
    """Extractor specifically designed for Tokopedia's actual data format."""
    
    def __init__(self, parser: Optional[HTMLParser] = None):
        self._parser = parser or HTMLParser()
    
    def extract_list_page(self, doc: Document) -> ListPageResult:
        """Extract affiliators from Tokopedia list page."""
        
        # Try multiple table selection strategies
        tables = self._parser.select(doc, "table")
        if not tables:
            logger.warning("No tables found in document")
            return ListPageResult(affiliators=[], next_page_url=None)
        
        # Find the main data table (usually the largest one)
        main_table = None
        max_rows = 0
        
        for table in tables:
            rows = self._parser.select(table, "tr")
            if len(rows) > max_rows:
                max_rows = len(rows)
                main_table = table
        
        if not main_table:
            logger.warning("No suitable data table found")
            return ListPageResult(affiliators=[], next_page_url=None)
        
        # Get all rows from the main table
        all_rows = self._parser.select(main_table, "tr")
        
        # Skip header row(s) - look for rows with actual data
        data_rows = []
        for row in all_rows:
            cells = self._parser.select(row, "td")
            if len(cells) >= 2:  # Must have at least 2 cells for data
                # Check if this looks like a data row (has text content)
                cell_text = self._parser.get_text(cells[1]) if len(cells) > 1 else ""
                if cell_text and len(cell_text.strip()) > 10:  # Has substantial content
                    data_rows.append(row)
        
        logger.info(f"Found {len(all_rows)} total rows, {len(data_rows)} data rows")
        
        affiliators: List[AffiliatorEntry] = []
        
        for i, row in enumerate(data_rows):
            try:
                entry = self._extract_row_data(row)
                if entry:
                    affiliators.append(entry)
                    logger.debug(f"Extracted creator {i+1}: {entry.username}")
                else:
                    logger.warning(f"Failed to extract data from row {i+1}")
            except Exception as e:
                logger.error(f"Error extracting row {i+1}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(affiliators)} creators")
        
        # Try to find next page URL (though it might not exist in this format)
        next_page_url = self._extract_next_page_url(doc)
        
        return ListPageResult(affiliators=affiliators, next_page_url=next_page_url)
    
    def _extract_row_data(self, row: Element) -> Optional[AffiliatorEntry]:
        """Extract data from a single table row."""
        
        # Get all cells
        cells = self._parser.select(row, "td")
        if len(cells) < 2:
            return None
        
        # Try multiple strategies to find the main data
        main_text = None
        
        # Strategy 1: Look for the main data span in the second cell
        main_spans = self._parser.select(cells[1], "span.arco-table-cell-wrap-value")
        if main_spans:
            main_text = self._parser.get_text(main_spans[0])
        
        # Strategy 2: If no specific span, get text from second cell directly
        if not main_text:
            main_text = self._parser.get_text(cells[1])
        
        # Strategy 3: Try other cells if second cell is empty
        if not main_text or len(main_text.strip()) < 5:
            for i, cell in enumerate(cells):
                cell_text = self._parser.get_text(cell)
                if cell_text and len(cell_text.strip()) > 10:
                    main_text = cell_text
                    logger.debug(f"Using cell {i} for main text: {cell_text[:50]}...")
                    break
        
        if not main_text:
            logger.debug("No main text found in row")
            return None
        
        # Parse the combined text
        parsed_data = self._parse_creator_text(main_text)
        
        if not parsed_data.username:
            logger.debug(f"No username found in text: {main_text[:50]}...")
            return None
        
        # Extract GMV data from other spans in the row
        gmv_value = self._extract_gmv_from_row(row)
        
        # Try to extract detail URL (though it might not exist)
        detail_url = self._extract_detail_url(row)
        
        # Create the entry
        entry = AffiliatorEntry(
            username=parsed_data.username,
            kategori=parsed_data.category,
            pengikut=parsed_data.followers,
            gmv=gmv_value,
            produk_terjual=None,  # Not available in this format
            rata_rata_tayangan=None,  # Not available in this format
            tingkat_interaksi=None,  # Not available in this format
            detail_url=detail_url
        )
        
        return entry
    
    def _parse_creator_text(self, text: str) -> ParsedCreatorData:
        """Parse the combined creator text string."""
        
        if not text:
            return ParsedCreatorData()
        
        # Extract username (before first "Lv.")
        username_match = re.match(r'^([^L]+?)Lv\.', text)
        username = username_match.group(1) if username_match else None
        
        # Extract follower count (pattern like "140,2 rb" or "1,7 jt")
        follower_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(rb|jt|k)', text, re.IGNORECASE)
        followers = None
        if follower_match:
            num_str = follower_match.group(1).replace(',', '.')
            suffix = follower_match.group(2).lower()
            num = float(num_str)
            if suffix == 'rb':
                followers = int(num * 1000)
            elif suffix == 'jt':
                followers = int(num * 1000000)
            elif suffix == 'k':
                followers = int(num * 1000)
        
        # Extract category - improved parsing to remove "Lv. X" noise
        category = self._extract_category(text, username)
        
        return ParsedCreatorData(
            username=username,
            category=category,
            followers=followers,
            raw_text=text
        )
    
    def _extract_category(self, text: str, username: Optional[str]) -> Optional[str]:
        """Extract and clean category from text."""
        
        # Pattern: find text after display name but before follower count
        category_pattern = r'Lv\.\s*\d+.*?([A-Za-z][^,+]+?)(?:,\s*\+|\s*,\s*\d)'
        category_match = re.search(category_pattern, text)
        category = None
        
        if category_match:
            category = category_match.group(1).strip()
            # Clean up category by removing common noise patterns
            category = re.sub(r'^Lv\.\s*\d+\s*', '', category)  # Remove leading Lv. X
            category = re.sub(r'\s*Lv\.\s*\d+\s*', ' ', category)  # Remove middle Lv. X
            category = re.sub(r'[🐣🌟🚀]+', '', category)  # Remove emojis
            category = re.sub(r'\s+', ' ', category).strip()  # Normalize whitespace
            
            # Additional cleanup: remove display names that got mixed in
            if username and username.lower() in category.lower():
                # Try to extract just the category part after the display name
                parts = category.split()
                # Find parts that don't match username
                clean_parts = []
                for part in parts:
                    if part.lower() not in username.lower() and len(part) > 2:
                        clean_parts.append(part)
                if clean_parts:
                    category = ' '.join(clean_parts)
        
        # Fallback: try a different pattern if first one didn't work well
        if not category or len(category) < 3:
            # Look for category pattern: after display name, before comma and numbers
            alt_pattern = r'[A-Za-z][^,]*?([A-Za-z&\s]+?)(?:,\s*\+\d|,\s*\d)'
            alt_match = re.search(alt_pattern, text)
            if alt_match:
                category = alt_match.group(1).strip()
                # Clean up
                category = re.sub(r'[🐣🌟🚀]+', '', category)
                category = re.sub(r'\s+', ' ', category).strip()
        
        return category
    
    def extract_detail_page(self, doc: Document, page_url: str = "") -> AffiliatorDetail:
        """Extract complete affiliator profile from a Tokopedia detail page.
        
        Args:
            doc: Parsed HTML document of the detail page.
            page_url: URL of the page (used for error logging).
            
        Returns:
            AffiliatorDetail with all available profile fields.
        """
        # Try to extract username from page title or URL
        username = None
        if page_url and "cid=" in page_url:
            # Extract creator ID from URL as fallback username
            import re
            cid_match = re.search(r"cid=([^&]+)", page_url)
            if cid_match:
                username = f"creator_{cid_match.group(1)[:8]}"  # Use first 8 chars of CID
        
        # Try to extract username from page content
        if not username:
            # Look for common username patterns in the page
            title_elements = self._parser.select(doc, "title, h1, h2, .username, .creator-name")
            for element in title_elements:
                text = self._parser.get_text(element)
                if text and len(text.strip()) > 0:
                    username = text.strip()
                    break
        
        # Extract contact information
        nomor_kontak = self._extract_contact_from_detail(doc, page_url)
        nomor_whatsapp = self._extract_whatsapp_from_detail(doc, page_url)
        
        # Return basic detail structure
        # Most data will come from the list page entry
        return AffiliatorDetail(
            username=username,
            kategori=None,  # Will be filled from list entry
            pengikut=None,  # Will be filled from list entry
            gmv=None,       # Will be filled from list entry
            produk_terjual=None,
            rata_rata_tayangan=None,
            tingkat_interaksi=None,
            nomor_kontak=nomor_kontak,
            nomor_whatsapp=nomor_whatsapp,
            gmv_per_pembeli=None,
            gmv_harian=None,
            gmv_mingguan=None,
            gmv_bulanan=None,
        )
    
    def _extract_contact_from_detail(self, doc: Document, page_url: str = "") -> Optional[str]:
        """Extract contact number from Tokopedia detail page."""
        
        # Get the full HTML text for pattern matching
        html_text = ""
        body_elements = self._parser.select(doc, "body")
        if body_elements:
            html_text = self._parser.get_text(body_elements[0])
        
        # Phone number patterns (Indonesian format)
        phone_patterns = [
            r'\+62\s*\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',  # +62 format
            r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}',         # 08xx format
            r'62\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}',       # 62xx format
            r'\d{4}[\s-]?\d{4}[\s-]?\d{3,4}'              # General format
        ]
        
        import re
        for pattern in phone_patterns:
            matches = re.findall(pattern, html_text)
            if matches:
                # Return the first valid-looking phone number
                for match in matches:
                    # Clean up the number
                    clean_number = re.sub(r'[\s-]', '', match)
                    if len(clean_number) >= 10:  # Minimum valid phone length
                        # Normalize to Indonesian format
                        normalized = self._normalize_phone_number(clean_number)
                        if normalized:
                            logger.debug(f"Found and normalized phone number: {normalized}")
                            return normalized
        
        # Look for tel: links
        tel_links = self._parser.select(doc, "a[href^='tel:']")
        for link in tel_links:
            href = self._parser.get_attribute(link, "href")
            if href:
                number = href[4:].strip()  # Remove 'tel:' prefix
                if number:
                    normalized = self._normalize_phone_number(number)
                    if normalized:
                        logger.debug(f"Found tel link and normalized: {normalized}")
                        return normalized
        
        logger.debug(f"No contact number found on page {page_url}")
        return None
    
    def _extract_whatsapp_from_detail(self, doc: Document, page_url: str = "") -> Optional[str]:
        """Extract WhatsApp number from Tokopedia detail page.
        
        Note: This method only handles static extraction. For interactive WhatsApp
        extraction (clicking on WhatsApp buttons/icons), use the browser-based
        extract_whatsapp_interactive method in the scraper orchestrator.
        """
        
        # Look for WhatsApp links first
        wa_selectors = [
            "a[href*='wa.me']",
            "a[href*='whatsapp']",
            "a[href*='api.whatsapp.com']"
        ]
        
        for selector in wa_selectors:
            elements = self._parser.select(doc, selector)
            for element in elements:
                href = self._parser.get_attribute(element, "href")
                if href:
                    # Extract number from WhatsApp URL
                    import re
                    if "wa.me/" in href:
                        number = href.split("wa.me/")[-1].split("?")[0]
                        if number and number.isdigit():
                            normalized = self._normalize_phone_number(number)
                            if normalized:
                                logger.debug(f"Found WhatsApp from wa.me: {normalized}")
                                return normalized
                    
                    # Extract from other WhatsApp URL patterns
                    wa_number_match = re.search(r'phone=(\d+)', href)
                    if wa_number_match:
                        number = wa_number_match.group(1)
                        normalized = self._normalize_phone_number(number)
                        if normalized:
                            logger.debug(f"Found WhatsApp from phone param: {normalized}")
                            return normalized
        
        # Look for WhatsApp patterns in text
        html_text = ""
        body_elements = self._parser.select(doc, "body")
        if body_elements:
            html_text = self._parser.get_text(body_elements[0])
        
        # WhatsApp number patterns in text
        wa_text_patterns = [
            r'wa\.me/(\d+)',
            r'whatsapp.*?(\+?62\d{9,13})',
            r'WA.*?(\+?62\d{9,13})',
            r'WhatsApp.*?(\+?62\d{9,13})',
            r'wa.*?(\d{10,15})'
        ]
        
        import re
        for pattern in wa_text_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    # Clean up the number
                    clean_number = re.sub(r'[^\d+]', '', match)
                    if len(clean_number) >= 10:
                        normalized = self._normalize_phone_number(clean_number)
                        if normalized:
                            logger.debug(f"Found WhatsApp from text pattern: {normalized}")
                            return normalized
        
        logger.debug(f"No static WhatsApp number found on page {page_url}")
        return None
    
    def _normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number to Indonesian format (08... or +62...).
        
        Valid Indonesian phone numbers:
        - Mobile: 08xx-xxxx-xxxx (10-13 digits total)
        - International: +62-8xx-xxxx-xxxx (12-15 digits total including +62)
        """
        
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        clean = re.sub(r'[^\d+]', '', phone)
        
        # Remove leading zeros (but keep + if present)
        if clean.startswith('+'):
            prefix = '+'
            clean = clean[1:].lstrip('0')
            clean = prefix + clean
        else:
            clean = clean.lstrip('0')
        
        # Handle different formats
        if clean.startswith('+62'):
            # Already in +62 format
            # Valid: +62 + 8-13 digits = 12-15 total length
            if 12 <= len(clean) <= 15:
                # Must start with +628 (Indonesian mobile)
                if clean[3] == '8':
                    return clean
        elif clean.startswith('62'):
            # Convert 62xxx to +62xxx
            # Valid: 62 + 8-13 digits = 11-14 total length
            if 11 <= len(clean) <= 14:
                # Must start with 628 (Indonesian mobile)
                if clean[2] == '8':
                    return '+' + clean
        elif clean.startswith('8'):
            # Convert 8xxx to 08xxx (Indonesian mobile format)
            # Valid: 8 + 8-12 more digits = 9-13 total length
            if 9 <= len(clean) <= 13:
                return '0' + clean
        
        # If we can't normalize it properly, return None
        logger.debug(f"Could not normalize phone number (invalid format or length): {phone} -> {clean}")
        return None
    
    def _extract_gmv_from_row(self, row: Element) -> Optional[float]:
        """Extract GMV value from row spans."""
        
        # Look for spans containing GMV data
        gmv_spans = self._parser.select(row, "span[class*='text-body-m-regular'][class*='text-neutral-text1']")
        
        for span in gmv_spans:
            text = self._parser.get_text(span)
            if 'Rp' in text or 'M' in text or 'JT' in text:
                return self._parse_gmv_value(text)
        
        return None
    
    def _parse_gmv_value(self, text: str) -> Optional[float]:
        """Parse GMV value from text like 'Rp2,3M' or 'Rp1JT+'."""
        
        if not text:
            return None
        
        # Remove 'Rp' and whitespace
        clean_text = re.sub(r'[Rp\s]', '', text)
        
        # Handle JT+ format
        if 'JT+' in clean_text.upper():
            clean_text = clean_text.upper().replace('JT+', '')
            multiplier = 1_000_000
        else:
            # Identify suffix
            suffix_multipliers = {
                'K': 1_000,
                'M': 1_000_000,
                'JT': 1_000_000,
                'B': 1_000_000_000
            }
            multiplier = 1
            upper = clean_text.upper()
            for suffix, mult in suffix_multipliers.items():
                if upper.endswith(suffix):
                    clean_text = clean_text[:-len(suffix)].strip()
                    multiplier = mult
                    break
        
        # Remove commas used as thousand separators
        clean_text = clean_text.replace(',', '')
        
        try:
            return float(clean_text) * multiplier
        except ValueError:
            logger.warning(f"Could not parse GMV value: {text}")
            return None
    
    def _extract_detail_url(self, row: Element) -> Optional[str]:
        """Try to extract detail URL from row."""
        
        # Check all cells for links
        cells = self._parser.select(row, "td")
        for cell in cells:
            links = self._parser.select(cell, "a")
            if links:
                href = self._parser.get_attribute(links[0], "href")
                if href and href not in ("#", "javascript:void(0)", ""):
                    return href
        
        # Check for onclick handlers that might contain URLs
        for cell in cells:
            onclick = self._parser.get_attribute(cell, "onclick")
            if onclick and "window.open" in onclick:
                # Extract URL from onclick handler
                import re
                url_match = re.search(r"window\.open\(['\"]([^'\"]+)['\"]", onclick)
                if url_match:
                    return url_match.group(1)
        
        # Check for data attributes that might contain URLs
        for cell in cells:
            data_href = self._parser.get_attribute(cell, "data-href")
            if data_href and data_href not in ("#", "javascript:void(0)", ""):
                return data_href
            
            data_url = self._parser.get_attribute(cell, "data-url")
            if data_url and data_url not in ("#", "javascript:void(0)", ""):
                return data_url
        
        # For Tokopedia, rows are clickable but don't have direct URLs
        # We'll use a special marker to indicate this row needs click-based navigation
        return "CLICKABLE_ROW"
    
    def _extract_next_page_url(self, doc: Document) -> Optional[str]:
        """Extract next page URL if available."""
        
        pagination_selectors = [
            "a[rel='next']",
            "a[data-testid='pagination-next']",
            "li.pagination-next a",
            "a.next-page",
            "button[aria-label='Next page']",
            "a[aria-label='Next']"
        ]
        
        for selector in pagination_selectors:
            elements = self._parser.select(doc, selector)
            if elements:
                href = self._parser.get_attribute(elements[0], "href")
                if href and href not in ("#", "javascript:void(0)", ""):
                    return href
        
        return None