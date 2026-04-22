"""Test fixtures - helper functions to load fixture files."""

from __future__ import annotations

import json
import os

_FIXTURES_DIR = os.path.dirname(__file__)


def load_fixture(filename: str) -> str:
    """Load a fixture file and return its contents as a string."""
    path = os.path.join(_FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_list_page_html() -> str:
    """Return the sample list page HTML fixture."""
    return load_fixture("list_page.html")


def load_detail_page_html() -> str:
    """Return the sample detail page HTML fixture."""
    return load_fixture("detail_page.html")


def load_config() -> dict:
    """Return the sample config fixture as a dict."""
    return json.loads(load_fixture("config.json"))
