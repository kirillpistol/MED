import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import history
from themes import THEMES, summarize_themes
from reports import generate_research_report

class ThemeAnalyticsTests(unittest.TestCase):
    def test_empty_archive_keeps_all_five_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "absent.sqlite3")
            result = summarize_themes(db)
            self.assertEqual(len(result["themes"]), 5)
            self.assertEqual(result["archive_studies"], 0)
            report = generate_research_report(db)
            self.assertIn("research_themes", report)
            self.assertEqual(len(report["research_themes"]["themes"]), 5)

    def test_topic_overlap_is_explicit_and_latest_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "research.sqlite3")
            prior = history.DB_PATH
            history.DB_PATH = db
            try:
                record = {
                    "source_id": "clinicaltrials", "external_id": "NCT12345678",
                    "source_checksum_sha256": "a" * 64,
                    "title": "Blood tissue regeneration after injury",
                    "conditions": ["Trauma"],
                    "interventions": [], "recruitment_status": "RECRUITING",
                }
                history.archive_public_studies([record])
                updated = {**record, "source_checksum_sha256": "b" * 64,
                           "recruitment_status": "COMPLETED"}
                history.archive_public_studies([updated])
                themes = summarize_themes(db)
                self.assertEqual(themes["archive_studies"], 1)
                self.assertEqual(themes["themes"]["blood"]["matched_studies"], 1)
                self.assertEqual(themes["themes"]["injuries"]["matched_studies"], 1)
                self.assertEqual(themes["themes"]["tissue"]["matched_studies"], 1)
                self.assertEqual(themes["themes"]["tissue"]["status_counts"], {"COMPLETED": 1})
            finally:
                history.DB_PATH = prior

if __name__ == "__main__":
    unittest.main()
