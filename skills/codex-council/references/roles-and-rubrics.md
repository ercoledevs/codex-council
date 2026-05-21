# Roles And Rubrics

Use this file before dispatching Codex Council agents.

## Member Lenses

| Role | Focus |
| --- | --- |
| Ada Lovelace - Principal Architect | boundaries, integration, maintainability, migration risk |
| Grace Hopper - Reliability Engineer | failure modes, tests, rollback, observability |
| Hypatia - Security/Governance | secrets, permissions, privacy, provenance, policy |
| Florence Nightingale - Product/Operator | workflow fit, docs, adoption, operational friction |
| Alan Turing - Contrarian Red Team | hidden assumptions, simpler alternatives, overengineering |

Each member returns the six SKILL.md sections only. Max 3 bullets per section.

When spawning agents, put the persona name at the start of the task prompt and preserve it in status summaries. The UI may assign arbitrary nicknames; the council identity is the persona written in the prompt and generated artifacts.

## Reviewer Roles

- Rubric Reviewer: strict scoring against the weighted rubric.
- Bias Auditor: verbosity, anchoring, role prestige, overconfidence, ignored dissent.
- Implementation Gatekeeper: actionability, tests, ownership, unsafe edits, rollback.
- Leonardo da Vinci - Brutally Honest UX/UI Critic: optional frontend reviewer for counterintuitive UI, visual hierarchy, accessibility, responsive behavior, and interaction friction.

Reviewer behavior follows the council pattern: judge anonymized candidates, rank them before synthesis, and explain the ranking with concrete evidence. Do not reward a candidate for sounding senior or being longer.

Leonardo activates only for frontend/UI/UX work. He does not add a permanent scoring dimension. His findings affect existing dimensions:

- clarity: unclear hierarchy, hidden affordances, confusing copy
- relevance: decorative or theatrical UI that does not serve the workflow
- completeness: missing states, mobile behavior, accessibility, or error paths
- accuracy: false UX assumptions such as "users will discover this gesture" without affordance

A Leonardo blocker lowers final confidence even if technical scores are high.

## Evidence Runner

Bob - Browser Customer Tester is not a council member and does not score candidates. Bob runs browser/in-app-browser checks for scenarios supplied by the council, then reports pass, fail, or not verified evidence for Chairman synthesis.

## Scoring Rubric

Use 1 to 10 integer or decimal scores.

| Dimension | Weight | Meaning |
| --- | ---: | --- |
| accuracy | 0.35 | technically correct, no known false claims |
| completeness | 0.20 | covers the user's constraints and important edge cases |
| clarity | 0.20 | easy to act on, structured, low ambiguity |
| conciseness | 0.15 | avoids padding and unnecessary scope |
| relevance | 0.10 | directly serves the requested outcome |

Accuracy ceiling:

- If accuracy is below 5, cap the weighted candidate score at 4.0.
- If accuracy is 5 or 6, cap the weighted candidate score at 7.0.
- If accuracy is 7 or above, do not cap.

## Reviewer JSON Format

Use this shape for deterministic aggregation:

```json
{
  "candidates": [{"id": "A"}, {"id": "B"}],
  "reviews": [
    {
      "reviewer": "rubric-reviewer",
      "ranking": ["A", "B"],
      "scores": {
        "A": {"accuracy": 8, "completeness": 7, "clarity": 8, "conciseness": 7, "relevance": 9},
        "B": {"accuracy": 7, "completeness": 8, "clarity": 7, "conciseness": 9, "relevance": 8}
      },
      "blocking_issues": {"A": [], "B": ["Needs migration tests"]},
      "notes": {"A": "Strong fit.", "B": "Good UX, weaker integration."}
    }
  ]
}
```

If original council members perform reciprocal review, exclude each reviewer's own candidate. If that cannot be tracked without leaking identity or wasting context, use independent reviewer agents or local Chairman scoring.

## Decision Thresholds

- High: clear winner, no blocker, concrete verification.
- Medium: plausible winner with dissent or missing confirmation.
- Low: close tie, weak evidence, or significant unknowns.
- Blocked: unresolved safety, data loss, security, or correctness blocker.
