# Changelog

All notable changes to Codex Council are documented in this file.

## [1.0.0] - 2026-07-10

### Added

- Added an experimental Decision Runtime for shadow evaluation. It is explicitly
  opt-in, writes sidecar decision data for inspection, and does not influence the
  authoritative Council verdict.
- Added deterministic Decision Cell and `frontier.jsonl` projections, transactional
  shadow generations with atomic `HEAD`, strict typed JSON Decision Patches, advisory
  impact plans, explicit recovery and rollback, quarantine, retention purge, replay,
  and a fifteen-point durability fault harness.
- Added adaptive panel routing with `--router auto` and selectable
  `full`, `targeted`, `triad`, and `solo` panels. Detected privacy, security,
  data-loss, and frontend-evidence risks continue to require full coverage.
- Added compact intelligence artifacts to scaffolded sessions:
  `context-capsule.json`, `run-manifest.json`, `decision-ledger.json`,
  `findings.jsonl`, `telemetry.json`, `router-decision.json`, and
  `compiled-context.json`.
- Added `doctor` for read-only session integrity and coverage checks.
- Added `dashboard` for a local overview of Council session history.
- Added `compile-context` to normalize and deduplicate repeated constraints and
  context before dispatch.
- Added deterministic finding deduplication and explicit router decision records.
- Added a centered, fixed-width Council banner with a clearer modern layout and
  complete member, reviewer, runner, and gate status lines.

### Changed

- Session scaffolding now records routing, risk flags, active-panel coverage, and
  intelligence metadata alongside the existing prompts, reviews, and synthesis
  artifacts.
- Preflight estimates now account for the selected panel while preserving the
  existing user-acceptance gate and expanded-mode confirmation.
- Council documentation and CLI examples now cover adaptive routing, session
  diagnostics, local dashboards, context compilation, and intelligence artifacts.
- The plugin version is advanced directly to `1.0.0` to mark the new runtime and
  observability foundation.

### Safety

- The Decision Runtime is off by default, shadow-only when enabled, and
  non-authoritative. Existing Council synthesis remains the source of truth.
- Adaptive routing is advisory and opt-in. Hard-risk detection fails closed to a
  full Council rather than silently reducing review coverage.
- New intelligence and diagnostic artifacts remain plugin-local under
  `.codex-council/`; raw session state remains excluded from version control.
- `doctor` is read-only and reports missing or partial evidence instead of
  presenting incomplete sessions as fully verified.
- Token and performance figures remain local estimates. This release makes no
  claim of measured latency, throughput, or token reduction.

### Compatibility

- Existing Council, Forge, Mind, Alters, frontend-review, and skill-review flows
  remain available.
- Existing CLI defaults continue to use the full panel with routing disabled.
- Existing session files and Markdown synthesis outputs remain supported; the new
  intelligence and Decision Runtime data are additive sidecars.
- Existing plugin-local session history requires no destructive migration.
- The helper runtime remains Python standard-library only.

### Deferred

- Making Decision Runtime output authoritative or allowing it to alter verdicts.
- Cross-session semantic memory, automatic recovery without operator action, and
  automatic reuse of prior decisions.
- Incremental reviewer reruns, impact-based agent scheduling, and automated early
  convergence exits.
- Model-prose patch extraction and authoritative reducer-driven synthesis.
- Council Lattice or Council Pulse graph interfaces and interactive decision UI.
- Any performance target or efficiency claim until reproducible paired benchmarks
  establish correctness, blocker/dissent recall, determinism, and runtime cost.
- A Deep Council security gate before any experimental decision sidecar becomes
  authoritative or enabled by default.
