---
name: verified-completion-loop
description: Close out long, multi-step tasks by mapping the original request to requirements, verifying current evidence, and automatically completing retryable gaps within the existing scope and authority. Use when a substantial task is approaching final delivery, the user asks to finish everything or not stop until complete, or omission and drift risk is material. Do not use as heavy project management for ordinary short tasks or to remediate an audit-only request.
metadata:
  short-description: Finish and verify every authorized requirement
---

# Verified Completion Loop

Do not treat a completion report as completion. Before ending a substantial task, prove that every mandatory part of the user's request is covered by current evidence. If an authorized requirement is incomplete, continue the work instead of returning the gap to the user.

## Operating shape

Use a three-stage lifecycle:

1. **Start anchor:** Preserve every original user request and later change verbatim in the conversation or another authorized source, plus explicit constraints, prohibited actions, authority boundaries, and expected deliverables. Keep this lightweight.
2. **Dormant execution:** Let the primary workflow do the work. Refresh the anchor only when the user changes scope or authority, context is compacted, work resumes after interruption, or an Owner gate appears.
3. **Closeout loop:** When the task appears ready to finish, build the full requirement-to-evidence matrix, verify it, remediate authorized gaps, run affected regressions, and repeat until the completion gate passes or only genuine blockers remain.

If invoked only at closeout, reconstruct the anchor from the original user messages and later changes. Never substitute an executor summary, plan, or prior closeout for the source request.

## Choose proportional depth

- **LIGHT:** Short, reversible, low-risk work. Preserve full requirement coverage; use concise direct checks.
- **STANDARD:** Multi-step or multi-file work. Use numbered requirements, targeted tests, relevant regression checks, and repository state.
- **STRICT:** Production, providers, payments, migrations, destructive operations, governance, long prompts, or high omission risk. Add prospective identities, before/after state, independent acceptance when available, and current external evidence.

Depth changes evidence cost, never coverage, safety, or truthfulness. Upgrade automatically when risk increases. Do not downgrade a user-requested level.

## Freeze requirements without losing the source

Create contiguous source-document, source-segment, and requirement IDs. Preserve both directions:

```text
S-001 -> R-001, R-002
R-001 -> S-001
R-002 -> S-001
```

Treat each original user message or authorized source as a complete source document. Partition the entire document into non-overlapping, gap-free source segments; do not select only the sentences that are convenient to implement. Every segment must be classified as `REQUIREMENT`, `CONSTRAINT`, `PROHIBITION`, `DELIVERABLE`, `CONTEXT`, or `EXAMPLE`. The first four require at least one mapped requirement. Context and examples may map to none.

Every requirement must map back to source segments, unless it is a necessary derived step with an explicit rationale. Preserve later additions, clarifications, replacements, and revocations; mark superseded requirements instead of deleting them. Detect and resolve:

- unmapped source requirements;
- orphan or duplicate requirements;
- silently dropped constraints or prohibitions;
- contradictory requirements;
- missing or non-contiguous source, segment, and requirement IDs;
- later user additions, replacements, and revocations without preserved history;
- output formats, counts, ordering, final status tokens, allowed files, and forbidden actions.

Do not rewrite a hard requirement to match the implementation. Do not inflate the denominator with speculative work.

## Keep authority separate from requirements

Requirements define the result. Authority defines permitted means. Ground each allowed or prohibited action in source authority or an explicit necessary-step rationale. For STANDARD and STRICT closeout, record every material observed mutation and the allowed action that authorized it. Record reads, writes, external actions, destructive actions, providers, production access, secrets, spending, communication, merge, and release boundaries as applicable.

Before each remediation action, confirm that it is:

1. necessary for an original requirement;
2. within the frozen scope;
3. already authorized;
4. below any additional safety or Owner gate.

Completion pressure never grants authority. Do not bypass a gate with direct database writes, synthetic substitutes presented as production proof, fabricated events, hidden scope changes, or lowered acceptance criteria.

## Build the completion matrix

Use these execution states:

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
VERIFYING
PASS
FAIL_RETRYABLE
BLOCKED_OWNER
BLOCKED_CAPABILITY
DEFERRED_BY_SCOPE
SUPERSEDED
```

`IMPLEMENTED` is not `PASS`. Define direct, current evidence and a pass condition for every effective mandatory requirement before claiming it complete. Evidence must include a capture time and reproducible provenance such as a command, artifact identity, or authoritative source. It may include file identity, tests, runtime behavior, screenshots, Git state, PR state, provider state, or Owner acceptance, depending on the requirement.

Historical evidence is context, not proof of current state. Tests do not override contradictory source or runtime evidence.

## Continue instead of stopping at findings

For every `FAIL_RETRYABLE`, `NOT_STARTED`, or otherwise executable gap:

1. diagnose the cause;
2. select a new in-scope strategy;
3. implement the smallest complete fix;
4. run the requirement's direct verification;
5. rerun affected previously passing requirements;
6. update evidence and repeat.

Do not end with an audit report when the task authorizes implementation. A finding is input to the remediation loop.

Do not busy-loop. A retry must add new evidence, diagnosis, strategy, or relevant external-state change. Treat a condition as blocked only after safe in-scope alternatives are exhausted according to the host's blocker policy.

## Batch genuine gates

A gate blocks only requirements that depend on it. Continue every independent authorized requirement first. Stop only when no safe executable requirement remains.

For each remaining blocker record:

- affected requirement IDs;
- exact missing decision, permission, capability, or external change;
- attempts and alternatives already exhausted;
- resume condition;
- exact next action;
- confirmation that independent authorized work is complete.

Do not ask the Owner to perform ordinary implementation, testing, Git, or cleanup work that remains authorized and executable.

## Respect the original task type

- **Change/build:** Remediate authorized failures until verified.
- **Audit-only or read-only:** Complete the audit; do not mutate the audited target. A defect in the target can coexist with a fully completed audit.
- **Diagnose-only:** Prove the cause; do not implement unless separately authorized.
- **Answer/explain:** Verify factual coverage; do not invent external writes.
- **Monitor/wait:** Continue through the authorized monitoring mechanism; unchanged state is not failure.

## Final completion gate

Before the final response, require all of the following:

```text
source coverage complete
every source document fully partitioned without gaps or overlaps
mandatory requirements accounted for exactly once
all effective mandatory requirements PASS
no missing or duplicate IDs
no unresolved retryable work
no authority violation
no scope drift
no relevant regression failure
current, timestamped, reproducible evidence supports every PASS
```

Only then claim `TASK_FULLY_VERIFIED`.

If all independent authorized work is complete and only proven Owner/capability blockers remain, use `ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE` and report the blockers precisely. Never call the whole task complete.

For audit-only work, use `AUDIT_COMPLETE` when every audit deliverable passes, regardless of whether the audited subject has defects.

For STANDARD or STRICT work, read [references/protocol.md](references/protocol.md). Use the V2 machine-readable manifest when the source can be stored safely in a temporary or task-authorized local location, then run:

```text
python scripts/validate_manifest.py <manifest.json>
```

Remove temporary manifests at closeout unless the user or project requires durable state. Never upload a task manifest. If source messages contain secrets or private content that must not be written to disk, perform the same complete span review in memory and state that machine manifest validation was intentionally not used; never replace it with a redacted manifest presented as full coverage.
