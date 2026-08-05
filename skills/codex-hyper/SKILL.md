---
name: codex-hyper
description: Orchestrate implementation of complex repository code changes with adaptive Solo/Relay routing, bounded read-only subagent investigation, single-writer ownership, independent falsification, and evidence-backed completion. Use when Codex is asked to build, fix, or refactor code and the task has an uncertain root cause, spans independently inspectable modules, changes a public, data, concurrency, build, or deployment contract, or otherwise benefits from independent verification. Do not use for read-only explanation or review, small mechanical edits, routine documentation, external-service operations, security workflows governed by Codex Security, or workflows governed end-to-end by a stricter domain skill unless that skill delegates implementation.
---

# Codex Hyper

Optimize for time to validated code, not time to the first patch. Use the
smallest agent topology that can materially shorten the critical path or reduce
risk.

## Non-negotiables

- Treat Codex Hyper as a bundled Codex Council skill. Never instruct the user to
  install, copy, or maintain Hyper as a standalone skill. Its canonical invocation
  is `$codex-council:codex-hyper`.
- Preserve system, developer, user, repository, sandbox, and approval rules.
- Keep the root agent as the only global writer and integrator. Make explorers
  and verifiers read-only.
- Inspect repository instructions and Git status before editing. Preserve all
  pre-existing user changes.
- Treat subagent role diversity as correlated evidence, not independent truth.
- Decide disagreements through files, commands, tests, and reproducible
  counterexamples rather than majority vote.
- Keep secrets, credentials, tokens, PII, and unnecessary raw logs out of
  prompts and handoffs.
- Never claim a check passed unless it actually ran. Mark each required check
  `PASS`, `FAIL`, or `UNKNOWN`.
- Do not invoke Codex Mind, Forge, or Council recursively. A stricter domain or
  security skill keeps authority over its workflow.
- Do not broaden authorization. A request to analyze, review, or plan does not
  authorize implementation.

## Select the route

Read [routing policy](references/routing-policy.md) when the route is not
obvious.

Choose **Solo** only when all Solo gates pass. Otherwise choose **Relay**.

| Route | Shape | Default use |
| --- | --- | --- |
| Solo | root inspects, writes, tests, and reviews | localized, low-risk, tightly coupled change with a clear oracle |
| Relay | bounded read-only explorers -> root writer -> fresh read-only verifier | uncertain, cross-module, contract-sensitive, or independently verifiable change |

Do not use parallel writers in version 1. Start Relay with one explorer; add a
second only for an independent question or surface. Respect the live thread cap
and degrade safely to Solo when agents are unavailable.

## Stage 0: Contract

Build a compact Mission Contract before editing:

- outcome and observable `done when`
- in-scope and out-of-scope surfaces
- repository and user constraints
- known baseline and uncertainties
- risk and rollback shape
- required verification or oracle
- selected route and why it is justified

Keep the contract in the active plan or context. Do not create a repository
artifact unless the task or repository workflow requires one.

For Relay or an upstream approved proposal, read
[execution contracts](references/execution-contracts.md).

## Stage 1: Observe

1. Read applicable `AGENTS.md`, project guidance, relevant code, tests, and
   configuration.
2. Inspect the worktree before edits and identify overlap with user changes.
3. Establish the smallest safe baseline check when practical. Record any
   pre-existing failure instead of claiming the change caused it.
4. In Relay, dispatch one or two independent read-only explorer questions.
   Require concise claims with `file:line`, commands, uncertainty, and blockers.
5. Keep noisy logs in subagent threads. Bring only decision-relevant evidence
   into the main context.

## Stage 2: Orient

1. Validate critical explorer claims against source artifacts.
2. Map dependencies and the critical path. Use a small DAG only when ordering
   is genuinely non-trivial.
3. Bind each acceptance criterion to a verification method.
4. Reserve every write surface for the root agent. Subagents may propose a
   change, but must not apply it.
5. Prefer the smallest reversible implementation. Escalate risk or request new
   authority before changing public APIs, data, permissions, dependencies, or
   external state outside the approved scope.

## Stage 3: Act

1. Implement the critical path in small, reviewable patches.
2. Use TDD when behavior has a reliable oracle, characterization tests for
   legacy behavior, and a time-boxed spike when the oracle is still unknown.
3. Run focused checks after meaningful increments instead of postponing all
   feedback to the end.
4. Stop or fall back to a narrower route on stale context, overlapping user
   edits, unexplained baseline failures, approval denial, repeated agent
   duplication, or coordination cost that exceeds useful work.

## Stage 4: Falsify

After implementation and root checks, run the falsification gate.

In Relay, give a fresh read-only verifier only:

- the Mission Contract
- the raw diff or exact changed files
- verification commands and raw results
- known constraints and unresolved risks

Do not give the verifier the builder's persuasive rationale. Ask it to find a
reproducible counterexample, missing acceptance criterion, regression, unsafe
scope change, or untested edge case.

In Solo, the root runs the same falsification checklist against the Mission
Contract, raw diff, and check results, and reports the reduced independent
coverage. If cold verification is required by the risk level, Solo is not
eligible; escalate to Relay or stop when a verifier is unavailable.

For every valid finding, fix it and rerun affected checks. If the change after
verification is material, run the applicable falsification gate again. A
critical `FAIL` or `UNKNOWN` blocks completion.

## Stage 5: Close

Before reporting completion:

1. Reconcile every `done when` item with evidence.
2. Run the relevant test, lint, type, build, or targeted runtime checks.
3. Review the final diff and worktree for unintended or unrelated changes.
4. Confirm rollback or reversibility when risk requires it.
5. Report outcome, route, changed surfaces, checks with results, unresolved
   risks, and anything not verified.

Do not turn a local estimate, agent agreement, or green but irrelevant test
into a correctness claim.

## Codex Mind handoff

Accept a Mind handoff only when it contains an approved proposal, immutable
constraints, acceptance criteria, verification criteria, non-blocking residual
risks, a Council Final Call of `build`, and no live blocker.

Require explicit implementation intent. If the verdict is `revise` or `stop`,
the scope changed after judgment, implementation was not authorized, or a
blocker remains, return control to Mind without editing.

Route every accepted Mind handoff through Relay so the approved scope receives
bounded read-only investigation and a fresh falsification verifier.

Mind may orchestrate Hyper, but Hyper owns implementation routing and
verification. Never reproduce Forge or Council inside Hyper.

## Evaluation

Read [evaluation protocol](references/evaluation-protocol.md) only when testing
or tuning this skill. Treat speed and quality improvements as hypotheses until
paired, repeated tasks establish them.

## Output

- Route: Solo or Relay, with the reason
- Outcome and changed surfaces
- Evidence mapped to `done when`
- Verification: `PASS`, `FAIL`, or `UNKNOWN` per required check
- Residual risk and rollback
- Blockers or unverified claims
