"""Read a user-downloaded KAP FinancialTable.zip OFFLINE.

KAP .xls entries are HTML Excel exports, not binary XLS. All outputs are
unreviewed evidence candidates; never publish screening or XK100 membership.
No HTTP, Excel formula evaluation, macro execution, or automatic approval.
"""
import argparse
import collections
import csv
from datetime import datetime
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import zipfile

FILE_RE = re.compile(r"^(.+?)_(\d+)_(\d{4})_(\d+)\.xls$")
HEAD_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
DIV_RE = re.compile(r"<div[^>]*>\s*(Gönderim Tarihi|Bildirim Tipi|Yıl|Periyot):\s*([^<]+?)\s*</div>", re.I | re.S)
UNIT_RE = re.compile(r'<td class="financial-header-title">\s*Sunum Para Birimi\s*</td>\s*<td>(.*?)</td>', re.I | re.S)
CONS_RE = re.compile(r'<td class="financial-header-title">\s*Finansal Tablo Niteliği\s*</td>\s*<td>(.*?)</td>', re.I | re.S)
ROLE_RE = re.compile(r'<table class="financial-table\s+(tbl_[^"\s]+)')
VALUE_RE = re.compile(r'<td[^>]*class="taxonomy-context-value col-order-class-(\d+)"[^>]*>(.*?)</td>', re.I | re.S)
NEXT_RE = re.compile(r'<tr class="(?:general_role_\d+)-row-')
TAG_RE = re.compile(r"<[^>]+>")
UNITS = {"TL": 1, "1.000 TL": 1000, "1.000.000 TL": 1000000}
ACCOUNT_LABELS = {
    "total_assets": ("TOPLAM VARLIKLAR", "tbl_general_role_210015"),
    "balance_sheet_sources": ("TOPLAM KAYNAKLAR", "tbl_general_role_210015"),
    "shareholders_equity": ("TOPLAM ÖZKAYNAKLAR", "tbl_general_role_210015"),
    "cash_equivalents": ("Nakit ve Nakit Benzerleri", "tbl_general_role_210015"),
    "short_term_borrowings_line": ("Kısa Vadeli Borçlanmalar", "tbl_general_role_210015"),
    "long_term_borrowings_line": ("Uzun Vadeli Borçlanmalar", "tbl_general_role_210015"),
    "revenue": ("Hasılat", "tbl_general_role_310003"),
}
COMPILED_LABELS = {key: re.compile(r">\s*" + re.escape(title) + r"\s*</div>", re.I | re.S)
                   for key, (title, _) in ACCOUNT_LABELS.items()}
MAX_ARCHIVE_ENTRIES, MAX_TOTAL_UNCOMPRESSED, MAX_ENTRY_BYTES = 5000, 2_000_000_000, 15_000_000


class KapArchiveError(ValueError):
    pass


def strip(value):
    return html.unescape(TAG_RE.sub("", value)).strip()


def parse_amount(value):
    raw = value.replace(" ", "").replace("\u00a0", "").strip()
    if not re.fullmatch(r"-?\d+(?:\.\d{3})*(?:,\d+)?", raw):
        return None
    normalized = raw.replace(".", "").replace(",", ".")
    return float(normalized) if "." in normalized else int(normalized)


def parse_document(name, data):
    match = FILE_RE.fullmatch(name)
    if not match or not data.lstrip().startswith(b"<html"):
        raise KapArchiveError("Not a named HTML-in-XLS financial report: " + name)
    text = data.decode("utf-8", errors="replace")
    heading = text[:12000]
    fields = {k: v.strip() for k, v in DIV_RE.findall(heading)}
    h = HEAD_RE.findall(heading)
    unit_m = UNIT_RE.search(heading)
    cons_m = CONS_RE.search(heading)
    if len(h) < 2 or not unit_m or not cons_m:
        raise KapArchiveError("Incomplete financial report metadata: " + name)
    symbol, disclosure_index, year, period = match.groups()
    if fields.get("Yıl") != year or fields.get("Periyot") != period or fields.get("Bildirim Tipi") != "FR":
        raise KapArchiveError("Report year/period/type mismatch: " + name)
    try:
        release = datetime.strptime(fields["Gönderim Tarihi"], "%d.%m.%Y %H:%M:%S")
    except (KeyError, ValueError) as exc:
        raise KapArchiveError("Missing or unparseable release timestamp: " + name) from exc
    unit = strip(unit_m.group(1))
    if unit not in UNITS:
        raise KapArchiveError("Unknown monetary unit: " + name)
    role = ROLE_RE.search(text)
    record = {
        "filename": name, "symbol_filename": symbol, "kap_disclosure_index": disclosure_index,
        "fiscal_year": year, "period_code": period,
        "issuer": strip(h[0]),
        "publication_timestamp_as_listed": fields["Gönderim Tarihi"],
        "publication_date_iso": release.date().isoformat(),
        "publication_timezone_verified": False,
        "consolidation": strip(cons_m.group(1)),
        "presentation_unit": unit, "scale_to_try": UNITS[unit],
        "taxonomy_first_table": role.group(1) if role else "NONE",
        "bytes": len(data), "source_sha256": sha256(data).hexdigest(),
        "source_url": "https://www.kap.org.tr/tr/Bildirim/" + disclosure_index,
        "status": "STRUCTURE_PARSED_UNREVIEWED",
    }
    lines = []
    for field, compiled in COMPILED_LABELS.items():
        title, expected_role = ACCOUNT_LABELS[field]
        for occurrence in compiled.finditer(text):
            origin = text.rfind('<table class="financial-table', 0, occurrence.start())
            if origin < 0 or expected_role not in text[origin:origin+130]:
                continue
            section = text[occurrence.end():occurrence.end()+2800]
            boundary = NEXT_RE.search(section)
            if boundary:
                section = section[:boundary.start()]
            values = {int(k): strip(v) for k, v in VALUE_RE.findall(section)}
            current = parse_amount(values.get(4, ""))
            if current is None:
                continue
            lines.append({
                "filename": name, "symbol_filename": symbol, "kap_disclosure_index": disclosure_index,
                "publication_timestamp_as_listed": fields["Gönderim Tarihi"], "fiscal_year": year,
                "period_code": period, "consolidation": record["consolidation"],
                "presentation_unit": unit, "scale_to_try": UNITS[unit],
                "account": field, "original_account_label": title,
                "raw_current": values[4], "raw_comparative": values.get(5, ""),
                "amount_in_original_units": current, "value_try_candidate": current*UNITS[unit],
                "taxonomy_table": expected_role, "source_sha256": record["source_sha256"],
                "source_url": record["source_url"],
                "review_status": "UNREVIEWED_CANDIDATE_NOT_FOR_EMPIRICAL_SCREENING",
            })
            break
    return record, lines


def inspect_archive(source: Path, output_dir: Path):
    if output_dir.exists() and any(output_dir.iterdir()):
        raise KapArchiveError("Output directory must be absent or empty; no overwrite")
    with zipfile.ZipFile(source) as z:
        items = z.infolist()
        if len(items) > MAX_ARCHIVE_ENTRIES or sum(x.file_size for x in items) > MAX_TOTAL_UNCOMPRESSED:
            raise KapArchiveError("Archive exceeds safe limits")
        if any(x.is_dir() or "/" in x.filename or "\\" in x.filename or
               x.file_size > MAX_ENTRY_BYTES or not FILE_RE.fullmatch(x.filename) for x in items):
            raise KapArchiveError("Archive has unknown filename, directory, or oversized member")
        catalog, candidates = [], []
        for item in items:
            data = z.read(item)
            one, lines = parse_document(item.filename, data)
            catalog.append(one)
            candidates.extend(lines)
    if not catalog:
        raise KapArchiveError("Empty archive")
    by_source = collections.defaultdict(dict)
    for value in candidates:
        by_source[value["filename"]][value["account"]] = value
    comparisons = [(r["total_assets"]["amount_in_original_units"],
                    r["balance_sheet_sources"]["amount_in_original_units"])
                   for r in by_source.values()
                   if "total_assets" in r and "balance_sheet_sources" in r]
    mismatches = sum(a != b for a, b in comparisons)
    if mismatches:
        raise KapArchiveError("Financial assets/source identities disagree; investigate before output")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("filing_catalog.csv", catalog), ("account_candidates.csv", candidates)):
        with (output_dir/name).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    result = {
        "archive_name": source.name, "archive_sha256": sha256(source.read_bytes()).hexdigest(),
        "filings": len(catalog), "distinct_symbol_strings": len(set(x["symbol_filename"] for x in catalog)),
        "candidates": len(candidates),
        "reported_units": dict(collections.Counter(x["presentation_unit"] for x in catalog)),
        "taxonomies": dict(collections.Counter(x["taxonomy_first_table"] for x in catalog)),
        "balance_sheet_identities_verified": len(comparisons),
        "balance_sheet_identities_failed": mismatches,
        "candidate_counts": dict(collections.Counter(x["account"] for x in candidates)),
        "research_dataset_complete": False, "screening_approved": False,
        "historical_XK100_membership_verified": False,
        "license_and_publication_timezone_verified": False,
        "warning": "One period/year source snapshot. Sector-specific templates and financial note classification require independent review. No debt or Sharia classification is inferred."
    }
    (output_dir/"source_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline KAP HTML-in-XLS ZIP catalog and provisional accounts")
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a=p.parse_args(argv)
    try:
        result=inspect_archive(a.archive, a.output_dir)
        print(json.dumps({"filings": result["filings"], "candidates": result["candidates"],
                          "status": "UNREVIEWED"}, ensure_ascii=False))
        return 0
    except (KapArchiveError, OSError, zipfile.BadZipFile) as exc:
        p.exit(2, f"Validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
