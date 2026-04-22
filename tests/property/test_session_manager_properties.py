"""Property-based tests for SessionManager.

**Validates: Requirements 8 and 23**
"""

from __future__ import annotations

import tempfile

import pytest
from hypothesis import given, settings, strategies as st

from src.core.http_client import Cookie
from src.core.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

cookie_strategy = st.builds(
    Cookie,
    name=st.text(min_size=1, max_size=64, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
    )),
    value=st.text(min_size=0, max_size=256),
    domain=st.text(min_size=1, max_size=64, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=".-"
    )),
    path=st.just("/"),
    secure=st.booleans(),
    http_only=st.booleans(),
    expires=st.one_of(st.none(), st.integers(min_value=0, max_value=9_999_999_999)),
)

cookie_list_strategy = st.lists(cookie_strategy, min_size=0, max_size=30)

storage_dict_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=64),
    values=st.text(min_size=0, max_size=256),
    max_size=20,
)


# ---------------------------------------------------------------------------
# Property 22: cookies set then retrieved are equivalent
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 22: Cookies Set Then Retrieved Are Equivalent"
)
@settings(max_examples=100)
@given(cookies=cookie_list_strategy)
def test_cookies_set_then_retrieved_equivalent(cookies: list[Cookie]):
    """**Validates: Requirements 8.1, 8.2, 23.1**

    FOR ALL lists of Cookie objects, calling set_cookies() followed by
    get_cookies() SHALL return a list containing all the same cookies
    (same name, value, domain, path, secure, http_only, expires).
    """
    sm = SessionManager()
    sm.set_cookies(cookies)
    result = sm.get_cookies()

    # Build a lookup by (name, domain) — duplicates are merged (last wins)
    expected: dict[tuple, Cookie] = {}
    for c in cookies:
        expected[(c.name, c.domain)] = c

    assert len(result) == len(expected)
    for c in result:
        key = (c.name, c.domain)
        assert key in expected
        orig = expected[key]
        assert c.value == orig.value
        assert c.path == orig.path
        assert c.secure == orig.secure
        assert c.http_only == orig.http_only
        assert c.expires == orig.expires


# ---------------------------------------------------------------------------
# Property 23: session save/load round-trip preserves all cookies
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 23: Session Save/Load Round-Trip Preserves All Cookies"
)
@settings(max_examples=100)
@given(
    cookies=cookie_list_strategy,
    local_storage=storage_dict_strategy,
    session_storage=storage_dict_strategy,
)
def test_session_save_load_round_trip(
    cookies: list[Cookie],
    local_storage: dict[str, str],
    session_storage: dict[str, str],
):
    """**Validates: Requirements 8.4, 8.5, 23.3**

    FOR ALL combinations of cookies, localStorage, and sessionStorage,
    saving to a file and loading back SHALL produce an identical session state.
    """
    sm = SessionManager()
    sm.set_cookies(cookies)
    for k, v in local_storage.items():
        sm.set_local_storage(k, v)
    for k, v in session_storage.items():
        sm.set_session_storage(k, v)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    sm.save_session(path)

    sm2 = SessionManager()
    sm2.load_session(path)

    # Verify cookies
    original_cookies = {(c.name, c.domain): c for c in sm.get_cookies()}
    restored_cookies = {(c.name, c.domain): c for c in sm2.get_cookies()}

    assert set(original_cookies.keys()) == set(restored_cookies.keys())
    for key in original_cookies:
        orig = original_cookies[key]
        rest = restored_cookies[key]
        assert rest.value == orig.value
        assert rest.path == orig.path
        assert rest.secure == orig.secure
        assert rest.http_only == orig.http_only
        assert rest.expires == orig.expires

    # Verify storage
    assert sm2.get_local_storage_all() == local_storage
    assert sm2.get_session_storage_all() == session_storage
