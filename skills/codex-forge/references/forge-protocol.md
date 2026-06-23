# Forge Protocol

Load this only when actually forging. Keep `SKILL.md` as the routing kernel. Everything here serves three goals at once: stronger proposals, hard safety/stability floors, and no token burst.

## Stage 0: Preflight (reused from Council)

- If no consumer profile exists, ask plan, model, reasoning effort, and optional budget; store only with consent.
- Estimate with `--type forge` and show the range in chat; the estimate already includes a re-brief overhead. Get acceptance before dispatch. `expanded` must not run without explicit confirmation.
- Classify the trigger: creating/designing is Forge; judging/reviewing is Council; explaining/comparing is `meta` (answer in one line, no dispatch). If intent is unclear, ask one line.

## Stage 1: One compact creative round

Dispatch the five creators in parallel. Order each prompt for prompt-cache hits — stable text first, variable last:

1. role contract + lens (stable)
2. output schema (stable)
3. security & stability floor (stable)
4. immutable constraints: system/developer/user instructions, repo rules, privacy, budget, scope, provenance (semi-stable)
5. the user's idea and the minimal relevant context (variable, last)

Pass only the minimal context a creator needs — the decision, hard constraints, and any directly relevant file or interface. Do not paste full transcripts, unrelated docs, or repeated role text.

Each creator returns only these sections:

```markdown
## Creative Proposal
## Rationale
## Constraints
## Risks
## Convergence Notes
## Verification Needed
```

Caps: compact 110 words, balanced 150. `Constraints` and `Risks` are never trimmed to save words. Performance, safety, and reliability claims are written as assumptions to verify unless they are grounded. Each creator names where it expects to disagree with the others (that is what `Convergence Notes` is for).

After all five finish, retrieve outputs and close the creators before any synthesis or next wave. The platform allows six open agents, so never hold the five creators open while spawning more.

## Stage 2: Security & stability floor (mandatory)

Forge does not verify safety — it designs for it. Every proposal must be designed to clear this floor; Margaret Hamilton enforces it, and any item it cannot meet becomes a blocker (which blocks convergence):

- No secrets, credentials, tokens, or PII baked into the design; least privilege by default.
- Fail-safe / fail-closed defaults; an explicit rollback and recovery path; no big-bang change.
- Data handling and privacy stated; no new sensitive-data path without justification.
- Does not weaken an existing safety, auth, validation, or isolation boundary.
- Dependencies are reputable and pinnable; supply-chain and version risk is named, not assumed away.
- Blast radius and failure modes are named; observability where an operator would need it.
- Bias to proven, modern patterns over trendy-but-fragile ones; the smallest viable shape that solves the problem.

Floor misses are reported as blockers in plain language, not smoothed over to look finished.

## Stage 3: Convergence

Score each creator on `novelty`, `feasibility`, `user_fit`, `risk_control`, `implementation_clarity`, plus `alignment` (all 1..10), with any blockers and persistent dissent:

```bash
python3 <plugin-root>/scripts/codex_council.py forge-convergence --input <scores.json>
```

Converged requires all of: minimum `alignment` >= 7.0, score spread (population stdev of weighted totals) <= 1.25, no blockers, and no persistent dissent. Otherwise the result is `nonconverged`. Use `partial` in prose only when the shape is agreed but named follow-ups remain; the machine status stays `nonconverged` until the gate is clean.

The assessment also returns `second_round`, which decides how the next round is entered:

- `none` — converged; stop.
- `auto` — round 1 is strongly discordant (minimum `alignment` < 5.0, or score spread > 2.0): the creators disagree from the start, so round 2 runs automatically.
- `optional` — a near-miss below the bar: ask the user before another round.

## Stage 4: Detailed synthesis — where the tokens go

Detail is paid once, here, not five times across creators. Run a separate synthesis pass over the saved creator outputs and the synthesis-input manifest (not chat memory):

- Lead with what to build and why this shape won.
- `Implementation Shape`: modules and interfaces, data shapes, sequencing, and the key edge cases.
- Keep the strongest creative idea; graft the useful parts of the runners-up; keep real dissent visible instead of averaging it away.
- Honor the security & stability floor explicitly, and carry every unmet item into `Safety And Performance Notes` as something Council must check.
- End with concrete `Verification` and a ready-to-send `Next Prompt` for Council judgment.

Budget: the unified proposal may be detailed — roughly 350 words compact, 550 balanced. Because this is a single pass, detail here does not multiply across agents.

## Stage 5: Round 2 — automatic on strong discord, opt-in on a near-miss

Run another round only when round 1 did not converge. How you enter it depends on `second_round`:

- `auto` (strong discord — the creators disagree from the start): start round 2 immediately, without asking. This stays inside the cost the user already accepted — the preflight estimate budgets the re-brief overhead, the round is divergence-scoped, and the hard cap of three is absolute — so it is not a token burst.
- `optional` (near-miss): ask the user before spending another round.

Either way:

- Re-brief the creators with a compact divergence delta: the specific disagreement, the floor items at risk, and the constraint in tension. Do not resend full prior transcripts.
- Do not re-run dimensions that already converged; touch only the open divergence.
- Hard cap is three rounds total. If it still has not converged at the cap, return `nonconverged` with the persistent dissent that blocked it — never a forced consensus.

## Token Discipline — avoiding bursts

- Five creators, one round, compact by default. Re-briefs are opt-in and divergence-scoped.
- Never pass full transcripts between rounds or into the synthesis; pass compact deltas and the manifest.
- Reduce output before input: shorter creator outputs do not weaken `Risks`, `Constraints`, or dissent.
- Static instruction prefixes first for cache hits; variable idea/context last.
- Load only this protocol while forging; load Council references only when judging.
- Use `stats --session <dir>` for closing metrics instead of pasting transcripts. Pre/post are local estimates, not Codex billing tokens.

## Handoff to Council

A forged proposal is a starting point, not a green light. For non-trivial risk, hand the `Next Prompt` to Codex Council — Deep mode for security, data-loss, migration, or irreversible work — before building.
