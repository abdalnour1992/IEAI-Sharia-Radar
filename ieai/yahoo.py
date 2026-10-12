"""Exploratory market snapshot only. Never manufacture historical eligibility."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import pandas as pd


def fetch_snapshot(symbols, start, end, directory):
    import yfinance as yf
    if not 1 <= len(symbols) <= 200 or any(not re.fullmatch(r"[A-Z0-9^.=-]{1,24}", s) for s in symbols):
        raise ValueError("Supply 1-200 valid explicit ticker symbols")
    start_date, end_date = pd.Timestamp(start), pd.Timestamp(end)
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    if start_date >= end_date or end_date > today:
        raise ValueError("Snapshot dates must be ordered and cannot include future sessions")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    prices, benchmarks, failures = [], [], []
    benchmark_symbols = {"XU100.IS": "BIST_100", "XK100.IS": "BIST_PARTICIPATION_100"}
    for symbol in list(dict.fromkeys([*symbols, *benchmark_symbols])):
        try:
            # End is exclusive at the provider, inclusive in our input contract.
            frame = yf.Ticker(symbol).history(start=start_date.strftime("%Y-%m-%d"),
                    end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"), interval="1d",
                    auto_adjust=False, actions=True, repair=False, raise_errors=True)
            if frame.empty or "Close" not in frame:
                raise ValueError("No historical closing observations")
            dates = pd.to_datetime(frame.index).tz_localize(None).normalize()
            valid = frame.Close.notna() & (frame.Close > 0)
            frame, dates = frame.loc[valid], dates[valid]
            if frame.empty:
                raise ValueError("No positive closing observations")
            if symbol in benchmark_symbols:
                benchmarks.append(pd.DataFrame({"date": dates, "benchmark": benchmark_symbols[symbol],
                    "level": frame.Close.to_numpy(), "kind": "price", "currency": "TRY"}))
            else:
                if "Adj Close" not in frame or frame["Adj Close"].isna().any():
                    raise ValueError("Missing adjusted-close series; no implicit substitute")
                prices.append(pd.DataFrame({"date": dates, "symbol": symbol,
                    "close": frame.Close.to_numpy(), "total_return_close": frame["Adj Close"].to_numpy(),
                    "volume": frame.Volume.to_numpy(),
                    "value_traded_try": (frame.Close * frame.Volume).to_numpy(),
                    "is_tradable": (frame.Volume > 0).to_numpy()}))
        except Exception as exc:
            failures.append({"symbol": symbol, "error": str(exc)[:1000]})
    files = {}
    if prices:
        files["prices.csv"] = pd.concat(prices, ignore_index=True).to_csv(index=False).encode()
    if benchmarks:
        files["benchmarks.csv"] = pd.concat(benchmarks, ignore_index=True).to_csv(index=False).encode()
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "dataset_id": "yahoo-exploratory-" + now, "dataset_kind": "real", "audit_status": "unreviewed",
        "currency": "TRY", "universe": "explicit_ticker_request_not_historical_index_membership",
        "price_convention": "Yahoo Close and Adj Close; corporate-action units require review against historical shares",
        "value_traded_convention": "ESTIMATE: daily close multiplied by share volume, not official cash turnover",
        "sources": [{"file": name, "provider": "Yahoo Finance via yfinance", "url": "https://finance.yahoo.com/",
                     "retrieved_at": now} for name in files],
        "sha256": {name: sha256(raw).hexdigest() for name, raw in files.items()},
        "retrieval_failures": failures,
        "missing_research_inputs": ["Historical participation membership with effective/available dates",
                                    "Historical shares outstanding", "Financial statements with publication dates",
                                    "Suitable Turkish-market factors", "CPI for real-value claims",
                                    "Reviewed corporate-action and total-return benchmark conventions"],
        "status": "MARKET_SNAPSHOT_ONLY_NOT_A_RESEARCH_DATASET",
    }
    for name, raw in files.items():
        (folder / name).write_bytes(raw)
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
