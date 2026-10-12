"""Eligibility and financial facts strictly as known at each decision date."""
import numpy as np
import pandas as pd


def latest_asof(frame, symbol, date):
    if frame.empty:
        return None
    rows = frame[(frame.symbol == symbol) & (frame.available_at <= date)]
    return None if rows.empty else rows.sort_values("available_at").iloc[-1]


def screen_at(dataset, symbols, date, protocol):
    date = pd.Timestamp(date)
    records = []
    for symbol in symbols:
        row = {"date": date, "symbol": symbol, "eligible": False,
               "status": "unknown", "reason": "missing_eligibility", "source_url": "",
               "shares_outstanding": np.nan, "market_cap": np.nan,
               "debt_assets": np.nan, "debt_market_cap": np.nan,
               "facts_available_at": pd.NaT}
        shares = latest_asof(dataset.get("shares.csv"), symbol, date)
        if shares is not None:
            row["shares_outstanding"] = float(shares.shares_outstanding)
        prices = dataset.get("prices.csv")
        observation = prices[(prices.symbol == symbol) & (prices.date == date)]
        if not observation.empty and shares is not None:
            row["market_cap"] = float(observation.iloc[0].close) * row["shares_outstanding"]
        eligible = dataset.get("eligibility.csv")
        candidates = eligible[(eligible.symbol == symbol) & (eligible.available_at <= date)
                              & (eligible.effective_from <= date) & (eligible.effective_to >= date)]
        if not candidates.empty:
            fact = candidates.sort_values(["available_at", "effective_from"]).iloc[-1]
            row.update(source_url=fact.source_url, facts_available_at=fact.available_at,
                       rule_set=fact.rule_set)
            if not bool(fact.eligible):
                row.update(status="ineligible", reason="attested_ineligible")
            elif protocol.screening_profile == "attested_membership":
                row.update(eligible=True, status="eligible", reason="attested_membership")
            else:
                financial = latest_asof(dataset.get("financials.csv"), symbol, date)
                if financial is None:
                    row["reason"] = "missing_financials"
                elif (date - financial.period_end).days > protocol.financial_max_age_days:
                    row["reason"] = "stale_financials"
                else:
                    debt = float(financial.interest_bearing_debt / financial.total_assets)
                    asset_ratio = float(financial.interest_bearing_assets / financial.total_assets)
                    income_ratio = float(financial.noncompliant_revenue / financial.total_revenue)
                    row.update(debt_assets=debt, interest_assets_ratio=asset_ratio,
                               noncompliant_income_ratio=income_ratio,
                               facts_available_at=max(fact.available_at, financial.available_at),
                               financial_source_url=financial.source_url)
                    if row["market_cap"] > 0:
                        row["debt_market_cap"] = financial.interest_bearing_debt / row["market_cap"]
                    tests = {"activity_failed": bool(financial.activity_pass),
                             "other_criteria_failed": bool(financial.other_criteria_pass),
                             "debt_above_research_30": debt <= 0.30}
                    failures = [key for key, passed in tests.items() if not passed]
                    row.update(eligible=not failures, status="ineligible" if failures else "eligible",
                               reason=";".join(failures) or "research_30_pass")
        records.append(row)
    return pd.DataFrame(records)


def screening_panel(dataset, protocol):
    """Vectorized per issuer to avoid scanning a whole market for every row."""
    prices = dataset.get("prices.csv")
    records = []
    for symbol, observations in prices.groupby("symbol", sort=True):
        left = observations[["date", "close"]].sort_values("date").copy()
        left["symbol"] = symbol
        left["eligible"] = False
        left["status"] = "unknown"
        left["reason"] = "missing_eligibility"
        left["source_url"] = ""
        left["rule_set"] = ""
        left["facts_available_at"] = pd.NaT
        attestations = dataset.get("eligibility.csv")
        attestations = attestations[attestations.symbol == symbol].sort_values(["available_at", "effective_from"])
        for fact in attestations.itertuples():
            mask = ((left.date >= fact.available_at) & (left.date >= fact.effective_from)
                    & (left.date <= fact.effective_to))
            left.loc[mask, "eligible"] = bool(fact.eligible)
            left.loc[mask, "status"] = "eligible" if fact.eligible else "ineligible"
            left.loc[mask, "reason"] = "attested_membership" if fact.eligible else "attested_ineligible"
            left.loc[mask, "source_url"] = fact.source_url
            left.loc[mask, "rule_set"] = fact.rule_set
            left.loc[mask, "facts_available_at"] = fact.available_at
        shares = dataset.get("shares.csv")
        shares = shares[shares.symbol == symbol][["available_at", "shares_outstanding"]].sort_values("available_at")
        left = pd.merge_asof(left, shares, left_on="date", right_on="available_at", direction="backward")
        left = left.rename(columns={"available_at": "shares_available_at"})
        left["market_cap"] = left.close * left.shares_outstanding
        left["debt_assets"] = np.nan
        left["debt_market_cap"] = np.nan
        if protocol.screening_profile == "research_30":
            financials = dataset.get("financials.csv")
            financials = financials[financials.symbol == symbol].drop(columns="symbol").sort_values("available_at")
            financials = financials.rename(columns={"source_url": "financial_source_url",
                                                    "available_at": "financial_available_at"})
            left = pd.merge_asof(left, financials, left_on="date", right_on="financial_available_at", direction="backward")
            original = left.eligible.copy()
            missing = left.financial_available_at.isna()
            stale = (left.date - left.period_end).dt.days > protocol.financial_max_age_days
            left.loc[original & missing, ["status", "reason"]] = ["unknown", "missing_financials"]
            left.loc[original & ~missing & stale, ["status", "reason"]] = ["unknown", "stale_financials"]
            left["eligible"] &= ~missing & ~stale
            left["debt_assets"] = left.interest_bearing_debt / left.total_assets
            left["debt_market_cap"] = left.interest_bearing_debt / left.market_cap
            left["interest_assets_ratio"] = left.interest_bearing_assets / left.total_assets
            left["noncompliant_income_ratio"] = left.noncompliant_revenue / left.total_revenue
            valid = left.eligible.copy()
            failures = pd.Series("", index=left.index)
            for reason, passed in [("activity_failed", left.activity_pass.fillna(False)),
                                   ("other_criteria_failed", left.other_criteria_pass.fillna(False)),
                                   ("debt_above_research_30", left.debt_assets <= 0.30)]:
                mask = valid & ~passed
                failures.loc[mask] += reason + ";"
            failed = failures != ""
            left.loc[valid & failed, "status"] = "ineligible"
            left.loc[valid & failed, "reason"] = failures[valid & failed].str.rstrip(";")
            left.loc[valid & ~failed, "reason"] = "research_30_pass"
            left["eligible"] &= ~failed
            left["facts_available_at"] = left[["facts_available_at", "financial_available_at"]].max(axis=1)
        records.append(left.drop(columns="close"))
    return pd.concat(records, ignore_index=True)
