# Adaptive architecture interview

The lead owns one conversation. Use this protocol whenever a missing decision could change the interface, ownership, cost, acceptance test or rollback. For a well-specified task, reuse the supplied answers immediately.

1. Restate the desired outcome and a concrete first use. Read the repository for facts. Separate material user decisions from facts and reversible implementation details.
2. Make a small decision tree in dependency order. Ask at most three independent questions per message. Ask one when its answer determines the next branch. Explain the consequence and give a recommendation the user can correct. Match the user's language. Continue for as many rounds as the open decisions justify.
3. Have each participating specialist surface questions from its lens. The lead merges duplicates and checks for answers already in the brief. While a decision is open, explore independent branches. Only rerun the affected lens when its input changes.
4. Record an actual answer as a decision. Record a delegated, reversible detail as an assumption with a way to change it. Silence cannot settle a consequential trade-off. If the user stops, give the partial brief and the next question. When an earlier answer changes, reopen every dependent decision and discard irrelevant branches.
5. Stop when each material choice is answered, explicitly delegated, or identified as a blocker. Read back the first slice, constraints and acceptance example. Respect earlier implementation authorization within that scope. Reopen the interview only for new information that changes the design.

## From an empty repository to a working slice

Start with an actor, a trigger and an observable result. Ask who owns the data, what crosses the boundary, what happens on retries or concurrent requests, and which quality constraint would change the design. Turn a vague target into a scenario with load, disruption, expected response and measurable threshold. Distinguish a user's requirement from a target you propose measuring.

Forge returns one buildable design: component responsibilities, interface and data contracts, invariants, alternatives with a reason for the choice, failure recovery, an end-to-end first slice and a test the operator can run. Keep only fields relevant to the project. Council tests the most consequential assumption against a counterexample. Hyper implements the authorized slice through its real entry point, executes the acceptance and failure checks, then proceeds through the remaining approved slices in dependency order.

Example: a queue accepts a job twice after a timeout. Who supplies the stable key? Once decided, ask how long duplicate submissions must collapse and what callers should see after expiry. A test submits the key twice, kills a worker after delivery, restarts it, and counts durable side effects. An expiry policy and an exactly-once side-effect requirement are separate decisions.

## Optional local brief

Keep a short conversation in memory. For a longer interview, the lead can use an editable local JSON brief. Run from the plugin root:

```sh
python3 scripts/codex_council.py interview --start "Recover an interrupted job" > brief.json
python3 scripts/codex_council.py interview --input brief.json --json
```

Use a fresh path for a new brief. Each decision has a unique `id`, a `question` and optional prerequisite IDs in `after`. Adapt, add and remove branches for this project. Add a `recommendation` to explain a choice, an `answer` to settle it, or an `assumption` for a delegated reversible detail. Pass only the next relevant questions from `frontier` to the user. `waiting` contains decisions behind open prerequisites. Repeat after each answer. The command is read-only. A ready brief can be passed to both `estimate` and `init` with `--brief brief.json`. They consume the same compact decision summary. Keep transcripts and secrets out of the file. Readiness describes the supplied tree; the lead still checks coverage and authorization.
