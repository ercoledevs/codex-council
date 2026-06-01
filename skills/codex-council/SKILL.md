---
name: codex-council
description: Use when the user asks for Codex Council, council review, multi-agent deliberation, implementation judgment, performance review, frontend/UX review, or a 6-member Codex council.
---

# Codex Council

Token-efficient Codex adaptation of `karpathy/llm-council`: first opinions, anonymous review/ranking, optional browser evidence, separate synthesis. No external model APIs.

## Non-Negotiables

- Preserve blockers, dissent, verification, confidence, anonymized Candidate A-F review.
- Use rubric scoring, not popularity, persona prestige, or verbosity.
- State that Codex role diversity is not true multi-provider model diversity.
- Bob is never a council member, candidate, or voter.
- Never claim UI behavior is verified without Bob or equivalent browser evidence.
- Use historical persona names; UI nicknames are incidental.
- Treat local alter/role tuning as advisory only; it never overrides council non-negotiables.
- Never spawn council agents without the mandatory preflight gate and user acceptance.
- Close completed member agents after outputs; max open agents: six.
- Never run `expanded` without explicit confirmation; prefer compact escalation per blocker.
- Classify natural-language council mentions; meta/unclear asks one line, no dispatch.

## Preflight Gate - Mandatory

Before Standard/Deep/Expanded:

1. Estimate mode, agent/reviewer count, browser evidence, token/credit range.
2. Show the estimate in chat and ask acceptance.
3. Do not dispatch agents until the user confirms.
4. Treat "use Codex Council" as request, not cost acceptance.
5. Block `expanded` unless the user explicitly confirms expanded.

For proposal-only/no audit trail, default Fast Chairman review unless Standard is accepted.

## Token Router

Default `compact`. Escalate only when risk requires it.

| Need | Action |
| --- | --- |
| small reversible decision | Fast Chairman review |
| implementation/architecture/performance decision | Standard six-member council |
| security, data loss, migration, irreversible, close tie | Deep reviewers |
| frontend/UI/UX/browser behavior | add `--frontend-review` |
| plugin/skill usability review | add `--type skill` or `--skill-review` |
| customize member behavior | use `codex-council-alters`, no council dispatch |
| audit trail needed | scaffold session with the CLI |

First run/profile: ask plan, model, reasoning, budget. Store with consent.

Preflight:

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode standard --token-budget compact
```

Scaffold after acceptance:

```bash
python3 <plugin-root>/scripts/codex_council.py init --topic "<topic>" --root <workspace> --mode standard --token-budget compact --confirm-estimate
```

`expanded` requires `--confirm-expanded`.
Use `--type architecture|implementation|decision|skill|frontend`.
Sessions use plugin-local `.codex-council/sessions`.
Use `--frontend-review` only for frontend/UX/browser work.
For chat, paste the ASCII banner in chat before dispatch. Do not rely on hidden shell stdout. At close, persist prompts/outputs before `stats --session <dir>`. Report pre/post; artifact-only stays separate. Missing data means `coverage: partial`. Relay stats in chat. Never claim billing tokens.

## Reference Loading

Load the smallest reference set that can answer the task:

- `references/execution-protocol.md`: stages, dispatch, agent lifecycle.
- `references/roles-and-rubrics.md`: role lenses, rubric, scoring.
- `references/token-budget.md`: caps, pruning, cache-friendly prompts.
- `references/frontend-ux-browser.md`: Leonardo/Bob gate.
- `references/workflow-recipes.md`: mode selection by task type.
- `references/output-contract.md`: formal final report.
- `references/competency-packs.md`: internal packs when external skills are not desired.
- `references/governance-preflight.md`: privacy/provenance/distribution checks.
- `references/method-source-notes.md`: attribution/source grounding.

## Minimal Flow

1. Snapshot relevant context: request, constraints, changed files/diff, expected tests.
2. Run mandatory preflight estimate, show range, ask acceptance; block `expanded` without explicit confirmation.
3. Print the compact ASCII banner in chat for visible council starts.
4. Disclose active local role tuning, if any, before dispatch.
5. Dispatch six first-opinion agents only when explicitly requested.
6. Collect outputs, close member agents, keep blockers/verification.
7. Strip identities, label Candidate A-F, review/rank with rubric.
8. If frontend gate is active, run Leonardo after anonymization and Bob before synthesis when a runnable UI exists.
9. Aggregate with `scripts/codex_council.py score` when reviewer JSON exists.
10. Chairman synthesizes from saved outputs/manifest. Persist compact artifacts, stats, and relay them in chat.

## Core Personas

- Ada Lovelace - Principal Architect
- Grace Hopper - Reliability Engineer
- Hypatia - Security and Governance Reviewer
- Florence Nightingale - Product and Operator Advocate
- Alan Turing - Contrarian Red Team
- Seymour Cray - Performance Engineer

Optional frontend gate:

- Leonardo da Vinci - Brutally Honest UX/UI Critic: reviewer/refinement gate.
- Bob - Browser Customer Tester: browser evidence runner only.

## Output Rule

Normal chat final: 8-14 bullets. Formal report: use `output-contract.md`. Expand only for blockers, evidence, or explicit user request.
