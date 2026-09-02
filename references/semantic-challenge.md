# Semantic Challenge

Use this pass after implementation evidence is assembled and before an accepted STANDARD or STRICT completion claim. Its purpose is to find defects that a schema validator cannot see.

## Reviewer isolation

Prefer `INDEPENDENT_AGENT`: a fresh reviewer receives the original source documents, the discovered artifact inventory, and access to current evidence. Do not provide the builder's PASS labels, suspected defect list, or proposed conclusion until the reviewer has produced its own obligation and authority inventories.

If no separate reviewer is available, use `ADVERSARIAL_SECOND_PASS`. Reread the original source and current artifacts from the beginning, reconstruct obligations without copying the existing requirement titles, and record the independence limitation. This is a fallback, not independent acceptance.

## Required challenge passes

1. `SOURCE_OMISSION`: Independently enumerate every normative source span. Compare that inventory with the manifest in both directions. Challenge segments labeled context or example when they contain action verbs, hard boundaries, counts, order, status tokens, or acceptance conditions.
2. `AUTHORITY_OMISSION`: Independently identify which artifacts and external states can define or contradict the result. Check that every discovered authoritative or target artifact is inspected, or explicitly excluded with a defensible reason and current identity.
3. `SEMANTIC_CLASSIFICATION`: Spot-check names, ownership, actor, object, polarity, dates, counts, scope, and lifecycle state. A mapped sentence is not covered if its meaning moved to the wrong requirement or owner.
4. `CONTRADICTION`: Search current sources for stale but presently worded claims, conflicting authorities, runtime contradictions, and tests that prove a narrower statement than the final claim.
5. `FINAL_RESPONSE_ALIGNMENT`: Review the proposed final response separately. Every completion statement, count, test result, external-state claim, and limitation must be supported by current evidence. Record the reviewed completion claim and mandatory PASS/total counts. Remove or narrow claims that exceed them.

## Failure behavior

Record concrete findings without softening them into suggestions. Map each finding to affected requirement and artifact IDs. `IN_SCOPE_REQUIRED_FIX`, `REGRESSION`, and other authorized retryable findings return to diagnose, fix, direct verification, and affected regression checks. Re-run the semantic challenge after the change.

Only genuine Owner or capability gates may remain. Complete independent work first and use the blocked completion claim; never convert a semantic review limitation into a false PASS.

## Known-failure replay

When the task or project has a prior false-completion example, replay at least one relevant example as a regression probe. Ask whether the revised process would now detect the original omission, wrong ownership, stale authority, or overbroad final claim. Preserve the smallest non-private regression fixture when practical; do not copy private task content into the skill repository.
