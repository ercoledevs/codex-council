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

## Release Or Completion Gate

Mode: Deep for irreversible, migration, security, or data-loss risk.

Packs: Test And Regression Sentinel, Governance And Audit Officer.

Prompt: "Deep Council: review release readiness, blockers, verification evidence, and rollback signals."

## Token-Sensitive Review

Mode: Fast or Standard compact.

Packs: Token And Context Optimizer, Contrarian Simplifier.

Prompt: "Council review this using compact output. Preserve blockers, dissent, and verification."
