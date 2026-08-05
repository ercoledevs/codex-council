# Plain arm — independent verdict

Status: **FAIL**

The candidate's seven included tests and syntax check passed, but the verifier
reproduced contract gaps outside that suite.

## Counterexamples

1. When a worker ignores the supplied `AbortSignal`, a timed-out attempt can
   continue physically while a retry begins. The original phrase “never run
   more than `concurrency` workers at once” was therefore not satisfied under
   the strict physical interpretation.
2. Option validation accepted a duck-typed signal object rather than requiring
   an actual `AbortSignal`.
3. Timer cleanup and unhandled-rejection safety were not independently
   established and remained `UNKNOWN`.
4. The changed public contract was not documented in the README.

The control arm was frozen after this verdict. No repair pass was applied.

## What did pass

- baseline compatibility cases covered by the candidate;
- stable result ordering in the included concurrency test;
- included retry, timeout, caller-abort, and validation cases;
- `npm test`: 7/7;
- `node --check src/scheduler.js`.
