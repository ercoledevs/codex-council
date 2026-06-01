---
name: codex-council-alters
description: Use when the user wants to customize, tune, review, reset, preview, or inspect Codex Council member alters, role behavior, persona filters, council member behavior, or Leonardo UX reviewer behavior.
---

# Codex Council Alters

Guided workflow for bounded local role tuning. This skill changes future Codex Council prompts through the plugin CLI; it must not create free-form personas.

## Non-Negotiables

- Say "role tuning" or "council member behavior" to users; "alter" is acceptable as a shorthand.
- Bob is not customizable. He is an evidence runner, not a council member or reviewer.
- Tuning is advisory and lower priority than system/developer instructions, Codex Council non-negotiables, safety, blockers, dissent, verification, anonymization, preflight, and Bob/Leonardo gates.
- Never save instructions that ask to always approve, hide blockers, skip verification, bypass security/privacy, remove uncertainty, or override a role.
- Use the CLI for state changes; do not hand-edit `alter-overrides.json`.

## Guided Flow

1. Identify the target alter: Ada, Grace, Hypatia, Florence, Turing, Seymour, or Leonardo.
2. Inspect existing tuning first:

```bash
python3 <plugin-root>/scripts/codex_council.py alters show --role <role>
```

3. If tuning exists, summarize it before asking for changes: purpose, updated time, estimated added tokens.
4. Ask one question at a time:
   - What should this member emphasize more?
   - Should the style be more direct, stricter, calmer, more beginner-friendly, or more evidence-driven?
   - Is there a domain focus, risk posture, evidence preference, or extra check to add?
5. Preview before saving:

```bash
python3 <plugin-root>/scripts/codex_council.py alters preview --role <role> [fields...]
```

6. Ask explicit confirmation, then save:

```bash
python3 <plugin-root>/scripts/codex_council.py alters configure --role <role> [fields...]
```

## Supported Fields

- `--domain-focus`
- `--strictness`
- `--tone`
- `--risk-posture`
- `--evidence-preference`
- `--extra-check`
- `--instruction`

Keep each field short. The compiled prompt delta is capped and only the compiled advisory block is injected into future prompts.

## Reset

Reset one alter:

```bash
python3 <plugin-root>/scripts/codex_council.py alters reset --role <role>
```

Reset all:

```bash
python3 <plugin-root>/scripts/codex_council.py alters reset --all
```

## Output

After save/reset, report the role, summary, estimated added tokens, and config path. Remind the user that future council runs disclose active role tuning before dispatch.
