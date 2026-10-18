import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import CaseRequest, Observation, calculate


class MedTests(unittest.TestCase):
    def test_reproducible_scoring_and_trace(self):
        case = CaseRequest(case_id="demo-001", synthetic=True,
            observations=[Observation(code="fever", present=True),
                          Observation(code="cough", present=True)])
        result = calculate(case)
        self.assertEqual(result["candidates"][0]["pattern"], "respiratory_pattern")
        self.assertEqual(result["candidates"][0]["similarity_score"], 0.6667)
        self.assertEqual(result["input_sha256"], calculate(case)["input_sha256"])

    def test_duplicate_observation_rejected(self):
        case = CaseRequest(case_id="demo-002", synthetic=True,
            observations=[Observation(code="fever", present=True),
                          Observation(code="fever", present=False)])
        with self.assertRaises(ValueError):
            calculate(case)

    def test_no_clinical_claim(self):
        case = CaseRequest(case_id="demo-003", synthetic=True,
                           observations=[Observation(code="headache", present=True)])
        result = calculate(case)
        self.assertIn("not diagnostic probabilities", result["warnings"][1])
        self.assertEqual(result["trace"]["algorithm"], "weighted_rule_overlap")


if __name__ == "__main__":
    unittest.main()
