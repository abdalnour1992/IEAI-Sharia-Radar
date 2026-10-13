"""Strict date-only as-of inventory for already verified KAP financial catalogs.

This is a source scheduling gate, NOT a historical index eligibility attestation.
It never claims the timezone or licensing/financial-review conditions are verified.
"""
import argparse
import collections
import csv
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re


class TemporalCatalogError(ValueError):
    pass


def _read_catalog(path):
    if not path.is_file() or path.is_symlink():
        raise TemporalCatalogError("Missing or symlinked input catalog")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise TemporalCatalogError("Empty catalog: " + str(path))
    return rows


def _field(row, *names):
    for name in names:
        value = row.get(name, "")
        if value is not None and str(value).strip():
            return str(value).strip()
    raise TemporalCatalogError("Missing source field among " + ", ".join(names))


def normalize(raw):
    """Support both existing archive-index and newer KAP importer column layouts."""
    symbol = _field(raw, "symbol_filename")
    filing = _field(raw, "kap_disclosure_index", "kap_disclosure_index_filename")
    year = _field(raw, "fiscal_year", "fiscal_year_filename")
    period = _field(raw, "period_code", "period_code_filename")
    published = _field(raw, "publication_timestamp_as_listed")
    source_hash = _field(raw, "source_sha256", "sha256_uncompressed")
    filename = _field(raw, "filename")
    if not re.fullmatch(r"\d+", filing) or not re.fullmatch(r"20\d\d", year) or period not in {"1", "2", "3", "4"}:
        raise TemporalCatalogError("Invalid financial report year/period/disclosure ID")
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise TemporalCatalogError("Invalid exact original-source SHA256")
    if (not filename.endswith(f"_{filing}_{year}_{period}.xls")
            or not filename.startswith(symbol + "_")):
        raise TemporalCatalogError("Source filename does not match report identity")
    try:
        published_at = datetime.strptime(published, "%d.%m.%Y %H:%M:%S")
    except ValueError as exc:
        raise TemporalCatalogError("Invalid original publication date/time: " + published) from exc
    url = "https://www.kap.org.tr/tr/Bildirim/" + filing
    provided_url = raw.get("source_url")
    if provided_url and provided_url != url:
        raise TemporalCatalogError("Original report link does not match disclosure ID")
    return {
        "filename": filename, "symbol_string": symbol, "kap_disclosure_index": filing,
        "fiscal_year": year, "period": period, "issuer": raw.get("issuer", raw.get("issuer_from_document", "")),
        "published_at_as_listed": published, "published_day": published_at.date().isoformat(),
        "original_zip_member_sha256": source_hash,
        "original_kap_url": url, "original_timezone_verified": False,
        "historical_index_member_verified": False,
        "financial_mapping_reviewed": False,
        "research_dataset_complete": False,
    }


def audit_catalogs(paths, cutoff: date):
    """Include strictly dates BEFORE cutoff; day-of-publication excluded as precaution.

    The conservative day comparison is not a proof of trading-time availability:
    timezone, original report identity and amendments still need manual review.
    """
    seen = set()
    rows = []
    source_hashes = {}
    for path in paths:
        path = Path(path)
        raw_rows = _read_catalog(path)
        source_hashes[path.name] = sha256(path.read_bytes()).hexdigest()
        for raw in raw_rows:
            row = normalize(raw)
            identity = (row["kap_disclosure_index"], row["filename"])
            if identity in seen:
                raise TemporalCatalogError("Duplicate report across input catalogs")
            seen.add(identity)
            release = date.fromisoformat(row["published_day"])
            row["before_cutoff_date"] = release < cutoff
            row["temporal_bucket"] = "PRE_CUTOFF_CANDIDATE" if release < cutoff else (
                "SAME_DAY_EXCLUDED" if release == cutoff else "POST_CUTOFF_EXCLUDED")
            rows.append(row)
    counts = collections.Counter(x["temporal_bucket"] for x in rows)
    units = collections.Counter(f"{r['fiscal_year']}/{r['period']}" for r in rows)
    return {
        "summary": {
            "cutoff_date": cutoff.isoformat(),
            "source_catalog_sha256": source_hashes, "reports": len(rows),
            "distinct_symbol_strings": len({r["symbol_string"] for r in rows}),
            "period_counts": dict(sorted(units.items())), "availability_buckets": dict(counts),
            "research_dataset_complete": False,
            "historical_XK100_eligible": False,
            "warning": "Only a conservative report-date inventory; no verified timezone, corrections, constituent history, financial classifications or release rights."
        },
        "rows": rows
    }


def write_audit(result, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TemporalCatalogError("Refusing to overwrite nonempty output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "kap_asof_filing_catalog.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["rows"][0].keys()))
        writer.writeheader()
        writer.writerows(result["rows"])
    (output_dir / "kap_asof_summary.json").write_text(
        json.dumps(result["summary"], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit original KAP filing dates without forward-looking reuse")
    parser.add_argument("--catalog", type=Path, action="append", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cutoff = date.fromisoformat(args.as_of)
        result = audit_catalogs(args.catalog, cutoff)
        write_audit(result, args.output_dir)
        print(json.dumps(result["summary"], ensure_ascii=False))
        return 0
    except (TemporalCatalogError, OSError, ValueError) as exc:
        parser.exit(2, "KAP date audit failed: "+str(exc)+"\n")


if __name__ == "__main__":
    raise SystemExit(main())
