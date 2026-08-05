# Task

Evolve `runJobs(jobs, worker)` into a bounded, retry-aware scheduler while
preserving its default behavior and result order.

## Required behavior

- Keep `runJobs(jobs, worker)` backwards compatible.
- Accept an optional third argument with `concurrency`, `maxRetries`,
  `timeoutMs`, and `signal`.
- Never run more than `concurrency` workers at once.
- Preserve result ordering by input index even when jobs finish out of order.
- Retry a failed or timed-out job at most `maxRetries` times.
- Pass `{ attempt, signal }` as a third worker argument; `attempt` starts at 1.
- A per-attempt timeout must abort that attempt and release its slot.
- Once the caller signal aborts, launch no new jobs; active attempts receive an
  aborted signal and every not-started job gets a deterministic rejected result.
- Invalid options fail before any worker starts.
- Do not leak timers or unhandled rejections.
- Use no dependencies. Add deterministic tests using `node:test`.

## Verification

Run `npm test`.
