"""Next-session CLOSE execution, self-financing costs, no leverage or silent marks."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .data import DataError
from .portfolio import target_weights

STRATEGIES = ["adaptive_ml", "static_eligible", "rules_risk", "exposure_control"]


@dataclass
class Backtest:
    daily: pd.DataFrame
    positions: pd.DataFrame
    trades: pd.DataFrame


def execute_rebalance(nav, holdings, target, cost_rate):
    """Solve NAV_after = NAV_before - c * sum(abs(new_position-old_position))."""
    assets = holdings.index.union(target.index)
    old = holdings.reindex(assets, fill_value=0.0)
    target = target.reindex(assets, fill_value=0.0)
    if (target < -1e-12).any() or target.sum() > 1 + 1e-12:
        raise DataError("Leverage/shorting prohibited")
    if not 0 <= cost_rate < 0.1:
        raise DataError("Invalid transaction cost rate")
    after = nav
    for _ in range(100):
        new = target * after
        updated = nav - cost_rate * float((new - old).abs().sum())
        if abs(updated - after) < max(1e-10, nav * 1e-12):
            after = updated
            break
        after = updated
    new = target * after
    delta = new - old
    cost = cost_rate * float(delta.abs().sum())
    return after, new[new.abs() > 1e-9], cost, delta


def simulate(scores, protocol, strategy):
    quotes = scores.pivot(index="date", columns="symbol", values="total_return_close").sort_index()
    tradability = scores.pivot(index="date", columns="symbol", values="is_tradable").reindex(quotes.index)
    sessions = quotes.index
    holdings = pd.Series(dtype=float)
    cash = protocol.initial_capital
    daily, trades, positions = [], [], []
    nav_previous = protocol.initial_capital
    cost_rate = (protocol.commission_bps + protocol.slippage_bps) / 10000
    last_rebalance = -protocol.rebalance_sessions
    for i, date in enumerate(sessions):
        if i > 0:
            returns = quotes.loc[date] / quotes.iloc[i - 1] - 1
            if not holdings.empty and not np.isfinite(returns.reindex(holdings.index)).all():
                raise DataError(f"Missing valuation for held asset on {date.date()}; resolve suspension/delisting explicitly")
            holdings = holdings * (1 + returns.reindex(holdings.index))
            cash *= 1 + protocol.cash_return_daily
        nav = float(holdings.sum() + cash)
        cost, gross_notional, requested_exposure = 0.0, 0.0, None
        signal_date = None
        if i > 0:
            signal_date = sessions[i - 1]
            signal = scores[scores.date == signal_date]
            allowed = set(signal.loc[signal.eligible, "symbol"])
            exclusion = any(symbol not in allowed for symbol in holdings.index)
            rebalance = i - last_rebalance >= protocol.rebalance_sessions or exclusion
            if rebalance:
                target, details = target_weights(signal, strategy, protocol)
                requested_exposure = details["requested_exposure"]
                # Do not assume an untradable held stock can be sold at its valuation.
                frozen = [s for s in holdings.index if not bool(tradability.loc[date, s])]
                candidate = target.reindex(holdings.index.union(target.index), fill_value=0.0)
                if frozen:
                    changes = candidate.loc[frozen] * nav - holdings.loc[frozen]
                    if changes.abs().max() > 1e-6:
                        raise DataError(f"Untradable holding {frozen} on {date.date()}; execution cannot be invented")
                # New orders that cannot execute are retained as cash, not silently filled.
                executable = tradability.loc[date].fillna(False).astype(bool)
                target = target.loc[target.index.intersection(executable[executable].index)]
                after, new_holdings, cost, changes = execute_rebalance(nav, holdings, target, cost_rate)
                gross_notional = float(changes.abs().sum())
                for symbol, notional in changes.items():
                    if abs(notional) > 1e-7:
                        trades.append({"date": date, "signal_date": signal_date, "strategy": strategy,
                                       "symbol": symbol, "side": "buy" if notional > 0 else "sell",
                                       "notional_try": abs(float(notional)),
                                       "cost_try": abs(float(notional)) * cost_rate})
                holdings, nav = new_holdings, after
                cash = nav - float(holdings.sum())
                last_rebalance = i
        for symbol, value in holdings.items():
            positions.append({"date": date, "strategy": strategy, "symbol": symbol,
                              "notional_try": float(value), "weight": float(value / nav)})
        net_return = nav / nav_previous - 1
        daily.append({"date": date, "strategy": strategy, "nav": nav,
                      "index_level": 100 * nav / protocol.initial_capital,
                      "net_return": net_return, "cash": cash, "exposure": float(holdings.sum() / nav),
                      "cost_try": cost, "traded_notional_try": gross_notional,
                      "requested_exposure": requested_exposure, "signal_date": signal_date,
                      "holdout": date >= pd.Timestamp(protocol.holdout_start)})
        nav_previous = nav
    return Backtest(pd.DataFrame(daily), pd.DataFrame(positions), pd.DataFrame(trades))


def performance(daily, protocol, rf=None):
    returns = daily.set_index("date").net_return
    if len(returns) < 2:
        return {"status": "insufficient_sessions"}
    hurdle = pd.Series(protocol.cash_return_daily, index=returns.index) if rf is None else rf.reindex(returns.index)
    if hurdle.isna().any():
        raise DataError("Missing risk-free/cash reference for performance period")
    excess = returns - hurdle
    wealth = (1 + returns).cumprod()
    peak = np.maximum.accumulate(np.r_[1.0, wealth.to_numpy()])[1:]
    deviation = float(excess.std(ddof=1))
    downside = float(np.sqrt(np.minimum(excess.to_numpy(), 0).__pow__(2).mean()))
    annual = protocol.annual_sessions
    return {"status": "computed", "sessions": len(returns),
            "total_return": float(wealth.iloc[-1] - 1),
            "cagr": float(wealth.iloc[-1] ** (annual / max(len(returns) - 1, 1)) - 1),
            "annual_volatility": deviation * np.sqrt(annual),
            "sharpe": float(excess.mean() / deviation * np.sqrt(annual)) if deviation > 0 else None,
            "sortino": float(excess.mean() / downside * np.sqrt(annual)) if downside > 0 else None,
            "max_drawdown": float((1 - wealth.to_numpy() / peak).max()),
            "positive_session_fraction": float((returns.iloc[1:] > 0).mean()),
            "total_cost_try": float(daily.cost_try.sum()),
            "traded_notional_try": float(daily.traded_notional_try.sum()),
            "mean_exposure": float(daily.exposure.mean()),
            "sharpe_reference": "supplied_daily_rf" if rf is not None else "declared_cash_hurdle_zero_by_default"}
