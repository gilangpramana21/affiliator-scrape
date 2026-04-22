"""Unit tests for DataStore (JSON and CSV serialization)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from src.core.data_store import DataStore, DataStoreError
from src.models.models import AffiliatorData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(
    username: str = "user1",
    nomor_kontak: str | None = "081234567890",
) -> AffiliatorData:
    return AffiliatorData(
        username=username,
        kategori="Fashion",
        pengikut=1000,
        gmv=500000.0,
        produk_terjual=50,
        rata_rata_tayangan=2000,
        tingkat_interaksi=4.5,
        nomor_kontak=nomor_kontak,
        detail_url="https://affiliate.tokopedia.com/creator/user1",
        scraped_at=datetime(2024, 1, 15, 10, 30, 0),
    )


def make_special_char_record() -> AffiliatorData:
    """Record with commas, quotes, and newlines in string fields."""
    return AffiliatorData(
        username='user,"tricky"',
        kategori='Food & Beverage, "Snacks"\nLine2',
        pengikut=100,
        gmv=1.0,
        produk_terjual=1,
        rata_rata_tayangan=1,
        tingkat_interaksi=1.0,
        nomor_kontak=None,
        detail_url="https://affiliate.tokopedia.com/creator/tricky",
        scraped_at=datetime(2024, 6, 1, 0, 0, 0),
    )


# ---------------------------------------------------------------------------
# DataStore initialisation
# ---------------------------------------------------------------------------

class TestDataStoreInit:
    def test_valid_json_format(self, tmp_path):
        ds = DataStore("json", str(tmp_path / "out.json"))
        assert ds.output_format == "json"

    def test_valid_csv_format(self, tmp_path):
        ds = DataStore("csv", str(tmp_path / "out.csv"))
        assert ds.output_format == "csv"

    def test_invalid_format_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported format"):
            DataStore("xml", str(tmp_path / "out.xml"))


# ---------------------------------------------------------------------------
# JSON save / load
# ---------------------------------------------------------------------------

class TestJSONSerialization:
    def test_save_creates_valid_json_array(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        records = [make_record("a"), make_record("b")]
        ds.save(records)

        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        original = [make_record("alice"), make_record("bob")]
        ds.save(original)
        loaded = ds.load()

        assert len(loaded) == 2
        assert loaded[0].username == "alice"
        assert loaded[1].username == "bob"

    def test_json_preserves_null_nomor_kontak(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        record = make_record(nomor_kontak=None)
        ds.save([record])
        loaded = ds.load()
        assert loaded[0].nomor_kontak is None

    def test_json_pretty_printed(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        ds.save([make_record()])
        content = path.read_text(encoding="utf-8")
        # indent=2 means there should be newlines
        assert "\n" in content

    def test_json_utf8_encoding(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        record = make_record("用户名")
        ds.save([record])
        content = path.read_bytes()
        # ensure_ascii=False means the character is stored as UTF-8, not escaped
        assert "用户名".encode("utf-8") in content

    def test_save_empty_list(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        ds.save([])
        loaded = ds.load()
        assert loaded == []

    def test_load_nonexistent_file_raises(self, tmp_path):
        ds = DataStore("json", str(tmp_path / "missing.json"))
        with pytest.raises(DataStoreError):
            ds.load()


# ---------------------------------------------------------------------------
# CSV save / load
# ---------------------------------------------------------------------------

class TestCSVSerialization:
    def test_save_creates_file_with_header(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        ds.save([make_record()])
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        assert lines[0].startswith('"username"') or "username" in lines[0]

    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        original = [make_record("alice"), make_record("bob")]
        ds.save(original)
        loaded = ds.load()

        assert len(loaded) == 2
        assert loaded[0].username == "alice"
        assert loaded[1].username == "bob"

    def test_csv_null_nomor_kontak_becomes_empty_string_then_none(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        record = make_record(nomor_kontak=None)
        ds.save([record])
        loaded = ds.load()
        # CSV round-trip: null → empty string → None (per requirement 12.2)
        assert loaded[0].nomor_kontak is None

    def test_csv_special_characters_escaped(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        record = make_special_char_record()
        ds.save([record])
        loaded = ds.load()
        assert loaded[0].username == record.username
        assert loaded[0].kategori == record.kategori

    def test_csv_utf8_bom(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        ds.save([make_record()])
        raw = path.read_bytes()
        # UTF-8 BOM is \xef\xbb\xbf
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_save_empty_list(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        ds.save([])
        loaded = ds.load()
        assert loaded == []

    def test_load_nonexistent_file_raises(self, tmp_path):
        ds = DataStore("csv", str(tmp_path / "missing.csv"))
        with pytest.raises(DataStoreError):
            ds.load()


# ---------------------------------------------------------------------------
# Incremental save (append)
# ---------------------------------------------------------------------------

class TestIncrementalSave:
    def test_json_append_builds_list(self, tmp_path):
        path = tmp_path / "out.json"
        ds = DataStore("json", str(path))
        ds.append(make_record("a"))
        ds.append(make_record("b"))
        ds.append(make_record("c"))
        loaded = ds.load()
        assert [r.username for r in loaded] == ["a", "b", "c"]

    def test_csv_append_creates_header_once(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        ds.append(make_record("x"))
        ds.append(make_record("y"))
        content = path.read_text(encoding="utf-8-sig")
        # Header should appear exactly once
        assert content.count("username") == 1

    def test_csv_append_preserves_all_records(self, tmp_path):
        path = tmp_path / "out.csv"
        ds = DataStore("csv", str(path))
        for i in range(5):
            ds.append(make_record(f"user{i}"))
        loaded = ds.load()
        assert len(loaded) == 5
        assert [r.username for r in loaded] == [f"user{i}" for i in range(5)]

    def test_json_append_in_memory_not_lost_on_new_instance(self, tmp_path):
        """Appended data is written to disk immediately."""
        path = tmp_path / "out.json"
        ds1 = DataStore("json", str(path))
        ds1.append(make_record("first"))

        # A second DataStore instance reading the same file should see the record
        ds2 = DataStore("json", str(path))
        loaded = ds2.load()
        assert loaded[0].username == "first"


# ---------------------------------------------------------------------------
# File I/O error handling
# ---------------------------------------------------------------------------

class TestFileIOErrorHandling:
    def test_save_to_unwritable_path_raises_data_store_error(self, tmp_path):
        # Create a directory where the file should be — can't write a file there
        bad_path = tmp_path / "dir_not_file"
        bad_path.mkdir()
        ds = DataStore("json", str(bad_path))
        with pytest.raises(DataStoreError):
            ds.save([make_record()])

    def test_in_memory_data_not_lost_after_failed_save(self, tmp_path):
        """Even if save() raises, the caller's list is unchanged."""
        bad_path = tmp_path / "dir_not_file"
        bad_path.mkdir()
        ds = DataStore("json", str(bad_path))
        records = [make_record("safe")]
        with pytest.raises(DataStoreError):
            ds.save(records)
        # The original list is still intact
        assert records[0].username == "safe"

    def test_parent_directory_created_automatically(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "out.json"
        ds = DataStore("json", str(nested))
        ds.save([make_record()])
        assert nested.exists()
