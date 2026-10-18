import tempfile
import unittest
from pathlib import Path
from documents import publish_report, list_reports, get_report

class DocumentsTests(unittest.TestCase):
    def test_publish_list_and_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "documents.sqlite3"
            self.assertEqual(list_reports(db)["documents"], [])
            report = {"report_type": "med.research.report",
                      "data": {"studies": 2}, "limitations": ["public metadata"]}
            entry = publish_report(report, db)
            self.assertEqual(entry["origin"], "MED-L3")
            self.assertEqual(len(list_reports(db)["documents"]), 1)
            self.assertEqual(get_report(entry["document_id"], db), report)
            self.assertIsNone(get_report("unknown", db))
    def test_reject_other_document_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                publish_report({"report_type": "patient-record"}, Path(tmp) / "x.db")

if __name__ == "__main__":
    unittest.main()
