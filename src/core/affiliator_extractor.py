"""Affiliator Extractor module for extracting structured data from Tokopedia HTML pages."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.html_parser import Document, Element, HTMLParser

logger = logging.getLogger(__name__)

# Default path for selector configuration
_DEFAULT_SELECTORS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "selectors.json",
)


@dataclass
class AffiliatorEntry:
    """Represents a single affiliator entry extracted from the list page."""

    username: Optional[str]
    kategori: Optional[str]
    pengikut: Optional[int]
    gmv: Optional[float]
    produk_terjual: Optional[int]
    rata_rata_tayangan: Optional[int]
    tingkat_interaksi: Optional[float]
    gmv_per_pembeli: Optional[float] = None
    gmv_harian: Optional[float] = None
    gmv_mingguan: Optional[float] = None
    gmv_bulanan: Optional[float] = None
    detail_url: Optional[str] = None


@dataclass
class ListPageResult:
    """Result of extracting a creator list page."""

    affiliators: List[AffiliatorEntry] = field(default_factory=list)
    next_page_url: Optional[str] = None


@dataclass
class AffiliatorDetail:
    """Complete affiliator profile extracted from a detail page."""

    username: Optional[str]
    kategori: Optional[str]
    pengikut: Optional[int]
    gmv: Optional[float]
    produk_terjual: Optional[int]
    rata_rata_tayangan: Optional[int]
    tingkat_interaksi: Optional[float]
    nomor_kontak: Optional[str]
    nomor_whatsapp: Optional[str] = None
    gmv_per_pembeli: Optional[float] = None
    gmv_harian: Optional[float] = None
    gmv_mingguan: Optional[float] = None
    gmv_bulanan: Optional[float] = None


class AffiliatorExtractor:
    """Extracts structured affiliator data from parsed Tokopedia HTML pages.

    Uses a configurable set of CSS selectors with fallback support so that
    minor page structure changes do not break extraction.
    """

    def __init__(
        self,
        selectors_path: Optional[str] = None,
        parser: Optional[HTMLParser] = None,
    ) -> None:
        """Initialize the extractor.

        Args:
            selectors_path: Path to the JSON selector configuration file.
                            Defaults to config/selectors.json.
            parser: HTMLParser instance to use. A new one is created if not provided.
        """
        self._parser = parser or HTMLParser()
        self._selectors = self._load_selectors(selectors_path or _DEFAULT_SELECTORS_PATH)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_list_page(self, doc: Document) -> ListPageResult:
        """Extract affiliators from a creator list page.

        Args:
            doc: Parsed HTML document of the list page.

        Returns:
            ListPageResult containing extracted affiliator entries and
            the next page URL (None if no more pages).
        """
        list_selectors = self._selectors.get("list_page", {})
        card_selectors: List[str] = list_selectors.get("affiliator_cards", [])

        cards: List[Element] = []
        for selector in card_selectors:
            cards = self._parser.select(doc, selector)
            if cards:
                break

        if not cards:
            logger.warning("No affiliator cards found on list page")

        affiliators: List[AffiliatorEntry] = []
        for card in cards:
            entry = self._extract_list_entry(card, list_selectors)
            affiliators.append(entry)

        next_page_url = self.extract_next_page_url(doc)

        return ListPageResult(affiliators=affiliators, next_page_url=next_page_url)

    def extract_detail_page(self, doc: Document, page_url: str = "") -> AffiliatorDetail:
        """Extract complete affiliator profile from a detail page.

        Args:
            doc: Parsed HTML document of the detail page.
            page_url: URL of the page (used for error logging).

        Returns:
            AffiliatorDetail with all available profile fields.
        """
        detail_selectors = self._selectors.get("detail_page", {})

        def _get(field_name: str, numeric: bool = False, float_val: bool = False):
            return self._extract_field(doc, detail_selectors, field_name, numeric, float_val, page_url)

        username = _get("username")
        if username is None:
            logger.warning("Could not extract username from detail page: %s", page_url)

        return AffiliatorDetail(
            username=username,
            kategori=_get("kategori"),
            pengikut=_get("pengikut", numeric=True),
            gmv=_get("gmv", float_val=True),
            produk_terjual=_get("produk_terjual", numeric=True),
            rata_rata_tayangan=_get("rata_rata_tayangan", numeric=True),
            tingkat_interaksi=_get("tingkat_interaksi", float_val=True),
            nomor_kontak=self._extract_contact(doc, detail_selectors, page_url),
            nomor_whatsapp=self._extract_whatsapp(doc, detail_selectors, page_url),
            gmv_per_pembeli=_get("gmv_per_pembeli", float_val=True),
            gmv_harian=_get("gmv_harian", float_val=True),
            gmv_mingguan=_get("gmv_mingguan", float_val=True),
            gmv_bulanan=_get("gmv_bulanan", float_val=True),
        )

    def extract_next_page_url(self, doc: Document) -> Optional[str]:
        """Extract the next page URL from pagination elements.

        Args:
            doc: Parsed HTML document.

        Returns:
            URL string for the next page, or None if no next page exists.
        """
        pagination_selectors: List[str] = (
            self._selectors.get("pagination", {}).get("next_page_url", [])
        )

        for selector in pagination_selectors:
            elements = self._parser.select(doc, selector)
            if elements:
                element = elements[0]
                # For <a> tags, get href; for <button>, look for data-href or similar
                href = self._parser.get_attribute(element, "href")
                if href and href not in ("#", "javascript:void(0)", ""):
                    return href
                # Try data-href as fallback
                data_href = self._parser.get_attribute(element, "data-href")
                if data_href:
                    return data_href

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_selectors(self, path: str) -> Dict:
        """Load selector configuration from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Selector configuration file not found: %s", path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in selector configuration %s: %s", path, exc)
            return {}

    def _extract_list_entry(
        self, card: Element, list_selectors: Dict
    ) -> AffiliatorEntry:
        """Extract a single affiliator entry from a card element."""

        def _get(field_name: str, numeric: bool = False, float_val: bool = False):
            return self._extract_field(card, list_selectors, field_name, numeric, float_val)

        # Detail URL is extracted from the card's link attribute
        detail_url = self._extract_detail_url(card, list_selectors)

        return AffiliatorEntry(
            username=_get("username"),
            kategori=_get("kategori"),
            pengikut=_get("pengikut", numeric=True),
            gmv=_get("gmv", float_val=True),
            produk_terjual=_get("produk_terjual", numeric=True),
            rata_rata_tayangan=_get("rata_rata_tayangan", numeric=True),
            tingkat_interaksi=_get("tingkat_interaksi", float_val=True),
            gmv_per_pembeli=_get("gmv_per_pembeli", float_val=True),
            gmv_harian=_get("gmv_harian", float_val=True),
            gmv_mingguan=_get("gmv_mingguan", float_val=True),
            gmv_bulanan=_get("gmv_bulanan", float_val=True),
            detail_url=detail_url,
        )

    def _extract_field(
        self,
        context: Element,
        selectors_config: Dict,
        field_name: str,
        numeric: bool = False,
        float_val: bool = False,
        page_url: str = "",
    ) -> Optional[object]:
        """Try each selector for a field in priority order.

        Args:
            context: The element to search within.
            selectors_config: Dict mapping field names to selector lists.
            field_name: The field to extract.
            numeric: If True, parse result as integer.
            float_val: If True, parse result as float.
            page_url: URL for error logging context.

        Returns:
            Extracted value (str, int, or float) or None if all selectors fail.
        """
        selector_list: List[str] = selectors_config.get(field_name, [])

        for selector in selector_list:
            elements = self._parser.select(context, selector)
            if elements:
                text = self._parser.get_text(elements[0], normalize=True)
                if text:
                    if numeric:
                        return self._parse_numeric_int(text, field_name, page_url)
                    if float_val:
                        return self._parse_numeric_float(text, field_name, page_url)
                    return text

        if selector_list:
            logger.warning(
                "All selectors failed for field '%s'%s",
                field_name,
                f" on page {page_url}" if page_url else "",
            )
        return None

    def _extract_whatsapp(
        self, doc: Element, detail_selectors: Dict, page_url: str = ""
    ) -> Optional[str]:
        whatsapp_selectors: List[str] = detail_selectors.get("nomor_whatsapp", [])
        for selector in whatsapp_selectors:
            elements = self._parser.select(doc, selector)
            if not elements:
                continue
            element = elements[0]
            href = self._parser.get_attribute(element, "href")
            if href:
                # Handle wa.me links and prefilled whatsapp URLs.
                normalized = href.lower()
                if "wa.me/" in normalized:
                    return href.rstrip("/").split("/")[-1]
                if "whatsapp" in normalized and "phone=" in normalized:
                    phone_param = href.split("phone=", 1)[-1].split("&", 1)[0].strip()
                    if phone_param:
                        return phone_param

            text = self._parser.get_text(element, normalize=True)
            if text:
                digits = re.sub(r"[^\d+]", "", text)
                if digits:
                    return digits

        logger.debug(
            "WhatsApp number not found%s",
            f" on page {page_url}" if page_url else "",
        )
        return None

    def _extract_detail_url(self, card: Element, list_selectors: Dict) -> Optional[str]:
        """Extract the detail page URL from a card element."""
        url_selectors: List[str] = list_selectors.get("detail_url", [])

        for selector in url_selectors:
            elements = self._parser.select(card, selector)
            if elements:
                href = self._parser.get_attribute(elements[0], "href")
                if href:
                    return href

        # Fallback: check if the card itself is an anchor
        href = self._parser.get_attribute(card, "href")
        if href:
            return href

        logger.warning("Could not extract detail URL from card")
        return None

    def _extract_contact(
        self, doc: Element, detail_selectors: Dict, page_url: str = ""
    ) -> Optional[str]:
        """Extract contact number from detail page.

        Handles tel: href links specially to extract the phone number.
        """
        contact_selectors: List[str] = detail_selectors.get("nomor_kontak", [])

        for selector in contact_selectors:
            elements = self._parser.select(doc, selector)
            if elements:
                element = elements[0]
                # For tel: links, prefer the href value
                href = self._parser.get_attribute(element, "href")
                if href and href.startswith("tel:"):
                    number = href[4:].strip()
                    if number:
                        return number

                text = self._parser.get_text(element, normalize=True)
                if text:
                    return text

        logger.debug(
            "Contact number not found%s",
            f" on page {page_url}" if page_url else "",
        )
        return None

    # ------------------------------------------------------------------
    # Numeric parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_numeric(value: Optional[str]) -> Optional[float]:
        """Parse a formatted numeric string to a float.

        Handles:
        - Plain integers: "1234" → 1234.0
        - Comma-separated thousands: "1,234" → 1234.0
        - K suffix (thousands): "1.2K" → 1200.0
        - M suffix (millions): "1.5M" → 1500000.0
        - B suffix (billions): "2.3B" → 2300000000.0
        - Percentage: "4.5%" → 4.5
        - "N/A", empty, None → None

        Args:
            value: The string to parse.

        Returns:
            Parsed float value, or None if the value cannot be parsed.
        """
        if value is None:
            return None

        text = value.strip()
        if not text or text.upper() in ("N/A", "-", "—", ""):
            return None

        # Remove percentage sign (keep the numeric value)
        text = text.replace("%", "").strip()

        # Remove currency symbols and whitespace
        text = re.sub(r"[Rp\s]", "", text)

        # Identify suffix
        suffix_multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        multiplier = 1
        upper = text.upper()
        for suffix, mult in suffix_multipliers.items():
            if upper.endswith(suffix):
                text = text[:-1]
                multiplier = mult
                break

        # Remove commas used as thousand separators
        text = text.replace(",", "")

        try:
            return float(text) * multiplier
        except ValueError:
            logger.warning("Could not parse numeric value: %r", value)
            return None

    def _parse_numeric_int(
        self, text: str, field_name: str = "", page_url: str = ""
    ) -> Optional[int]:
        """Parse text to int, logging a warning on failure."""
        result = self.parse_numeric(text)
        if result is None:
            logger.warning(
                "Could not parse integer for field '%s': %r%s",
                field_name,
                text,
                f" on page {page_url}" if page_url else "",
            )
            return None
        return int(result)

    def _parse_numeric_float(
        self, text: str, field_name: str = "", page_url: str = ""
    ) -> Optional[float]:
        """Parse text to float, logging a warning on failure."""
        result = self.parse_numeric(text)
        if result is None:
            logger.warning(
                "Could not parse float for field '%s': %r%s",
                field_name,
                text,
                f" on page {page_url}" if page_url else "",
            )
            return None
        return result
