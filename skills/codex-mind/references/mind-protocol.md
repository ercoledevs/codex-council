# Mind Protocol

Load this only when running Codex Mind. Mind is an orchestrator: it sequences Codex Forge and then Codex Council, adds one combined estimate and a compact handoff, and otherwise defers to each skill's own protocol. The goal is the same as the rest of the plugin — strong output, hard safety/stability floors, and no token burst.

## Stage 0: Banner and intake

1. Paste the ASCII brain banner from `references/brain-banner.md` verbatim, inside a fenced code block, as the first thing in the run. Nothing before it; no text inside it.
2. Decide the entry:
   - A proposal already exists (the user pasted one, or a prior Forge produced one) → confirm it in one line and skip to Stage 2 (Council).
   - No proposal yet → ask exactly one focused question: what should we create, and what are the hard constraints (scope, compatibility, deadline, budget, privacy)? Do not interrogate; one question, then proceed.

## Stage 1: Combined preflight (one estimate, up front)

Mind runs two multi-agent stages, so the user must see the total before either spends. Estimate both stages and present a single summed range:

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode standard --type forge --token-budget compact
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode <council-mode> --token-budget compact
```

- Show the combined low–high range in chat and get one acceptance for the whole pipeline. Default `compact` for both stages.
- `<council-mode>` is `standard` by default, `deep` for security, data loss, migration, or irreversible work.
- `expanded` is blocked unless the user explicitly confirms it, for either stage.
- The Forge estimate already includes its re-brief overhead, so an automatic round 2 on strong discord stays inside the accepted total.

## Stage 2: Forge stage

Run Codex Forge per `forge-protocol.md`: five creators, one bounded round, auto round 2 only on strong discord, hard cap three. Close the creators before synthesis. Produce the unified proposal and its `Next Prompt`.

If Forge returns `nonconverged`, do not silently roll into Council. Surface the persistent dissent and ask whether to judge the best partial proposal anyway, refine the brief, or stop. This protects the user from paying for a Council review of a proposal that has not settled.

## Stage 3: Compact handoff

Council judges the artifact, not the workshop. Pass only:

- the unified proposal,
- its safety/performance notes and any unmet floor items,
- Forge's `Next Prompt`.

Never pass full Forge transcripts or per-creator outputs into Council. This is the main lever that keeps a two-stage run from doubling tokens.

## Stage 4: Council stage

Run Codex Council on the proposal as the thing under review (Standard, or Deep for security/data-loss/migration/irreversible). The council keeps its own non-negotiables: anonymized review, rubric scoring, preserved dissent, no fake UI verification, and explicit verification. A Council blocker stops the pipeline with that blocker named — it is not smoothed over.

## Stage 5: Final synthesis

Return one coherent result, leading with the decision:

- Idea, restated in one line.
- Forge: the unified proposal, convergence result, and any persistent dissent.
- Council: recommendation, confidence (high / medium / low / blocked), blockers vs refinements, preserved dissent, and the exact verification.
- Final Call: build, revise, or stop — with the single next concrete step.

Keep Forge's creative dissent and Council's review dissent distinct; do not merge them into a false consensus.

## Token discipline — avoiding bursts

- One combined estimate accepted up front; default `compact` for both stages.
- Compact handoff only (proposal + `Next Prompt`), never transcripts.
- Two waves total — Forge, then Council — each closed before the next; max six open agents at any time.
- Escalate one stage (Deep Council, or a Forge re-brief) only when risk requires it; expand a blocker or a divergence, not the whole pipeline.
- Early exits are savings: a Forge `nonconverged` checkpoint and a Council blocker both stop spend instead of pushing on.
- Use `stats --session <dir>` per stage for closing metrics; pre/post are local estimates, not Codex billing.

## Stop conditions

- User says stop → end with what is known.
- Forge `nonconverged` → checkpoint; do not auto-run Council.
- Council returns a blocker → stop at `revise` or `stop`; never report `build` over a live blocker.
- Estimate not accepted → do not dispatch.
