"""Property-based tests for HTMLParser.

**Validates: Requirements 4**
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from src.core.html_parser import HTMLParser


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

# Simple valid HTML strings
html_strategy = st.one_of(
    # Minimal HTML with text content
    st.builds(
        lambda tag, text: f"<{tag}>{text}</{tag}>",
        tag=st.sampled_from(["div", "span", "p", "section", "article"]),
        text=st.text(min_size=0, max_size=200),
    ),
    # Full HTML document
    st.builds(
        lambda body: f"<html><head><title>Test</title></head><body>{body}</body></html>",
        body=st.text(min_size=0, max_size=200),
    ),
    # Just a text node wrapped in a div
    st.text(min_size=0, max_size=100).map(lambda t: f"<div>{t}</div>"),
)

# CSS selectors that are syntactically valid but unlikely to match anything
non_matching_selectors = st.sampled_from([
    "div.nonexistent-class-xyz",
    "#nonexistent-id-xyz",
    "span[data-nonexistent='xyz']",
    "table.missing > tr > td.absent",
    "article.ghost",
])

# Whitespace-heavy text for normalization tests
whitespace_text_strategy = st.builds(
    lambda prefix, middle, suffix: f"<p>{'  ' * prefix}hello{'   ' * middle}world{'  ' * suffix}</p>",
    prefix=st.integers(min_value=0, max_value=5),
    middle=st.integers(min_value=1, max_value=5),
    suffix=st.integers(min_value=0, max_value=5),
)


# ---------------------------------------------------------------------------
# Property 13: parse(html) always returns a non-None document
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 13: parse() Always Returns Non-None Document"
)
@settings(max_examples=100)
@given(html=html_strategy)
def test_parse_always_returns_non_none(html: str):
    """**Validates: Requirements 4.1, 4.7**

    FOR ALL HTML strings (including malformed ones), parse() SHALL always
    return a non-None document object.
    """
    parser = HTMLParser()
    doc = parser.parse(html)
    assert doc is not None


# ---------------------------------------------------------------------------
# Property 14: select() with non-matching selector always returns empty list
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 14: select() With Non-Matching Selector Returns Empty List"
)
@settings(max_examples=100)
@given(
    html=html_strategy,
    selector=non_matching_selectors,
)
def test_select_non_matching_returns_empty_list(html: str, selector: str):
    """**Validates: Requirements 4.3**

    FOR ALL HTML documents and non-matching CSS selectors, select() SHALL
    return an empty list (never None, never raise an exception).
    """
    parser = HTMLParser()
    doc = parser.parse(html)
    result = parser.select(doc, selector)
    assert result == []
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Property 15: get_text(normalize=True) never contains leading/trailing whitespace
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 15: get_text(normalize=True) Never Has Leading/Trailing Whitespace"
)
@settings(max_examples=100)
@given(html=whitespace_text_strategy)
def test_get_text_normalized_no_leading_trailing_whitespace(html: str):
    """**Validates: Requirements 4.5**

    FOR ALL HTML elements, get_text(normalize=True) SHALL never return a
    string with leading or trailing whitespace.
    """
    parser = HTMLParser()
    doc = parser.parse(html)
    text = parser.get_text(doc, normalize=True)
    assert text == text.strip(), (
        f"Normalized text has leading/trailing whitespace: {text!r}"
    )


# ---------------------------------------------------------------------------
# Property 16: get_text(normalize=True) never contains consecutive spaces
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 16: get_text(normalize=True) Never Contains Consecutive Spaces"
)
@settings(max_examples=100)
@given(html=whitespace_text_strategy)
def test_get_text_normalized_no_consecutive_spaces(html: str):
    """**Validates: Requirements 4.5**

    FOR ALL HTML elements, get_text(normalize=True) SHALL never contain
    two or more consecutive space characters.
    """
    parser = HTMLParser()
    doc = parser.parse(html)
    text = parser.get_text(doc, normalize=True)
    assert "  " not in text, (
        f"Normalized text contains consecutive spaces: {text!r}"
    )
