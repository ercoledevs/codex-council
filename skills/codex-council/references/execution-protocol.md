# Execution Protocol

Use this for the full council stage order. Keep `SKILL.md` as the routing kernel.

## Stage 0: Optional Session Start

For chat council runs, paste the compact ASCII council table directly in chat before dispatching agents. Do not hide the only visible banner in shell stdout, because the user may never see it.

For direct terminal scaffold runs, add `--banner` to print the same table in stdout. Do not use it in automation that expects path-only stdout.

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

## Stage 6: Optional Session Stats

When the user wants a closing report, run:

```bash
python3 <plugin-root>/scripts/codex_council.py stats --session <session-dir>
```

Use `--write` to persist `stats.json` and `stats.md`. Token numbers are estimated from local session artifacts only; they are not actual Codex usage, billing telemetry, hidden prompt overhead, or tool-call accounting.

When working in chat, summarize the stats in the final message instead of leaving them only in stdout or files.

Stats only count session artifacts on disk. If member/reviewer/final outputs stayed only in chat, say the report is scaffold-only. For a real closeout, persist compact member outputs, reviewer notes, and Chairman synthesis into the generated files before running stats.
