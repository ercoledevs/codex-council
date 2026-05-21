# Output Contract

Use this structure for Codex Council final synthesis.

## Required Sections

- Recommendation: direct decision or blocked state.
- Council Result: winner/synthesis, confidence, reason, material dissent, ties.
- Blocking Issues: must-fix items before approval.
- Refinements: useful non-blocking improvements.
- Implementation Shape: touched files/modules, ownership, migration, errors, observability. For non-code: policy, rejected alternatives, rollout, owner.
- Verification: exact tests, commands, manual QA, security review, rollback signal.
- Audit Notes: sources, assumptions, unresolved questions, transcript/score path.
- Frontend Evidence: when active, summarize Leonardo UX blockers/refinements separately from Bob browser-observed pass/fail/not-verified cases.

## Style

- Lead with the decision.
- Keep dissent visible.
- Separate blockers from refinements.
- Separate UX judgment from browser evidence.
- Avoid theatrical certainty.
- Do not report raw subagent transcripts unless the user asks.
