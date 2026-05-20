# Method Source Notes

Use this only for source grounding, provenance, or publication.

## Primary Open Source Reference

Repository: https://github.com/gauravvij/llm_council

Attribution/audit details are intentionally omitted from routine council runs. Load source-audit notes only when publishing, redistributing, or discussing provenance.

Observed summary:

- Public repository: `gauravvij/llm_council`.
- Historical HN link redirects from `abhishekgandhi-neo/llm_council`.
- README describes async multi-LLM orchestration, synthesis/voting, transparency, retries, timeouts, graceful degradation.
- GitHub API returned `license: null`, while the README says MIT. Do not reuse upstream code without verifying license state; this plugin uses a clean Codex-specific implementation and preserves method ideas only.

## Preserve

- Parallel independent first pass: the original queries council members concurrently.
- Synthesis judge: the original uses the first configured model as judge for synthesis.
- Voting fallback: the original supports a simpler majority strategy.
- Graceful degradation: failed members do not fail the whole council if at least one valid response exists.
- Transparency: individual responses are retained alongside final synthesis.
- Recommended size: 3 to 5 members balances quality, cost, and latency.
- Configuration shape: the original exposes member list, strategy, retries, timeout, and API base. `max_retries` is configured and documented, but the inspected engine did not implement retry loops.

## Codex Adaptation

Diversity comes from independent role prompts, context framing, and review rubric, not different vendors. The main Codex agent is Chairman. Deterministic aggregation is local when reviewer JSON exists.

## Broader LLM Council Design References

Useful public design details:

- anonymize responses to reduce self-preference, provider loyalty, and model recognition
- exclude self-votes when a candidate evaluates itself
- collect rankings, numeric scores, and justifications
- continue when some members fail
- prefer simple normalized score averaging for 3 to 5 reviewers instead of complex voting systems
- use structured rubric dimensions such as accuracy, completeness, conciseness, clarity, and relevance
- treat bias metrics as indicators unless enough sessions have been persisted
- expose quality metrics and alerts rather than presenting a binary magic answer

## Stance

Codex Council intentionally avoids:

- requiring external APIs
- pretending role prompts are equivalent to model diversity
- overfitting complex voting theory to small reviewer counts
- hiding dissent
- turning advisory review into an automatic approval without user context

## Token Optimization Sources

Public OpenAI guidance used for this plugin:

- Put instructions first and use clear output formats.
- Reduce fluffy wording.
- Control response length with explicit shape/length instructions.
- Reduce output tokens first; output reduction usually improves latency more than input trimming.
- Filter context and keep stable prompt prefixes before dynamic project context.
