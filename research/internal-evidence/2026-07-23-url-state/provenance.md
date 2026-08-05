# Provenance scope

## Outcome replay

Status: **PASS for source checks; browser UNKNOWN**

The shipped baseline, task, patches, checksums, and candidate commands are
enough to apply each code outcome again and rerun the published codec and
syntax checks. Both patches pass `git apply --check` against `baseline/`.

## Workflow provenance

Status: **PARTIAL**

Captured:

- frozen baseline and SHA-256 checksums;
- exact task text;
- final patch for each arm;
- normalized final source-check excerpts;
- final verifier summaries;
- plugin commit/version plus hashes of the Hyper instruction files.

Not retained:

- raw implementation-agent responses;
- raw explorer responses;
- raw pre-repair verifier transcripts and exact probe commands;
- runtime model identifier, token usage, and end-to-end duration;
- a complete archive of the dirty plugin worktree.

The two pre-repair findings are records from the live orchestration. They cannot
be independently reconstructed from the final patch alone. No real-browser run
has executed, so hydration, history, keyboard, focus, console, and responsive
claims remain `UNKNOWN`.
