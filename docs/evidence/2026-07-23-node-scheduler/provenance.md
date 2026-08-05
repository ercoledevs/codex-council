# Provenance scope

## Outcome replay

Status: **PASS**

The published baseline, final task, patch, checksums, and commands are enough to
apply the completed code outcome again and rerun its test suite.

## Workflow provenance

Status: **PARTIAL**

Captured:

- frozen baseline and SHA-256 checksums;
- accepted final task;
- completed Hyper patch;
- final check summary and command exit codes;
- final fresh-verifier summary;
- plugin commit/version and hashes of the Hyper instruction files.

Unavailable:

- raw implementation-agent and explorer transcripts;
- raw intermediate verifier transcripts;
- runtime model identifier;
- token usage;
- end-to-end duration;
- raw command stdout/stderr;
- a complete archive of the dirty plugin worktree.

The code outcome is replayable. The full orchestration conversation is not.
