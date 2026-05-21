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

Mode: Standard.

Packs: Implementation Strategist, Operator UX Reviewer, Governance And Audit Officer.

Prompt: "Council review this plugin change for packaging, usability, provenance, and validation."

## Frontend Or UX Review

Mode: Standard with `--frontend-review`; Deep if the change affects checkout, auth, payments, permissions, destructive actions, accessibility-critical flows, or production release.

Optional reviewer: Leonardo da Vinci - Brutally Honest UX/UI Critic.

Evidence runner: Bob - Browser Customer Tester, only when a runnable app, prototype, or local route exists.

Packs: Operator UX Reviewer, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council frontend review this change. Activate Leonardo for brutal UX/UI critique and have Bob verify council-supplied browser cases before Chairman synthesis."

## Release Or Completion Gate

Mode: Deep for irreversible, migration, security, or data-loss risk.

Packs: Test And Regression Sentinel, Governance And Audit Officer.

Prompt: "Deep Council: review release readiness, blockers, verification evidence, and rollback signals."

## Jury Go/No-Go

Mode: Standard unless security, migration, data loss, or compliance is involved, then Deep.

Packs: Governance And Audit Officer, Test And Regression Sentinel, Contrarian Simplifier.

Prompt: "Council jury: give a go/no-go decision, required blockers, dissent, confidence, and exact verification before approval."

## Token-Sensitive Review

Mode: Fast or Standard compact.

Packs: Token And Context Optimizer, Contrarian Simplifier.

Prompt: "Council review this using compact output. Preserve blockers, dissent, and verification."
