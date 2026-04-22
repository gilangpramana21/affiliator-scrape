"""Unit tests for FingerprintGenerator (Task 8.9)"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.anti_detection.fingerprint_generator import (
    BROWSER_WEIGHTS,
    SCREEN_RESOLUTIONS,
    TIMEZONE_WEIGHTS,
    WEBGL_CONFIGS,
    FingerprintGenerator,
)
from src.models.models import BrowserFingerprint


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def gen(tmp_path):
    """FingerprintGenerator using a temp directory for saves."""
    return FingerprintGenerator(fingerprint_dir=str(tmp_path / "fingerprints"))


@pytest.fixture
def fp(gen):
    """A freshly generated fingerprint."""
    return gen.generate()


# ── 8.1 / 8.2  FingerprintGenerator class + User-Agent generation ─────────────


class TestGenerate:
    def test_returns_browser_fingerprint(self, fp):
        assert isinstance(fp, BrowserFingerprint)

    def test_all_required_fields_present(self, fp):
        required = [
            "user_agent", "platform", "browser", "browser_version",
            "screen_resolution", "viewport_size", "timezone", "timezone_offset",
            "language", "languages", "color_depth", "pixel_ratio",
            "hardware_concurrency", "device_memory",
            "sec_ch_ua", "sec_ch_ua_mobile", "sec_ch_ua_platform",
            "plugins", "webgl_vendor", "webgl_renderer",
        ]
        for field in required:
            assert hasattr(fp, field), f"Missing field: {field}"
            assert getattr(fp, field) is not None, f"Field is None: {field}"

    def test_user_agent_is_non_empty_string(self, fp):
        assert isinstance(fp.user_agent, str)
        assert len(fp.user_agent) > 0

    def test_browser_is_valid(self, fp):
        valid_browsers = {b for b, _ in BROWSER_WEIGHTS}
        assert fp.browser in valid_browsers

    def test_user_agent_contains_browser_hint(self, fp):
        ua = fp.user_agent
        if fp.browser == "Chrome":
            assert "Chrome" in ua
        elif fp.browser == "Firefox":
            assert "Firefox" in ua
        elif fp.browser == "Safari":
            assert "Safari" in ua

    def test_chrome_ua_format(self, gen):
        """Chrome UA must contain AppleWebKit and Chrome/."""
        for _ in range(20):
            f = gen.generate()
            if f.browser == "Chrome":
                assert "AppleWebKit/537.36" in f.user_agent
                assert "Chrome/" in f.user_agent
                return
        pytest.skip("No Chrome fingerprint generated in 20 tries")

    def test_firefox_ua_format(self, gen):
        """Firefox UA must contain Gecko and Firefox/."""
        for _ in range(30):
            f = gen.generate()
            if f.browser == "Firefox":
                assert "Gecko/20100101" in f.user_agent
                assert "Firefox/" in f.user_agent
                return
        pytest.skip("No Firefox fingerprint generated in 30 tries")

    def test_safari_ua_format(self, gen):
        """Safari UA must contain Version/ and Safari/."""
        for _ in range(50):
            f = gen.generate()
            if f.browser == "Safari":
                assert "Version/" in f.user_agent
                assert "Safari/" in f.user_agent
                return
        pytest.skip("No Safari fingerprint generated in 50 tries")


# ── 8.3  Screen resolution randomization ─────────────────────────────────────


class TestScreenResolution:
    def test_screen_resolution_is_tuple_of_two_ints(self, fp):
        assert isinstance(fp.screen_resolution, tuple)
        assert len(fp.screen_resolution) == 2
        assert all(isinstance(v, int) for v in fp.screen_resolution)

    def test_screen_resolution_is_from_known_list(self, fp):
        assert fp.screen_resolution in SCREEN_RESOLUTIONS

    def test_viewport_width_equals_screen_width(self, fp):
        assert fp.viewport_size[0] == fp.screen_resolution[0]

    def test_viewport_height_less_than_screen_height(self, fp):
        assert fp.viewport_size[1] < fp.screen_resolution[1]

    def test_viewport_height_positive(self, fp):
        assert fp.viewport_size[1] > 0

    def test_multiple_resolutions_generated(self, gen):
        """Over many runs, more than one resolution should appear."""
        resolutions = {gen.generate().screen_resolution for _ in range(50)}
        assert len(resolutions) > 1


# ── 8.4  Timezone selection ───────────────────────────────────────────────────


class TestTimezone:
    def test_timezone_is_indonesian(self, fp):
        valid_timezones = {tz for tz, _, _ in TIMEZONE_WEIGHTS}
        assert fp.timezone in valid_timezones

    def test_timezone_offset_matches_timezone(self, fp):
        tz_offset_map = {tz: off for tz, off, _ in TIMEZONE_WEIGHTS}
        assert fp.timezone_offset == tz_offset_map[fp.timezone]

    def test_wib_offset(self, gen):
        for _ in range(30):
            f = gen.generate()
            if f.timezone == "Asia/Jakarta":
                assert f.timezone_offset == -420
                return
        pytest.skip("WIB not generated in 30 tries")

    def test_wita_offset(self, gen):
        for _ in range(50):
            f = gen.generate()
            if f.timezone == "Asia/Makassar":
                assert f.timezone_offset == -480
                return
        pytest.skip("WITA not generated in 50 tries")

    def test_wit_offset(self, gen):
        for _ in range(100):
            f = gen.generate()
            if f.timezone == "Asia/Jayapura":
                assert f.timezone_offset == -540
                return
        pytest.skip("WIT not generated in 100 tries")


# ── 8.5  sec-ch-ua headers ────────────────────────────────────────────────────


class TestSecChUa:
    def test_chrome_has_sec_ch_ua(self, gen):
        for _ in range(20):
            f = gen.generate()
            if f.browser == "Chrome":
                assert f.sec_ch_ua != ""
                assert "Google Chrome" in f.sec_ch_ua
                assert "Chromium" in f.sec_ch_ua
                return
        pytest.skip("No Chrome fingerprint in 20 tries")

    def test_firefox_has_empty_sec_ch_ua(self, gen):
        for _ in range(30):
            f = gen.generate()
            if f.browser == "Firefox":
                assert f.sec_ch_ua == ""
                return
        pytest.skip("No Firefox fingerprint in 30 tries")

    def test_safari_has_empty_sec_ch_ua(self, gen):
        for _ in range(50):
            f = gen.generate()
            if f.browser == "Safari":
                assert f.sec_ch_ua == ""
                return
        pytest.skip("No Safari fingerprint in 50 tries")

    def test_sec_ch_ua_mobile_is_question_zero(self, fp):
        assert fp.sec_ch_ua_mobile == "?0"

    def test_sec_ch_ua_platform_matches_os(self, fp):
        platform_to_sec = {
            "Win32": '"Windows"',
            "MacIntel": '"macOS"',
            "Linux x86_64": '"Linux"',
        }
        expected = platform_to_sec.get(fp.platform)
        assert fp.sec_ch_ua_platform == expected

    def test_chrome_sec_ch_ua_version_matches_browser_version(self, gen):
        for _ in range(20):
            f = gen.generate()
            if f.browser == "Chrome":
                major = f.browser_version.split(".")[0]
                assert f'v="{major}"' in f.sec_ch_ua
                return
        pytest.skip("No Chrome fingerprint in 20 tries")


# ── 8.6  WebGL vendor/renderer ────────────────────────────────────────────────


class TestWebGL:
    def test_webgl_vendor_non_empty(self, fp):
        assert isinstance(fp.webgl_vendor, str)
        assert len(fp.webgl_vendor) > 0

    def test_webgl_renderer_non_empty(self, fp):
        assert isinstance(fp.webgl_renderer, str)
        assert len(fp.webgl_renderer) > 0

    def test_webgl_pair_from_known_list(self, fp):
        assert (fp.webgl_vendor, fp.webgl_renderer) in WEBGL_CONFIGS

    def test_multiple_webgl_configs_generated(self, gen):
        configs = {(gen.generate().webgl_vendor, gen.generate().webgl_renderer) for _ in range(30)}
        assert len(configs) > 1


# ── 8.7  Fingerprint consistency validation ───────────────────────────────────


class TestConsistency:
    def test_generated_fingerprint_is_consistent(self, gen):
        for _ in range(20):
            f = gen.generate()
            assert gen.validate_consistency(f), (
                f"Inconsistent fingerprint: browser={f.browser}, platform={f.platform}, "
                f"tz={f.timezone}, sec_ch_ua={f.sec_ch_ua!r}"
            )

    def test_safari_must_be_macos(self, gen):
        """Safari on non-macOS platform should fail validation."""
        f = gen.generate()
        f = BrowserFingerprint(
            **{**f.to_dict(),
               "browser": "Safari",
               "platform": "Win32",
               "screen_resolution": tuple(f.screen_resolution),
               "viewport_size": tuple(f.viewport_size),
               "languages": f.languages,
               "plugins": f.plugins}
        )
        assert not gen.validate_consistency(f)

    def test_invalid_timezone_fails(self, fp, gen):
        data = fp.to_dict()
        data["timezone"] = "America/New_York"
        data["timezone_offset"] = 300
        bad = BrowserFingerprint.from_dict(data)
        assert not gen.validate_consistency(bad)

    def test_mismatched_timezone_offset_fails(self, fp, gen):
        data = fp.to_dict()
        data["timezone"] = "Asia/Jakarta"
        data["timezone_offset"] = -540  # wrong offset for Jakarta
        bad = BrowserFingerprint.from_dict(data)
        assert not gen.validate_consistency(bad)

    def test_chrome_without_sec_ch_ua_fails(self, gen):
        for _ in range(20):
            f = gen.generate()
            if f.browser == "Chrome":
                data = f.to_dict()
                data["sec_ch_ua"] = ""
                bad = BrowserFingerprint.from_dict(data)
                assert not gen.validate_consistency(bad)
                return
        pytest.skip("No Chrome fingerprint in 20 tries")

    def test_viewport_larger_than_screen_fails(self, fp, gen):
        data = fp.to_dict()
        data["viewport_size"] = list(fp.screen_resolution)  # same as screen → invalid
        bad = BrowserFingerprint.from_dict(data)
        assert not gen.validate_consistency(bad)


# ── 8.8  Save / load fingerprint ─────────────────────────────────────────────


class TestSaveLoad:
    def test_save_returns_string_id(self, gen, fp):
        fid = gen.save(fp)
        assert isinstance(fid, str)
        assert len(fid) > 0

    def test_save_creates_json_file(self, gen, fp, tmp_path):
        fid = gen.save(fp)
        expected = Path(gen._dir) / f"{fid}.json"
        assert expected.exists()

    def test_load_returns_equivalent_fingerprint(self, gen, fp):
        fid = gen.save(fp)
        loaded = gen.load(fid)
        assert loaded.user_agent == fp.user_agent
        assert loaded.browser == fp.browser
        assert loaded.platform == fp.platform
        assert loaded.timezone == fp.timezone
        assert loaded.timezone_offset == fp.timezone_offset
        assert loaded.screen_resolution == fp.screen_resolution
        assert loaded.viewport_size == fp.viewport_size
        assert loaded.sec_ch_ua == fp.sec_ch_ua
        assert loaded.webgl_vendor == fp.webgl_vendor
        assert loaded.webgl_renderer == fp.webgl_renderer

    def test_load_nonexistent_raises_file_not_found(self, gen):
        with pytest.raises(FileNotFoundError):
            gen.load("nonexistent-id-12345")

    def test_save_creates_directory_if_missing(self, tmp_path):
        deep_dir = str(tmp_path / "a" / "b" / "c")
        g = FingerprintGenerator(fingerprint_dir=deep_dir)
        f = g.generate()
        fid = g.save(f)
        assert Path(deep_dir, f"{fid}.json").exists()

    def test_saved_file_is_valid_json(self, gen, fp):
        fid = gen.save(fp)
        path = Path(gen._dir) / f"{fid}.json"
        with open(path) as fh:
            data = json.load(fh)
        assert "user_agent" in data
        assert "browser" in data

    def test_multiple_saves_produce_unique_ids(self, gen, fp):
        ids = {gen.save(fp) for _ in range(5)}
        assert len(ids) == 5


# ── Language / misc fields ────────────────────────────────────────────────────


class TestMiscFields:
    def test_language_is_id_ID(self, fp):
        assert fp.language == "id-ID"

    def test_languages_list(self, fp):
        assert "id-ID" in fp.languages
        assert "id" in fp.languages

    def test_color_depth_is_24(self, fp):
        assert fp.color_depth == 24

    def test_pixel_ratio_valid(self, fp):
        assert fp.pixel_ratio in (1.0, 1.5, 2.0)

    def test_hardware_concurrency_positive(self, fp):
        assert fp.hardware_concurrency > 0

    def test_device_memory_positive(self, fp):
        assert fp.device_memory > 0
