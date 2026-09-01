import hashlib
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_manifest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


CAPTURED_AT = "2026-09-01T00:00:00Z"


def evidence(summary="Target test exits 0"):
    return {
        "kind": "test",
        "summary": summary,
        "fresh": True,
        "capturedAt": CAPTURED_AT,
        "command": "python -m unittest",
    }


def valid_manifest():
    content = "Make the change and verify it."
    return {
        "schemaVersion": 2,
        "level": "STANDARD",
        "taskType": "CHANGE",
        "expectedSourceDocumentIds": ["D-001"],
        "expectedSourceSegmentIds": ["S-001"],
        "expectedRequirementIds": ["R-001"],
        "sourceDocuments": [
            {
                "id": "D-001",
                "sequence": 1,
                "content": content,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        ],
        "sourceSegments": [
            {
                "id": "S-001",
                "documentId": "D-001",
                "start": 0,
                "end": len(content),
                "classification": "REQUIREMENT",
                "changeType": "INITIAL",
                "requirementIds": ["R-001"],
                "affectedRequirementIds": [],
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
                "effective": True,
                "supersededBySourceIds": [],
                "status": "PASS",
                "evidence": [evidence()],
            }
        ],
        "authority": {
            "allowed": [
                {
                    "id": "A-001",
                    "action": "edit the admitted target",
                    "basisSourceIds": ["S-001"],
                    "derivedNecessary": False,
                    "rationale": "",
                }
            ],
            "prohibited": [
                {
                    "id": "P-001",
                    "action": "deploy to production",
                    "basisSourceIds": [],
                    "derivedNecessary": True,
                    "rationale": "The request did not authorize deployment.",
                }
            ],
            "observedActions": [
                {"id": "X-001", "action": "edited the admitted target", "allowedBy": "A-001"}
            ],
            "violations": [],
        },
        "scopeDrift": [],
        "missingIds": [],
        "duplicateIds": [],
        "regressionChecks": [evidence("Relevant regression exits 0")],
        "regressionFailures": [],
        "beforeAfter": [],
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

    def test_rejects_source_document_gap(self):
        manifest = valid_manifest()
        manifest["sourceSegments"][0]["start"] = 1
        self.assertTrue(any("coverage gap" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_source_document_hash_mismatch(self):
        manifest = valid_manifest()
        manifest["sourceDocuments"][0]["sha256"] = "0" * 64
        self.assertTrue(any("SHA-256 mismatch" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_missing_declared_requirement_id(self):
        manifest = valid_manifest()
        manifest["expectedRequirementIds"].append("R-002")
        self.assertTrue(any("expectedRequirementIds mismatch" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_noncontiguous_requirement_ids(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["id"] = "R-002"
        manifest["sourceSegments"][0]["requirementIds"] = ["R-002"]
        manifest["expectedRequirementIds"] = ["R-002"]
        self.assertTrue(any("contiguous" in error for error in MODULE.validate_manifest(manifest)))

    def test_malformed_id_type_returns_errors_instead_of_raising(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["id"] = {"unexpected": "object"}
        errors = MODULE.validate_manifest(manifest)
        self.assertTrue(any("Invalid requirement id" in error for error in errors))

    def test_malformed_reference_types_return_errors_instead_of_raising(self):
        mutations = [
            lambda item: item["sourceDocuments"][0].__setitem__("id", {"bad": "document"}),
            lambda item: item["sourceSegments"][0].__setitem__("documentId", {"bad": "reference"}),
            lambda item: item["authority"]["observedActions"][0].__setitem__("allowedBy", {"bad": "authority"}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                manifest = valid_manifest()
                mutate(manifest)
                self.assertIsInstance(MODULE.validate_manifest(manifest), list)

    def test_rejects_orphan_requirement(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["sourceIds"] = []
        self.assertTrue(any("orphan" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_false_full_completion(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["status"] = "FAIL_RETRYABLE"
        manifest["requirements"][0]["evidence"] = []
        self.assertTrue(any("every effective mandatory" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_evidence_without_freshness_provenance(self):
        manifest = valid_manifest()
        del manifest["requirements"][0]["evidence"][0]["capturedAt"]
        del manifest["requirements"][0]["evidence"][0]["command"]
        errors = MODULE.validate_manifest(manifest)
        self.assertTrue(any("capturedAt" in error for error in errors))
        self.assertTrue(any("reproducible provenance" in error for error in errors))

    def test_rejects_authority_violation(self):
        manifest = valid_manifest()
        manifest["authority"]["violations"] = ["production write without authorization"]
        self.assertTrue(any("Authority violations" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_allowed_action_without_authority_basis(self):
        manifest = valid_manifest()
        manifest["authority"]["allowed"][0]["basisSourceIds"] = []
        self.assertTrue(any("authority basis" in error for error in MODULE.validate_manifest(manifest)))

    def test_rejects_observed_action_without_known_authorization(self):
        manifest = valid_manifest()
        manifest["authority"]["observedActions"][0]["allowedBy"] = "A-999"
        self.assertTrue(any("unknown allowed action" in error for error in MODULE.validate_manifest(manifest)))

    def test_accepts_complete_blocker_closeout(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["status"] = "BLOCKED_OWNER"
        manifest["requirements"][0]["evidence"] = []
        manifest["blockers"] = [
            {
                "type": "OWNER",
                "requirementIds": ["R-001"],
                "reason": "A new production decision is required",
                "attempts": ["Checked the current request and authority ledger"],
                "alternativesExhausted": ["No non-production substitute proves the required production state"],
                "resumeCondition": "Owner chooses the production target",
                "nextAction": "Apply the chosen target",
                "independentWorkComplete": True,
            }
        ]
        manifest["completionClaim"] = "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE"
        self.assertEqual(MODULE.validate_manifest(manifest), [])

    def test_rejects_blocker_without_attempts_and_alternatives(self):
        manifest = valid_manifest()
        manifest["requirements"][0]["status"] = "BLOCKED_CAPABILITY"
        manifest["requirements"][0]["evidence"] = []
        manifest["blockers"] = [
            {
                "type": "CAPABILITY",
                "requirementIds": ["R-001"],
                "reason": "Required runtime is unavailable",
                "attempts": [],
                "alternativesExhausted": [],
                "resumeCondition": "Runtime becomes available",
                "nextAction": "Run the verification",
                "independentWorkComplete": True,
            }
        ]
        manifest["completionClaim"] = "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE"
        errors = MODULE.validate_manifest(manifest)
        self.assertTrue(any("attempts" in error for error in errors))
        self.assertTrue(any("alternativesExhausted" in error for error in errors))

    def test_accepts_preserved_replacement_history(self):
        manifest = valid_manifest()
        replacement = "Use the safer replacement instead."
        manifest["expectedSourceDocumentIds"].append("D-002")
        manifest["sourceDocuments"].append(
            {
                "id": "D-002",
                "sequence": 2,
                "content": replacement,
                "sha256": hashlib.sha256(replacement.encode("utf-8")).hexdigest(),
            }
        )
        manifest["expectedSourceSegmentIds"].append("S-002")
        manifest["sourceSegments"].append(
            {
                "id": "S-002",
                "documentId": "D-002",
                "start": 0,
                "end": len(replacement),
                "classification": "REQUIREMENT",
                "changeType": "REPLACE",
                "requirementIds": ["R-001", "R-002"],
                "affectedRequirementIds": ["R-001"],
            }
        )
        manifest["requirements"][0]["sourceIds"].append("S-002")
        manifest["requirements"][0]["effective"] = False
        manifest["requirements"][0]["supersededBySourceIds"] = ["S-002"]
        manifest["requirements"][0]["status"] = "SUPERSEDED"
        manifest["requirements"][0]["evidence"] = []
        manifest["expectedRequirementIds"].append("R-002")
        manifest["requirements"].append(
            {
                "id": "R-002",
                "title": "Use the safer replacement",
                "sourceIds": ["S-002"],
                "derivedNecessary": False,
                "rationale": "",
                "mandatory": True,
                "effective": True,
                "supersededBySourceIds": [],
                "status": "PASS",
                "evidence": [evidence("Replacement verification exits 0")],
            }
        )
        manifest["authority"]["allowed"][0]["basisSourceIds"].append("S-002")
        self.assertEqual(MODULE.validate_manifest(manifest), [])

    def test_strict_claim_requires_before_after_evidence(self):
        manifest = valid_manifest()
        manifest["level"] = "STRICT"
        self.assertTrue(any("beforeAfter" in error for error in MODULE.validate_manifest(manifest)))

    def test_standard_claim_requires_regression_evidence(self):
        manifest = valid_manifest()
        manifest["regressionChecks"] = []
        self.assertTrue(any("regressionChecks" in error for error in MODULE.validate_manifest(manifest)))


if __name__ == "__main__":
    unittest.main()
