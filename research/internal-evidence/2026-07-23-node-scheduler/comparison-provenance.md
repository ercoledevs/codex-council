# Provenance scope

## Outcome replay

Status: **PASS**

The shipped baseline, exact task files, normalized patches, checksums, and final
candidate commands are enough to apply each code outcome again and rerun its
published test suite. `normal.patch` and `hyper.patch` both pass
`git apply --check` against `baseline/`.

## Workflow provenance

Status: **PARTIAL**

Captured:

- frozen baseline and SHA-256 checksums;
- initial and revised task text;
- final patch for each arm;
- normalized final-check excerpts;
- plain-arm verifier summary and final Hyper verifier summary;
- plugin commit/version plus hashes of the Hyper instruction files.

Not retained:

- raw implementation-agent responses;
- raw explorer responses;
- raw transcripts for the three failed Hyper falsification passes;
- exact command logs for the failed verifier probes;
- runtime model identifier, token usage, and end-to-end duration;
- a complete archive of the dirty plugin worktree.

Therefore the code outcome is replayable, but the full agent conversation and
four-pass orchestration history are not independently reproducible. The
four-pass count and repaired-issue list are disclosed as records from the live
orchestration, not as claims derivable from the published patch alone.
