"""HAC factor regressions and two-way fixed effects, with explicit diagnostics.

No automatic claim of causality or confirmed research hypotheses is made.
"""
import numpy as np
import pandas as pd
from scipy.stats import t as student_t


def hac_ols(y, x, names, lags=5):
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    n, k = x.shape
    if n < max(30, 5 * k) or np.linalg.matrix_rank(x) != k:
        return {"status": "insufficient_or_rank_deficient", "observations": n}
    inverse = np.linalg.inv(x.T @ x)
    beta = inverse @ x.T @ y
    residual = y - x @ beta
    xu = x * residual[:, None]
    meat = xu.T @ xu
    for lag in range(1, min(lags, n - 1) + 1):
        cross = xu[lag:].T @ xu[:-lag]
        meat += (1 - lag / (lags + 1)) * (cross + cross.T)
    covariance = inverse @ meat @ inverse
    variance = np.diag(covariance)
    if (variance < -1e-12).any():
        return {"status": "invalid_covariance", "observations": n}
    stderr = np.sqrt(np.maximum(variance, 0))
    statistic = np.divide(beta, stderr, out=np.full(k, np.nan), where=stderr > 0)
    pvalues = 2 * student_t.sf(np.abs(statistic), df=n - k)
    coefficients = [{"term": name, "estimate": float(b), "standard_error": float(se),
                     "p_value": float(p), "ci_low": float(b - student_t.ppf(.975, n-k) * se),
                     "ci_high": float(b + student_t.ppf(.975, n-k) * se)}
                    for name, b, se, p in zip(names, beta, stderr, pvalues)]
    return {"status": "computed", "observations": n, "hac_lags": lags,
            "covariance": covariance.tolist(), "coefficients": coefficients,
            "interpretation": "Association only; alpha is not a capital-safety guarantee"}


def factor_models(daily, factors):
    if factors.empty:
        return {"status": "missing_factors", "reason": "Supply TRY, same-frequency factors suitable for the Turkish market"}
    merged = daily[["date", "net_return"]].merge(factors, on="date", how="inner")
    if len(merged) != len(daily):
        return {"status": "incomplete_factor_coverage", "matched": len(merged), "required": len(daily)}
    y = merged.net_return - merged.rf
    output = {}
    for label, fields in [("ff3", ["market_excess", "smb", "hml"]),
                          ("ff5", ["market_excess", "smb", "hml", "rmw", "cma"])]:
        x = np.column_stack([np.ones(len(merged)), merged[fields].to_numpy()])
        output[label] = hac_ols(y, x, ["alpha", *fields])
    return output


def _within(values, entities, dates):
    result = pd.DataFrame(values)
    for _ in range(1000):
        previous = result.to_numpy().copy()
        result -= result.groupby(entities).transform("mean")
        result -= result.groupby(dates).transform("mean")
        if np.max(np.abs(result.to_numpy() - previous)) < 1e-10:
            return result.to_numpy()
    raise ValueError("Fixed-effect demeaning did not converge")


def _cluster_meat(xu, labels):
    grouped = pd.DataFrame(xu).groupby(labels).sum().to_numpy()
    return grouped.T @ grouped, len(grouped)


def panel_model(scores):
    columns = ["score", "max_drawdown", "downside_volatility", "amihud", "abnormal_turnover"]
    rows = scores.dropna(subset=["target_event", *columns]).copy().reset_index(drop=True)
    if rows.empty or rows.symbol.nunique() < 5 or rows.date.nunique() < 30:
        return {"status": "insufficient_panel", "observations": len(rows),
                "reason": "At least 5 issuer clusters and 30 dates required; small-cluster inference remains limited"}
    entities, dates = rows.symbol, rows.date
    z = np.column_stack([rows.target_event.to_numpy(), rows.score.to_numpy() / 100,
                         rows[columns[1:]].to_numpy()])
    transformed = _within(z, entities, dates)
    y, x = transformed[:, 0], transformed[:, 1:]
    scale = np.sqrt((x*x).mean(axis=0))
    if (scale <= 1e-15).any():
        return {"status": "constant_regressor_after_fixed_effects"}
    x_scaled = x / scale
    n, k = x.shape
    if np.linalg.matrix_rank(x_scaled) != k:
        return {"status": "rank_deficient_panel"}
    inverse = np.linalg.inv(x_scaled.T @ x_scaled)
    beta_scaled = inverse @ x_scaled.T @ y
    residual = y - x_scaled @ beta_scaled
    xu = x_scaled * residual[:, None]
    entity_meat, g1 = _cluster_meat(xu, entities)
    date_meat, g2 = _cluster_meat(xu, dates)
    joint = pd.Series(list(zip(entities, dates)))
    joint_meat, g12 = _cluster_meat(xu, joint)
    # Conservative df count for connected issuer/date effects; disclose small samples.
    full_k = k + g1 + g2 - 1
    if n <= full_k:
        return {"status": "insufficient_residual_degrees_of_freedom"}
    def correction(g):
        return g / (g - 1) * (n - 1) / (n - full_k)
    meat = correction(g1)*entity_meat + correction(g2)*date_meat - correction(g12)*joint_meat
    covariance_scaled = inverse @ meat @ inverse
    covariance = covariance_scaled / np.outer(scale, scale)
    variance = np.diag(covariance)
    if (variance < 0).any():
        return {"status": "nonpositive_two_way_cluster_covariance", "observations": n,
                "reason": "No p-values reported from an invalid finite-sample covariance"}
    beta = beta_scaled / scale
    stderr = np.sqrt(variance)
    df = min(g1, g2) - 1
    statistic = np.divide(beta, stderr, out=np.full(k, np.nan), where=stderr > 0)
    return {"status": "computed", "model": "two_way_FE_linear_probability",
            "observations": n, "issuer_clusters": g1, "date_clusters": g2,
            "coefficients": [{"term": name, "estimate": float(b), "standard_error": float(se),
                              "p_value": float(p)} for name, b, se, p in
                             zip(columns, beta, stderr, 2*student_t.sf(abs(statistic), df=df))],
            "interpretation": "Current score predicts a subsequently observed event; observational association, not causal proof"}
