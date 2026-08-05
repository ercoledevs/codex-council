# Codex Hyper FAQ

## Is Hyper installed separately from Codex Council?

No. Hyper is bundled under `skills/codex-hyper/` in the Codex Council plugin.
If it is missing from the active skill catalog, reinstall or reload the plugin
and start a fresh task. Do not create a standalone copy under the user skill
directory. Invoke the bundled skill as `$codex-council:codex-hyper`.

## Does Hyper always use subagents?

No. Hyper means the smallest justified topology. A simple or tightly coupled
change uses Solo even when the user explicitly invokes `$codex-council:codex-hyper`.

## What happens when subagents are unavailable?

Fall back to Solo, state the reduced independent coverage, and keep the same
verification bar. Stop only when independent evidence is essential to the
authorized risk level.

## Can explorers edit their own files?

No in version 1. Explorers and verifiers are read-only. The root agent is the
single writer and integrator so all agents cannot overwrite the same worktree.

## What if the worktree already contains changes?

Treat them as user-owned. Map overlap before editing, avoid unrelated cleanup,
and stop for direction when the requested patch cannot be separated safely.

## What if baseline tests already fail?

Record the exact pre-existing failure. Use a narrower relevant oracle when
possible and never attribute the baseline failure to the new patch without
evidence.

## What if explorers disagree?

Do not vote. Inspect the cited artifacts or run the smallest discriminating
check. Preserve an unresolved material disagreement as `UNKNOWN`.

## What if the verifier finds a problem?

Fix valid findings, rerun affected checks, and repeat verification after a
material change. Do not report completion while a critical result is `FAIL` or
`UNKNOWN`.

## How does Hyper interact with domain skills?

The domain skill owns scope and stricter gates. Hyper may orchestrate only the
implementation portion explicitly delegated to it. Security finding fixes stay
under the relevant Codex Security workflow.

## When can Codex Mind call Hyper?

Only after explicit implementation intent, a Council Final Call of `build`, no
live blockers, and a complete handoff. A `revise` or `stop` verdict never starts
Hyper.
