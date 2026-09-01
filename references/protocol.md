# Completion Protocol

Read this reference for STANDARD and STRICT closeout work.

## 1. Source ledger

Preserve the original request and every later change as stable source segments. Record whether a later segment adds, replaces, narrows, revokes, or clarifies earlier requirements. Do not erase history when the effective requirement changes.

Classifications:

- `REQUIREMENT`: a result the task must achieve;
- `CONSTRAINT`: a limit on how or where work is performed;
- `PROHIBITION`: an action that must not occur;
- `DELIVERABLE`: required output, format, or final state;
- `CONTEXT`: background that does not independently require work;
- `EXAMPLE`: illustrative material unless the wording makes it normative.

Run a bidirectional coverage review:

1. Every normative source segment maps to one or more requirements.
2. Every source-backed requirement maps to every relevant source segment.
3. A derived requirement has no source mapping only when it is necessary to complete or verify a source-backed requirement and includes a rationale.
4. No requirement is duplicated under different wording.
5. Prohibitions and output constraints are represented, not left in prose outside the matrix.

## 2. Requirement record

Each requirement should contain:

```json
{
  "id": "R-001",
  "title": "Preserve the target file",
  "sourceIds": ["S-003"],
  "derivedNecessary": false,
  "rationale": "",
  "mandatory": true,
  "status": "PASS",
  "evidence": [
    {
      "kind": "file-identity",
      "summary": "Before and after SHA-256 match",
      "fresh": true
    }
  ]
}
```

Use direct evidence proportional to the claim. Record what was actually observed, not what the implementation should theoretically do.

## 3. Authority manifest

Keep authorization independent of completion status:

```json
{
  "allowed": ["read workspace", "edit admitted files", "run local tests"],
  "prohibited": ["production writes", "secret access", "merge without approval"],
  "violations": []
}
```

An empty violation list is required for any accepted completion claim. If an action needs new authority, do not execute it merely because it would close a requirement.

## 4. Remediation queue

Prioritize unresolved requirements by dependency, safety, and how many downstream checks they unblock. A remediation unit should close a source-backed requirement or a necessary blocker, not create a speculative side project.

Classify new findings:

- `IN_SCOPE_REQUIRED_FIX`
- `BLOCKER_TO_REQUIREMENT`
- `REGRESSION`
- `DEBT`
- `OUT_OF_SCOPE`
- `OWNER_DECISION_REQUIRED`

Only the first three automatically enter the current remediation loop.

After a fix, rerun its direct verification and every passing requirement materially affected by the change. In STRICT mode, perform a final full-matrix recheck from current evidence.

## 5. Blockers

A blocker record requires:

```json
{
  "type": "OWNER",
  "requirementIds": ["R-014"],
  "reason": "Production migration approval is absent",
  "resumeCondition": "Owner authorizes or rejects the production migration",
  "nextAction": "Execute the approved migration plan or close the requirement as rejected",
  "independentWorkComplete": true
}
```

Use `CAPABILITY` instead of `OWNER` when the missing condition is an unavailable tool, service, runtime, or external-state change rather than a decision.

Do not mark a requirement blocked because it is difficult, slow, failed once, or would benefit from clarification that can be safely inferred from current evidence.

## 6. Machine-readable manifest

The optional validator accepts this shape:

```json
{
  "schemaVersion": 1,
  "level": "STANDARD",
  "taskType": "CHANGE",
  "sourceSegments": [
    {
      "id": "S-001",
      "text": "Update the parser and run its tests.",
      "classification": "REQUIREMENT",
      "requirementIds": ["R-001", "R-002"]
    }
  ],
  "requirements": [
    {
      "id": "R-001",
      "title": "Update the parser",
      "sourceIds": ["S-001"],
      "derivedNecessary": false,
      "rationale": "",
      "mandatory": true,
      "status": "PASS",
      "evidence": [
        {"kind": "diff", "summary": "Parser handles the new form", "fresh": true}
      ]
    },
    {
      "id": "R-002",
      "title": "Run parser tests",
      "sourceIds": ["S-001"],
      "derivedNecessary": false,
      "rationale": "",
      "mandatory": true,
      "status": "PASS",
      "evidence": [
        {"kind": "test", "summary": "Parser suite exits 0", "fresh": true}
      ]
    }
  ],
  "authority": {
    "allowed": ["edit parser files", "run local tests"],
    "prohibited": ["deploy to production"],
    "violations": []
  },
  "scopeDrift": [],
  "missingIds": [],
  "duplicateIds": [],
  "regressionFailures": [],
  "blockers": [],
  "completionClaim": "TASK_FULLY_VERIFIED"
}
```

Accepted claims:

- `TASK_FULLY_VERIFIED`: every mandatory requirement is `PASS` and no blocker remains;
- `AUDIT_COMPLETE`: task type is `AUDIT_ONLY` and every mandatory audit deliverable is `PASS`;
- `ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE`: all unresolved mandatory requirements are `BLOCKED_OWNER` or `BLOCKED_CAPABILITY`, each is covered by a complete blocker record, and no executable work remains.

The validator checks structural integrity and claim eligibility. It cannot prove that evidence statements are true; the agent must inspect current reality.

## 7. Final response

Lead with the actual terminal state. Report:

- completed mandatory count and total;
- unresolved requirement IDs, if any;
- direct verification performed;
- regressions checked;
- authority boundaries preserved;
- exact blockers and resume conditions;
- what was not verified.

Do not say “complete” when the accepted state is only `ALL_AUTHORIZED_INDEPENDENT_WORK_COMPLETE`.
