# Token Budget

Use this only when optimizing a council run. Token savings must not remove blockers, dissent, verification, confidence, anonymization, or Bob's non-voting status.

## Profiles

| Profile | Use | Cap |
| --- | --- | --- |
| compact | default, normal decisions | tight outputs, smallest reference set |
| balanced | blockers, ambiguity, non-trivial tradeoffs | more detail only on risks |
| expanded | security, data loss, migrations, irreversible work | full evidence and audit trail |

Escalate profile, not every stage. A compact run may still expand one blocker.

## Per-Agent Caps

- Member: 90 words compact, 140 balanced, blocker-only expansion. Seymour may spend the extra words only on performance blockers or measurements.
- Reviewer: 120 words compact, 180 balanced.
- Leonardo: 120 words unless UX is blocked.
- Bob: one compact evidence record per browser case; summarize DOM/screenshot artifacts by path.
- Chairman: 8-14 bullets by default.
- If more room is required, say which blocker needs expansion.

## Context Pruning

Include:

- decision/request
- relevant files or diff
- hard constraints
- tests/verification expected

Exclude:

- full transcripts unless requested
- unrelated docs
- repeated role descriptions
- previous candidates once summarized
- Bob browser transcripts when pass/fail evidence summary is enough
- session stats unless the user requests a closing report

## Cache-Friendly Shape

Keep stable text first and variable context last:

1. council role contract
2. output schema
3. rubric
4. project-specific context

This mirrors OpenAI prompt-caching guidance: exact static prefixes improve cache hits, while dynamic user/project context should come later.

## Reference Loading

Load the smallest reference set that can preserve correctness. Do not force "one file only" when a frontend or governance run needs multiple contracts.

- Standard architecture: `execution-protocol.md`, `roles-and-rubrics.md`.
- Performance-sensitive: add `roles-and-rubrics.md` only; Seymour and the performance reviewer are already in the core protocol.
- Frontend: add `frontend-ux-browser.md`.
- Formal final: add `output-contract.md`.
- Distribution/privacy: add `governance-preflight.md` and `method-source-notes.md`.

## No-Regression Rules

- Never remove blocker reporting.
- Never remove dissent.
- Never skip verification.
- Never let conciseness outrank accuracy.
- Never skip anonymization before candidate comparison.
- Never let missing candidate scores pass as valid coverage.
- Escalate to Deep mode when security, data loss, migration, or irreversible decisions are involved.
- Never treat Bob as a voting council member.
- Never claim UI behavior is verified unless Bob or equivalent browser evidence actually ran.

## Source-Grounded Tactics

- Static instructions first, variable context last for cache-friendly prefixes.
- Reduce output tokens first: shorter answers usually reduce cost and latency without weakening evidence if blockers are preserved.
- Use lower reasoning/effort only for low-risk Fast mode; raise effort/profile for blockers and irreversible work.
- Use structured outputs and concise schemas when traceability matters.
- Use `stats --session <dir>` for closing metrics instead of pasting transcripts; report only estimated artifact tokens and local counts.
