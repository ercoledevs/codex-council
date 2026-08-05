# Completed run checks

## Final implementation gate

Command:

```sh
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```

Retained result summary:

```text
✔ runs jobs in input order
✔ captures worker failures without stopping later jobs
✔ validates arguments
✔ omitting options preserves the two-argument callback shape
✔ omitting options preserves the legacy dynamic array loop
✔ bounds concurrency and preserves input order
✔ retries failures with one-based attempts and fresh signals
✔ timeout aborts an attempt, releases the lane, and consumes late failure
✔ caller aborts active attempts and prevents new launches
✔ a pre-aborted signal starts no workers
✔ worker-triggered caller abort wins over a synchronous throw
✔ invalid options reject before a worker starts
✔ non-coercible rejection reasons settle without an unhandled rejection
tests 13
pass 13
fail 0
```

Exit codes:

- strict `npm test`: `0`
- `node --check src/scheduler.js`: `0`

The raw command stdout/stderr was not retained; the block above is a normalized
summary of the named tests and totals. Timing lines were also omitted because
process test duration is not end-to-end workflow duration.

## Published patch replay · 2026-07-24

The repository evidence test:

1. copied the published baseline into a fresh temporary directory;
2. verified task, patch, verifier, and baseline SHA-256 values;
3. ran `git apply --check`;
4. applied `hyper.patch`;
5. reran the 13 tests under strict unhandled-rejection mode;
6. checked `src/scheduler.js` syntax.

Result: PASS.

Replay exit codes were `0` for `git apply --check`, `git apply`, strict
`npm test`, and `node --check src/scheduler.js`. This validates the published
code outcome. It does not reconstruct unavailable agent transcripts or raw
command output.
