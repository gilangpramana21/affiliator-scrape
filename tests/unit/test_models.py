"""Unit tests for data models"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.models.models import AffiliatorData, BrowserFingerprint, Checkpoint, ScrapingResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_affiliator():
    return AffiliatorData(
        username="creator123",
        kategori="Fashion",
        pengikut=50000,
        gmv=12500000.0,
        produk_terjual=320,
        rata_rata_tayangan=8000,
        tingkat_interaksi=4.5,
        nomor_kontak="+6281234567890",
        detail_url="https://affiliate-id.tokopedia.com/creator/creator123",
        scraped_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_fingerprint():
    return BrowserFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        platform="Windows",
        browser="Chrome",
        browser_version="120.0.0.0",
        screen_resolution=(1920, 1080),
        viewport_size=(1366, 768),
        timezone="Asia/Jakarta",
        timezone_offset=-420,
        language="id-ID",
        languages=["id-ID", "id", "en-US", "en"],
        color_depth=24,
        pixel_ratio=1.0,
        hardware_concurrency=8,
        device_memory=8,
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        sec_ch_ua_mobile="?0",
        sec_ch_ua_platform='"Windows"',
        plugins=["PDF Viewer", "Chrome PDF Viewer"],
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1060)",
    )


@pytest.fixture
def sample_checkpoint():
    return Checkpoint(
        last_list_page=3,
        last_affiliator_index=12,
        scraped_usernames={"user1", "user2", "user3"},
        timestamp=datetime(2024, 1, 15, 11, 0, 0),
    )


@pytest.fixture
def sample_result(sample_checkpoint):
    return ScrapingResult(
        total_scraped=100,
        unique_affiliators=95,
        duplicates_found=5,
        errors=2,
        captchas_encountered=1,
        duration=3600.0,
        start_time=datetime(2024, 1, 15, 9, 0, 0),
        end_time=datetime(2024, 1, 15, 10, 0, 0),
        checkpoint=sample_checkpoint,
    )


# ---------------------------------------------------------------------------
# AffiliatorData tests
# ---------------------------------------------------------------------------

class TestAffiliatorData:
    def test_creation(self, sample_affiliator):
        assert sample_affiliator.username == "creator123"
        assert sample_affiliator.kategori == "Fashion"
        assert sample_affiliator.pengikut == 50000
        assert sample_affiliator.gmv == 12500000.0
        assert sample_affiliator.tingkat_interaksi == 4.5
        assert sample_affiliator.nomor_kontak == "+6281234567890"

    def test_optional_nomor_kontak_none(self):
        a = AffiliatorData(
            username="x",
            kategori="Tech",
            pengikut=0,
            gmv=0.0,
            produk_terjual=0,
            rata_rata_tayangan=0,
            tingkat_interaksi=0.0,
            nomor_kontak=None,
            detail_url="https://example.com",
            scraped_at=datetime(2024, 1, 1),
        )
        assert a.nomor_kontak is None

    def test_to_dict(self, sample_affiliator):
        d = sample_affiliator.to_dict()
        assert d["username"] == "creator123"
        assert d["kategori"] == "Fashion"
        assert d["pengikut"] == 50000
        assert d["gmv"] == 12500000.0
        assert d["produk_terjual"] == 320
        assert d["rata_rata_tayangan"] == 8000
        assert d["tingkat_interaksi"] == 4.5
        assert d["nomor_kontak"] == "+6281234567890"
        assert d["detail_url"] == "https://affiliate-id.tokopedia.com/creator/creator123"
        assert d["scraped_at"] == "2024-01-15T10:30:00"

    def test_scraped_at_iso_format(self, sample_affiliator):
        d = sample_affiliator.to_dict()
        # Must be parseable as ISO datetime
        parsed = datetime.fromisoformat(d["scraped_at"])
        assert parsed == sample_affiliator.scraped_at

    def test_from_dict_roundtrip(self, sample_affiliator):
        d = sample_affiliator.to_dict()
        restored = AffiliatorData.from_dict(d)
        assert restored.username == sample_affiliator.username
        assert restored.kategori == sample_affiliator.kategori
        assert restored.pengikut == sample_affiliator.pengikut
        assert restored.gmv == sample_affiliator.gmv
        assert restored.produk_terjual == sample_affiliator.produk_terjual
        assert restored.rata_rata_tayangan == sample_affiliator.rata_rata_tayangan
        assert restored.tingkat_interaksi == sample_affiliator.tingkat_interaksi
        assert restored.nomor_kontak == sample_affiliator.nomor_kontak
        assert restored.detail_url == sample_affiliator.detail_url
        assert restored.scraped_at == sample_affiliator.scraped_at

    def test_from_dict_missing_nomor_kontak(self):
        d = {
            "username": "u",
            "kategori": "k",
            "pengikut": 1,
            "gmv": 1.0,
            "produk_terjual": 1,
            "rata_rata_tayangan": 1,
            "tingkat_interaksi": 1.0,
            "detail_url": "https://example.com",
            "scraped_at": "2024-01-01T00:00:00",
        }
        a = AffiliatorData.from_dict(d)
        assert a.nomor_kontak is None


# ---------------------------------------------------------------------------
# BrowserFingerprint tests
# ---------------------------------------------------------------------------

class TestBrowserFingerprint:
    def test_creation(self, sample_fingerprint):
        assert sample_fingerprint.platform == "Windows"
        assert sample_fingerprint.browser == "Chrome"
        assert sample_fingerprint.screen_resolution == (1920, 1080)
        assert sample_fingerprint.viewport_size == (1366, 768)
        assert sample_fingerprint.color_depth == 24
        assert sample_fingerprint.language == "id-ID"

    def test_to_dict(self, sample_fingerprint):
        d = sample_fingerprint.to_dict()
        assert d["platform"] == "Windows"
        assert d["browser"] == "Chrome"
        assert d["screen_resolution"] == [1920, 1080]
        assert d["viewport_size"] == [1366, 768]
        assert d["languages"] == ["id-ID", "id", "en-US", "en"]
        assert d["plugins"] == ["PDF Viewer", "Chrome PDF Viewer"]
        assert d["color_depth"] == 24

    def test_from_dict_roundtrip(self, sample_fingerprint):
        d = sample_fingerprint.to_dict()
        restored = BrowserFingerprint.from_dict(d)
        assert restored.user_agent == sample_fingerprint.user_agent
        assert restored.platform == sample_fingerprint.platform
        assert restored.browser == sample_fingerprint.browser
        assert restored.browser_version == sample_fingerprint.browser_version
        assert restored.screen_resolution == sample_fingerprint.screen_resolution
        assert restored.viewport_size == sample_fingerprint.viewport_size
        assert restored.timezone == sample_fingerprint.timezone
        assert restored.timezone_offset == sample_fingerprint.timezone_offset
        assert restored.language == sample_fingerprint.language
        assert restored.languages == sample_fingerprint.languages
        assert restored.color_depth == sample_fingerprint.color_depth
        assert restored.pixel_ratio == sample_fingerprint.pixel_ratio
        assert restored.hardware_concurrency == sample_fingerprint.hardware_concurrency
        assert restored.device_memory == sample_fingerprint.device_memory
        assert restored.sec_ch_ua == sample_fingerprint.sec_ch_ua
        assert restored.sec_ch_ua_mobile == sample_fingerprint.sec_ch_ua_mobile
        assert restored.sec_ch_ua_platform == sample_fingerprint.sec_ch_ua_platform
        assert restored.plugins == sample_fingerprint.plugins
        assert restored.webgl_vendor == sample_fingerprint.webgl_vendor
        assert restored.webgl_renderer == sample_fingerprint.webgl_renderer

    def test_screen_resolution_is_tuple_after_roundtrip(self, sample_fingerprint):
        d = sample_fingerprint.to_dict()
        restored = BrowserFingerprint.from_dict(d)
        assert isinstance(restored.screen_resolution, tuple)
        assert isinstance(restored.viewport_size, tuple)


# ---------------------------------------------------------------------------
# Checkpoint tests
# ---------------------------------------------------------------------------

class TestCheckpoint:
    def test_creation(self, sample_checkpoint):
        assert sample_checkpoint.last_list_page == 3
        assert sample_checkpoint.last_affiliator_index == 12
        assert sample_checkpoint.scraped_usernames == {"user1", "user2", "user3"}

    def test_to_dict(self, sample_checkpoint):
        d = sample_checkpoint.to_dict()
        assert d["last_list_page"] == 3
        assert d["last_affiliator_index"] == 12
        assert set(d["scraped_usernames"]) == {"user1", "user2", "user3"}
        assert d["timestamp"] == "2024-01-15T11:00:00"

    def test_from_dict_roundtrip(self, sample_checkpoint):
        d = sample_checkpoint.to_dict()
        restored = Checkpoint.from_dict(d)
        assert restored.last_list_page == sample_checkpoint.last_list_page
        assert restored.last_affiliator_index == sample_checkpoint.last_affiliator_index
        assert restored.scraped_usernames == sample_checkpoint.scraped_usernames
        assert restored.timestamp == sample_checkpoint.timestamp

    def test_scraped_usernames_is_set_after_roundtrip(self, sample_checkpoint):
        d = sample_checkpoint.to_dict()
        restored = Checkpoint.from_dict(d)
        assert isinstance(restored.scraped_usernames, set)

    def test_save_and_load(self, sample_checkpoint, tmp_path):
        filepath = str(tmp_path / "checkpoint.json")
        sample_checkpoint.save(filepath)

        # File should exist and be valid JSON
        assert Path(filepath).exists()
        with open(filepath) as f:
            raw = json.load(f)
        assert raw["last_list_page"] == 3

        loaded = Checkpoint.load(filepath)
        assert loaded.last_list_page == sample_checkpoint.last_list_page
        assert loaded.last_affiliator_index == sample_checkpoint.last_affiliator_index
        assert loaded.scraped_usernames == sample_checkpoint.scraped_usernames
        assert loaded.timestamp == sample_checkpoint.timestamp

    def test_save_creates_valid_json(self, sample_checkpoint, tmp_path):
        filepath = str(tmp_path / "cp.json")
        sample_checkpoint.save(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert isinstance(data["scraped_usernames"], list)

    def test_empty_scraped_usernames(self, tmp_path):
        cp = Checkpoint(
            last_list_page=0,
            last_affiliator_index=0,
            scraped_usernames=set(),
            timestamp=datetime(2024, 1, 1),
        )
        filepath = str(tmp_path / "empty_cp.json")
        cp.save(filepath)
        loaded = Checkpoint.load(filepath)
        assert loaded.scraped_usernames == set()


# ---------------------------------------------------------------------------
# ScrapingResult tests
# ---------------------------------------------------------------------------

class TestScrapingResult:
    def test_creation(self, sample_result):
        assert sample_result.total_scraped == 100
        assert sample_result.unique_affiliators == 95
        assert sample_result.duplicates_found == 5
        assert sample_result.errors == 2
        assert sample_result.captchas_encountered == 1
        assert sample_result.duration == 3600.0

    def test_optional_checkpoint_none(self):
        r = ScrapingResult(
            total_scraped=0,
            unique_affiliators=0,
            duplicates_found=0,
            errors=0,
            captchas_encountered=0,
            duration=0.0,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1),
        )
        assert r.checkpoint is None

    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["total_scraped"] == 100
        assert d["unique_affiliators"] == 95
        assert d["duplicates_found"] == 5
        assert d["errors"] == 2
        assert d["captchas_encountered"] == 1
        assert d["duration"] == 3600.0
        assert d["start_time"] == "2024-01-15T09:00:00"
        assert d["end_time"] == "2024-01-15T10:00:00"
        assert d["checkpoint"] is not None
        assert d["checkpoint"]["last_list_page"] == 3

    def test_to_dict_no_checkpoint(self):
        r = ScrapingResult(
            total_scraped=10,
            unique_affiliators=10,
            duplicates_found=0,
            errors=0,
            captchas_encountered=0,
            duration=60.0,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1),
            checkpoint=None,
        )
        d = r.to_dict()
        assert d["checkpoint"] is None

    def test_from_dict_roundtrip(self, sample_result):
        d = sample_result.to_dict()
        restored = ScrapingResult.from_dict(d)
        assert restored.total_scraped == sample_result.total_scraped
        assert restored.unique_affiliators == sample_result.unique_affiliators
        assert restored.duplicates_found == sample_result.duplicates_found
        assert restored.errors == sample_result.errors
        assert restored.captchas_encountered == sample_result.captchas_encountered
        assert restored.duration == sample_result.duration
        assert restored.start_time == sample_result.start_time
        assert restored.end_time == sample_result.end_time
        assert restored.checkpoint is not None
        assert restored.checkpoint.last_list_page == sample_result.checkpoint.last_list_page

    def test_from_dict_no_checkpoint(self):
        d = {
            "total_scraped": 5,
            "unique_affiliators": 5,
            "duplicates_found": 0,
            "errors": 0,
            "captchas_encountered": 0,
            "duration": 10.0,
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T00:00:10",
            "checkpoint": None,
        }
        r = ScrapingResult.from_dict(d)
        assert r.checkpoint is None
