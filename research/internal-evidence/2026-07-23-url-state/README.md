# URL state case study

This local case study records implementation and source-level verification for
a dependency-free incident board. The required browser gate has not run
because Playwright requires explicit user approval. The case therefore remains
**INCOMPLETE** and every browser-only claim is **UNKNOWN**.

It is published to show that missing evidence stays visible—not to imply a
completed or superior workflow.

The shipped baseline and patches make the code outcomes replayable. Workflow
provenance is **PARTIAL**: raw agent/explorer transcripts and exact pre-repair
probe logs were not retained. See `provenance.md`.

## Frozen source

- Plugin: `codex-council`
- Local plugin version: `1.0.0+codex.20260716085645`
- Source commit: `95732dd3bbd5e440dbaa448aae94e59ce9c21473`
- Source worktree: dirty; pre-existing local changes were preserved
- Captured on: 2026-07-23
- Runtime-reported model, token usage, and workflow duration: unavailable
- Application dependencies: none
- Browser harness: Playwright, development-only, not executed
- Exact dirty worktree snapshot: unavailable; hashes for the Hyper instruction
  files used by the run are recorded in `manifest.json`

## Task

Persist query and status filters in a canonical URL, restore state through
browser history, keep reset and announcements accessible, render incident data
without unsafe HTML insertion, and prove desktop/mobile behavior in a real
browser.

The exact prompt is in `task.md`.

## What ran

Both candidates completed dependency-free codec tests and syntax checks.

| Gate | Plain arm | Hyper arm |
| --- | --- | --- |
| Codec tests | PASS · 4/4 | PASS · 4/4 |
| JS syntax | PASS | PASS |
| Static unsafe-HTML scan | PASS | PASS |
| URL-state source review | PASS | PASS after repair |
| Browser script present | PASS | PASS |
| Browser script executed | UNKNOWN | UNKNOWN |
| Keyboard, history, focus, console, overflow | UNKNOWN | UNKNOWN |

The live orchestration record says Hyper's cold source verifier reproduced two
defects before the repair:

1. a whitespace-only query was encoded as `query=+++`;
2. `popstate` recovered invalid status controls but did not canonicalize the
   shareable URL.

Both defects were patched. A final source-only verifier summary records a pass
for the corrected codec and popstate probes. Raw intermediate probe transcripts
were not retained, and browser behavior was deliberately not promoted to PASS.

## Reproduce source checks

```sh
npm test
node --check app.js
node --check state-codec.js
```

The browser gate remains pending. Do not describe this case as complete until
the saved browser scripts run against a local HTTP server and the evidence
record is updated.

`checks.md` contains normalized check excerpts, not byte-for-byte process
stdout. Copy `baseline/`, apply `normal.patch` or `hyper.patch`, and rerun the
commands above to verify the published code outcome.
