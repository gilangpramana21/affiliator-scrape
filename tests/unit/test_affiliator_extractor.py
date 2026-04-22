"""Unit tests for AffiliatorExtractor using fabricated Tokopedia-like HTML."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

import pytest

from src.core.affiliator_extractor import (
    AffiliatorDetail,
    AffiliatorEntry,
    AffiliatorExtractor,
    ListPageResult,
)
from src.core.html_parser import HTMLParser

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

LIST_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Affiliate Creator List</title></head>
<body>
  <div class="creator-list">
    <div class="creator-card">
      <a class="creator-card-link" href="/affiliate/creator/johndoe">
        <div class="creator-name"><span class="username">johndoe</span></div>
        <span class="creator-category">Fashion</span>
        <span class="follower-count">1.2K</span>
        <span class="gmv-value">5,000,000</span>
        <span class="product-sold-count">150</span>
        <span class="avg-view-count">3.5K</span>
        <span class="engagement-rate">4.5%</span>
      </a>
    </div>
    <div class="creator-card">
      <a class="creator-card-link" href="/affiliate/creator/janedoe">
        <div class="creator-name"><span class="username">janedoe</span></div>
        <span class="creator-category">Beauty</span>
        <span class="follower-count">50K</span>
        <span class="gmv-value">25,000,000</span>
        <span class="product-sold-count">1,234</span>
        <span class="avg-view-count">15.5K</span>
        <span class="engagement-rate">6.2%</span>
      </a>
    </div>
    <div class="creator-card">
      <a class="creator-card-link" href="/affiliate/creator/nodata">
        <div class="creator-name"><span class="username">nodata</span></div>
      </a>
    </div>
  </div>
  <a rel="next" href="/affiliate/creators?page=2">Next</a>
</body>
</html>
"""

LIST_PAGE_NO_NEXT_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-list">
    <div class="creator-card">
      <a class="creator-card-link" href="/affiliate/creator/user1">
        <div class="creator-name"><span class="username">user1</span></div>
        <span class="creator-category">Tech</span>
        <span class="follower-count">500</span>
        <span class="gmv-value">1,000,000</span>
        <span class="product-sold-count">50</span>
        <span class="avg-view-count">1K</span>
        <span class="engagement-rate">3.0%</span>
      </a>
    </div>
  </div>
</body>
</html>
"""

DETAIL_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Creator Profile - johndoe</title></head>
<body>
  <div class="creator-profile">
    <h1 class="profile-username">johndoe</h1>
    <span class="profile-category">Fashion</span>
    <div class="profile-stats">
      <span class="profile-follower-count">1.2K</span>
      <span class="profile-gmv">5,000,000</span>
      <span class="profile-products-sold">150</span>
      <span class="profile-avg-views">3.5K</span>
      <span class="profile-engagement-rate">4.5%</span>
    </div>
    <div class="contact-info">
      <span class="contact-number">08123456789</span>
    </div>
  </div>
</body>
</html>
"""

DETAIL_PAGE_TEL_LINK_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-profile">
    <h1 class="profile-username">teluser</h1>
    <div class="contact-info">
      <a href="tel:+628123456789" class="contact-number">+628123456789</a>
    </div>
  </div>
</body>
</html>
"""

DETAIL_PAGE_NO_CONTACT_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-profile">
    <h1 class="profile-username">nocontact</h1>
    <span class="profile-category">Gaming</span>
    <div class="profile-stats">
      <span class="profile-follower-count">10K</span>
    </div>
  </div>
</body>
</html>
"""

FALLBACK_SELECTOR_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-card">
    <a class="creator-card-link" href="/affiliate/creator/fallbackuser">
      <span data-testid="creator-username">fallbackuser</span>
      <div data-metric="followers"><span class="count">2,500</span></div>
    </a>
  </div>
</body>
</html>
"""

PAGINATION_DATA_HREF_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-card">
    <a class="creator-card-link" href="/affiliate/creator/u1">
      <span class="username">u1</span>
    </a>
  </div>
  <a data-testid="pagination-next" href="/affiliate/creators?page=3">Next</a>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_extractor(selectors: Optional[dict] = None) -> AffiliatorExtractor:
    """Create an AffiliatorExtractor with optional custom selectors written to a temp file."""
    if selectors is None:
        # Use the real selectors.json from the project
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        selectors_path = os.path.join(project_root, "config", "selectors.json")
        return AffiliatorExtractor(selectors_path=selectors_path)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(selectors, f)
        tmp_path = f.name

    extractor = AffiliatorExtractor(selectors_path=tmp_path)
    os.unlink(tmp_path)
    return extractor


def parse_html(html: str) -> object:
    return HTMLParser().parse(html)


# ---------------------------------------------------------------------------
# Tests: extract_list_page
# ---------------------------------------------------------------------------

class TestExtractListPage:
    def test_returns_list_page_result(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert isinstance(result, ListPageResult)

    def test_extracts_correct_number_of_affiliators(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert len(result.affiliators) == 3

    def test_extracts_username(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].username == "johndoe"
        assert result.affiliators[1].username == "janedoe"

    def test_extracts_kategori(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].kategori == "Fashion"
        assert result.affiliators[1].kategori == "Beauty"

    def test_extracts_pengikut_as_int(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].pengikut == 1200
        assert result.affiliators[1].pengikut == 50000

    def test_extracts_gmv_as_float(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].gmv == 5_000_000.0
        assert result.affiliators[1].gmv == 25_000_000.0

    def test_extracts_produk_terjual(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].produk_terjual == 150
        assert result.affiliators[1].produk_terjual == 1234

    def test_extracts_rata_rata_tayangan(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].rata_rata_tayangan == 3500
        assert result.affiliators[1].rata_rata_tayangan == 15500

    def test_extracts_tingkat_interaksi(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].tingkat_interaksi == pytest.approx(4.5)
        assert result.affiliators[1].tingkat_interaksi == pytest.approx(6.2)

    def test_extracts_detail_url(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].detail_url == "/affiliate/creator/johndoe"
        assert result.affiliators[1].detail_url == "/affiliate/creator/janedoe"

    def test_missing_fields_are_null(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        # Third card has no stats
        entry = result.affiliators[2]
        assert entry.username == "nodata"
        assert entry.kategori is None
        assert entry.pengikut is None
        assert entry.gmv is None
        assert entry.produk_terjual is None
        assert entry.rata_rata_tayangan is None
        assert entry.tingkat_interaksi is None

    def test_next_page_url_extracted(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.next_page_url == "/affiliate/creators?page=2"

    def test_next_page_url_none_when_absent(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_NO_NEXT_HTML)
        result = extractor.extract_list_page(doc)
        assert result.next_page_url is None

    def test_empty_page_returns_empty_list(self):
        extractor = make_extractor()
        doc = parse_html("<html><body></body></html>")
        result = extractor.extract_list_page(doc)
        assert result.affiliators == []
        assert result.next_page_url is None


# ---------------------------------------------------------------------------
# Tests: extract_detail_page
# ---------------------------------------------------------------------------

class TestExtractDetailPage:
    def test_returns_affiliator_detail(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert isinstance(result, AffiliatorDetail)

    def test_extracts_username(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.username == "johndoe"

    def test_extracts_kategori(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.kategori == "Fashion"

    def test_extracts_pengikut(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.pengikut == 1200

    def test_extracts_gmv(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.gmv == 5_000_000.0

    def test_extracts_produk_terjual(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.produk_terjual == 150

    def test_extracts_rata_rata_tayangan(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.rata_rata_tayangan == 3500

    def test_extracts_tingkat_interaksi(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.tingkat_interaksi == pytest.approx(4.5)

    def test_extracts_nomor_kontak(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.nomor_kontak == "08123456789"

    def test_extracts_tel_link_contact(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_TEL_LINK_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.nomor_kontak == "+628123456789"

    def test_nomor_kontak_null_when_absent(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_NO_CONTACT_HTML)
        result = extractor.extract_detail_page(doc)
        assert result.nomor_kontak is None

    def test_accepts_page_url_for_logging(self):
        extractor = make_extractor()
        doc = parse_html(DETAIL_PAGE_HTML)
        # Should not raise
        result = extractor.extract_detail_page(doc, page_url="https://example.com/creator/johndoe")
        assert result.username == "johndoe"


# ---------------------------------------------------------------------------
# Tests: extract_next_page_url
# ---------------------------------------------------------------------------

class TestExtractNextPageUrl:
    def test_extracts_rel_next(self):
        extractor = make_extractor()
        doc = parse_html(LIST_PAGE_HTML)
        url = extractor.extract_next_page_url(doc)
        assert url == "/affiliate/creators?page=2"

    def test_extracts_data_testid_pagination_next(self):
        extractor = make_extractor()
        doc = parse_html(PAGINATION_DATA_HREF_HTML)
        url = extractor.extract_next_page_url(doc)
        assert url == "/affiliate/creators?page=3"

    def test_returns_none_when_no_pagination(self):
        extractor = make_extractor()
        doc = parse_html("<html><body><p>No pagination</p></body></html>")
        url = extractor.extract_next_page_url(doc)
        assert url is None

    def test_ignores_hash_href(self):
        html = '<html><body><a rel="next" href="#">Next</a></body></html>'
        extractor = make_extractor()
        doc = parse_html(html)
        url = extractor.extract_next_page_url(doc)
        assert url is None


# ---------------------------------------------------------------------------
# Tests: fallback selectors
# ---------------------------------------------------------------------------

class TestFallbackSelectors:
    def test_falls_back_to_data_testid_username(self):
        extractor = make_extractor()
        doc = parse_html(FALLBACK_SELECTOR_HTML)
        result = extractor.extract_list_page(doc)
        assert len(result.affiliators) == 1
        assert result.affiliators[0].username == "fallbackuser"

    def test_falls_back_to_data_metric_followers(self):
        extractor = make_extractor()
        doc = parse_html(FALLBACK_SELECTOR_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].pengikut == 2500

    def test_missing_field_returns_null_not_exception(self):
        extractor = make_extractor()
        doc = parse_html("<html><body><div class='creator-card'><a class='creator-card-link' href='/x'></a></div></body></html>")
        result = extractor.extract_list_page(doc)
        assert result.affiliators[0].username is None


# ---------------------------------------------------------------------------
# Tests: parse_numeric (static method)
# ---------------------------------------------------------------------------

class TestParseNumeric:
    def test_plain_integer(self):
        assert AffiliatorExtractor.parse_numeric("1234") == 1234.0

    def test_zero(self):
        assert AffiliatorExtractor.parse_numeric("0") == 0.0

    def test_comma_separated(self):
        assert AffiliatorExtractor.parse_numeric("1,234") == 1234.0

    def test_large_comma_separated(self):
        assert AffiliatorExtractor.parse_numeric("1,234,567") == 1_234_567.0

    def test_k_suffix_integer(self):
        assert AffiliatorExtractor.parse_numeric("1K") == 1000.0

    def test_k_suffix_decimal(self):
        assert AffiliatorExtractor.parse_numeric("1.2K") == 1200.0

    def test_m_suffix(self):
        assert AffiliatorExtractor.parse_numeric("1.5M") == 1_500_000.0

    def test_b_suffix(self):
        assert AffiliatorExtractor.parse_numeric("2.3B") == 2_300_000_000.0

    def test_k_suffix_lowercase(self):
        assert AffiliatorExtractor.parse_numeric("5k") == 5000.0

    def test_m_suffix_lowercase(self):
        assert AffiliatorExtractor.parse_numeric("3m") == 3_000_000.0

    def test_percentage_stripped(self):
        assert AffiliatorExtractor.parse_numeric("4.5%") == pytest.approx(4.5)

    def test_none_returns_none(self):
        assert AffiliatorExtractor.parse_numeric(None) is None

    def test_empty_string_returns_none(self):
        assert AffiliatorExtractor.parse_numeric("") is None

    def test_na_returns_none(self):
        assert AffiliatorExtractor.parse_numeric("N/A") is None

    def test_dash_returns_none(self):
        assert AffiliatorExtractor.parse_numeric("-") is None

    def test_non_numeric_returns_none(self):
        assert AffiliatorExtractor.parse_numeric("abc") is None

    def test_whitespace_stripped(self):
        assert AffiliatorExtractor.parse_numeric("  500  ") == 500.0

    def test_50k(self):
        assert AffiliatorExtractor.parse_numeric("50K") == 50_000.0

    def test_15_5k(self):
        assert AffiliatorExtractor.parse_numeric("15.5K") == 15_500.0

    def test_25_million(self):
        assert AffiliatorExtractor.parse_numeric("25,000,000") == 25_000_000.0


# ---------------------------------------------------------------------------
# Tests: selector config loading
# ---------------------------------------------------------------------------

class TestSelectorConfigLoading:
    def test_missing_file_returns_empty_selectors(self):
        extractor = AffiliatorExtractor(selectors_path="/nonexistent/path/selectors.json")
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        # With no selectors, no cards found → empty list
        assert result.affiliators == []

    def test_invalid_json_returns_empty_selectors(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{ invalid json }")
            tmp_path = f.name

        extractor = AffiliatorExtractor(selectors_path=tmp_path)
        os.unlink(tmp_path)
        doc = parse_html(LIST_PAGE_HTML)
        result = extractor.extract_list_page(doc)
        assert result.affiliators == []

    def test_custom_selectors_used(self):
        custom_selectors = {
            "list_page": {
                "affiliator_cards": ["div.custom-card"],
                "username": ["span.custom-name"],
                "detail_url": ["a.custom-link"],
            },
            "pagination": {},
        }
        html = """
        <html><body>
          <div class="custom-card">
            <a class="custom-link" href="/custom/user1">
              <span class="custom-name">customuser</span>
            </a>
          </div>
        </body></html>
        """
        extractor = make_extractor(custom_selectors)
        doc = parse_html(html)
        result = extractor.extract_list_page(doc)
        assert len(result.affiliators) == 1
        assert result.affiliators[0].username == "customuser"
        assert result.affiliators[0].detail_url == "/custom/user1"
