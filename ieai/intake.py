"""Compile explicitly reviewed source records; unknown values remain unknown.

Review flags are declarations by the data curator, not source authentication.
The public-source downloader deliberately does not produce these flags.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from .data import DataError, SCHEMAS, validate_frame


FINANCIAL_FIELDS = ["total_assets", "interest_bearing_debt", "interest_bearing_assets", "total_revenue",
                    "noncompliant_revenue", "activity_pass", "other_criteria_pass"]
FACT_COLUMNS = ["bundle_id", "symbol", "field", "value", "scale", "currency", "period_end",
                "published_at", "effective_from", "source_url", "source_sha256", "evidence_locator",
                "mapping_note", "unit_basis", "review_status"]
EVENT_COLUMNS = ["symbol", "event_kind", "available_at", "effective_from", "source_url",
                 "source_sha256", "evidence_locator", "review_status"]


def _evidence(frame, columns):
    missing = set(columns) - set(frame)
    if missing:
        raise DataError(f"Source ledger missing columns: {sorted(missing)}")
    frame = frame.copy()
    for name in ["symbol", "source_url", "source_sha256", "evidence_locator", "review_status"]:
        if frame[name].isna().any() or frame[name].astype(str).str.strip().eq("").any():
            raise DataError(f"Missing source evidence: {name}")
    if not frame.source_sha256.astype(str).str.fullmatch(r"[0-9a-f]{64}").all():
        raise DataError("Source SHA256 must identify the archived original bytes")
    if not frame.source_url.astype(str).str.match(r"^https://").all():
        raise DataError("Original source HTTPS URL required")
    if not frame.review_status.eq("reviewed").all():
        raise DataError("Unreviewed source records cannot be promoted to research inputs")
    return frame


def decision_availability(published_at):
    """Conservative daily convention: first decision after local publication day.

    Original times are retained in the source ledger. Date-only sources are also
    deferred one day; this never invents knowledge at the preceding close.
    """
    value = pd.Timestamp(published_at)
    if pd.isna(value):
        raise DataError("Invalid publication timestamp")
    if value.tzinfo is not None:
        value = value.tz_convert("Europe/Istanbul").tz_localize(None)
    return value.normalize() + pd.Timedelta(days=1)


def _iso_day(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
        raise DataError("Effective/period dates must be explicit YYYY-MM-DD dates")
    return pd.Timestamp(value)


def compile_membership(events, coverage, start, end):
    events = _evidence(events, EVENT_COLUMNS)
    if coverage.get("continuity_review_status") != "reviewed" or str(coverage.get("complete_through") or "") < end:
        raise DataError("Reviewed initial snapshot AND complete exceptional-change coverage required")
    if not isinstance(coverage.get("initial_member_count"), int) or coverage["initial_member_count"] <= 0:
        raise DataError("Declare the independently checked initial snapshot count")
    if not events.event_kind.isin(["snapshot", "add", "remove", "reserve"]).all():
        raise DataError("Unknown membership event; resolve issuer/code renames explicitly before compilation")
    for field in ("available_at", "effective_from"):
        events[field] = events[field].map(_iso_day)
    events["usable_at"] = events[["available_at", "effective_from"]].max(axis=1)
    snapshots = events[events.event_kind == "snapshot"]
    if snapshots.empty:
        raise DataError("Changes and reserve lists cannot replace a complete initial membership snapshot")
    if snapshots[["available_at", "effective_from", "source_url", "source_sha256"]].drop_duplicates().shape[0] != 1:
        raise DataError("Exactly one coherent initial snapshot source/version is required")
    if snapshots.symbol.duplicated().any() or len(snapshots) != coverage["initial_member_count"]:
        raise DataError("Initial snapshot count mismatch or duplicate member")
    if snapshots.effective_from.iloc[0] > pd.Timestamp(start):
        raise DataError("Initial snapshot starts after requested membership coverage")
    boundary = snapshots.usable_at.iloc[0]
    changes = events[~events.event_kind.isin(["snapshot", "reserve"])]
    if (changes.usable_at < boundary).any():
        raise DataError("Changes precede the initial snapshot knowledge boundary")
    if changes.duplicated(["symbol", "usable_at"]).any():
        raise DataError("Ambiguous same-day membership transitions require reviewed consolidation")
    state, rows = {}, []
    def append(fact, eligible):
        symbol = fact.symbol
        if symbol in state:
            rows[state[symbol]]["effective_to"] = (fact.usable_at - pd.Timedelta(days=1)).date().isoformat()
        rows.append({"symbol": symbol, "available_at": fact.available_at.date().isoformat(),
                     "effective_from": fact.effective_from.date().isoformat(), "effective_to": end,
                     "eligible": eligible, "rule_set": coverage.get("rule_set", "historical_XK100_attestation"),
                     "source_url": fact.source_url, "source_sha256": fact.source_sha256})
        state[symbol] = len(rows)-1
    for fact in snapshots.sort_values("symbol").itertuples():
        append(fact, True)
    for fact in changes.sort_values(["usable_at", "symbol"]).itertuples():
        if fact.usable_at > pd.Timestamp(end):
            continue
        current = fact.symbol in state and rows[state[fact.symbol]]["eligible"]
        if fact.event_kind == "add" and current or fact.event_kind == "remove" and not current:
            raise DataError("Inconsistent change chain: missing exceptional event or wrong membership list")
        append(fact, fact.event_kind == "add")
    output = pd.DataFrame(rows)
    # Zero-length transitions at the snapshot boundary cannot establish history.
    output = output[pd.to_datetime(output.effective_from) <= pd.to_datetime(output.effective_to)]
    return validate_frame("eligibility.csv", output)


def compile_facts(facts, price_unit_basis):
    facts = _evidence(facts, FACT_COLUMNS)
    if not price_unit_basis:
        raise DataError("Reviewed price/share/volume unit basis is required")
    if not facts.field.isin([*FINANCIAL_FIELDS, "shares_outstanding"]).all():
        raise DataError("Unmapped source account; total liabilities are not interest-bearing debt")
    for name in ["bundle_id", "mapping_note", "unit_basis"]:
        if facts[name].isna().any() or facts[name].astype(str).str.strip().eq("").any():
            raise DataError(f"Explicit account mapping and units required: {name}")
    facts["available_at"] = facts.published_at.map(decision_availability)
    financials, shares, gaps = [], [], []
    for key, group in facts.groupby(["symbol", "bundle_id"], sort=True):
        symbol, bundle = key
        if group.field.duplicated().any():
            raise DataError("Duplicate source fields within a facts bundle")
        periods = group.period_end.astype(str).unique()
        if len(periods) != 1:
            raise DataError("Mixed financial periods within a facts bundle")
        available = group.available_at.max()
        values = {}
        for fact in group.itertuples():
            if fact.field in {"activity_pass", "other_criteria_pass"}:
                text = str(fact.value).lower().strip()
                if text not in {"true", "false", "1", "0"}:
                    raise DataError("Activity/other-criteria findings must be explicit source attestations")
                values[fact.field] = text in {"true", "1"}
                continue
            if fact.currency != "TRY" and fact.field != "shares_outstanding":
                raise DataError("Financial source currency must be TRY; conversion requires a separate review")
            try:
                value, scale = float(fact.value), float(fact.scale)
            except (ValueError, TypeError) as exc:
                raise DataError("Source values must be normalized numeric literals, not guessed number locales") from exc
            if not np.isfinite([value, scale]).all() or scale <= 0 or value < 0:
                raise DataError("Invalid source value/scale")
            values[fact.field] = value*scale
            if not np.isfinite(values[fact.field]):
                raise DataError("Scaled source value is nonfinite")
        source_url = group.source_url.iloc[0]
        if "shares_outstanding" in values:
            fact = group[group.field == "shares_outstanding"].iloc[0]
            if fact.unit_basis != price_unit_basis:
                raise DataError("Share count basis does not match reviewed price and volume units")
            shares.append({"symbol": symbol, "available_at": fact.available_at,
                           "effective_from": _iso_day(fact.effective_from),
                           "shares_outstanding": values["shares_outstanding"], "source_url": fact.source_url,
                           "source_sha256": fact.source_sha256})
        financial_values = {k: values[k] for k in FINANCIAL_FIELDS if k in values}
        if financial_values:
            missing = sorted(set(FINANCIAL_FIELDS)-set(financial_values))
            if missing:
                gaps.append({"symbol": symbol, "bundle_id": bundle, "missing_fields": missing})
            else:
                financials.append({"symbol": symbol, "available_at": available,
                                   "period_end": _iso_day(periods[0]), "source_url": source_url,
                                   "evidence_bundle": bundle, **financial_values})
    frames = {}
    for name, rows in [("financials.csv", financials), ("shares.csv", shares)]:
        if rows:
            frames[name] = validate_frame(name, pd.DataFrame(rows))
    return frames, gaps


def compile_intake(directory, output):
    folder, target = Path(directory), Path(output)
    if target.exists() and any(target.iterdir()):
        raise DataError("Intake output must be empty; do not retain stale previously complete inputs")
    target.mkdir(parents=True, exist_ok=True)
    spec = json.loads((folder / "intake_review.json").read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or not spec.get("dataset_id") or spec.get("source_review_status") != "reviewed":
        raise DataError("Dataset identity and declared source review required")
    frames, gaps = {}, []
    if (folder / "membership_events.csv").exists():
        try:
            frames["eligibility.csv"] = compile_membership(pd.read_csv(folder / "membership_events.csv"),
                spec["membership_coverage"], spec["study_start"], spec["study_end"])
        except DataError as exc:
            gaps.append({"component": "membership", "error": str(exc)})
    if (folder / "source_facts.csv").exists():
        fact_frames, fact_gaps = compile_facts(pd.read_csv(folder / "source_facts.csv", dtype=str), spec.get("price_unit_basis"))
        frames.update(fact_frames); gaps.extend(fact_gaps)
    for name in ("prices.csv", "benchmarks.csv", "factors.csv", "factors_ff3.csv", "market_factors.csv", "cpi.csv"):
        if (folder / name).exists():
            frames[name] = validate_frame(name, pd.read_csv(folder / name))
    for name in ["prices.csv", "eligibility.csv", "shares.csv", "financials.csv", "benchmarks.csv", "factors.csv", "factors_ff3.csv"]:
        if name not in frames:
            gaps.append({"component": name, "error": "missing reviewed research input"})
    for name, frame in frames.items():
        frame.to_csv(target / name, index=False, date_format="%Y-%m-%d")
    hashes = {name: sha256((target/name).read_bytes()).hexdigest() for name in frames}
    sources = spec.get("sources", [])
    for name in frames:
        if not any(isinstance(x, dict) and x.get("file") == name and x.get("url") and
                   x.get("provider") and x.get("retrieved_at") for x in sources):
            gaps.append({"component": name, "error": "missing per-file source provenance"})
    report = {"dataset_id": spec["dataset_id"], "status": "INPUTS_COMPILED_COVERAGE_REQUIRES_AUDIT" if not gaps else "INCOMPLETE_INPUTS",
              "research_dataset_complete": False, "rows": {name: len(frame) for name, frame in frames.items()},
              "gaps": gaps, "sha256": hashes,
              "source_ledger_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()
                                      if p.name in {"source_facts.csv", "membership_events.csv", "intake_review.json"}},
              "note": "Review flags are curator declarations, not source authentication"}
    manifest = {"dataset_id": spec["dataset_id"], "dataset_kind": "real", "audit_status": "unreviewed",
                "currency": "TRY", "universe": spec.get("universe", "Historical XK100; continuity audit pending"),
                "price_convention": spec.get("price_unit_basis", "unreviewed"), "sources": sources, "sha256": hashes,
                "intake_status": report["status"], "research_dataset_complete": False,
                "source_ledger_sha256": report["source_ledger_sha256"],
                "coverage_evidence": spec.get("coverage_evidence", {}),
                "membership_coverage": spec.get("membership_coverage", {})}
    (target/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (target/"intake_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
