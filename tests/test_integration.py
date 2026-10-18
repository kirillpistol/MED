import unittest
from unittest.mock import patch
from integration import integration_status

class IntegrationTests(unittest.TestCase):
    def test_contract_shape(self):
        with patch("integration.study_analytics", return_value={"archive_available": False,"studies":0,"archived_versions":0}), patch("integration.archive_quality", return_value={"archive_available": False,"checked":0,"failed":0}), patch("integration.discovery_inventory", return_value=[]), patch("integration.collection_status", return_value={"latest":[],"description":"no runs"}):
            status = integration_status()
            self.assertEqual(status["contract"], "med.integration.status")
            self.assertEqual(status["layer"], "L3")
            self.assertFalse(status["integration"]["clinical_validation"])
            self.assertIn("components", status)
    def test_dependency_error_is_degraded(self):
        with patch("integration.study_analytics", side_effect=RuntimeError):
            self.assertEqual(integration_status()["state"], "degraded")
if __name__ == "__main__":
    unittest.main()
