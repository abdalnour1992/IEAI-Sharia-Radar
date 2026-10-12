from datetime import datetime, timezone
from io import BytesIO
import importlib.metadata
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import numpy as np
import pandas as pd
from . import __version__
from .backtest import STRATEGIES, performance, simulate
from .data import DataError
from .econometrics import factor_models, panel_model
from .features import feature_panel
from .learning import forecast_metrics, walk_forward
from .screening import screening_panel


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def run_experiment(dataset, protocol, allow_synthetic=False, progress=None):
    if dataset.manifest["dataset_kind"] == "synthetic" and not allow_synthetic:
        raise DataError("Synthetic datasets are disabled for research; explicitly opt in for software tests only")
    dataset.require_research_inputs(protocol.screening_profile)
    def stage(message):
        if progress:
            progress(message)
    stage("point_in_time_screening")
    eligibility = screening_panel(dataset, protocol)
    stage("backward_features_and_separate_forward_labels")
    features = feature_panel(dataset, eligibility, protocol)
    # Labels maturing after the declared study end are not evaluated or used in training.
    outside = features.label_end > pd.Timestamp(protocol.study_end)
    features.loc[outside, ["target_event", "forward_loss"]] = np.nan
    stage("purged_walk_forward_and_frozen_holdout")
    scores, audits = walk_forward(features, protocol)
    start = scores.loc[scores.score.notna(), "date"].min()
    scores = scores[scores.date >= start].copy()
    stage("next_session_execution_and_costs")
    tests = {name: simulate(scores, protocol, name) for name in STRATEGIES}
    factors = dataset.get("factors.csv")
    reference = None if factors.empty else factors.set_index("date").rf
    metrics = {}
    for name, test in tests.items():
        metrics[name] = {"full_test": performance(test.daily, protocol, reference),
                         "frozen_holdout": performance(test.daily[test.daily.holdout], protocol, reference)}
    stage("benchmark_and_econometric_evaluation")
    benchmarks, warnings = {}, []
    expected = {"BIST_100", "BIST_PARTICIPATION_100"}
    benchmark_frame = dataset.get("benchmarks.csv")
    for name in expected:
        series = benchmark_frame[benchmark_frame.benchmark == name] if not benchmark_frame.empty else pd.DataFrame()
        if series.empty:
            warnings.append(f"Missing external benchmark: {name}")
            continue
        dates = tests["adaptive_ml"].daily.date
        levels = series.set_index("date").level.reindex(dates)
        if levels.isna().any():
            warnings.append(f"Incomplete external benchmark: {name}; no filling or fabricated comparison")
            continue
        benchmark_returns = levels.pct_change(fill_method=None).fillna(0)
        b = tests["adaptive_ml"].daily[["date", "holdout", "elapsed_session"]].copy()
        b["net_return"] = benchmark_returns.to_numpy()
        b["nav"] = protocol.initial_capital * (1 + b.net_return).cumprod()
        b["index_level"] = b.nav / protocol.initial_capital * 100
        b["cost_try"], b["traded_notional_try"], b["exposure"] = 0.0, 0.0, 1.0
        kind = series.kind.iloc[0]
        benchmarks[name] = b
        metrics[name] = {"kind": kind, "full_test": performance(b, protocol, reference),
                         "frozen_holdout": performance(b[b.holdout], protocol, reference)}
        if kind != "total_return":
            warnings.append(f"{name} is PRICE-only; not a like-for-like total-return benchmark")
    if factors.empty:
        warnings.append("No local-market factor data: FF3/FF5 cannot be reported")
    if dataset.get("cpi.csv").empty:
        warnings.append("Nominal TRY analysis only: no inflation-adjusted preservation claim")
    real_metrics = None
    cpi = dataset.get("cpi.csv")
    if not cpi.empty:
        d = tests["adaptive_ml"].daily[["date", "nav"]].sort_values("date")
        inflation = pd.merge_asof(d, cpi.sort_values("date"), on="date", direction="backward")
        if inflation.cpi.notna().all():
            real_nav = inflation.nav / (inflation.cpi / inflation.cpi.iloc[0])
            real_metrics = {"total_real_return": float(real_nav.iloc[-1] / protocol.initial_capital - 1),
                            "convention": "Latest period CPI at each valuation date; ex-post evaluation only"}
        else:
            warnings.append("Incomplete CPI coverage; real-return result omitted")
    versions = {}
    for package in ("numpy", "pandas", "scikit-learn", "scipy", "streamlit", "yfinance"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    is_real = dataset.manifest["dataset_kind"] == "real"
    report = clean_json({
        "engine_version": __version__, "created_at": datetime.now(timezone.utc),
        "dataset_id": dataset.manifest["dataset_id"], "dataset_kind": dataset.manifest["dataset_kind"],
        "audit_status": dataset.manifest["audit_status"], "provenance": dataset.manifest,
        "input_sha256": dataset.hashes, "dependency_versions": versions,
        "protocol": protocol.to_dict(), "actual_test_start": start,
        "actual_test_end": scores.date.max(), "metrics": metrics,
        "forecast_validation": forecast_metrics(scores), "real_return": real_metrics,
        "factor_models": factor_models(tests["adaptive_ml"].daily, factors),
        "panel_model": panel_model(scores), "warnings": warnings,
        "research_claim_status": "EMPIRICAL_RESULTS_REQUIRE_ACADEMIC_REVIEW" if is_real else "SOFTWARE_TEST_ONLY_NOT_EMPIRICAL_EVIDENCE",
        "source_review_note": "Input reviewed status is declared by the supplier, not authenticated by this software",
        "assumptions": ["Daily signals; next observed session CLOSE execution; long-only",
                        "Total-return exposures assume reinvestment; cash return is explicitly configured",
                        "Costs are protocol assumptions, not measured historical spreads",
                        "RF score measures a specified forward-loss event, not religious status or guaranteed safety",
                        "Final holdout model is frozen; no hypothesis is automatically confirmed",
                        "Price conventions and point-in-time source records require independent data review"],
    })
    return {"report": report, "eligibility": eligibility, "features": features,
            "scores": scores, "model_audit": audits, "backtests": tests, "benchmarks": benchmarks}


def result_files(result):
    files = {"report.json": json.dumps(result["report"], ensure_ascii=False, indent=2, allow_nan=False).encode()}
    for name in ("eligibility", "features", "scores", "model_audit"):
        files[name + ".csv"] = result[name].to_csv(index=False).encode()
    for name, test in result["backtests"].items():
        for kind in ("daily", "positions", "trades"):
            files[f"{name}_{kind}.csv"] = getattr(test, kind).to_csv(index=False).encode()
    for name, frame in result["benchmarks"].items():
        files[name + ".csv"] = frame.to_csv(index=False).encode()
    from hashlib import sha256
    sums = "".join(f"{sha256(raw).hexdigest()}  {name}\n" for name, raw in sorted(files.items()))
    files["SHA256SUMS.txt"] = sums.encode()
    return files


def result_zip(result):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, raw in result_files(result).items():
            archive.writestr(name, raw)
    return output.getvalue()


def write_results(result, directory):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    for name, raw in result_files(result).items():
        (path / name).write_bytes(raw)
    (path / "experiment.zip").write_bytes(result_zip(result))
