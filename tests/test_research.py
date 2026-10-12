from dataclasses import replace
from io import BytesIO
import json
import unittest
from zipfile import ZipFile
import numpy as np
import pandas as pd
from ieai.backtest import execute_rebalance, performance, simulate
from ieai.data import DataError, Dataset
from ieai.features import FEATURES, feature_panel
from ieai.learning import fit_at, forecast_metrics, walk_forward
from ieai.portfolio import capped_weights
from ieai.screening import screen_at, screening_panel
from ieai.experiment import run_experiment, result_zip
from tests.fixtures import fixture_dataset, fixture_files, fixture_protocol


class Contracts(unittest.TestCase):
    def test_missing_eligibility_is_blocked(self):
        files = fixture_files(); del files["eligibility.csv"]
        with self.assertRaises(DataError): Dataset.from_bytes(files)

    def test_duplicate_quote_is_blocked(self):
        files = fixture_files()
        frame = pd.read_csv(BytesIO(files["prices.csv"]))
        files["prices.csv"] = pd.concat([frame, frame.iloc[:1]]).to_csv(index=False).encode()
        with self.assertRaisesRegex(DataError, "duplicate"): Dataset.from_bytes(files)

    def test_future_quotes_are_blocked(self):
        files = fixture_files()
        frame = pd.read_csv(BytesIO(files["prices.csv"]))
        frame.loc[0, "date"] = (pd.Timestamp.now() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
        files["prices.csv"] = frame.to_csv(index=False).encode()
        with self.assertRaisesRegex(DataError, "Future"): Dataset.from_bytes(files)

    def test_false_boolean_is_not_truthy_string(self):
        files = fixture_files()
        frame = pd.read_csv(BytesIO(files["eligibility.csv"]))
        frame["eligible"] = "False"
        files["eligibility.csv"] = frame.to_csv(index=False).encode()
        self.assertFalse(Dataset.from_bytes(files).get("eligibility.csv").eligible.any())

    def test_hash_mismatch_is_blocked(self):
        files = fixture_files(); manifest = json.loads(files["manifest.json"])
        manifest["sha256"] = {"prices.csv": "0"*64}
        files["manifest.json"] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(DataError, "Hash"): Dataset.from_bytes(files)

    def test_archive_path_is_blocked(self):
        buf = BytesIO()
        with ZipFile(buf, "w") as z: z.writestr("../prices.csv", "bad")
        with self.assertRaisesRegex(DataError, "paths"): Dataset.from_zip(buf.getvalue())

    def test_malformed_zip_is_friendly_error(self):
        with self.assertRaisesRegex(DataError, "ZIP"): Dataset.from_zip(b"not a zip")

    def test_synthetic_cannot_be_run_as_research(self):
        with self.assertRaisesRegex(DataError, "Synthetic"):
            run_experiment(fixture_dataset(), fixture_protocol())

    def test_invalid_date_order_is_blocked(self):
        with self.assertRaises(ValueError): fixture_protocol(holdout_start="2022-01-01")


class TemporalScreening(unittest.TestCase):
    def setUp(self):
        self.data = fixture_dataset(2); self.protocol = fixture_protocol()

    def test_financials_not_used_before_publication(self):
        f = self.data.frames["financials.csv"]
        f.loc[(f.symbol == "TEST00") & (f.available_at == pd.Timestamp("2022-01-01")), "interest_bearing_debt"] = 9000000
        before = screen_at(self.data, ["TEST00"], "2021-12-31", self.protocol).iloc[0]
        after = screen_at(self.data, ["TEST00"], "2022-01-03", self.protocol).iloc[0]
        self.assertTrue(before.eligible); self.assertFalse(after.eligible)
        self.assertIn("debt_above", after.reason)

    def test_eligibility_effective_date_is_not_enough(self):
        self.data.frames["eligibility.csv"].loc[0, "available_at"] = pd.Timestamp("2022-02-01")
        row = screen_at(self.data, ["TEST00"], "2022-01-03", self.protocol).iloc[0]
        self.assertEqual(row.status, "unknown")

    def test_expired_attestation_does_not_persist(self):
        self.data.frames["eligibility.csv"].loc[0, "effective_to"] = pd.Timestamp("2021-12-31")
        row = screen_at(self.data, ["TEST00"], "2022-01-03", self.protocol).iloc[0]
        self.assertFalse(row.eligible)

    def test_missing_financials_are_not_zero_debt(self):
        self.data.frames["financials.csv"] = self.data.get("financials.csv")[lambda x: x.symbol != "TEST00"]
        row = screen_at(self.data, ["TEST00"], "2022-01-03", self.protocol).iloc[0]
        self.assertEqual(row.reason, "missing_financials")

    def test_market_cap_ratio_does_not_change_religious_gate(self):
        prices = self.data.frames["prices.csv"]
        prices.loc[(prices.symbol == "TEST00") & (prices.date == pd.Timestamp("2022-01-03")), "close"] = .01
        row = screen_at(self.data, ["TEST00"], "2022-01-03", self.protocol).iloc[0]
        self.assertTrue(row.eligible); self.assertGreater(row.debt_market_cap, 1)

    def test_vectorized_screen_preserves_publication_boundary(self):
        self.data.frames["financials.csv"].loc[2, "interest_bearing_debt"] = 9000000
        panel = screening_panel(self.data, self.protocol)
        for date in ("2021-12-31", "2022-01-03", "2023-01-03"):
            direct = screen_at(self.data, ["TEST00", "TEST01"], date, self.protocol).set_index("symbol")
            bulk = panel[panel.date == pd.Timestamp(date)].set_index("symbol")
            self.assertEqual(direct.eligible.to_dict(), bulk.eligible.to_dict())
            self.assertEqual(direct.reason.to_dict(), bulk.reason.to_dict())


class FeatureCausality(unittest.TestCase):
    def test_future_price_changes_do_not_change_past_features(self):
        data = fixture_dataset(2); cfg = fixture_protocol()
        before = feature_panel(data, screening_panel(data, cfg), cfg)
        cutoff = pd.Timestamp("2022-06-01")
        data.frames["prices.csv"].loc[lambda x: x.date > cutoff, "total_return_close"] *= 7
        after = feature_panel(data, screening_panel(data, cfg), cfg)
        pd.testing.assert_frame_equal(before.loc[before.date <= cutoff, FEATURES], after.loc[after.date <= cutoff, FEATURES])

    def test_no_liquidity_is_not_safe_zero(self):
        data = fixture_dataset(2); cfg = fixture_protocol()
        data.frames["prices.csv"].loc[lambda x: x.symbol == "TEST00", "value_traded_try"] = 0
        frame = feature_panel(data, screening_panel(data, cfg), cfg)
        self.assertTrue(frame.loc[frame.symbol == "TEST00", "amihud"].isna().all())

    def test_unmatured_targets_are_unknown_not_non_events(self):
        data = fixture_dataset(2); cfg = fixture_protocol()
        frame = feature_panel(data, screening_panel(data, cfg), cfg)
        for _, rows in frame.groupby("symbol"):
            self.assertTrue(rows.tail(cfg.horizon).target_event.isna().all())

    def test_actual_known_loss_becomes_event(self):
        data = fixture_dataset(2); cfg = fixture_protocol(horizon=5)
        prices = data.frames["prices.csv"]
        dates = sorted(prices.date.unique())
        symbol = prices.symbol == "TEST00"
        prices.loc[symbol, "total_return_close"] = 100.0
        prices.loc[symbol & (prices.date == dates[100]), "total_return_close"] = 80.0
        frame = feature_panel(data, screening_panel(data, cfg), cfg)
        row = frame[(frame.symbol == "TEST00") & (frame.date == dates[99])].iloc[0]
        self.assertEqual(row.target_event, 1); self.assertAlmostEqual(row.forward_loss, .2)


class Execution(unittest.TestCase):
    def test_cost_accounting_is_self_financing(self):
        holdings = pd.Series({"A": 70000.0, "B": 10000.0})
        target = pd.Series({"A": .20, "B": .50, "C": .10})
        nav, new, cost, delta = execute_rebalance(100000, holdings, target, .0015)
        self.assertAlmostEqual(nav + cost, 100000, places=6)
        self.assertAlmostEqual(cost, delta.abs().sum()*.0015, places=6)
        self.assertGreaterEqual(nav-new.sum(), 0)

    def test_position_cap_retains_unallocatable_cash(self):
        w = capped_weights(pd.Series({"A": 9, "B": 1}), .9, .2)
        self.assertLessEqual(w.max(), .2); self.assertAlmostEqual(w.sum(), .4)

    def test_zero_scores_mean_cash(self):
        self.assertTrue(capped_weights(pd.Series({"A": 0}), 1, 1).empty)

    def test_next_close_execution_cannot_capture_prior_jump(self):
        dates = pd.bdate_range("2023-01-02", periods=4)
        scores = pd.DataFrame({"date": dates, "symbol": "A", "total_return_close": [100.,200.,200.,300.],
                              "eligible": True, "is_tradable": True, "market_cap": 100,
                              "score": 80, **{f: .01 for f in FEATURES}})
        cfg = fixture_protocol(commission_bps=0, slippage_bps=0, max_stock_weight=1,
                               exposure_policy="fully_invested", rebalance_sessions=2)
        test = simulate(scores, cfg, "adaptive_ml")
        self.assertAlmostEqual(test.daily.nav.iloc[1], cfg.initial_capital)
        self.assertAlmostEqual(test.daily.nav.iloc[-1], 1.5*cfg.initial_capital)
        self.assertTrue((test.trades.date > test.trades.signal_date).all())

    def test_missing_held_quote_stops_instead_of_zero_return(self):
        dates = pd.bdate_range("2023-01-02", periods=4)
        scores = pd.DataFrame({"date": dates, "symbol": "A", "total_return_close": [100.,100.,np.nan,110.],
                              "eligible": True, "is_tradable": True, "market_cap": 100,
                              "score": 80, **{f: .01 for f in FEATURES}})
        with self.assertRaisesRegex(DataError, "Missing valuation"):
            simulate(scores, fixture_protocol(max_stock_weight=1), "adaptive_ml")

    def test_holdout_drawdown_includes_starting_wealth(self):
        dates = pd.bdate_range("2023-01-02", periods=3)
        frame = pd.DataFrame({"date": dates, "net_return": [-.2,0.,.1], "cost_try": 0.,
                              "traded_notional_try": 0., "exposure": 1.})
        result = performance(frame, fixture_protocol())
        self.assertAlmostEqual(result["max_drawdown"], .2)

    def test_annualization_counts_actual_return_intervals(self):
        dates = pd.bdate_range("2023-01-02", periods=4)
        frame = pd.DataFrame({"date": dates, "net_return": [0.,.01,.01,.01],
                              "elapsed_session": [False,True,True,True],
                              "cost_try": 0., "traded_notional_try": 0., "exposure": 1.})
        full = performance(frame, fixture_protocol())
        sliced = performance(frame.iloc[1:], fixture_protocol())
        self.assertEqual(full["sessions"],3)
        self.assertAlmostEqual(full["cagr"],1.01**252-1,places=9)
        self.assertAlmostEqual(full["cagr"],sliced["cagr"],places=9)

    def test_sliced_period_retains_its_first_profitable_session(self):
        frame = pd.DataFrame({"date": pd.bdate_range("2023-07-03",periods=3),
                              "net_return": [.02,-.01,-.01], "elapsed_session": True,
                              "cost_try": 0., "traded_notional_try": 0., "exposure": 1.})
        result = performance(frame,fixture_protocol())
        self.assertAlmostEqual(result["positive_session_fraction"],1/3)


class FullResearchFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_experiment(fixture_dataset(), fixture_protocol(), allow_synthetic=True)

    def test_no_training_or_calibration_looks_forward(self):
        audit = self.result["model_audit"]
        good = audit[audit.status == "trained_and_calibrated"]
        self.assertGreater(len(good), 0)
        self.assertTrue((pd.to_datetime(good.training_label_end) < pd.to_datetime(good.calibration_start)).all())
        self.assertTrue((pd.to_datetime(good.calibration_label_end) < pd.to_datetime(good.decision_date)).all())

    def test_final_holdout_is_frozen(self):
        scores = self.result["scores"]
        self.assertEqual(scores.loc[scores.holdout & scores.score.notna(), "model_id"].nunique(), 1)
        trained = self.result["model_audit"][lambda x: x.status == "trained_and_calibrated"]
        self.assertLess(pd.to_datetime(trained.decision_date).max(), pd.Timestamp("2023-07-01"))

    def test_trades_have_real_signal_dates_and_costs(self):
        trades = self.result["backtests"]["adaptive_ml"].trades
        self.assertGreater(len(trades), 0)
        self.assertTrue((trades.date > trades.signal_date).all())
        self.assertTrue((trades.cost_try >= 0).all())

    def test_scores_are_defined_and_bounded(self):
        scores = self.result["scores"].dropna(subset=["score"])
        self.assertTrue(scores.score.between(0,100).all())
        np.testing.assert_allclose(scores.score, 100*(1-scores.event_probability))

    def test_test_export_never_claims_empirical_success(self):
        report = self.result["report"]
        self.assertEqual(report["research_claim_status"], "SOFTWARE_TEST_ONLY_NOT_EMPIRICAL_EVIDENCE")
        self.assertIn("input_sha256", report)
        self.assertEqual(report["factor_models"]["status"], "missing_factors")

    def test_exports_contain_auditable_ledger_and_hashes(self):
        raw = result_zip(self.result)
        with ZipFile(BytesIO(raw)) as z:
            self.assertIn("adaptive_ml_trades.csv", z.namelist())
            self.assertIn("SHA256SUMS.txt", z.namelist())
            report = json.loads(z.read("report.json"))
            self.assertEqual(report["dataset_kind"], "synthetic")

    def test_model_hash_is_deterministic(self):
        data = fixture_dataset(); cfg = fixture_protocol()
        panel = feature_panel(data, screening_panel(data,cfg),cfg)
        one = fit_at(panel, "2023-01-02", cfg)
        two = fit_at(panel, "2023-01-02", cfg)
        self.assertEqual(one.audit["model_id"], two.audit["model_id"])
        sample = panel[panel.date == pd.Timestamp("2023-01-02")]
        np.testing.assert_array_equal(one.predict(sample), two.predict(sample))


if __name__ == "__main__": unittest.main()
