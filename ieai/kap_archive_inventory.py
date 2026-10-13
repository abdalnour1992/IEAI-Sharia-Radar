"""Inventory already-downloaded KAP bulk exports, entirely offline.

Do not fetch, bulk-scrape, decompress archives, or certify disclosures.
Preserves original source archive/file byte hashes for review and traceability.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys


class InventoryError(ValueError):
    pass


SUPPORTED = {".pdf", ".xlsx", ".xls", ".csv", ".xml", ".txt", ".json", ".zip", ".rar"}
PERIODS = {"3M", "6M", "9M", "FY", "ALL"}
MAX_FILES = 5000
MAX_FILE_BYTES = 1024 * 1024 * 1024


def _hash(path):
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_magic(path):
    with path.open("rb") as stream:
        return stream.read(8)


def build_inventory(directory: Path, archive: Path, year: int, period: str) -> dict:
    if year < 2020 or year > 2026 or period not in PERIODS:
        raise InventoryError("Specify actual official export year (2020-2026) and period")
    if not directory.is_dir() or directory.is_symlink():
        raise InventoryError("Already-extracted source directory is missing or a symlink")
    if not archive.is_file() or archive.is_symlink():
        raise InventoryError("Original unmodified KAP archive file is required")
    if archive.suffix.lower() not in {".rar", ".zip"}:
        raise InventoryError("Expected original KAP .rar or .zip archive")
    magic = _read_magic(archive)
    if not (magic.startswith(b"Rar!\x1a\x07") or magic.startswith(b"PK\x03\x04")):
        raise InventoryError("Archive bytes do not match RAR or ZIP format")
    if archive.stat().st_size > MAX_FILE_BYTES:
        raise InventoryError("Archive too large for this local inventory tool")
    files = []
    seen = set()
    for file in sorted(directory.rglob("*")):
        if file.is_symlink():
            raise InventoryError(f"Source folder contains symlink: {file.name}")
        if not file.is_file():
            continue
        rel = file.relative_to(directory).as_posix()
        if rel in seen or file.suffix.lower() not in SUPPORTED:
            raise InventoryError(f"Duplicate or unsupported extracted file: {rel}")
        seen.add(rel)
        if len(files) >= MAX_FILES or file.stat().st_size > MAX_FILE_BYTES:
            raise InventoryError("Input exceeds safe inventory file count or size")
        files.append({
            "relative_filename": rel,
            "kind": file.suffix.lower().lstrip("."),
            "size_bytes": file.stat().st_size,
            "sha256": _hash(file),
            "disclosure_id": None,
            "original_publication_timestamp": None,
            "fiscal_period_end": None,
            "issuer_verified": False,
            "account_mappings_reviewed": False,
            "status": "PENDING_SOURCE_LINKAGE_AND_REVIEW",
        })
    if not files:
        raise InventoryError("No recognized files found in extracted archive directory")
    return {
        "status": "RAW_ARCHIVE_INVENTORIED_NOT_VALIDATED",
        "research_dataset_complete": False,
        "approved_for_empirical_screening": False,
        "KAP_source_page": "https://www.kap.org.tr/tr",
        "export_year_selected": year,
        "export_period_selected": period,
        "retrieved_at_utc": None,
        "inventoried_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_filename": archive.name,
        "archive_sha256": _hash(archive),
        "archive_size_bytes": archive.stat().st_size,
        "file_count": len(files),
        "records": files,
        "warning": "Official year/period bulk export may exclude original audit PDFs, report revision metadata and exact disclosure publication timestamps. Manual source linkage required. No automated KAP requests performed.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inventory already-downloaded official KAP archive")
    parser.add_argument("--extracted-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--period", choices=sorted(PERIODS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise InventoryError("Refuse to overwrite existing audit evidence")
        report = build_inventory(args.extracted_dir, args.archive, args.year, args.period)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"Inventoried {report['file_count']} source files; no research data certified.")
        return 0
    except (InventoryError, OSError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
