# Workflow Recipes

Use this only when choosing how Codex Council should combine roles or internal competency packs.

## Architecture Decision

Mode: Standard.

Packs: Implementation Strategist, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council review this architecture decision. Preserve dissent and give implementation verification."

## Bug Or Regression

Mode: Fast unless root cause is unclear, then Standard.

Packs: Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council review this bugfix plan for root-cause evidence and regression risk."

## Plugin Or Skill Change

Mode: `--type skill --skill-review` for focused skill/tool usability. Use Standard when architecture, security, packaging, or performance risk needs the full six-member council.

Packs: Implementation Strategist, Operator UX Reviewer, Governance And Audit Officer, Performance Impact Analyst.

Prompt: "Council review this plugin change for packaging, usability, provenance, performance impact, and validation."

Skill-review lenses: skill engineer, UX-for-tools, non-expert adoption.

## Performance-Sensitive Change

Mode: Standard. Deep if performance risk can cause outage, timeout, data backlog, cost blowup, missed SLA, or user-visible latency/jank.

Packs: Performance Impact Analyst, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council review this change for latency, throughput, memory, cost, scaling limits, benchmark evidence, and safer performance alternatives."

## Frontend Or UX Review

Mode: Standard with `--type frontend` or `--frontend-review`; Deep if the change affects checkout, auth, payments, permissions, destructive actions, accessibility-critical flows, or production release.

Optional reviewer: Leonardo da Vinci - Brutally Honest UX/UI Critic.

Evidence runner: Bob - Browser Customer Tester, only when a runnable app, prototype, or local route exists.

Packs: Operator UX Reviewer, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council frontend review this change. Activate Leonardo for brutal UX/UI critique and have Bob verify council-supplied browser cases before Chairman synthesis."

## Release Or Completion Gate

Mode: Deep for irreversible, migration, security, or data-loss risk.

Packs: Test And Regression Sentinel, Governance And Audit Officer.

Prompt: "Deep Council: review release readiness, blockers, verification evidence, and rollback signals."

## Jury Go/No-Go

Mode: Standard with `--type decision` unless security, migration, data loss, or compliance is involved, then Deep.

Packs: Governance And Audit Officer, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council jury: give a go/no-go decision, required blockers, dissent, confidence, and exact verification before approval."

## Token-Sensitive Review

Mode: Fast or Standard compact.

Packs: Token And Context Optimizer, Contrarian Simplifier.

Prompt: "Council review this using compact output. Preserve blockers, dissent, and verification."

Before dispatch, run a preflight estimate and ask acceptance. If the local consumer profile is missing, ask plan, typical model, reasoning effort, and optional self-declared 5-hour/weekly budget.

## Session Closeout Stats

Mode: Any scaffolded session.

Prompt: "Generate Codex Council session stats. Compare pre_execution_estimate and post_execution_estimate, keep artifact_only_tokens separate, and do not imply actual Codex token usage."

Use `--record-history` after the session only when the user consented to local learning history.

Use `--raw-bundle` only for audit handoff; it writes relative artifact paths, not raw transcripts.
