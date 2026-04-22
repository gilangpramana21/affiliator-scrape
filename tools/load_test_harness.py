"""Long-run harness for stability checks without real scraping traffic."""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.data_store import DataStore
from src.models.models import AffiliatorData


def _record(i: int) -> AffiliatorData:
    return AffiliatorData(
        username=f"load_user_{i}",
        kategori="General",
        pengikut=1000 + i,
        gmv=100000.0 + i,
        produk_terjual=100 + i,
        rata_rata_tayangan=2000 + i,
        tingkat_interaksi=1.5,
        nomor_kontak=None,
        nomor_whatsapp=None,
        gmv_per_pembeli=10000.0,
        gmv_harian=30000.0,
        gmv_mingguan=200000.0,
        gmv_bulanan=900000.0,
        detail_url=f"https://example.com/{i}",
        scraped_at=datetime.now(),
    )


def run(duration_minutes: int, batch_size: int) -> int:
    output = ROOT_DIR / "output" / "load_test.json"
    store = DataStore(output_format="json", output_path=str(output))
    tracemalloc.start()

    started = time.time()
    deadline = started + (duration_minutes * 60)
    all_records: list[AffiliatorData] = []
    i = 0
    batches = 0

    while time.time() < deadline:
        batch = [_record(i + n) for n in range(batch_size)]
        i += batch_size
        all_records.extend(batch)
        store.save(all_records)
        _ = store.load()
        batches += 1

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    report = {
        "duration_minutes": duration_minutes,
        "batches": batches,
        "records_written": len(all_records),
        "memory_current_mb": round(current / (1024 * 1024), 2),
        "memory_peak_mb": round(peak / (1024 * 1024), 2),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test harness")
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    raise SystemExit(run(args.minutes, args.batch_size))

