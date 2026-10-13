"""Temporal KAP catalog tests: no membership or intraday availability fabricated."""
import csv
from datetime import date
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from ieai.kap_temporal_catalog import TemporalCatalogError, normalize, audit_catalogs, write_audit


def row(symbol, idx, published, period="2"):
    return {
        "filename": f"{symbol}_{idx}_2021_{period}.xls",
        "symbol_filename": symbol, "kap_disclosure_index": idx,
        "fiscal_year": "2021", "period_code": period,
        "issuer": symbol+" TEST A.S.",
        "publication_timestamp_as_listed": published,
        "source_sha256": "a"*64,
        "source_url": "https://www.kap.org.tr/tr/Bildirim/"+idx
    }


def write(path, rows):
    with path.open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class TemporalCatalogTests(unittest.TestCase):
    def test_pre_cutoff_only_and_no_index_membership_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"filing_catalog.csv"
            write(p,[row("SASA","955229","06.08.2021 07:47:00"),
                     row("A","966206","01.10.2021 18:46:11"),
                     row("B","995229","19.01.2022 20:55:57")])
            result=audit_catalogs([p],date(2021,10,1))
            self.assertEqual(result["summary"]["reports"],3)
            self.assertEqual(result["summary"]["availability_buckets"],{
                "PRE_CUTOFF_CANDIDATE":1,"SAME_DAY_EXCLUDED":1,"POST_CUTOFF_EXCLUDED":1})
            self.assertFalse(result["summary"]["historical_XK100_eligible"])
            self.assertFalse(result["rows"][0]["historical_index_member_verified"])
            write_audit(result,Path(d)/"new")
            self.assertTrue((Path(d)/"new"/"kap_asof_filing_catalog.csv").exists())
            with self.assertRaises(TemporalCatalogError):
                write_audit(result,Path(d)/"new")

    def test_old_and_new_catalog_columns(self):
        old = {
            "filename":"SASA_1004314_2021_4.xls","symbol_filename":"SASA",
            "kap_disclosure_index_filename":"1004314", "fiscal_year_filename":"2021",
            "period_code_filename":"4", "publication_timestamp_as_listed":"25.02.2022 07:26:37",
            "sha256_uncompressed":"a"*64,
        }
        a=normalize(old)
        self.assertEqual(a["period"],"4")
        self.assertEqual(a["published_day"],"2022-02-25")
        self.assertFalse(a["financial_mapping_reviewed"])

    def test_failure_for_tampered_identity_bad_hash_or_date(self):
        good=row("SASA","955229","06.08.2021 07:47:00")
        for changed in [
            {"filename":"SASA_XXX_2021_2.xls"},
            {"source_sha256":"short"},
            {"publication_timestamp_as_listed":"invalid"},
            {"source_url":"https://example.com"},
        ]:
            with self.subTest(changed=changed):
                with self.assertRaises(TemporalCatalogError):
                    normalize({**good,**changed})

    def test_duplicate_reports_rejected_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"first.csv"
            q=Path(d)/"second.csv"
            write(p,[row("SASA","955229","06.08.2021 07:47:00")])
            write(q,[row("SASA","955229","06.08.2021 07:47:00")])
            with self.assertRaises(TemporalCatalogError):
                audit_catalogs([p,q],date(2021,10,1))


if __name__=="__main__":
    unittest.main()
