"""Data models for the Tokopedia Affiliate Scraper"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class AffiliatorData:
    """Represents a single affiliator's scraped data"""
    username: str
    kategori: str
    pengikut: int
    gmv: float
    produk_terjual: int
    rata_rata_tayangan: int
    tingkat_interaksi: float  # percentage 0-100
    nomor_kontak: Optional[str] = None
    nomor_whatsapp: Optional[str] = None
    gmv_per_pembeli: float = 0.0
    gmv_harian: float = 0.0
    gmv_mingguan: float = 0.0
    gmv_bulanan: float = 0.0
    detail_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "kategori": self.kategori,
            "pengikut": self.pengikut,
            "gmv": self.gmv,
            "produk_terjual": self.produk_terjual,
            "rata_rata_tayangan": self.rata_rata_tayangan,
            "tingkat_interaksi": self.tingkat_interaksi,
            "nomor_kontak": self.nomor_kontak,
            "nomor_whatsapp": self.nomor_whatsapp,
            "gmv_per_pembeli": self.gmv_per_pembeli,
            "gmv_harian": self.gmv_harian,
            "gmv_mingguan": self.gmv_mingguan,
            "gmv_bulanan": self.gmv_bulanan,
            "detail_url": self.detail_url,
            "scraped_at": self.scraped_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AffiliatorData":
        return cls(
            username=data["username"],
            kategori=data["kategori"],
            pengikut=data["pengikut"],
            gmv=data["gmv"],
            produk_terjual=data["produk_terjual"],
            rata_rata_tayangan=data["rata_rata_tayangan"],
            tingkat_interaksi=data["tingkat_interaksi"],
            nomor_kontak=data.get("nomor_kontak"),
            nomor_whatsapp=data.get("nomor_whatsapp"),
            gmv_per_pembeli=data.get("gmv_per_pembeli", 0.0),
            gmv_harian=data.get("gmv_harian", 0.0),
            gmv_mingguan=data.get("gmv_mingguan", 0.0),
            gmv_bulanan=data.get("gmv_bulanan", 0.0),
            detail_url=data["detail_url"],
            scraped_at=datetime.fromisoformat(data["scraped_at"]),
        )


@dataclass
class BrowserFingerprint:
    """Browser fingerprint configuration for anti-detection"""
    user_agent: str
    platform: str  # Windows, macOS, Linux
    browser: str   # Chrome, Firefox, Safari
    browser_version: str
    screen_resolution: Tuple[int, int]
    viewport_size: Tuple[int, int]
    timezone: str  # Asia/Jakarta, Asia/Makassar, Asia/Jayapura
    timezone_offset: int
    language: str  # id-ID
    languages: List[str]
    color_depth: int  # 24
    pixel_ratio: float
    hardware_concurrency: int
    device_memory: int
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    plugins: List[str]
    webgl_vendor: str
    webgl_renderer: str

    def to_dict(self) -> Dict:
        return {
            "user_agent": self.user_agent,
            "platform": self.platform,
            "browser": self.browser,
            "browser_version": self.browser_version,
            "screen_resolution": list(self.screen_resolution),
            "viewport_size": list(self.viewport_size),
            "timezone": self.timezone,
            "timezone_offset": self.timezone_offset,
            "language": self.language,
            "languages": self.languages,
            "color_depth": self.color_depth,
            "pixel_ratio": self.pixel_ratio,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "sec_ch_ua": self.sec_ch_ua,
            "sec_ch_ua_mobile": self.sec_ch_ua_mobile,
            "sec_ch_ua_platform": self.sec_ch_ua_platform,
            "plugins": self.plugins,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BrowserFingerprint":
        return cls(
            user_agent=data["user_agent"],
            platform=data["platform"],
            browser=data["browser"],
            browser_version=data["browser_version"],
            screen_resolution=tuple(data["screen_resolution"]),
            viewport_size=tuple(data["viewport_size"]),
            timezone=data["timezone"],
            timezone_offset=data["timezone_offset"],
            language=data["language"],
            languages=data["languages"],
            color_depth=data["color_depth"],
            pixel_ratio=data["pixel_ratio"],
            hardware_concurrency=data["hardware_concurrency"],
            device_memory=data["device_memory"],
            sec_ch_ua=data["sec_ch_ua"],
            sec_ch_ua_mobile=data["sec_ch_ua_mobile"],
            sec_ch_ua_platform=data["sec_ch_ua_platform"],
            plugins=data["plugins"],
            webgl_vendor=data["webgl_vendor"],
            webgl_renderer=data["webgl_renderer"],
        )


@dataclass
class Checkpoint:
    """Scraping checkpoint for resume support"""
    last_list_page: int
    last_affiliator_index: int
    scraped_usernames: Set[str]
    timestamp: datetime

    def save(self, filepath: str) -> None:
        """Serialize checkpoint to JSON file"""
        data = {
            "last_list_page": self.last_list_page,
            "last_affiliator_index": self.last_affiliator_index,
            "scraped_usernames": list(self.scraped_usernames),
            "timestamp": self.timestamp.isoformat(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Checkpoint":
        """Deserialize checkpoint from JSON file"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            last_list_page=data["last_list_page"],
            last_affiliator_index=data["last_affiliator_index"],
            scraped_usernames=set(data["scraped_usernames"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def to_dict(self) -> Dict:
        return {
            "last_list_page": self.last_list_page,
            "last_affiliator_index": self.last_affiliator_index,
            "scraped_usernames": list(self.scraped_usernames),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        return cls(
            last_list_page=data["last_list_page"],
            last_affiliator_index=data["last_affiliator_index"],
            scraped_usernames=set(data["scraped_usernames"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ScrapingResult:
    """Summary of a completed scraping run"""
    total_scraped: int
    unique_affiliators: int
    duplicates_found: int
    errors: int
    captchas_encountered: int
    duration: float  # seconds
    start_time: datetime
    end_time: datetime
    checkpoint: Optional[Checkpoint] = None

    def to_dict(self) -> Dict:
        return {
            "total_scraped": self.total_scraped,
            "unique_affiliators": self.unique_affiliators,
            "duplicates_found": self.duplicates_found,
            "errors": self.errors,
            "captchas_encountered": self.captchas_encountered,
            "duration": self.duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ScrapingResult":
        checkpoint = None
        if data.get("checkpoint"):
            checkpoint = Checkpoint.from_dict(data["checkpoint"])
        return cls(
            total_scraped=data["total_scraped"],
            unique_affiliators=data["unique_affiliators"],
            duplicates_found=data["duplicates_found"],
            errors=data["errors"],
            captchas_encountered=data["captchas_encountered"],
            duration=data["duration"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            checkpoint=checkpoint,
        )
