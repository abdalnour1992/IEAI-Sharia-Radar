"""Test KAP archive inventory entirely from synthetic offline ZIP fixtures."""
import tempfile
from pathlib import Path
import unittest
import zipfile
from ieai.kap_archive_inventory import build_inventory, InventoryError


class InventoryTests(unittest.TestCase):
    def test_inventory_preserves_hashes_and_blocks_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            archive = folder / "official-example.zip"
            with zipfile.ZipFile(archive, "w") as out:
                out.writestr("financials.csv", "SAMPLE,NOT_RESEARCH\n")
            extracted = folder / "extracted"
            extracted.mkdir()
            (extracted / "financials.csv").write_text("SAMPLE,NOT_RESEARCH\n")
            result = build_inventory(extracted, archive, 2021, "FY")
            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["export_year_selected"], 2021)
            self.assertFalse(result["research_dataset_complete"])
            self.assertFalse(result["approved_for_empirical_screening"])
            self.assertFalse(result["records"][0]["issuer_verified"])
            self.assertIsNone(result["records"][0]["original_publication_timestamp"])
            self.assertEqual(len(result["records"][0]["sha256"]), 64)

    def test_invalid_file_extension_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            archive = folder / "original.zip"
            with zipfile.ZipFile(archive, "w") as out:
                out.writestr("report.csv", "x")
            extracted = folder / "unpacked"
            extracted.mkdir()
            (extracted / "danger.exe").write_bytes(b"not-executable")
            with self.assertRaises(InventoryError):
                build_inventory(extracted, archive, 2021, "FY")

    def test_archive_magic_required_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            extracted = folder / "files"
            extracted.mkdir()
            (extracted / "report.csv").write_bytes(b"x")
            fake = folder / "fake.rar"
            fake.write_bytes(b"not-an-archive")
            with self.assertRaisesRegex(InventoryError, "Archive bytes"):
                build_inventory(extracted, fake, 2022, "FY")
            with zipfile.ZipFile(folder / "good.zip", "w") as z:
                z.writestr("report.csv", "x")
            with self.assertRaisesRegex(InventoryError, "Specify actual"):
                build_inventory(extracted, folder / "good.zip", 2030, "FY")


if __name__ == "__main__":
    unittest.main()
