"""Backward-looking risk inputs, and separately stored forward event labels."""
import numpy as np
import pandas as pd

FEATURES = ["max_drawdown", "downside_volatility", "amihud", "abnormal_turnover"]


def _drawdown(values):
    peaks = np.maximum.accumulate(values)
    return float(np.max(1 - values / peaks))


def feature_panel(dataset, eligibility, protocol):
    prices = dataset.get("prices.csv")
    sessions = pd.DatetimeIndex(sorted(prices.date.unique()))
    output = []
    for symbol, frame in prices.groupby("symbol", sort=True):
        frame = frame.set_index("date").reindex(sessions)
        frame["symbol"] = symbol
        facts = eligibility[eligibility.symbol == symbol].set_index("date").reindex(sessions)
        returns = frame.total_return_close.pct_change(fill_method=None)
        downside = np.minimum(returns - protocol.downside_target_daily, 0) ** 2
        frame["downside_volatility"] = np.sqrt(downside.rolling(protocol.lookback, min_periods=protocol.lookback).mean())
        frame["max_drawdown"] = frame.total_return_close.rolling(protocol.lookback, min_periods=protocol.lookback).apply(_drawdown, raw=True)
        valid_value = frame.value_traded_try.where(frame.value_traded_try > 0)
        frame["amihud"] = (returns.abs() / valid_value).rolling(protocol.lookback, min_periods=protocol.lookback).mean()
        turnover = frame.volume / facts.shares_outstanding
        frame["abnormal_turnover"] = turnover - turnover.shift(1).rolling(protocol.lookback, min_periods=protocol.lookback).mean()
        frame["eligible"] = facts.eligible.fillna(False).astype(bool)
        frame["market_cap"] = facts.market_cap
        frame["eligibility_reason"] = facts.reason
        frame["target_event"] = np.nan
        frame["forward_loss"] = np.nan
        frame["label_end"] = pd.NaT
        wealth = frame.total_return_close.to_numpy()
        for i in range(len(frame) - protocol.horizon):
            future = wealth[i + 1:i + 1 + protocol.horizon]
            if np.isfinite(wealth[i]) and np.isfinite(future).all():
                # Loss relative to decision-date wealth, not future peak-to-trough MDD.
                loss = max(0.0, float(1 - future.min() / wealth[i]))
                frame.iloc[i, frame.columns.get_loc("forward_loss")] = loss
                frame.iloc[i, frame.columns.get_loc("target_event")] = float(loss >= protocol.loss_threshold)
                frame.iloc[i, frame.columns.get_loc("label_end")] = sessions[i + protocol.horizon]
        frame.index.name = "date"
        output.append(frame.reset_index())
    result = pd.concat(output, ignore_index=True)
    result["label_end"] = pd.to_datetime(result.label_end)
    # No imputation of absent quotes, shares, eligibility or zero-volume liquidity.
    return result.sort_values(["date", "symbol"]).reset_index(drop=True)
