"""Convert exported browser cookies into scraper-compatible JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _normalize_cookie(raw: dict[str, Any]) -> dict[str, Any]:
    name = raw.get("name")
    value = raw.get("value")
    if not name or value is None:
        raise ValueError("Each cookie must include `name` and `value`")

    domain = raw.get("domain")
    path = raw.get("path", "/")
    url = raw.get("url")
    secure = bool(raw.get("secure", False))

    cookie: dict[str, Any] = {
        "name": name,
        "value": value,
        "path": path,
        "httpOnly": bool(raw.get("httpOnly", False)),
        "secure": secure,
    }

    # Prefer explicit url if available; otherwise use domain/path format.
    if url:
        cookie["url"] = url
    elif domain:
        cookie["domain"] = domain
    else:
        raise ValueError(f"Cookie `{name}` must include `url` or `domain`")

    # Playwright uses unix timestamp (seconds) for expires.
    expires = raw.get("expires")
    if isinstance(expires, (int, float)) and expires > 0:
        cookie["expires"] = int(expires)

    return cookie


def convert(input_path: str, output_path: str) -> int:
    in_file = Path(input_path)
    out_file = Path(output_path)

    if not in_file.exists():
        print(f"[FAIL] Input file not found: {in_file}")
        return 1

    with open(in_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    cookies = data.get("cookies", data) if isinstance(data, dict) else data
    if not isinstance(cookies, list):
        print("[FAIL] Input JSON must be a list or an object with `cookies` list")
        return 1

    converted = []
    for item in cookies:
        if not isinstance(item, dict):
            print("[FAIL] Every cookie entry must be a JSON object")
            return 1
        converted.append(_normalize_cookie(item))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump({"cookies": converted}, fh, ensure_ascii=False, indent=2)

    print(f"[OK] Converted {len(converted)} cookies -> {out_file}")
    return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert browser cookie export")
    parser.add_argument("--input", required=True, help="Path to exported cookies JSON")
    parser.add_argument(
        "--output",
        default="config/cookies.json",
        help="Output path for scraper cookies",
    )
    args = parser.parse_args()

    sys.exit(convert(args.input, args.output))

