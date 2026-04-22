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
