# Evaluation protocol

Treat the claim “Hyper reaches validated code faster without losing quality” as
falsifiable.

## Comparison

Run paired, repeated tasks with the same repository state, model class,
permissions, requirements, and quality bar:

1. disciplined Codex without Hyper
2. Codex Hyper Solo
3. Codex Hyper Relay

Add naive multi-agent fan-out only as a diagnostic baseline. Do not make it the
control.

Stratify tasks across localized bugs, ambiguous bugs, multi-module features,
legacy refactors, public contracts, concurrency, build failures, and risky
changes. Keep hidden acceptance checks outside the agent context.

## Primary measures

- hidden acceptance success on the first completed attempt
- time to validated completion, including coordination and verification
- escaped defects and regressions
- lost or overwritten user changes
- human intervention and rollback success

## Efficiency measures

- spawn, queue, approval, merge, and verification time
- coordination and rework time
- token or credit cost when observable from an authoritative source
- duplicate investigation and cancelled work
- variance across repeated runs

## Ablations and failure injection

Remove or perturb one component at a time:

- routing policy
- explorer
- single-writer rule
- cold verifier
- evidence contract

Inject stale context, misleading tests, flaky failures, overlapping user edits,
approval denial, worker interruption, conflicting evidence, and an incorrect
summary.

## Decision rule

Pre-register the minimum quality and performance improvement that matters. Keep
Relay optional until it is non-inferior on correctness and safety and shows a
repeatable benefit on tasks that actually pass its routing gate.

If Solo or disciplined Codex dominates Relay, simplify the skill instead of
adding more orchestration.
