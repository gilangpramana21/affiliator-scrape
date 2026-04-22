"""Data Store for persisting scraped affiliator data to JSON/CSV/XLSX files."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import List

from src.models.models import AffiliatorData

logger = logging.getLogger(__name__)


class DataStoreError(Exception):
    """Raised when a file I/O operation in DataStore fails."""


class DataStore:
    """Persists AffiliatorData to JSON or CSV files.

    Supports full save, incremental append, and load operations.
    In-memory data is never lost when a file write fails.
    """

    SUPPORTED_FORMATS = ("json", "csv", "xlsx")

    def __init__(self, output_format: str, output_path: str) -> None:
        """Initialize data store.

        Args:
            output_format: "json", "csv", or "xlsx"
            output_path: Path to the output file.

        Raises:
            ValueError: If output_format is not supported.
        """
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{output_format}'. "
                f"Choose from: {self.SUPPORTED_FORMATS}"
            )
        self.output_format = output_format
        self.output_path = Path(output_path)
        # In-memory buffer used by append() for JSON incremental saves
        self._buffer: List[AffiliatorData] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, data: List[AffiliatorData]) -> None:
        """Save (overwrite) all records to the output file.

        Args:
            data: List of AffiliatorData objects to persist.

        Raises:
            DataStoreError: If the file cannot be written.
        """
        self._ensure_parent_dir()
        try:
            if self.output_format == "json":
                self._save_json(data)
            elif self.output_format == "csv":
                self._save_csv(data)
            else:
                self._save_xlsx(data)
        except OSError as exc:
            logger.error("Failed to save data to %s: %s", self.output_path, exc)
            raise DataStoreError(
                f"Failed to save data to {self.output_path}: {exc}"
            ) from exc

    def append(self, record: AffiliatorData) -> None:
        """Append a single record (incremental save).

        For JSON: maintains an in-memory list and rewrites the whole file.
        For CSV: appends a single row to the file (creates with header if new).

        Args:
            record: AffiliatorData object to append.

        Raises:
            DataStoreError: If the file cannot be written.
        """
        self._ensure_parent_dir()
        try:
            if self.output_format == "json":
                self._append_json(record)
            elif self.output_format == "csv":
                self._append_csv(record)
            else:
                self._append_xlsx(record)
        except OSError as exc:
            logger.error(
                "Failed to append record to %s: %s", self.output_path, exc
            )
            raise DataStoreError(
                f"Failed to append record to {self.output_path}: {exc}"
            ) from exc

    def load(self) -> List[AffiliatorData]:
        """Load all records from the output file.

        Returns:
            List of AffiliatorData objects.

        Raises:
            DataStoreError: If the file cannot be read or parsed.
        """
        try:
            if self.output_format == "json":
                return self._load_json()
            elif self.output_format == "csv":
                return self._load_csv()
            else:
                return self._load_xlsx()
        except OSError as exc:
            logger.error("Failed to load data from %s: %s", self.output_path, exc)
            raise DataStoreError(
                f"Failed to load data from {self.output_path}: {exc}"
            ) from exc
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error(
                "Failed to parse data from %s: %s", self.output_path, exc
            )
            raise DataStoreError(
                f"Failed to parse data from {self.output_path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    def _save_json(self, data: List[AffiliatorData]) -> None:
        records = [item.to_dict() for item in data]
        with open(self.output_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)

    def _append_json(self, record: AffiliatorData) -> None:
        """Add record to in-memory buffer and rewrite the JSON file."""
        self._buffer.append(record)
        self._save_json(self._buffer)

    def _load_json(self) -> List[AffiliatorData]:
        with open(self.output_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return [AffiliatorData.from_dict(item) for item in raw]

    # ------------------------------------------------------------------
    # CSV helpers
    # ------------------------------------------------------------------

    _CSV_FIELDS = [
        "username",
        "kategori",
        "pengikut",
        "gmv",
        "produk_terjual",
        "rata_rata_tayangan",
        "tingkat_interaksi",
        "nomor_kontak",
        "nomor_whatsapp",
        "gmv_per_pembeli",
        "gmv_harian",
        "gmv_mingguan",
        "gmv_bulanan",
        "detail_url",
        "scraped_at",
    ]

    def _save_csv(self, data: List[AffiliatorData]) -> None:
        # UTF-8 with BOM so Excel opens it correctly
        with open(self.output_path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=self._CSV_FIELDS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            for item in data:
                writer.writerow(self._to_csv_row(item))

    def _append_csv(self, record: AffiliatorData) -> None:
        file_exists = self.output_path.exists()
        with open(self.output_path, "a", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=self._CSV_FIELDS,
                quoting=csv.QUOTE_ALL,
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(self._to_csv_row(record))

    def _load_csv(self) -> List[AffiliatorData]:
        from datetime import datetime

        results: List[AffiliatorData] = []
        # UTF-8-sig strips the BOM on read
        with open(self.output_path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                results.append(
                    AffiliatorData(
                        username=row["username"],
                        kategori=row["kategori"],
                        pengikut=int(row["pengikut"]),
                        gmv=float(row["gmv"]),
                        produk_terjual=int(row["produk_terjual"]),
                        rata_rata_tayangan=int(row["rata_rata_tayangan"]),
                        tingkat_interaksi=float(row["tingkat_interaksi"]),
                        nomor_kontak=row["nomor_kontak"] or None,
                        nomor_whatsapp=row.get("nomor_whatsapp", "") or None,
                        gmv_per_pembeli=float(row.get("gmv_per_pembeli", 0.0)),
                        gmv_harian=float(row.get("gmv_harian", 0.0)),
                        gmv_mingguan=float(row.get("gmv_mingguan", 0.0)),
                        gmv_bulanan=float(row.get("gmv_bulanan", 0.0)),
                        detail_url=row["detail_url"],
                        scraped_at=datetime.fromisoformat(row["scraped_at"]),
                    )
                )
        return results

    @staticmethod
    def _to_csv_row(item: AffiliatorData) -> dict:
        return {
            "username": item.username,
            "kategori": item.kategori,
            "pengikut": item.pengikut,
            "gmv": item.gmv,
            "produk_terjual": item.produk_terjual,
            "rata_rata_tayangan": item.rata_rata_tayangan,
            "tingkat_interaksi": item.tingkat_interaksi,
            "nomor_kontak": item.nomor_kontak if item.nomor_kontak is not None else "",
            "nomor_whatsapp": item.nomor_whatsapp if item.nomor_whatsapp is not None else "",
            "gmv_per_pembeli": item.gmv_per_pembeli,
            "gmv_harian": item.gmv_harian,
            "gmv_mingguan": item.gmv_mingguan,
            "gmv_bulanan": item.gmv_bulanan,
            "detail_url": item.detail_url,
            "scraped_at": item.scraped_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # XLSX helpers
    # ------------------------------------------------------------------

    def _save_xlsx(self, data: List[AffiliatorData]) -> None:
        import pandas as pd

        rows = [self._to_csv_row(item) for item in data]
        dataframe = pd.DataFrame(rows, columns=self._CSV_FIELDS)
        dataframe.to_excel(self.output_path, index=False)

    def _append_xlsx(self, record: AffiliatorData) -> None:
        rows = []
        if self.output_path.exists():
            for item in self._load_xlsx():
                rows.append(self._to_csv_row(item))
        rows.append(self._to_csv_row(record))

        import pandas as pd

        dataframe = pd.DataFrame(rows, columns=self._CSV_FIELDS)
        dataframe.to_excel(self.output_path, index=False)

    def _load_xlsx(self) -> List[AffiliatorData]:
        from datetime import datetime
        import pandas as pd

        results: List[AffiliatorData] = []
        dataframe = pd.read_excel(self.output_path)
        for row in dataframe.to_dict(orient="records"):
            results.append(
                AffiliatorData(
                    username=str(row["username"]),
                    kategori=str(row["kategori"]),
                    pengikut=int(row["pengikut"]),
                    gmv=float(row["gmv"]),
                    produk_terjual=int(row["produk_terjual"]),
                    rata_rata_tayangan=int(row["rata_rata_tayangan"]),
                    tingkat_interaksi=float(row["tingkat_interaksi"]),
                    nomor_kontak=(str(row.get("nomor_kontak")) if row.get("nomor_kontak") else None),
                    nomor_whatsapp=(str(row.get("nomor_whatsapp")) if row.get("nomor_whatsapp") else None),
                    gmv_per_pembeli=float(row.get("gmv_per_pembeli", 0.0)),
                    gmv_harian=float(row.get("gmv_harian", 0.0)),
                    gmv_mingguan=float(row.get("gmv_mingguan", 0.0)),
                    gmv_bulanan=float(row.get("gmv_bulanan", 0.0)),
                    detail_url=str(row["detail_url"]),
                    scraped_at=datetime.fromisoformat(str(row["scraped_at"])),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _ensure_parent_dir(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
