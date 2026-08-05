# Codex Council

[![Latest release](https://img.shields.io/github/v/release/ercoledevs/codex-council?label=release&color=0f6b57)](https://github.com/ercoledevs/codex-council/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f6b57)](LICENSE)
[![Website](https://img.shields.io/badge/docs-website-0f6b57)](https://ercoledevs.github.io/codex-council/)

![Codex Council cover](assets/cover.svg)

**From an idea to reviewed, verified code in Codex.**

Codex Council is an open-source development workflow plugin for Codex. Forge turns
goals and constraints into an implementation proposal. Council challenges that
proposal through isolated roles and anonymous review. Mind coordinates the gates.
Hyper applies an authorized change to the repository and closes only on executed
checks and a mandatory falsification pass. Estimates are local and shown before each
costly stage; the plugin does not call third-party model APIs.

Maintained independently by [@ercoledevs](https://github.com/ercoledevs);
source, releases, changes, and issues stay public.

📖 **[Website](https://ercoledevs.github.io/codex-council/)** ·
🧭 **[Wiki](https://ercoledevs.github.io/codex-council/wiki.html)** ·
✅ **[Completed run](https://ercoledevs.github.io/codex-council/examples.html)** ·
💻 **[Source](https://github.com/ercoledevs/codex-council)** ·
📦 **[Releases](https://github.com/ercoledevs/codex-council/releases)** ·
📝 **[Changelog](CHANGELOG.md)** ·
🐛 **[Issues](https://github.com/ercoledevs/codex-council/issues)** ·
🇮🇹 **[Italiano](https://ercoledevs.github.io/codex-council/it/)**

> Role separation can make anchoring and dissent easier to inspect. It is not
> multi-vendor independence and does not prove correctness. Project checks still
> decide whether a change is ready.

> **Included in the current release:** Council, Forge, Mind, Hyper, Alters, frontend
> evidence review, local session tooling, and Decision Runtime. Decision Runtime is
> released as an experimental, opt-in, non-authoritative sidecar.

---

## Contents

- [When to use it](#when-to-use-it)
- [Quickstart](#quickstart)
- [How it works](#how-it-works)
- [The council](#the-council)
- [Modes & token budget](#modes--token-budget)
- [Forging proposals](#forging-proposals)
- [Codex Mind](#codex-mind)
- [Codex Hyper](#codex-hyper)
- [Decision Runtime](#decision-runtime)
- [How to prompt it](#how-to-prompt-it)
- [Tuning roles (alters)](#tuning-roles-alters)
- [CLI reference](#cli-reference)
- [Privacy & local state](#privacy--local-state)
- [Limits](#limits)
- [Install options](#install-options)
- [Development](#development)
- [Why I built it](#why-i-built-it)
- [Credits & license](#credits--license)

---

## When to use it

Use Codex Council when a development task needs more structure than one direct
implementation pass: the proposal is still unclear, the decision is expensive to
reverse, or the repository change needs independent falsification. For small,
reversible work with an obvious check, plain Codex is usually enough.

| Good fit | Skip it |
| --- | --- |
| Idea → proposal → review → implementation | Tiny edits and quick questions |
| Architecture decisions, risky diffs, migrations | A localized fix with one obvious test |
| Security, privacy, data‑loss risk | Anything you can verify yourself in a minute |
| Frontend/UX behavior and release go/no‑go | A task that just needs one straightforward answer |
| Creative implementation shaping with Codex Forge | Rubber-stamp validation |

---

## Quickstart

**1. Install** from the Codex Marketplace CLI, then reload Codex:

```bash
npx codex-marketplace add ercoledevs/codex-council --plugin --global -y
```

**2. Ask for the full development path** in chat:

```text
Use $codex-council:codex-mind to turn this request into an implementation proposal,
review it, and—only if the verdict is build with no blockers—offer
$codex-council:codex-hyper to implement it. Show each estimate and ask before editing.
```

**3. Accept the gates.** Mind shows one estimate for Forge + Council. If the result
is a blocker-free `build`, Mind shows the Hyper execution preflight, confirms
authorization already given for the unchanged scope or obtains it if missing, then
invokes Hyper. Material scope, risk, or sensitive actions require fresh authorization.
`expanded` always needs an additional explicit yes.

That's it. Everything below is detail you can reach for when you need it.

---

## How it works

The complete path has four owned stages:

| Stage | Owner | Concrete output |
| --- | --- | --- |
| **1. Propose** | Forge | One bounded implementation proposal, or `nonconverged` with dissent. |
| **2. Review** | Council | A Final Call with approval status, blockers, dissent, confidence, and required verification. |
| **3. Gate** | Mind | `build`, `revise`, or `stop`, plus a controlled handoff that stops on nonconvergence, blockers, scope drift, or missing authorization. |
| **4. Implement** | Hyper | Repository changes, executed checks, falsification result, rollback, and residual risk. Relay adds a fresh verifier. |

Use Mind for the full sequence or invoke Forge, Council, and Hyper separately when
the task already starts at a later stage.

### How Council reviews

A Council review uses four steps:

| Stage | What happens |
| --- | --- |
| **1. First opinions** | Up to six isolated role prompts run in parallel before seeing each other's work. |
| **2. Anonymous review** | Outputs lose their authorship (Candidate A–F) and are ranked/scored on a rubric — not on who sounds senior. |
| **3. Aggregation** | Scores combine deterministically (locally, when reviewer JSON exists). Blockers and dissent are kept, not averaged away. |
| **4. Chairman synthesis** | The main agent writes the final call from saved outputs — decision, confidence, dissent, blockers, and verification. |

The final answer leads with the decision and a **confidence** level (high / medium /
low / blocked), separates **blockers** from **refinements**, keeps **dissent**
visible, and lists the exact **verification** to run. Council consensus is not proof —
the verification is how you make it real.

---

## The council

A default full Standard run uses six role members, then blinded review. Its
scaffold prepares Performance Impact Reviewer and Coverage Integrator roles;
deterministic scoring runs only when complete reviewer JSON exists. Opt-in
adaptive panels may use fewer; hard-risk work still returns to full coverage.
Each lens guards a different concern:

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

- **Leonardo da Vinci** — a UX/UI reviewer focused on interaction quality,
  accessibility, and visible regressions. A Leonardo blocker lowers final confidence.
- **Bob** — a browser evidence runner. When a target and browser tool are
  available, he attempts the requested path and reports PASS / FAIL / UNKNOWN.
  **Bob never votes**; UI behavior is verified only for paths that actually ran.

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
| `expanded` | larger context and output allowance for hard cases. It does not guarantee complete evidence. **Blocked until you confirm.** |

Typed synthesis templates are available via `--type architecture|implementation|decision|skill|frontend`.

---

## Forging proposals

`codex-forge` turns an idea into one bounded, review-ready proposal:

- **Forge creates** a bounded implementation proposal from several creative lenses.
- **Council reviews** the proposal for blockers, dissent, and required verification.

Forge uses five creator roles:

| Role | Lens |
| --- | --- |
| **Buckminster Fuller** | system shape, primitives, boundaries |
| **Hedy Lamarr** | product value, workflow fit, interaction concept |
| **Katherine Johnson** | feasibility, interfaces, implementation path |
| **Margaret Hamilton** | safety, reliability, rollback, privacy |
| **John von Neumann** | performance, complexity, cost, simplification |

The loop is bounded: one structured round by default, then a second
round — which you approve after round 1, or which starts automatically when round 1
comes back strongly discordant — and a hard cap of three. If the creators still do
not converge, Forge returns `nonconverged` with persistent dissent instead of forcing
consensus. Forge proposes; it does not verify correctness.

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

`codex-mind` runs Forge, then Council, under one accepted deliberation estimate. If
you do not have a proposal yet, Mind asks what to create. It passes the proposal—not
the full Forge transcripts—to Council and returns one **build / revise / stop**
decision with blockers, dissent, and verification.

Each run opens with an ASCII digital‑brain banner, then:

1. Asks what to create — only if no proposal exists yet.
2. Shows one combined estimate for Forge + Council; you accept once.
3. Forges the proposal.
4. Hands only the proposal to Council — never full transcripts — and judges it.
5. Returns the verdict.
6. It may hand the approved scope to the bundled Hyper workflow only when
   implementation was explicitly requested, the verdict is `build`, no live blocker
   remains, and `$codex-council:codex-hyper` is available.
7. After authorization is confirmed, Hyper enters Relay, implements the approved
   scope through one root writer, runs falsification, and returns `completed` or
   `blocked` with `PASS`, `FAIL`, or `UNKNOWN` evidence.

It honours stop conditions: a Forge `nonconverged` or a Council blocker pauses the run
rather than forcing it forward, so a full pipeline doesn't burst your token budget.
Hyper remains a separate, optional implementation step. Mind closes the Council
agents, passes only the approved scope and evidence, then shows a separate execution
preflight. It confirms authorization already given for the unchanged scope or obtains
it if missing; material scope or risk changes require fresh authorization. If the
bundled Hyper skill fails its availability check, Mind returns a ready handoff and
asks for a plugin reload instead of emulating it. Material scope drift sends the
proposal back to `revise`.

```text
Use Codex Mind to forge a proposal for this idea and run it through the council. If the
verdict is build with no blockers, offer $codex-council:codex-hyper for implementation and show its
separate execution preflight before proceeding.
```

---

## Codex Hyper

`codex-hyper` is the implementation workflow bundled with Codex Council. Invoke it
directly for a complex authorized code change, or let Mind hand it a blocker-free
`build`. A Mind handoff requires a Council `build` plus valid implementation
authorization; direct Hyper invocation needs an authorized implementation request,
but not a prior Council run.

Hyper chooses the smallest justified route:

| Route | Use it when | Topology |
| --- | --- | --- |
| **Solo** | A direct Hyper task is clear, localized, reversible, low-risk, and has a deterministic check. | Root Codex inspects, writes, tests, and reviews. |
| **Relay** | Every approved Mind handoff; also direct tasks where root cause, impact, contracts, concurrency, data, build, or deployment need separate investigation. | One or two bounded read-only explorers → root-only writer → fresh read-only verifier. |

Its method is explicit:

1. **Contract** — define observable done, scope, constraints, rollback, checks, and route.
2. **Observe** — read repository rules, worktree, code, tests, and the smallest safe baseline.
3. **Orient** — verify claims against source and map every acceptance criterion to evidence.
4. **Act** — apply small reversible patches and run focused checks after meaningful increments.
5. **Falsify** — challenge the contract, raw diff, and raw check results; Relay uses a fresh read-only verifier, while Solo reports its reduced independent coverage. Critical `FAIL` or `UNKNOWN` blocks completion.
6. **Close** — reconcile every done item, inspect the final diff, report rollback and residual risk.

Hyper never uses parallel writers. Agent agreement is not treated as proof: conflicts
return to files, commands, tests, or reproducible counterexamples. Its execution
preflight and authorization remain distinct from Mind's Forge + Council estimate.

```text
Use $codex-council:codex-hyper to implement this change with the smallest justified agent topology and
evidence-backed verification.
```

---

## Decision Runtime

Version 1.0 adds an experimental local view of saved evidence from completed
sessions. It is not a second Chairman and does not change a verdict. It projects
allowlisted legacy artifacts into two representations, compares them, and can persist
the result as an isolated transactional sidecar:

| Capability | v1.0 status |
| --- | --- |
| Decision Cell projection and typed edge patches | experimental, deterministic |
| `frontier.jsonl` baseline | experimental, deterministic |
| Cell-vs-frontier export checks and replay | experimental, non-authoritative |
| Transactional generations, `HEAD`, recovery, rollback | opt-in shadow sidecar |
| Typed JSON Decision Patches | opt-in, sidecar-only |
| Fail-closed impact plan | advisory only; never dispatches agents |
| Legacy session and verdict | stable and authoritative |

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
for schemas, constraints, recovery states, and replay gates.

---

## How to prompt it

A useful Council prompt names the decision, evidence, constraints, and expected
verification:

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

➡️ The [Wiki](https://ercoledevs.github.io/codex-council/wiki.html) has 30
paste-ready prompt templates for common situations.

---

## Tuning roles (alters)

An **alter** is a bounded, local adjustment to one reviewer's focus, tone, or extra
checks—for example API boundaries for Ada, database cost for Seymour, or mobile
accessibility for Leonardo.

Tuning is **advisory only**: it can sharpen focus and tone, but it can never remove
blockers, dissent, verification, anonymization, or Bob's non‑voting status. Bob isn't
tunable. Always preview before saving:

```bash
python3 scripts/codex_council.py alters preview --role leonardo \
  --tone "direct about confusing interaction design" \
  --domain-focus "mobile UI, modal accessibility, and click-through regressions"
```

See [CLI reference → Tune roles](#cli-reference) for the full command set.

---

## CLI reference

The helper script (`scripts/codex_council.py`) is stdlib‑only. For everyday use you
don't need it at all — ask in chat. The CLI is for **traceable sessions, estimates,
scoring, and stats** you want to keep. `init` scaffolds session artifacts; it does
not dispatch agents or execute the review. Sections are collapsed; click to expand.

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
├── skills/codex-mind/               # guided Forge -> Council orchestration
├── skills/codex-hyper/              # bundled implementation + falsification skill
├── docs/                            # the website (GitHub Pages)
├── CHANGELOG.md
├── assets/
├── tests/
└── PROVENANCE.md
```

The public site in `docs/` is published with GitHub Pages from the `main` branch
(`/docs` folder) → https://ercoledevs.github.io/codex-council/

---

## Why I built it

I built Codex Council because one Codex pass can blur four different jobs: defining
the change, judging the design, editing the repository, and proving the result. I
wanted a repeatable path that turns an idea into a bounded proposal, exposes blockers
and dissent before implementation, then applies the authorized scope without hiding
the checks needed to close it.

I maintain the project independently. The source, releases, changelog, and issue
tracker stay public so you can inspect what changed and report what does not work.

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
