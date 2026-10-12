"""Long-only capped allocation; score and religious eligibility are independent."""
import numpy as np
import pandas as pd
from .features import FEATURES


def capped_weights(raw, exposure, cap):
    raw = pd.Series(raw, dtype=float)
    raw = raw[np.isfinite(raw) & (raw > 0)]
    weights = pd.Series(0.0, index=raw.index)
    remaining = min(float(exposure), float(cap) * len(raw))
    active = raw.index.tolist()
    while active and remaining > 1e-12:
        proposal = raw.loc[active] / raw.loc[active].sum() * remaining
        capped = proposal[proposal > cap + 1e-12].index.tolist()
        if not capped:
            weights.loc[active] = proposal
            break
        weights.loc[capped] = cap
        remaining -= cap * len(capped)
        active = [symbol for symbol in active if symbol not in capped]
    return weights


def target_weights(rows, strategy, protocol):
    rows = rows[rows.eligible & rows.is_tradable.fillna(False)
                & np.isfinite(rows[FEATURES]).all(axis=1)].set_index("symbol")
    if rows.empty:
        return pd.Series(dtype=float), {"requested_exposure": 0.0, "reason": "no_eligible_liquid_observations"}
    base = pd.Series(1.0, index=rows.index) if protocol.base_weight == "equal" else rows.market_cap
    if strategy == "rules_risk":
        # Transparent non-ML comparison using the same four contemporaneous inputs.
        risk = rows[FEATURES].rank(pct=True).mean(axis=1)
        score = (1 - risk).clip(lower=0) * 100
        exposure = float(score.mean() / 100) if protocol.exposure_policy == "mean_score" else 1.0
        raw = base * score
    elif strategy in {"adaptive_ml", "exposure_control"}:
        rows = rows[rows.score.notna()]
        base = base.loc[rows.index]
        if rows.empty:
            return pd.Series(dtype=float), {"requested_exposure": 0.0, "reason": "model_unavailable"}
        score = rows.score
        exposure = float(score.mean() / 100) if protocol.exposure_policy == "mean_score" else 1.0
        raw = base * score if strategy == "adaptive_ml" else base
    elif strategy == "static_eligible":
        raw, exposure = base, 1.0
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    result = capped_weights(raw, exposure, protocol.max_stock_weight)
    return result, {"requested_exposure": exposure, "actual_exposure": float(result.sum()),
                    "eligible_candidates": len(rows), "reason": "allocated"}
