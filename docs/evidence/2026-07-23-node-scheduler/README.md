# Completed Codex Hyper scheduler run

This is one successful local case study captured on 2026-07-23 and replayed on
2026-07-24. Codex Hyper implemented a bounded Node.js scheduler on a frozen
baseline, then closed only after its required checks and fresh-verifier gate
passed.

This is not a benchmark or a general quality claim.

## Product snapshot

- Plugin: `codex-council`
- Historical local build identifier: `1.0.0+codex.20260716085645`
- Source commit: `95732dd3bbd5e440dbaa448aae94e59ce9c21473`
- Source worktree: dirty; unrelated local changes were preserved
- Hyper workflow: bundled Codex Council skill, Relay route
- Runtime model, token usage, and end-to-end duration: unavailable
- Scheduler runtime dependencies: none

## Final contract

The exact accepted task is in `task.md`. It required:

- bounded logical concurrency and ordered results;
- retries and per-attempt timeouts;
- caller cancellation with real `AbortSignal` validation;
- compatibility with the legacy two-argument callback and dynamic job array;
- deterministic `node:test` coverage;
- explicit documentation of cooperative cancellation.

JavaScript cannot forcibly terminate a worker that ignores its aborted signal.
The final contract states that boundary directly instead of claiming physical
cancellation the runtime cannot guarantee.

## Completed outcome

- Route: Hyper Relay
- Files changed: 3
- Diff: +482 / -11
- Candidate tests: 13/13 PASS
- Test mode: `NODE_OPTIONS=--unhandled-rejections=strict`
- JavaScript syntax: PASS
- Fresh-verifier gate: PASS against the final contract
- Published patch replay: PASS on 2026-07-24

The completed implementation covers hostile rejection values, late settlement,
legacy callback behavior, dynamic job arrays, invalid `null` options, and
abort/timeout ties.

Residual risk remains explicit: a worker that ignores its `AbortSignal` may
continue physical work after its logical scheduler slot is released. Late
settlement is consumed to prevent unhandled rejections.

## Replay

Copy the shipped baseline, apply the patch, and run:

```sh
cp -R baseline /tmp/codex-hyper-scheduler
cd /tmp/codex-hyper-scheduler
git apply --check /path/to/hyper.patch
git apply /path/to/hyper.patch
NODE_OPTIONS=--unhandled-rejections=strict npm test
node --check src/scheduler.js
```

## Evidence files

- `baseline/`: exact replay input
- `task.md`: accepted final contract
- `hyper.patch`: completed implementation
- `checks.md`: final-check and replay record
- `hyper-verifier.md`: fresh-verifier verdict
- `manifest.json`: hashes, status, and known limits
- `provenance.md`: what was and was not captured
