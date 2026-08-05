---
name: codex-mind
description: Use when the user wants the full guided run — invent a proposal and then judge it — in one pass, with an optional implementation handoff after approval. Codex Mind orchestrates Codex Forge and Codex Council end to end, then may offer the bundled $codex-council:codex-hyper skill from the same plugin only when the Council returns build, no blocker remains, and implementation is explicitly authorized.
---

# Codex Mind

The guided pipeline: Forge invents a proposal, Council judges it, and an approved proposal may be handed to the bundled `$codex-council:codex-hyper` skill for implementation. Mind orchestrates the stages; Forge, Council, and Hyper keep their own non-negotiables.

```text
Forge -> Council -> [Hyper, only when eligible and authorized]
```

## Non-Negotiables

- At the very start, paste the ASCII brain banner from `references/brain-banner.md` verbatim in a code block. It is art only — never add text inside the drawing.
- If no proposal exists yet, ask the user what to create before anything else — one focused question (goal + hard constraints), not a form.
- One combined **deliberation preflight estimate** covers Forge + Council only. Show it once and get acceptance before dispatching either stage. Default `compact`. `expanded` only with explicit confirmation.
- Hyper is bundled in the same Codex Council plugin but remains a task-dependent execution stage. Never hide it inside the Forge + Council estimate or treat acceptance of that estimate as implicit implementation authorization.
- Reuse every Forge and Council non-negotiable: preflight gate, plugin-local sessions, agent lifecycle (max six open agents, close each wave before the next), stats, and never claim billing tokens.
- Hand a compact artifact between stages — the unified proposal plus Forge's `Next Prompt`, not full Forge transcripts. Council judges the proposal; it does not re-derive it.
- Start Hyper only when every eligibility gate passes: the user explicitly wants implementation, the Council Final Call is `build`, no live blocker remains, and `$codex-council:codex-hyper` is available.
- Close all Council agents before loading or invoking Hyper. Pass a compact approved-build handoff, not Council transcripts.
- Hyper requires its own visible execution preflight. Up-front implementation intent may authorize it only while the approved scope and risk profile remain unchanged; any new material, external, destructive, or otherwise approval-sensitive action requires fresh authorization.
- If `$codex-council:codex-hyper` is unavailable despite being bundled, treat the plugin/session as stale or incomplete. Do not imitate or partially reimplement it; return the verdict and a ready-to-use handoff, then direct the user to reinstall the plugin or start a fresh task.
- Any material scope drift after the Council verdict invalidates approval. Return to `revise`; do not ask Hyper to implement unreviewed work.
- Honor stop conditions: a Forge `nonconverged`, a Council `revise` or `stop`, any Council blocker, a Hyper `FAIL` or `UNKNOWN`, or a user stop ends the relevant path with what is known. Never force a happy ending.
- The Forge security and stability floor, Council verification, and Hyper falsification are never skipped to look finished.

## Token Router

Mind adds orchestration, not hidden agents. The deliberation has a Forge wave followed by a Council wave, each closed before the next. Eligible implementation is a separate optional Hyper wave.

| Need | Action |
| --- | --- |
| new idea, no proposal yet | ask one question, then Forge -> Council, compact |
| a proposal already exists | confirm it, skip Forge, go straight to Council |
| forge, judge, and implement if approved | disclose the optional third wave; estimate Forge + Council only; apply the Hyper gates after judgment |
| security, data loss, migration, irreversible | keep Forge compact; run Deep Council before any build; preserve specialist safety workflows |
| only invent, only judge, or only implement | use Codex Forge, Codex Council, or Codex Hyper directly |

## Minimal Flow

1. Paste the ASCII brain banner.
2. Record whether the user wants decision only or implementation if approved. If a proposal already exists, confirm it and skip Forge; otherwise ask the one question: what should we create, and what are the hard constraints?
3. Deliberation preflight: estimate the Forge and Council stages that will actually run, show one summed range when both run, state explicitly that Hyper is excluded, and get acceptance. Block `expanded` without explicit confirmation.
4. Forge stage: run Codex Forge (one bounded round; auto round 2 on strong discord; hard cap three). Produce the unified proposal.
5. Show the proposal briefly. If Forge returned `nonconverged`, surface the dissent and ask before paying for Council. Otherwise continue within the accepted estimate. The user may refine or stop here.
6. Council stage: run Codex Council on the proposal (Standard; Deep for security, data loss, migration, or irreversible work). Judge it and close every Council agent.
7. Apply the Hyper eligibility gate. A result other than `build`, any live blocker, absent implementation intent, or unavailable `$codex-council:codex-hyper` stops execution without emulation.
8. If eligible, show a separate Hyper execution preflight and confirm that the approved scope, constraints, and risk profile have not changed. Obtain any authorization still required.
9. Invoke `$codex-council:codex-hyper` with only the approved proposal, immutable constraints, acceptance and verification criteria, and non-blocking dissent or risks. Hyper owns routing, implementation, and falsification.
10. Return the proposal, Council verdict, Hyper status, and one clear final call. Report implementation complete only when Hyper's evidence is `PASS`; preserve `FAIL` or `UNKNOWN` as blocked work.

## Reference

Load `references/mind-protocol.md` when running: it defines the banner step, deliberation estimate, compact handoffs, optional Hyper gates, and stop conditions. The Forge stage loads the `codex-forge` skill and its `forge-protocol.md`; the Council stage loads `codex-council` and its references. Load and follow `$codex-council:codex-hyper` only after its eligibility, availability, and authorization gates pass.

## Output

- Idea (restated in one line)
- Forge: Unified Proposal, Convergence Result, Persistent Dissent
- Council: Recommendation, Confidence, Blockers vs Refinements, Verification
- Hyper: `not requested`, `not eligible`, `unavailable`, `declined`, `completed`, or `blocked`
- Final Call: build, revise, stop, or implementation outcome — with the next concrete step

The Council verdict is necessary but not sufficient authorization to write code. Hyper implements only the unchanged, approved scope and verifies it before completion.
