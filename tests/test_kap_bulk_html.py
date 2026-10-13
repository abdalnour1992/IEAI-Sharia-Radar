"""No-network KAP FinancialTable.zip HTML-as-XLS regression tests."""
from pathlib import Path
import tempfile
import unittest
import zipfile
from ieai.kap_bulk_html import KapArchiveError, parse_document, inspect_archive


def fixture(unit="1.000 TL", fiscal="2021", report_type="FR"):
    return f"""<html><head></head><body>
<h1>SASA POLYESTER SANAYİ A.Ş.</h1><h1>Finansal Rapor</h1>
<div>Gönderim Tarihi:25.02.2022 07:26:37</div>
<div>Bildirim Tipi:{report_type}</div><div>Yıl:{fiscal}</div><div>Periyot:4</div>
<table><tr><td class="financial-header-title">Sunum Para Birimi</td><td>{unit}</td></tr>
<tr><td class="financial-header-title">Finansal Tablo Niteliği</td><td>Konsolide</td></tr></table>
<table class="financial-table tbl_general_role_210015"><tbody>
<tr class="general_role_210015-row-1 data-input-row">
<td class="taxonomy-field-title"><div>TOPLAM VARLIKLAR</div></td>
<td class="taxonomy-context-value col-order-class-4"><div>22.194.163</div></td>
<td class="taxonomy-context-value col-order-class-5"><div>10.790.195</div></td></tr>
<tr class="general_role_210015-row-2 data-input-row"><td class="taxonomy-field-title"><div>TOPLAM KAYNAKLAR</div></td><td class="taxonomy-context-value col-order-class-4"><div>22.194.163</div></td></tr>
<tr class="general_role_210015-row-3 data-input-row"><td class="taxonomy-field-title"><div>Kısa Vadeli Borçlanmalar</div></td><td class="taxonomy-context-value col-order-class-4"><div>1.768.787</div></td></tr>
</tbody></table>
<table class="financial-table tbl_general_role_310003"><tbody>
<tr class="general_role_310003-row-1 data-input-row"><td class="taxonomy-field-title"><div>Hasılat</div></td><td class="taxonomy-context-value col-order-class-4"><div>14.644.953</div></td></tr>
</tbody></table></body></html>""".encode("utf-8")


class TestKapBulkHTML(unittest.TestCase):
    name = "SASA_1004314_2021_4.xls"

    def test_source_metadata_numeric_and_no_approval(self):
        record, rows = parse_document(self.name, fixture())
        self.assertEqual(record["kap_disclosure_index"], "1004314")
        self.assertEqual(record["publication_timestamp_as_listed"], "25.02.2022 07:26:37")
        self.assertEqual(record["presentation_unit"], "1.000 TL")
        self.assertFalse(record["publication_timezone_verified"])
        fields = {x["account"]: x for x in rows}
        self.assertEqual(fields["total_assets"]["value_try_candidate"], 22194163000)
        self.assertEqual(fields["revenue"]["raw_current"], "14.644.953")
        self.assertEqual(fields["total_assets"]["raw_comparative"], "10.790.195")
        self.assertIn("UNREVIEWED", fields["total_assets"]["review_status"])

    def test_million_lira_scaled(self):
        _, rows = parse_document(self.name, fixture(unit="1.000.000 TL"))
        fields = {x["account"]: x for x in rows}
        self.assertEqual(fields["total_assets"]["value_try_candidate"], 22194163000000)

    def test_metadata_mismatch_and_unknown_unit_fail(self):
        for change in [dict(fiscal="2022"), dict(report_type="DUY"), dict(unit="UNKNOWN")]:
            with self.subTest(change=change):
                with self.assertRaises(KapArchiveError):
                    parse_document(self.name, fixture(**change))

    def test_archive_index_and_no_empirical_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archive = base/"FinancialTable.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(self.name, fixture())
            output = base/"out"
            result = inspect_archive(archive, output)
            self.assertEqual(result["filings"], 1)
            self.assertEqual(result["balance_sheet_identities_verified"], 1)
            self.assertEqual(result["balance_sheet_identities_failed"], 0)
            self.assertFalse(result["screening_approved"])
            self.assertFalse(result["research_dataset_complete"])
            self.assertTrue((output/"filing_catalog.csv").exists())
            with self.assertRaises(KapArchiveError):
                inspect_archive(archive, output)

    def test_zip_path_and_identity_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            archive=base/"FinancialTable.zip"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("../report.xls",fixture())
            with self.assertRaises(KapArchiveError):
                inspect_archive(archive,base/"out")
            bad=fixture().replace(b"22.194.163</div></td></tr>\n<tr class=\"general_role_210015-row-3",b"22.194.162</div></td></tr>\n<tr class=\"general_role_210015-row-3")
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr(self.name,bad)
            with self.assertRaisesRegex(KapArchiveError,"identities disagree"):
                inspect_archive(archive,base/"out")


if __name__ == "__main__":
    unittest.main()
