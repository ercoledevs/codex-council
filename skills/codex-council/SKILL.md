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

Choose one effort: `simple` for a bounded question, `mid` (default) for architecture, `ultra` for a full challenge. The CLI selects the panel and budget. Hard risks raise Council coverage before estimation. Inspect the actual panel. Risk matching is heuristic. For a known hard risk the router missed, choose ultra, add frontend review when relevant, and re-estimate before dispatch. Treat "use Codex Council" as request, not cost acceptance.

1. Resolve material ambiguity with the [adaptive interview](references/architecture-interview.md). Members send the lead questions; the lead groups independent decisions, gives a recommendation, and waits only on affected branches.
2. Show the preflight estimate, panel and risk overrides. Get acceptance before dispatch. Legacy expanded runs need explicit confirmation.
3. Scaffold the accepted configuration. For chat, paste the ASCII banner in chat. Do not rely on hidden shell stdout.

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --effort mid
python3 <plugin-root>/scripts/codex_council.py init --topic "<topic>" --effort mid --confirm-estimate
```

Use `--type architecture|implementation|decision|skill|frontend` and optionally the same settled `--brief` for both commands. For UI evidence use frontend review. For role tuning use Alters. For post-run projection use Decision Runtime. Offer profile calibration only when relevant; store with consent.

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
5. Dispatch only the roles in the accepted panel. Use host-sized waves.
6. Collect outputs, close member agents, keep blockers/verification.
7. Strip identities and assign letters to actual candidates only. A solo opinion has no peer ranking.
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
