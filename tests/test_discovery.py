import tempfile
import unittest
from pathlib import Path
from discovery import discover, discovery_inventory
from collector_status import collection_status

class DiscoveryTests(unittest.TestCase):
    def test_collect_new_sites_and_topics(self):
        def fake(query, limit):
            return {"results": [{"title": "Regeneration study",
                "primary_location": {"landing_page_url": "https://journal.example.org/article/1"}},
                {"title": "Unsafe link",
                "primary_location": {"landing_page_url": "http://example.org/not-https"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "discovery.sqlite")
            result = discover(db_path=db, queries=("tissue engineering",), fetch=fake)
            self.assertEqual(result[0]["candidates_seen"], 1)
            self.assertEqual(len(discovery_inventory(db)), 1)
            discover(db_path=db, queries=("tissue engineering",), fetch=fake)
            self.assertEqual(len(discovery_inventory(db)), 1)
            self.assertEqual(discovery_inventory(db)[0]["status"], "candidate")

    def test_collection_history_before_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = collection_status(str(Path(tmp) / "missing.sqlite"))
            self.assertEqual(status["latest"], [])

if __name__ == "__main__":
    unittest.main()
