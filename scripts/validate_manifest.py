#!/usr/bin/env python3
"""Validate a Verified Completion Loop v3 JSON manifest."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ID_PATTERNS = {
    "document": re.compile(r"^D-[0-9]{3,}$"),
    "segment": re.compile(r"^S-[0-9]{3,}$"),
    "requirement": re.compile(r"^R-[0-9]{3,}$"),
    "allowed action": re.compile(r"^A-[0-9]{3,}$"),
    "prohibited action": re.compile(r"^P-[0-9]{3,}$"),
    "observed action": re.compile(r"^X-[0-9]{3,}$"),
    "artifact": re.compile(r"^I-[0-9]{3,}$"),
}
LEVELS = {"LIGHT", "STANDARD", "STRICT"}
TASK_TYPES = {"CHANGE", "AUDIT_ONLY", "DIAGNOSE_ONLY", "ANSWER", "MONITOR"}
CLASSIFICATIONS = {"REQUIREMENT", "CONSTRAINT", "PROHIBITION", "DELIVERABLE", "CONTEXT", "EXAMPLE"}
NORMATIVE = {"REQUIREMENT", "CONSTRAINT", "PROHIBITION", "DELIVERABLE"}
CHANGE_TYPES = {"INITIAL", "ADD", "CLARIFY", "REPLACE", "REVOKE", "NONE"}
STATUSES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "IMPLEMENTED",
    "VERIFYING",
    "PASS",
    "FAIL_RETRYABLE",
    "BLOCKED_OWNER",
    "BLOCKED_CAPABILITY",
    "DEFERRED_BY_SCOPE",
    "SUPERSEDED",
}
ACCEPTED_CLAIMS = {
    "TASK_FULLY_VERIFIED",
    "AUDIT_COMPLETE",
    "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE",
}
SEMANTIC_CHECK_KINDS = {
    "SOURCE_OMISSION",
    "AUTHORITY_OMISSION",
    "SEMANTIC_CLASSIFICATION",
    "CONTRADICTION",
    "FINAL_RESPONSE_ALIGNMENT",
}


def _duplicates(values: list[Any]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _validate_expected_ids(
    field: str,
    expected: Any,
    actual: list[Any],
    prefix: str,
    label: str,
    errors: list[str],
) -> None:
    if not _string_list(expected, allow_empty=False):
        errors.append(f"{field} must be a non-empty array of ids.")
        return
    duplicates = _duplicates(expected)
    for duplicate in sorted(duplicates, key=repr):
        errors.append(f"{field} contains duplicate id {duplicate}.")
    contiguous = [f"{prefix}-{index:03d}" for index in range(1, len(expected) + 1)]
    if expected != contiguous:
        errors.append(f"{field} must be contiguous from {prefix}-001.")
    actual_strings = [value for value in actual if isinstance(value, str)]
    if set(expected) != set(actual_strings) or len(expected) != len(actual):
        errors.append(f"{field} mismatch: declared ids do not equal actual {label} ids.")


def _validate_evidence(item: Any, label: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{label} must be an object.")
        return
    if not isinstance(item.get("kind"), str) or not item["kind"].strip():
        errors.append(f"{label} lacks kind.")
    if not isinstance(item.get("summary"), str) or not item["summary"].strip():
        errors.append(f"{label} lacks summary.")
    if item.get("fresh") is not True:
        errors.append(f"{label} is not marked fresh.")
    if not _valid_timestamp(item.get("capturedAt")):
        errors.append(f"{label} lacks a valid capturedAt timestamp.")
    provenance = (item.get("command"), item.get("artifactIdentity"), item.get("source"))
    if not any(isinstance(value, str) and value.strip() for value in provenance):
        errors.append(f"{label} lacks reproducible provenance: command, artifactIdentity, or source.")


def _validate_authority_record(
    record: Any,
    label: str,
    pattern: re.Pattern[str],
    source_ids: set[str],
    errors: list[str],
) -> str | None:
    if not isinstance(record, dict):
        errors.append(f"{label} must be an object.")
        return None
    record_id = record.get("id")
    if not isinstance(record_id, str) or not pattern.fullmatch(record_id):
        errors.append(f"{label} has invalid id {record_id!r}.")
    if not isinstance(record.get("action"), str) or not record["action"].strip():
        errors.append(f"{label} lacks action.")
    basis = record.get("basisSourceIds")
    if not _string_list(basis):
        errors.append(f"{label}.basisSourceIds must be an array of source ids.")
        basis = []
    for source_id in basis:
        if source_id not in source_ids:
            errors.append(f"{label} references unknown authority source {source_id}.")
    derived = record.get("derivedNecessary") is True
    rationale = record.get("rationale")
    if not basis and not (derived and isinstance(rationale, str) and rationale.strip()):
        errors.append(f"{label} lacks an explicit authority basis or derived-necessity rationale.")
    return record_id if isinstance(record_id, str) else None


def validate_manifest(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Manifest root must be an object."]

    if data.get("schemaVersion") != 3:
        errors.append("schemaVersion must be 3.")
    level = data.get("level")
    if level not in LEVELS:
        errors.append("level must be LIGHT, STANDARD, or STRICT.")
    task_type = data.get("taskType")
    if task_type not in TASK_TYPES:
        errors.append("taskType is unsupported.")

    documents = data.get("sourceDocuments")
    segments = data.get("sourceSegments")
    requirements = data.get("requirements")
    if not isinstance(documents, list) or not documents:
        errors.append("sourceDocuments must be a non-empty array.")
        documents = []
    if not isinstance(segments, list) or not segments:
        errors.append("sourceSegments must be a non-empty array.")
        segments = []
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty array.")
        requirements = []

    document_ids = [item.get("id") for item in documents if isinstance(item, dict)]
    segment_ids = [item.get("id") for item in segments if isinstance(item, dict)]
    requirement_ids = [item.get("id") for item in requirements if isinstance(item, dict)]
    if len(document_ids) != len(documents):
        errors.append("Every source document must be an object with an id.")
    if len(segment_ids) != len(segments):
        errors.append("Every source segment must be an object with an id.")
    if len(requirement_ids) != len(requirements):
        errors.append("Every requirement must be an object with an id.")

    _validate_expected_ids(
        "expectedSourceDocumentIds", data.get("expectedSourceDocumentIds"), document_ids, "D", "source document", errors
    )
    _validate_expected_ids(
        "expectedSourceSegmentIds", data.get("expectedSourceSegmentIds"), segment_ids, "S", "source segment", errors
    )
    _validate_expected_ids(
        "expectedRequirementIds", data.get("expectedRequirementIds"), requirement_ids, "R", "requirement", errors
    )

    for label, values, pattern in (
        ("source document", document_ids, ID_PATTERNS["document"]),
        ("source segment", segment_ids, ID_PATTERNS["segment"]),
        ("requirement", requirement_ids, ID_PATTERNS["requirement"]),
    ):
        for duplicate in sorted(_duplicates(values), key=repr):
            errors.append(f"Duplicate {label} id: {duplicate}.")
        for value in values:
            if not isinstance(value, str) or not pattern.fullmatch(value):
                errors.append(f"Invalid {label} id: {value!r}.")

    document_set = {value for value in document_ids if isinstance(value, str)}
    segment_set = {value for value in segment_ids if isinstance(value, str)}
    requirement_set = {value for value in requirement_ids if isinstance(value, str)}
    document_by_id: dict[str, dict[str, Any]] = {}
    sequences: list[Any] = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_id = document.get("id")
        sequences.append(document.get("sequence"))
        content = document.get("content")
        if not isinstance(content, str) or not content:
            errors.append(f"{document_id}: content must be a non-empty string.")
            content = ""
        sha256 = document.get("sha256")
        actual_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            errors.append(f"{document_id}: sha256 must be 64 lowercase hexadecimal characters.")
        elif sha256 != actual_sha256:
            errors.append(f"{document_id}: source-document SHA-256 mismatch.")
        if isinstance(document_id, str):
            document_by_id[document_id] = {"content": content, "length": len(content)}
    if sequences != list(range(1, len(documents) + 1)):
        errors.append("sourceDocuments.sequence must be contiguous and ordered from 1.")

    source_links: set[tuple[str, str]] = set()
    requirement_links: set[tuple[str, str]] = set()
    segment_by_id: dict[str, dict[str, Any]] = {}
    segments_by_document: dict[str, list[tuple[int, int, str]]] = {document_id: [] for document_id in document_set}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("id")
        document_id = segment.get("documentId")
        if not isinstance(document_id, str) or document_id not in document_set:
            errors.append(f"{segment_id}: unknown documentId {document_id!r}.")
        start = segment.get("start")
        end = segment.get("end")
        document_length = document_by_id.get(document_id, {}).get("length", 0) if isinstance(document_id, str) else 0
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            errors.append(f"{segment_id}: start and end must be integers.")
        elif start < 0 or end <= start or end > document_length:
            errors.append(f"{segment_id}: invalid source range {start}:{end}.")
        elif isinstance(document_id, str):
            segments_by_document.setdefault(document_id, []).append((start, end, str(segment_id)))

        classification = segment.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"{segment_id}: unsupported classification.")
        change_type = segment.get("changeType")
        if change_type not in CHANGE_TYPES:
            errors.append(f"{segment_id}: unsupported changeType.")
        mapped = segment.get("requirementIds")
        if not _string_list(mapped):
            errors.append(f"{segment_id}: requirementIds must be an array of requirement ids.")
            mapped = []
        elif len(set(mapped)) != len(mapped):
            errors.append(f"{segment_id}: requirementIds contains duplicates.")
        if classification in NORMATIVE and not mapped:
            errors.append(f"{segment_id}: normative source segment is unmapped.")
        for requirement_id in mapped:
            if requirement_id not in requirement_set:
                errors.append(f"{segment_id}: unknown requirement id {requirement_id}.")
            source_links.add((str(segment_id), requirement_id))

        affected = segment.get("affectedRequirementIds")
        if not _string_list(affected):
            errors.append(f"{segment_id}: affectedRequirementIds must be an array of requirement ids.")
            affected = []
        if change_type in {"REPLACE", "REVOKE"} and not affected:
            errors.append(f"{segment_id}: {change_type} requires affectedRequirementIds.")
        for requirement_id in affected:
            if requirement_id not in requirement_set:
                errors.append(f"{segment_id}: unknown affected requirement id {requirement_id}.")
            if requirement_id not in mapped:
                errors.append(f"{segment_id}: affected requirement {requirement_id} must also be mapped.")
        if isinstance(segment_id, str):
            segment_by_id[segment_id] = {"changeType": change_type, "affected": set(affected)}

    for document_id in document_set:
        ranges = sorted(segments_by_document.get(document_id, []))
        cursor = 0
        for start, end, segment_id in ranges:
            if start != cursor:
                errors.append(f"{document_id}: source coverage gap or overlap before {segment_id} at {cursor}:{start}.")
            cursor = max(cursor, end)
        expected_end = document_by_id.get(document_id, {}).get("length", 0)
        if cursor != expected_end:
            errors.append(f"{document_id}: source coverage gap after final segment at {cursor}:{expected_end}.")

    effective_mandatory: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        requirement_id = requirement.get("id")
        if not isinstance(requirement.get("title"), str) or not requirement["title"].strip():
            errors.append(f"{requirement_id}: title must be non-empty.")
        mandatory = requirement.get("mandatory")
        effective = requirement.get("effective")
        if not isinstance(mandatory, bool):
            errors.append(f"{requirement_id}: mandatory must be boolean.")
        if not isinstance(effective, bool):
            errors.append(f"{requirement_id}: effective must be boolean.")
        if mandatory is True and effective is True:
            effective_mandatory.append(requirement)

        status = requirement.get("status")
        if status not in STATUSES:
            errors.append(f"{requirement_id}: unsupported status.")
        mapped = requirement.get("sourceIds")
        if not _string_list(mapped):
            errors.append(f"{requirement_id}: sourceIds must be an array of source-segment ids.")
            mapped = []
        elif len(set(mapped)) != len(mapped):
            errors.append(f"{requirement_id}: sourceIds contains duplicates.")
        derived = requirement.get("derivedNecessary") is True
        rationale = requirement.get("rationale")
        if not mapped and not (derived and isinstance(rationale, str) and rationale.strip()):
            errors.append(f"{requirement_id}: orphan requirement lacks source mapping or derived-step rationale.")
        for source_id in mapped:
            if source_id not in segment_set:
                errors.append(f"{requirement_id}: unknown source id {source_id}.")
            requirement_links.add((source_id, str(requirement_id)))

        superseded_by = requirement.get("supersededBySourceIds")
        if not _string_list(superseded_by):
            errors.append(f"{requirement_id}: supersededBySourceIds must be an array of source ids.")
            superseded_by = []
        if effective is False:
            if status != "SUPERSEDED":
                errors.append(f"{requirement_id}: ineffective requirement must have status SUPERSEDED.")
            if not superseded_by:
                errors.append(f"{requirement_id}: superseded requirement must preserve its replacing or revoking source ids.")
            for source_id in superseded_by:
                segment = segment_by_id.get(source_id)
                if not segment or segment["changeType"] not in {"REPLACE", "REVOKE"}:
                    errors.append(f"{requirement_id}: superseding source {source_id} is not a REPLACE or REVOKE segment.")
                elif requirement_id not in segment["affected"]:
                    errors.append(f"{requirement_id}: superseding source {source_id} does not identify the affected requirement.")
        elif effective is True:
            if status == "SUPERSEDED":
                errors.append(f"{requirement_id}: effective requirement cannot be SUPERSEDED.")
            if superseded_by:
                errors.append(f"{requirement_id}: effective requirement cannot retain supersededBySourceIds.")

        evidence = requirement.get("evidence")
        if status == "PASS":
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{requirement_id}: PASS requires current direct evidence.")
            else:
                for index, item in enumerate(evidence, start=1):
                    _validate_evidence(item, f"{requirement_id}: evidence #{index}", errors)

    for link in sorted(source_links - requirement_links):
        errors.append(f"One-way mapping exists only in source segment: {link[0]} -> {link[1]}.")
    for link in sorted(requirement_links - source_links):
        errors.append(f"One-way mapping exists only in requirement: {link[1]} -> {link[0]}.")

    authority = data.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be an object.")
        authority = {}
    allowed = authority.get("allowed")
    prohibited = authority.get("prohibited")
    observed = authority.get("observedActions")
    violations = authority.get("violations")
    if not isinstance(allowed, list) or not allowed:
        errors.append("authority.allowed must be a non-empty array.")
        allowed = []
    if not isinstance(prohibited, list):
        errors.append("authority.prohibited must be an array.")
        prohibited = []
    if not isinstance(observed, list):
        errors.append("authority.observedActions must be an array.")
        observed = []
    if not _string_list(violations):
        errors.append("authority.violations must be an array of non-empty strings.")
        violations = []

    allowed_ids = [item.get("id") for item in allowed if isinstance(item, dict)]
    prohibited_ids = [item.get("id") for item in prohibited if isinstance(item, dict)]
    observed_ids = [item.get("id") for item in observed if isinstance(item, dict)]
    for label, records, ids, prefix in (
        ("allowed action", allowed, allowed_ids, "A"),
        ("prohibited action", prohibited, prohibited_ids, "P"),
        ("observed action", observed, observed_ids, "X"),
    ):
        if ids:
            expected = [f"{prefix}-{index:03d}" for index in range(1, len(ids) + 1)]
            if ids != expected:
                errors.append(f"{label} ids must be contiguous from {prefix}-001.")
        for duplicate in sorted(_duplicates(ids), key=repr):
            errors.append(f"Duplicate {label} id: {duplicate}.")

    known_allowed: set[str] = set()
    for index, record in enumerate(allowed, start=1):
        record_id = _validate_authority_record(
            record, f"allowed action #{index}", ID_PATTERNS["allowed action"], segment_set, errors
        )
        if record_id:
            known_allowed.add(record_id)
    for index, record in enumerate(prohibited, start=1):
        _validate_authority_record(
            record, f"prohibited action #{index}", ID_PATTERNS["prohibited action"], segment_set, errors
        )
    for index, record in enumerate(observed, start=1):
        if not isinstance(record, dict):
            errors.append(f"observed action #{index} must be an object.")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not ID_PATTERNS["observed action"].fullmatch(record_id):
            errors.append(f"observed action #{index} has invalid id {record_id!r}.")
        if not isinstance(record.get("action"), str) or not record["action"].strip():
            errors.append(f"observed action #{index} lacks action.")
        allowed_by = record.get("allowedBy")
        if not isinstance(allowed_by, str) or allowed_by not in known_allowed:
            errors.append(f"observed action #{index} references unknown allowed action {allowed_by!r}.")
    if violations:
        errors.append("Authority violations prevent an accepted completion claim.")

    for field in ("scopeDrift", "missingIds", "duplicateIds", "regressionFailures"):
        value = data.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} must be an array.")
        elif value:
            errors.append(f"{field} must be empty for an accepted completion claim.")

    regression_checks = data.get("regressionChecks")
    if not isinstance(regression_checks, list):
        errors.append("regressionChecks must be an array.")
        regression_checks = []
    if level in {"STANDARD", "STRICT"} and not regression_checks:
        errors.append(f"{level} completion requires regressionChecks evidence.")
    for index, item in enumerate(regression_checks, start=1):
        _validate_evidence(item, f"regressionChecks #{index}", errors)

    before_after = data.get("beforeAfter")
    if not isinstance(before_after, list):
        errors.append("beforeAfter must be an array.")
        before_after = []
    if level == "STRICT" and not before_after:
        errors.append("STRICT completion requires beforeAfter evidence.")
    for index, item in enumerate(before_after, start=1):
        if not isinstance(item, dict):
            errors.append(f"beforeAfter #{index} must be an object.")
            continue
        for field in ("subject", "before", "after"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"beforeAfter #{index} lacks {field}.")
        expectation = item.get("expectation")
        if expectation not in {"UNCHANGED", "CHANGED"}:
            errors.append(f"beforeAfter #{index} has unsupported expectation.")
        elif expectation == "UNCHANGED" and item.get("before") != item.get("after"):
            errors.append(f"beforeAfter #{index} expected UNCHANGED but identities differ.")
        elif expectation == "CHANGED" and item.get("before") == item.get("after"):
            errors.append(f"beforeAfter #{index} expected CHANGED but identities match.")
        if item.get("verified") is not True:
            errors.append(f"beforeAfter #{index} is not verified.")

    artifact_inventory = data.get("artifactInventory")
    inspected_artifact_ids: set[str] = set()
    if level in {"STANDARD", "STRICT"} and (
        not isinstance(artifact_inventory, dict) or not artifact_inventory
    ):
        errors.append(f"{level} completion requires artifactInventory discovery evidence.")
        artifact_inventory = {}
    elif artifact_inventory is None:
        artifact_inventory = {}
    elif not isinstance(artifact_inventory, dict):
        errors.append("artifactInventory must be an object.")
        artifact_inventory = {}
    if artifact_inventory:
        if artifact_inventory.get("discoveryPerformed") is not True:
            errors.append("artifactInventory must confirm discoveryPerformed.")
        if not isinstance(artifact_inventory.get("method"), str) or not artifact_inventory["method"].strip():
            errors.append("artifactInventory lacks a discovery method.")
        if not _valid_timestamp(artifact_inventory.get("capturedAt")):
            errors.append("artifactInventory lacks a valid capturedAt timestamp.")
        discovery_evidence = artifact_inventory.get("evidence")
        if not isinstance(discovery_evidence, list) or not discovery_evidence:
            errors.append("artifactInventory requires current discovery evidence.")
        else:
            for index, item in enumerate(discovery_evidence, start=1):
                _validate_evidence(item, f"artifactInventory.evidence #{index}", errors)
        artifacts = artifact_inventory.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append("artifactInventory.artifacts must be an array.")
            artifacts = []
        no_artifacts_reason = artifact_inventory.get("noExternalArtifactsReason")
        if not artifacts and not (isinstance(no_artifacts_reason, str) and no_artifacts_reason.strip()):
            errors.append("artifactInventory requires artifacts or a noExternalArtifactsReason.")
        artifact_ids = [item.get("id") for item in artifacts if isinstance(item, dict)]
        expected_artifact_ids = [f"I-{index:03d}" for index in range(1, len(artifact_ids) + 1)]
        if artifact_ids != expected_artifact_ids:
            errors.append("artifact ids must be contiguous from I-001.")
        if len(artifact_ids) != len(artifacts):
            errors.append("Every artifact inventory entry must be an object with an id.")
        for index, artifact in enumerate(artifacts, start=1):
            if not isinstance(artifact, dict):
                continue
            artifact_id = artifact.get("id")
            if not isinstance(artifact_id, str) or not ID_PATTERNS["artifact"].fullmatch(artifact_id):
                errors.append(f"artifact #{index} has invalid id {artifact_id!r}.")
            for field in ("locator", "rationale"):
                if not isinstance(artifact.get(field), str) or not artifact[field].strip():
                    errors.append(f"{artifact_id}: artifact lacks {field}.")
            if artifact.get("role") not in {"AUTHORITATIVE", "TARGET", "SUPPORTING"}:
                errors.append(f"{artifact_id}: artifact has unsupported role.")
            disposition = artifact.get("disposition")
            if disposition not in {"INSPECTED", "EXCLUDED"}:
                errors.append(f"{artifact_id}: artifact has unsupported disposition.")
            if artifact.get("role") == "AUTHORITATIVE" and disposition == "EXCLUDED":
                errors.append(f"{artifact_id}: authoritative artifact cannot be EXCLUDED.")
            if disposition == "INSPECTED":
                if isinstance(artifact_id, str):
                    inspected_artifact_ids.add(artifact_id)
                if not isinstance(artifact.get("identity"), str) or not artifact["identity"].strip():
                    errors.append(f"{artifact_id}: inspected artifact lacks identity.")

    semantic_review = data.get("semanticReview")
    if level in {"STANDARD", "STRICT"} and (
        not isinstance(semantic_review, dict) or not semantic_review
    ):
        errors.append(f"{level} completion requires semanticReview.")
        semantic_review = {}
    elif semantic_review is None:
        semantic_review = {}
    elif not isinstance(semantic_review, dict):
        errors.append("semanticReview must be an object.")
        semantic_review = {}
    if semantic_review:
        mode = semantic_review.get("mode")
        if mode not in {"INDEPENDENT_AGENT", "ADVERSARIAL_SECOND_PASS"}:
            errors.append("semanticReview.mode is unsupported.")
        if not isinstance(semantic_review.get("reviewer"), str) or not semantic_review["reviewer"].strip():
            errors.append("semanticReview lacks reviewer identity.")
        independent_available = semantic_review.get("independentReviewAvailable")
        if not isinstance(independent_available, bool):
            errors.append("semanticReview.independentReviewAvailable must be boolean.")
        elif level == "STRICT" and independent_available and mode != "INDEPENDENT_AGENT":
            errors.append("STRICT must use INDEPENDENT_AGENT when independent review is available.")
        if mode == "ADVERSARIAL_SECOND_PASS":
            limitation = semantic_review.get("independenceLimitation")
            if not isinstance(limitation, str) or not limitation.strip():
                errors.append("ADVERSARIAL_SECOND_PASS must disclose its independenceLimitation.")
        if semantic_review.get("sourceReadDirectly") is not True:
            errors.append("semanticReview must reread the source directly.")
        reviewed_requirements = semantic_review.get("reviewedRequirementIds")
        expected_reviewed_requirements = {
            str(item.get("id")) for item in effective_mandatory if isinstance(item.get("id"), str)
        }
        if not _string_list(reviewed_requirements) or set(reviewed_requirements) != expected_reviewed_requirements:
            errors.append("semanticReview must review every effective mandatory requirement exactly once.")
        elif len(reviewed_requirements) != len(set(reviewed_requirements)):
            errors.append("semanticReview.reviewedRequirementIds contains duplicates.")
        reviewed_artifacts = semantic_review.get("reviewedArtifactIds")
        if not _string_list(reviewed_artifacts) or set(reviewed_artifacts) != inspected_artifact_ids:
            errors.append("semanticReview must review every inspected artifact exactly once.")
        elif len(reviewed_artifacts) != len(set(reviewed_artifacts)):
            errors.append("semanticReview.reviewedArtifactIds contains duplicates.")
        checks = semantic_review.get("checks")
        seen_check_kinds: set[str] = set()
        if not isinstance(checks, list):
            errors.append("semanticReview.checks must be an array.")
            checks = []
        for index, check in enumerate(checks, start=1):
            if not isinstance(check, dict):
                errors.append(f"semanticReview.check #{index} must be an object.")
                continue
            kind = check.get("kind")
            if kind not in SEMANTIC_CHECK_KINDS:
                errors.append(f"semanticReview.check #{index} has unsupported kind.")
            elif kind in seen_check_kinds:
                errors.append(f"semanticReview contains duplicate {kind} check.")
            else:
                seen_check_kinds.add(kind)
            if check.get("result") != "PASS":
                errors.append(f"semanticReview.check #{index} must PASS before an accepted claim.")
            if not isinstance(check.get("summary"), str) or not check["summary"].strip():
                errors.append(f"semanticReview.check #{index} lacks summary.")
        for missing_kind in sorted(SEMANTIC_CHECK_KINDS - seen_check_kinds):
            errors.append(f"semanticReview lacks required {missing_kind} check.")
        findings = semantic_review.get("findings")
        if not isinstance(findings, list):
            errors.append("semanticReview.findings must be an array.")
        elif findings:
            errors.append("Unresolved semantic findings prevent an accepted completion claim.")
        if semantic_review.get("verdict") != "PASS":
            errors.append("semanticReview.verdict must be PASS before an accepted completion claim.")
        expected_pass_count = sum(item.get("status") == "PASS" for item in effective_mandatory)
        if semantic_review.get("reviewedCompletionClaim") != data.get("completionClaim"):
            errors.append("semanticReview.reviewedCompletionClaim must match completionClaim.")
        if semantic_review.get("reviewedMandatoryPass") != expected_pass_count:
            errors.append("semanticReview.reviewedMandatoryPass must match the current PASS count.")
        if semantic_review.get("reviewedMandatoryTotal") != len(effective_mandatory):
            errors.append("semanticReview.reviewedMandatoryTotal must match the effective mandatory total.")
        if not _valid_timestamp(semantic_review.get("capturedAt")):
            errors.append("semanticReview lacks a valid capturedAt timestamp.")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be an array.")
        blockers = []
    blocked_ids: set[str] = set()
    for index, blocker in enumerate(blockers, start=1):
        if not isinstance(blocker, dict):
            errors.append(f"blocker #{index} must be an object.")
            continue
        if blocker.get("type") not in {"OWNER", "CAPABILITY"}:
            errors.append(f"blocker #{index} has unsupported type.")
        ids = blocker.get("requirementIds")
        if not _string_list(ids, allow_empty=False):
            errors.append(f"blocker #{index} must identify requirements.")
            ids = []
        for requirement_id in ids:
            if requirement_id not in requirement_set:
                errors.append(f"blocker #{index} references unknown requirement {requirement_id}.")
        blocked_ids.update(ids)
        for field in ("reason", "resumeCondition", "nextAction"):
            if not isinstance(blocker.get(field), str) or not blocker[field].strip():
                errors.append(f"blocker #{index} lacks {field}.")
        for field in ("attempts", "alternativesExhausted"):
            if not _string_list(blocker.get(field), allow_empty=False):
                errors.append(f"blocker #{index}.{field} must be a non-empty array.")
        if blocker.get("independentWorkComplete") is not True:
            errors.append(f"blocker #{index} must confirm independent work is complete.")

    claim = data.get("completionClaim")
    if claim not in ACCEPTED_CLAIMS:
        errors.append("completionClaim is unsupported or incomplete.")
    effective_mandatory_nonpass = [item for item in effective_mandatory if item.get("status") != "PASS"]
    if claim == "TASK_FULLY_VERIFIED":
        if effective_mandatory_nonpass:
            errors.append("TASK_FULLY_VERIFIED requires every effective mandatory requirement to PASS.")
        if blockers:
            errors.append("TASK_FULLY_VERIFIED cannot retain blockers.")
    elif claim == "AUDIT_COMPLETE":
        if task_type != "AUDIT_ONLY":
            errors.append("AUDIT_COMPLETE requires taskType AUDIT_ONLY.")
        if effective_mandatory_nonpass:
            errors.append("AUDIT_COMPLETE requires every effective mandatory audit deliverable to PASS.")
    elif claim == "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE":
        unresolved_ids = {str(item.get("id")) for item in effective_mandatory_nonpass}
        if not unresolved_ids:
            errors.append("Use TASK_FULLY_VERIFIED when no effective mandatory blocker remains.")
        if any(item.get("status") not in {"BLOCKED_OWNER", "BLOCKED_CAPABILITY"} for item in effective_mandatory_nonpass):
            errors.append("All unresolved effective mandatory requirements must be genuinely blocked.")
        if blocked_ids != unresolved_ids:
            errors.append("Blocker records must cover exactly the unresolved effective mandatory requirements.")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_manifest.py <manifest.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"MANIFEST_INVALID: {exc}", file=sys.stderr)
        return 2

    errors = validate_manifest(data)
    requirements = data.get("requirements", []) if isinstance(data, dict) else []
    mandatory = [
        item
        for item in requirements
        if isinstance(item, dict) and item.get("mandatory") is True and item.get("effective") is True
    ]
    passed = sum(item.get("status") == "PASS" for item in mandatory)
    blocked = sum(item.get("status") in {"BLOCKED_OWNER", "BLOCKED_CAPABILITY"} for item in mandatory)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(
            f"COMPLETION_MANIFEST status=FAIL mandatory={len(mandatory)} "
            f"pass={passed} blocked={blocked} errors={len(errors)}"
        )
        return 2

    print(
        f"COMPLETION_MANIFEST status=PASS claim={data['completionClaim']} "
        f"mandatory={len(mandatory)} pass={passed} blocked={blocked}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
