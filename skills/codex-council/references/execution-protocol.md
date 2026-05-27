# Execution Protocol

Use this for the full council stage order. Keep `SKILL.md` as the routing kernel.

## Stage 1: Independent First Opinions

Dispatch six agents in parallel for Standard/Deep mode:

- Ada Lovelace - Principal Architect
- Grace Hopper - Reliability Engineer
- Hypatia - Security and Governance Reviewer
- Florence Nightingale - Product and Operator Advocate
- Alan Turing - Contrarian Red Team
- Seymour Cray - Performance Engineer

Put instructions first, then output schema, then task-specific context. Each dispatch prompt starts with:

```text
You are <persona> - <role> for Codex Council.
```

Member output:

```markdown
## Recommendation
## Rationale
## Blocking Issues
## Non-Blocking Improvements
## Verification Required
## Confidence
```

Compact cap: 90 words. Balanced cap: 140 words. Expanded cap: only when blockers require detail.

## Stage 2: Anonymous Review

Strip role/agent names and label outputs Candidate A-F. Review locally in Standard mode unless Deep mode is needed.

Required review output:

- ranked candidate order
- winner reason
- blocking issues per candidate
- material dissent or tie note
- rubric scores when traceability matters
- performance impact coverage and missing measurements

If reciprocal member review is used, exclude self-votes. If self-vote exclusion is unclear, use independent reviewers or local Chairman review.

## Stage 3: Deterministic Aggregation

When reviewer JSON exists:

```bash
python3 <plugin-root>/scripts/codex_council.py score --input <reviews.json>
```

The script requires every non-excluded reviewer to score every candidate. Missing scores are invalid coverage, not a token-saving shortcut.

Standard scaffold includes `performance-impact-reviewer` and `coverage-integrator`. Deep mode adds rubric, bias, and implementation reviewers.

## Stage 4: Optional Frontend Evidence

When `--frontend-review` is active:

- Leonardo reviews anonymized candidates after Stage 2.
- Bob tests browser cases before Chairman synthesis if a runnable UI exists.
- Failed Bob cases become blockers when they invalidate the recommendation.
- Untested UI claims are reported as not verified.

## Stage 5: Chairman Synthesis

The main agent compiles the strongest recommendation from winner, dissent, blockers, and verification evidence. It does not simply announce the highest score.

Final output includes:

- recommendation
- confidence: high, medium, low, or blocked
- blockers vs refinements
- preserved dissent
- implementation/verification steps
