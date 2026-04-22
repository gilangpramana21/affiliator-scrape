"""Property-based tests for DataStore serialization.

**Validates: Requirements 7 and 12**
"""

from __future__ import annotations

import math
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from src.core.data_store import DataStore
from src.models.models import AffiliatorData


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

indonesian_phone = st.one_of(
    st.from_regex(r"08\d{8,12}", fullmatch=True),
    st.from_regex(r"\+62\d{8,13}", fullmatch=True),
)

affiliator_strategy = st.builds(
    AffiliatorData,
    username=st.text(min_size=1, max_size=100),
    kategori=st.text(min_size=1, max_size=100),
    pengikut=st.integers(min_value=0, max_value=10_000_000),
    gmv=st.floats(
        min_value=0,
        max_value=1_000_000_000,
        allow_nan=False,
        allow_infinity=False,
    ),
    produk_terjual=st.integers(min_value=0, max_value=1_000_000),
    rata_rata_tayangan=st.integers(min_value=0, max_value=10_000_000),
    tingkat_interaksi=st.floats(
        min_value=0.0,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    nomor_kontak=st.one_of(st.none(), indonesian_phone),
    detail_url=st.from_regex(
        r"https://affiliate\.tokopedia\.com/creator/[A-Za-z0-9_]+",
        fullmatch=True,
    ),
    scraped_at=st.datetimes(allow_imaginary=False),
)


# ---------------------------------------------------------------------------
# Property 1: JSON round-trip preserves all non-null field values
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 1: JSON Serialization Round-Trip Preserves Data"
)
@settings(max_examples=100)
@given(affiliator=affiliator_strategy)
def test_json_round_trip(affiliator: AffiliatorData):
    """**Validates: Requirements 12.1, 12.3**

    FOR ALL valid AffiliatorData objects, serializing to JSON and then
    deserializing SHALL produce an equivalent object.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "rt.json"
        ds = DataStore("json", str(path))
        ds.save([affiliator])
        restored = ds.load()[0]

    assert restored.username == affiliator.username
    assert restored.kategori == affiliator.kategori
    assert restored.pengikut == affiliator.pengikut
    assert math.isclose(restored.gmv, affiliator.gmv, rel_tol=1e-9)
    assert restored.produk_terjual == affiliator.produk_terjual
    assert restored.rata_rata_tayangan == affiliator.rata_rata_tayangan
    assert math.isclose(
        restored.tingkat_interaksi, affiliator.tingkat_interaksi, rel_tol=1e-9
    )
    assert restored.nomor_kontak == affiliator.nomor_kontak
    assert restored.detail_url == affiliator.detail_url
    assert restored.scraped_at == affiliator.scraped_at


# ---------------------------------------------------------------------------
# Property 2: CSV round-trip preserves all non-null field values
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 2: CSV Serialization Round-Trip Preserves Data"
)
@settings(max_examples=100)
@given(affiliator=affiliator_strategy)
def test_csv_round_trip(affiliator: AffiliatorData):
    """**Validates: Requirements 12.2, 12.3**

    FOR ALL valid AffiliatorData objects, serializing to CSV and then
    parsing SHALL preserve all non-null field values (null → empty string).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "rt.csv"
        ds = DataStore("csv", str(path))
        ds.save([affiliator])
        restored = ds.load()[0]

    assert restored.username == affiliator.username
    assert restored.kategori == affiliator.kategori
    assert restored.pengikut == affiliator.pengikut
    assert math.isclose(restored.gmv, affiliator.gmv, rel_tol=1e-9)
    assert restored.produk_terjual == affiliator.produk_terjual
    assert restored.rata_rata_tayangan == affiliator.rata_rata_tayangan
    assert math.isclose(
        restored.tingkat_interaksi, affiliator.tingkat_interaksi, rel_tol=1e-9
    )
    # null nomor_kontak becomes empty string in CSV, then back to None on load
    if affiliator.nomor_kontak is not None:
        assert restored.nomor_kontak == affiliator.nomor_kontak
    else:
        assert restored.nomor_kontak is None
    assert restored.detail_url == affiliator.detail_url
    assert restored.scraped_at == affiliator.scraped_at


# ---------------------------------------------------------------------------
# Property 3: Special characters are properly escaped in CSV round-trip
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 3: Special Character Escaping in CSV Round-Trip"
)
@settings(max_examples=100)
@given(
    username=st.text(min_size=1, max_size=80),
    kategori=st.text(min_size=1, max_size=80),
)
def test_csv_special_character_escaping(username: str, kategori: str):
    """**Validates: Requirements 7.4, 12.4**

    WHEN special characters (commas, quotes, newlines) exist in string fields,
    the CSV serializer SHALL properly escape and unescape them during round-trip.
    """
    record = AffiliatorData(
        username=username,
        kategori=kategori,
        pengikut=0,
        gmv=0.0,
        produk_terjual=0,
        rata_rata_tayangan=0,
        tingkat_interaksi=0.0,
        nomor_kontak=None,
        detail_url="https://affiliate.tokopedia.com/creator/x",
        scraped_at=datetime(2024, 1, 1),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "special.csv"
        ds = DataStore("csv", str(path))
        ds.save([record])
        restored = ds.load()[0]

    assert restored.username == username
    assert restored.kategori == kategori


# ---------------------------------------------------------------------------
# Property 4: Incremental save preserves all appended records (JSON)
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 4: Incremental Save Preserves All Records"
)
@settings(max_examples=50)
@given(records=st.lists(affiliator_strategy, min_size=1, max_size=20))
def test_incremental_save_preserves_data_json(records: list[AffiliatorData]):
    """**Validates: Requirements 7.5**

    FOR ALL sequences of AffiliatorData objects appended incrementally,
    loading the file SHALL return all records in insertion order.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "incremental.json"
        ds = DataStore("json", str(path))
        for record in records:
            ds.append(record)
        loaded = ds.load()

    assert len(loaded) == len(records)
    for original, restored in zip(records, loaded):
        assert restored.username == original.username
        assert restored.pengikut == original.pengikut


# ---------------------------------------------------------------------------
# Property 4b: Incremental save preserves all appended records (CSV)
# ---------------------------------------------------------------------------

@pytest.mark.property_test
@pytest.mark.tag(
    "Feature: tokopedia-affiliate-scraper, "
    "Property 4b: Incremental CSV Save Preserves All Records"
)
@settings(max_examples=50)
@given(records=st.lists(affiliator_strategy, min_size=1, max_size=20))
def test_incremental_save_preserves_data_csv(records: list[AffiliatorData]):
    """**Validates: Requirements 7.5**

    FOR ALL sequences of AffiliatorData objects appended incrementally to CSV,
    loading the file SHALL return all records in insertion order.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "incremental.csv"
        ds = DataStore("csv", str(path))
        for record in records:
            ds.append(record)
        loaded = ds.load()

    assert len(loaded) == len(records)
    for original, restored in zip(records, loaded):
        assert restored.username == original.username
        assert restored.pengikut == original.pengikut
