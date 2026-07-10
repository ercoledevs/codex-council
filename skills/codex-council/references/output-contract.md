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

- Session Stats: include only when requested or closing a scaffolded session. Show pre-execution estimate, post-execution estimate, artifact-only tokens, delta, ratio, calibration, and coverage. Never present them as billing-token telemetry.
- Preflight Estimate: include before dispatch, not at the end. Label it as local heuristic range and ask user acceptance. For `expanded`, require explicit confirmation.
- Raw Output Bundle: optional audit artifact with relative paths only; do not paste raw transcripts unless explicitly requested.
- Decision Runtime Evidence: when explicitly requested, report representation
  compared, corpus/repetitions, determinism, blocker/dissent/verification recall,
  impact-plan fallback, runtime state, quarantine/recovery, and measured overhead.
  Keep local estimates separate from billing telemetry and unmeasured claims.

## Style

- Lead with the decision.
- Keep dissent visible.
- Treat Chairman output as a separate synthesis pass over saved artifacts.
- Separate blockers from refinements.
- Separate measured performance evidence from unverified performance claims.
- Separate UX judgment from browser evidence.
- Separate artifact-only tokens from full-session pre/post execution estimates.
- Mark post estimates `coverage: partial` when prompts or outputs are missing.
- Avoid theatrical certainty.
- Do not report raw subagent transcripts unless the user asks.
