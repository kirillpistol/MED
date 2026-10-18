import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import history
from quality import archive_quality, validate_record

class QualityTests(unittest.TestCase):
    def test_valid_record(self):
        record = {"source_id":"clinicaltrials", "external_id":"NCT12345678",
                  "url":"https://clinicaltrials.gov/study/NCT12345678",
                  "title":"Synthetic", "recruitment_status":"RECRUITING",
                  "last_update_posted":"2025-01-01",
                  "source_checksum_sha256":"a"*64}
        self.assertTrue(validate_record(record)["passed"])

    def test_missing_metadata_flags(self):
        result = validate_record({"source_id":"clinicaltrials","external_id":"wrong"})
        self.assertFalse(result["passed"])
        self.assertIn("invalid_nct", result["issues"])
        self.assertIn("missing_title", result["issues"])

    def test_archive_quality_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/"test.db")
            previous = history.DB_PATH
            history.DB_PATH = path
            try:
                history.archive_public_studies([{"source_id":"clinicaltrials",
                    "external_id":"NCT12345678","source_checksum_sha256":"b"*64,
                    "title":"Synthetic","recruitment_status":"RECRUITING",
                    "url":"https://clinicaltrials.gov/study/NCT12345678",
                    "last_update_posted":"2025-01-01"}])
                result = archive_quality(path)
                self.assertEqual(result["checked"],1)
                self.assertEqual(result["passed"],1)
                self.assertEqual(result["failed"],0)
            finally:
                history.DB_PATH = previous

if __name__ == "__main__":
    unittest.main()
