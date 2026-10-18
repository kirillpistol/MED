import tempfile
import unittest
from pathlib import Path
from file_registry import register_file, file_inventory

class FileRegistryTests(unittest.TestCase):
    def test_versions_and_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            file=root/"sample.csv"
            db=root/"history.sqlite"
            file.write_text("name,value\npublic,1\n",encoding="utf-8")
            self.assertTrue(register_file(file,"test_public",db)["new_version"])
            self.assertFalse(register_file(file,"test_public",db)["new_version"])
            file.write_text("name,value\npublic,2\n",encoding="utf-8")
            self.assertTrue(register_file(file,"test_public",db)["new_version"])
            self.assertEqual(len(file_inventory(db)),2)

    def test_reject_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            file=root/"script.py"
            file.write_text("pass",encoding="utf-8")
            with self.assertRaises(ValueError):
                register_file(file,"public",root/"history.sqlite")

if __name__=="__main__":
    unittest.main()
