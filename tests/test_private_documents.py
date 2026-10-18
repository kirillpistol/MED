import unittest
from private_documents import validate_submission

class PrivateDocumentsTests(unittest.TestCase):
    def test_private_medical_study(self):
        result = validate_submission({
            "document_id": "MEDTEST001", "owner_ref": "GENESISUSER001",
            "filename": "synthetic_blood.pdf", "kind": "blood_test",
            "consent_scope": "private_analysis"})
        self.assertEqual(result["storage"], "L2_only")
        self.assertFalse(result["trained_into_model"])
    def test_book_needs_rights_basis(self):
        with self.assertRaises(ValueError):
            validate_submission({"document_id": "MEDBOOK001",
                                 "owner_ref": "GENESISUSER001",
                                 "filename": "book_scan.pdf", "kind": "medical_book",
                                 "consent_scope": "private_reference"})
if __name__ == "__main__":
    unittest.main()
