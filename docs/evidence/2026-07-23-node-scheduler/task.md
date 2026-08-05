# Final accepted task

Evolve `runJobs(jobs, worker)` into a bounded, retry-aware scheduler while
preserving its default behavior and result order.

## Required behavior

- Keep `runJobs(jobs, worker)` backwards compatible. Omitting the options
  argument preserves the legacy sequential loop and two-argument worker call.
- Accept an optional third argument with `concurrency`, `maxRetries`,
  `timeoutMs`, and `signal`.
- Reject invalid options, including `null` numeric values, before any worker
  starts.
- Never run more than `concurrency` scheduler-controlled logical attempts at
  once.
- Preserve result ordering by input index even when jobs finish out of order.
- Retry a failed or timed-out job at most `maxRetries` times.
- Pass `{ attempt, signal }` as a third worker argument when options are used;
  `attempt` starts at 1.
- A per-attempt timeout aborts that attempt and releases its logical slot.
- Once the caller signal aborts, launch no new jobs. Active attempts receive an
  aborted signal and every not-started job gets a deterministic rejected result.
- Workers using timeout or cancellation must cooperate with the supplied
  `AbortSignal`. JavaScript cannot forcibly terminate physical work that ignores
  it, so aborted attempts may continue outside the scheduler after their logical
  slot is released.
- Consume late settlement so timers and unhandled rejections do not leak.
- Use no dependencies. Add deterministic tests with `node:test`.

## Verification

```sh
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```
