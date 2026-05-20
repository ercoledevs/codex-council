# Token Budget

Use this only when optimizing a council run.

## Defaults

- Prefer Standard mode for meaningful decisions: five compact members, local Chairman review.
- Use Deep mode only for high-risk decisions or explicit user request.
- Load only one reference at a time.
- Keep dynamic project context after stable council instructions.
- Ask members for deltas, blockers, and verification, not essays.

## Per-Agent Caps

- Member answer: max 90 words, max 3 bullets per section.
- Reviewer answer: max 120 words per reviewer.
- Chairman answer: 8-14 bullets by default.
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

## Cache-Friendly Shape

Keep stable text first and variable context last:

1. council role contract
2. output schema
3. rubric
4. project-specific context

## No-Regression Rules

- Never remove blocker reporting.
- Never remove dissent.
- Never skip verification.
- Never let conciseness outrank accuracy.
- Escalate to Deep mode when security, data loss, migration, or irreversible decisions are involved.
