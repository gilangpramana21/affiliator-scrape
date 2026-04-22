"""Unit tests for SessionManager."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.core.http_client import Cookie
from src.core.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cookie(name: str, value: str = "v", domain: str = "example.com",
                expires: int | None = None) -> Cookie:
    return Cookie(name=name, value=value, domain=domain, expires=expires)


# ---------------------------------------------------------------------------
# 14.1 / 14.2  Initialization and cookie storage
# ---------------------------------------------------------------------------

class TestCookieStorage:
    def test_initial_cookies_empty(self):
        sm = SessionManager()
        assert sm.get_cookies() == []

    def test_set_and_get_cookies(self):
        sm = SessionManager()
        cookies = [make_cookie("a"), make_cookie("b", "2")]
        sm.set_cookies(cookies)
        result = sm.get_cookies()
        assert len(result) == 2
        names = {c.name for c in result}
        assert names == {"a", "b"}

    def test_set_cookies_replaces_same_name_domain(self):
        sm = SessionManager()
        sm.set_cookies([make_cookie("tok", "old")])
        sm.set_cookies([make_cookie("tok", "new")])
        cookies = sm.get_cookies()
        assert len(cookies) == 1
        assert cookies[0].value == "new"

    def test_set_cookies_keeps_different_domain(self):
        sm = SessionManager()
        sm.set_cookies([Cookie("tok", "v1", domain="a.com")])
        sm.set_cookies([Cookie("tok", "v2", domain="b.com")])
        assert len(sm.get_cookies()) == 2

    def test_get_cookies_returns_copy(self):
        sm = SessionManager()
        sm.set_cookies([make_cookie("x")])
        copy = sm.get_cookies()
        copy.clear()
        assert len(sm.get_cookies()) == 1


# ---------------------------------------------------------------------------
# 14.3  Session save / load
# ---------------------------------------------------------------------------

class TestSessionPersistence:
    def test_save_and_load_round_trip(self):
        sm = SessionManager()
        sm.set_cookies([
            Cookie("session", "abc123", domain="tokopedia.com", path="/",
                   secure=True, http_only=True, expires=9999999999),
        ])
        sm.set_local_storage("key1", "val1")
        sm.set_session_storage("skey", "sval")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        sm.save_session(path)

        sm2 = SessionManager()
        sm2.load_session(path)

        cookies = sm2.get_cookies()
        assert len(cookies) == 1
        c = cookies[0]
        assert c.name == "session"
        assert c.value == "abc123"
        assert c.domain == "tokopedia.com"
        assert c.secure is True
        assert c.http_only is True
        assert c.expires == 9999999999

        assert sm2.get_local_storage("key1") == "val1"
        assert sm2.get_session_storage("skey") == "sval"

    def test_save_creates_valid_json(self):
        sm = SessionManager()
        sm.set_cookies([make_cookie("c", "v")])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        sm.save_session(path)
        with open(path) as fh:
            data = json.load(fh)
        assert "cookies" in data
        assert "local_storage" in data
        assert "session_storage" in data

    def test_load_empty_session_file(self):
        sm = SessionManager()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"cookies": [], "local_storage": {}, "session_storage": {}}, f)
            path = f.name
        sm.load_session(path)
        assert sm.get_cookies() == []


# ---------------------------------------------------------------------------
# 14.4  Session expiration detection
# ---------------------------------------------------------------------------

class TestSessionExpiration:
    def test_not_expired_when_no_cookies(self):
        sm = SessionManager()
        assert sm.is_expired() is False

    def test_not_expired_when_session_cookie_future(self):
        sm = SessionManager()
        future = int(time.time()) + 3600
        sm.set_cookies([make_cookie("session", expires=future)])
        assert sm.is_expired() is False

    def test_expired_when_session_cookie_past(self):
        sm = SessionManager()
        past = int(time.time()) - 1
        sm.set_cookies([make_cookie("session", expires=past)])
        assert sm.is_expired() is True

    def test_expired_when_auth_cookie_past(self):
        sm = SessionManager()
        past = int(time.time()) - 1
        sm.set_cookies([make_cookie("auth", expires=past)])
        assert sm.is_expired() is True

    def test_not_expired_for_unrelated_cookie(self):
        sm = SessionManager()
        past = int(time.time()) - 1
        sm.set_cookies([make_cookie("other", expires=past)])
        assert sm.is_expired() is False

    def test_expired_via_login_redirect(self):
        sm = SessionManager(login_url="/login")
        sm.set_last_response_url("https://example.com/login?next=/home")
        assert sm.is_expired() is True

    def test_not_expired_when_no_login_redirect(self):
        sm = SessionManager(login_url="/login")
        sm.set_last_response_url("https://example.com/home")
        assert sm.is_expired() is False

    def test_no_login_url_configured(self):
        sm = SessionManager()
        sm.set_last_response_url("https://example.com/login")
        assert sm.is_expired() is False


# ---------------------------------------------------------------------------
# 14.5  clear()
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_removes_cookies(self):
        sm = SessionManager()
        sm.set_cookies([make_cookie("x")])
        sm.clear()
        assert sm.get_cookies() == []

    def test_clear_removes_local_storage(self):
        sm = SessionManager()
        sm.set_local_storage("k", "v")
        sm.clear()
        assert sm.get_local_storage_all() == {}

    def test_clear_removes_session_storage(self):
        sm = SessionManager()
        sm.set_session_storage("k", "v")
        sm.clear()
        assert sm.get_session_storage_all() == {}

    def test_clear_resets_last_response_url(self):
        sm = SessionManager(login_url="/login")
        sm.set_last_response_url("https://example.com/login")
        sm.clear()
        assert sm.is_expired() is False


# ---------------------------------------------------------------------------
# 14.6  localStorage / sessionStorage
# ---------------------------------------------------------------------------

class TestBrowserStorage:
    def test_local_storage_set_get(self):
        sm = SessionManager()
        sm.set_local_storage("token", "abc")
        assert sm.get_local_storage("token") == "abc"

    def test_local_storage_missing_key_returns_none(self):
        sm = SessionManager()
        assert sm.get_local_storage("missing") is None

    def test_session_storage_set_get(self):
        sm = SessionManager()
        sm.set_session_storage("page", "1")
        assert sm.get_session_storage("page") == "1"

    def test_session_storage_missing_key_returns_none(self):
        sm = SessionManager()
        assert sm.get_session_storage("missing") is None

    def test_local_storage_overwrite(self):
        sm = SessionManager()
        sm.set_local_storage("k", "old")
        sm.set_local_storage("k", "new")
        assert sm.get_local_storage("k") == "new"

    def test_storage_persisted_in_save_load(self):
        sm = SessionManager()
        sm.set_local_storage("ls_key", "ls_val")
        sm.set_session_storage("ss_key", "ss_val")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        sm.save_session(path)
        sm2 = SessionManager()
        sm2.load_session(path)
        assert sm2.get_local_storage("ls_key") == "ls_val"
        assert sm2.get_session_storage("ss_key") == "ss_val"
