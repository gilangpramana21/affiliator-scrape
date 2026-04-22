"""Data models for the scraper"""

from src.models.config import ProxyConfig, Configuration
from src.models.models import (
    AffiliatorData,
    BrowserFingerprint,
    Checkpoint,
    ScrapingResult,
)

__all__ = [
    "ProxyConfig",
    "Configuration",
    "AffiliatorData",
    "BrowserFingerprint",
    "Checkpoint",
    "ScrapingResult",
]
