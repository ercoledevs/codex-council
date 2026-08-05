# Routing policy

## Solo gate

Choose Solo only when every statement is true:

- The implementation path is clear after initial inspection.
- The task is localized to one tightly coupled responsibility, regardless of
  raw file count.
- The change is reversible and has a low blast radius.
- It does not alter a public contract, persistent data, authentication,
  authorization, concurrency, build, deployment, or external state.
- A deterministic and relevant verification method exists.
- Parallel investigation or independent verification would not materially
  shorten the critical path or reduce meaningful risk.

An explicit `$codex-council:codex-hyper` invocation on a small task may still use Solo. Hyper
does not imply fan-out.

## Relay gate

Choose Relay when any statement is true:

- Root cause or implementation path is uncertain.
- Architecture, dependencies, tests, or impact can be investigated
  independently.
- Multiple modules or contracts must remain aligned.
- Regression, performance, privacy, security, concurrency, data, build, or
  deployment risk is non-trivial.
- A cold reviewer could find materially different evidence.
- The task arrived as an approved Codex Mind implementation handoff.

## Explorer selection

Start with one explorer. Add a second only when it answers a separate question,
such as:

- architecture and dependency path
- current tests and regression surface
- performance or concurrency behavior
- security or data boundary, when no stricter security workflow owns the task

Do not delegate two agents to broadly “investigate the bug.” Give each a bounded
question, source scope, read-only contract, output schema, and stop condition.

## Escalation and fallback

- Escalate Solo to Relay when inspection reveals uncertainty or hidden impact.
- Fall back to Solo when threads are unavailable or agent coordination stops
  producing new evidence.
- Stop for user direction when new scope or authority would materially change
  the requested result.
- Route explicit vulnerability-fix workflows through the appropriate Codex
  Security skill rather than duplicating its gates.

Do not introduce Mesh or parallel writers until isolated-worktree behavior and
paired benchmarks demonstrate a safe advantage.
