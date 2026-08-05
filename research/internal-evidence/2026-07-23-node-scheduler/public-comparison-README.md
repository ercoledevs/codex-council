# Node scheduler case study

This local case study was captured on 2026-07-23. Its code outcomes are
replayable from the shipped baseline and patches. It compares a plain
single-pass implementation arm with a Codex Hyper Relay run on the same frozen
Node.js baseline.

It is not a speed test or proof that one workflow is generally superior. The
plain arm was frozen after its first implementation and independent review.
Hyper was allowed to use its designed investigate, implement, falsify, and
repair loop. That makes this a case study, not an apples-to-apples model
benchmark.

Workflow provenance is **PARTIAL**. Raw agent transcripts, the three
intermediate failed-falsifier transcripts, and exact failed-verifier command
logs were not retained. The recorded four-pass count comes from the
orchestration record and is not independently replayable. See `provenance.md`.

## Frozen source

- Plugin: `codex-council`
- Local plugin version: `1.0.0+codex.20260716085645`
- Source commit: `95732dd3bbd5e440dbaa448aae94e59ce9c21473`
- Source worktree: dirty; pre-existing local changes were preserved
- Hyper skill SHA-256:
  `2f766a1417db401887ff4f9aeb3eb0565d4ad847ff45470cca626446d6087f2e`
- Runtime-reported model and token usage: unavailable
- Network and third-party dependencies: none
- Exact dirty worktree snapshot: unavailable; hashes for the Hyper instruction
  files used by the run are recorded in `manifest.json`

The baseline contained one scheduler module, one test file, and three passing
tests. Checksums are recorded in `manifest.json`.

The frozen fixture's internal README says “benchmark”; that was its original
project name. This evidence record uses it only as a case-study fixture and
does not claim a controlled or statistical benchmark.

## Exact task

The initial prompt is preserved in `task.md`. It asked for bounded concurrency,
ordered results, retries, per-attempt timeout, caller cancellation, strict
validation, timer and rejection safety, no dependencies, and deterministic
`node:test` coverage.

Cold verification exposed an ambiguity that JavaScript cannot solve for an
arbitrary worker: code that ignores its `AbortSignal` cannot be forcibly
terminated. The revised contract in `task-v2.md` makes the scheduler's logical
concurrency boundary and the worker's cooperative-cancellation duty explicit.
The revision is part of the evidence, not hidden post-processing.

## Plain arm

Topology: one implementation agent with Council, Forge, Mind, and Hyper
disabled, followed by one read-only verifier.

- Candidate tests: 7/7 passed
- Syntax check: passed
- Diff: 2 files, +305/-11
- Independent verdict: failed

The verifier reproduced two contract gaps:

1. a timed-out worker that ignored cancellation could continue physically while
   the retry began;
2. signal validation accepted a duck-typed object instead of an actual
   `AbortSignal`.

Timer cleanup and unhandled-rejection safety were not independently
established and remained `UNKNOWN`. The implementation also left the new public
behavior undocumented. Per the control protocol, the arm was frozen and not
repaired.

## Hyper arm

Recorded route: Relay. One root writer integrated bounded read-only
investigation and cold falsification. The orchestration record reports four
verifier passes before closure; raw intermediate transcripts were not retained.

- Candidate tests: 13/13 passed under
  `NODE_OPTIONS=--unhandled-rejections=strict`
- Syntax check: passed
- Diff: 3 files, +482/-11
- Final independent verdict: completed against the revised contract

The falsification loop found and repaired:

- hostile, non-coercible rejection values;
- the legacy two-argument callback and dynamic-array behavior;
- `null` accepted as an option default;
- timeout and abort tie behavior;
- incomplete documentation of cooperative cancellation.

Residual risk is explicit: a JavaScript worker that ignores its aborted signal
may continue physical work after its logical scheduler slot is released. Late
settlement is consumed to prevent unhandled rejections.

## Reproduce

Copy the shipped `baseline/` directory, apply either sibling patch, then run:

```sh
cp -R baseline /tmp/node-scheduler-replay
cd /tmp/node-scheduler-replay
git apply --check /path/to/normal.patch
git apply /path/to/normal.patch
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```

Files:

- `baseline/`: the exact replay input
- `normal.patch`: the frozen plain arm
- `hyper.patch`: the completed Hyper arm
- `normal-verifier.md`: independent counterexample
- `hyper-verifier.md`: final independent gate
- `checks.md`: normalized final-check excerpts; not byte-for-byte stdout
- `manifest.json`: provenance, checksums, and known unknowns
- `provenance.md`: captured and unavailable workflow evidence
