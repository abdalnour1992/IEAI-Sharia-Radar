"""Deterministic software fixtures. Never real market or empirical research data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from ieai.config import Protocol
from ieai.data import Dataset


def fixture_files(issuers=8):
    rng = np.random.default_rng(91)
    dates = pd.bdate_range("2021-01-01", "2023-12-29")
    prices, shares, eligibility, financials = [], [], [], []
    for i in range(issuers):
        symbol = f"TEST{i:02d}"
        returns = rng.normal(.0001, .025 + .002*(i%3), len(dates))
        wealth = 100 * (1+returns).cumprod()
        volume = rng.integers(10000, 100000, len(dates))
        prices.append(pd.DataFrame({"date": dates, "symbol": symbol, "close": wealth,
            "total_return_close": wealth, "volume": volume, "value_traded_try": volume*wealth,
            "is_tradable": True}))
        shares.append({"symbol": symbol, "available_at": "2020-12-31", "effective_from": "2020-12-31", "shares_outstanding": 1000000,
                       "source_url": "https://example.org/SYNTHETIC-software-test"})
        eligibility.append({"symbol": symbol, "available_at": "2021-01-01", "effective_from": "2021-01-01",
            "effective_to": "2023-12-31", "eligible": True, "rule_set": "SYNTHETIC-test-only",
            "source_url": "https://example.org/SYNTHETIC-software-test"})
        for year in (2020, 2021, 2022, 2023):
            financials.append({"symbol": symbol, "available_at": f"{year+1}-01-01", "period_end": f"{year}-12-31",
                "total_assets": 10000000, "interest_bearing_debt": 2000000,
                "interest_bearing_assets": 100000, "total_revenue": 1000000, "noncompliant_revenue": 0,
                "activity_pass": True, "other_criteria_pass": True,
                "source_url": "https://example.org/SYNTHETIC-software-test"})
    frames = {"prices.csv": pd.concat(prices), "shares.csv": pd.DataFrame(shares),
              "eligibility.csv": pd.DataFrame(eligibility), "financials.csv": pd.DataFrame(financials)}
    manifest = {"dataset_id": "SYNTHETIC-unit-fixture-91", "dataset_kind": "synthetic", "audit_status": "unreviewed",
                "currency": "TRY", "universe": "SYNTHETIC-software-fixture-not-BIST",
                "price_convention": "SYNTHETIC-test-positive-total-return-series",
                "sources": [{"file": name, "provider": "SYNTHETIC test generator",
                             "url": "https://example.org/SYNTHETIC", "retrieved_at": "2026-10-12"} for name in frames]}
    files = {name: frame.to_csv(index=False).encode() for name, frame in frames.items()}
    files["manifest.json"] = json.dumps(manifest).encode()
    return files


def fixture_protocol(**changes):
    values = dict(study_start="2021-10-01", evaluation_start="2022-07-01",
                  holdout_start="2023-07-01", study_end="2023-12-29", trees=16,
                  min_samples_leaf=8, max_depth=4, max_stock_weight=.20,
                  minimum_training_rows=180, minimum_training_dates=100, calibration_dates=30,
                  refit_sessions=40)
    values.update(changes)
    return Protocol(**values)


def fixture_dataset(issuers=8):
    return Dataset.from_bytes(fixture_files(issuers))


def write_fixture(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    for name, raw in fixture_files().items():
        (path / name).write_bytes(raw)
    (path / "fixture_protocol.json").write_text(json.dumps(fixture_protocol().to_dict(), indent=2))


if __name__ == "__main__":
    import sys
    write_fixture(sys.argv[1])
