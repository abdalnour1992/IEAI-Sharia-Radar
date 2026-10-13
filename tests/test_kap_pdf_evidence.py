"""Pure offline KAP evidence workbench tests (no live portal or credentials)."""
import tempfile
from pathlib import Path
import unittest
from hashlib import sha256
from ieai.kap_pdf_evidence import (
    EvidenceError, _contains_amount, _verify_file, validate_observations,
    reconciliation, build_report
)


class KapEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "status": "DOCUMENT_EXTRACTED_PENDING_REVIEW",
            "research_dataset_complete": False, "currency": "TRY",
            "raw_monetary_unit": "1000 TRY", "publication_timezone": "unverified",
            "publication_timestamp_as_listed": "2022-02-25 07:26:37",
            "consolidated": True,
            "source_url": "https://www.kap.org.tr/tr/Bildirim/1004314",
            "symbol": "SASA", "fiscal_period_end": "2021-12-31",
            "files_sha256": {"turkish_original": "a" * 64}
        }
        self.row = {
            "symbol": "SASA", "bundle_id": "KAP_1004314",
            "observation": "total_assets", "raw_value": "22194163",
            "raw_unit": "TRY_thousands", "scale_to_try": "1000",
            "period_end": "2021-12-31", "published_at_source": "2022-02-25 07:26:37",
            "primary_pdf_page": "Turkish report p.1",
            "translation_pdf_page": "English report p.1",
            "source_url": self.manifest["source_url"],
            "primary_pdf_sha256": "a" * 64,
            "review_status": "source_observed_not_certified"
        }

    def test_exact_large_integer_match(self):
        self.assertTrue(_contains_amount("Assets 22.194.163", 22194163))
        self.assertTrue(_contains_amount("Assets 22,194,163", 22194163))
        self.assertFalse(_contains_amount("Assets 122.194.163", 22194163))

    def test_valid_observation_is_still_nonpromotable(self):
        result = validate_observations([self.row], self.manifest,
                                       ["22.194.163"], ["22,194,163"])
        self.assertEqual(result["total_assets"], 22194163)

    def test_fail_closed_on_review_or_unit_or_source_mismatch(self):
        for key, val in [
            ("review_status", "reviewed"), ("scale_to_try", "1"),
            ("raw_value", ""), ("period_end", "2020-12-31"),
            ("source_url", "https://attacker.example/")
        ]:
            with self.subTest(key=key):
                with self.assertRaises(EvidenceError):
                    validate_observations(
                        [dict(self.row, **{key: val})], self.manifest,
                        ["22.194.163"], ["22.194.163"])

    def test_page_mismatch_is_error(self):
        with self.assertRaisesRegex(EvidenceError, "missing"):
            validate_observations([self.row], self.manifest,
                                  ["20.000.000"], ["22.194.163"])

    def test_original_byte_hash_and_path_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "report.pdf"
            source.write_bytes(b"test-input")
            digest = sha256(source.read_bytes()).hexdigest()
            self.assertEqual(_verify_file(folder, "report.pdf", digest), source)
            with self.assertRaises(EvidenceError):
                _verify_file(folder, "report.pdf", "f" * 64)
            with self.assertRaises(EvidenceError):
                _verify_file(folder, "../report.pdf", digest)

    def test_financial_reconciliations_and_no_certificate(self):
        vals = {
            "total_assets": 22194163,
            "total_financial_borrowings": 11998872,
            "short_term_financial_borrowings": 3206990,
            "long_term_financial_borrowings": 8791882,
            "bank_borrowings_including_accruals": 9004412,
            "convertible_bond_liability": 2822264,
            "lease_liabilities_total": 172196,
            "interest_expense_total": 445091,
            "bank_interest_expense": 388062,
            "convertible_bond_interest_expense": 57029,
            "revenue": 14644953,
            "interest_income": 20567,
            "interest_support_income": 32077,
        }
        report = build_report(self.manifest, vals)
        self.assertEqual(set(report["reconciliations"].values()), {"PASS"})
        self.assertFalse(report["approved_for_empirical_screening"])
        self.assertFalse(report["research_dataset_complete"])
        self.assertFalse(report["historical_XK100_membership_attested"])
        self.assertEqual(report["classification_decision"], "UNKNOWN")
        self.assertAlmostEqual(report["descriptive_ratios_only"]["debt_assets_including_leases_pct"], 54.0632, places=3)
        vals["total_financial_borrowings"] += 1
        self.assertEqual(reconciliation(vals)["borrowings_by_maturity"], "FAIL")


if __name__ == "__main__":
    unittest.main()
