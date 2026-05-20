---
name: codex-council
description: Use when the user asks for Codex Council, council review, multi-agent deliberation, architecture decision review, implementation judgment, or a 5-member Codex agent council.
---

# Codex Council

Codex-only LLM Council. No external model APIs. Use subagents only when the user explicitly asks for council/multi-agent review.

## Core Contract

- Default to compact mode: fewer tokens, same decision gates.
- For substantial decisions, use five isolated members, then synthesize.
- Preserve dissent, blockers, verification, and confidence.
- Anonymize member outputs as Candidate A-E before peer review.
- Use rubric scoring, not popularity or verbosity.
- Consensus is a decision aid, not proof.

## Before Running

1. If the user did not clearly request council/parallel review, ask before spawning agents.
2. Snapshot only relevant context: `pwd`, `git status --short`, touched files/diff/tests. Send agents filtered context only.
3. Load references only when needed:
   - `references/roles-and-rubrics.md`: exact role prompts, scoring JSON.
   - `references/output-contract.md`: final synthesis format.
   - `references/token-budget.md`: token-saving modes and limits.
   - `references/competency-packs.md`: internal competences when external skills are not desired.
   - `references/workflow-recipes.md`: task-to-mode recipes.
   - `references/governance-preflight.md`: audit/privacy/session checklist.
   - `references/method-source-notes.md`: attribution/source grounding.
4. For durable audit, run:
   - `python3 <plugin-root>/scripts/codex_council.py init --topic "<topic>" --root <workspace> --mode standard`
   - Resolve `<plugin-root>` to the installed `codex-council` plugin directory.

## Modes

- Fast: local Chairman review for small, reversible, non-security choices.
- Standard: five member agents, compact outputs, local Chairman review.
- Deep: five members plus three reviewer agents for security, data loss, migration, irreversible decisions, close ties, or explicit full-council request.

## Internal Competences

If external skills are not desired, use `references/competency-packs.md` instead of invoking other skills. Treat packs as lenses inside Council, not standalone skills.

## Workflow Recipes

Use `references/workflow-recipes.md` for architecture, bug/regression, plugin/skill, release gate, and token-sensitive reviews.

## Stage 1: Members

For Standard/Deep mode, dispatch five agents in parallel. Put instructions first, then role output schema, then only task-specific context.

- Principal Architect: boundaries, integration, maintainability.
- Reliability Engineer: failures, tests, rollback, observability.
- Security/Governance: permissions, privacy, provenance, policy.
- Product/Operator: workflow, usability, docs, adoption.
- Contrarian Red Team: assumptions, simpler alternatives, overengineering.

Each member returns compact output only:

```markdown
## Recommendation
## Rationale
## Blocking Issues
## Non-Blocking Improvements
## Verification Required
## Confidence
```

Caps: max 3 bullets per section, max 90 words per member unless a blocker needs detail. Compress wording, not roles/blockers/dissent/verification.

## Stage 2: Anonymous Review

Strip role/agent names and label outputs Candidate A-E. Review locally unless Deep mode is needed.

Rubric weights:

- accuracy 0.35
- completeness 0.20
- clarity 0.20
- conciseness 0.15
- relevance 0.10

## Stage 3: Deterministic Aggregation

For traceable scoring, save reviewer JSON and run:

```bash
python3 <plugin-root>/scripts/codex_council.py score --input <reviews.json>
```

The script handles weighted scoring, z-score normalization, tie detection, and confidence. If skipped, state aggregation was manual.

## Stage 4: Chairman Synthesis

The main agent is Chairman. Final output must include:

- recommendation
- confidence: high, medium, low, or blocked
- blockers vs refinements
- preserved dissent
- implementation/verification steps

Default final length: 8-14 bullets. Expand only if the user asks or blockers require it.

## Output

Follow `references/output-contract.md` when a formal report is needed. For normal chat, keep the compact final shape above.
