"""Unit tests for Deduplicator."""

from __future__ import annotations

import logging
from datetime import datetime

import pytest

from src.core.deduplicator import Deduplicator
from src.models.models import AffiliatorData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_affiliator(username: str = "user1") -> AffiliatorData:
    return AffiliatorData(
        username=username,
        kategori="Fashion",
        pengikut=1000,
        gmv=500000.0,
        produk_terjual=50,
        rata_rata_tayangan=2000,
        tingkat_interaksi=4.5,
        nomor_kontak="081234567890",
        detail_url=f"https://affiliate.tokopedia.com/creator/{username}",
        scraped_at=datetime(2024, 1, 15, 10, 30, 0),
    )


# ---------------------------------------------------------------------------
# is_duplicate
# ---------------------------------------------------------------------------

class TestIsDuplicate:
    def test_new_username_is_not_duplicate(self):
        d = Deduplicator()
        assert d.is_duplicate(make_affiliator("alice")) is False

    def test_after_add_same_username_is_duplicate(self):
        d = Deduplicator()
        a = make_affiliator("alice")
        d.add(a)
        assert d.is_duplicate(make_affiliator("alice")) is True

    def test_different_username_is_not_duplicate(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        assert d.is_duplicate(make_affiliator("bob")) is False


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------

class TestAdd:
    def test_add_new_record_returns_true(self):
        d = Deduplicator()
        assert d.add(make_affiliator("alice")) is True

    def test_add_duplicate_returns_false(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        assert d.add(make_affiliator("alice")) is False

    def test_add_unique_records_increases_unique_count(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("bob"))
        assert d.get_unique_count() == 2

    def test_add_duplicate_does_not_increase_unique_count(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        assert d.get_unique_count() == 1

    def test_add_duplicate_increases_duplicate_count(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        assert d.get_duplicate_count() == 1

    def test_add_duplicate_logs_warning(self, caplog):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        with caplog.at_level(logging.WARNING, logger="src.core.deduplicator"):
            d.add(make_affiliator("alice"))
        assert "alice" in caplog.text
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_add_multiple_duplicates_counts_all(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        assert d.get_duplicate_count() == 2
        assert d.get_unique_count() == 1


# ---------------------------------------------------------------------------
# get_all()
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_get_all_returns_unique_records(self):
        d = Deduplicator()
        a = make_affiliator("alice")
        b = make_affiliator("bob")
        d.add(a)
        d.add(b)
        result = d.get_all()
        assert len(result) == 2
        assert result[0].username == "alice"
        assert result[1].username == "bob"

    def test_get_all_returns_copy(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        result = d.get_all()
        result.append(make_affiliator("injected"))
        # Internal list should be unaffected
        assert d.get_unique_count() == 1

    def test_get_all_empty_when_no_records(self):
        d = Deduplicator()
        assert d.get_all() == []

    def test_get_all_excludes_duplicates(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        assert len(d.get_all()) == 1


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_resets_unique_count(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.clear()
        assert d.get_unique_count() == 0

    def test_clear_resets_duplicate_count(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("alice"))
        d.clear()
        assert d.get_duplicate_count() == 0

    def test_clear_allows_re_adding_same_username(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.clear()
        assert d.add(make_affiliator("alice")) is True
        assert d.get_unique_count() == 1

    def test_clear_empties_get_all(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.clear()
        assert d.get_all() == []


# ---------------------------------------------------------------------------
# Counts invariant
# ---------------------------------------------------------------------------

class TestCountInvariant:
    def test_unique_plus_duplicate_equals_total_adds(self):
        d = Deduplicator()
        d.add(make_affiliator("alice"))
        d.add(make_affiliator("bob"))
        d.add(make_affiliator("alice"))  # duplicate
        d.add(make_affiliator("carol"))
        d.add(make_affiliator("bob"))   # duplicate
        assert d.get_unique_count() + d.get_duplicate_count() == 5
