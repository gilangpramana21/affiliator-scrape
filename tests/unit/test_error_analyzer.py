"""Unit tests for ErrorAnalyzer (Task 16)."""

from __future__ import annotations

import pytest

from src.core.error_analyzer import Action, ErrorAnalysis, ErrorAnalyzer
from src.core.http_client import Response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_url_counter = 0


def make_response(
    status: int = 200,
    url: str | None = None,
    text: str = "<html><body>" + "Hello world, this is a normal page with enough content. " * 3 + "</body></html>",
    headers: dict | None = None,
) -> Response:
    global _url_counter
    if url is None:
        _url_counter += 1
        url = f"https://example.com/page{_url_counter}"
    return Response(
        status=status,
        url=url,
        headers=headers or {},
        body=text.encode(),
        text=text,
    )


# ---------------------------------------------------------------------------
# 16.1 / 16.2  ErrorAnalyzer class and analyze() method
# ---------------------------------------------------------------------------

class TestErrorAnalyzerBasic:
    def test_analyze_returns_error_analysis(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(200))
        assert isinstance(result, ErrorAnalysis)

    def test_analyze_200_ok_returns_continue(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(200))
        assert result.recommended_action == Action.CONTINUE
        assert result.is_bot_detection is False
        assert result.is_rate_limit is False
        assert result.is_redirect_loop is False

    def test_analyze_records_response_time(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(200), response_time=1.5)
        assert 1.5 in analyzer.response_times

    def test_analyze_status_code_stored(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(404))
        assert result.status_code == 404


# ---------------------------------------------------------------------------
# 16.3  403 Forbidden detection
# ---------------------------------------------------------------------------

class TestForbiddenDetection:
    def test_403_is_bot_detection(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(403))
        assert result.is_bot_detection is True

    def test_403_recommends_slow_down(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(403))
        assert result.recommended_action == Action.SLOW_DOWN

    def test_403_logged_as_bot_detection(self, caplog):
        import logging
        analyzer = ErrorAnalyzer()
        with caplog.at_level(logging.WARNING, logger="src.core.error_analyzer"):
            analyzer.analyze(make_response(403))
        assert any("bot detection" in r.message.lower() for r in caplog.records)

    def test_three_consecutive_403_triggers_pause(self):
        analyzer = ErrorAnalyzer()
        for _ in range(3):
            analyzer.analyze(make_response(403))
        assert analyzer.should_pause() is True

    def test_three_consecutive_403_recommends_pause(self):
        analyzer = ErrorAnalyzer()
        result = None
        for _ in range(3):
            result = analyzer.analyze(make_response(403))
        assert result.recommended_action == Action.PAUSE


# ---------------------------------------------------------------------------
# 16.4  429 Too Many Requests detection
# ---------------------------------------------------------------------------

class TestRateLimitDetection:
    def test_429_is_rate_limit(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(429))
        assert result.is_rate_limit is True

    def test_429_recommends_slow_down(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(429))
        assert result.recommended_action == Action.SLOW_DOWN

    def test_three_consecutive_429_triggers_pause(self):
        analyzer = ErrorAnalyzer()
        for _ in range(3):
            analyzer.analyze(make_response(429))
        assert analyzer.should_pause() is True

    def test_mixed_403_429_triggers_pause(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(403))
        analyzer.analyze(make_response(429))
        analyzer.analyze(make_response(403))
        assert analyzer.should_pause() is True

    def test_200_resets_consecutive_errors(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(403))
        analyzer.analyze(make_response(403))
        analyzer.analyze(make_response(200))
        assert analyzer.should_pause() is False


# ---------------------------------------------------------------------------
# 16.5  Redirect loop detection
# ---------------------------------------------------------------------------

class TestRedirectLoopDetection:
    def test_same_url_three_times_is_redirect_loop(self):
        analyzer = ErrorAnalyzer()
        url = "https://example.com/redirect"
        for _ in range(3):
            result = analyzer.analyze(make_response(200, url=url))
        assert result.is_redirect_loop is True

    def test_redirect_loop_recommends_abort(self):
        analyzer = ErrorAnalyzer()
        url = "https://example.com/loop"
        result = None
        for _ in range(3):
            result = analyzer.analyze(make_response(200, url=url))
        assert result.recommended_action == Action.ABORT

    def test_different_urls_no_redirect_loop(self):
        analyzer = ErrorAnalyzer()
        for i in range(5):
            result = analyzer.analyze(make_response(200, url=f"https://example.com/page{i}"))
        assert result.is_redirect_loop is False

    def test_two_visits_not_yet_redirect_loop(self):
        analyzer = ErrorAnalyzer()
        url = "https://example.com/page"
        for _ in range(2):
            result = analyzer.analyze(make_response(200, url=url))
        assert result.is_redirect_loop is False


# ---------------------------------------------------------------------------
# 16.6  Honeypot link detection
# ---------------------------------------------------------------------------

class TestHoneypotDetection:
    def test_display_none_link_is_honeypot(self):
        html = '<a href="/trap" style="display:none">click</a>'
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/trap" in result

    def test_visibility_hidden_link_is_honeypot(self):
        html = '<a href="/hidden" style="visibility:hidden">link</a>'
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/hidden" in result

    def test_opacity_zero_link_is_honeypot(self):
        html = '<a href="/invisible" style="opacity:0">link</a>'
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/invisible" in result

    def test_visible_link_not_honeypot(self):
        html = '<a href="/normal" style="color:red">Normal link</a>'
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/normal" not in result

    def test_no_links_returns_empty(self):
        html = "<p>No links here</p>"
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert result == []

    def test_multiple_honeypots_detected(self):
        html = (
            '<a href="/trap1" style="display:none">t1</a>'
            '<a href="/trap2" style="visibility:hidden">t2</a>'
            '<a href="/ok" style="color:blue">ok</a>'
        )
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/trap1" in result
        assert "/trap2" in result
        assert "/ok" not in result

    def test_width_zero_link_is_honeypot(self):
        html = '<a href="/tiny" style="width:0px;">link</a>'
        result = ErrorAnalyzer.detect_honeypot_links(html)
        assert "/tiny" in result


# ---------------------------------------------------------------------------
# 16.7  Response time analysis
# ---------------------------------------------------------------------------

class TestResponseTimeAnalysis:
    def test_slow_response_flagged(self):
        analyzer = ErrorAnalyzer()
        # Establish baseline
        for _ in range(5):
            analyzer.analyze(make_response(200), response_time=1.0)
        # Now a very slow response
        result = analyzer.analyze(make_response(200), response_time=5.0)
        assert result.recommended_action == Action.SLOW_DOWN

    def test_normal_response_time_not_flagged(self):
        analyzer = ErrorAnalyzer()
        for _ in range(5):
            analyzer.analyze(make_response(200), response_time=1.0)
        result = analyzer.analyze(make_response(200), response_time=1.2)
        assert result.recommended_action == Action.CONTINUE

    def test_response_time_stored(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(200), response_time=2.5)
        assert 2.5 in analyzer.response_times

    def test_rolling_window_capped(self):
        analyzer = ErrorAnalyzer()
        for i in range(15):
            analyzer.analyze(make_response(200), response_time=float(i + 1))
        assert len(analyzer.response_times) <= ErrorAnalyzer.ROLLING_WINDOW


# ---------------------------------------------------------------------------
# 16.8  should_slow_down() and should_pause()
# ---------------------------------------------------------------------------

class TestShouldSlowDownAndPause:
    def test_should_slow_down_false_initially(self):
        analyzer = ErrorAnalyzer()
        assert analyzer.should_slow_down() is False

    def test_should_pause_false_initially(self):
        analyzer = ErrorAnalyzer()
        assert analyzer.should_pause() is False

    def test_should_slow_down_after_429(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(429))
        assert analyzer.should_slow_down() is True

    def test_should_pause_after_three_errors(self):
        analyzer = ErrorAnalyzer()
        for _ in range(3):
            analyzer.analyze(make_response(403))
        assert analyzer.should_pause() is True

    def test_should_pause_false_after_two_errors(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(403))
        analyzer.analyze(make_response(403))
        assert analyzer.should_pause() is False

    def test_should_slow_down_elevated_response_times(self):
        analyzer = ErrorAnalyzer()
        # Establish baseline of 1s
        for _ in range(5):
            analyzer.analyze(make_response(200), response_time=1.0)
        # Three consecutive slow responses
        for _ in range(3):
            analyzer.analyze(make_response(200), response_time=5.0)
        assert analyzer.should_slow_down() is True


# ---------------------------------------------------------------------------
# 16.9  get_recommended_action()
# ---------------------------------------------------------------------------

class TestGetRecommendedAction:
    def test_initial_state_returns_continue(self):
        analyzer = ErrorAnalyzer()
        assert analyzer.get_recommended_action() == Action.CONTINUE

    def test_after_429_returns_slow_down(self):
        analyzer = ErrorAnalyzer()
        analyzer.analyze(make_response(429))
        assert analyzer.get_recommended_action() == Action.SLOW_DOWN

    def test_after_three_errors_returns_pause(self):
        analyzer = ErrorAnalyzer()
        for _ in range(3):
            analyzer.analyze(make_response(403))
        assert analyzer.get_recommended_action() == Action.PAUSE

    def test_pause_takes_priority_over_slow_down(self):
        analyzer = ErrorAnalyzer()
        # 3 consecutive 429s → should_pause AND should_slow_down both true
        for _ in range(3):
            analyzer.analyze(make_response(429))
        assert analyzer.get_recommended_action() == Action.PAUSE

    def test_captcha_page_returns_use_browser(self):
        analyzer = ErrorAnalyzer()
        html = "<html><body>Please solve the reCAPTCHA to continue.</body></html>"
        result = analyzer.analyze(make_response(200, text=html))
        assert result.recommended_action == Action.USE_BROWSER

    def test_js_challenge_returns_use_browser(self):
        analyzer = ErrorAnalyzer()
        html = "<html><body>Checking your browser before accessing the site.</body></html>"
        result = analyzer.analyze(make_response(200, text=html))
        assert result.recommended_action == Action.USE_BROWSER

    def test_empty_content_200_returns_use_browser(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(200, text="<html></html>"))
        assert result.recommended_action == Action.USE_BROWSER

    def test_404_returns_retry(self):
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze(make_response(404))
        assert result.recommended_action == Action.RETRY


# ---------------------------------------------------------------------------
# 15.8  "Coba lagi" blocking page detection
# ---------------------------------------------------------------------------

class TestCobaLagiDetection:
    """Tests for detect_coba_lagi() method (Task 15.8)."""

    def test_detect_coba_lagi_indonesian(self):
        """Test detection of Indonesian 'coba lagi' text."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Coba lagi</h1><p>Silakan coba lagi nanti.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_detect_coba_lagi_english(self):
        """Test detection of English 'try again' text."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Try Again</h1><p>Please try again later.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_detect_silakan_coba_lagi(self):
        """Test detection of 'silakan coba lagi' phrase."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><p>Silakan coba lagi dalam beberapa menit.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_detect_please_try_again(self):
        """Test detection of 'please try again' phrase."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><p>Please try again in a few minutes.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_detect_terjadi_kesalahan(self):
        """Test detection of 'terjadi kesalahan' (error occurred) text."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h2>Terjadi kesalahan</h2><p>Mohon coba lagi.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_detect_something_went_wrong(self):
        """Test detection of 'something went wrong' text."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h2>Something went wrong</h2><p>Please try again.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is True

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        analyzer = ErrorAnalyzer()
        html_upper = "<html><body><h1>COBA LAGI</h1></body></html>"
        html_mixed = "<html><body><h1>CoBa LaGi</h1></body></html>"
        assert analyzer.detect_coba_lagi(html_upper) is True
        assert analyzer.detect_coba_lagi(html_mixed) is True

    def test_normal_page_not_detected(self):
        """Test that normal pages are not detected as 'coba lagi'."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Welcome</h1><p>This is a normal page with content.</p></body></html>"
        assert analyzer.detect_coba_lagi(html) is False

    def test_empty_html_not_detected(self):
        """Test that empty HTML is not detected as 'coba lagi'."""
        analyzer = ErrorAnalyzer()
        assert analyzer.detect_coba_lagi("") is False
        assert analyzer.detect_coba_lagi(None) is False

    def test_affiliate_page_not_detected(self):
        """Test that normal affiliate pages are not detected as 'coba lagi'."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Affiliate Center</h1><div class='creator-list'>Content here</div></body></html>"
        assert analyzer.detect_coba_lagi(html) is False

    def test_coba_lagi_in_middle_of_page(self):
        """Test detection when 'coba lagi' appears in the middle of content."""
        analyzer = ErrorAnalyzer()
        html = """
        <html>
        <body>
            <div class="header">Header content</div>
            <div class="main">
                <p>Some content before</p>
                <div class="error-message">Coba lagi nanti</div>
                <p>Some content after</p>
            </div>
        </body>
        </html>
        """
        assert analyzer.detect_coba_lagi(html) is True

    def test_multiple_patterns_detected(self):
        """Test that any of the patterns triggers detection."""
        analyzer = ErrorAnalyzer()
        
        # Test each pattern individually
        patterns = [
            "coba lagi",
            "try again",
            "silakan coba lagi",
            "please try again",
            "terjadi kesalahan",
            "something went wrong"
        ]
        
        for pattern in patterns:
            html = f"<html><body><p>{pattern}</p></body></html>"
            assert analyzer.detect_coba_lagi(html) is True, f"Pattern '{pattern}' should be detected"

    def test_logged_when_detected(self, caplog):
        """Test that detection is logged."""
        import logging
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Coba lagi</h1></body></html>"
        
        with caplog.at_level(logging.WARNING, logger="src.core.error_analyzer"):
            analyzer.detect_coba_lagi(html)
        
        assert any("coba lagi" in r.message.lower() for r in caplog.records)
        assert any("blocking page detected" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# 15.9  Cookie expiration detection
# ---------------------------------------------------------------------------

class TestCookieExpirationDetection:
    """Tests for detect_cookie_expiration() method (Task 15.9)."""

    def test_detect_redirect_to_login(self):
        """Test detection of redirect to /login page."""
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/login")
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_redirect_to_signin(self):
        """Test detection of redirect to /signin page."""
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/signin")
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_redirect_to_auth(self):
        """Test detection of redirect to /auth page."""
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/auth")
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_redirect_to_masuk(self):
        """Test detection of redirect to /masuk (Indonesian login) page."""
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/masuk")
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_session_expired_message(self):
        """Test detection of 'session expired' message in content."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Session Expired</h1><p>Your session has expired. Please login again.</p></body></html>"
        response = make_response(200, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_sesi_berakhir_message(self):
        """Test detection of Indonesian 'sesi berakhir' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Sesi Berakhir</h1><p>Sesi telah berakhir. Silakan login kembali.</p></body></html>"
        response = make_response(200, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_login_required_message(self):
        """Test detection of 'login required' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><div class='error'>Login required to access this page.</div></body></html>"
        response = make_response(200, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_please_login_message(self):
        """Test detection of 'please login' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><p>Please login to continue.</p></body></html>"
        response = make_response(200, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_silakan_login_message(self):
        """Test detection of Indonesian 'silakan login' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><p>Silakan login untuk melanjutkan.</p></body></html>"
        response = make_response(200, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_authentication_required(self):
        """Test detection of 'authentication required' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h2>Authentication Required</h2></body></html>"
        response = make_response(401, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_unauthorized_message(self):
        """Test detection of 'unauthorized' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>401 Unauthorized</h1><p>You are not authorized to access this resource.</p></body></html>"
        response = make_response(401, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_detect_access_denied_message(self):
        """Test detection of 'access denied' message."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Access Denied</h1></body></html>"
        response = make_response(403, text=html)
        assert analyzer.detect_cookie_expiration(response) is True

    def test_case_insensitive_url_detection(self):
        """Test that URL detection is case-insensitive."""
        analyzer = ErrorAnalyzer()
        response_upper = make_response(302, url="https://affiliate-id.tokopedia.com/LOGIN")
        response_mixed = make_response(302, url="https://affiliate-id.tokopedia.com/SignIn")
        assert analyzer.detect_cookie_expiration(response_upper) is True
        assert analyzer.detect_cookie_expiration(response_mixed) is True

    def test_case_insensitive_message_detection(self):
        """Test that message detection is case-insensitive."""
        analyzer = ErrorAnalyzer()
        html_upper = "<html><body><h1>SESSION EXPIRED</h1></body></html>"
        html_mixed = "<html><body><h1>Session Has Expired</h1></body></html>"
        response_upper = make_response(200, text=html_upper)
        response_mixed = make_response(200, text=html_mixed)
        assert analyzer.detect_cookie_expiration(response_upper) is True
        assert analyzer.detect_cookie_expiration(response_mixed) is True

    def test_normal_page_not_detected(self):
        """Test that normal pages are not detected as cookie expiration."""
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Affiliate Center</h1><div class='creator-list'>Content here</div></body></html>"
        response = make_response(200, url="https://affiliate-id.tokopedia.com/connection/creator", text=html)
        assert analyzer.detect_cookie_expiration(response) is False

    def test_none_response_not_detected(self):
        """Test that None response is handled gracefully."""
        analyzer = ErrorAnalyzer()
        assert analyzer.detect_cookie_expiration(None) is False

    def test_empty_content_not_detected(self):
        """Test that empty content without login indicators is not detected."""
        analyzer = ErrorAnalyzer()
        response = make_response(200, url="https://affiliate-id.tokopedia.com/connection/creator", text="")
        assert analyzer.detect_cookie_expiration(response) is False

    def test_login_url_in_middle_of_path(self):
        """Test detection when login appears in the middle of URL path."""
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/redirect/login/callback")
        assert analyzer.detect_cookie_expiration(response) is True

    def test_multiple_patterns_detected(self):
        """Test that any of the patterns triggers detection."""
        analyzer = ErrorAnalyzer()
        
        # Test URL patterns
        url_patterns = ["/login", "/signin", "/sign-in", "/auth", "/authenticate", "/masuk"]
        for pattern in url_patterns:
            response = make_response(302, url=f"https://example.com{pattern}")
            assert analyzer.detect_cookie_expiration(response) is True, f"URL pattern '{pattern}' should be detected"
        
        # Test message patterns
        message_patterns = [
            "session expired",
            "session has expired",
            "sesi berakhir",
            "sesi telah berakhir",
            "login required",
            "please login",
            "silakan login",
            "authentication required",
            "autentikasi diperlukan",
            "unauthorized",
            "tidak terotorisasi",
            "access denied",
            "akses ditolak",
        ]
        
        for pattern in message_patterns:
            html = f"<html><body><p>{pattern}</p></body></html>"
            response = make_response(200, text=html)
            assert analyzer.detect_cookie_expiration(response) is True, f"Message pattern '{pattern}' should be detected"

    def test_logged_when_detected_url(self, caplog):
        """Test that URL-based detection is logged."""
        import logging
        analyzer = ErrorAnalyzer()
        response = make_response(302, url="https://affiliate-id.tokopedia.com/login")
        
        with caplog.at_level(logging.WARNING, logger="src.core.error_analyzer"):
            analyzer.detect_cookie_expiration(response)
        
        assert any("cookie expiration" in r.message.lower() for r in caplog.records)
        assert any("redirect to login" in r.message.lower() for r in caplog.records)

    def test_logged_when_detected_message(self, caplog):
        """Test that message-based detection is logged."""
        import logging
        analyzer = ErrorAnalyzer()
        html = "<html><body><h1>Session Expired</h1></body></html>"
        response = make_response(200, text=html)
        
        with caplog.at_level(logging.WARNING, logger="src.core.error_analyzer"):
            analyzer.detect_cookie_expiration(response)
        
        assert any("cookie expiration" in r.message.lower() for r in caplog.records)
        assert any("session expired message" in r.message.lower() for r in caplog.records)

