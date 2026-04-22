"""Performance profiling helpers for parser and serialization paths."""

from __future__ import annotations

import gc
import json
import logging
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.affiliator_extractor import AffiliatorExtractor
from src.core.data_store import DataStore
from src.core.html_parser import HTMLParser
from src.models.models import AffiliatorData


def _sample_html(rows: int = 500) -> str:
    cards = []
    for idx in range(rows):
        cards.append(
            f"""
            <div class="creator-card">
              <a class="creator-card-link" href="https://affiliate-id.tokopedia.com/creator/{idx}"></a>
              <div class="creator-name"><span class="username">creator_{idx}</span></div>
              <span class="creator-category">Fashion</span>
              <span class="follower-count">{idx + 1000}</span>
              <span class="gmv-value">1500000</span>
              <span class="product-sold-count">2900</span>
              <span class="avg-view-count">4800</span>
              <span class="engagement-rate">1.2%</span>
            </div>
            """
        )
    return "<html><body>" + "".join(cards) + "</body></html>"


def _sample_records(count: int = 5000) -> list[AffiliatorData]:
    now = datetime.now()
    return [
        AffiliatorData(
            username=f"user_{i}",
            kategori="Fashion",
            pengikut=1_000 + i,
            gmv=100_000.0 + i,
            produk_terjual=100 + i,
            rata_rata_tayangan=500 + i,
            tingkat_interaksi=2.5,
            nomor_kontak=None,
            nomor_whatsapp=None,
            gmv_per_pembeli=15_000.0,
            gmv_harian=50_000.0,
            gmv_mingguan=350_000.0,
            gmv_bulanan=1_500_000.0,
            detail_url=f"https://affiliate-id.tokopedia.com/creator/{i}",
            scraped_at=now,
        )
        for i in range(count)
    ]


def profile_parser(iterations: int = 20) -> dict:
    parser = HTMLParser()
    extractor = AffiliatorExtractor(parser=parser)
    html = _sample_html()
    start = time.perf_counter()
    total = 0
    for _ in range(iterations):
        doc = parser.parse(html)
        result = extractor.extract_list_page(doc)
        total += len(result.affiliators)
    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "total_records": total,
        "elapsed_seconds": round(elapsed, 4),
        "records_per_second": round(total / elapsed, 2) if elapsed else 0.0,
    }


def profile_datastore(tmp_dir: Path) -> dict:
    records = _sample_records()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    json_path = tmp_dir / "perf_data.json"
    csv_path = tmp_dir / "perf_data.csv"
    xlsx_path = tmp_dir / "perf_data.xlsx"

    metrics = {}
    formats = [
        ("json", json_path),
        ("csv", csv_path),
    ]
    try:
        import pandas  # noqa: F401
        formats.append(("xlsx", xlsx_path))
    except ModuleNotFoundError:
        metrics["xlsx"] = {"skipped": "pandas not installed in current venv"}

    for output_format, path in formats:
        store = DataStore(output_format=output_format, output_path=str(path))
        t0 = time.perf_counter()
        store.save(records)
        save_elapsed = time.perf_counter() - t0

        t1 = time.perf_counter()
        loaded = store.load()
        load_elapsed = time.perf_counter() - t1
        metrics[output_format] = {
            "saved_records": len(records),
            "loaded_records": len(loaded),
            "save_seconds": round(save_elapsed, 4),
            "load_seconds": round(load_elapsed, 4),
        }
    return metrics


def run() -> int:
    logging.getLogger().setLevel(logging.CRITICAL)
    gc.collect()
    tracemalloc.start()

    parser_metrics = profile_parser()
    datastore_metrics = profile_datastore(ROOT_DIR / "output" / "perf")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    report = {
        "parser": parser_metrics,
        "datastore": datastore_metrics,
        "memory": {
            "current_mb": round(current / (1024 * 1024), 2),
            "peak_mb": round(peak / (1024 * 1024), 2),
        },
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

