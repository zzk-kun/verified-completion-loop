#!/usr/bin/env python3
"""Validate a Verified Completion Loop JSON manifest using the standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SOURCE_ID = re.compile(r"^S-[0-9]{3,}$")
REQUIREMENT_ID = re.compile(r"^R-[0-9]{3,}$")
LEVELS = {"LIGHT", "STANDARD", "STRICT"}
TASK_TYPES = {"CHANGE", "AUDIT_ONLY", "DIAGNOSE_ONLY", "ANSWER", "MONITOR"}
CLASSIFICATIONS = {"REQUIREMENT", "CONSTRAINT", "PROHIBITION", "DELIVERABLE", "CONTEXT", "EXAMPLE"}
NORMATIVE = {"REQUIREMENT", "CONSTRAINT", "PROHIBITION", "DELIVERABLE"}
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
}
ACCEPTED_CLAIMS = {
    "TASK_FULLY_VERIFIED",
    "AUDIT_COMPLETE",
    "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE",
}


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    return {value for value in values if value in seen or seen.add(value)}


def _nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def validate_manifest(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Manifest root must be an object."]

    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1.")
    if data.get("level") not in LEVELS:
        errors.append("level must be LIGHT, STANDARD, or STRICT.")
    if data.get("taskType") not in TASK_TYPES:
        errors.append("taskType is unsupported.")

    segments = data.get("sourceSegments")
    requirements = data.get("requirements")
    if not isinstance(segments, list) or not segments:
        errors.append("sourceSegments must be a non-empty array.")
        segments = []
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty array.")
        requirements = []

    source_ids = [item.get("id") for item in segments if isinstance(item, dict)]
    requirement_ids = [item.get("id") for item in requirements if isinstance(item, dict)]
    if len(source_ids) != len(segments):
        errors.append("Every source segment must be an object with an id.")
    if len(requirement_ids) != len(requirements):
        errors.append("Every requirement must be an object with an id.")
    for duplicate in sorted(_duplicates(source_ids), key=repr):
        errors.append(f"Duplicate source segment id: {duplicate}.")
    for duplicate in sorted(_duplicates(requirement_ids), key=repr):
        errors.append(f"Duplicate requirement id: {duplicate}.")

    source_set = set(source_ids)
    requirement_set = set(requirement_ids)
    source_links: set[tuple[str, str]] = set()
    requirement_links: set[tuple[str, str]] = set()

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not SOURCE_ID.fullmatch(segment_id):
            errors.append(f"Invalid source segment id: {segment_id!r}.")
        if not isinstance(segment.get("text"), str) or not segment["text"].strip():
            errors.append(f"{segment_id}: text must be non-empty.")
        classification = segment.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"{segment_id}: unsupported classification.")
        mapped = segment.get("requirementIds")
        if not isinstance(mapped, list) or not all(isinstance(item, str) for item in mapped):
            errors.append(f"{segment_id}: requirementIds must be an array of strings.")
            mapped = []
        elif len(set(mapped)) != len(mapped):
            errors.append(f"{segment_id}: requirementIds contains duplicates.")
        if classification in NORMATIVE and not mapped:
            errors.append(f"{segment_id}: normative source segment is unmapped.")
        for requirement_id in mapped:
            if requirement_id not in requirement_set:
                errors.append(f"{segment_id}: unknown requirement id {requirement_id}.")
            source_links.add((segment_id, requirement_id))

    mandatory: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        requirement_id = requirement.get("id")
        if not isinstance(requirement_id, str) or not REQUIREMENT_ID.fullmatch(requirement_id):
            errors.append(f"Invalid requirement id: {requirement_id!r}.")
        if not isinstance(requirement.get("title"), str) or not requirement["title"].strip():
            errors.append(f"{requirement_id}: title must be non-empty.")
        if not isinstance(requirement.get("mandatory"), bool):
            errors.append(f"{requirement_id}: mandatory must be boolean.")
        elif requirement["mandatory"]:
            mandatory.append(requirement)

        status = requirement.get("status")
        if status not in STATUSES:
            errors.append(f"{requirement_id}: unsupported status.")

        mapped = requirement.get("sourceIds")
        if not isinstance(mapped, list) or not all(isinstance(item, str) for item in mapped):
            errors.append(f"{requirement_id}: sourceIds must be an array of strings.")
            mapped = []
        elif len(set(mapped)) != len(mapped):
            errors.append(f"{requirement_id}: sourceIds contains duplicates.")
        derived = requirement.get("derivedNecessary") is True
        rationale = requirement.get("rationale")
        if not mapped and not (derived and isinstance(rationale, str) and rationale.strip()):
            errors.append(f"{requirement_id}: orphan requirement lacks source mapping or derived-step rationale.")
        for source_id in mapped:
            if source_id not in source_set:
                errors.append(f"{requirement_id}: unknown source id {source_id}.")
            requirement_links.add((source_id, requirement_id))

        evidence = requirement.get("evidence")
        if status == "PASS":
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{requirement_id}: PASS requires current direct evidence.")
            else:
                for index, item in enumerate(evidence):
                    if not isinstance(item, dict):
                        errors.append(f"{requirement_id}: evidence #{index + 1} must be an object.")
                        continue
                    if not isinstance(item.get("kind"), str) or not item["kind"].strip():
                        errors.append(f"{requirement_id}: evidence #{index + 1} lacks kind.")
                    if not isinstance(item.get("summary"), str) or not item["summary"].strip():
                        errors.append(f"{requirement_id}: evidence #{index + 1} lacks summary.")
                    if item.get("fresh") is not True:
                        errors.append(f"{requirement_id}: evidence #{index + 1} is not marked fresh.")

    for link in sorted(source_links - requirement_links):
        errors.append(f"One-way mapping exists only in source segment: {link[0]} -> {link[1]}.")
    for link in sorted(requirement_links - source_links):
        errors.append(f"One-way mapping exists only in requirement: {link[1]} -> {link[0]}.")

    authority = data.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be an object.")
        authority = {}
    for field in ("allowed", "prohibited", "violations"):
        if field not in authority or not _nonempty_strings(authority.get(field)):
            errors.append(f"authority.{field} must be an array of non-empty strings.")
    if authority.get("violations"):
        errors.append("Authority violations prevent an accepted completion claim.")

    for field in ("scopeDrift", "missingIds", "duplicateIds", "regressionFailures"):
        value = data.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} must be an array.")
        elif value:
            errors.append(f"{field} must be empty for an accepted completion claim.")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be an array.")
        blockers = []
    blocked_ids: set[str] = set()
    for index, blocker in enumerate(blockers):
        if not isinstance(blocker, dict):
            errors.append(f"blocker #{index + 1} must be an object.")
            continue
        if blocker.get("type") not in {"OWNER", "CAPABILITY"}:
            errors.append(f"blocker #{index + 1} has unsupported type.")
        ids = blocker.get("requirementIds")
        if not isinstance(ids, list) or not ids:
            errors.append(f"blocker #{index + 1} must identify requirements.")
            ids = []
        blocked_ids.update(item for item in ids if isinstance(item, str))
        for field in ("reason", "resumeCondition", "nextAction"):
            if not isinstance(blocker.get(field), str) or not blocker[field].strip():
                errors.append(f"blocker #{index + 1} lacks {field}.")
        if blocker.get("independentWorkComplete") is not True:
            errors.append(f"blocker #{index + 1} must confirm independent work is complete.")

    claim = data.get("completionClaim")
    if claim not in ACCEPTED_CLAIMS:
        errors.append("completionClaim is unsupported or incomplete.")
    mandatory_nonpass = [item for item in mandatory if item.get("status") != "PASS"]
    if claim == "TASK_FULLY_VERIFIED":
        if mandatory_nonpass:
            errors.append("TASK_FULLY_VERIFIED requires every mandatory requirement to PASS.")
        if blockers:
            errors.append("TASK_FULLY_VERIFIED cannot retain blockers.")
    elif claim == "AUDIT_COMPLETE":
        if data.get("taskType") != "AUDIT_ONLY":
            errors.append("AUDIT_COMPLETE requires taskType AUDIT_ONLY.")
        if mandatory_nonpass:
            errors.append("AUDIT_COMPLETE requires every mandatory audit deliverable to PASS.")
    elif claim == "ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE":
        unresolved_ids = {item.get("id") for item in mandatory_nonpass}
        if not unresolved_ids:
            errors.append("Use TASK_FULLY_VERIFIED when no mandatory blocker remains.")
        if any(item.get("status") not in {"BLOCKED_OWNER", "BLOCKED_CAPABILITY"} for item in mandatory_nonpass):
            errors.append("All unresolved mandatory requirements must be genuinely blocked.")
        if blocked_ids != unresolved_ids:
            errors.append("Blocker records must cover exactly the unresolved mandatory requirements.")

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
    mandatory = [item for item in data.get("requirements", []) if isinstance(item, dict) and item.get("mandatory") is True]
    passed = sum(item.get("status") == "PASS" for item in mandatory)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"COMPLETION_MANIFEST status=FAIL mandatory={len(mandatory)} pass={passed} errors={len(errors)}")
        return 2

    print(f"COMPLETION_MANIFEST status=PASS claim={data['completionClaim']} mandatory={len(mandatory)} pass={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
