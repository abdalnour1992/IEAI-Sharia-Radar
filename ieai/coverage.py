"""Observable coverage checks, distinct from authenticity and hypothesis tests."""
import json
from pathlib import Path
import pandas as pd
from .data import Dataset, DataError
from .screening import effective_fact_stream


def audit_coverage(directory, protocol):
    root = Path(directory); issues = []; summary = {}; samples = []
    def issue(component, message):
        issues.append({"component": component, "reason": message})
    try:
        dataset = Dataset.from_directory(root)
        dataset.require_research_inputs(protocol.screening_profile)
    except (DataError, ValueError, OSError) as exc:
        report = {"coverage_complete_for_declared_scope": False, "status": "INVALID_OR_INCOMPLETE_INPUTS",
                  "issues": [{"component": "input_contract", "reason": str(exc)}]}
        return report
    start, end = pd.Timestamp(protocol.study_start), pd.Timestamp(protocol.study_end)
    manifest = dataset.manifest
    if manifest["dataset_kind"] != "real":
        issue("kind", "Synthetic fixtures cannot certify empirical input coverage")
    evidence = manifest.get("coverage_evidence", {})
    membership = manifest.get("membership_coverage", {})
    if membership.get("continuity_review_status") != "reviewed" or str(membership.get("complete_through") or "") < protocol.study_end:
        issue("membership", "Missing declared review of initial snapshot, exceptional events and code continuity")
    for key in ["disclosures_complete_through", "capital_events_complete_through"]:
        if str(evidence.get(key) or "") < protocol.study_end:
            issue(key, "Complete point-in-time source coverage has not been attested")
    if evidence.get("price_share_volume_basis_reviewed") is not True:
        issue("units", "Price, share counts, volumes and corporate-action units require a matching source review")
    if evidence.get("financial_definitions_reviewed") is not True:
        issue("financial_definitions", "Debt/account classifications and activity findings have not been attested")
    if evidence.get("local_factors_reviewed") is not True or evidence.get("factor_market") != "Turkey":
        issue("factors", "Country, currency, frequency, separate FF3/FF5 SMB and methodology require review")
    benchmarks = dataset.get("benchmarks.csv")
    calendars = {}
    for name in ["BIST_100", "BIST_PARTICIPATION_100"]:
        series = benchmarks[benchmarks.benchmark == name] if not benchmarks.empty else pd.DataFrame()
        if series.empty or not series.kind.eq("total_return").all():
            issue(name, "Complete TRY total-return benchmark required")
            continue
        window = series[series.date.between(start, end)]
        calendars[name] = pd.DatetimeIndex(window.date)
        summary[name] = {"rows": len(window), "first": None if window.empty else window.date.min().date().isoformat(),
                         "last": None if window.empty else window.date.max().date().isoformat()}
    if len(calendars) != 2 or not calendars["BIST_100"].equals(calendars["BIST_PARTICIPATION_100"]):
        issue("calendar", "Official benchmark equity-session calendars are absent or disagree")
        sessions = pd.DatetimeIndex([])
    else:
        sessions = calendars["BIST_PARTICIPATION_100"]
        if not len(sessions) or sessions[-1] < end:
            issue("calendar", "Declared study-end coverage is missing; do not silently shorten the study")
    for name in ["factors_ff3.csv", "factors.csv"]:
        factors = dataset.get(name)
        missing = len(sessions) if factors.empty else len(sessions.difference(pd.DatetimeIndex(factors.date)))
        summary[name] = {"missing_sessions": missing, "rows": len(factors)}
        if factors.empty or missing:
            issue(name, "Missing model-specific daily Turkish factors")
    prices, shares, financials, eligibility = [dataset.get(n) for n in ["prices.csv", "shares.csv", "financials.csv", "eligibility.csv"]]
    needed, quote_gaps, share_gaps, financial_gaps = 0, 0, 0, 0
    for symbol, attestations in eligibility[eligibility.eligible].groupby("symbol", sort=True):
        dates = pd.DatetimeIndex([])
        for fact in attestations.itertuples():
            dates = dates.union(sessions[(sessions >= max(fact.available_at, fact.effective_from)) & (sessions <= fact.effective_to)])
        if not len(dates):
            continue
        needed += len(dates)
        quotes = prices[prices.symbol == symbol]
        missing_quotes = dates.difference(pd.DatetimeIndex(quotes.date))
        quote_gaps += len(missing_quotes)
        left = pd.DataFrame({"date": dates})
        sf = effective_fact_stream(shares[shares.symbol == symbol], "effective_from")
        s = pd.merge_asof(left, sf[["usable_at", "shares_outstanding"]], left_on="date", right_on="usable_at", direction="backward")
        missing_shares = int(s.shares_outstanding.isna().sum()); share_gaps += missing_shares
        ff = effective_fact_stream(financials[financials.symbol == symbol], "period_end") if not financials.empty else pd.DataFrame()
        if ff.empty:
            missing_financial = len(dates)
        else:
            f = pd.merge_asof(left, ff[["usable_at", "period_end"]], left_on="date", right_on="usable_at", direction="backward")
            missing_financial = int((f.period_end.isna() | ((f.date-f.period_end).dt.days > protocol.financial_max_age_days)).sum())
        financial_gaps += missing_financial
        if len(missing_quotes) or missing_shares or missing_financial:
            samples.append({"symbol": symbol, "missing_quotes": len(missing_quotes), "missing_share_facts": missing_shares,
                            "missing_or_stale_financials": missing_financial})
    summary["member_session_coverage"] = {"required_cells": needed, "missing_quotes": quote_gaps,
                                         "missing_shares": share_gaps, "missing_or_stale_financials": financial_gaps}
    if not needed or quote_gaps or share_gaps or financial_gaps:
        issue("member_session_coverage", "Member prices, effective issued shares or published financials are incomplete")
    report = {"status": "COVERAGE_CHECKS_PASS_SOURCE_REVIEW_DECLARED" if not issues else "RESEARCH_INPUTS_INCOMPLETE",
              "coverage_complete_for_declared_scope": not issues, "study_start": protocol.study_start, "study_end": protocol.study_end,
              "input_sha256": dataset.hashes, "summary": summary, "issues": issues, "gap_samples": samples[:100],
              "source_authentication": "Not performed; source-review flags are curator declarations",
              "hypotheses_confirmed": False}
    (root/"coverage_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
