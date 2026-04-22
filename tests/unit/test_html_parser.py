"""Unit tests for HTMLParser (Task 4)."""

import pytest
from src.core.html_parser import HTMLParser


SIMPLE_HTML = """
<html>
  <head><title>Test Page</title></head>
  <body>
    <div id="main" class="container">
      <h1 class="title">Hello World</h1>
      <p class="desc">  This   has   extra   spaces  </p>
      <a href="https://example.com" data-id="42">Click here</a>
      <ul>
        <li class="item">Item 1</li>
        <li class="item">Item 2</li>
        <li class="item">Item 3</li>
      </ul>
    </div>
  </body>
</html>
"""

MALFORMED_HTML = """
<html>
  <body>
    <div>
      <p>Unclosed paragraph
      <span>Nested <b>bold without close
      <a href="http://test.com">Link
    </div>
  </body>
"""

WHITESPACE_HTML = """
<html><body>
  <p>  leading and trailing  </p>
  <p>multiple   spaces   between   words</p>
  <p>
    newlines
    and
    tabs\there
  </p>
</body></html>
"""


@pytest.fixture
def parser():
    return HTMLParser()


# ── Task 4.1 / 4.2: parse() ──────────────────────────────────────────────────

class TestParse:
    def test_parse_returns_element(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        assert doc is not None

    def test_parse_valid_html(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        # Should be able to find the title element
        results = parser.select(doc, "h1.title")
        assert len(results) == 1

    def test_parse_empty_string(self, parser):
        doc = parser.parse("")
        assert doc is not None

    def test_parse_minimal_html(self, parser):
        doc = parser.parse("<p>hello</p>")
        assert doc is not None
        results = parser.select(doc, "p")
        assert len(results) >= 1


# ── Task 4.3: select() ───────────────────────────────────────────────────────

class TestSelect:
    def test_select_by_id(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.select(doc, "#main")
        assert len(results) == 1

    def test_select_by_class(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.select(doc, ".item")
        assert len(results) == 3

    def test_select_by_tag(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.select(doc, "li")
        assert len(results) == 3

    def test_select_nested(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.select(doc, "div.container a")
        assert len(results) == 1

    def test_select_no_match_returns_empty(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.select(doc, ".nonexistent")
        assert results == []

    def test_select_invalid_selector_returns_empty(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        # An invalid CSS selector should not raise; return empty list
        results = parser.select(doc, "::invalid-pseudo")
        assert isinstance(results, list)


# ── Task 4.4: xpath() ────────────────────────────────────────────────────────

class TestXPath:
    def test_xpath_by_tag(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.xpath(doc, ".//li")
        assert len(results) == 3

    def test_xpath_by_attribute(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.xpath(doc, ".//*[@id='main']")
        assert len(results) == 1

    def test_xpath_no_match_returns_empty(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.xpath(doc, ".//section")
        assert results == []

    def test_xpath_invalid_expression_returns_empty(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        results = parser.xpath(doc, "///invalid[[[")
        assert isinstance(results, list)

    def test_xpath_text_expression_excluded(self, parser):
        """XPath text() nodes should not appear in the returned list."""
        doc = parser.parse(SIMPLE_HTML)
        results = parser.xpath(doc, ".//h1/text()")
        # text nodes are strings, not HtmlElements; should be filtered out
        assert results == []


# ── Task 4.5: get_text() ─────────────────────────────────────────────────────

class TestGetText:
    def test_get_text_basic(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        h1 = parser.select(doc, "h1")[0]
        assert parser.get_text(h1) == "Hello World"

    def test_get_text_strips_whitespace(self, parser):
        doc = parser.parse(WHITESPACE_HTML)
        p = parser.select(doc, "p")[0]
        text = parser.get_text(p)
        assert not text.startswith(" ")
        assert not text.endswith(" ")

    def test_get_text_collapses_spaces(self, parser):
        doc = parser.parse(WHITESPACE_HTML)
        paragraphs = parser.select(doc, "p")
        # Second paragraph has multiple spaces between words
        text = parser.get_text(paragraphs[1])
        assert "  " not in text  # no double spaces

    def test_get_text_collapses_newlines(self, parser):
        doc = parser.parse(WHITESPACE_HTML)
        paragraphs = parser.select(doc, "p")
        text = parser.get_text(paragraphs[2])
        assert "\n" not in text
        assert "  " not in text

    def test_get_text_normalize_false(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        p = parser.select(doc, "p.desc")[0]
        raw = parser.get_text(p, normalize=False)
        # Raw text should preserve original whitespace
        assert "  " in raw or raw != raw.strip()

    def test_get_text_nested_elements(self, parser):
        html = "<div><span>Hello</span> <span>World</span></div>"
        doc = parser.parse(html)
        div = parser.select(doc, "div")[0]
        text = parser.get_text(div)
        assert "Hello" in text
        assert "World" in text


# ── Task 4.6: get_attribute() ────────────────────────────────────────────────

class TestGetAttribute:
    def test_get_existing_attribute(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        a = parser.select(doc, "a")[0]
        assert parser.get_attribute(a, "href") == "https://example.com"

    def test_get_data_attribute(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        a = parser.select(doc, "a")[0]
        assert parser.get_attribute(a, "data-id") == "42"

    def test_get_missing_attribute_returns_none(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        a = parser.select(doc, "a")[0]
        assert parser.get_attribute(a, "nonexistent") is None

    def test_get_class_attribute(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        div = parser.select(doc, "#main")[0]
        assert parser.get_attribute(div, "class") == "container"

    def test_get_id_attribute(self, parser):
        doc = parser.parse(SIMPLE_HTML)
        div = parser.select(doc, "#main")[0]
        assert parser.get_attribute(div, "id") == "main"


# ── Task 4.7: malformed HTML / html5lib fallback ─────────────────────────────

class TestMalformedHTML:
    def test_parse_malformed_does_not_raise(self, parser):
        doc = parser.parse(MALFORMED_HTML)
        assert doc is not None

    def test_parse_malformed_recovers_content(self, parser):
        doc = parser.parse(MALFORMED_HTML)
        # Should still find the div and its content
        divs = parser.select(doc, "div")
        assert len(divs) >= 1

    def test_parse_malformed_link_accessible(self, parser):
        doc = parser.parse(MALFORMED_HTML)
        links = parser.select(doc, "a")
        assert len(links) >= 1
        assert parser.get_attribute(links[0], "href") == "http://test.com"

    def test_parse_deeply_malformed(self, parser):
        bad_html = "<html><body><table><tr><td><div><p>text"
        doc = parser.parse(bad_html)
        assert doc is not None
        results = parser.select(doc, "p")
        assert len(results) >= 1

    def test_parse_html_with_encoding_errors(self, parser):
        html_with_entities = "<p>Price: &lt;100&gt; &amp; more</p>"
        doc = parser.parse(html_with_entities)
        p = parser.select(doc, "p")[0]
        text = parser.get_text(p)
        assert "100" in text
