import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clinical_trials as ct


class ClinicalTrialsTests(unittest.TestCase):
    def setUp(self):
        ct._cache.clear()

    def test_normalization_provenance(self):
        study = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678", "briefTitle": "Synthetic Trial"},
            "statusModule": {"overallStatus": "RECRUITING",
                             "lastUpdatePostDateStruct": {"date": "2026-04-02"}},
            "conditionsModule": {"conditions": ["Synthetic condition"]},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
        }}
        with patch.object(ct, "_fetch", return_value={"studies": [study], "totalCount": 1}) as fetch:
            first = ct.search_studies("synthetic trial", 5)
            second = ct.search_studies("synthetic trial", 5)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["records"][0]["external_id"], "NCT12345678")
        self.assertEqual(first["records"][0]["last_update_posted"], "2026-04-02")
        self.assertEqual(len(first["records"][0]["source_checksum_sha256"]), 64)
        self.assertTrue(second["cache_hit"])

    def test_invalid_data_rejected(self):
        with self.assertRaises(ValueError):
            ct.normalize_study({"protocolSection": {"identificationModule": {"nctId": "bad"}}}, "today")
        for bad in ["hi", "someone@example.com"]:
            with self.assertRaises(ValueError):
                ct.search_studies(bad)
        with self.assertRaises(ValueError):
            ct.search_studies("synthetic trial", 11)

    def test_empty_results(self):
        with patch.object(ct, "_fetch", return_value={"studies": [], "totalCount": 0}):
            result = ct.search_studies("no results")
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
