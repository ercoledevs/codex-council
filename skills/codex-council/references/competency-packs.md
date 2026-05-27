# Competency Packs

Use these internal packs when the user does not want external skills.

## Implementation Strategist

Use for architecture-to-plan decisions.

Focus: sequencing, ownership, migration path, smallest useful scope.

Output: implementation order, files/modules, risks, verification.

## Test And Regression Sentinel

Use when correctness or regressions matter.

Focus: missing tests, edge cases, rollback, smoke checks.

Output: blocking regression risks, required tests, minimal verification.

## Performance Impact Analyst

Use when latency, throughput, memory, CPU, I/O, database/query cost, cache behavior, startup/build time, concurrency, token/runtime cost, or scalability can change the decision.

Focus: performance claims, workload assumptions, baseline vs change, measurement gaps, degradation under contention.

Output: performance impact, blocker threshold, required benchmark or profiling evidence.

## Token And Context Optimizer

Use when the run may get expensive or verbose.

Focus: mode choice, loaded references, context pruning, output caps.

Output: token-saving choices and no-regression guardrails.

## Governance And Audit Officer

Use for privacy, provenance, permissions, and distribution decisions.

Focus: sensitive data, license status, audit trail, redaction.

Output: preflight risks, required audit fields, approval blockers.

## Operator UX Reviewer

Use when adoption or day-to-day workflow matters.

Focus: trigger clarity, default prompts, concise final output.

Output: operator friction, clearer wording, workflow recipes.

## Frontend UX Critic

Use when frontend, layout, navigation, accessibility, responsive behavior, copy, or interaction design matters.

Focus: counterintuitive flows, hidden affordances, weak visual hierarchy, mobile failure, decorative bloat, and unclear task paths.

Output: UX verdict, smallest required refinement, Bob browser scenarios.

## Contrarian Simplifier

Use to reduce scope.

Focus: what not to build, cheaper alternatives, hidden assumptions.

Output: rejected scope, simpler option, invalidation conditions.
