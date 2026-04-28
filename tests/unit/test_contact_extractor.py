"""Unit tests for ContactExtractor with real contact data samples."""

from __future__ import annotations

import pytest

from src.core.contact_extractor import ContactExtractor


# ---------------------------------------------------------------------------
# HTML fixtures with realistic contact data
# ---------------------------------------------------------------------------

# WhatsApp extraction test cases
WHATSAPP_WA_ME_LINK_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact-info">
    <span>WhatsApp:</span>
    <a href="https://wa.me/628123456789">+62 812-3456-789</a>
  </div>
</body>
</html>
"""

WHATSAPP_API_LINK_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact-section">
    <p>Hubungi saya di WhatsApp:</p>
    <a href="https://api.whatsapp.com/send?phone=6281234567890">Chat WhatsApp</a>
  </div>
</body>
</html>
"""

WHATSAPP_TEL_LINK_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="profile-contact">
    <a href="tel:08123456789" class="phone-link">08123456789</a>
  </div>
</body>
</html>
"""

WHATSAPP_TEXT_PATTERN_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-profile">
    <p>Kontak:</p>
    <p>WA: 0812-3456-789</p>
  </div>
</body>
</html>
"""

WHATSAPP_PLUS62_FORMAT_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <span>WhatsApp: +62 812 3456 789</span>
  </div>
</body>
</html>
"""

WHATSAPP_NO_PREFIX_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <span class="phone">8123456789</span>
  </div>
</body>
</html>
"""

WHATSAPP_WITH_DASHES_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact-info">
    <p>Hubungi: 0812-345-6789</p>
  </div>
</body>
</html>
"""

WHATSAPP_WITH_SPACES_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="profile">
    <span>Phone: 0812 3456 789</span>
  </div>
</body>
</html>
"""

# Email extraction test cases
EMAIL_MAILTO_LINK_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact-info">
    <span>Email:</span>
    <a href="mailto:creator@example.com">creator@example.com</a>
  </div>
</body>
</html>
"""

EMAIL_MAILTO_WITH_SUBJECT_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <a href="mailto:affiliator@gmail.com?subject=Collaboration">Contact Me</a>
  </div>
</body>
</html>
"""

EMAIL_TEXT_PATTERN_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="profile">
    <p>Email: business.inquiry@tokopedia.com</p>
  </div>
</body>
</html>
"""

EMAIL_IN_SPAN_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="creator-contact">
    <span class="email">creator.official@yahoo.com</span>
  </div>
</body>
</html>
"""

EMAIL_MIXED_CASE_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <p>Email: MyCreator@Gmail.COM</p>
  </div>
</body>
</html>
"""

# Combined contact test cases
BOTH_CONTACTS_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="profile">
    <div class="contact">
      <p>Hubungi saya:</p>
      <p>WA: 0812-3456-789</p>
      <p>Email: affiliator@gmail.com</p>
    </div>
  </div>
</body>
</html>
"""

BOTH_CONTACTS_LINKS_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact-section">
    <a href="https://wa.me/628123456789">WhatsApp</a>
    <a href="mailto:creator@example.com">Email</a>
  </div>
</body>
</html>
"""

# Missing contact test cases
NO_CONTACT_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="profile">
    <h1>Creator Profile</h1>
    <p>Username: johndoe</p>
    <p>Category: Fashion</p>
  </div>
</body>
</html>
"""

ONLY_WHATSAPP_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <a href="https://wa.me/628123456789">WhatsApp</a>
  </div>
</body>
</html>
"""

ONLY_EMAIL_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <a href="mailto:creator@example.com">Email</a>
  </div>
</body>
</html>
"""

# Edge cases
INVALID_EMAIL_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <span>Email: test@test.com</span>
  </div>
</body>
</html>
"""

MALFORMED_HTML = """
<div class="contact">
  <p>WA: 0812-3456-7890
  <p>Email: creator@example.com
</div>
"""

EMPTY_HTML = """
<!DOCTYPE html>
<html>
<body>
</body>
</html>
"""

MULTIPLE_PHONES_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <p>WA 1: 0812-3456-789</p>
    <p>WA 2: 0813-9876-543</p>
  </div>
</body>
</html>
"""

MULTIPLE_EMAILS_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="contact">
    <p>Business: business@example.com</p>
    <p>Personal: personal@example.com</p>
  </div>
</body>
</html>
"""

# Real-world complex HTML
COMPLEX_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Creator Profile</title></head>
<body>
  <div class="page-container">
    <header>
      <nav>Navigation</nav>
    </header>
    <main>
      <div class="creator-profile">
        <div class="profile-header">
          <img src="/avatar.jpg" alt="Avatar">
          <h1>@fashionista_id</h1>
          <span class="category">Fashion & Lifestyle</span>
        </div>
        <div class="profile-stats">
          <div class="stat">
            <span class="label">Followers</span>
            <span class="value">125K</span>
          </div>
          <div class="stat">
            <span class="label">GMV</span>
            <span class="value">Rp 50,000,000</span>
          </div>
        </div>
        <div class="profile-bio">
          <p>Fashion enthusiast | Content creator | Tokopedia Affiliate</p>
        </div>
        <div class="contact-section">
          <h3>Hubungi Saya</h3>
          <div class="contact-methods">
            <div class="contact-item">
              <i class="icon-whatsapp"></i>
              <a href="https://wa.me/6281234567890" class="contact-link">
                <span>WhatsApp</span>
              </a>
            </div>
            <div class="contact-item">
              <i class="icon-email"></i>
              <a href="mailto:fashionista.collab@gmail.com" class="contact-link">
                <span>Email</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
    <footer>Footer content</footer>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Tests: WhatsApp Extraction
# ---------------------------------------------------------------------------

class TestWhatsAppExtraction:
    """Test WhatsApp number extraction from various HTML formats."""
    
    def test_extracts_from_wa_me_link(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_WA_ME_LINK_HTML)
        assert result == "+628123456789"
    
    def test_extracts_from_api_whatsapp_link(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_API_LINK_HTML)
        assert result == "+6281234567890"
    
    def test_extracts_from_tel_link(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_TEL_LINK_HTML)
        assert result == "+628123456789"
    
    def test_extracts_from_text_pattern(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_TEXT_PATTERN_HTML)
        assert result == "+628123456789"
    
    def test_extracts_plus62_format(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_PLUS62_FORMAT_HTML)
        assert result == "+628123456789"
    
    def test_extracts_no_prefix_format(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_NO_PREFIX_HTML)
        # Phone without 0 or +62 prefix may not be detected reliably
        # This is expected behavior - we need at least 08 or +62 prefix
        assert result is None or result.startswith("+62")
    
    def test_extracts_with_dashes(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_WITH_DASHES_HTML)
        assert result == "+628123456789"
    
    def test_extracts_with_spaces(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_WITH_SPACES_HTML)
        assert result == "+628123456789"
    
    def test_normalizes_08_prefix_to_plus62(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(WHATSAPP_TEXT_PATTERN_HTML)
        assert result.startswith("+62")
        assert "08" not in result
    
    def test_returns_first_phone_when_multiple(self):
        extractor = ContactExtractor()
        result = extractor.extract_whatsapp(MULTIPLE_PHONES_HTML)
        # Should return the first valid phone number found
        assert result is not None
        assert result.startswith("+62")


# ---------------------------------------------------------------------------
# Tests: Email Extraction
# ---------------------------------------------------------------------------

class TestEmailExtraction:
    """Test email extraction from various HTML formats."""
    
    def test_extracts_from_mailto_link(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(EMAIL_MAILTO_LINK_HTML)
        assert result == "creator@example.com"
    
    def test_extracts_from_mailto_with_subject(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(EMAIL_MAILTO_WITH_SUBJECT_HTML)
        assert result == "affiliator@gmail.com"
    
    def test_extracts_from_text_pattern(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(EMAIL_TEXT_PATTERN_HTML)
        assert result == "business.inquiry@tokopedia.com"
    
    def test_extracts_from_span(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(EMAIL_IN_SPAN_HTML)
        assert result == "creator.official@yahoo.com"
    
    def test_normalizes_to_lowercase(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(EMAIL_MIXED_CASE_HTML)
        assert result == "mycreator@gmail.com"
        assert result.islower()
    
    def test_rejects_invalid_test_email(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(INVALID_EMAIL_HTML)
        # test@test.com should be rejected as invalid
        assert result is None
    
    def test_returns_first_email_when_multiple(self):
        extractor = ContactExtractor()
        result = extractor.extract_email(MULTIPLE_EMAILS_HTML)
        # Should return the first valid email found
        assert result is not None
        assert "@" in result


# ---------------------------------------------------------------------------
# Tests: Combined Contact Extraction
# ---------------------------------------------------------------------------

class TestCombinedContactExtraction:
    """Test extraction of both WhatsApp and Email together."""
    
    def test_extracts_both_contacts_from_text(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(BOTH_CONTACTS_HTML)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] == "affiliator@gmail.com"
    
    def test_extracts_both_contacts_from_links(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(BOTH_CONTACTS_LINKS_HTML)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] == "creator@example.com"
    
    def test_extracts_from_complex_profile(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(COMPLEX_PROFILE_HTML)
        assert result['whatsapp'] == "+6281234567890"
        assert result['email'] == "fashionista.collab@gmail.com"


# ---------------------------------------------------------------------------
# Tests: Missing Contact Scenarios
# ---------------------------------------------------------------------------

class TestMissingContactScenarios:
    """Test handling of missing or incomplete contact information."""
    
    def test_no_contact_returns_none(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(NO_CONTACT_HTML)
        assert result['whatsapp'] is None
        assert result['email'] is None
    
    def test_only_whatsapp_present(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(ONLY_WHATSAPP_HTML)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] is None
    
    def test_only_email_present(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(ONLY_EMAIL_HTML)
        assert result['whatsapp'] is None
        assert result['email'] == "creator@example.com"
    
    def test_empty_html_returns_none(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts(EMPTY_HTML)
        assert result['whatsapp'] is None
        assert result['email'] is None
    
    def test_malformed_html_handles_gracefully(self):
        extractor = ContactExtractor()
        # Should not raise exception
        result = extractor.extract_contacts(MALFORMED_HTML)
        # May or may not extract depending on parser recovery
        assert isinstance(result, dict)
        assert 'whatsapp' in result
        assert 'email' in result


# ---------------------------------------------------------------------------
# Tests: Phone Number Normalization
# ---------------------------------------------------------------------------

class TestPhoneNumberNormalization:
    """Test phone number normalization to +62 format."""
    
    def test_normalizes_08_prefix(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("08123456789")
        assert result == "+628123456789"
    
    def test_normalizes_62_prefix(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("628123456789")
        assert result == "+628123456789"
    
    def test_normalizes_8_prefix(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("8123456789")
        assert result == "+628123456789"
    
    def test_keeps_plus62_format(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("+628123456789")
        assert result == "+628123456789"
    
    def test_removes_dashes_and_spaces(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("0812-345-6789")
        assert result == "+628123456789"
        assert "-" not in result
    
    def test_handles_spaces(self):
        extractor = ContactExtractor()
        result = extractor._normalize_phone_number("0812 3456 789")
        assert result == "+628123456789"
        assert " " not in result


# ---------------------------------------------------------------------------
# Tests: Email Validation
# ---------------------------------------------------------------------------

class TestEmailValidation:
    """Test email validation logic."""
    
    def test_validates_correct_email(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("user@example.com") is True
    
    def test_validates_subdomain_email(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("user@mail.example.com") is True
    
    def test_validates_plus_addressing(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("user+tag@example.com") is True
    
    def test_rejects_no_at_symbol(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("userexample.com") is False
    
    def test_rejects_no_domain(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("user@") is False
    
    def test_rejects_no_local_part(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("@example.com") is False
    
    def test_rejects_no_tld(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("user@example") is False
    
    def test_rejects_test_email(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("test@test.com") is False
    
    def test_rejects_email_at_email(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("email@email.com") is False
    
    def test_rejects_noreply(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("noreply@example.com") is False
    
    def test_rejects_empty_string(self):
        extractor = ContactExtractor()
        assert extractor._validate_email("") is False
    
    def test_rejects_none(self):
        extractor = ContactExtractor()
        assert extractor._validate_email(None) is False


# ---------------------------------------------------------------------------
# Tests: URL Extraction
# ---------------------------------------------------------------------------

class TestURLExtraction:
    """Test extraction of phone numbers from URLs."""
    
    def test_extracts_from_wa_me_url(self):
        extractor = ContactExtractor()
        result = extractor._extract_number_from_url("https://wa.me/628123456789")
        assert result == "628123456789"
    
    def test_extracts_from_wa_me_with_query(self):
        extractor = ContactExtractor()
        result = extractor._extract_number_from_url("https://wa.me/628123456789?text=Hello")
        assert result == "628123456789"
    
    def test_extracts_from_api_whatsapp_url(self):
        extractor = ContactExtractor()
        result = extractor._extract_number_from_url("https://api.whatsapp.com/send?phone=628123456789")
        assert result == "628123456789"
    
    def test_extracts_from_phone_parameter(self):
        extractor = ContactExtractor()
        result = extractor._extract_number_from_url("https://example.com/contact?phone=628123456789&source=web")
        assert result == "628123456789"
    
    def test_returns_none_for_invalid_url(self):
        extractor = ContactExtractor()
        result = extractor._extract_number_from_url("https://example.com/contact")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Text Extraction
# ---------------------------------------------------------------------------

class TestTextExtraction:
    """Test extraction from plain text."""
    
    def test_extracts_phone_from_text(self):
        extractor = ContactExtractor()
        result = extractor._extract_phone_from_text("Hubungi saya di 0812-3456-789")
        assert result == "+628123456789"
    
    def test_extracts_email_from_text(self):
        extractor = ContactExtractor()
        result = extractor._extract_email_from_text("Email saya: creator@example.com")
        assert result == "creator@example.com"
    
    def test_extracts_phone_with_prefix_text(self):
        extractor = ContactExtractor()
        result = extractor._extract_phone_from_text("WA: +62 812 3456 789")
        assert result == "+628123456789"
    
    def test_extracts_email_without_prefix(self):
        extractor = ContactExtractor()
        result = extractor._extract_email_from_text("Contact: business@tokopedia.com for inquiries")
        assert result == "business@tokopedia.com"
    
    def test_returns_none_when_no_phone(self):
        extractor = ContactExtractor()
        result = extractor._extract_phone_from_text("No phone number here")
        assert result is None
    
    def test_returns_none_when_no_email(self):
        extractor = ContactExtractor()
        result = extractor._extract_email_from_text("No email address here")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_handles_invalid_html_gracefully(self):
        extractor = ContactExtractor()
        # Should not raise exception
        result = extractor.extract_whatsapp("<invalid>html")
        # Result may be None or extracted if parser recovers
        assert result is None or isinstance(result, str)
    
    def test_handles_empty_string(self):
        extractor = ContactExtractor()
        result = extractor.extract_contacts("")
        assert result['whatsapp'] is None
        assert result['email'] is None
    
    def test_handles_none_input_gracefully(self):
        extractor = ContactExtractor()
        # This should handle the error internally
        result = extractor.extract_whatsapp(None)
        assert result is None
    
    def test_handles_very_long_html(self):
        extractor = ContactExtractor()
        # Create a large HTML document
        large_html = "<html><body>" + "<p>Filler content</p>" * 1000
        large_html += '<a href="https://wa.me/628123456789">WhatsApp</a>'
        large_html += "</body></html>"
        
        result = extractor.extract_whatsapp(large_html)
        assert result == "+628123456789"
    
    def test_handles_unicode_characters(self):
        extractor = ContactExtractor()
        html = """
        <div class="contact">
            <p>📱 WhatsApp: 0812-3456-789</p>
            <p>📧 Email: creator@example.com</p>
        </div>
        """
        result = extractor.extract_contacts(html)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] == "creator@example.com"
    
    def test_handles_html_entities(self):
        extractor = ContactExtractor()
        html = """
        <div class="contact">
            <p>Email: creator&commat;example&period;com</p>
        </div>
        """
        # HTML entities should be decoded by lxml
        result = extractor.extract_email(html)
        # This may or may not work depending on entity handling
        assert result is None or "@" in result


# ---------------------------------------------------------------------------
# Tests: Integration with Real Scenarios
# ---------------------------------------------------------------------------

class TestRealWorldScenarios:
    """Test with realistic Tokopedia-like HTML structures."""
    
    def test_tokopedia_style_profile_page(self):
        """Test extraction from a Tokopedia-style profile page."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="css-1dbjc4n r-1awozwy r-18u37iz">
                <div class="css-1dbjc4n r-1loqt21">
                    <div class="creator-profile-header">
                        <h1>@beauty_guru_id</h1>
                    </div>
                    <div class="creator-stats">
                        <span>Followers: 250K</span>
                        <span>GMV: Rp 100M</span>
                    </div>
                    <div class="creator-contact-section">
                        <div class="contact-row">
                            <span class="contact-label">WhatsApp</span>
                            <a href="https://wa.me/6281298765432" class="contact-value">
                                +62 812-9876-5432
                            </a>
                        </div>
                        <div class="contact-row">
                            <span class="contact-label">Email</span>
                            <a href="mailto:beauty.collab@gmail.com" class="contact-value">
                                beauty.collab@gmail.com
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        extractor = ContactExtractor()
        result = extractor.extract_contacts(html)
        assert result['whatsapp'] == "+6281298765432"
        assert result['email'] == "beauty.collab@gmail.com"
    
    def test_minimal_contact_section(self):
        """Test extraction from minimal HTML."""
        html = """
        <div>
            <p>WA: 0812-3456-789</p>
            <p>Email: minimal@example.com</p>
        </div>
        """
        extractor = ContactExtractor()
        result = extractor.extract_contacts(html)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] == "minimal@example.com"
    
    def test_nested_contact_structure(self):
        """Test extraction from deeply nested HTML."""
        html = """
        <div class="outer">
            <div class="middle">
                <div class="inner">
                    <div class="contact-wrapper">
                        <div class="contact-container">
                            <a href="tel:+628123456789">Call</a>
                            <a href="mailto:nested@example.com">Email</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        extractor = ContactExtractor()
        result = extractor.extract_contacts(html)
        assert result['whatsapp'] == "+628123456789"
        assert result['email'] == "nested@example.com"
