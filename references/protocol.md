# Completion Protocol V2

Read this reference for STANDARD and STRICT closeout work.

## 1. Preserve the complete source

Use each original user message and every later addition, clarification, replacement, or revocation as an ordered source document. Do not build the matrix from an executor summary, plan, issue title, or prior closeout.

Assign contiguous IDs:

```text
D-001, D-002, ...  source documents
S-001, S-002, ...  source segments
R-001, R-002, ...  requirements
```

Partition every character of every source document into ordered, non-overlapping, gap-free source segments. This is the control that prevents an omitted paragraph from disappearing before requirement counting begins.

Classify every segment:

- `REQUIREMENT`: a result the task must achieve;
- `CONSTRAINT`: a limit on how or where work is performed;
- `PROHIBITION`: an action that must not occur;
- `DELIVERABLE`: required output, format, count, order, or final state;
- `CONTEXT`: background that does not independently require work;
- `EXAMPLE`: illustrative material unless the wording makes it normative.

The first four classifications require at least one mapped requirement. Context and examples may map to none, but they must still occupy their source span.

## 2. Preserve change history

Every segment records one change type:

```text
INITIAL
ADD
CLARIFY
REPLACE
REVOKE
NONE
```

`REPLACE` and `REVOKE` segments identify the requirements they affect. Do not delete the old requirement. Preserve it with:

```json
{
  "effective": false,
  "status": "SUPERSEDED",
  "supersededBySourceIds": ["S-006"]
}
```

The replacement receives a new contiguous requirement ID. Final completion counts only effective mandatory requirements, while the full history remains auditable.

## 3. Run bidirectional coverage

Require both mappings:

```text
S-001 -> R-001, R-002
R-001 -> S-001
R-002 -> S-001
```

Reject:

- an unsegmented source range;
- an unmapped normative segment;
- a requirement without source segments or a necessary-step rationale;
- a one-way mapping;
- duplicate or non-contiguous IDs;
- a declared expected-ID inventory that differs from actual records;
- a replacement or revocation that erases history.

A necessary derived requirement may omit source IDs only when `derivedNecessary` is true and `rationale` explains why it is required to complete or verify a source-backed requirement.

## 4. Keep authority independent

Desired completion does not grant the means to reach it. Record:

- `allowed`: actions grounded in source authority or an explicit necessary-step rationale;
- `prohibited`: boundaries grounded the same way;
- `observedActions`: material mutations performed and the allowed action authorizing each one;
- `violations`: any proven authority breach.

Use contiguous IDs:

```text
A-001  allowed action
P-001  prohibited action
X-001  observed material action
```

An accepted claim requires zero authority violations. Do not silently infer provider, production, payment, secret, destructive, merge, release, or external-communication authority from a broad completion request.

## 5. Require current evidence

A `PASS` requires at least one evidence record containing:

```json
{
  "kind": "test",
  "summary": "The focused suite exits 0",
  "fresh": true,
  "capturedAt": "2026-09-01T00:00:00Z",
  "command": "python -m unittest"
}
```

Evidence must have a valid capture time and at least one reproducible provenance field:

- `command`;
- `artifactIdentity`;
- `source`.

Historical evidence is context, not current proof. A test does not override contradictory source, runtime, provider, Git, or Owner evidence.

STANDARD and STRICT claims require regression-check evidence. STRICT claims also require explicit before/after records. A STRICT before/after record states whether a subject was expected to change and verifies the corresponding identities.

## 6. Remediate instead of reporting retryable gaps

Classify findings:

- `IN_SCOPE_REQUIRED_FIX`
- `BLOCKER_TO_REQUIREMENT`
- `REGRESSION`
- `DEBT`
- `OUT_OF_SCOPE`
- `OWNER_DECISION_REQUIRED`

The first three automatically enter the current remediation queue when the task authorizes implementation.

For each retryable gap:

1. diagnose the cause;
2. select a materially new in-scope strategy;
3. implement the smallest complete fix;
4. run direct verification;
5. rerun affected passing requirements;
6. update current evidence;
7. repeat.

A retry must add evidence, diagnosis, strategy, or relevant external-state change. Repeating the same failed command is not progress.

## 7. Prove genuine blockers

A blocker record requires:

```json
{
  "type": "OWNER",
  "requirementIds": ["R-014"],
  "reason": "Production migration approval is absent",
  "attempts": ["Checked the current request and authority ledger"],
  "alternativesExhausted": ["Preview evidence cannot prove production state"],
  "resumeCondition": "Owner authorizes or rejects the production migration",
  "nextAction": "Execute the authorized decision",
  "independentWorkComplete": true
}
```

Use `CAPABILITY` when the missing condition is a tool, service, runtime, or external-state change rather than a decision. A gate blocks only dependent requirements; complete every independent authorized requirement first.

## 8. Respect task type

- `CHANGE`: remediate authorized gaps until verified.
- `AUDIT_ONLY`: complete every audit deliverable without mutating the audited target.
- `DIAGNOSE_ONLY`: prove the cause without implementation.
- `ANSWER`: cover and verify the requested answer without external mutation.
- `MONITOR`: use the authorized monitoring mechanism; unchanged state is expected.

The subject of an audit may fail while the audit itself reaches `AUDIT_COMPLETE`.

## 9. V2 manifest shape

The validator accepts a JSON object with these sections:

```json
{
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
      "content": "Update the parser and run its tests.",
      "sha256": "a636a2341131c348462847567634363646127e2c87a3ff56c22ee5930ccf32a0"
    }
  ],
  "sourceSegments": [
    {
      "id": "S-001",
      "documentId": "D-001",
      "start": 0,
      "end": 36,
      "classification": "REQUIREMENT",
      "changeType": "INITIAL",
      "requirementIds": ["R-001"],
      "affectedRequirementIds": []
    }
  ],
  "requirements": [
    {
      "id": "R-001",
      "title": "Update and verify the parser",
      "sourceIds": ["S-001"],
      "derivedNecessary": false,
      "rationale": "",
      "mandatory": true,
      "effective": true,
      "supersededBySourceIds": [],
      "status": "PASS",
      "evidence": [
        {
          "kind": "test",
          "summary": "Parser tests exit 0",
          "fresh": true,
          "capturedAt": "2026-09-01T00:00:00Z",
          "command": "python -m unittest"
        }
      ]
    }
  ],
  "authority": {
    "allowed": [
      {
        "id": "A-001",
        "action": "edit parser files",
        "basisSourceIds": ["S-001"],
        "derivedNecessary": false,
        "rationale": ""
      }
    ],
    "prohibited": [],
    "observedActions": [
      {"id": "X-001", "action": "edited parser files", "allowedBy": "A-001"}
    ],
    "violations": []
  },
  "scopeDrift": [],
  "missingIds": [],
  "duplicateIds": [],
  "regressionChecks": [
    {
      "kind": "test",
      "summary": "Relevant regressions exit 0",
      "fresh": true,
      "capturedAt": "2026-09-01T00:00:00Z",
      "command": "python -m unittest"
    }
  ],
  "regressionFailures": [],
  "beforeAfter": [],
  "blockers": [],
  "completionClaim": "TASK_FULLY_VERIFIED"
}
```

Calculate `sourceDocuments[].sha256` from the exact UTF-8 content. Ranges use zero-based Python string offsets, and the segments for each document must cover `0..len(content)` exactly.

## 10. Privacy rule

The full-source manifest is optional because source text may be sensitive.

- Use it only in a temporary or explicitly authorized local location.
- Never upload it with the skill, a PR, logs, or a closeout report.
- Delete the temporary manifest after validation unless durable storage is explicitly required.
- If the source contains secrets or private content that must not be written to disk, perform the same complete span review in memory and disclose that machine manifest validation was intentionally not used.
- Never validate a redacted or partial source and present it as complete coverage.

## 11. Completion claims

- `TASK_FULLY_VERIFIED`: every effective mandatory requirement is `PASS`; source coverage, authority, regression, and level-specific checks pass; no blocker remains.
- `AUDIT_COMPLETE`: task type is `AUDIT_ONLY` and every effective mandatory audit deliverable is `PASS`.
- `ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE`: all unresolved effective mandatory requirements are `BLOCKED_OWNER` or `BLOCKED_CAPABILITY`; complete blocker records cover exactly those requirements; no executable independent work remains.

The validator proves manifest structure and claim eligibility. It cannot determine whether a sentence was semantically misclassified or whether an evidence statement is truthful; the closeout agent must independently inspect current reality.

## 12. Final response

Lead with the terminal state. Report:

- effective mandatory pass count and total;
- superseded requirement count when relevant;
- unresolved IDs;
- direct verification and regressions;
- preserved authority boundaries;
- exact blockers and resume conditions;
- anything intentionally not verified.

Do not say the whole task is complete when the accepted state is only `ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE`.
