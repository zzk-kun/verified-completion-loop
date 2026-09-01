import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_manifest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_manifest():
    return {
        "schemaVersion": 1,
        "level": "STANDARD",
        "taskType": "CHANGE",
        "sourceSegments": [
            {
                "id": "S-001",
                "text": "Make the change and verify it.",
                "classification": "REQUIREMENT",
                "requirementIds": ["R-001"],
            }
        ],
        "requirements": [
            {
                "id": "R-001",
                "title": "Make and verify the change",
                "sourceIds": ["S-001"],
                "derivedNecessary": False,
                "rationale": "",
                "mandatory": True,
                "status": "PASS",
                "evidence": [{"kind": "test", "summary": "Target test exits 0", "fresh": True}],
            }
        ],
        "authority": {"allowed": ["edit target"], "prohibited": ["deploy"], "violations": []},
        "scopeDrift": [],
        "missingIds": [],
        "duplicateIds": [],
        "regressionFailures": [],
        "blockers": [],
        "completionClaim": "TASK_FULLY_VERIFIED",
    }


class ManifestValidationTests(unittest.TestCase):
    def test_valid_full_completion(self):
        self.assertEqual(MODULE.validate_manifest(valid_manifest()), [])

    def test_rejects_unmapped_normative_source(self):
        manifest = valid_manifest()
        manifest["sourceSegments"][0]["requirementIds"] = []
        self.assertTrue(any("unmapped" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_orphan_requirement(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["sourceIds"] = []
        self.assertTrue(any("orphan" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_false_full_completion(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["status"] = "FAIL_RETRYABLE"
        manifest["requirements"][0]["evidence"] = []
        self.assertTrue(any("every mandatory" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_authority_violation(self):
        manifest = valid_manifest()
        manifest["authority"]["violations"] = ["production write without authorization"]
        self.assertTrue(any("Authority violations" in error for error in MODULE.validate_manifest(manifest)))

    def test_requires_explicit_authority_fields(self):
        manifest = valid_manifest()
        del manifest["authority"]["prohibited"]
        self.assertTrue(any("authority.prohibited" in error for error in MODULE.validate_manifest(manifest)))

    def test_accepts_complete_blocker_closeout(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["status"] = "BLOCKED_OWNER"
        manifest["requirements"][0]["evidence"] = []
        manifest["blockers"] = [
            {
                "type": "OWNER",
                "requirementIds": ["R-001"],
                "reason": "A new production decision is required",
                "resumeCondition": "Owner chooses the production target",
                "nextAction": "Apply the chosen target",
                "independentWorkComplete": True,
            }
        ]
        manifest["completionClaim"] = "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE"
        self.assertEqual(MODULE.validate_manifest(manifest), [])


if __name__ == "__main__":
    unittest.main()
