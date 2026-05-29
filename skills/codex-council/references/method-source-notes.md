# Method Source Notes

Use this only for source grounding, provenance, or publication.

## Primary Open Source Reference

Repository: https://github.com/karpathy/llm-council

Public documentation: https://llm-council.dev/

Attribution/audit details are intentionally omitted from routine council runs. Load source-audit notes only when publishing, redistributing, or discussing provenance.

Observed summary from `karpathy/llm-council`:

- The project groups multiple LLM providers into an "LLM Council" through OpenRouter.
- Stage 1 collects independent first responses from all configured models.
- Stage 2 anonymizes candidate responses before peer review so reviewers rank work rather than provider identity.
- Peer review asks for judgment on accuracy and insight.
- Stage 3 uses a designated Chairman model to compile the final answer.
- The upstream README frames the app as a simple local web app and an experimental reference, not a production governance system.

## Preserve

- Parallel independent first pass: members produce first opinions before seeing other candidates.
- Candidate inspection: keep individual member outputs available for audit instead of hiding all intermediate reasoning.
- Anonymous peer review: strip role/agent names and use Candidate A-F labels before review.
- Ranking plus scoring: collect preference order, rubric scores, and concrete justifications.
- Chairman synthesis: final answer is not a raw vote; it is a synthesis that preserves blockers, dissent, and evidence gaps.
- Failure tolerance: if some members fail, continue when enough evidence remains and disclose degraded coverage.

## Codex Adaptation

Diversity comes from independent role prompts, context framing, and review rubric, not different vendors. The main Codex agent is Chairman. Deterministic aggregation is local when reviewer JSON exists.

Because Codex Council does not call multiple model providers, never claim that role prompts are equivalent to true model diversity. The correct claim is narrower: role isolation and anonymous review reduce single-pass anchoring and make dissent easier to surface inside Codex.

## Broader LLM Council Design References

Useful public design details from https://llm-council.dev/:

- support confidence tiers so low-risk questions do not pay for a maximal council
- support jury-style go/no-go decisions for binary approval gates
- use architecture decisions, code review, content validation, and complex problem solving as natural council use cases
- anonymize responses to reduce self-preference, provider loyalty, and model recognition
- exclude self-votes when a candidate evaluates itself or use independent reviewers instead
- collect rankings, numeric scores, and justifications
- continue when some members fail
- prefer simple normalized score averaging for 3 to 5 reviewers instead of complex voting systems
- use structured rubric dimensions such as accuracy, completeness, conciseness, clarity, and relevance
- treat bias metrics as indicators unless enough sessions have been persisted
- expose quality metrics and alerts rather than presenting a binary magic answer

## Workflow Inspiration

Repository: https://github.com/chrisblattman/claudeblattman

Useful transferable patterns from its `/council` skill:

- single-round parallel critics
- separate synthesis pass over raw outputs
- task-type panel routing
- compact skill/tool review panel
- meta-reference guard before dispatch
- fail-fast setup checks
- visible dispatch announcement
- compact invocation logging

Codex Council adopts these as local Codex workflow patterns only. It intentionally does not copy cross-vendor peer-swap behavior because this plugin remains Codex-only.

## Stance

Codex Council intentionally avoids:

- requiring external APIs
- pretending role prompts are equivalent to model diversity
- overfitting complex voting theory to small reviewer counts
- hiding dissent
- turning advisory review into an automatic approval without user context

## Token Optimization Sources

Public OpenAI guidance used for this plugin:

- Prompt caching: https://platform.openai.com/docs/guides/prompt-caching
- Prompting: https://platform.openai.com/docs/guides/prompting
- Latency optimization: https://platform.openai.com/docs/guides/latency-optimization
- Model verbosity/reasoning controls: https://platform.openai.com/docs/guides/latest-model

Applied tactics:

- Keep stable instructions first and variable project context last.
- Use explicit output shapes and caps.
- Reduce output tokens first while preserving blockers, dissent, confidence, and verification.
- Load references lazily instead of putting every schema into `SKILL.md`.
- Escalate reasoning/profile only for risk, ambiguity, or irreversible work.
