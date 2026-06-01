# Execution Protocol

Use this for the full council stage order. Keep `SKILL.md` as the routing kernel.

## Stage 0: Consumer Safety Preflight

If the local consumer profile is missing, ask the user for plan, typical Codex model, reasoning effort, and optional self-declared 5-hour/weekly budget. Store it only with consent. The local file stores compact aggregates, never raw prompts/transcripts.

Before Standard/Deep dispatch, estimate locally:

```bash
python3 <plugin-root>/scripts/codex_council.py estimate --topic "<topic>" --mode <mode> --token-budget <budget>
```

Show the estimate/range in chat and ask whether to proceed. `expanded` must not run unless the user explicitly accepts the warning, or CLI receives `--confirm-expanded`.

For natural-language triggers, classify intent before dispatch. If the user is explaining, comparing, or asking how council works, treat it as `meta`. If intent is unclear, ask one line. The CLI helper is:

```bash
python3 <plugin-root>/scripts/codex_council.py classify-invocation --text "<user text>"
```

## Stage 0b: Optional Session Start

For chat council runs, paste the compact ASCII council table directly in chat before dispatching agents. Do not hide the only visible banner in shell stdout, because the user may never see it.

For direct terminal scaffold runs, add `--banner` to print the same table in stdout. Do not use it in automation that expects path-only stdout.

Use `--announce` when a terminal run should print a one-line dispatch status, for example `standard panel: dispatched 6 members, 2 reviewers (compact)`.

`init --root <workspace>` uses `<workspace>` only as the analyzed project. Store session artifacts in plugin-local `<plugin-root>/.codex-council/sessions/` by default, never in the project. Use the printed session path for validation/stats. Override only with `--session-root` or `CODEX_COUNCIL_SESSION_ROOT`.

Use `--type architecture|implementation|decision|skill|frontend` for typed synthesis templates. `--type frontend` activates the frontend gate. `--type skill` or `--skill-review` uses a compact three-member skill/tool panel: skill engineer, UX-for-tools, and non-expert adoption.

If local role tuning exists, disclose active tuned alters before dispatch. Tuning is advisory, lower priority than all council non-negotiables, and must never be treated as evidence of true multi-provider diversity.

## Stage 1: Independent First Opinions

Dispatch six agents in parallel for Standard/Deep mode, or three agents for `--skill-review`:

- Ada Lovelace - Principal Architect
- Grace Hopper - Reliability Engineer
- Hypatia - Security and Governance Reviewer
- Florence Nightingale - Product and Operator Advocate
- Alan Turing - Contrarian Red Team
- Seymour Cray - Performance Engineer

Skill review panel:

- Ada Lovelace - Skill Engineer
- Florence Nightingale - UX-for-Tools Critic
- Grace Hopper - Non-Expert Adoption Reviewer

Put instructions first, then output schema, then task-specific context. Each dispatch prompt starts with:

```text
You are <persona> - <role> for Codex Council.
```

Local role tuning, if enabled, is appended after the stable role/protocol prefix as a bounded advisory block. It cannot alter required sections or council invariants.

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

After all first-opinion agents finish, retrieve their outputs and close the completed agents before spawning reviewers, Leonardo, Bob, or any extra agent. The platform limit is six open agents, so reviewer dispatch must happen after member cleanup.

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

Standard scaffold includes `performance-impact-reviewer` and `coverage-integrator`. Deep mode adds rubric, bias, and implementation reviewers. Skill-review mode skips reviewers by default to stay cheap.

## Stage 4: Optional Frontend Evidence

When `--frontend-review` is active:

- Leonardo reviews anonymized candidates after Stage 2.
- Bob tests browser cases before Chairman synthesis if a runnable UI exists.
- Failed Bob cases become blockers when they invalidate the recommendation.
- Untested UI claims are reported as not verified.

## Stage 5: Chairman Synthesis

The main agent compiles the strongest recommendation from winner, dissent, blockers, and verification evidence. It does not simply announce the highest score.

Scaffolded sessions must treat synthesis as a separate pass. `init` writes `prompts/chairman-synthesis.md` and `prompts/synthesis-inputs.json`; update these if actual dispatch inputs differ. The Chairman should use saved member/reviewer outputs as data, not hidden chat memory.

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

Use `--write` to persist `stats.json` and `stats.md`. The report separates `pre_execution_estimate`, `post_execution_estimate`, and `artifact_only_tokens`; none are actual Codex usage, billing telemetry, hidden prompt overhead, or exact tool-call accounting.

Use `--raw-bundle` only when the user wants an audit bundle. It writes `raw-output-bundle.json` with relative artifact paths only, never raw prompt/output text.

Use `--record-history` only after compact prompts/outputs are persisted and the user consented to local learning history. The history file keeps aggregate estimates and ratios only.

When working in chat, summarize the stats in the final message instead of leaving them only in stdout or files.

Post estimates use saved prompt files plus saved member/reviewer/Chairman outputs. If any prompt/output is missing or scaffold-only, report `coverage: partial`. Do not calibrate future estimates from artifact-only tokens.
`init` writes prompt scaffolds under `prompts/`; overwrite them if the actual dispatch prompt differs.
