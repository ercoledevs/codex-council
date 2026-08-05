# Mind Protocol

Load this only when running Codex Mind. Mind sequences Codex Forge and Codex Council, then optionally hands an approved build to the bundled `$codex-council:codex-hyper` skill from the same plugin. It adds a deliberation estimate and compact handoffs while deferring to each stage's own protocol. Hyper is bundled but is never estimated, authorized, or invoked implicitly.

## Stage 0: Banner and intake

1. Paste the ASCII brain banner from `references/brain-banner.md` verbatim, inside a fenced code block, as the first thing in the run. Nothing before it; no text inside it.
2. Capture the execution intent as one of:
   - `decision-only`: invent and judge, then stop with a recommendation;
   - `implement-if-approved`: offer implementation only if every Hyper gate later passes.
3. Decide the entry:
   - A proposal already exists (the user pasted one, or a prior Forge produced one) -> confirm it in one line and skip to the Council path.
   - No proposal yet -> ask exactly one focused question: what should we create, and what are the hard constraints (scope, compatibility, deadline, budget, privacy)? Do not interrogate; one question, then proceed.

An up-front `implement-if-approved` request expresses intent, but does not approve an unbounded or changed implementation. Record the approved scope and any action-specific constraints for the later execution preflight.

## Stage 1: Deliberation preflight

The estimate covers **Forge + Council only**. Estimate the deliberation stages that will actually run and, when both run, present one summed range:

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode standard --type forge --token-budget compact
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode <council-mode> --token-budget compact
```

- Show the low-high range in chat and get acceptance before dispatching. Default `compact` for both stages.
- When a proposal already exists and Forge is skipped, estimate Council only rather than charging for a stage that will not run.
- `<council-mode>` is `standard` by default, `deep` for security, data loss, migration, or irreversible work.
- `expanded` is blocked unless the user explicitly confirms it, for either stage.
- The Forge estimate already includes its re-brief overhead, so an automatic round 2 on strong discord stays inside the accepted Forge estimate.
- If execution intent is `implement-if-approved`, disclose a possible third wave. State that Hyper is task-dependent, has its own estimate, and is subject to a separate execution preflight after judgment.
- Acceptance of deliberation spend is never implementation authorization.

## Stage 2: Forge stage

Run Codex Forge per `forge-protocol.md`: five creators, one bounded round, auto round 2 only on strong discord, hard cap three. Close the creators before synthesis. Produce the unified proposal and its `Next Prompt`.

If Forge returns `nonconverged`, do not silently roll into Council. Surface the persistent dissent and ask whether to judge the best partial proposal anyway, refine the brief, or stop. This protects the user from paying for a Council review of a proposal that has not settled.

## Stage 3: Compact Council handoff

Council judges the artifact, not the workshop. Pass only:

- the unified proposal,
- its safety and performance notes and any unmet floor items,
- Forge's `Next Prompt`.

Never pass full Forge transcripts or per-creator outputs into Council. This is the main lever that keeps deliberation bounded.

## Stage 4: Council stage

Run Codex Council on the proposal as the thing under review (Standard, or Deep for security/data-loss/migration/irreversible). The Council keeps its own non-negotiables: anonymized review, rubric scoring, preserved dissent, no fake UI verification, and explicit verification.

Normalize the Final Call to `build`, `revise`, or `stop`, and preserve every blocker separately from non-blocking refinements. A live blocker can never coexist with an executable `build` handoff.

Close every Council agent and its stage session before evaluating or invoking Hyper. Deliberation and implementation may never overlap as live waves.

## Stage 5: Hyper eligibility gate

Hyper is eligible only if all four conditions are true:

1. execution intent is `implement-if-approved` or the user now explicitly requests implementation;
2. the Council Final Call is exactly `build`;
3. no live blocker remains;
4. `$codex-council:codex-hyper` is available in the current skill catalog.

Apply the gate fail-closed:

- `revise`, `stop`, or any blocker -> do not execute;
- no implementation request -> report `Hyper: not requested`;
- unavailable bundled skill -> report `Hyper: unavailable`, treat the plugin/session as stale or incomplete, do not emulate the workflow, and emit a ready-to-use handoff for a fresh task after reinstall or reload;
- any material scope, constraint, or risk-profile change after judgment -> invalidate `build`, report `revise`, and return the changed proposal to deliberation.

Do not load Hyper instructions before this gate passes.

## Stage 6: Hyper execution preflight and authorization

Before code changes:

1. show that Hyper is a separate, task-dependent execution wave with its own estimate;
2. restate the exact approved scope, immutable constraints, expected repository, and acceptance and verification criteria;
3. name any known non-blocking risk or dissent;
4. confirm availability of the required repository and tools;
5. obtain explicit implementation authorization if it was not already given for this unchanged scope.

Up-front authorization remains valid only if the scope and risk profile are unchanged and no new material external, destructive, privileged, or otherwise approval-sensitive action has appeared. Such actions always require their own authorization under the active Codex safety rules.

If authorization is declined or missing, report `Hyper: declined` and stop after the approved handoff.

## Stage 7: Compact Hyper handoff and execution

Pass only:

- the approved proposal;
- immutable constraints and explicit out-of-scope items;
- Council conditions attached to `build`;
- acceptance criteria and verification criteria;
- preserved non-blocking dissent and residual risks.

Never pass Forge or Council transcripts. Do not prescribe an agent count or copy Hyper's internal routing protocol into Mind.

Now load and follow `$codex-council:codex-hyper`. Hyper owns repository observation, Solo/Relay routing, writing, testing, independent falsification, and evidence classification. Mind does not start implementation agents of its own.

Hyper returns one of:

- `completed`: all required evidence is `PASS`;
- `blocked`: at least one required criterion is `FAIL` or `UNKNOWN`, or execution cannot safely continue.

Any material fix after falsification requires Hyper to verify again before `completed` is valid.

## Stage 8: Final synthesis

Return one coherent result, leading with the decision:

- Idea, restated in one line.
- Forge: unified proposal, convergence result, and persistent dissent.
- Council: recommendation, confidence (high / medium / low / blocked), blockers vs refinements, preserved dissent, and exact verification.
- Hyper: `not requested`, `not eligible`, `unavailable`, `declined`, `completed`, or `blocked`, plus implementation evidence when it ran.
- Final Call: build, revise, stop, or implementation outcome, with the single next concrete step.

Keep Forge's creative dissent, Council's review dissent, and Hyper's execution evidence distinct. Never merge them into false consensus or promote `UNKNOWN` to success.

## Token discipline — avoiding bursts

- One deliberation estimate accepted up front; default `compact` for Forge and Council.
- Compact Council handoff only (proposal + `Next Prompt`), never transcripts.
- Two deliberation waves — Forge, then Council — each closed before the next; max six open agents at any time.
- Hyper, when eligible, is a separate optional execution wave after every Council agent is closed.
- Escalate one deliberation stage only when risk requires it; expand a blocker or divergence, not the whole pipeline.
- Early exits save work: a Forge `nonconverged` checkpoint, a Council `revise`/`stop`/blocker, or a failed Hyper gate stops dispatch.
- Use `stats --session <dir>` per deliberation stage for closing metrics; pre/post figures are local estimates, not Codex billing.

## Stop conditions

- User says stop -> end with what is known.
- Deliberation estimate is not accepted -> do not dispatch Forge or Council.
- Forge returns `nonconverged` -> checkpoint; do not auto-run Council.
- Council returns `revise`, `stop`, or a blocker -> do not invoke Hyper.
- No explicit implementation intent -> stop after the verdict.
- bundled `$codex-council:codex-hyper` is unavailable -> treat the plugin/session as stale or incomplete, do not emulate it, and return a ready handoff for a fresh task after reinstall or reload.
- Hyper authorization is declined or missing -> stop after the approved handoff.
- Scope or material risk changes after judgment -> invalidate `build` and return to `revise`.
- A destructive, external, privileged, or otherwise approval-sensitive action lacks its required authorization -> do not perform it.
- Hyper verification returns `FAIL` or `UNKNOWN` -> report `blocked`, not `completed`.
