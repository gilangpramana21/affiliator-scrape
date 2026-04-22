"""HTML Parser module using lxml with html5lib fallback for malformed HTML."""

import re
from typing import List, Optional

import lxml.html
from lxml.html import HtmlElement

# Type aliases matching the design doc
Document = HtmlElement
Element = HtmlElement


class HTMLParser:
    """Parses HTML into a queryable DOM structure using lxml.

    Falls back to html5lib for malformed HTML that lxml cannot handle.
    """

    def parse(self, html: str) -> Document:
        """Parse HTML string into a Document (lxml HtmlElement).

        Attempts lxml parsing first; falls back to html5lib for malformed HTML.

        Args:
            html: Raw HTML string to parse.

        Returns:
            Root HtmlElement representing the parsed document.
        """
        try:
            doc = lxml.html.fromstring(html)
            # Ensure we always return an HtmlElement (not a plain Element)
            if not isinstance(doc, HtmlElement):
                # Wrap in a proper html document
                doc = lxml.html.document_fromstring(html)
            return doc
        except Exception:
            return self._parse_with_html5lib(html)

    def _parse_with_html5lib(self, html: str) -> Document:
        """Fallback parser using html5lib for malformed HTML."""
        import html5lib
        from lxml import etree

        tree = html5lib.parse(html, treebuilder="lxml", namespaceHTMLElements=False)
        # html5lib returns an ElementTree; get the root element
        root = tree.getroot() if hasattr(tree, "getroot") else tree
        # Convert to lxml.html.HtmlElement by re-serialising through lxml.html
        serialized = etree.tostring(root, encoding="unicode", method="html")
        return lxml.html.document_fromstring(serialized)

    def select(self, doc: Document, selector: str) -> List[Element]:
        """Query document using a CSS selector.

        Args:
            doc: Parsed document root element.
            selector: CSS selector string.

        Returns:
            List of matching elements, or empty list if none match.
        """
        try:
            return doc.cssselect(selector)
        except Exception:
            return []

    def xpath(self, doc: Document, xpath: str) -> List[Element]:
        """Query document using an XPath expression.

        Args:
            doc: Parsed document root element.
            xpath: XPath expression string.

        Returns:
            List of matching elements, or empty list if none match.
        """
        try:
            results = doc.xpath(xpath)
            # xpath() can return strings/numbers for expressions like text()
            return [r for r in results if isinstance(r, HtmlElement)]
        except Exception:
            return []

    def get_text(self, element: Element, normalize: bool = True) -> str:
        """Extract text content from an element.

        Args:
            element: The element to extract text from.
            normalize: If True, strips leading/trailing whitespace and
                       collapses multiple consecutive spaces into one.

        Returns:
            Text content of the element.
        """
        text = element.text_content()
        if normalize:
            text = text.strip()
            text = re.sub(r"\s+", " ", text)
        return text

    def get_attribute(self, element: Element, attr: str) -> Optional[str]:
        """Get an attribute value from an element.

        Args:
            element: The element to query.
            attr: Attribute name.

        Returns:
            Attribute value string, or None if the attribute does not exist.
        """
        return element.get(attr)
