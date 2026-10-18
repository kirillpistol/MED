import sys
import tempfile
import json
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_catalog import source_catalog


class SourceCatalogTests(unittest.TestCase):
    def test_catalog_inventory_only(self):
        result = source_catalog()
        self.assertEqual(result["count"], 17)
        self.assertTrue(result["all_sources_candidate"])
        self.assertEqual(result["network_requests_performed"], 0)
        self.assertTrue(all(not x["fetch_enabled"] for x in result["sources"]))

    def test_categories(self):
        self.assertEqual(source_catalog(category="russia")["count"], 7)
        self.assertEqual(source_catalog(category="neuro")["count"], 4)
        with self.assertRaises(ValueError):
            source_catalog(category="other")

    def test_reject_unreviewed_connector_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(__file__).resolve().parents[1] / "config" / "extended_sources.json"
            data = json.loads(src.read_text(encoding="utf-8"))
            data["sources"][0]["fetch_enabled"] = True
            out = Path(temp) / "catalog.json"
            out.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                source_catalog(out)


if __name__ == "__main__":
    unittest.main()
