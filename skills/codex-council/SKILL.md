---
name: codex-council
description: Use for Codex Council review, multi-agent judgment, performance/frontend review, or offline Decision Runtime projection and replay.
---

# Codex Council

Codex-only council: independent opinions, anonymous ranking, optional browser evidence, separate synthesis. No external model APIs.

## Non-Negotiables

- Preserve blockers, dissent, verification, confidence, Candidate A-F review.
- Use rubric scoring, not popularity, persona prestige, or verbosity.
- State that Codex role diversity is not true multi-provider model diversity.
- Bob is never a council member, candidate, or voter.
- Never claim UI behavior is verified without Bob or equivalent browser evidence.
- Use historical persona names; local tuning stays advisory.
- Never spawn council agents without the mandatory preflight gate and user acceptance.
- Close completed member agents after outputs; max open agents: six.
- Never run `expanded` without explicit confirmation; prefer compact escalation per blocker.
- Classify natural-language council mentions; meta/unclear asks one line, no dispatch.
- Decision Runtime is opt-in, shadow-only, legacy-authoritative, and fail-closed; never claim unmeasured savings.

## Preflight Gate - Mandatory

Before Standard/Deep/Expanded:

1. Estimate mode, counts, evidence, and range.
2. Show the preflight estimate and ask acceptance.
3. Wait for confirmation before dispatch.
4. Treat "use Codex Council" as request, not cost acceptance.
5. Block `expanded` unless the user explicitly confirms expanded.

Proposal-only defaults Fast unless Standard is accepted. Router shortcuts are opt-in; hard risk forces full.

## Token Router

Default `compact`; escalate only the risky part.

| Need | Action |
| --- | --- |
| small reversible decision | Fast Chairman review |
| implementation/architecture/performance decision | Standard six-member council |
| security, data loss, migration, irreversible, close tie | Deep reviewers |
| frontend/UI/UX/browser behavior | add `--frontend-review` |
| plugin/skill usability review | add `--type skill` or `--skill-review` |
| customize member behavior | use `codex-council-alters`, no council dispatch |
| audit trail | scaffold session with CLI |
| project/replay completed evidence | Decision Runtime, no council dispatch |

First profile: ask plan, model, reasoning, budget; store with consent.

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
Sessions use plugin-local `.codex-council/sessions`; `doctor`/`dashboard` inspect health. Frontend uses `--frontend-review`.
For chat, paste the ASCII banner in chat before dispatch. Do not rely on hidden shell stdout. At close, persist prompts/outputs before `stats --session <dir>`. Report pre/post; artifact-only stays separate. Missing data means `coverage: partial`. Relay stats in chat. Never claim billing tokens.

## Reference Loading

Load the smallest reference set:

- `references/execution-protocol.md`: stages and lifecycle.
- `references/roles-and-rubrics.md`: lenses and scoring.
- `references/token-budget.md`: caps and pruning.
- `references/frontend-ux-browser.md`: Leonardo/Bob.
- `references/workflow-recipes.md`: task routing.
- `references/output-contract.md`: formal report.
- `references/competency-packs.md`: internal packs.
- `references/governance-preflight.md`: privacy/provenance/distribution.
- `references/method-source-notes.md`: source grounding.
- `references/decision-runtime.md`: shadow projection, patch, recovery, replay.

## Minimal Flow

1. Snapshot request, constraints, diff, tests.
2. Run preflight, show range, ask acceptance; gate `expanded`.
3. Print the compact ASCII banner in chat for visible council starts.
4. Disclose active local role tuning, if any, before dispatch.
5. Dispatch six first-opinion agents only when explicitly requested.
6. Collect outputs, close member agents, keep blockers/verification.
7. Strip identities, label Candidate A-F, review/rank with rubric.
8. For frontend, run Leonardo after anonymization and Bob before synthesis.
9. Aggregate reviewer JSON with the CLI when present.
10. Synthesize from saved artifacts. Persist compact artifacts and Relay stats in chat.

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
