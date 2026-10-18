import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research


class ResearchTests(unittest.TestCase):
    def setUp(self):
        research._cache.clear()

    def test_search_and_provenance(self):
        def fake(endpoint, params):
            if endpoint == "esearch.fcgi":
                return {"esearchresult": {"idlist": ["12345"], "count": "1"}}
            return {"result": {"12345": {"title": "Synthetic paper",
                        "fulljournalname": "Example", "pubdate": "2026",
                        "authors": [{"name": "Test Author"}]}}}
        with patch.object(research, "_json", side_effect=fake) as source:
            one = research.search_publications("synthetic example", 3)
            two = research.search_publications("synthetic example", 3)
        self.assertEqual(source.call_count, 2)
        self.assertEqual(one["records"][0]["pmid"], "12345")
        self.assertEqual(one["records"][0]["source"], "NCBI PubMed")
        self.assertTrue(two["cache_hit"])

    def test_reject_unbounded_or_sensitive_inputs(self):
        for term in ["a", "patient@email.com", "https://example.com"]:
            with self.assertRaises(ValueError):
                research.search_publications(term)
        with self.assertRaises(ValueError):
            research.search_publications("oncology", 11)

    def test_empty_search(self):
        with patch.object(research, "_json", return_value={"esearchresult":{"idlist":[],"count":"0"}}):
            result = research.search_publications("rare disease")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
