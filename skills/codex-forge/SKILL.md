---
name: codex-forge
description: Use when the user wants Codex to creatively design, invent, shape, brainstorm, or forge a technical/product proposal with multiple specialized creation agents before returning a unified implementation idea.
---

# Codex Forge

Forge is bounded convergent creation for Codex: five creators shape one buildable proposal; Council judges it. Forge creates — it does not validate truth, safety, UI behavior, or correctness. It designs for them and flags what Council must check.

## Non-Negotiables

- Reuse Codex Council preflight, token budgets, plugin-local sessions, stats, banner, and agent lifecycle. Never dispatch without the preflight estimate and user acceptance.
- Default `compact`. `balanced` only for real ambiguity. `expanded` only with explicit confirmation. Expand one divergence, not the whole session.
- The loop is bounded: one structured round is the default. The next round is normally an optional second round you accept after the round-1 synthesis — but if round 1 is strongly discordant (creators disagree from the start), it starts automatically. A hard cap of three rounds always holds, and every extra round re-briefs only the unresolved divergence.
- If creators do not converge, return `nonconverged` with persistent dissent. Never manufacture consensus.
- Every proposal must be designed to clear the security & stability floor (see protocol). An item it cannot meet is a blocker, and blockers block convergence.
- Preserve immutable constraints: system/developer/user instructions, repo rules, privacy, budget, scope, provenance. Tuning and creativity never override them.
- Close the five creators after each round before the next wave; max six open agents.
- Detail lives in the single synthesis, not in five verbose creators. Keep creators compact.
- Persist compact prompts/outputs before stats. Report pre/post estimates; never claim billing tokens.

## Token Router

Default `compact`. Escalate only what risk requires.

| Need | Action |
| --- | --- |
| shape a new idea into a buildable proposal | Forge, one round, compact |
| meaningful ambiguity or competing shapes | Forge `balanced`; expand only the divergence |
| judge an existing proposal | hand off to Codex Council; do not Forge |
| security, data loss, irreversible surface | Forge stays compact, but require Deep Council before building |

Preflight (the estimate already counts re-brief overhead):

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode standard --type forge --token-budget compact
```

Scaffold after acceptance (`expanded` needs `--confirm-expanded`):

```bash
python3 <plugin-root>/scripts/codex_council.py init --topic "<topic>" --root <workspace> --mode standard --type forge --token-budget compact --confirm-estimate
```

## Roles

- Buckminster Fuller - Systems Imagination Architect: bold system shape, primitives, boundaries.
- Hedy Lamarr - Product Invention Strategist: user value, workflow fit, interaction concept.
- Katherine Johnson - Feasibility and Integration Engineer: dependencies, interfaces, implementation path.
- Margaret Hamilton - Safety and Reliability Builder: failure modes, privacy, rollback, reliability. Owns the security & stability floor.
- John von Neumann - Performance and Complexity Optimizer: latency, cost, scalability, simplification.

## Design Bar

Proposals should be modern (current, justified best practice — not trendy-but-fragile), creative (bold shape), functional (buildable, smallest viable scope), stable (named failure modes and rollback), secure (clears the floor), and detailed — but the detail is produced once, in the synthesis.

## Minimal Flow

1. Classify: Forge creates/designs; Council judges/reviews. Route judgment to Council; treat explaining as meta (one line, no dispatch).
2. Run the mandatory preflight estimate; show the range; get acceptance. Block `expanded` without explicit confirmation.
3. Paste the Forge banner in chat. Dispatch the five creators in parallel with the compact brief.
4. Collect outputs, close the creators, keep constraints, risks, and dissent.
5. Run a separate synthesis: one detailed, buildable unified proposal that honors the floor and keeps dissent visible.
6. Score with `forge-convergence` when score JSON exists (novelty, feasibility, user fit, risk control, implementation clarity, alignment). Converged needs minimum alignment >= 7, low score spread, no blockers, no dissent.
7. If not converged, read `second_round` from forge-convergence: `auto` (strong discord) runs round 2 immediately, `optional` (near-miss) asks first. Either way, re-brief only the divergence and never exceed three rounds. Otherwise return the unified proposal.
8. Persist compact artifacts, relay stats, and offer the next Council prompt.

## Reference

Load `references/forge-protocol.md` when forging: stage order, per-agent token caps, the security & stability floor, the detailed-proposal contract, and the divergence-targeted re-brief. Load Council references only when judging.

## Output

- Unified Proposal
- Convergence Result: converged, partial, or nonconverged
- Persistent Dissent
- Implementation Shape
- Safety And Performance Notes
- Verification
- Next Prompt (for Council judgment)

If the user asks to implement a forged proposal, run Codex Council or normal implementation verification first when risk is non-trivial.
