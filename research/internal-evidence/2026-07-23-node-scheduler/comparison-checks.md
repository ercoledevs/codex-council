# Normalized final-check excerpts

These blocks preserve the command, named test cases, totals, and observed
result. They are not byte-for-byte process stdout: timing lines were omitted,
and original exit-code telemetry was not retained.

## Plain arm

Command:

```sh
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```

Result:

```text
> bounded-job-scheduler@0.1.0 test
> node --test

✔ runs jobs in input order
✔ captures worker failures without stopping later jobs
✔ validates arguments
✔ bounds concurrency and preserves result order
✔ retries failed and timed-out attempts and handles late rejection
✔ caller abort stops launches and rejects queued jobs
✔ invalid options fail before workers start
tests 7
pass 7
fail 0
```

The independent verifier still returned `FAIL`; green candidate tests alone did
not close the contract.

## Hyper arm

Command:

```sh
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```

Result:

```text
> bounded-job-scheduler@0.1.0 test
> node --test

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

Timing lines were intentionally omitted because process-level test duration is
not an end-to-end workflow duration and would be misleading.

## Published patch replay

Both `normal.patch` and `hyper.patch` were replayed into fresh copies of the
frozen baseline with `git apply --check` followed by `git apply`. The candidate
test suites then passed 7/7 and 13/13 respectively.

## Published evidence verification · 2026-07-24

The repository evidence test copied the shipped baseline into fresh temporary
directories, verified task/baseline SHA-256 values, ran `git apply --check`,
applied both patches, reran each candidate test suite, and checked
`src/scheduler.js` syntax. The test exited successfully:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_docs.DocsTests.test_evidence_lab_records_are_replayable_and_honest
```

This fresh replay validates the published code outcomes. It does not reconstruct
the unavailable agent transcripts.
