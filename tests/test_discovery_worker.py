import os
import unittest
from unittest.mock import patch
from discovery_worker import interval_hours, main

class WorkerTests(unittest.TestCase):
    def test_interval_bounds(self):
        with patch.dict(os.environ, {"MED_DISCOVERY_INTERVAL_HOURS": "24"}):
            self.assertEqual(interval_hours(), 24)
        with patch.dict(os.environ, {"MED_DISCOVERY_INTERVAL_HOURS": "0"}):
            with self.assertRaises(ValueError):
                interval_hours()
    def test_once(self):
        with patch("discovery_worker.discover", return_value=[{"status": "ok"}]) as mock:
            self.assertEqual(main(["once"]), 0)
            mock.assert_called_once()
    def test_error(self):
        with patch("discovery_worker.discover", return_value=[{"status": "error"}]):
            self.assertEqual(main(["once"]), 1)

if __name__ == "__main__":
    unittest.main()
