"""Preflight checks before running the scraper."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.models.config import Configuration


def _load_cookie_entries(cookie_path: Path) -> list[dict]:
    with open(cookie_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("cookies"), list):
        return raw["cookies"]
    raise ValueError("Cookie file must be a list or object with `cookies` list")


def run(config_path: str) -> int:
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"[FAIL] Config not found: {config_file}")
        return 1

    config = Configuration.from_file(str(config_file))
    errors = config.validate()
    if errors:
        print("[FAIL] Config validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"[OK] Config valid: {config_file}")

    if config.require_cookie_file:
        cookie_file = Path(config.cookie_file or "")
        if not cookie_file.exists():
            print(f"[FAIL] Cookie file not found: {cookie_file}")
            return 1

        cookies = _load_cookie_entries(cookie_file)
        if not cookies:
            print("[FAIL] Cookie file exists but has no cookie entries")
            return 1

        invalid = 0
        now_ts = int(time.time())
        expiring_soon = 0
        for idx, cookie in enumerate(cookies):
            if not isinstance(cookie, dict):
                invalid += 1
                print(f"[WARN] Cookie #{idx + 1} is not an object")
                continue
            if not cookie.get("name") or not cookie.get("value"):
                invalid += 1
                print(f"[WARN] Cookie #{idx + 1} missing `name` or `value`")
            # Playwright requires either url or domain/path combo.
            has_url = bool(cookie.get("url"))
            has_domain = bool(cookie.get("domain"))
            has_path = bool(cookie.get("path"))
            if not has_url and not (has_domain and has_path):
                invalid += 1
                print(
                    f"[WARN] Cookie #{idx + 1} should include `url` or `domain` + `path`"
                )
            expires = cookie.get("expires", cookie.get("expirationDate"))
            if isinstance(expires, (int, float)) and expires > 0:
                remaining = int(expires) - now_ts
                if remaining <= 0:
                    invalid += 1
                    print(f"[WARN] Cookie #{idx + 1} is already expired")
                elif remaining <= 60 * 60 * 24:
                    expiring_soon += 1

        if invalid > 0:
            print(f"[FAIL] Found {invalid} cookie issues")
            return 1
        print(f"[OK] Cookie file valid: {cookie_file} ({len(cookies)} cookies)")
        if expiring_soon > 0:
            print(f"[WARN] {expiring_soon} cookies will expire within 24 hours")

    print("[OK] Preflight checks passed")
    return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Scraper preflight checks")
    parser.add_argument(
        "--config",
        default="config/config.safe.json",
        help="Path to config JSON file",
    )
    args = parser.parse_args()
    sys.exit(run(args.config))

