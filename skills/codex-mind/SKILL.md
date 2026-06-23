---
name: codex-mind
description: Use when the user wants the full guided run — invent a proposal and then judge it — in one pass. Codex Mind orchestrates Codex Forge and then Codex Council end to end, asking what to build first if no proposal exists yet.
---

# Codex Mind

The guided pipeline: Forge invents a proposal, then Council judges it — one process, end to end. Mind only orchestrates; Forge and Council keep their own non-negotiables.

## Non-Negotiables

- At the very start, paste the ASCII brain banner from `references/brain-banner.md` verbatim in a code block. It is art only — never add text inside the drawing.
- If no proposal exists yet, ask the user what to create before anything else — one focused question (goal + hard constraints), not a form.
- One combined preflight estimate covers both stages (Forge + Council). Show it once and get acceptance before dispatching anything. Default `compact`. `expanded` only with explicit confirmation.
- Reuse every Forge and Council non-negotiable: preflight gate, plugin-local sessions, agent lifecycle (max six open agents, close each wave before the next), stats, and never claim billing tokens.
- Hand a compact artifact between stages — the unified proposal plus Forge's `Next Prompt`, not full Forge transcripts. Council judges the proposal; it does not re-derive it.
- Honor stop conditions: a Forge `nonconverged`, a Council blocker, or a user stop ends the pipeline with what is known. Never force a happy ending.
- The Forge security & stability floor and the Council verification are never skipped to look finished.

## Token Router

Mind adds orchestration, not extra agents: the Forge wave, then the Council wave, each closed before the next. Estimate once, up front.

| Need | Action |
| --- | --- |
| new idea, no proposal yet | ask one question, then Forge → Council, compact |
| a proposal already exists | confirm it, skip Forge, go straight to Council |
| security, data loss, migration, irreversible | keep Forge compact; run Deep Council before any build |
| only invent, or only judge | use Codex Forge or Codex Council directly, not Mind |

## Minimal Flow

1. Paste the ASCII brain banner.
2. If a proposal already exists (user-supplied or from a prior Forge), confirm it and skip to step 5. Otherwise ask the one question: what should we create, and the hard constraints?
3. Combined preflight: estimate Forge plus the intended Council mode together, compact; show the summed range; get acceptance. Block `expanded` without explicit confirmation.
4. Forge stage: run Codex Forge (one bounded round; auto round 2 on strong discord; hard cap three). Produce the unified proposal.
5. Show the proposal briefly. If Forge returned `nonconverged`, surface the dissent and ask before paying for Council. Otherwise continue within the accepted estimate. The user may refine or stop here.
6. Council stage: run Codex Council on the proposal (Standard; Deep for security, data loss, migration, or irreversible work). Judge it.
7. Final result: the proposal, the Council verdict, and one clear build / revise / stop call with blockers, dissent, and verification.

## Reference

Load `references/mind-protocol.md` when running: the banner step, the combined estimate, the compact handoff contract, and the stop conditions. The Forge stage loads the `codex-forge` skill and its `forge-protocol.md`; the Council stage loads `codex-council` and its references. Load each only when that stage runs.

## Output

- Idea (restated in one line)
- Forge: Unified Proposal, Convergence Result, Persistent Dissent
- Council: Recommendation, Confidence, Blockers vs Refinements, Verification
- Final Call: build, revise, or stop — with the next concrete step

If the user asks to implement the result, treat the Council verdict as the gate: build only what cleared it, and verify before shipping.
