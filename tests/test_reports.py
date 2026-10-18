import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import history
from reports import generate_research_report

class ResearchReportTests(unittest.TestCase):
    def test_empty_archive_has_traceable_report(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "missing.sqlite3")
            a = generate_research_report(db)
            b = generate_research_report(db)
            self.assertEqual(a["report_type"], "med.research.report")
            self.assertEqual(a["data"]["studies"], 0)
            self.assertEqual(a["data_checksum_sha256"], b["data_checksum_sha256"])
            self.assertIn("ClinicalTrials.gov", a["primary_source"]["name"])

    def test_report_changes_when_public_archive_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            before = generate_research_report(db)
            old = history.DB_PATH
            try:
                history.DB_PATH = db
                history.archive_public_studies([{"source_id": "clinicaltrials",
                    "external_id": "NCT12345678", "source_checksum_sha256": "a" * 64,
                    "recruitment_status": "RECRUITING", "phases": ["PHASE2"]}])
                after = generate_research_report(db)
                self.assertEqual(after["data"]["studies"], 1)
                self.assertNotEqual(before["data_checksum_sha256"], after["data_checksum_sha256"])
            finally:
                history.DB_PATH = old

if __name__ == "__main__":
    unittest.main()
