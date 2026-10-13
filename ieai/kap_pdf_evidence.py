"""Offline, fail-closed KAP report PDF evidence checks (NOT an API crawler).

Verifies SHA-256, exact numbers on referenced printed PDF pages, raw units,
and basic financial identities. Does not verify semantic accounting mappings,
legality, Sharia compliance, historical index membership, or corpus coverage.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unicodedata


class EvidenceError(ValueError):
    """Insufficient source authenticity or evidence integrity."""


MANDATORY = (
    "symbol", "bundle_id", "observation", "raw_value", "raw_unit",
    "scale_to_try", "period_end", "published_at_source",
    "primary_pdf_page", "source_url", "primary_pdf_sha256", "review_status",
)
NON_PROMOTABLE = {"source_observed_not_certified", "pending_human_review"}
PAGE_RE = re.compile(r"\bp\.\s*(\d+)\b", re.I)
NUMBER_RE = re.compile(r"(?<![0-9])(?:[0-9]{1,3}(?:[.,][0-9]{3})+|[0-9]+)(?![0-9])")


def _verify_file(folder: Path, name: str, expected_sha: str) -> Path:
    if not name or name != Path(name).name or Path(name).is_absolute():
        raise EvidenceError("PDF name must be a simple basename")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise EvidenceError("Expected SHA256 is invalid")
    path = folder / name
    if not path.is_file() or path.is_symlink():
        raise EvidenceError(f"Missing source or symlink: {name}")
    if sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise EvidenceError(f"Original source hash mismatch: {name}")
    return path


def _read_observations(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(MANDATORY) - set(reader.fieldnames):
            raise EvidenceError("CSV missing required observations columns")
        rows = list(reader)
    if not rows:
        raise EvidenceError("Empty observations CSV")
    return rows


def _page_number(locator: str, total: int) -> int:
    match = PAGE_RE.search(locator or "")
    if not match:
        raise EvidenceError(f"Missing PDF printed page in locator: {locator!r}")
    page = int(match.group(1))
    if page < 1 or page > total:
        raise EvidenceError("PDF page outside source document")
    return page


def _contains_amount(text: str, integer: int) -> bool:
    return any(int(tok.replace(".", "").replace(",", "")) == integer
               for tok in NUMBER_RE.findall(text))


def validate_observations(rows: list[dict], manifest: dict,
                          turkish_pages: list[str], english_pages: list[str]) -> dict:
    """Check amount occurrence on claimed pages, NOT whether account label is right."""
    if manifest.get("research_dataset_complete") is not False or manifest.get("status") == "reviewed":
        raise EvidenceError("Pilot evidence may not attest empirical completion")
    if manifest.get("currency") != "TRY" or manifest.get("raw_monetary_unit") != "1000 TRY":
        raise EvidenceError("Pilot monetary source must be thousand TRY")
    if manifest.get("publication_timezone") not in {"unverified", "Europe/Istanbul"}:
        raise EvidenceError("Publication timezone is undocumented")
    if manifest.get("consolidated") is not True:
        raise EvidenceError("Expected original consolidated financials")
    ref = manifest.get("source_url")
    if not isinstance(ref, str) or not re.fullmatch(
            r"https://www\.kap\.org\.tr/(?:tr|en)/Bildirim/\d+", ref):
        raise EvidenceError("Missing original KAP disclosure link")
    digest = manifest["files_sha256"]["turkish_original"]
    values = {}
    for r in rows:
        field = r["observation"]
        if not field or field in values:
            raise EvidenceError("Blank/duplicate account observation")
        publication = manifest["publication_timestamp_as_listed"]
        if not r.get("bundle_id") or not r.get("published_at_source", "").startswith(publication):
            raise EvidenceError(f"Missing source bundle or original publication timestamp: {field}")
        if (r["symbol"] != manifest["symbol"] or r["source_url"] != ref
                or r["primary_pdf_sha256"] != digest
                or r["period_end"] != manifest["fiscal_period_end"]
                or r["review_status"] not in NON_PROMOTABLE):
            raise EvidenceError(f"Source identity or review flag mismatch: {field}")
        if not re.fullmatch(r"\d+", r["raw_value"] or ""):
            raise EvidenceError(f"Invalid nonnegative raw numeric amount: {field}")
        amount = int(r["raw_value"])
        if (r["raw_unit"], r["scale_to_try"]) not in {
            ("TRY_thousands", "1000"), ("shares", "1")
        }:
            raise EvidenceError(f"Source unit and scale mismatch: {field}")
        pg = _page_number(r["primary_pdf_page"], len(turkish_pages))
        if not _contains_amount(turkish_pages[pg - 1], amount):
            raise EvidenceError(f"Raw amount missing from Turkish PDF p{pg}: {field}")
        en = (r.get("translation_pdf_page") or "").strip()
        if en:
            p = _page_number(en, len(english_pages))
            if not _contains_amount(english_pages[p - 1], amount):
                raise EvidenceError(f"Raw amount missing from translated PDF p{p}: {field}")
        values[field] = amount
    return values


def reconciliation(values: dict) -> dict:
    formulas = {
        "borrowings_by_maturity": ("total_financial_borrowings",
                                   ["short_term_financial_borrowings",
                                    "long_term_financial_borrowings"]),
        "borrowings_by_instrument": ("total_financial_borrowings",
                                     ["bank_borrowings_including_accruals",
                                      "convertible_bond_liability", "lease_liabilities_total"]),
        "interest_expense_components": ("interest_expense_total",
                                        ["bank_interest_expense",
                                         "convertible_bond_interest_expense"]),
    }
    results = {}
    for name, (whole, parts) in formulas.items():
        if not all(k in values for k in [whole, *parts]):
            results[name] = "INCOMPLETE_FIELDS"
        else:
            results[name] = "PASS" if values[whole] == sum(values[k] for k in parts) else "FAIL"
    return results


def build_report(manifest: dict, values: dict) -> dict:
    reconciliation_results = reconciliation(values)
    ratios = {}
    assets, revenue = values.get("total_assets"), values.get("revenue")
    if assets and "total_financial_borrowings" in values:
        debt = values["total_financial_borrowings"]
        ratios["debt_assets_including_leases_pct"] = round(100 * debt / assets, 4)
        if "lease_liabilities_total" in values:
            ratios["debt_assets_excluding_leases_pct"] = round(
                100 * (debt - values["lease_liabilities_total"]) / assets, 4)
    if revenue and "interest_income" in values:
        ratios["interest_to_sales_pct"] = round(100 * values["interest_income"] / revenue, 4)
        if "interest_support_income" in values:
            ratios["interest_plus_support_to_sales_sensitivity_pct"] = round(
                100 * (values["interest_income"] + values["interest_support_income"]) / revenue, 4)
    return {
        "status": "NUMERIC_ANCHORS_PASS_REVIEW_PENDING" if all(
            x == "PASS" for x in reconciliation_results.values()
        ) else "RECONCILIATION_INCOMPLETE_OR_FAILED",
        "research_dataset_complete": False,
        "approved_for_empirical_screening": False,
        "classification_decision": "UNKNOWN",
        "historical_XK100_membership_attested": False,
        "observations_checked": len(values),
        "observed_accounts": sorted(values),
        "reconciliations": reconciliation_results,
        "descriptive_ratios_only": ratios,
        "research_30_mapping_gaps": {
            "interest_bearing_debt": "Lease classification needs approved rules",
            "interest_bearing_assets": "Complete reviewed asset taxonomy missing",
            "noncompliant_revenue": "Interest and subsidies are not a validated full numerator",
            "activity_pass": "unattested",
            "other_criteria_pass": "unattested",
            "shares_outstanding": "Nominal shares require price/capital-action basis review"
        },
        "source_url": manifest["source_url"],
        "period_end": manifest["fiscal_period_end"],
        "source_published_as_listed": manifest["publication_timestamp_as_listed"],
        "publication_timezone": manifest["publication_timezone"],
        "currency": "TRY", "monetary_multiplier": 1000,
        "caveat": "Only exact PDF numeric presence tested: NOT label-level semantic verification, Sharia attestation, licensing or complete historical coverage."
    }


def verify_bundle(folder: Path, manifest_path: Path, observed_csv: Path) -> dict:
    from pypdf import PdfReader
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digests = manifest["files_sha256"]
    kinds = {
        "original": ("source", "turkish_original"),
        "translation": ("translated_reference", "english_translation"),
        "kap_export": ("filing_export", "kap_export"),
    }
    paths = {name: _verify_file(folder, manifest[name_field], digests[digest_field])
             for name, (name_field, digest_field) in kinds.items()}
    original, english, kap = [PdfReader(paths[k]) for k in kinds]
    if len(original.pages) < 10 or len(english.pages) < 10 or len(kap.pages) < 2:
        raise EvidenceError("Unexpectedly short report PDF")
    turkish_pages = [(p.extract_text() or "") for p in original.pages]
    english_pages = [(p.extract_text() or "") for p in english.pages]
    issuer = manifest.get("issuer", "").strip()
    if len(issuer.split()) < 2:
        raise EvidenceError("Need legal issuer name in manifest")
    def normalized(value: str) -> str:
        return " ".join(unicodedata.normalize(
            "NFKD", value.replace("ı", "i").replace("İ", "I")
        ).encode("ascii", "ignore").decode().upper().split())
    anchor = " ".join(normalized(issuer).split()[:2])
    if anchor not in normalized(turkish_pages[0]) or anchor not in normalized(english_pages[0]):
        raise EvidenceError("Company name not found on both report cover pages")
    values = validate_observations(_read_observations(observed_csv), manifest,
                                   turkish_pages, english_pages)
    report = build_report(manifest, values)
    if "FAIL" in report["reconciliations"].values():
        raise EvidenceError("Internal financial identity mismatch")
    report["original_files_sha256"] = digests
    report["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline original KAP PDF evidence check (no compliance certification)")
    parser.add_argument("--pdf-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise EvidenceError("Refuse to overwrite an existing audit")
        report = verify_bundle(args.pdf_dir, args.manifest, args.observations)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps({k: report[k] for k in (
            "status", "observations_checked", "classification_decision")}))
        return 0
    except (EvidenceError, KeyError, ValueError, OSError) as exc:
        print(f"Evidence check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
