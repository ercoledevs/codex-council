# Execution contracts

## Mission Contract

```text
Outcome:
Done when:
In scope:
Out of scope:
Constraints:
Baseline and unknowns:
Risk and rollback:
Verification:
Route and rationale:
```

## Explorer contract

```text
Read-only question:
Allowed scope:
Do not edit files or external state.
Return:
- claims
- file:line or command evidence
- confidence and uncertainty
- blockers
- the smallest next discriminating check
```

Do not ask for a solution unless proposal generation is the explorer's bounded
question. Explorers should return evidence, not long narratives.

## Evidence record

```text
claim | source or command | result | confidence | unresolved
```

Keep the record compact and task-local. Evidence becomes stale when the base
commit, relevant file, environment, or verification input changes.

## Verifier contract

```text
You are a fresh read-only verifier.
Inputs: Mission Contract, raw diff/changed files, raw check results, constraints.
Do not edit files. Do not trust builder intent or agent consensus.
Try to falsify completion with reproducible evidence.
Return each acceptance criterion as PASS, FAIL, or UNKNOWN, then list:
- counterexamples
- regressions or unsafe scope changes
- missing or irrelevant tests
- residual risk
- exact next check
```

## Mind-to-Hyper handoff

```text
Council Final Call: build
Live blockers: none
Implementation authorization: explicit
Approved proposal:
Immutable constraints:
Acceptance criteria:
Verification criteria:
Non-blocking dissent and residual risks:
```

Reject the handoff if any required field is absent, the approved scope changed,
or a live blocker exists. Return a compact reason instead of silently filling
the gap.

## Completion evidence

```text
Route:
Outcome:
Changed surfaces:
Done-when evidence:
Checks and results:
Verifier result:
Rollback:
Residual risks:
Unverified:
```
