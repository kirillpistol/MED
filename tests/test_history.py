import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import history


class HistoryTests(unittest.TestCase):
    def test_versions_deduplicate_and_retain_different_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            old = history.DB_PATH
            history.DB_PATH = str(Path(directory) / "med.sqlite3")
            try:
                base = {"source_id": "clinicaltrials", "external_id": "NCT12345678",
                        "source_checksum_sha256": "a" * 64, "title": "Synthetic study"}
                self.assertEqual(history.archive_public_studies([base])["inserted_versions"], 1)
                self.assertEqual(history.archive_public_studies([base])["inserted_versions"], 0)
                changed = {**base, "title": "Synthetic update", "source_checksum_sha256": "b" * 64}
                self.assertEqual(history.archive_public_studies([changed])["inserted_versions"], 1)
                self.assertEqual(len(history.study_history("NCT12345678")), 2)
                with self.assertRaises(ValueError):
                    history.archive_public_studies([{**base, "source_id": "private_patient"}])
            finally:
                history.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
