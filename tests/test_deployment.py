import os
import tempfile
import unittest
from unittest.mock import patch
from deployment import topology, validate_storage

class DeploymentTests(unittest.TestCase):
    def test_default_single_host(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"MED_DATA_DIR": folder, "MED_TOPOLOGY":"single-host"}, clear=True):
                data = topology()
                self.assertEqual(data["storage"], "sqlite-local")
                self.assertFalse(data["distributed_ready"])
                self.assertEqual(len(data["database_paths"]), 5)
                self.assertFalse(validate_storage()["database_checks"]["history"]["database_present"])

    def test_reject_premature_distributed_mode(self):
        with patch.dict(os.environ, {"MED_TOPOLOGY": "distributed"}):
            with self.assertRaises(ValueError):
                topology()

if __name__ == "__main__":
    unittest.main()
