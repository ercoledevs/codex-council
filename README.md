# Codex Council

[![Latest release](https://img.shields.io/github/v/release/ercoledevs/codex-council?label=release&color=0f6b57)](https://github.com/ercoledevs/codex-council/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f6b57)](LICENSE)
[![Website](https://img.shields.io/badge/docs-website-0f6b57)](https://ercoledevs.github.io/codex-council/)

![Codex Council cover](assets/cover.svg)

**Make Codex argue with itself before you ship.**

Codex Council turns one Codex request into a small panel review: several reviewers
answer independently, their work is anonymized and ranked on a rubric, and a Chairman
writes the final call — with a local token estimate shown up front. It runs entirely inside
Codex and **never calls a third‑party model API**.

📖 **[Website](https://ercoledevs.github.io/codex-council/)** · 🧭 **[Wiki / playbook](https://ercoledevs.github.io/codex-council/wiki.html)** · 🧠 **[Decision Runtime](https://ercoledevs.github.io/codex-council/runtime.html)** · 📝 **[Changelog](CHANGELOG.md)** · 🇮🇹 **[Italiano](https://ercoledevs.github.io/codex-council/it/)**

> **One honest caveat, up front.** The "diversity" here comes from isolated role
> prompts and anonymous review, not from multiple model vendors. That's enough to
> break single‑pass anchoring and surface dissent — it is **not** the same as a panel
> of independent labs. The whole project is built around saying that plainly.

> **New in 1.0.0:** an experimental, opt-in Decision Runtime can project completed
> sessions into deterministic Decision Cells and a simpler frontier log, compare the
> two, persist transactional shadow generations, validate typed patches, and produce
> fail-closed impact plans. Legacy Council artifacts and verdicts remain authoritative.

---

## Contents

- [When to use it](#when-to-use-it)
- [Quickstart](#quickstart)
- [How it works](#how-it-works)
- [The council](#the-council)
- [Modes & token budget](#modes--token-budget)
- [Forging proposals](#forging-proposals)
- [Codex Mind](#codex-mind)
- [Decision Runtime](#decision-runtime)
- [How to prompt it](#how-to-prompt-it)
- [Tuning roles (alters)](#tuning-roles-alters)
- [CLI reference](#cli-reference)
- [Privacy & local state](#privacy--local-state)
- [Limits](#limits)
- [Install options](#install-options)
- [Development](#development)
- [Credits & license](#credits--license)

---

## When to use it

Reach for the council when a confident, wrong answer is expensive — a migration you
can't undo, a regression users will hit, a tradeoff you can't call alone. For small,
reversible, checkable work, plain Codex is faster.

| Good fit | Skip it |
| --- | --- |
| Architecture decisions, risky diffs, migrations | Tiny edits and quick questions |
| Security, privacy, data‑loss risk | Anything you can verify yourself in a minute |
| Frontend/UX behavior and release go/no‑go | A task that just needs one straightforward answer |
| Creative implementation shaping with Codex Forge | Rubber-stamp validation |

---

## Quickstart

**1. Install** from the Codex Marketplace CLI, then reload Codex:

```bash
npx codex-marketplace add ercoledevs/codex-council --plugin --global -y
```

**2. Ask for a review** in chat — just say what to review and what you care about:

```text
Use Codex Council to review this architecture decision.
Focus on blockers, rollback, and verification.
```

**3. Accept the estimate.** Before any Standard/Deep run, the council shows a token
estimate and waits for your OK. "Use Codex Council" is a request, not permission to
spend — and `expanded` needs a separate, explicit yes.

That's it. Everything below is detail you can reach for when you need it.

---

## How it works

One request becomes four stages:

| Stage | What happens |
| --- | --- |
| **1. First opinions** | Up to six reviewers answer independently, in parallel, before seeing each other's work. |
| **2. Anonymous review** | Outputs lose their authorship (Candidate A–F) and are ranked/scored on a rubric — not on who sounds senior. |
| **3. Aggregation** | Scores combine deterministically (locally, when reviewer JSON exists). Blockers and dissent are kept, not averaged away. |
| **4. Chairman synthesis** | The main agent writes the final call from saved outputs — winner, dissent, blockers, verification. Not just "the highest score wins." |

The final answer leads with the decision and a **confidence** level (high / medium /
low / blocked), separates **blockers** from **refinements**, keeps **dissent**
visible, and lists the exact **verification** to run. Council consensus is not proof —
the verification is how you make it real.

---

## The council

A default full Standard run uses six reviewers. Opt-in adaptive panels may use fewer;
hard-risk work still returns to full coverage. Each lens guards a different concern:

| Role | Lens |
| --- | --- |
| **Ada Lovelace** — Principal Architect | boundaries, integration, maintainability, migration risk |
| **Grace Hopper** — Reliability Engineer | failure modes, tests, rollback, observability |
| **Hypatia** — Security & Governance | secrets, permissions, privacy, provenance, policy |
| **Florence Nightingale** — Product & Operator | workflow fit, docs, adoption, operational friction |
| **Alan Turing** — Contrarian Red Team | hidden assumptions, simpler alternatives, overengineering |
| **Seymour Cray** — Performance Engineer | latency, throughput, memory, cost, scale, measurement |

### Optional frontend gate

Turn it on with `--frontend-review` (or `--type frontend`) for UI/UX work:

- **Leonardo da Vinci** — a brutally honest UX/UI critic. A Leonardo blocker lowers
  final confidence even when the technical scores are high.
- **Bob** — a browser evidence runner. He drives a real browser and reports
  pass/fail. **Bob never votes**, and nothing is called "verified" until Bob (or
  equivalent browser evidence) actually ran the path.

---

## Modes & token budget

Pick the smallest mode that catches the risk. Escalate per blocker, not by default.

| Mode | Use it for |
| --- | --- |
| `fast` | small, reversible, low‑risk decisions (a single Chairman pass) |
| `standard` | implementation, architecture, and performance decisions (six members) |
| `deep` | security, data loss, migrations, irreversible changes, or a close tie |
| `--frontend-review` | UI/UX/browser behavior (adds Leonardo + Bob) |
| `--type skill --skill-review` | plugin/skill usability (a cheap three‑lens panel) |

Output detail is controlled by `--token-budget`, which defaults to `compact`:

| Budget | When |
| --- | --- |
| `compact` *(default)* | normal decisions — tight outputs, smallest reference set |
| `balanced` | real tradeoffs and ambiguity — more detail, only on the risky parts |
| `expanded` | security/data‑loss/irreversible — full evidence. **Blocked until you confirm.** |

Typed synthesis templates are available via `--type architecture|implementation|decision|skill|frontend`.

---

## Forging proposals

`codex-forge` is the creative sibling of Codex Council:

- **Forge creates** a bounded implementation proposal from several creative lenses.
- **Council judges** whether that proposal is safe, coherent, and worth shipping.

Forge uses five creator roles:

| Role | Lens |
| --- | --- |
| **Buckminster Fuller** | system shape, primitives, boundaries |
| **Hedy Lamarr** | product value, workflow fit, interaction concept |
| **Katherine Johnson** | feasibility, interfaces, implementation path |
| **Margaret Hamilton** | safety, reliability, rollback, privacy |
| **John von Neumann** | performance, complexity, cost, simplification |

The loop is deliberately bounded: one structured round by default, then a second
round — which you approve after round 1, or which starts automatically when round 1
comes back strongly discordant — and a hard cap of three. If the creators still do
not converge, Forge returns `nonconverged` with persistent dissent instead of forcing
fake consensus.

```text
Use Codex Forge to design a bounded implementation proposal for this idea.
```

```bash
python3 scripts/codex_council.py estimate --topic "Forge a release workflow" --mode standard --type forge --token-budget compact
python3 scripts/codex_council.py init --topic "Forge a release workflow" --root . --mode standard --type forge --confirm-estimate
```

Use Council after Forge when the forged proposal needs judgment.

---

## Codex Mind

`codex-mind` runs that whole arc for you — Forge, then Council, in one guided pass.
If you don't have a proposal yet, it asks what to build first. You see **one combined
estimate** up front (both stages, summed) and get a single **build / revise / stop**
call at the end, with blockers, dissent, and verification.

Each run opens with an ASCII digital‑brain banner, then:

1. Asks what to create — only if no proposal exists yet.
2. Shows one combined estimate for Forge + Council; you accept once.
3. Forges the proposal.
4. Hands only the proposal to Council — never full transcripts — and judges it.
5. Returns the verdict.

It honours stop conditions: a Forge `nonconverged` or a Council blocker pauses the run
rather than forcing it forward, so a full pipeline doesn't burst your token budget.

```text
Use Codex Mind to forge a proposal for this idea and then run it through the council.
```

---

## Decision Runtime

Version 1.0 adds a **local decision-intelligence lab** for completed sessions. It is
not a second Chairman and it never changes a verdict. It projects allowlisted legacy
evidence into two representations, compares them, and can persist the result as an
isolated transactional sidecar:

| Capability | v1.0 status |
| --- | --- |
| Decision Cell projection and typed edge patches | experimental, deterministic |
| `frontier.jsonl` baseline | experimental, deterministic |
| Cell-vs-frontier export checks and replay | experimental, non-authoritative |
| Transactional generations, `HEAD`, recovery, rollback | opt-in shadow sidecar |
| Typed JSON Decision Patches | opt-in, sidecar-only |
| Fail-closed impact plan | advisory only; never dispatches agents |
| Legacy session and verdict | stable and authoritative |
| Learned scheduling, semantic memory, automatic early exit | deferred |

The intended flow is deliberately one-way:

```text
completed legacy session
        -> deterministic projection
        -> Decision Cell <-> frontier.jsonl comparison
        -> optional shadow generation
        -> advisory impact plan
```

Start with a non-committing preview:

```bash
python3 scripts/codex_council.py cells project \
  --session <session-dir> --compare frontier --plan --json
```

When the preview is useful, persist the first transactional shadow generation
explicitly, then inspect its health:

```bash
python3 scripts/codex_council.py cells project \
  --session <session-dir> --compare frontier --commit --plan --json
python3 scripts/codex_council.py cells doctor \
  --session <session-dir> --json
```

A committed generation is required before applying a typed patch or planning from
`HEAD`.

Opt in at scaffold time with `init --decision-runtime shadow`, or project an older
completed session explicitly. Runtime data lives inside that session under
`decision-runtime/`; directories use restrictive permissions, writes are
single-writer and generational, and every interrupted switch leaves an old-or-new
valid `HEAD` while every legacy artifact remains unchanged. `ignored` and
`quarantined` always mean “use legacy”.

Typed patches must be standalone validated JSON. Arbitrary Markdown/model prose is
never parsed as a patch. Hashes and session-scoped IDs provide integrity and
pseudonymization, not encryption or correctness. Retention is reported by `doctor`
and applied only by an explicit purge command.

See the [Decision Runtime showcase](https://ercoledevs.github.io/codex-council/runtime.html)
for the product view, or the [technical contract](skills/codex-council/references/decision-runtime.md)
for schemas, recovery states, replay gates, and the deferred roadmap.

---

## How to prompt it

A council prompt isn't a question — it's a decision to pressure‑test. The shape that
works:

```text
[Standard|Deep|Frontend] Council: review <the specific decision>.
Context: <the diff, files, or links it should look at>.
Constraints: <hard limits — compatibility, deadline, budget>.
Return: blockers, dissent, confidence, the safest v1, and the exact verification.
```

A few ready‑to‑use examples:

```text
Council review this diff.
Focus on regressions, missing tests, and performance impact.
```

```text
Deep Council: review this migration for security, rollback, and data-loss risk.
```

```text
Frontend Council: review this modal flow with Leonardo and have Bob verify
the browser interaction cases before Chairman synthesis.
```

**Tips:** name the mode (it sets cost and scrutiny), give it a real decision rather
than a vibe, point at evidence, and state your hard constraints. Don't ask it to "just
confirm" — the council preserves dissent on purpose. Explaining the council ("how does
it work?") is not running it; an ambiguous ask gets one clarifying line, no dispatch.

➡️ The [Wiki](https://ercoledevs.github.io/codex-council/wiki.html) has a 16‑recipe
cookbook with paste‑ready prompts for common situations.

---

## Tuning roles (alters)

An **alter** is a bounded, local tweak to how one reviewer behaves — make Ada blunter,
point Seymour at database cost, tell Leonardo to stop being polite about bad UI.

Tuning is **advisory only**: it can sharpen focus and tone, but it can never remove
blockers, dissent, verification, anonymization, or Bob's non‑voting status. Bob isn't
tunable. Always preview before saving:

```bash
python3 scripts/codex_council.py alters preview --role leonardo \
  --tone "more brutally honest about confusing interaction design" \
  --domain-focus "mobile UI, modal accessibility, and click-through regressions"
```

See [CLI reference → Tune roles](#cli-reference) for the full command set.

---

## CLI reference

The helper script (`scripts/codex_council.py`) is stdlib‑only. For everyday use you
don't need it at all — ask in chat. The CLI is for **traceable sessions, estimates,
scoring, and stats** you want to keep. Sections are collapsed; click to expand.

<details>
<summary><b>Setup & estimate</b></summary>

```bash
# Configure the local consumer profile used for estimates (stored with consent).
python3 scripts/codex_council.py profile --plan Plus --model GPT-5.3-Codex --reasoning medium

# Show the first-run questions when no profile exists.
python3 scripts/codex_council.py profile

# Estimate before starting, then accept the range.
python3 scripts/codex_council.py estimate --topic "Architecture Review" --mode standard --token-budget compact

# Optional adaptive router preview. Hard-risk flags still force full coverage.
python3 scripts/codex_council.py estimate --topic "Docs cleanup" --router auto --panel auto --json

# Is this a real run, or just talking about the council?
python3 scripts/codex_council.py classify-invocation --text "explain how council works"
```
</details>

<details>
<summary><b>Run a traceable session</b></summary>

```bash
# Scaffold a session after accepting the estimate. --root is the workspace analyzed;
# artifacts are stored in plugin-local .codex-council/sessions/, never in your project.
python3 scripts/codex_council.py init --topic "Architecture Review" --root . \
  --mode standard --token-budget compact --confirm-estimate

# Frontend session (Leonardo + Bob).
python3 scripts/codex_council.py init --topic "Modal Review" --root . \
  --mode standard --frontend-review --confirm-estimate

# Compact skill/tool review session.
python3 scripts/codex_council.py init --topic "Skill Review" --root . \
  --type skill --skill-review --confirm-estimate

# Optional targeted/triad panel. Recorded in router-decision.json.
python3 scripts/codex_council.py init --topic "Low-risk docs cleanup" --root . \
  --router auto --panel auto --confirm-estimate

# Creative proposal forging session.
python3 scripts/codex_council.py init --topic "Forge a Release Workflow" --root . \
  --type forge --token-budget compact --confirm-estimate

# expanded must be confirmed explicitly.
python3 scripts/codex_council.py init --topic "Migration Review" --root . \
  --mode deep --token-budget expanded --confirm-expanded

# Optional: ASCII banner (terminal) or a one-line dispatch announcement.
python3 scripts/codex_council.py init --topic "Architecture Review" --root . --banner
python3 scripts/codex_council.py init --topic "Decision Review" --root . --type decision --announce --confirm-estimate
```
</details>

<details>
<summary><b>Score, validate & close out</b></summary>

```bash
# Aggregate reviewer scores from a JSON file (use --compact for compact JSON).
python3 scripts/codex_council.py score --input reviews.json

# Assess Forge convergence from saved round scores.
python3 scripts/codex_council.py forge-convergence --input forge-scores.json

# Validate a generated session.
python3 scripts/codex_council.py validate-session --session <printed-session-dir>

# Read-only health check for session integrity and partial coverage.
python3 scripts/codex_council.py doctor --session <printed-session-dir>

# End-of-session stats; --write persists stats.json and stats.md.
python3 scripts/codex_council.py stats --session <printed-session-dir> --write

# Dashboard across local session history.
python3 scripts/codex_council.py dashboard

# Compile/deduplicate a small context packet before dispatch.
python3 scripts/codex_council.py compile-context --topic "Review handoff reports" \
  --constraint "No public links" --constraint "No public links" --json

# Optional: path-only raw bundle, and compact pre/post history (with consent).
python3 scripts/codex_council.py stats --session <printed-session-dir> --write --raw-bundle
python3 scripts/codex_council.py stats --session <printed-session-dir> --write --record-history
```

Stats are **local estimates**, not actual Codex token usage, billing telemetry, or
exact tool‑call accounting. They separate `pre_execution_estimate`,
`post_execution_estimate`, and `artifact_only_tokens`; if prompts or outputs are
missing, coverage is reported as `partial`.

Every scaffolded session also writes a compact intelligence layer:
`context-capsule.json`, `run-manifest.json`, `decision-ledger.json`,
`findings.jsonl`, `telemetry.json`, `router-decision.json`, and
`compiled-context.json`.
</details>

<details>
<summary><b>Decision Runtime lab</b></summary>

```bash
# Persist a completed session as a shadow generation and show advisory impact.
python3 scripts/codex_council.py cells project --session <session-dir> \
  --compare frontier --commit --plan --json

# Apply a strict standalone JSON patch to the shadow sidecar only.
python3 scripts/codex_council.py cells apply --session <session-dir> \
  --patch patch.json --json

# Read-only health and advisory planning.
python3 scripts/codex_council.py cells doctor --session <session-dir> --json
python3 scripts/codex_council.py cells plan --session <session-dir> \
  --changed <cell-id> --json

# Explicit operator actions; none touches legacy artifacts.
python3 scripts/codex_council.py cells recover --session <session-dir> --json
python3 scripts/codex_council.py cells rollback --session <session-dir> \
  --to <generation> --json
python3 scripts/codex_council.py cells purge --session <session-dir> \
  --expired --json

# Reproducible evaluation on a sanitized local corpus.
python3 scripts/codex_council.py cells replay --corpus <corpus-dir> \
  --compare frontier --repetitions 10 --json
python3 scripts/codex_council.py cells fault-test --corpus <corpus-dir> --json
```

Persisted health states are `healthy`, `ignored`, `recovered`, or `quarantined`. Impact plans
are always `advisory_only: true` and `authoritative: false`. Privacy/security/data-loss
or ambiguous dependencies force full coverage. No v1 command automatically reruns a
reviewer, changes a verdict, or deletes expired data.
</details>

<details>
<summary><b>Tune roles (alters)</b></summary>

```bash
# Inspect current tuning.
python3 scripts/codex_council.py alters list
python3 scripts/codex_council.py alters show --role ada

# Preview, then save (Ada, Grace, Hypatia, Florence, Turing, Seymour, Leonardo).
python3 scripts/codex_council.py alters preview   --role ada --tone "more direct" --domain-focus "API design and maintainability"
python3 scripts/codex_council.py alters configure --role ada --tone "more direct" --domain-focus "API design and maintainability"

# Reset one role or all tuning.
python3 scripts/codex_council.py alters reset --role ada
python3 scripts/codex_council.py alters reset --all
```

Supported fields: `--domain-focus`, `--strictness`, `--tone`, `--risk-posture`,
`--evidence-preference`, `--extra-check`, `--instruction`. Use the CLI for changes —
don't hand‑edit `alter-overrides.json`.
</details>

<details>
<summary><b>Maintain</b></summary>

```bash
# Strict plugin validation.
python3 scripts/codex_council.py validate --plugin-root . --strict

# Check for a newer GitHub release (--json for machine-readable output).
python3 scripts/codex_council.py check-update

# Run the test suite.
python3 -m unittest discover -s tests -v
```
</details>

---

## Privacy & local state

The council keeps its runtime artifacts — session scaffolds, estimates, prompts,
outputs, stats, history, and alter overrides — in plugin‑local `.codex-council/`,
**not inside your project**, and the folder is gitignored. So you can reuse profiles
and learning history across projects without polluting any repo.

- Invocation logs are compact JSONL and **never** store prompt text, raw output,
  secrets, topics, workspace roots, or absolute paths.
- The consumer profile stores only your declared plan/model/reasoning and compact
  aggregate history — never prompts or transcripts.
- State lives in a stable parent (`codex-council/.codex-council/`) so tuning and
  history survive plugin updates. Override paths with `CODEX_COUNCIL_STATE_ROOT`,
  `CODEX_COUNCIL_HOME`, or `CODEX_COUNCIL_SESSION_ROOT`.
- Experimental Decision Runtime state is session-scoped and opt-in; IDs and source
  references are session-pseudonymous, while decision text remains readable local
  data. It is excluded from legacy token stats. Runtime directories/files use `0700`/`0600`,
  reject symlinks/path escape, and fail closed to legacy on unsafe state.
- Runtime retention never deletes automatically. `doctor` only reports expiry;
  explicit purge never touches legacy artifacts and preserves current `HEAD` unless
  the operator confirms a full runtime purge with the session ID.

---

## Limits

Read these before you rely on it:

- **Consensus is not proof.** This is an advisory workflow, not a legal, security, or
  compliance approval system. Always run the verification.
- **Not multi‑vendor diversity.** Role isolation reduces single‑pass anchoring; it does
  not equal multiple independent model providers.
- **No fake UI verification.** UI behavior isn't "verified" unless Bob, or equivalent
  browser evidence, actually ran the path.
- **No billing telemetry.** Token reports are local heuristics, not your real Codex
  usage or remaining quota — check **Codex Settings → Usage** for that.
- **`expanded` is gated.** It can consume a lot of usage, so it never runs without
  explicit confirmation. Prefer expanding one blocker over a whole session.
- Use **Deep mode** for sensitive, irreversible, privacy, security, migration, or
  data‑loss decisions.
- **Decision Runtime is experimental.** Its patches and impact plans are sidecar-only
  and advisory. `healthy` is integrity evidence, not proof that a decision is true.
- **No efficiency promise yet.** Cell/frontier size and replay timing can be measured,
  but token/latency improvements require paired workloads and are not release claims.

---

## Install options

<details>
<summary><b>Project vs. global scope</b></summary>

```bash
# Pick scope when prompted, or set it explicitly:
npx codex-marketplace add ercoledevs/codex-council --plugin --project
npx codex-marketplace add ercoledevs/codex-council --plugin --global

# Non-interactive:
npx codex-marketplace add ercoledevs/codex-council --plugin --global -y
```

Restart or reload Codex after installing or updating.
</details>

<details>
<summary><b>Update</b></summary>

Re‑run the install command to pull the latest version:

```bash
npx codex-marketplace add ercoledevs/codex-council --plugin --global -y
```

Then reload Codex. To get notified of new versions, **Watch** the repo →
**Custom** → enable **Releases**. You can also check from the CLI:

```bash
python3 scripts/codex_council.py check-update
```

Upgrading from 0.x to 1.0 is additive: existing sessions, profiles, alters, Markdown,
ledger, findings, and stats need no migration. Decision Runtime is off by default;
old sessions participate only when you explicitly run `cells project`.
</details>

<details>
<summary><b>Manual install</b></summary>

Clone into your local Codex plugin directory:

```bash
mkdir -p ~/plugins
git clone https://github.com/ercoledevs/codex-council.git ~/plugins/codex-council
```

Add it to your local marketplace file (usually `~/.agents/plugins/marketplace.json`):

```json
{
  "name": "codex-council",
  "source": { "source": "local", "path": "./plugins/codex-council" },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
  "category": "Productivity"
}
```

Restart or reload Codex after adding the plugin.
</details>

---

## Development

```bash
# Tests
python3 -m unittest discover -s tests -v

# Decision Runtime replay/fault harness on sanitized fixtures
python3 scripts/codex_council.py cells replay \
  --corpus tests/fixtures/council_cells --compare frontier --repetitions 10 --json
python3 scripts/codex_council.py cells fault-test \
  --corpus tests/fixtures/council_cells --json

# Strict validation
python3 scripts/codex_council.py validate --plugin-root . --strict

# Before publishing, check for stray local artifacts
find . -name '.DS_Store' -o -name '._*' -o -name '__pycache__' -o -name '*.pyc'
```

Repository layout:

```text
codex-council/
├── .codex-plugin/plugin.json        # plugin manifest
├── scripts/codex_council.py         # stdlib-only helper CLI
├── scripts/council_cells.py         # experimental shadow Decision Runtime
├── skills/codex-council/            # the skill + reference docs
│   ├── SKILL.md
│   └── references/                  # roles, rubric, protocol, token budget, …
├── skills/codex-council-alters/     # role-tuning skill
├── skills/codex-forge/              # creative proposal forging skill
├── docs/                            # the website (GitHub Pages)
├── CHANGELOG.md
├── assets/
├── tests/
└── PROVENANCE.md
```

The public site in `docs/` is published with GitHub Pages from the `main` branch
(`/docs` folder) → https://ercoledevs.github.io/codex-council/

---

## Credits & license

Inspired by the public **LLM Council** pattern:

- [karpathy/llm-council](https://github.com/karpathy/llm-council)
- [llm-council.dev](https://llm-council.dev/)

The original asks multiple independent models for answers, anonymizes them for peer
review/ranking, then has a Chairman model synthesize the result. Codex Council keeps
that decision shape while adapting execution to Codex roles, optional Codex subagents,
and local deterministic scoring. Additional workflow patterns (single‑round critics, a
separate synthesis pass, typed panels, fail‑fast setup checks, compact invocation
logging) are adapted from Chris Blattman's Claude council pattern — without adding any
cross‑vendor model calls. See [PROVENANCE.md](PROVENANCE.md) for details.

Licensed under the [MIT License](LICENSE).
