---
name: codex-council
description: Use when the user asks for Codex Council, council review, multi-agent deliberation, architecture decision review, implementation judgment, frontend/UI/UX council review, or a 5-member Codex agent council.
---

# Codex Council

Token-efficient Codex adaptation of `karpathy/llm-council`: independent first opinions, anonymous peer review/ranking, optional browser evidence, then Chairman synthesis. No external model APIs.

## Non-Negotiables

- Preserve blockers, dissent, verification, confidence, and anonymized Candidate A-E review.
- Use rubric scoring, not popularity, persona prestige, or verbosity.
- State that Codex role diversity is not true multi-provider model diversity.
- Bob is never a council member, candidate, or voter.
- Never claim UI behavior is verified without Bob or equivalent browser evidence.
- Use historical persona names in prompts/status; UI nicknames are incidental.

## Token Router

Default profile is `compact`. Escalate only when risk requires it.

| Need | Action |
| --- | --- |
| small reversible decision | Fast local Chairman review |
| meaningful implementation/architecture decision | Standard five-member council |
| security, data loss, migration, irreversible, close tie | Deep reviewers |
| frontend/UI/UX/browser behavior | add `--frontend-review` |
| audit trail needed | scaffold session with the CLI |

Session scaffold:

```bash
python3 <plugin-root>/scripts/codex_council.py init --topic "<topic>" --root <workspace> --mode standard --token-budget compact
```

Add `--frontend-review` only for frontend, UX, accessibility, browser behavior, overlays, or user-facing interaction work.

## Reference Loading

Load the smallest reference set that can answer the task:

- `references/execution-protocol.md`: stage order and dispatch shape.
- `references/roles-and-rubrics.md`: role lenses, reviewer rubric, scoring JSON.
- `references/token-budget.md`: profiles, caps, pruning, cache-friendly prompt shape.
- `references/frontend-ux-browser.md`: Leonardo/Bob frontend gate.
- `references/workflow-recipes.md`: mode selection by task type.
- `references/output-contract.md`: formal final report.
- `references/competency-packs.md`: internal packs when external skills are not desired.
- `references/governance-preflight.md`: privacy/provenance/distribution checks.
- `references/method-source-notes.md`: attribution/source grounding.

## Minimal Flow

1. Snapshot only relevant context: request, constraints, changed files/diff, expected tests.
2. Dispatch five first-opinion agents only when council review is explicitly requested.
3. Start each dispatch prompt with `You are <persona> - <role> for Codex Council`.
4. Compress member outputs, but keep concrete blockers and verification details.
5. Strip identities, label Candidate A-E, review/rank with rubric.
6. If frontend gate is active, run Leonardo after anonymization and Bob before synthesis when a runnable UI exists.
7. Aggregate with `scripts/codex_council.py score` when reviewer JSON exists.
8. Chairman synthesizes recommendation, confidence, blockers/refinements, dissent, and verification.

## Core Personas

- Ada Lovelace - Principal Architect
- Grace Hopper - Reliability Engineer
- Hypatia - Security and Governance Reviewer
- Florence Nightingale - Product and Operator Advocate
- Alan Turing - Contrarian Red Team

Optional frontend gate:

- Leonardo da Vinci - Brutally Honest UX/UI Critic: reviewer/refinement gate.
- Bob - Browser Customer Tester: browser evidence runner only.

## Output Rule

Normal chat final: 8-14 bullets. Formal report: use `output-contract.md`. Expand only for blockers, evidence, or explicit user request.
