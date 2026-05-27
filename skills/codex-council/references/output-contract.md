# Output Contract

Use this structure for Codex Council final synthesis.

## Required Sections

- Recommendation: direct decision or blocked state.
- Council Result: winner/synthesis, confidence, reason, material dissent, ties.
- Blocking Issues: must-fix items before approval.
- Refinements: useful non-blocking improvements.
- Implementation Shape: touched files/modules, ownership, migration, errors, observability. For non-code: policy, rejected alternatives, rollout, owner.
- Verification: exact tests, commands, manual QA, security review, rollback signal.
- Performance Impact: latency, throughput, memory, cost, scale assumptions, and required measurements when relevant.
- Audit Notes: sources, assumptions, unresolved questions, transcript/score path.
- Frontend Evidence: when active, summarize Leonardo UX blockers/refinements separately from Bob browser-observed pass/fail/not-verified cases.

## Optional Sections

- Session Stats: include only when requested or when a scaffolded session report is being closed. Label token numbers as estimated artifact tokens, not actual Codex usage or billing telemetry.

## Style

- Lead with the decision.
- Keep dissent visible.
- Separate blockers from refinements.
- Separate measured performance evidence from unverified performance claims.
- Separate UX judgment from browser evidence.
- Separate estimated session artifact tokens from real model/account usage.
- Avoid theatrical certainty.
- Do not report raw subagent transcripts unless the user asks.
