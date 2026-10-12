"""Research-data integrity regressions; all fixtures below are SOFTWARE TESTS."""
from io import BytesIO
import json
from pathlib import Path
import struct
import tempfile
import unittest
import numpy as np
import pandas as pd
from ieai.data import DataError, validate_frame
from ieai.intake import compile_membership, compile_facts, decision_availability, compile_intake
from ieai.official import approved_url, parse_index, unwrap_pdf, market_controls, change_candidates, participation_notices, cash_reference_checks
from ieai.econometrics import factor_models
from ieai.screening import screen_at, screening_panel
from ieai.coverage import audit_coverage
from tests.fixtures import fixture_dataset, fixture_protocol, fixture_files


SOURCE = {"source_url": "https://example.org/SYNTHETIC-source", "source_sha256": "a"*64,
          "evidence_locator": "SYNTHETIC software test row", "review_status": "reviewed"}


def events():
    return pd.DataFrame([
        {**SOURCE, "symbol": "TEST00", "event_kind": "snapshot", "available_at": "2021-10-02", "effective_from": "2021-10-01"},
        {**SOURCE, "symbol": "TEST01", "event_kind": "snapshot", "available_at": "2021-10-02", "effective_from": "2021-10-01"},
        {**SOURCE, "symbol": "TEST02", "event_kind": "reserve", "available_at": "2021-10-02", "effective_from": "2021-10-01"},
        {**SOURCE, "symbol": "TEST00", "event_kind": "remove", "available_at": "2022-01-05", "effective_from": "2022-01-03"},
        {**SOURCE, "symbol": "TEST03", "event_kind": "add", "available_at": "2022-01-05", "effective_from": "2022-01-03"},
    ])


def coverage():
    return {"continuity_review_status": "reviewed", "complete_through": "2023-12-31", "initial_member_count": 2}


def facts():
    fields = {"total_assets": "10000", "interest_bearing_debt": "2000", "interest_bearing_assets": "100",
              "total_revenue": "1000", "noncompliant_revenue": "0", "activity_pass": "true", "other_criteria_pass": "true"}
    return pd.DataFrame([{**SOURCE, "bundle_id": "SYNTHETIC-annual", "symbol": "TEST00", "field": field,
                          "value": value, "scale": "1000", "currency": "TRY", "period_end": "2021-12-31",
                          "published_at": "2022-03-10T21:30:00+03:00", "effective_from": "2021-12-31",
                          "mapping_note": "SYNTHETIC tested account mapping", "unit_basis": "SYNTHETIC-compatible"}
                         for field, value in fields.items()])


class OfficialSources(unittest.TestCase):
    def payload(self):
        return {"status": "success", "data": [{"indexName": "XK100", "clval": 1406.78, "hisTs": "2021-10-01"}]}

    def test_returned_index_identity_must_match(self):
        with self.assertRaisesRegex(DataError, "identity"):
            parse_index(self.payload(), "XKTUM")

    def test_duplicate_closes_are_ambiguous(self):
        p = self.payload(); p["data"] *= 2
        with self.assertRaises(DataError): parse_index(p, "XK100")

    def test_nonpositive_or_nonfinite_index_level_is_not_a_quote(self):
        for value in [0, -1, np.nan, np.inf]:
            p = self.payload(); p["data"][0]["clval"] = value
            with self.assertRaises(DataError): parse_index(p, "XK100")

    def test_failed_provider_response_does_not_become_empty_success(self):
        with self.assertRaises(DataError): parse_index({"status": "error", "data": []}, "XK100")

    def test_urls_do_not_allow_credentials_redirect_hosts_or_http(self):
        for value in ["http://www.kap.org.tr/tr", "https://kap.org.tr.attacker.example/tr", "https://user:secret@kap.org.tr/tr", "file:///tmp/source"]:
            with self.assertRaises(DataError): approved_url(value)

    def test_recognized_kap_byte_array_is_decoded_without_deserialization(self):
        raw = b"%PDF-1.7\nSOFTWARE TEST ONLY"
        prefix = bytes.fromhex("aced0005757200025b42acf317f8060854e00200007870")
        self.assertEqual(unwrap_pdf(prefix+struct.pack(">I",len(raw))+raw),raw)
        with self.assertRaises(DataError): unwrap_pdf(prefix+struct.pack(">I",len(raw)+1)+raw)
        with self.assertRaises(DataError): unwrap_pdf(b"html page %PDF-1.7 not an envelope")

    def proxy_series(self):
        dates = pd.to_datetime(["2021-09-28","2021-09-29","2021-09-30","2021-10-01","2021-10-04"])
        return pd.DataFrame({"date": dates, "level": [100.,101.,102.,103.,104.]}), pd.DataFrame({"date": dates, "level": [100.,100.05,100.10,100.25,100.30]})

    def test_cash_accrual_is_aligned_to_realized_interval_not_friday_quote_date(self):
        market, cash = self.proxy_series()
        c = market_controls(market,cash,"2021-10-01","2021-10-04")
        self.assertAlmostEqual(c.rf.iloc[0],100.10/100.05-1)
        self.assertAlmostEqual(c.rf.iloc[1],100.25/100.10-1)
        self.assertAlmostEqual(c.market_excess.iloc[1],104/103-1-c.rf.iloc[1])

    def test_missing_cash_proxy_is_not_forward_filled(self):
        market, cash = self.proxy_series(); cash = cash[cash.date != pd.Timestamp("2021-09-30")]
        with self.assertRaisesRegex(DataError,"coverage"):
            market_controls(market,cash,"2021-10-01","2021-10-04")

    def test_cash_calendar_is_cross_checked_against_independent_official_calculator(self):
        market, cash = self.proxy_series()
        class Calculator:
            def fetch(self, source_id, url):
                r = 100.10/100.05-1 if "20211001" in source_id else 100.25/100.10-1
                return json.dumps({"status":"success","data":{"periodReturn":r*100,"periodDayCount":1}}).encode()
        self.assertEqual(len(cash_reference_checks(market,cash,Calculator())),2)
        class WrongCalendar:
            def fetch(self, source_id, url):
                return b'{"status":"success","data":{"periodReturn":90,"periodDayCount":1}}'
        with self.assertRaisesRegex(DataError,"convention"):
            cash_reference_checks(market,cash,WrongCalendar())

    def change_source(self):
        return {"source_id":"SYNTHETIC","period_start":"2023-05-01","period_end":"2023-09-30",
                "published_date":"2023-04-26","announcement_url":"https://example.org/SYNTHETIC"}

    def test_shifted_pdf_headers_do_not_promote_removed_or_reserve_stocks(self):
        header = "STOCKS TO BE INCLUDED".ljust(50)+"STOCKS TO BE EXCLUDED".ljust(40)+"SUBSTITUTE STOCKS"
        data = "1  TESTA".ljust(42)+"1  TESTB".ljust(35)+"1  TESTC"
        text = "MAY 1, 2023-SEPTEMBER 30, 2023\nBIST PARTICIPATION 100 INDEX\n"+header+"\n"+data+"\nBIST PARTICIPATION 50 INDEX"
        out = change_candidates(text,self.change_source(),pd.bdate_range("2023-05-02",periods=3))
        self.assertEqual(out.set_index("event_kind").symbol.to_dict(),{"add":"TESTA.IS","remove":"TESTB.IS","reserve":"TESTC.IS"})
        self.assertEqual(out.effective_from.iloc[0],"2023-05-02")
        self.assertTrue(out.review_status.eq("unreviewed").all())

    def test_mutable_attachment_with_wrong_historical_period_is_quarantined(self):
        with self.assertRaisesRegex(DataError,"period mismatch"):
            change_candidates("MAY 1, 2025-SEPTEMBER 30, 2025",self.change_source(),pd.bdate_range("2023-05-02",periods=3))

    def test_announcement_inventory_retains_other_index_scope_for_review(self):
        html = '<table><tr><td>12.01.2022</td><td><a href="/duyuru/12914/test">Example</a></td><td>BIST Pay Endeksleri|Katılım</td></tr></table>'
        out = participation_notices(html,"2021-10-01","2025-12-31")
        self.assertEqual(len(out),1); self.assertEqual(out.published_date.iloc[0],"2022-01-12")
        self.assertEqual(out.review_status.iloc[0],"unreviewed")


class ReviewedIntake(unittest.TestCase):
    def test_changes_cannot_replace_missing_initial_snapshot(self):
        f = events(); f = f[f.event_kind != "snapshot"]
        with self.assertRaisesRegex(DataError,"snapshot"):
            compile_membership(f,coverage(),"2021-10-01","2023-12-31")

    def test_reserve_is_not_member_and_late_removal_does_not_rewrite_past_knowledge(self):
        out = compile_membership(events(),coverage(),"2021-10-01","2023-12-31")
        self.assertNotIn("TEST02",set(out.symbol))
        first = out[(out.symbol == "TEST00") & out.eligible].iloc[0]
        self.assertEqual(first.effective_to,pd.Timestamp("2022-01-04"))

    def test_missing_exceptional_change_review_blocks_continuity_claim(self):
        c = coverage(); c["continuity_review_status"] = "unreviewed"
        with self.assertRaises(DataError): compile_membership(events(),c,"2021-10-01","2023-12-31")

    def test_unreviewed_machine_candidates_are_not_research_eligibility(self):
        e = events(); e.review_status = "unreviewed"
        with self.assertRaisesRegex(DataError,"Unreviewed"):
            compile_membership(e,coverage(),"2021-10-01","2023-12-31")

    def test_initial_count_or_inconsistent_change_chain_is_rejected(self):
        c = coverage(); c["initial_member_count"] = 3
        with self.assertRaises(DataError): compile_membership(events(),c,"2021-10-01","2023-12-31")
        e = events(); e.loc[e.event_kind == "remove","symbol"] = "TEST99"
        with self.assertRaisesRegex(DataError,"chain"):
            compile_membership(e,coverage(),"2021-10-01","2023-12-31")

    def test_istanbul_publication_timestamp_never_uses_previous_utc_day(self):
        self.assertEqual(decision_availability("2022-03-10T23:00:00Z"),pd.Timestamp("2022-03-12"))

    def test_units_are_scaled_and_financial_publication_controls_availability(self):
        frames,gaps = compile_facts(facts(),"SYNTHETIC-compatible")
        f = frames["financials.csv"].iloc[0]
        self.assertEqual(f.total_assets,10000000)
        self.assertEqual(f.available_at,pd.Timestamp("2022-03-11")); self.assertEqual(gaps,[])

    def test_missing_noncompliant_revenue_is_not_assumed_zero(self):
        f = facts(); f = f[f.field != "noncompliant_revenue"]
        frames,gaps = compile_facts(f,"SYNTHETIC-compatible")
        self.assertNotIn("financials.csv",frames)
        self.assertEqual(gaps[0]["missing_fields"],["noncompliant_revenue"])

    def test_total_liabilities_are_not_mapped_as_interest_debt(self):
        f = facts(); f.loc[f.field == "interest_bearing_debt","field"] = "total_liabilities"
        with self.assertRaisesRegex(DataError,"Unmapped"):
            compile_facts(f,"SYNTHETIC-compatible")

    def test_share_basis_and_effective_date_are_explicit(self):
        f = facts().iloc[:1].copy(); f["field"] = "shares_outstanding"; f["value"] = "1000000"; f["scale"] = "1"
        f["effective_from"] = "2022-04-01"
        frames,_ = compile_facts(f,"SYNTHETIC-compatible")
        self.assertEqual(frames["shares.csv"].effective_from.iloc[0],pd.Timestamp("2022-04-01"))
        with self.assertRaisesRegex(DataError,"basis"):
            compile_facts(f,"SYNTHETIC-other-basis")

    def test_empty_template_is_not_an_approved_data_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/"intake_review.json").write_text('{"source_review_status":"unreviewed"}')
            with self.assertRaises(DataError): compile_intake(root,root/"output")

    def test_synthetic_fixture_does_not_pass_empirical_coverage_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,raw in fixture_files().items(): (root/name).write_bytes(raw)
            out = audit_coverage(root,fixture_protocol())
            self.assertFalse(out["coverage_complete_for_declared_scope"])
            self.assertIn("kind",[x["component"] for x in out["issues"]])


class PointInTimeCapital(unittest.TestCase):
    def test_announced_future_capital_does_not_apply_before_effective_date(self):
        data = fixture_dataset(2); p = fixture_protocol()
        old = data.frames["shares.csv"].iloc[0].copy()
        new = old.copy(); new.available_at = pd.Timestamp("2022-01-03"); new.effective_from = pd.Timestamp("2022-02-01"); new.shares_outstanding = 2000000
        data.frames["shares.csv"] = pd.concat([data.frames["shares.csv"],pd.DataFrame([new])],ignore_index=True)
        panel = screening_panel(data,p)
        for date,count in [("2022-01-04",1000000),("2022-02-01",2000000)]:
            direct=screen_at(data,["TEST00"],date,p).iloc[0]
            bulk=panel[(panel.symbol == "TEST00") & (panel.date == pd.Timestamp(date))].iloc[0]
            self.assertEqual(direct.shares_outstanding,count); self.assertEqual(bulk.shares_outstanding,count)

    def test_late_old_capital_report_cannot_erase_later_effective_capital(self):
        data = fixture_dataset(2); p = fixture_protocol()
        new = data.frames["shares.csv"].iloc[0].copy(); new.available_at = pd.Timestamp("2022-01-03"); new.effective_from = pd.Timestamp("2022-01-03"); new.shares_outstanding = 2000000
        old_revision = data.frames["shares.csv"].iloc[0].copy(); old_revision.available_at = pd.Timestamp("2022-03-01")
        data.frames["shares.csv"] = pd.concat([data.frames["shares.csv"],pd.DataFrame([new,old_revision])],ignore_index=True)
        direct=screen_at(data,["TEST00"],"2022-03-02",p).iloc[0]
        panel=screening_panel(data,p); bulk=panel[(panel.symbol == "TEST00") & (panel.date == pd.Timestamp("2022-03-02"))].iloc[0]
        self.assertEqual(direct.shares_outstanding,2000000); self.assertEqual(bulk.shares_outstanding,2000000)

    def test_old_period_financial_restatement_cannot_erase_newer_period(self):
        data=fixture_dataset(2);p=fixture_protocol()
        revision=data.frames["financials.csv"].iloc[0].copy(); revision.available_at=pd.Timestamp("2022-03-01"); revision.interest_bearing_debt=9000000
        data.frames["financials.csv"]=pd.concat([data.frames["financials.csv"],pd.DataFrame([revision])],ignore_index=True)
        direct=screen_at(data,["TEST00"],"2022-03-02",p).iloc[0]
        panel=screening_panel(data,p); bulk=panel[(panel.symbol == "TEST00") & (panel.date == pd.Timestamp("2022-03-02"))].iloc[0]
        self.assertTrue(direct.eligible);self.assertTrue(bulk.eligible)


class LocalFactorModels(unittest.TestCase):
    def factor_fixture(self):
        rng=np.random.default_rng(381); dates=pd.bdate_range("2023-01-02",periods=120)
        factors=pd.DataFrame({"date":dates,"market_excess":rng.normal(0,.01,120),"smb":rng.normal(0,.01,120),
                              "hml":rng.normal(0,.01,120),"rmw":rng.normal(0,.01,120),"cma":rng.normal(0,.01,120),"rf":.0001})
        daily=pd.DataFrame({"date":dates,"net_return":.001+.4*factors.market_excess+factors.rf,"elapsed_session":True})
        return daily,factors

    def test_market_controls_do_not_fabricate_smb_or_ff_alpha(self):
        daily,factors=self.factor_fixture()
        out=factor_models(daily,pd.DataFrame(),factors[["date","market_excess","rf"]])
        self.assertEqual(out["status"],"market_controls_only_ff3_ff5_unavailable")
        self.assertNotIn("ff3",out);self.assertEqual(out["capm"]["status"],"computed")

    def test_ff5_smb_is_not_silently_called_classic_ff3(self):
        daily,factors=self.factor_fixture();out=factor_models(daily,factors)
        self.assertEqual(out["ff5"]["status"],"computed")
        self.assertEqual(out["ff3"]["status"],"missing_model_specific_factors")

    def test_model_specific_ff3_and_ff5_are_both_computed(self):
        daily,factors=self.factor_fixture();ff3=factors[["date","market_excess","smb","hml","rf"]].copy();ff3.smb *= 2
        out=factor_models(daily,factors,ff3_factors=ff3)
        self.assertEqual(out["ff3"]["status"],"computed");self.assertEqual(out["ff5"]["status"],"computed")

    def test_currency_reference_mismatch_between_models_is_reported(self):
        daily,factors=self.factor_fixture();ff3=factors[["date","market_excess","smb","hml","rf"]].copy();ff3.rf *= 10
        self.assertEqual(factor_models(daily,factors,ff3_factors=ff3)["status"],"inconsistent_ff3_ff5_market_or_cash_reference")


if __name__ == "__main__": unittest.main()
