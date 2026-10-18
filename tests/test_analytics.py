import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import history
from analytics import study_analytics


class AnalyticsTests(unittest.TestCase):
    def test_empty_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            out = study_analytics(str(Path(directory) / "absent.sqlite"))
            self.assertFalse(out["archive_available"])
            self.assertEqual(out["studies"], 0)

    def test_latest_version_and_status_change(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = history.DB_PATH
            history.DB_PATH = str(Path(directory) / "history.sqlite")
            try:
                base = {"source_id": "clinicaltrials", "external_id": "NCT12345678",
                        "source_checksum_sha256": "a" * 64,
                        "recruitment_status": "RECRUITING",
                        "phases": ["PHASE2"], "url": "https://clinicaltrials.gov/study/NCT12345678"}
                self.assertEqual(history.archive_public_studies([base])["inserted_versions"], 1)
                newer = {**base, "source_checksum_sha256": "b" * 64,
                         "recruitment_status": "COMPLETED"}
                self.assertEqual(history.archive_public_studies([newer])["inserted_versions"], 1)
                report = study_analytics(history.DB_PATH)
                self.assertEqual(report["studies"], 1)
                self.assertEqual(report["archived_versions"], 2)
                self.assertEqual(report["status_counts"], {"COMPLETED": 1})
                self.assertEqual(report["phase_counts"], {"PHASE2": 1})
                self.assertTrue(report["changes"][0]["recruitment_status_changed"])
            finally:
                history.DB_PATH = previous


if __name__ == "__main__":
    unittest.main()
