# Governance Preflight

Use before Standard or Deep runs when sensitive data, subagents, publication, or irreversible changes are involved.

## Checklist

- User explicitly requested council or parallel review.
- Mode selected: fast, standard, or deep.
- Data sensitivity classified: public, internal, confidential, secret.
- Secrets/tokens/customer data checked and redacted.
- Files shared with agents are listed.
- License/provenance concerns are noted.
- Verification commands are known before final synthesis.
- Final state will be one of: approved, approved-with-risk, blocked.

## Deep Mode Required

Use Deep mode for security, privacy, data loss, migrations, irreversible edits, publication, or license/provenance decisions.

## Audit Fields

Record in `session.json`: topic, mode, status, workspace root, roles, reviewers, context files, redaction notes, verification commands, final state.

## Decision Runtime Addendum

Before a shadow projection or patch, verify session-root confinement, no symlinks,
directory/file modes `0700`/`0600`, allowlisted sources, PII/secret scanning,
session-scoped pseudonymous IDs, size/graph quotas, retention policy, and explicit
purge semantics. Hashes are integrity controls, not encryption. Runtime corruption,
unsafe permissions, policy mismatch, or incomplete impact must be reported as
`quarantined` or `ignored` with legacy fallback. A Deep gate is required before any
future runtime output can influence a verdict.
