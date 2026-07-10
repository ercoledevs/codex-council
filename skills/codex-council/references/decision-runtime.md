# Decision Runtime

Use this reference only for post-run Decision Runtime work. The runtime is an
experimental, local, opt-in sidecar. It never changes the authoritative Council
verdict, member panel, synthesis, or legacy session artifacts in v1.0.0.

## Operating Contract

- Default is `off`. `init --decision-runtime shadow` records intent but does not
  reduce Council coverage or make a projection authoritative.
- Run projection only after the legacy session artifacts exist.
- Existing Markdown, ledger, findings, reviews, and synthesis remain source of truth.
- Unknown schema, corruption, unsafe permissions, symlinks, stale patches, missing
  dependencies, hard risk, or incomplete impact all fail closed.
- Hashes and session-scoped IDs provide integrity/pseudonymization, not encryption,
  authorization, correctness, or truth.
- Never claim token, latency, or quality savings without paired replay evidence.

## Representations

The projector derives a typed Cell view and a compact frontier export from the same
allowlisted legacy evidence:

- `Decision Cell`: immutable, typed facts (`claim`, `option`, `evidence`, `risk`,
  `blocker`, `dissent`, `verification`, `decision`, `counterfactual`) plus explicit
  edges (`supports`, `contradicts`, `depends_on`, `supersedes`, `verifies`,
  `derived_from`).
- `frontier.jsonl`: a simpler append-only sequence of observed/superseded facts with
  state, planning metadata, dependencies, and pseudonymous source reference.

Cell IDs are deterministic only inside one session: canonical UTF-8 JSON is keyed
with a session salt so identical text is not correlatable across sessions. Confidence
is descriptive and cannot close a blocker or control routing. Unknown fields,
dangling edges, self-edges, and cycles in dependency/supersession edges are invalid.

The comparison reports semantic recall, active-frontier export equivalence, artifact
size, deterministic digests, and frontier-only impact-plan equivalence. Results are
`frontier_export_equivalent` or `cell_graph_required`; Decision Cell never wins by default.

## Typed Patches

Patches are standalone JSON, never extracted from Markdown fences. V1 accepts only:

- `add_cell`
- `add_edge`
- `supersede_cell`

There is no mutation or delete. Reapplying the same patch is idempotent; a stale
`base_generation` conflicts. Validate duplicate keys, NaN, unknown fields, size,
nesting, references, cycles, sensitivity, and privacy before staging any content.
Raw model output stays untrusted and is never treated as a patch implicitly.

## Flight Cell Generations

Runtime state lives under a session-local `decision-runtime/` directory. Directories
use `0700`; files use `0600`. A single-writer transaction follows:

1. Validate the real session root and reject symlinks/path escape.
2. Acquire the runtime lock.
3. Validate current `HEAD`, parent generation, policy, and source hashes.
4. Write a same-filesystem staging generation with no-follow/exclusive files.
5. `fsync` every file and the staging directory.
6. Verify the manifest and atomically rename into `generations/`.
7. `fsync` the generations directory.
8. Atomically replace and synchronize `HEAD` only after the generation is complete.

Every failure leaves legacy artifacts unchanged and `HEAD` old-or-new valid after an
atomic switch. Orphaned, corrupt, policy-violating, or unsafe data is ignored or
quarantined with a reason.
Only an explicit recovery command may move `HEAD`; rollback selects a validated
ancestor and never deletes evidence.

## Impact Planner

The planner is deterministic, advisory, and non-authoritative. It returns a proposed
full or targeted panel, dependency closure, and fallback reasons. It never dispatches
agents or edits `session.json`.

Always force full coverage for privacy, security, data loss, frontend evidence,
unknown domains/relations, open blockers or dissent, missing references, cycles,
corruption, closure overflow, Forge/skill sessions, or any ambiguous impact. A known
low-risk change may propose a bounded targeted panel with Ada, Grace, Turing, relevant
domain roles, and the coverage integrator. No solo panel or early exit is allowed.

## Operational States

- `healthy`: current generation and checksums validate.
- `ignored`: runtime is off, absent, or source evidence is incomplete; use legacy.
- `recovered`: an explicit recovery selected a validated generation.
- `quarantined`: unsafe permission, symlink, schema, checksum, policy, or HEAD state
  requires operator action. Never present this state as OK.

`doctor` is read-only. Retention is reported, never applied automatically. Purge is
explicit, preserves current `HEAD` unless the user confirms a full runtime purge with
the session ID, and never touches legacy artifacts.

## CLI

```bash
python3 scripts/codex_council.py cells project --session <dir> --compare frontier --commit --plan --json
python3 scripts/codex_council.py cells apply --session <dir> --patch patch.json --json
python3 scripts/codex_council.py cells plan --session <dir> --changed <cid> --json
python3 scripts/codex_council.py cells doctor --session <dir> --json
python3 scripts/codex_council.py cells recover --session <dir> --json
python3 scripts/codex_council.py cells rollback --session <dir> --to <generation> --json
python3 scripts/codex_council.py cells purge --session <dir> --expired --json
python3 scripts/codex_council.py cells replay --corpus <dir> --compare frontier --repetitions 10 --json
python3 scripts/codex_council.py cells fault-test --corpus <dir> --json
```

`project` is the opt-in for historical sessions; it previews by default and persists
a shadow generation only with `--commit`.
`apply` only changes the sidecar. `plan` remains advice. Replay and fault-test operate
on sanitized, versioned fixtures or explicitly selected local sessions.

## Verification Gate

Before describing the runtime as healthy:

- legacy output is byte-identical with runtime off and after sidecar failures;
- Cell/frontier projection is deterministic across repeated runs;
- blocker, dissent, and verification recall is 100% on the paired corpus;
- every hard-risk case returns full coverage;
- write/fsync/rename/HEAD failure leaves the prior generation authoritative;
- concurrency, corruption, traversal, symlink, permission, privacy, purge, recovery,
  rollback, stale patch, and cycle cases pass;
- runtime artifacts are excluded from legacy token stats and raw bundles.

## Deferred Beyond v1.0.0

- authoritative verdict changes or automatic panel reduction;
- interpreting arbitrary Markdown/model prose as patches;
- learned scheduling, semantic matching, cross-session memory, automatic reuse;
- automatic TTL deletion, graph UI, and early exit;
- performance claims before reproducible paired benchmarks.
