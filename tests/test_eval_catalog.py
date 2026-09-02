import json
import unittest
from pathlib import Path


CASES = Path(__file__).parents[1] / "evals" / "cases.json"


class EvalCatalogTests(unittest.TestCase):
    def test_catalog_covers_the_five_primary_failure_classes(self):
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertEqual([case["id"] for case in cases], [f"E-{index:03d}" for index in range(1, 7)])
        failure_modes = {case["failureMode"] for case in cases}
        self.assertTrue(
            {
                "source-omission",
                "retryable-gap-returned-to-owner",
                "completion-pressure-expands-authority",
                "simple-task-overhead",
                "final-response-overclaim",
            }.issubset(failure_modes)
        )
        for case in cases:
            self.assertTrue(case["prompt"].strip())
            self.assertTrue(case["candidate"].strip())
            self.assertTrue(case["expected"])


if __name__ == "__main__":
    unittest.main()
