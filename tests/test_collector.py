import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collector


class CollectorTests(unittest.TestCase):
    def test_cycle_logs_success_and_failure(self):
        jobs = {"schedule_hours": 6, "queries": [
            {"source": "clinicaltrials", "term": "research", "limit": 2},
            {"source": "pubmed", "term": "research", "limit": 2}]}
        with tempfile.TemporaryDirectory() as d:
            db = str(Path(d) / "runs.sqlite3")
            with patch.object(collector, "search_studies", return_value={"count": 1, "records": []}), \
                 patch.object(collector, "archive_public_studies", return_value={"inserted_versions": 0}), \
                 patch.object(collector, "search_publications", side_effect=RuntimeError("temporary outage")), \
                 patch.object(collector.time, "sleep"):
                results = collector.run_cycle(jobs, db_path=db)
            self.assertEqual([r["status"] for r in results], ["ok", "error"])
            self.assertEqual(results[1]["error_type"], "RuntimeError")
            import sqlite3
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0], 2)

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.json"
            path.write_text(json.dumps({"schedule_hours": 0, "queries": []}))
            with self.assertRaises(ValueError):
                collector._config(path)
            path.write_text(json.dumps({"schedule_hours": 6, "queries": [
                {"source": "private", "term": "test", "limit": 3}]}))
            with self.assertRaises(ValueError):
                collector._config(path)


if __name__ == "__main__":
    unittest.main()
