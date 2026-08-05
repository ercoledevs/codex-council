#!/usr/bin/env python3
"""Codex Council utility commands.

This script is intentionally stdlib-only. It creates traceable council session
folders and aggregates reviewer score JSON with normalized score averaging.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from . import council_cells
except ImportError:  # Direct execution: python3 scripts/codex_council.py
    import council_cells  # type: ignore[no-redef]


WEIGHTS = {
    "accuracy": 0.35,
    "completeness": 0.20,
    "clarity": 0.20,
    "conciseness": 0.15,
    "relevance": 0.10,
}

ROLE_FILES = {
    "01-ada-principal-architect.md": "Ada Lovelace - Principal Architect",
    "02-grace-reliability-engineer.md": "Grace Hopper - Reliability Engineer",
    "03-hypatia-security-governance.md": "Hypatia - Security and Governance Reviewer",
    "04-florence-product-operator.md": "Florence Nightingale - Product and Operator Advocate",
    "05-turing-contrarian-red-team.md": "Alan Turing - Contrarian Red Team",
    "06-seymour-performance-engineer.md": "Seymour Cray - Performance Engineer",
}

SKILL_REVIEW_ROLE_FILES = {
    "01-ada-skill-engineer.md": "Ada Lovelace - Skill Engineer",
    "02-florence-ux-for-tools.md": "Florence Nightingale - UX-for-Tools Critic",
    "03-grace-non-expert-adoption.md": "Grace Hopper - Non-Expert Adoption Reviewer",
}

FORGE_ROLE_FILES = {
    "01-fuller-systems-imagination.md": "Buckminster Fuller - Systems Imagination Architect",
    "02-hedy-product-invention.md": "Hedy Lamarr - Product Invention Strategist",
    "03-katherine-feasibility-integration.md": "Katherine Johnson - Feasibility and Integration Engineer",
    "04-margaret-safety-reliability.md": "Margaret Hamilton - Safety and Reliability Builder",
    "05-von-neumann-performance-complexity.md": "John von Neumann - Performance and Complexity Optimizer",
}

MEMBER_PROMPT_FILES = {
    "01-ada-principal-architect.md": "01-ada.md",
    "02-grace-reliability-engineer.md": "02-grace.md",
    "03-hypatia-security-governance.md": "03-hypatia.md",
    "04-florence-product-operator.md": "04-florence.md",
    "05-turing-contrarian-red-team.md": "05-turing.md",
    "06-seymour-performance-engineer.md": "06-seymour.md",
}

SKILL_REVIEW_PROMPT_FILES = {
    "01-ada-skill-engineer.md": "01-ada-skill-engineer.md",
    "02-florence-ux-for-tools.md": "02-florence-ux-for-tools.md",
    "03-grace-non-expert-adoption.md": "03-grace-non-expert-adoption.md",
}

FORGE_PROMPT_FILES = {
    "01-fuller-systems-imagination.md": "01-fuller.md",
    "02-hedy-product-invention.md": "02-hedy.md",
    "03-katherine-feasibility-integration.md": "03-katherine.md",
    "04-margaret-safety-reliability.md": "04-margaret.md",
    "05-von-neumann-performance-complexity.md": "05-von-neumann.md",
}

SKILL_REVIEW_LENSES = {
    "Ada Lovelace - Skill Engineer": "Will this skill/plugin work, last, stay discoverable, and avoid duplicating existing rules?",
    "Florence Nightingale - UX-for-Tools Critic": "Where does this add friction, cognitive load, brittle flags, or recovery pain?",
    "Grace Hopper - Non-Expert Adoption Reviewer": "Can a junior user invoke it and recover from failure in under 30 minutes?",
}

FORGE_LENSES = {
    "Buckminster Fuller - Systems Imagination Architect": "Generate the bold system shape, boundaries, primitives, and creative architecture.",
    "Hedy Lamarr - Product Invention Strategist": "Turn the idea into user value, workflow fit, interaction shape, and adoption hooks.",
    "Katherine Johnson - Feasibility and Integration Engineer": "Ground the idea in implementable steps, dependencies, interfaces, and constraints.",
    "Margaret Hamilton - Safety and Reliability Builder": "Surface safety, reliability, privacy, rollback, and failure-mode constraints.",
    "John von Neumann - Performance and Complexity Optimizer": "Optimize for performance, cost, latency, simplicity, and measurable efficiency.",
}

BASE_REVIEWERS = ["performance-impact-reviewer", "coverage-integrator"]
DEEP_REVIEWERS = ["rubric-reviewer", "bias-auditor", "implementation-gatekeeper"]

FRONTEND_REVIEWER_FILES = {
    "leonardo-ux-ui-critic.md": "Leonardo da Vinci - Brutally Honest UX/UI Critic",
}

EVIDENCE_RUNNER_FILES = {
    "bob-browser-customer-tester.md": "Bob - Browser Customer Tester",
}

MODES = {"fast", "standard", "deep"}
TOKEN_BUDGETS = {"compact", "balanced", "expanded"}
SESSION_TYPES = {"general", "architecture", "implementation", "decision", "skill", "frontend", "forge"}
DECISION_RUNTIME_MODES = {"off", "shadow"}
PANELS = {"full", "targeted", "triad", "solo", "auto"}
TEXT_ARTIFACT_SUFFIXES = {".json", ".md", ".txt"}
GENERATED_STATS_FILES = {"stats.json", "stats.md"}
PREFLIGHT_FILES = {"preflight-estimate.json", "preflight-estimate.md"}
SYNTHESIS_INPUT_MANIFEST = "synthesis-inputs.json"
RAW_OUTPUT_BUNDLE = "raw-output-bundle.json"
CONTEXT_CAPSULE_FILE = "context-capsule.json"
DECISION_LEDGER_FILE = "decision-ledger.json"
RUN_MANIFEST_FILE = "run-manifest.json"
FINDINGS_FILE = "findings.jsonl"
TELEMETRY_FILE = "telemetry.json"
ROUTER_DECISION_FILE = "router-decision.json"
COMPILED_CONTEXT_FILE = "compiled-context.json"
DECISION_RUNTIME_DIR = "decision-runtime"
INTELLIGENCE_SCHEMA_VERSION = 1
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
CONSUMER_FILE_VERSION = 1
ALTER_CONFIG_VERSION = 1
DEFAULT_CONSUMER_DIR = ".codex-council"
DEFAULT_SESSION_SUBDIR = "sessions"
CONSUMER_FILENAME = "consumer-profile.json"
ALTER_CONFIG_FILENAME = "alter-overrides.json"
INVOCATION_LOG_FILENAME = "invocations.jsonl"
MAX_RECENT_HISTORY = 25
MAX_HISTORY_SUMMARY_RATIOS = 40
ALTER_COMPILED_WORD_CAP = 90
ALTER_FIELD_CHAR_CAP = 180
EXPANDED_CONFIRMATION = "I understand expanded mode can consume significantly more Codex usage"
SCORING_STATS_OVERHEAD_TOKENS = 220
TOOL_OVERHEAD_PER_PROMPT_TOKENS = 35
TOOL_OVERHEAD_BASE_TOKENS = 120
FORGE_DEFAULT_ROUNDS = 1
FORGE_OPTIONAL_ROUND_CAP = 2
FORGE_HARD_ROUND_CAP = 3
FORGE_ALIGNMENT_THRESHOLD = 7.0
FORGE_SCORE_STDEV_THRESHOLD = 1.25
# Strong discord (creators disagree from the start) auto-triggers a second round;
# a near-miss below the convergence bar stays opt-in.
FORGE_STRONG_DISCORD_ALIGNMENT = 5.0
FORGE_STRONG_DISCORD_STDEV = 2.0

ROUTER_RISK_PATTERNS = {
    "privacy": r"\b(privacy|redaction|redact|pii|personal data|public link|shareable|handoff|team link)\b",
    "security": r"\b(security|secrets?|token|credentials?|permissions?|auth(?:entication|orization)?|oauth|csp|xss|csrf)\b",
    "data_loss": r"\b(data loss|delete|migration|rollback|irreversible|production|billing|payment)\b",
    "frontend_evidence": r"\b(frontend|ui|ux|browser|modal|click|focus|accessibility)\b",
    "performance": r"\b(performance|latency|throughput|memory|scale|cache|cost)\b",
}

FORGE_WEIGHTS = {
    "novelty": 0.18,
    "feasibility": 0.24,
    "user_fit": 0.20,
    "risk_control": 0.20,
    "implementation_clarity": 0.18,
}

ALTER_ROLE_CATALOG = {
    "ada": {
        "display_name": "Ada Lovelace",
        "kind": "member",
        "applies_to": ["Ada Lovelace - Principal Architect", "Ada Lovelace - Skill Engineer"],
    },
    "grace": {
        "display_name": "Grace Hopper",
        "kind": "member",
        "applies_to": ["Grace Hopper - Reliability Engineer", "Grace Hopper - Non-Expert Adoption Reviewer"],
    },
    "hypatia": {
        "display_name": "Hypatia",
        "kind": "member",
        "applies_to": ["Hypatia - Security and Governance Reviewer"],
    },
    "florence": {
        "display_name": "Florence Nightingale",
        "kind": "member",
        "applies_to": [
            "Florence Nightingale - Product and Operator Advocate",
            "Florence Nightingale - UX-for-Tools Critic",
        ],
    },
    "turing": {
        "display_name": "Alan Turing",
        "kind": "member",
        "applies_to": ["Alan Turing - Contrarian Red Team"],
    },
    "seymour": {
        "display_name": "Seymour Cray",
        "kind": "member",
        "applies_to": ["Seymour Cray - Performance Engineer"],
    },
    "leonardo": {
        "display_name": "Leonardo da Vinci",
        "kind": "reviewer",
        "applies_to": ["Leonardo da Vinci - Brutally Honest UX/UI Critic"],
    },
}

FORBIDDEN_ALTER_PATTERNS = (
    r"\b(ignore|bypass|disable|skip|remove)\b.*\b(preflight|blocker|verification|security|privacy|anonym)",
    r"\b(always approve|always accept|never block|hide blockers|hide risks|do not mention uncertainty)\b",
    r"\b(override|supersede|replace)\b.*\b(non-negotiable|system|developer|council|safety|role)\b",
    r"\b(bob)\b.*\b(member|vote|voter|candidate|council)\b",
)

CODEX_CREDIT_RATES_PER_MILLION = {
    "gpt-5.5": {"input": 125.0, "cached_input": 12.50, "output": 750.0},
    "gpt-5.4": {"input": 62.50, "cached_input": 6.250, "output": 375.0},
    "gpt-5.4-mini": {"input": 18.75, "cached_input": 1.875, "output": 113.0},
    "gpt-5.3-codex": {"input": 43.75, "cached_input": 4.375, "output": 350.0},
    "gpt-5.2": {"input": 43.75, "cached_input": 4.375, "output": 350.0},
}

REQUIRED_MEMBER_SECTIONS = [
    "## Recommendation",
    "## Rationale",
    "## Blocking Issues",
    "## Non-Blocking Improvements",
    "## Verification Required",
    "## Confidence",
]

REQUIRED_FORGE_MEMBER_SECTIONS = [
    "## Creative Proposal",
    "## Rationale",
    "## Constraints",
    "## Risks",
    "## Convergence Notes",
    "## Verification Needed",
]

PERFORMANCE_MEMBER_EXTRA_SECTIONS = [
    "## Performance Impact",
    "## Measurement Required",
]

FRONTEND_REVIEWER_SECTIONS = [
    "## UX Verdict",
    "## Counterintuitive Risk",
    "## User Harm",
    "## Required Refinement",
    "## Verification Required",
    "## Bob Test Scenarios",
]

REQUIRED_EVIDENCE_RUNNER_SECTIONS = [
    "## Mission",
    "## Scenarios From Council",
    "## Browser Checks",
    "## Browser Evidence",
    "## Reproducibility",
    "## Verdict",
]

REQUIRED_FINAL_SECTIONS = [
    "## Recommendation",
    "## Council Result",
    "## Blocking Issues",
    "## Refinements",
    "## Implementation Shape",
    "## Verification",
    "## Audit Notes",
]

REQUIRED_FORGE_FINAL_SECTIONS = [
    "## Unified Proposal",
    "## Convergence Result",
    "## Persistent Dissent",
    "## Implementation Shape",
    "## Safety And Performance Notes",
    "## Verification",
    "## Next Prompt",
]

REQUIRED_REFERENCES = [
    "competency-packs.md",
    "decision-runtime.md",
    "execution-protocol.md",
    "frontend-ux-browser.md",
    "governance-preflight.md",
    "method-source-notes.md",
    "output-contract.md",
    "roles-and-rubrics.md",
    "token-budget.md",
    "workflow-recipes.md",
]

REQUIRED_HYPER_FILES = [
    "SKILL.md",
    "FAQ.md",
    "agents/openai.yaml",
    "references/routing-policy.md",
    "references/execution-contracts.md",
    "references/evaluation-protocol.md",
]

SYNTHESIS_TEMPLATES = {
    "general": "Recommendation -> Council Result -> Blocking Issues -> Refinements -> Implementation Shape -> Verification -> Audit Notes.",
    "architecture": "Architecture verdict -> Top blockers -> Tradeoffs -> Migration/rollback shape -> Verification.",
    "implementation": "Implementation verdict -> Files/modules -> Risks -> Tests -> Rollout notes.",
    "decision": "Recommended action -> Top risks -> Reasons in favor -> Dissent -> Go/no-go confidence.",
    "skill": "Ship/revise/kill -> Top blockers -> Top patches -> Adoption risk -> First-run check.",
    "frontend": "UX verdict -> Browser evidence -> Interaction blockers -> Accessibility/mobile checks -> Verification.",
    "forge": "Unified proposal -> convergence result -> persistent dissent -> implementation shape -> safety/performance -> verification -> next prompt.",
}

DEFAULT_REPOSITORY = "ercoledevs/codex-council"
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    raw_mean: float
    normalized_mean: float
    normalized_stderr: float
    review_count: int
    blocked: bool
    blocking_issues: list[str]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)[:64] or "council-session"


def normalize_semver(value: str) -> str:
    match = SEMVER_RE.match(value.strip())
    if not match:
        raise ValueError(f"Unsupported semantic version: {value}")
    return ".".join(str(int(part)) for part in match.groups())


def semver_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in normalize_semver(value).split("."))  # type: ignore[return-value]


def compare_semver(left: str, right: str) -> int:
    left_tuple = semver_tuple(left)
    right_tuple = semver_tuple(right)
    if left_tuple < right_tuple:
        return -1
    if left_tuple > right_tuple:
        return 1
    return 0


def repository_slug(value: Optional[str]) -> str:
    if not value:
        return DEFAULT_REPOSITORY
    match = re.search(r"github\.com[:/]([^/]+)/([^/#?]+)", value)
    if not match:
        return value.strip().removesuffix(".git") or DEFAULT_REPOSITORY
    owner, repo = match.groups()
    return f"{owner}/{repo.removesuffix('.git')}"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def state_base_plugin_root(root: Optional[Path] = None) -> Path:
    root = (root or plugin_root()).expanduser()
    if SEMVER_RE.match(root.name) and root.parent.name == "codex-council":
        return root.parent
    return root


def version_local_state_root() -> Path:
    return plugin_root() / DEFAULT_CONSUMER_DIR


def plugin_state_root(state_root: Optional[Path] = None) -> Path:
    if state_root is not None:
        return state_root.expanduser()
    configured = os.environ.get("CODEX_COUNCIL_STATE_ROOT")
    if configured:
        return Path(configured).expanduser()
    return state_base_plugin_root() / DEFAULT_CONSUMER_DIR


def session_storage_root(session_root: Optional[Path] = None) -> Path:
    if session_root is not None:
        return session_root.expanduser()
    configured = os.environ.get("CODEX_COUNCIL_SESSION_ROOT")
    if configured:
        return Path(configured).expanduser()
    return plugin_state_root() / DEFAULT_SESSION_SUBDIR


def legacy_consumer_file() -> Path:
    return Path.home() / DEFAULT_CONSUMER_DIR / CONSUMER_FILENAME


def invocation_log_path(storage_root: Optional[Path] = None) -> Path:
    if storage_root is None:
        return plugin_state_root() / INVOCATION_LOG_FILENAME
    storage_root = storage_root.expanduser()
    if storage_root.name == DEFAULT_SESSION_SUBDIR:
        return storage_root.parent / INVOCATION_LOG_FILENAME
    return storage_root / INVOCATION_LOG_FILENAME


def consumer_dir(config_root: Optional[Path] = None) -> Path:
    if config_root is not None:
        return config_root.expanduser()
    configured = os.environ.get("CODEX_COUNCIL_HOME")
    if configured:
        return Path(configured).expanduser()
    return plugin_state_root()


def consumer_file(config_root: Optional[Path] = None) -> Path:
    return consumer_dir(config_root) / CONSUMER_FILENAME


def alter_config_file(config_root: Optional[Path] = None) -> Path:
    return consumer_dir(config_root) / ALTER_CONFIG_FILENAME


def _explicit_consumer_state(config_root: Optional[Path] = None) -> bool:
    return bool(config_root or os.environ.get("CODEX_COUNCIL_HOME") or os.environ.get("CODEX_COUNCIL_STATE_ROOT"))


def migrate_version_local_state_file(filename: str, config_root: Optional[Path] = None) -> Optional[Path]:
    if _explicit_consumer_state(config_root):
        return None
    destination = consumer_dir(config_root) / filename
    source = version_local_state_root() / filename
    if destination == source or destination.exists() or not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    return destination


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_council_invocation(text: str, explicit: bool = False) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if explicit:
        return "invoke"
    if not normalized:
        return "unclear"
    invoke_patterns = (
        r"\b(use|usa|run|avvia|attiva|launch|start|esegui)\b.*\b(codex council|council|consiglio)\b",
        r"\b(codex council|council|consiglio)\b.*\b(review|valuta|analizza|giudica|attiva|run|esegui)\b",
        r"\b(spin up|panel of advisors|council this|consiglio su)\b",
    )
    meta_patterns = (
        r"\b(what is|cos.?è|come funziona|spiegami|explain|parlami|dimmi)\b.*\b(codex council|council|consiglio)\b",
        r"\b(codex council|council|consiglio)\b.*\b(metodo|method|workflow|flow|funziona)\b",
    )
    if any(re.search(pattern, normalized) for pattern in invoke_patterns):
        return "invoke"
    if any(re.search(pattern, normalized) for pattern in meta_patterns):
        return "meta"
    if "council" in normalized or "consiglio" in normalized:
        return "unclear"
    return "meta"


def _select_panel_filenames(
    filenames: list[str],
    topic: str = "",
    session_type: str = "general",
    panel: str = "full",
) -> list[str]:
    if panel in {"full", "auto"} or len(filenames) <= 1:
        return filenames
    if panel == "solo":
        return filenames[:1]
    normalized = f"{topic} {session_type}".lower()
    preferred: list[str]
    if re.search(ROUTER_RISK_PATTERNS["frontend_evidence"], normalized):
        preferred = [
            "01-ada-principal-architect.md",
            "04-florence-product-operator.md",
            "06-seymour-performance-engineer.md",
        ]
    elif re.search(ROUTER_RISK_PATTERNS["performance"], normalized):
        preferred = [
            "01-ada-principal-architect.md",
            "02-grace-reliability-engineer.md",
            "06-seymour-performance-engineer.md",
        ]
    elif re.search(ROUTER_RISK_PATTERNS["security"], normalized):
        preferred = [
            "01-ada-principal-architect.md",
            "02-grace-reliability-engineer.md",
            "03-hypatia-security-governance.md",
        ]
    else:
        preferred = [
            "01-ada-principal-architect.md",
            "02-grace-reliability-engineer.md",
            "06-seymour-performance-engineer.md",
        ]
    cap = 3 if panel == "triad" else 4
    selected = [filename for filename in preferred if filename in filenames]
    selected.extend(filename for filename in filenames if filename not in selected)
    return selected[:cap]


def active_role_files(
    skill_review: bool = False,
    session_type: str = "general",
    panel: str = "full",
    topic: str = "",
) -> dict[str, str]:
    if skill_review:
        return SKILL_REVIEW_ROLE_FILES
    if session_type == "forge":
        return FORGE_ROLE_FILES
    selected = set(_select_panel_filenames(list(ROLE_FILES), topic, session_type, panel))
    return {filename: role for filename, role in ROLE_FILES.items() if filename in selected}


def active_member_prompt_files(
    skill_review: bool = False,
    session_type: str = "general",
    panel: str = "full",
    topic: str = "",
) -> dict[str, str]:
    if skill_review:
        return SKILL_REVIEW_PROMPT_FILES
    if session_type == "forge":
        return FORGE_PROMPT_FILES
    selected = set(_select_panel_filenames(list(MEMBER_PROMPT_FILES), topic, session_type, panel))
    return {filename: prompt for filename, prompt in MEMBER_PROMPT_FILES.items() if filename in selected}


def normalize_session_options(
    session_type: str = "general",
    frontend_review: bool = False,
    skill_review: bool = False,
) -> tuple[str, bool, bool]:
    if session_type not in SESSION_TYPES:
        raise ValueError(f"session_type must be one of: {', '.join(sorted(SESSION_TYPES))}")
    if session_type == "frontend":
        frontend_review = True
    if session_type == "skill":
        skill_review = True
    if skill_review:
        session_type = "skill"
        frontend_review = False
    return session_type, frontend_review, skill_review


def detect_risk_flags(topic: str, session_type: str = "general", frontend_review: bool = False) -> list[str]:
    text = f"{topic} {session_type}".lower()
    flags = [name for name, pattern in ROUTER_RISK_PATTERNS.items() if re.search(pattern, text)]
    if frontend_review and "frontend_evidence" not in flags:
        flags.append("frontend_evidence")
    return sorted(set(flags))


def route_council_panel(
    topic: str,
    mode: str = "standard",
    session_type: str = "general",
    frontend_review: bool = False,
    skill_review: bool = False,
    requested_panel: str = "full",
    router: str = "off",
    max_agents: Optional[int] = None,
    early_exit: bool = False,
) -> dict[str, Any]:
    if requested_panel not in PANELS:
        raise ValueError(f"panel must be one of: {', '.join(sorted(PANELS))}")
    if router not in {"off", "auto"}:
        raise ValueError("router must be off or auto")
    session_type, frontend_review, skill_review = normalize_session_options(session_type, frontend_review, skill_review)
    risk_flags = detect_risk_flags(topic, session_type, frontend_review)
    hard_full_flags = {"privacy", "security", "data_loss", "frontend_evidence"}
    forced_full = bool(hard_full_flags.intersection(risk_flags)) and not skill_review and session_type != "forge"
    reasons: list[str] = []
    if forced_full:
        reasons.append("Hard-risk flags require full council coverage.")
    if forced_full:
        selected_panel = "full"
        reasons.append("Hard-risk safety floor overrides panel reduction whether routing is on or off.")
    elif router == "off":
        selected_panel = "full" if requested_panel in {"auto", "full"} else requested_panel
        reasons.append("Router is off; selected panel follows the explicit request.")
    elif requested_panel == "auto":
        if mode == "fast":
            selected_panel = "solo"
        elif "performance" in risk_flags:
            selected_panel = "triad"
        else:
            selected_panel = "triad"
        reasons.append("Router auto selected the smallest advisory panel that preserves relevant lenses.")
    else:
        selected_panel = requested_panel
        reasons.append("Router auto accepted the requested panel because no hard-risk flag was detected.")
    if max_agents is not None and max_agents > 0 and selected_panel == "full":
        reasons.append("max_agents recorded as advisory only; hard/full coverage is not silently reduced.")
    role_count = len(active_role_files(skill_review, session_type, selected_panel, topic))
    if selected_panel == "full":
        role_count = len(active_role_files(skill_review, session_type, "full", topic))
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "router": router,
        "requested_panel": requested_panel,
        "selected_panel": selected_panel,
        "forced_full": forced_full,
        "mode": mode,
        "session_type": session_type,
        "risk_flags": risk_flags,
        "max_agents": max_agents,
        "early_exit": bool(early_exit),
        "estimated_role_count": role_count,
        "requires_acceptance": selected_panel != "full" or router == "auto",
        "reasons": reasons,
        "policy": "Advisory routing only; never reduce coverage silently.",
    }


def _compact_lines(values: list[str]) -> tuple[list[str], int]:
    seen: set[str] = set()
    compacted: list[str] = []
    duplicates = 0
    for value in values:
        line = re.sub(r"\s+", " ", str(value).strip())
        if not line:
            continue
        key = line.lower().rstrip(".")
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        compacted.append(line)
    return compacted, duplicates


def compile_context_capsule(
    topic: str,
    constraints: Optional[list[str]] = None,
    context: str = "",
) -> dict[str, Any]:
    raw_parts = [topic]
    if constraints:
        raw_parts.extend(constraints)
    if context:
        raw_parts.append(context)
    raw_text = "\n".join(raw_parts)
    context_lines = context.splitlines() if context else []
    compact_constraints, duplicate_constraints = _compact_lines(constraints or [])
    compact_context, duplicate_context = _compact_lines(context_lines)
    compact_topic = re.sub(r"\s+", " ", topic).strip()
    compiled_sections = [f"Topic: {compact_topic}"]
    if compact_constraints:
        compiled_sections.append("Constraints: " + "; ".join(compact_constraints))
    if compact_context:
        compiled_sections.append("Context: " + " / ".join(compact_context))
    compiled_text = "\n".join(compiled_sections)
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "raw_tokens": estimate_tokens(len(raw_text)),
        "compiled_tokens": estimate_tokens(len(compiled_text)),
        "duplicates_removed": duplicate_constraints + duplicate_context,
        "compiled_text": compiled_text,
    }


def _normalize_finding_claim(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def deduplicate_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, dict[str, Any]] = {}
    for finding in findings:
        claim = re.sub(r"\s+", " ", str(finding.get("claim", "")).strip()).rstrip(".")
        if not claim:
            continue
        key = _normalize_finding_claim(claim)
        source = str(finding.get("source", "")).strip()
        if key not in merged:
            merged[key] = {
                "claim": claim,
                "sources": [],
                "count": 0,
            }
        merged[key]["count"] += 1
        if source and source not in merged[key]["sources"]:
            merged[key]["sources"].append(source)
    results = list(merged.values())
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "input_count": len(findings),
        "unique_count": len(results),
        "duplicates_removed": max(len(findings) - len(results), 0),
        "findings": results,
    }


def default_alter_config() -> dict[str, Any]:
    return {
        "version": ALTER_CONFIG_VERSION,
        "updated_at": utc_now(),
        "alters": {},
    }


def role_id_for_label(label: str) -> Optional[str]:
    for role_id, spec in ALTER_ROLE_CATALOG.items():
        if label in spec["applies_to"]:
            return role_id
    return None


def normalize_alter_role(role_id: str) -> str:
    normalized = role_id.strip().lower().replace("_", "-")
    aliases = {
        "alan": "turing",
        "alan-turing": "turing",
        "ada-lovelace": "ada",
        "grace-hopper": "grace",
        "florence-nightingale": "florence",
        "seymour-cray": "seymour",
        "leonardo-da-vinci": "leonardo",
        "bob": "bob",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized == "bob":
        raise ValueError("Bob is an evidence runner and cannot be customized as an alter")
    if normalized not in ALTER_ROLE_CATALOG:
        raise ValueError(f"Unknown alter role: {role_id}")
    return normalized


def _compact_text(value: Optional[str], field_name: str, char_cap: int = ALTER_FIELD_CHAR_CAP) -> str:
    if value is None:
        return ""
    compact = re.sub(r"\s+", " ", value.strip())
    if len(compact) > char_cap:
        raise ValueError(f"{field_name} exceeds {char_cap} characters")
    if has_forbidden_alter_instruction(compact):
        raise ValueError(f"{field_name} attempts to override council non-negotiables")
    return compact


def has_forbidden_alter_instruction(text: str) -> bool:
    normalized = text.lower()
    return any(re.search(pattern, normalized) for pattern in FORBIDDEN_ALTER_PATTERNS)


def default_alter_entry(role_id: str) -> dict[str, Any]:
    return {
        "role_id": role_id,
        "display_name": ALTER_ROLE_CATALOG[role_id]["display_name"],
        "enabled": True,
        "updated_at": utc_now(),
        "summary": "",
        "compiled_instruction": "",
        "dimensions": {
            "domain_focus": "",
            "strictness": "",
            "tone": "",
            "risk_posture": "",
            "evidence_preference": "",
            "extra_checks": [],
        },
        "estimated_added_tokens": 0,
    }


def compile_alter_instruction(
    role_id: str,
    domain_focus: Optional[str] = None,
    strictness: Optional[str] = None,
    tone: Optional[str] = None,
    risk_posture: Optional[str] = None,
    evidence_preference: Optional[str] = None,
    extra_checks: Optional[list[str]] = None,
    instruction: Optional[str] = None,
) -> tuple[str, dict[str, Any]]:
    role_id = normalize_alter_role(role_id)
    dimensions = {
        "domain_focus": _compact_text(domain_focus, "domain_focus"),
        "strictness": _compact_text(strictness, "strictness"),
        "tone": _compact_text(tone, "tone"),
        "risk_posture": _compact_text(risk_posture, "risk_posture"),
        "evidence_preference": _compact_text(evidence_preference, "evidence_preference"),
        "extra_checks": [_compact_text(item, "extra_check", 120) for item in (extra_checks or []) if _compact_text(item, "extra_check", 120)],
    }
    bounded_instruction = _compact_text(instruction, "instruction", 280)
    clauses: list[str] = []
    if dimensions["tone"]:
        clauses.append(f"Tone: {dimensions['tone']}.")
    if dimensions["strictness"]:
        clauses.append(f"Rigor: {dimensions['strictness']}.")
    if dimensions["domain_focus"]:
        clauses.append(f"Domain focus: {dimensions['domain_focus']}.")
    if dimensions["risk_posture"]:
        clauses.append(f"Risk posture: {dimensions['risk_posture']}.")
    if dimensions["evidence_preference"]:
        clauses.append(f"Evidence preference: {dimensions['evidence_preference']}.")
    if dimensions["extra_checks"]:
        clauses.append("Extra checks: " + "; ".join(dimensions["extra_checks"]) + ".")
    if bounded_instruction:
        clauses.append(f"Additional bounded instruction: {bounded_instruction}")
    if not clauses:
        raise ValueError("At least one alter tuning field is required")
    compiled = " ".join(clauses)
    word_count = len(re.findall(r"\S+", compiled))
    if word_count > ALTER_COMPILED_WORD_CAP:
        raise ValueError(f"compiled_instruction exceeds {ALTER_COMPILED_WORD_CAP} words")
    if has_forbidden_alter_instruction(compiled):
        raise ValueError("compiled_instruction attempts to override council non-negotiables")
    return compiled, dimensions


def build_alter_entry(
    role_id: str,
    domain_focus: Optional[str] = None,
    strictness: Optional[str] = None,
    tone: Optional[str] = None,
    risk_posture: Optional[str] = None,
    evidence_preference: Optional[str] = None,
    extra_checks: Optional[list[str]] = None,
    instruction: Optional[str] = None,
    enabled: bool = True,
) -> dict[str, Any]:
    role_id = normalize_alter_role(role_id)
    compiled, dimensions = compile_alter_instruction(
        role_id,
        domain_focus=domain_focus,
        strictness=strictness,
        tone=tone,
        risk_posture=risk_posture,
        evidence_preference=evidence_preference,
        extra_checks=extra_checks,
        instruction=instruction,
    )
    entry = default_alter_entry(role_id)
    entry.update(
        {
            "enabled": enabled,
            "updated_at": utc_now(),
            "summary": render_alter_summary(role_id, compiled, dimensions),
            "compiled_instruction": compiled,
            "dimensions": dimensions,
            "estimated_added_tokens": estimate_tokens(len(render_alter_prompt_block(entry | {"compiled_instruction": compiled}))),
        }
    )
    return entry


def validate_alter_entry(role_id: str, entry: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    try:
        normalized_role_id = normalize_alter_role(role_id)
    except ValueError as exc:
        return [str(exc)]
    if entry.get("role_id", normalized_role_id) != normalized_role_id:
        problems.append("role_id mismatch")
    compiled = str(entry.get("compiled_instruction", ""))
    if entry.get("enabled", True) and not compiled.strip():
        problems.append("enabled alter has empty compiled_instruction")
    if len(re.findall(r"\S+", compiled)) > ALTER_COMPILED_WORD_CAP:
        problems.append(f"compiled_instruction exceeds {ALTER_COMPILED_WORD_CAP} words")
    if has_forbidden_alter_instruction(compiled):
        problems.append("compiled_instruction attempts to override council non-negotiables")
    return problems


def validate_alter_config(data: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if data.get("version") != ALTER_CONFIG_VERSION:
        problems.append("unsupported alter config version")
    alters = data.get("alters")
    if not isinstance(alters, dict):
        return problems + ["alters must be an object"]
    for role_id, entry in alters.items():
        if not isinstance(entry, dict):
            problems.append(f"{role_id} alter entry must be an object")
            continue
        problems.extend(f"{role_id}: {problem}" for problem in validate_alter_entry(role_id, entry))
    return problems


def load_alter_config(config_root: Optional[Path] = None) -> dict[str, Any]:
    migrate_version_local_state_file(ALTER_CONFIG_FILENAME, config_root)
    path = alter_config_file(config_root)
    if not path.exists():
        return default_alter_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid alter config JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid alter config at {path}: root must be an object")
    problems = validate_alter_config(data)
    if problems:
        raise ValueError(f"Invalid alter config at {path}: {'; '.join(problems)}")
    baseline = default_alter_config()
    baseline.update({key: data[key] for key in data if key != "alters"})
    baseline["alters"] = data.get("alters", {})
    return baseline


def save_alter_config(data: dict[str, Any], config_root: Optional[Path] = None) -> Path:
    problems = validate_alter_config(data)
    if problems:
        raise ValueError(f"Cannot save invalid alter config: {'; '.join(problems)}")
    path = alter_config_file(config_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = utc_now()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        tmp_path.chmod(0o600)
    except OSError:
        pass
    tmp_path.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def configure_alter(
    role_id: str,
    config_root: Optional[Path] = None,
    domain_focus: Optional[str] = None,
    strictness: Optional[str] = None,
    tone: Optional[str] = None,
    risk_posture: Optional[str] = None,
    evidence_preference: Optional[str] = None,
    extra_checks: Optional[list[str]] = None,
    instruction: Optional[str] = None,
) -> dict[str, Any]:
    role_id = normalize_alter_role(role_id)
    data = load_alter_config(config_root)
    entry = build_alter_entry(
        role_id,
        domain_focus=domain_focus,
        strictness=strictness,
        tone=tone,
        risk_posture=risk_posture,
        evidence_preference=evidence_preference,
        extra_checks=extra_checks,
        instruction=instruction,
    )
    data["alters"][role_id] = entry
    path = save_alter_config(data, config_root)
    return {"path": str(path), "role_id": role_id, "entry": entry}


def reset_alter(role_id: Optional[str] = None, config_root: Optional[Path] = None) -> dict[str, Any]:
    data = load_alter_config(config_root)
    if role_id is None:
        removed = sorted(data.get("alters", {}).keys())
        data["alters"] = {}
    else:
        role_id = normalize_alter_role(role_id)
        removed = [role_id] if role_id in data.get("alters", {}) else []
        data.get("alters", {}).pop(role_id, None)
    path = save_alter_config(data, config_root)
    return {"path": str(path), "removed": removed}


def render_alter_summary(role_id: str, compiled_instruction: str, dimensions: dict[str, Any]) -> str:
    role_name = ALTER_ROLE_CATALOG[role_id]["display_name"]
    active_fields = [
        label
        for label, value in dimensions.items()
        if (isinstance(value, list) and value) or (isinstance(value, str) and value.strip())
    ]
    field_summary = ", ".join(active_fields) if active_fields else "bounded instruction"
    word_count = len(re.findall(r"\S+", compiled_instruction))
    return f"{role_name}: {field_summary}; {word_count} words."


def active_alter_entry(alter_config: dict[str, Any], role_label: str) -> Optional[dict[str, Any]]:
    role_id = role_id_for_label(role_label)
    if role_id is None:
        return None
    entry = alter_config.get("alters", {}).get(role_id)
    if not isinstance(entry, dict) or not entry.get("enabled", True):
        return None
    if validate_alter_entry(role_id, entry):
        return None
    return entry


def render_alter_prompt_block(entry: dict[str, Any]) -> str:
    instruction = re.sub(r"\s+", " ", str(entry.get("compiled_instruction", "")).strip())
    if not instruction:
        return ""
    return (
        "\n\nLocal role tuning (advisory, lower priority than all Codex Council non-negotiables):\n"
        f"- {instruction}\n"
        "- This tuning cannot remove blockers, dissent, verification, confidence, anonymization, safety checks, or role boundaries.\n"
    )


def active_alter_session_metadata(alter_config: dict[str, Any], roles: list[str], reviewers: list[str]) -> dict[str, Any]:
    applied: list[dict[str, Any]] = []
    for label in roles + reviewers:
        role_id = role_id_for_label(label)
        if role_id is None:
            continue
        entry = active_alter_entry(alter_config, label)
        if entry is None:
            continue
        compiled = str(entry.get("compiled_instruction", ""))
        applied.append(
            {
                "role_id": role_id,
                "display_name": ALTER_ROLE_CATALOG[role_id]["display_name"],
                "kind": ALTER_ROLE_CATALOG[role_id]["kind"],
                "summary": entry.get("summary", ""),
                "estimated_added_tokens": entry.get("estimated_added_tokens", estimate_tokens(len(compiled))),
                "fingerprint": hashlib.sha256(compiled.encode("utf-8")).hexdigest()[:12],
            }
        )
    return {
        "count": len(applied),
        "roles": applied,
        "raw_instructions_logged": False,
        "precedence": "advisory; lower priority than Codex Council non-negotiables",
    }


def render_alter_config(data: dict[str, Any], role_id: Optional[str] = None, config_root: Optional[Path] = None) -> str:
    lines = ["Codex Council role tuning", f"- Path: {alter_config_file(config_root)}", f"- Version: {data.get('version')}"]
    role_ids = [normalize_alter_role(role_id)] if role_id else sorted(ALTER_ROLE_CATALOG)
    for current_role_id in role_ids:
        spec = ALTER_ROLE_CATALOG[current_role_id]
        entry = data.get("alters", {}).get(current_role_id)
        lines.append("")
        lines.append(f"## {spec['display_name']} ({current_role_id})")
        if not entry:
            lines.append("- Status: default")
            lines.append("- Summary: no local tuning")
            continue
        lines.append(f"- Status: {'enabled' if entry.get('enabled', True) else 'disabled'}")
        lines.append(f"- Updated: {entry.get('updated_at', 'unknown')}")
        lines.append(f"- Summary: {entry.get('summary', '')}")
        lines.append(f"- Estimated added tokens: {entry.get('estimated_added_tokens', 0)}")
    lines.append("")
    lines.append("Bob is intentionally absent: he is an evidence runner, not a council alter.")
    return "\n".join(lines)


def render_alter_preview(entry: dict[str, Any]) -> str:
    role_id = str(entry["role_id"])
    return "\n".join(
        [
            f"# {ALTER_ROLE_CATALOG[role_id]['display_name']} Role Tuning Preview",
            "",
            entry.get("summary", ""),
            "",
            "## Effective Prompt Delta",
            render_alter_prompt_block(entry).strip(),
            "",
            f"Estimated added tokens per affected prompt: {entry.get('estimated_added_tokens', 0)}",
        ]
    )


def default_consumer_data() -> dict[str, Any]:
    return {
        "version": CONSUMER_FILE_VERSION,
        "profile": {
            "plan": "unknown",
            "typical_model": "unknown",
            "reasoning": "unknown",
            "five_hour_limit_tokens": None,
            "weekly_limit_tokens": None,
            "credit_budget": None,
            "storage_consent": False,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
        "history": {
            "summary": {
                "sessions": 0,
                "avg_post_to_pre_ratio": 1.0,
                "ratio_samples": [],
            },
            "recent": [],
        },
    }


def load_consumer_data(config_root: Optional[Path] = None) -> dict[str, Any]:
    migrate_version_local_state_file(CONSUMER_FILENAME, config_root)
    path = consumer_file(config_root)
    if (
        config_root is None
        and not path.exists()
        and not os.environ.get("CODEX_COUNCIL_HOME")
        and not os.environ.get("CODEX_COUNCIL_STATE_ROOT")
        and legacy_consumer_file() != path
        and legacy_consumer_file().exists()
    ):
        path = legacy_consumer_file()
    if not path.exists():
        return default_consumer_data()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_consumer_data()
    if not isinstance(data, dict) or data.get("version") != CONSUMER_FILE_VERSION:
        return default_consumer_data()
    baseline = default_consumer_data()
    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    history = data.get("history") if isinstance(data.get("history"), dict) else {}
    baseline["profile"].update(profile)
    if isinstance(history.get("summary"), dict):
        baseline["history"]["summary"].update(history["summary"])
    if isinstance(history.get("recent"), list):
        baseline["history"]["recent"] = history["recent"][-MAX_RECENT_HISTORY:]
    return baseline


def save_consumer_data(data: dict[str, Any], config_root: Optional[Path] = None) -> Path:
    path = consumer_file(config_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = compact_consumer_history(data)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def update_consumer_profile(
    config_root: Optional[Path],
    plan: Optional[str] = None,
    model: Optional[str] = None,
    reasoning: Optional[str] = None,
    five_hour_limit_tokens: Optional[int] = None,
    weekly_limit_tokens: Optional[int] = None,
    credit_budget: Optional[float] = None,
    storage_consent: bool = True,
) -> dict[str, Any]:
    data = load_consumer_data(config_root)
    profile = data["profile"]
    if plan:
        profile["plan"] = plan
    if model:
        profile["typical_model"] = model
    if reasoning:
        profile["reasoning"] = reasoning
    if five_hour_limit_tokens is not None:
        profile["five_hour_limit_tokens"] = five_hour_limit_tokens
    if weekly_limit_tokens is not None:
        profile["weekly_limit_tokens"] = weekly_limit_tokens
    if credit_budget is not None:
        profile["credit_budget"] = credit_budget
    profile["storage_consent"] = storage_consent
    profile["updated_at"] = utc_now()
    save_consumer_data(data, config_root)
    return data


def compact_consumer_history(data: dict[str, Any]) -> dict[str, Any]:
    history = data.setdefault("history", {})
    summary = history.setdefault("summary", {})
    recent = history.get("recent", [])
    if not isinstance(recent, list):
        recent = []
    history["recent"] = recent[-MAX_RECENT_HISTORY:]
    ratios = summary.get("ratio_samples", [])
    if not isinstance(ratios, list):
        ratios = []
    ratios = [float(value) for value in ratios if isinstance(value, (int, float)) and value > 0]
    summary["ratio_samples"] = ratios[-MAX_HISTORY_SUMMARY_RATIOS:]
    summary["sessions"] = int(summary.get("sessions", 0) or 0)
    summary["avg_post_to_pre_ratio"] = round(statistics.fmean(summary["ratio_samples"]), 4) if summary["ratio_samples"] else 1.0
    return data


def history_multiplier(consumer_data: dict[str, Any]) -> float:
    ratio = consumer_data.get("history", {}).get("summary", {}).get("avg_post_to_pre_ratio", 1.0)
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        value = 1.0
    return min(max(value, 0.75), 2.5)


def normalize_model_name(model: str) -> str:
    return re.sub(r"\s+", "-", model.strip().lower())


def estimate_credits(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    rates = CODEX_CREDIT_RATES_PER_MILLION.get(normalize_model_name(model))
    if rates is None:
        return None
    credits = (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])
    return round(credits, 4)


def estimate_pre_session(
    topic: str,
    mode: str = "standard",
    token_budget: str = "compact",
    frontend_review: bool = False,
    session_type: str = "general",
    skill_review: bool = False,
    context_tokens: int = 0,
    consumer_data: Optional[dict[str, Any]] = None,
    alter_config: Optional[dict[str, Any]] = None,
    panel: str = "full",
    router: str = "off",
    max_agents: Optional[int] = None,
    early_exit: bool = False,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(MODES))}")
    if token_budget not in TOKEN_BUDGETS:
        raise ValueError(f"token_budget must be one of: {', '.join(sorted(TOKEN_BUDGETS))}")
    session_type, frontend_review, skill_review = normalize_session_options(session_type, frontend_review, skill_review)
    route_decision = route_council_panel(
        topic,
        mode=mode,
        session_type=session_type,
        frontend_review=frontend_review,
        skill_review=skill_review,
        requested_panel=panel,
        router=router,
        max_agents=max_agents,
        early_exit=early_exit,
    )
    active_panel = route_decision["selected_panel"]
    consumer_data = consumer_data or default_consumer_data()
    alter_config = alter_config or default_alter_config()
    profile = consumer_data["profile"]
    if skill_review:
        member_count = len(SKILL_REVIEW_ROLE_FILES)
        reviewer_count = 0
    elif session_type == "forge":
        member_count = len(FORGE_ROLE_FILES)
        reviewer_count = 0
    else:
        member_count = 1 if mode == "fast" else len(active_role_files(False, session_type, active_panel, topic))
        reviewer_count = 0 if mode == "fast" else len(session_reviewers(mode, frontend_review, session_type=session_type, panel=active_panel))
    evidence_count = len(session_evidence_runners(frontend_review))
    topic_tokens = estimate_tokens(len(topic))
    budget_factor = {"compact": 1.0, "balanced": 1.55, "expanded": 3.2}[token_budget]
    mode_factor = {"fast": 0.35, "standard": 1.0, "deep": 1.75}[mode]
    reasoning_factor = {
        "none": 0.75,
        "minimal": 0.85,
        "low": 0.95,
        "medium": 1.0,
        "high": 1.25,
        "xhigh": 1.55,
    }.get(str(profile.get("reasoning", "unknown")).lower(), 1.1)
    static_overhead = 950
    per_member_input = 420 + topic_tokens
    per_member_output = {"compact": 120, "balanced": 220, "expanded": 650}[token_budget]
    per_reviewer_input = 320 + (member_count * per_member_output)
    per_reviewer_output = {"compact": 100, "balanced": 180, "expanded": 400}[token_budget]
    chairman_input = 350 + (member_count * per_member_output) + (reviewer_count * per_reviewer_output)
    chairman_output = {"compact": 250, "balanced": 420, "expanded": 900}[token_budget]
    factor_in = mode_factor * reasoning_factor
    factor_out = mode_factor * budget_factor
    forge_rebrief_overhead = 0
    if session_type == "forge":
        forge_rebrief_overhead = int((180 + (member_count * 40)) * factor_out)
        chairman_input += 160
    active_labels = list(active_role_files(skill_review, session_type, active_panel, topic).values()) + session_reviewers(
        mode,
        frontend_review,
        skill_review,
        session_type,
        active_panel,
    )
    alter_tuning_prompt_tokens = sum(
        int(entry.get("estimated_added_tokens", estimate_tokens(len(str(entry.get("compiled_instruction", ""))))))
        for label in active_labels
        for entry in [active_alter_entry(alter_config, label)]
        if entry is not None
    )
    components = {
        "static_protocol_input_tokens": int(static_overhead * factor_in),
        "member_input_tokens": int(member_count * per_member_input * factor_in),
        "member_output_tokens": int(member_count * per_member_output * factor_out),
        "reviewer_input_tokens": int(reviewer_count * per_reviewer_input * factor_in),
        "reviewer_output_tokens": int(reviewer_count * per_reviewer_output * factor_out),
        "synthesis_input_tokens": int(chairman_input * factor_in),
        "synthesis_output_tokens": int(chairman_output * factor_out),
        "scoring_stats_overhead_tokens": int(SCORING_STATS_OVERHEAD_TOKENS * mode_factor),
        "context_duplication_tokens": int(context_tokens * max(member_count + reviewer_count + 1, 1) * factor_in),
        "frontend_browser_evidence_tokens": int(evidence_count * 180 * factor_out),
        "alter_tuning_prompt_tokens": int(alter_tuning_prompt_tokens * factor_in),
        "forge_rebrief_overhead_tokens": forge_rebrief_overhead,
    }
    input_tokens = (
        components["static_protocol_input_tokens"]
        + components["member_input_tokens"]
        + components["reviewer_input_tokens"]
        + components["synthesis_input_tokens"]
        + components["context_duplication_tokens"]
        + components["alter_tuning_prompt_tokens"]
    )
    output_tokens = (
        components["member_output_tokens"]
        + components["reviewer_output_tokens"]
        + components["synthesis_output_tokens"]
        + components["frontend_browser_evidence_tokens"]
        + components["scoring_stats_overhead_tokens"]
        + components["forge_rebrief_overhead_tokens"]
    )
    calibrated_total = int((input_tokens + output_tokens) * history_multiplier(consumer_data))
    input_share = input_tokens / max(input_tokens + output_tokens, 1)
    calibrated_input = int(calibrated_total * input_share)
    calibrated_output = max(calibrated_total - calibrated_input, 0)
    high_factor = 1.35 if token_budget != "expanded" else 1.75
    pre_execution_estimate = {
        "label": "pre_execution_estimate",
        "total_tokens": calibrated_total,
        "input_tokens": calibrated_input,
        "output_tokens": calibrated_output,
        "range": {
            "low": int(calibrated_total * 0.75),
            "high": int(calibrated_total * high_factor),
        },
        "components": components,
        "assumptions": {
            "chars_per_token": TOKEN_ESTIMATE_CHARS_PER_TOKEN,
            "mode_factor": mode_factor,
            "budget_factor": budget_factor,
            "reasoning_factor": reasoning_factor,
            "history_multiplier": history_multiplier(consumer_data),
            "context_tokens_hint": context_tokens,
            "counts": {
                "members": member_count,
                "reviewers": reviewer_count,
                "evidence_runners": evidence_count,
                "active_alters": active_alter_session_metadata(alter_config, active_labels, [])["count"],
            },
            "note": "Forecast includes duplicated context across agents, expected prompts/outputs, synthesis, scoring/stats overhead, and optional browser evidence. It is not real Codex billing usage.",
        },
    }
    estimate = {
        "label": "estimated pre-session tokens",
        "source": "local heuristic from mode, token profile, role counts, optional context token hint, and compact local history",
        "is_actual_codex_usage": False,
        "limitation": "Not actual Codex token usage, remaining quota, billing telemetry, hidden prompt overhead, cached input, or tool-call accounting.",
        "mode": mode,
        "session_type": session_type,
        "skill_review": skill_review,
        "token_budget": token_budget,
        "frontend_review": frontend_review,
        "panel": active_panel,
        "requested_panel": panel,
        "router_decision": route_decision,
        "role_count": member_count,
        "reviewer_count": reviewer_count,
        "evidence_runner_count": evidence_count,
        "context_tokens_hint": context_tokens,
        "history_multiplier": history_multiplier(consumer_data),
        "confidence": "medium" if consumer_data["history"]["summary"].get("sessions", 0) >= 3 else "low",
        "estimated_input_tokens": calibrated_input,
        "estimated_output_tokens": calibrated_output,
        "estimated_total_tokens": calibrated_total,
        "estimated_total_tokens_range": {
            "low": pre_execution_estimate["range"]["low"],
            "high": pre_execution_estimate["range"]["high"],
        },
        "pre_execution_estimate": pre_execution_estimate,
        "estimated_credits": estimate_credits(str(profile.get("typical_model", "")), calibrated_input, calibrated_output),
        "profile_snapshot": {
            "plan": profile.get("plan", "unknown"),
            "typical_model": profile.get("typical_model", "unknown"),
            "reasoning": profile.get("reasoning", "unknown"),
            "five_hour_limit_tokens": profile.get("five_hour_limit_tokens"),
            "weekly_limit_tokens": profile.get("weekly_limit_tokens"),
            "credit_budget": profile.get("credit_budget"),
        },
        "confirmation_required": token_budget == "expanded",
        "expanded_confirmation_phrase": EXPANDED_CONFIRMATION if token_budget == "expanded" else None,
    }
    return estimate


def render_pre_session_estimate(estimate: dict[str, Any]) -> str:
    pre = estimate.get("pre_execution_estimate", {})
    components = pre.get("components", {})
    lines = [
        "# Codex Council Preflight Estimate",
        "",
        "These numbers are local estimates, not actual Codex usage, remaining quota, or billing telemetry.",
        "",
        f"- Mode: {estimate['mode']}",
        f"- Type: {estimate.get('session_type', 'general')}",
        f"- Token profile: {estimate['token_budget']}",
        f"- Roles/reviewers/evidence runners: {estimate['role_count']}/{estimate['reviewer_count']}/{estimate['evidence_runner_count']}",
        f"- Estimated total tokens: {estimate['estimated_total_tokens']} "
        f"(range {estimate['estimated_total_tokens_range']['low']}..{estimate['estimated_total_tokens_range']['high']})",
        f"- Estimated input/output tokens: {estimate['estimated_input_tokens']}/{estimate['estimated_output_tokens']}",
        f"- Confidence: {estimate['confidence']}",
        f"- Local history multiplier: {estimate['history_multiplier']}",
    ]
    if components:
        lines.extend(
            [
                "",
                "## Pre-execution components",
                f"- Member input/output: {components['member_input_tokens']}/{components['member_output_tokens']}",
                f"- Reviewer input/output: {components['reviewer_input_tokens']}/{components['reviewer_output_tokens']}",
                f"- Synthesis input/output: {components['synthesis_input_tokens']}/{components['synthesis_output_tokens']}",
                f"- Context duplication: {components['context_duplication_tokens']}",
                f"- Local role tuning: {components.get('alter_tuning_prompt_tokens', 0)}",
                f"- Forge re-brief overhead: {components.get('forge_rebrief_overhead_tokens', 0)}",
                f"- Scoring/stats overhead: {components['scoring_stats_overhead_tokens']}",
                f"- Browser evidence: {components['frontend_browser_evidence_tokens']}",
            ]
        )
    if estimate.get("estimated_credits") is not None:
        lines.append(f"- Estimated credits from configured model rate: {estimate['estimated_credits']}")
    if estimate["confirmation_required"]:
        lines.extend(
            [
                "",
                "WARNING: expanded mode can consume significantly more Codex usage.",
                f"To continue, confirm with: {EXPANDED_CONFIRMATION}",
            ]
        )
    return "\n".join(lines)


def write_preflight_estimate(session_dir: Path, estimate: dict[str, Any]) -> None:
    (session_dir / "preflight-estimate.json").write_text(
        json.dumps(estimate, indent=2) + "\n",
        encoding="utf-8",
    )
    (session_dir / "preflight-estimate.md").write_text(
        render_pre_session_estimate(estimate) + "\n",
        encoding="utf-8",
    )


def render_member_prompt(
    role: str,
    topic: str,
    mode: str,
    token_budget: str,
    session_type: str = "general",
    skill_review: bool = False,
    alter_config: Optional[dict[str, Any]] = None,
) -> str:
    if session_type == "forge":
        lens = f"\nLens: {FORGE_LENSES.get(role, 'Create a useful proposal while preserving constraints.')}\n"
        return (
            f"You are {role} for Codex Forge.\n\n"
            f"Topic: {topic}\nMode: {mode}\nType: {session_type}\nToken profile: {token_budget}\n"
            f"{lens}\n"
            "Generate one creative but implementable proposal. Respect immutable user/project constraints, privacy, "
            "token budget, and verification needs. Preserve useful dissent; do not claim validation or truth.\n\n"
            "Required sections:\n"
            "## Creative Proposal\n## Rationale\n## Constraints\n## Risks\n"
            "## Convergence Notes\n## Verification Needed\n"
        )
    lens = f"\nLens: {SKILL_REVIEW_LENSES[role]}\n" if skill_review and role in SKILL_REVIEW_LENSES else ""
    alter_block = render_alter_prompt_block(active_alter_entry(alter_config or default_alter_config(), role) or {})
    return (
        f"You are {role} for Codex Council.\n\n"
        f"Topic: {topic}\nMode: {mode}\nType: {session_type}\nToken profile: {token_budget}\n"
        f"{lens}\n"
        "Give an independent first opinion. Preserve blockers, dissent, verification, and confidence. "
        "Use compact output unless a blocker requires detail.\n\n"
        "Required sections:\n"
        "## Recommendation\n## Rationale\n## Blocking Issues\n"
        "## Non-Blocking Improvements\n## Verification Required\n## Confidence\n"
        f"{alter_block}"
    )


def render_reviewer_prompt(
    reviewer: str,
    topic: str,
    mode: str,
    token_budget: str,
    session_type: str = "general",
    alter_config: Optional[dict[str, Any]] = None,
) -> str:
    alter_block = render_alter_prompt_block(active_alter_entry(alter_config or default_alter_config(), reviewer) or {})
    return (
        f"You are {reviewer} for Codex Council.\n\n"
        f"Topic: {topic}\nMode: {mode}\nType: {session_type}\nToken profile: {token_budget}\n\n"
        "Review anonymized candidates A-F when available. Rank candidates, preserve blockers, "
        "surface missing measurements, and keep the review compact.\n"
        f"{alter_block}"
    )


def render_chairman_prompt(topic: str, mode: str, token_budget: str, session_type: str = "general") -> str:
    template = SYNTHESIS_TEMPLATES.get(session_type, SYNTHESIS_TEMPLATES["general"])
    if session_type == "forge":
        return (
            "You are the Forge synthesizer for Codex Forge.\n\n"
            f"Topic: {topic}\nMode: {mode}\nType: {session_type}\nToken profile: {token_budget}\n\n"
            f"Synthesis template: {template}\n\n"
            "Run a separate creative synthesis using saved Forge outputs and the synthesis input manifest. "
            "Summarize divided opinions, re-brief only if the user approved another round, and return either "
            "a unified proposal or an explicit nonconverged result with persistent dissent. "
            "Do not claim the proposal is validated truth.\n"
        )
    return (
        "You are the Chairman synthesizer for Codex Council.\n\n"
        f"Topic: {topic}\nMode: {mode}\nType: {session_type}\nToken profile: {token_budget}\n\n"
        f"Synthesis template: {template}\n\n"
        "Run a separate synthesis pass using only saved member/reviewer outputs and the synthesis input manifest. "
        "Do not inline-synthesize during collection. Preserve dissent, blockers, performance impact, and verification. "
        "Do not invent browser evidence or billing-token telemetry.\n"
    )


def write_prompt_scaffold(
    session_dir: Path,
    topic: str,
    mode: str,
    token_budget: str,
    frontend_review: bool = False,
    session_type: str = "general",
    skill_review: bool = False,
    alter_config: Optional[dict[str, Any]] = None,
    panel: str = "full",
) -> None:
    member_prompts_dir = session_dir / "prompts" / "members"
    reviewer_prompts_dir = session_dir / "prompts" / "reviewers"
    member_prompts_dir.mkdir(parents=True, exist_ok=True)
    reviewer_prompts_dir.mkdir(parents=True, exist_ok=True)
    role_files = active_role_files(skill_review, session_type, panel, topic)
    prompt_files = active_member_prompt_files(skill_review, session_type, panel, topic)
    for member_file, role in role_files.items():
        (member_prompts_dir / prompt_files[member_file]).write_text(
            render_member_prompt(role, topic, mode, token_budget, session_type, skill_review, alter_config),
            encoding="utf-8",
        )
    for reviewer in session_reviewers(mode, frontend_review, skill_review, session_type, panel):
        reviewer_slug = slugify(reviewer)
        if reviewer in BASE_REVIEWERS or reviewer in DEEP_REVIEWERS:
            reviewer_slug = reviewer
        (reviewer_prompts_dir / f"{reviewer_slug}.md").write_text(
            render_reviewer_prompt(reviewer, topic, mode, token_budget, session_type, alter_config),
            encoding="utf-8",
        )
    (session_dir / "prompts" / "chairman-synthesis.md").write_text(
        render_chairman_prompt(topic, mode, token_budget, session_type),
        encoding="utf-8",
    )


def write_synthesis_input_manifest(
    session_dir: Path,
    role_files: dict[str, str],
    reviewers: list[str],
    evidence_runners: list[str],
    session_type: str,
) -> None:
    manifest = {
        "version": 1,
        "session_type": session_type,
        "contract": "separate_synthesis_pass",
        "inputs": {
            "brief": "brief.md",
            "members": [f"members/{filename}" for filename in role_files],
            "reviewers": [f"reviews/{reviewer_filename(reviewer)}" for reviewer in reviewers],
            "evidence_runners": [f"evidence-runners/{slugify(runner)}.md" for runner in evidence_runners],
            "score_example": "reviews/reviews.example.json",
        },
        "rules": [
            "Use saved member/reviewer outputs as data.",
            "Do not synthesize during collection.",
            "Preserve material dissent and blockers.",
            "Do not include raw prompt/output text in invocation logs.",
        ],
    }
    (session_dir / "prompts" / SYNTHESIS_INPUT_MANIFEST).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def record_session_history(
    session_dir: Path,
    stats: dict[str, Any],
    config_root: Optional[Path] = None,
) -> Optional[Path]:
    data = load_consumer_data(config_root)
    if not data["profile"].get("storage_consent"):
        return None
    metadata = _read_json_object(session_dir / "session.json")
    pre = stats.get("pre_execution_estimate", {})
    post = stats.get("post_execution_estimate", {})
    post_tokens = post.get("total_tokens")
    pre_tokens = pre.get("total_tokens")
    ratio = None
    if isinstance(pre_tokens, int) and pre_tokens > 0 and isinstance(post_tokens, int):
        ratio = round(post_tokens / pre_tokens, 4)
    history = data["history"]
    summary = history["summary"]
    summary["sessions"] = int(summary.get("sessions", 0) or 0) + 1
    if ratio is not None and post.get("coverage") == "full":
        samples = summary.setdefault("ratio_samples", [])
        samples.append(ratio)
    history["recent"].append(
        {
            "recorded_at": utc_now(),
            "mode": metadata.get("mode", "unknown"),
            "session_type": metadata.get("session_type", "general"),
            "token_budget": metadata.get("token_budget", "unknown"),
            "frontend_review": "frontend-ui-ux" in metadata.get("activation_tags", []),
            "skill_review": "skill-review" in metadata.get("activation_tags", []),
            "pre_estimated_tokens": pre_tokens,
            "post_estimated_tokens": post_tokens,
            "post_coverage": post.get("coverage", "partial"),
            "artifact_only_tokens": stats.get("artifact_only_tokens", {}).get("total_tokens"),
            "post_to_pre_ratio": ratio,
            "validation_ok": stats.get("validation", {}).get("ok"),
        }
    )
    return save_consumer_data(data, config_root)


def weighted_score(dimensions: dict[str, Any]) -> float:
    missing = [name for name in WEIGHTS if name not in dimensions]
    if missing:
        raise ValueError(f"Missing score dimensions: {', '.join(missing)}")

    score = 0.0
    for name, weight in WEIGHTS.items():
        value = float(dimensions[name])
        if not 1 <= value <= 10:
            raise ValueError(f"Score {name}={value} is outside 1..10")
        score += value * weight

    accuracy = float(dimensions["accuracy"])
    if accuracy < 5:
        return min(score, 4.0)
    if accuracy < 7:
        return min(score, 7.0)
    return score


def z_scores(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    mean = statistics.fmean(values.values())
    if len(values) < 2:
        return {key: 0.0 for key in values}
    std = statistics.pstdev(values.values())
    if math.isclose(std, 0.0):
        return {key: 0.0 for key in values}
    return {key: (value - mean) / std for key, value in values.items()}


def aggregate(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates", [])
    reviews = payload.get("reviews", [])
    candidate_ids = [candidate["id"] for candidate in candidates]
    if not candidate_ids:
        raise ValueError("At least one candidate is required")
    if not reviews:
        raise ValueError("At least one review is required")

    raw_scores: dict[str, list[float]] = {candidate_id: [] for candidate_id in candidate_ids}
    normalized_scores: dict[str, list[float]] = {candidate_id: [] for candidate_id in candidate_ids}
    blocking_issues: dict[str, list[str]] = {candidate_id: [] for candidate_id in candidate_ids}

    for review in reviews:
        reviewer_scores = review.get("scores", {})
        excluded = set(review.get("excluded_candidates", []))
        unknown_excluded = sorted(excluded.difference(candidate_ids))
        if unknown_excluded:
            raise ValueError(f"Review excludes unknown candidates: {', '.join(unknown_excluded)}")
        expected_candidate_ids = [candidate_id for candidate_id in candidate_ids if candidate_id not in excluded]
        missing_scores = [candidate_id for candidate_id in expected_candidate_ids if candidate_id not in reviewer_scores]
        if missing_scores:
            reviewer = review.get("reviewer", "unknown")
            raise ValueError(f"Review {reviewer} missing scores for candidates: {', '.join(missing_scores)}")

        per_reviewer_raw: dict[str, float] = {}
        for candidate_id in expected_candidate_ids:
            if candidate_id not in reviewer_scores:
                continue
            score = weighted_score(reviewer_scores[candidate_id])
            raw_scores[candidate_id].append(score)
            per_reviewer_raw[candidate_id] = score

        for candidate_id, normalized in z_scores(per_reviewer_raw).items():
            normalized_scores[candidate_id].append(normalized)

        for candidate_id, issues in review.get("blocking_issues", {}).items():
            if candidate_id in blocking_issues:
                blocking_issues[candidate_id].extend(str(issue) for issue in issues)

    results: list[CandidateScore] = []
    for candidate_id in candidate_ids:
        normalized = normalized_scores[candidate_id]
        raw = raw_scores[candidate_id]
        if not normalized or not raw:
            continue
        stderr = 0.0
        if len(normalized) > 1:
            stderr = statistics.pstdev(normalized) / math.sqrt(len(normalized))
        issues = blocking_issues[candidate_id]
        results.append(
            CandidateScore(
                candidate_id=candidate_id,
                raw_mean=round(statistics.fmean(raw), 4),
                normalized_mean=round(statistics.fmean(normalized), 4),
                normalized_stderr=round(stderr, 4),
                review_count=len(raw),
                blocked=bool(issues),
                blocking_issues=issues,
            )
        )

    if not results:
        raise ValueError("No candidate received valid scores")

    ranking = sorted(
        results,
        key=lambda item: (item.blocked, -item.normalized_mean, -item.raw_mean, item.candidate_id),
    )
    top = ranking[0]
    second = ranking[1] if len(ranking) > 1 else None
    margin = None if second is None else round(top.normalized_mean - second.normalized_mean, 4)
    tied_with_next = bool(second and margin is not None and margin < 0.25)
    if top.blocked:
        confidence = "blocked"
    elif tied_with_next:
        confidence = "low"
    elif margin is not None and margin >= 0.60 and top.normalized_stderr <= 0.45:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "winner": top.candidate_id,
        "confidence": confidence,
        "tied_with_next": tied_with_next,
        "top_margin": margin,
        "weights": WEIGHTS,
        "ranking": [
            {
                "candidate_id": item.candidate_id,
                "raw_mean": item.raw_mean,
                "normalized_mean": item.normalized_mean,
                "normalized_stderr": item.normalized_stderr,
                "review_count": item.review_count,
                "blocked": item.blocked,
                "blocking_issues": item.blocking_issues,
            }
            for item in ranking
        ],
    }


def forge_weighted_score(dimensions: dict[str, Any]) -> float:
    missing = [name for name in FORGE_WEIGHTS if name not in dimensions]
    if missing:
        raise ValueError(f"Missing Forge score dimensions: {', '.join(missing)}")
    score = 0.0
    for name, weight in FORGE_WEIGHTS.items():
        value = float(dimensions[name])
        if not 1 <= value <= 10:
            raise ValueError(f"Forge score {name}={value} is outside 1..10")
        score += value * weight
    return round(score, 4)


def assess_forge_convergence(payload: dict[str, Any]) -> dict[str, Any]:
    agents = payload.get("agents", {})
    if not isinstance(agents, dict) or not agents:
        raise ValueError("Forge convergence requires at least one agent score")
    persistent_dissent = payload.get("persistent_dissent", [])
    if persistent_dissent is None:
        persistent_dissent = []
    if not isinstance(persistent_dissent, list):
        raise ValueError("persistent_dissent must be a list")

    agent_results: dict[str, Any] = {}
    alignments: list[float] = []
    totals: list[float] = []
    blockers: list[str] = []
    for agent_id, scores in agents.items():
        if not isinstance(scores, dict):
            raise ValueError(f"Forge agent score for {agent_id} must be an object")
        alignment = float(scores.get("alignment", 0))
        if not 1 <= alignment <= 10:
            raise ValueError(f"Forge alignment for {agent_id} is outside 1..10")
        weighted = forge_weighted_score(scores)
        agent_blockers = [str(item) for item in scores.get("blockers", []) if str(item).strip()]
        blockers.extend(f"{agent_id}: {item}" for item in agent_blockers)
        alignments.append(alignment)
        totals.append(weighted)
        agent_results[str(agent_id)] = {
            "alignment": alignment,
            "weighted_score": weighted,
            "blockers": agent_blockers,
        }

    score_stdev = statistics.pstdev(totals) if len(totals) > 1 else 0.0
    min_alignment = min(alignments)
    converged = (
        min_alignment >= FORGE_ALIGNMENT_THRESHOLD
        and score_stdev <= FORGE_SCORE_STDEV_THRESHOLD
        and not blockers
        and not persistent_dissent
    )
    # Strong discord = creators disagree from the start (low alignment or wide spread).
    # It auto-triggers the next round; a near-miss stays opt-in.
    strong_discord = (
        min_alignment < FORGE_STRONG_DISCORD_ALIGNMENT
        or score_stdev > FORGE_STRONG_DISCORD_STDEV
    )
    if converged:
        second_round = "none"
    elif strong_discord:
        second_round = "auto"
    else:
        second_round = "optional"
    return {
        "label": "forge_convergence_assessment",
        "status": "converged" if converged else "nonconverged",
        "converged": converged,
        "strong_discord": strong_discord,
        "second_round": second_round,
        "min_alignment": round(min_alignment, 4),
        "score_stdev": round(score_stdev, 4),
        "thresholds": {
            "min_alignment": FORGE_ALIGNMENT_THRESHOLD,
            "score_stdev": FORGE_SCORE_STDEV_THRESHOLD,
            "strong_discord_alignment": FORGE_STRONG_DISCORD_ALIGNMENT,
            "strong_discord_stdev": FORGE_STRONG_DISCORD_STDEV,
        },
        "weights": FORGE_WEIGHTS,
        "agent_results": agent_results,
        "persistent_dissent": [str(item) for item in persistent_dissent],
        "blockers": blockers,
    }


def session_reviewers(
    mode: str,
    frontend_review: bool = False,
    skill_review: bool = False,
    session_type: str = "general",
    panel: str = "full",
) -> list[str]:
    if skill_review or session_type == "forge":
        return []
    if panel in {"solo", "triad", "targeted"}:
        reviewers = ["coverage-integrator"] if mode != "fast" else []
        if frontend_review:
            reviewers.extend(FRONTEND_REVIEWER_FILES.values())
        return reviewers
    reviewers = BASE_REVIEWERS.copy()
    if mode == "deep":
        reviewers = DEEP_REVIEWERS + reviewers
    if frontend_review:
        reviewers.extend(FRONTEND_REVIEWER_FILES.values())
    return reviewers


def session_evidence_runners(frontend_review: bool = False) -> list[str]:
    if not frontend_review:
        return []
    return list(EVIDENCE_RUNNER_FILES.values())


def reviewer_filename(reviewer: str) -> str:
    for filename, label in FRONTEND_REVIEWER_FILES.items():
        if label == reviewer:
            return filename
    if reviewer in BASE_REVIEWERS or reviewer in DEEP_REVIEWERS:
        return f"{reviewer}.md"
    return f"{slugify(reviewer)}.md"


def render_dispatch_announcement(
    mode: str,
    token_budget: str,
    frontend_review: bool = False,
    skill_review: bool = False,
    session_type: str = "general",
    panel: str = "full",
) -> str:
    panel_label = "skill-review" if skill_review else session_type if session_type != "general" else mode
    if panel != "full":
        panel_label = f"{panel_label}/{panel}"
    members = len(active_role_files(skill_review, session_type, panel))
    reviewers = len(session_reviewers(mode, frontend_review, skill_review, session_type, panel))
    runners = len(session_evidence_runners(frontend_review))
    suffix = f", {runners} evidence runners" if runners else ""
    return f"{panel_label} panel: dispatched {members} members, {reviewers} reviewers{suffix} ({token_budget})"


def render_council_banner(
    mode: str,
    token_budget: str,
    frontend_review: bool = False,
    skill_review: bool = False,
    session_type: str = "general",
    panel: str = "full",
) -> str:
    reviewers = len(session_reviewers(mode, frontend_review, skill_review, session_type, panel))
    runners = len(session_evidence_runners(frontend_review))
    gates = "performance"
    roles = len(active_role_files(skill_review, session_type, panel))
    if skill_review:
        gates = "skill-review"
    if session_type == "forge":
        gates = "bounded creation"
    if frontend_review:
        gates += " + UX + Bob"
    width = 80
    border = "+" + "-" * (width - 2) + "+"

    def row(text: str = "") -> str:
        inner_width = width - 4
        if len(text) > inner_width:
            raise ValueError(f"Banner row is too wide ({len(text)} > {inner_width}): {text}")
        return f"| {text.center(inner_width)} |"

    is_forge = session_type == "forge"
    title = "CODEX FORGE" if is_forge else "CODEX COUNCIL"
    tagline = "IMAGINE / SHAPE / CONVERGE" if is_forge else "INDEPENDENT / ANONYMOUS / EVIDENCE-LED"
    members = (
        "[FULLER]  [HEDY]  [KATHERINE]  [HAMILTON]  [VON NEUMANN]"
        if is_forge
        else "[ADA]  [GRACE]  [HYPATIA]  [FLORENCE]  [TURING]  [CRAY]"
    )
    connectors = (
        r"\       \           |           /       /"
        if is_forge
        else r"\       \       \       /       /       /"
    )
    flow = (
        "DIVERGE > SYNTHESIZE > RE-BRIEF > CONVERGE"
        if is_forge
        else "FIRST OPINIONS > ANONYMOUS REVIEW > CHAIRMAN VERDICT"
    )
    core_width = 64
    core_border = "+" + "-" * (core_width - 2) + "+"
    core_row = f"| {flow.center(core_width - 4)} |"
    configuration = f"{mode.upper()} / {session_type.upper()} / {token_budget.upper()}"
    counts = f"MEMBERS {roles:02d} / REVIEWERS {reviewers:02d} / RUNNERS {runners:02d}"

    return "\n".join(
        [
            border,
            row(title),
            row(tagline),
            row(),
            row(members),
            row(connectors),
            row(core_border),
            row(core_row),
            row(core_border),
            row(),
            row(configuration),
            row(counts),
            row(f"GATES / {gates.upper()}"),
            border,
        ]
    )


def estimate_tokens(characters: int) -> int:
    if characters <= 0:
        return 0
    return math.ceil(characters / TOKEN_ESTIMATE_CHARS_PER_TOKEN)


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _session_artifacts(session_dir: Path) -> list[Path]:
    artifacts: list[Path] = []
    for path in sorted(session_dir.rglob("*")):
        if not path.is_file():
            continue
        if DECISION_RUNTIME_DIR in path.relative_to(session_dir).parts:
            continue
        if path.name in GENERATED_STATS_FILES:
            continue
        if path.suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
            artifacts.append(path)
    return artifacts


def _text_metric(path: Path, root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    characters = len(text)
    words = len(re.findall(r"\S+", text))
    return {
        "path": path.relative_to(root).as_posix(),
        "characters": characters,
        "words": words,
        "estimated_tokens": estimate_tokens(characters),
    }


def _sum_tokens(paths: list[Path], root: Path) -> tuple[int, list[dict[str, Any]]]:
    metrics = [_text_metric(path, root) for path in paths if path.exists()]
    return sum(metric["estimated_tokens"] for metric in metrics), metrics


def _markdown_has_body(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return True
    return False


def load_pre_execution_estimate(session_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        _read_json_object(session_dir / "preflight-estimate.json"),
        metadata.get("pre_execution_estimate", {}),
        metadata.get("pre_session_estimate", {}),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("pre_execution_estimate")
        if isinstance(nested, dict) and "total_tokens" in nested:
            return nested
        if "total_tokens" in candidate:
            return candidate
        if "estimated_total_tokens" in candidate:
            return {
                "label": "pre_execution_estimate",
                "total_tokens": candidate.get("estimated_total_tokens", 0),
                "input_tokens": candidate.get("estimated_input_tokens", 0),
                "output_tokens": candidate.get("estimated_output_tokens", 0),
                "range": candidate.get("estimated_total_tokens_range", {}),
                "components": {},
                "assumptions": {
                    "note": "Legacy pre-session estimate normalized for stats comparison.",
                },
            }
    return {
        "label": "pre_execution_estimate",
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "range": {},
        "components": {},
        "assumptions": {
            "note": "Missing preflight estimate. Run init through the preflight flow for comparable pre/post accounting.",
        },
    }


def collect_artifact_tokens(session_dir: Path) -> dict[str, Any]:
    file_breakdown: list[dict[str, Any]] = []
    total_characters = 0
    total_words = 0

    for path in _session_artifacts(session_dir):
        metric = _text_metric(path, session_dir)
        total_characters += metric["characters"]
        total_words += metric["words"]
        file_breakdown.append(metric)

    top_artifacts = sorted(file_breakdown, key=lambda item: item["estimated_tokens"], reverse=True)[:5]
    return {
        "label": "artifact_only_tokens",
        "source": "saved local session artifact text only",
        "method": f"ceil(total_characters / {TOKEN_ESTIMATE_CHARS_PER_TOKEN})",
        "characters": total_characters,
        "words": total_words,
        "total_tokens": estimate_tokens(total_characters),
        "estimated_tokens": estimate_tokens(total_characters),
        "is_actual_codex_usage": False,
        "limitation": "Artifact-only tokens are not comparable to full session cost because they exclude unsaved prompt/output/tool overhead.",
        "top_artifacts": top_artifacts,
        "file_breakdown": file_breakdown,
    }


def collect_post_execution_estimate(session_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    prompts_dir = session_dir / "prompts"
    member_prompt_paths = sorted((prompts_dir / "members").glob("*.md")) if (prompts_dir / "members").is_dir() else []
    reviewer_prompt_paths = sorted((prompts_dir / "reviewers").glob("*.md")) if (prompts_dir / "reviewers").is_dir() else []
    chairman_prompt_paths = [
        path
        for path in [
            prompts_dir / "chairman-synthesis.md",
            prompts_dir / SYNTHESIS_INPUT_MANIFEST,
        ]
        if path.exists()
    ]
    member_output_paths = sorted((session_dir / "members").glob("*.md")) if (session_dir / "members").is_dir() else []
    reviewer_output_paths = sorted((session_dir / "reviews").glob("*.md")) if (session_dir / "reviews").is_dir() else []
    synthesis_output_paths = [session_dir / "final.md"] if (session_dir / "final.md").exists() else []
    browser_output_paths = (
        sorted((session_dir / "evidence-runners").glob("*.md"))
        if (session_dir / "evidence-runners").is_dir()
        else []
    )
    scoring_paths = [
        path
        for path in [
            session_dir / "reviews" / "reviews.example.json",
            session_dir / "preflight-estimate.json",
            session_dir / "preflight-estimate.md",
        ]
        if path.exists()
    ]
    member_input, member_input_files = _sum_tokens(member_prompt_paths, session_dir)
    reviewer_input, reviewer_input_files = _sum_tokens(reviewer_prompt_paths, session_dir)
    synthesis_input, synthesis_input_files = _sum_tokens(chairman_prompt_paths, session_dir)
    member_output, member_output_files = _sum_tokens(member_output_paths, session_dir)
    reviewer_output, reviewer_output_files = _sum_tokens(reviewer_output_paths, session_dir)
    synthesis_output, synthesis_output_files = _sum_tokens(synthesis_output_paths, session_dir)
    browser_output, browser_output_files = _sum_tokens(browser_output_paths, session_dir)
    scoring_tokens, scoring_files = _sum_tokens(scoring_paths, session_dir)
    prompt_count = len(member_prompt_paths) + len(reviewer_prompt_paths) + len(chairman_prompt_paths)
    tool_overhead = TOOL_OVERHEAD_BASE_TOKENS + (prompt_count * TOOL_OVERHEAD_PER_PROMPT_TOKENS)
    missing_data: list[str] = []
    if not member_prompt_paths:
        missing_data.append("missing member prompts")
    if (
        not reviewer_prompt_paths
        and metadata.get("mode") != "fast"
        and not metadata.get("skill_review")
        and metadata.get("session_type") != "forge"
    ):
        missing_data.append("missing reviewer prompts")
    if not chairman_prompt_paths:
        missing_data.append("missing chairman synthesis prompt")
    for path in member_output_paths + reviewer_output_paths + synthesis_output_paths:
        if not _markdown_has_body(path):
            missing_data.append(f"partial output: {path.relative_to(session_dir).as_posix()}")
    coverage = "full" if not missing_data else "partial"
    components = {
        "member_input_tokens": member_input,
        "member_output_tokens": member_output,
        "reviewer_input_tokens": reviewer_input,
        "reviewer_output_tokens": reviewer_output,
        "synthesis_input_tokens": synthesis_input,
        "synthesis_output_tokens": synthesis_output,
        "browser_evidence_tokens": browser_output,
        "scorer_stats_artifact_tokens": scoring_tokens,
        "estimated_tool_overhead_tokens": tool_overhead,
    }
    input_tokens = member_input + reviewer_input + synthesis_input
    output_tokens = member_output + reviewer_output + synthesis_output + browser_output
    total = input_tokens + output_tokens + scoring_tokens + tool_overhead
    return {
        "label": "post_execution_estimate",
        "source": "saved prompts, saved outputs, scoring artifacts, and estimated tool overhead",
        "coverage": coverage,
        "total_tokens": total,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "components": components,
        "files": {
            "member_inputs": member_input_files,
            "member_outputs": member_output_files,
            "reviewer_inputs": reviewer_input_files,
            "reviewer_outputs": reviewer_output_files,
            "synthesis_inputs": synthesis_input_files,
            "synthesis_outputs": synthesis_output_files,
            "browser_outputs": browser_output_files,
            "scoring_stats": scoring_files,
        },
        "missing_data": missing_data,
        "unmeasured_overhead_note": "No access to actual Codex billing/API usage, cached input, hidden system prompts, or exact tool-call token accounting. Tool overhead is estimated.",
        "is_actual_codex_usage": False,
    }


def calibration_recommendation(pre_total: int, post_total: int, coverage: str) -> dict[str, Any]:
    if pre_total <= 0 or post_total <= 0:
        return {
            "action": "insufficient_data",
            "message": "Cannot calibrate without both pre and post estimates.",
        }
    ratio = round(post_total / pre_total, 4)
    if coverage != "full":
        action = "do_not_calibrate"
        message = "Post estimate is partial; persist complete prompts and outputs before updating future multipliers."
    elif ratio > 1.25:
        action = "increase_future_estimates"
        message = "Post estimate exceeded preflight materially; increase the local multiplier."
    elif ratio < 0.75:
        action = "decrease_future_estimates"
        message = "Post estimate was materially below preflight; decrease the local multiplier cautiously."
    else:
        action = "keep_multiplier"
        message = "Pre/post estimates are close enough; keep current multiplier."
    return {"action": action, "ratio": ratio, "message": message}


def collect_session_stats(session_dir: Path) -> dict[str, Any]:
    session_dir = Path(session_dir)
    metadata = _read_json_object(session_dir / "session.json")
    validation = validate_session(session_dir)
    artifact_only = collect_artifact_tokens(session_dir)
    pre_execution = load_pre_execution_estimate(session_dir, metadata)
    post_execution = collect_post_execution_estimate(session_dir, metadata)
    pre_total = int(pre_execution.get("total_tokens") or 0)
    post_total = int(post_execution.get("total_tokens") or 0)
    delta = post_total - pre_total if pre_total or post_total else None
    ratio = round(post_total / pre_total, 4) if pre_total > 0 else None
    return {
        "session": {
            "id": session_dir.name,
            "mode": metadata.get("mode", "unknown"),
            "session_type": metadata.get("session_type", "general"),
            "status": metadata.get("status", "unknown"),
            "final_state": metadata.get("final_state", "unknown"),
            "token_budget": metadata.get("token_budget", "unknown"),
            "frontend_review": "frontend-ui-ux" in metadata.get("activation_tags", []),
            "skill_review": "skill-review" in metadata.get("activation_tags", []),
        },
        "counts": {
            "roles": len(metadata.get("roles", [])),
            "reviewers": len(metadata.get("reviewers", [])),
            "evidence_runners": len(metadata.get("evidence_runners", [])),
            "artifact_files": len(artifact_only["file_breakdown"]),
            "member_files": len(list((session_dir / "members").glob("*.md"))) if (session_dir / "members").is_dir() else 0,
            "review_files": len(list((session_dir / "reviews").glob("*.md"))) if (session_dir / "reviews").is_dir() else 0,
            "evidence_files": (
                len(list((session_dir / "evidence-runners").glob("*.md")))
                if (session_dir / "evidence-runners").is_dir()
                else 0
            ),
        },
        "pre_execution_estimate": pre_execution,
        "post_execution_estimate": post_execution,
        "artifact_only_tokens": artifact_only,
        "delta": {
            "post_minus_pre_tokens": delta,
            "ratio_post_to_pre": ratio,
        },
        "calibration_recommendation": calibration_recommendation(
            pre_total,
            post_total,
            str(post_execution.get("coverage", "partial")),
        ),
        "missing_unmeasured_data": {
            "coverage": post_execution.get("coverage", "partial"),
            "missing_data": post_execution.get("missing_data", []),
            "unmeasured_overhead_note": post_execution["unmeasured_overhead_note"],
        },
        "estimated_artifact_usage": {
            "label": "estimated artifact tokens",
            "source": artifact_only["source"],
            "method": artifact_only["method"],
            "characters": artifact_only["characters"],
            "words": artifact_only["words"],
            "estimated_tokens": artifact_only["total_tokens"],
            "is_actual_codex_usage": False,
            "limitation": artifact_only["limitation"],
        },
        "top_artifacts": artifact_only["top_artifacts"],
        "file_breakdown": artifact_only["file_breakdown"],
        "validation": validation,
    }


def render_session_stats(stats: dict[str, Any]) -> str:
    session = stats["session"]
    counts = stats["counts"]
    pre = stats["pre_execution_estimate"]
    post = stats["post_execution_estimate"]
    artifact = stats["artifact_only_tokens"]
    delta = stats["delta"]
    recommendation = stats["calibration_recommendation"]
    missing = stats["missing_unmeasured_data"]
    validation = stats["validation"]
    lines = [
        "# Codex Council Session Stats",
        "",
        "Token numbers are local estimates, not actual Codex usage, billing telemetry, hidden prompt overhead, or exact tool-call accounting.",
        "",
        f"- Mode: {session['mode']}",
        f"- Type: {session.get('session_type', 'general')}",
        f"- Token profile: {session['token_budget']}",
        f"- Status: {session['status']} -> {session['final_state']}",
        f"- Frontend gate: {'active' if session['frontend_review'] else 'inactive'}",
        f"- Roles: {counts['roles']}",
        f"- Reviewers: {counts['reviewers']}",
        f"- Evidence runners: {counts['evidence_runners']}",
        f"- Validation: {'ok' if validation['ok'] else 'problems found'}",
        "",
        "## Pre-execution estimate",
        f"- Total tokens: {pre.get('total_tokens', 0)}",
        f"- Input/output tokens: {pre.get('input_tokens', 0)}/{pre.get('output_tokens', 0)}",
        f"- Range: {pre.get('range', {}).get('low', 0)}..{pre.get('range', {}).get('high', 0)}",
        "",
        "## Post-execution estimate",
        f"- Total tokens: {post.get('total_tokens', 0)}",
        f"- Input/output tokens: {post.get('input_tokens', 0)}/{post.get('output_tokens', 0)}",
        f"- Coverage: {post.get('coverage', 'partial')}",
        f"- Member input/output: {post['components']['member_input_tokens']}/{post['components']['member_output_tokens']}",
        f"- Reviewer input/output: {post['components']['reviewer_input_tokens']}/{post['components']['reviewer_output_tokens']}",
        f"- Synthesis input/output: {post['components']['synthesis_input_tokens']}/{post['components']['synthesis_output_tokens']}",
        f"- Scorer/stats artifacts: {post['components']['scorer_stats_artifact_tokens']}",
        f"- Estimated tool overhead: {post['components']['estimated_tool_overhead_tokens']}",
        "",
        "## Artifact-only tokens",
        f"- Total tokens: {artifact['total_tokens']}",
        f"- Text counted: {artifact['characters']} characters, {artifact['words']} words",
        f"- Artifact files counted: {counts['artifact_files']}",
        "",
        "## Delta",
        f"- Post - pre tokens: {delta['post_minus_pre_tokens']}",
        f"- Post / pre ratio: {delta['ratio_post_to_pre']}",
        "",
        "## Calibration recommendation",
        f"- Action: {recommendation['action']}",
        f"- Message: {recommendation['message']}",
        "",
        "## Missing/unmeasured data",
        f"- Coverage: {missing['coverage']}",
        f"- Unmeasured overhead note: {missing['unmeasured_overhead_note']}",
    ]
    if missing["missing_data"]:
        lines.extend(f"- {item}" for item in missing["missing_data"])
    if artifact["top_artifacts"]:
        lines.extend(["", "## Largest Artifacts"])
        for item in artifact["top_artifacts"]:
            lines.append(
                f"- {item['path']}: {item['estimated_tokens']} estimated tokens"
            )
    if not validation["ok"]:
        lines.extend(["", "## Validation Problems"])
        lines.extend(f"- {problem}" for problem in validation["problems"])
    return "\n".join(lines)


def write_session_stats(session_dir: Path, stats: dict[str, Any]) -> None:
    (session_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    (session_dir / "stats.md").write_text(render_session_stats(stats) + "\n", encoding="utf-8")


def doctor_session(session_dir: Path) -> dict[str, Any]:
    session_dir = Path(session_dir)
    problems: list[dict[str, str]] = []
    validation = validate_session(session_dir)
    for problem in validation["problems"]:
        problems.append({"severity": "error", "code": "session_validation", "message": problem})
    metadata_path = session_dir / "session.json"
    metadata = _read_json_object(metadata_path) if metadata_path.exists() else {}
    intelligence_files = (CONTEXT_CAPSULE_FILE, RUN_MANIFEST_FILE, DECISION_LEDGER_FILE, TELEMETRY_FILE)
    has_intelligence_layer = isinstance(metadata.get("intelligence_layer"), dict) or any(
        (session_dir / filename).exists() for filename in intelligence_files
    )
    if has_intelligence_layer:
        for filename in intelligence_files:
            path = session_dir / filename
            if not path.exists():
                problems.append({"severity": "error", "code": "missing_intelligence_artifact", "message": filename})
                continue
            data = _read_json_object(path)
            if data.get("schema_version") != INTELLIGENCE_SCHEMA_VERSION:
                problems.append({"severity": "error", "code": "schema_version", "message": filename})
    try:
        runtime_health = council_cells.doctor_runtime(session_dir)
    except (council_cells.DecisionRuntimeError, OSError, TypeError, ValueError) as exc:
        runtime_health = {
            "ok": False,
            "status": "quarantined",
            "fallback_reason": "runtime_diagnostic_failed",
            "problems": [{"code": "runtime_diagnostic_failed", "message": str(exc)}],
            "generation": None,
            "authoritative": False,
            "read_only": True,
        }
    if runtime_health["status"] == "quarantined":
        problems.append(
            {
                "severity": "error",
                "code": "decision_runtime_quarantined",
                "message": runtime_health.get("fallback_reason") or "Decision Runtime failed closed to legacy artifacts.",
            }
        )
    stats = collect_session_stats(session_dir)
    coverage = stats.get("post_execution_estimate", {}).get("coverage", "partial")
    if coverage != "full":
        problems.append(
            {
                "severity": "warn",
                "code": "partial_coverage",
                "message": "Post estimate is partial until prompts and outputs contain real body content.",
            }
        )
    ok = not any(problem["severity"] == "error" for problem in problems)
    return {
        "ok": ok,
        "session": session_dir.name,
        "coverage": coverage,
        "problems": problems,
        "decision_runtime": runtime_health,
        "pre_execution_total_tokens": stats["pre_execution_estimate"].get("total_tokens", 0),
        "post_execution_total_tokens": stats["post_execution_estimate"].get("total_tokens", 0),
    }


def collect_state_dashboard(state_root: Path) -> dict[str, Any]:
    state_root = Path(state_root)
    sessions_dir = state_root / DEFAULT_SESSION_SUBDIR
    if not sessions_dir.exists() and state_root.name == DEFAULT_SESSION_SUBDIR:
        sessions_dir = state_root
    elif (
        not sessions_dir.exists()
        and state_root.exists()
        and any((child / "session.json").exists() for child in state_root.iterdir() if child.is_dir())
    ):
        sessions_dir = state_root
    sessions = [path for path in sorted(sessions_dir.iterdir()) if path.is_dir()] if sessions_dir.exists() else []
    totals = {
        "pre_execution_tokens": 0,
        "post_execution_tokens": 0,
        "artifact_only_tokens": 0,
    }
    coverage: dict[str, int] = {}
    session_rows: list[dict[str, Any]] = []
    unique_findings = 0
    for session in sessions:
        stats_path = session / "stats.json"
        stats = _read_json_object(stats_path) if stats_path.exists() else collect_session_stats(session)
        pre_total = int(stats.get("pre_execution_estimate", {}).get("total_tokens") or 0)
        post_total = int(stats.get("post_execution_estimate", {}).get("total_tokens") or 0)
        artifact_total = int(stats.get("artifact_only_tokens", {}).get("total_tokens") or 0)
        cov = str(stats.get("post_execution_estimate", {}).get("coverage", "partial"))
        totals["pre_execution_tokens"] += pre_total
        totals["post_execution_tokens"] += post_total
        totals["artifact_only_tokens"] += artifact_total
        coverage[cov] = coverage.get(cov, 0) + 1
        findings = []
        findings_path = session / FINDINGS_FILE
        if findings_path.exists():
            for line in findings_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        unique_findings += deduplicate_findings(findings).get("unique_count", 0)
        session_rows.append(
            {
                "session": session.name,
                "pre_execution_tokens": pre_total,
                "post_execution_tokens": post_total,
                "coverage": cov,
            }
        )
    denominator = max(totals["post_execution_tokens"], 1)
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "state_root": str(state_root),
        "session_count": len(session_rows),
        "totals": totals,
        "coverage": coverage,
        "efficiency": {
            "unique_signal_per_1k_tokens": round(unique_findings / denominator * 1000, 4),
            "unique_findings": unique_findings,
        },
        "sessions": session_rows,
    }


def render_state_dashboard(dashboard: dict[str, Any]) -> str:
    totals = dashboard["totals"]
    efficiency = dashboard["efficiency"]
    return "\n".join(
        [
            "# Codex Council Dashboard",
            "",
            f"- Sessions: {dashboard['session_count']}",
            f"- Pre-execution tokens: {totals['pre_execution_tokens']}",
            f"- Post-execution tokens: {totals['post_execution_tokens']}",
            f"- Artifact-only tokens: {totals['artifact_only_tokens']}",
            f"- Unique signal / 1k tokens: {efficiency['unique_signal_per_1k_tokens']}",
        ]
    )


def write_raw_output_bundle(session_dir: Path) -> Path:
    metadata = _read_json_object(session_dir / "session.json")
    paths: list[str] = []
    for folder in ("members", "reviews", "evidence-runners"):
        directory = session_dir / folder
        if directory.is_dir():
            paths.extend(path.relative_to(session_dir).as_posix() for path in sorted(directory.glob("*.md")))
    if (session_dir / "final.md").exists():
        paths.append("final.md")
    bundle = {
        "version": 1,
        "session_id": session_dir.name,
        "session_type": metadata.get("session_type", "general"),
        "content_policy": "path-only; no raw prompt or output text",
        "retention": "local plugin state; delete session directory to purge",
        "paths": paths,
    }
    path = session_dir / RAW_OUTPUT_BUNDLE
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return path


def record_invocation_log(session_dir: Path, storage_root: Path, metadata: dict[str, Any]) -> Path:
    path = invocation_log_path(storage_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": metadata.get("created_at", utc_now()),
        "session_id": session_dir.name,
        "session_type": metadata.get("session_type", "general"),
        "mode": metadata.get("mode", "unknown"),
        "token_budget": metadata.get("token_budget", "unknown"),
        "member_count": len(metadata.get("roles", [])),
        "reviewer_count": len(metadata.get("reviewers", [])),
        "evidence_runner_count": len(metadata.get("evidence_runners", [])),
        "frontend_review": "frontend-ui-ux" in metadata.get("activation_tags", []),
        "skill_review": "skill-review" in metadata.get("activation_tags", []),
        "status": metadata.get("status", "unknown"),
    }
    path.write_text(path.read_text(encoding="utf-8") + json.dumps(entry, sort_keys=True) + "\n" if path.exists() else json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_context_capsule(
    topic: str,
    root: Path,
    metadata: dict[str, Any],
    route_decision: dict[str, Any],
    compiled_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "created_at": metadata.get("created_at", utc_now()),
        "topic": topic,
        "session_type": metadata.get("session_type", "general"),
        "mode": metadata.get("mode", "standard"),
        "token_budget": metadata.get("token_budget", "compact"),
        "panel": metadata.get("panel", "full"),
        "workspace_root": str(root),
        "risk_flags": route_decision.get("risk_flags", []),
        "constraints": [
            "Preserve blockers, dissent, verification, and confidence.",
            "Do not claim real billing/API token usage.",
            "Keep routing advisory unless explicitly requested.",
        ],
        "source_metadata": {
            "storage_scope": metadata.get("storage_scope", "plugin-local"),
            "role_count": len(metadata.get("roles", [])),
            "reviewer_count": len(metadata.get("reviewers", [])),
            "evidence_runner_count": len(metadata.get("evidence_runners", [])),
        },
        "compiled_context": compiled_context,
    }


def write_intelligence_artifacts(
    session_dir: Path,
    root: Path,
    metadata: dict[str, Any],
    pre_session_estimate: dict[str, Any],
    route_decision: dict[str, Any],
    compiled_context: dict[str, Any],
) -> None:
    capsule = build_context_capsule(metadata.get("topic", ""), root, metadata, route_decision, compiled_context)
    manifest = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "session_id": session_dir.name,
        "created_at": metadata.get("created_at", utc_now()),
        "mode": metadata.get("mode", "standard"),
        "session_type": metadata.get("session_type", "general"),
        "panel": metadata.get("panel", "full"),
        "router": route_decision,
        "privacy": {
            "state_scope": metadata.get("storage_scope", "plugin-local"),
            "raw_prompt_logging": "session-local only",
            "invocation_log": "sanitized metadata only",
        },
        "artifacts": {
            "context_capsule": CONTEXT_CAPSULE_FILE,
            "decision_ledger": DECISION_LEDGER_FILE,
            "findings": FINDINGS_FILE,
            "telemetry": TELEMETRY_FILE,
        },
    }
    ledger = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "session_id": session_dir.name,
        "status": metadata.get("status", "scaffolded"),
        "decisions": [],
        "blockers": [],
        "dissent": [],
        "verification": [],
        "confidence": "pending",
        "next_prompt": "",
    }
    telemetry = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "session_id": session_dir.name,
        "created_at": metadata.get("created_at", utc_now()),
        "pre_execution_estimate": pre_session_estimate.get("pre_execution_estimate", {}),
        "counts": {
            "roles": len(metadata.get("roles", [])),
            "reviewers": len(metadata.get("reviewers", [])),
            "evidence_runners": len(metadata.get("evidence_runners", [])),
        },
        "timings": {},
        "coverage": "preflight_only",
    }
    placeholder_finding = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "kind": "placeholder",
        "message": "Normalized findings are appended here after member/reviewer outputs exist.",
    }
    (session_dir / CONTEXT_CAPSULE_FILE).write_text(json.dumps(capsule, indent=2) + "\n", encoding="utf-8")
    (session_dir / RUN_MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (session_dir / DECISION_LEDGER_FILE).write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    (session_dir / TELEMETRY_FILE).write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")
    (session_dir / ROUTER_DECISION_FILE).write_text(json.dumps(route_decision, indent=2) + "\n", encoding="utf-8")
    (session_dir / COMPILED_CONTEXT_FILE).write_text(json.dumps(compiled_context, indent=2) + "\n", encoding="utf-8")
    (session_dir / FINDINGS_FILE).write_text(json.dumps(placeholder_finding, sort_keys=True) + "\n", encoding="utf-8")


def init_session(
    topic: str,
    root: Path,
    mode: str = "standard",
    frontend_review: bool = False,
    token_budget: str = "compact",
    session_type: str = "general",
    skill_review: bool = False,
    pre_session_estimate: Optional[dict[str, Any]] = None,
    confirmation: Optional[dict[str, Any]] = None,
    session_root: Optional[Path] = None,
    config_root: Optional[Path] = None,
    panel: str = "full",
    router: str = "off",
    max_agents: Optional[int] = None,
    early_exit: bool = False,
    delta_from: Optional[Path] = None,
    decision_runtime: str = "off",
) -> Path:
    if mode not in MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(MODES))}")
    if token_budget not in TOKEN_BUDGETS:
        raise ValueError(f"token_budget must be one of: {', '.join(sorted(TOKEN_BUDGETS))}")
    if decision_runtime not in DECISION_RUNTIME_MODES:
        raise ValueError(f"decision_runtime must be one of: {', '.join(sorted(DECISION_RUNTIME_MODES))}")
    session_type, frontend_review, skill_review = normalize_session_options(session_type, frontend_review, skill_review)
    route_decision = route_council_panel(
        topic,
        mode=mode,
        session_type=session_type,
        frontend_review=frontend_review,
        skill_review=skill_review,
        requested_panel=panel,
        router=router,
        max_agents=max_agents,
        early_exit=early_exit,
    )
    active_panel = route_decision["selected_panel"]
    runtime_problems = validate_runtime_contract(plugin_root())
    if runtime_problems:
        raise RuntimeError("Codex Council runtime contract failed: " + "; ".join(runtime_problems))
    alter_config = load_alter_config(config_root)
    if pre_session_estimate is None:
        pre_session_estimate = estimate_pre_session(
            topic,
            mode=mode,
            token_budget=token_budget,
            frontend_review=frontend_review,
            session_type=session_type,
            skill_review=skill_review,
            alter_config=alter_config,
            panel=panel,
            router=router,
            max_agents=max_agents,
            early_exit=early_exit,
        )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    storage_root = session_storage_root(session_root)
    session_dir = storage_root / f"{timestamp}-{slugify(topic)}"
    members_dir = session_dir / "members"
    reviews_dir = session_dir / "reviews"
    evidence_runners_dir = session_dir / "evidence-runners"
    members_dir.mkdir(parents=True, exist_ok=False)
    reviews_dir.mkdir(parents=True, exist_ok=False)
    if frontend_review:
        evidence_runners_dir.mkdir(parents=True, exist_ok=False)

    role_files = active_role_files(skill_review, session_type, active_panel, topic)
    reviewers = session_reviewers(mode, frontend_review, skill_review, session_type, active_panel)
    evidence_runners = session_evidence_runners(frontend_review)
    alter_metadata = active_alter_session_metadata(alter_config, list(role_files.values()), reviewers)
    activation_tags: list[str] = []
    if frontend_review:
        activation_tags.append("frontend-ui-ux")
    if skill_review:
        activation_tags.append("skill-review")
    if session_type == "forge":
        activation_tags.append("forge")
    if decision_runtime == "shadow":
        activation_tags.append("decision-runtime-shadow")
    dispatch_line = render_dispatch_announcement(mode, token_budget, frontend_review, skill_review, session_type, active_panel)
    compiled_context = compile_context_capsule(topic)

    metadata = {
        "topic": topic,
        "mode": mode,
        "session_type": session_type,
        "skill_review": skill_review,
        "status": "scaffolded",
        "created_at": timestamp,
        "workspace_root": str(root),
        "storage_root": str(storage_root),
        "storage_scope": "plugin-local" if session_root is None else "custom",
        "roles": list(role_files.values()),
        "reviewers": reviewers,
        "evidence_runners": evidence_runners,
        "activation_tags": activation_tags,
        "token_budget": token_budget,
        "panel": active_panel,
        "requested_panel": panel,
        "router": router,
        "route_decision": route_decision,
        "delta_from": str(delta_from) if delta_from else None,
        "decision_runtime": {
            "mode": decision_runtime,
            "authoritative": False,
            "status": "not_initialized" if decision_runtime == "shadow" else "disabled",
        },
        "context_files": [],
        "redaction_notes": "",
        "verification_commands": [],
        "final_state": "pending",
        "pre_session_estimate": pre_session_estimate or {},
        "pre_execution_estimate": (pre_session_estimate or {}).get("pre_execution_estimate", {}),
        "confirmation": confirmation or {},
        "dispatch_line": dispatch_line,
        "synthesis_contract": "separate_synthesis_pass",
        "alter_overrides": alter_metadata,
        "intelligence_layer": {
            "schema_version": INTELLIGENCE_SCHEMA_VERSION,
            "context_capsule": CONTEXT_CAPSULE_FILE,
            "decision_ledger": DECISION_LEDGER_FILE,
            "run_manifest": RUN_MANIFEST_FILE,
            "findings": FINDINGS_FILE,
            "telemetry": TELEMETRY_FILE,
        },
    }
    (session_dir / "session.json").write_text(
        json.dumps(metadata, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (session_dir / "brief.md").write_text(
        (
            f"# {'Codex Forge' if session_type == 'forge' else 'Codex Council'} Brief\n\nTopic: {topic}\nMode: {mode}\nType: {session_type}\n"
            f"Token Profile: {token_budget}\n\n## Context\n\n## Constraints\n\n## Success Criteria\n"
        ),
        encoding="utf-8",
    )
    if pre_session_estimate:
        write_preflight_estimate(session_dir, pre_session_estimate)
    write_intelligence_artifacts(session_dir, root, metadata, pre_session_estimate or {}, route_decision, compiled_context)
    write_prompt_scaffold(session_dir, topic, mode, token_budget, frontend_review, session_type, skill_review, alter_config, active_panel)
    write_synthesis_input_manifest(session_dir, role_files, reviewers, evidence_runners, session_type)
    for filename, role in role_files.items():
        sections = REQUIRED_FORGE_MEMBER_SECTIONS.copy() if session_type == "forge" else REQUIRED_MEMBER_SECTIONS.copy()
        if session_type != "forge" and not skill_review and filename == "06-seymour-performance-engineer.md":
            sections.extend(PERFORMANCE_MEMBER_EXTRA_SECTIONS)
        (members_dir / filename).write_text(
            f"# {role}\n\n" + "\n\n".join(sections) + "\n",
            encoding="utf-8",
        )
    if not skill_review and session_type != "forge":
        (reviews_dir / "performance-impact-reviewer.md").write_text(
            "# Performance Impact Reviewer\n\n## Ranking\n\n## Performance Blockers\n\n## Missing Measurements\n\n## Verification Required\n",
            encoding="utf-8",
        )
        (reviews_dir / "coverage-integrator.md").write_text(
            "# Coverage Integrator\n\n## Covered Perspectives\n\n## Missing Perspectives\n\n## Cross-Council Conflicts\n\n## Chairman Inputs\n",
            encoding="utf-8",
        )
    if frontend_review:
        for filename, reviewer in FRONTEND_REVIEWER_FILES.items():
            (reviews_dir / filename).write_text(
                f"# {reviewer}\n\n" + "\n\n".join(FRONTEND_REVIEWER_SECTIONS) + "\n",
                encoding="utf-8",
            )
        for filename, runner in EVIDENCE_RUNNER_FILES.items():
            (evidence_runners_dir / filename).write_text(
                f"# {runner}\n\n" + "\n\n".join(REQUIRED_EVIDENCE_RUNNER_SECTIONS) + "\n",
                encoding="utf-8",
            )
    (reviews_dir / "reviews.example.json").write_text(
        json.dumps(
            {
                "candidates": [
                    {"id": "A", "summary": "Neutral summary of Candidate A"},
                    {"id": "B", "summary": "Neutral summary of Candidate B"},
                ],
                "reviews": [
                    {
                        "reviewer": "rubric-reviewer",
                        "scores": {
                            "A": {
                                "accuracy": 8,
                                "completeness": 8,
                                "clarity": 8,
                                "conciseness": 7,
                                "relevance": 9,
                            },
                            "B": {
                                "accuracy": 7,
                                "completeness": 8,
                                "clarity": 7,
                                "conciseness": 9,
                                "relevance": 8,
                            },
                        },
                        "blocking_issues": {"A": [], "B": []},
                        "notes": {"A": "Example note", "B": "Example note"},
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    final_sections = REQUIRED_FORGE_FINAL_SECTIONS.copy() if session_type == "forge" else REQUIRED_FINAL_SECTIONS.copy()
    if frontend_review:
        final_sections.insert(final_sections.index("## Audit Notes"), "## Frontend Evidence")
    (session_dir / "final.md").write_text("# Chairman Synthesis\n\n" + "\n\n".join(final_sections) + "\n", encoding="utf-8")
    record_invocation_log(session_dir, storage_root, metadata)
    return session_dir


def _missing_sections(path: Path, required_sections: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [section for section in required_sections if section not in text]


def validate_session(session_dir: Path) -> dict[str, Any]:
    session_dir = Path(session_dir)
    problems: list[str] = []
    metadata: dict[str, Any] = {}

    metadata_path = session_dir / "session.json"
    if not metadata_path.exists():
        problems.append("missing session.json")
    else:
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"invalid session.json: {exc}")
        else:
            for key in ("topic", "mode", "status", "created_at", "workspace_root", "roles"):
                if key not in metadata:
                    problems.append(f"session.json missing {key}")
            if metadata.get("mode") not in MODES:
                problems.append("session.json mode is invalid")
            if metadata.get("session_type", "general") not in SESSION_TYPES:
                problems.append("session.json session_type is invalid")
            if metadata.get("token_budget") not in TOKEN_BUDGETS:
                problems.append("session.json token_budget is invalid")
            runtime_metadata = metadata.get("decision_runtime", {"mode": "off", "authoritative": False})
            if not isinstance(runtime_metadata, dict) or runtime_metadata.get("mode", "off") not in DECISION_RUNTIME_MODES:
                problems.append("session.json decision_runtime mode is invalid")
            elif runtime_metadata.get("authoritative") is not False:
                problems.append("session.json decision_runtime must remain non-authoritative")
            role_files = active_role_files(
                bool(metadata.get("skill_review")),
                metadata.get("session_type", "general"),
                metadata.get("panel", "full"),
                metadata.get("topic", ""),
            )
            if len(metadata.get("roles", [])) != len(role_files):
                problems.append(f"session.json roles must contain the {len(role_files)} expected council members")

    for filename in ("brief.md", "final.md"):
        path = session_dir / filename
        if not path.exists():
            problems.append(f"missing {filename}")
    for filename in ("chairman-synthesis.md", SYNTHESIS_INPUT_MANIFEST):
        path = session_dir / "prompts" / filename
        if not path.exists():
            problems.append(f"missing prompts/{filename}")
    final_path = session_dir / "final.md"
    if final_path.exists():
        required_final_sections = REQUIRED_FORGE_FINAL_SECTIONS if metadata.get("session_type") == "forge" else REQUIRED_FINAL_SECTIONS
        for section in _missing_sections(final_path, required_final_sections):
            problems.append(f"final.md missing {section}")

    members_dir = session_dir / "members"
    role_files = active_role_files(
        bool(metadata.get("skill_review")),
        metadata.get("session_type", "general"),
        metadata.get("panel", "full"),
        metadata.get("topic", ""),
    )
    if not members_dir.is_dir():
        problems.append("missing members directory")
    else:
        for filename in role_files:
            path = members_dir / filename
            if not path.exists():
                problems.append(f"missing member file: {filename}")
                continue
            required_member_sections = REQUIRED_FORGE_MEMBER_SECTIONS if metadata.get("session_type") == "forge" else REQUIRED_MEMBER_SECTIONS
            for section in _missing_sections(path, required_member_sections):
                problems.append(f"{filename} missing {section}")
            if metadata.get("session_type") != "forge" and not metadata.get("skill_review") and filename == "06-seymour-performance-engineer.md":
                for section in _missing_sections(path, PERFORMANCE_MEMBER_EXTRA_SECTIONS):
                    problems.append(f"{filename} missing {section}")

    reviews_path = session_dir / "reviews" / "reviews.example.json"
    if not reviews_path.exists():
        problems.append("missing reviews/reviews.example.json")
    else:
        try:
            aggregate(json.loads(reviews_path.read_text(encoding="utf-8")))
        except Exception as exc:
            problems.append(f"invalid reviews example: {exc}")

    if not metadata.get("skill_review") and metadata.get("session_type") != "forge":
        expected_reviewers = metadata.get("reviewers") or BASE_REVIEWERS
        for reviewer in expected_reviewers:
            filename = reviewer_filename(reviewer)
            path = session_dir / "reviews" / filename
            if not path.exists():
                problems.append(f"missing reviewer file: {filename}")

    intelligence_files = (CONTEXT_CAPSULE_FILE, DECISION_LEDGER_FILE, RUN_MANIFEST_FILE, FINDINGS_FILE, TELEMETRY_FILE)
    has_intelligence_layer = isinstance(metadata.get("intelligence_layer"), dict) or any(
        (session_dir / filename).exists() for filename in intelligence_files
    )
    if has_intelligence_layer:
        for filename in intelligence_files:
            path = session_dir / filename
            if not path.exists():
                problems.append(f"missing intelligence artifact: {filename}")
            elif filename.endswith(".json"):
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    problems.append(f"invalid intelligence artifact {filename}: {exc}")

    if "frontend-ui-ux" in metadata.get("activation_tags", []):
        if final_path.exists() and "## Frontend Evidence" not in final_path.read_text(encoding="utf-8"):
            problems.append("final.md missing ## Frontend Evidence")
        reviews_dir = session_dir / "reviews"
        for filename in FRONTEND_REVIEWER_FILES:
            path = reviews_dir / filename
            if not path.exists():
                problems.append(f"missing frontend reviewer file: {filename}")
                continue
            for section in _missing_sections(path, FRONTEND_REVIEWER_SECTIONS):
                problems.append(f"{filename} missing {section}")

        evidence_runners_dir = session_dir / "evidence-runners"
        if not evidence_runners_dir.is_dir():
            problems.append("missing evidence-runners directory")
        else:
            for filename in EVIDENCE_RUNNER_FILES:
                path = evidence_runners_dir / filename
                if not path.exists():
                    problems.append(f"missing evidence runner file: {filename}")
                    continue
                for section in _missing_sections(path, REQUIRED_EVIDENCE_RUNNER_SECTIONS):
                    problems.append(f"{filename} missing {section}")

    return {"ok": not problems, "problems": problems}


def validate_runtime_contract(root: Path) -> list[str]:
    skill_dir = root / "skills" / "codex-council"
    hyper_dir = root / "skills" / "codex-hyper"
    references_dir = skill_dir / "references"
    required_paths = [
        root / ".codex-plugin" / "plugin.json",
        skill_dir / "SKILL.md",
        skill_dir / "agents" / "openai.yaml",
        root / "scripts" / "codex_council.py",
        root / "scripts" / "council_cells.py",
    ]
    required_paths.extend(references_dir / filename for filename in REQUIRED_REFERENCES)
    required_paths.extend(hyper_dir / filename for filename in REQUIRED_HYPER_FILES)
    return [f"missing runtime file: {path.relative_to(root).as_posix()}" for path in required_paths if not path.exists()]


def validate_plugin(root: Path, strict: bool = False) -> dict[str, Any]:
    manifest_path = root / ".codex-plugin" / "plugin.json"
    skill_path = root / "skills" / "codex-council" / "SKILL.md"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    if not skill_path.exists():
        raise FileNotFoundError(f"Missing skill: {skill_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if manifest.get("name") != "codex-council":
        problems.append("manifest name must be codex-council")
    if manifest.get("skills") != "./skills/":
        problems.append("manifest skills path must be ./skills/")
    interface = manifest.get("interface", {})
    for asset_key in ("composerIcon", "logo"):
        asset_path = interface.get(asset_key)
        if asset_path and not (root / asset_path.removeprefix("./")).exists():
            problems.append(f"missing interface asset: {asset_path}")
    scaffold_marker = "[TO" + "DO:"
    if scaffold_marker in json.dumps(manifest):
        problems.append("manifest still contains scaffold placeholder markers")
    if strict:
        problems.extend(validate_runtime_contract(root))
        skill_dir = root / "skills" / "codex-council"
        references_dir = skill_dir / "references"
        for filename in REQUIRED_REFERENCES:
            if not (references_dir / filename).exists():
                problems.append(f"missing reference: {filename}")
        if not (skill_dir / "agents" / "openai.yaml").exists():
            problems.append("missing agents/openai.yaml")
        if not (root / "PROVENANCE.md").exists():
            problems.append("missing PROVENANCE.md")
        if not (root / "README.md").exists():
            problems.append("missing README.md")
        if any(root.rglob(".DS_Store")):
            problems.append("package contains .DS_Store files")
        if not (root / "tests" / "test_codex_council.py").exists():
            problems.append("missing test suite")
        if not (root / "tests" / "test_council_cells.py").exists():
            problems.append("missing Decision Runtime test suite")
        for docs_path in (root / "docs" / "runtime.html", root / "docs" / "it" / "runtime.html"):
            if not docs_path.exists():
                problems.append(f"missing Decision Runtime docs: {docs_path.relative_to(root).as_posix()}")
        skill_text = skill_path.read_text(encoding="utf-8")
        if len(skill_text.split()) > 700:
            problems.append("SKILL.md exceeds compact word budget")
        for forbidden in ("```json", "## UX Verdict\nPass, Needs Refinement, or Blocked."):
            if forbidden in skill_text:
                problems.append("SKILL.md contains detailed schema that belongs in references")
        for required in ("competency-packs.md", "decision-runtime.md", "workflow-recipes.md", "governance-preflight.md"):
            if required not in skill_text:
                problems.append(f"SKILL.md does not reference {required}")
        token_budget_path = references_dir / "token-budget.md"
        if token_budget_path.exists():
            token_text = token_budget_path.read_text(encoding="utf-8")
            for phrase in (
                "Never remove blocker reporting",
                "Never remove dissent",
                "Never skip verification",
                "Never skip anonymization",
                "Never let missing candidate scores pass",
                "Never treat Bob as a voting council member",
                "Never claim UI behavior is verified",
                "Never let conciseness outrank accuracy",
            ):
                if phrase not in token_text:
                    problems.append(f"token-budget.md missing guardrail: {phrase}")
    return {"ok": not problems, "problems": problems}


def fetch_latest_release(repository: str, timeout: float = 8.0) -> Optional[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "codex-council-update-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"GitHub release check failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub release check failed: {exc.reason}") from exc


def check_update(
    plugin_root: Path,
    repository: Optional[str] = None,
    timeout: float = 8.0,
    latest_version: Optional[str] = None,
    fetch_latest: Any = fetch_latest_release,
) -> dict[str, Any]:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    local_version = normalize_semver(str(manifest["version"]))
    repository_name = repository_slug(repository or manifest.get("repository"))

    release_url = f"https://github.com/{repository_name}/releases"
    if latest_version:
        latest = {
            "tag_name": latest_version,
            "html_url": f"{release_url}/tag/{latest_version}",
        }
    else:
        latest = fetch_latest(repository_name, timeout)
        if latest is None:
            return {
                "status": "no_releases",
                "update_available": False,
                "repository": repository_name,
                "local_version": local_version,
                "latest_version": None,
                "release_url": release_url,
                "update_command": f"npx codex-marketplace add {repository_name} --plugin --global -y",
                "project_update_command": f"npx codex-marketplace add {repository_name} --plugin --project -y",
            }

    latest_tag = str(latest.get("tag_name") or latest.get("name") or "")
    latest_normalized = normalize_semver(latest_tag)
    comparison = compare_semver(local_version, latest_normalized)
    if comparison < 0:
        status = "update_available"
    elif comparison > 0:
        status = "local_newer"
    else:
        status = "up_to_date"

    return {
        "status": status,
        "update_available": status == "update_available",
        "repository": repository_name,
        "local_version": local_version,
        "latest_version": latest_normalized,
        "latest_tag": latest_tag,
        "release_url": latest.get("html_url") or release_url,
        "update_command": f"npx codex-marketplace add {repository_name} --plugin --global -y",
        "project_update_command": f"npx codex-marketplace add {repository_name} --plugin --project -y",
    }


def render_update_status(result: dict[str, Any]) -> str:
    status = result["status"]
    if status == "update_available":
        return (
            f"Update available: {result['local_version']} -> {result['latest_version']}\n"
            f"Release: {result['release_url']}\n"
            f"Global update: {result['update_command']}\n"
            f"Project update: {result['project_update_command']}"
        )
    if status == "up_to_date":
        return f"Codex Council is up to date ({result['local_version']})."
    if status == "local_newer":
        return (
            f"Local version {result['local_version']} is newer than the latest release "
            f"{result['latest_version']}."
        )
    return (
        f"No GitHub releases found for {result['repository']}.\n"
        "Create a GitHub Release to notify watchers about new versions."
    )


def render_decision_runtime_result(result: dict[str, Any]) -> str:
    """Render a compact operator summary without overstating shadow evidence."""

    lines = [f"Decision Runtime: {result.get('status', 'complete')}"]
    if result.get("generation"):
        lines.append(f"Generation: {result['generation']}")
    if isinstance(result.get("comparison"), dict):
        recommendation = result["comparison"].get("recommendation")
        if recommendation:
            lines.append(f"Comparison: {recommendation}")
    if isinstance(result.get("impact_plan"), dict):
        plan = result["impact_plan"]
        lines.append(f"Impact plan: {plan.get('coverage', 'full')} (advisory only)")
    if result.get("fallback_reason"):
        lines.append(f"Fallback: {result['fallback_reason']} -> legacy artifacts")
    elif result.get("fallback"):
        lines.append(f"Fallback: {result['fallback']}")
    if result.get("message"):
        lines.append(f"Reason: {result['message']}")
    if "case_count" in result:
        lines.append(f"Replay cases: {result['case_count']} x {result.get('repetitions', 1)}")
    if isinstance(result.get("points"), list):
        lines.append(f"Fault points: {len(result['points'])}")
    lines.append("Authoritative: no")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex Council session and scoring utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a council session folder")
    init_parser.add_argument("--topic", required=True)
    init_parser.add_argument("--root", default=".", help="Workspace/project root being analyzed; not used for session storage")
    init_parser.add_argument("--session-root", help="Override local session storage root")
    init_parser.add_argument("--mode", choices=sorted(MODES), default="standard")
    init_parser.add_argument("--type", dest="session_type", choices=sorted(SESSION_TYPES), default="general")
    init_parser.add_argument("--skill-review", action="store_true", help="Use compact 3-lens skill/tool review panel")
    init_parser.add_argument("--panel", choices=sorted(PANELS), default="full", help="Optional advisory panel shape")
    init_parser.add_argument("--router", choices=("off", "auto"), default="off", help="Optional advisory budget router")
    init_parser.add_argument("--max-agents", type=int, help="Advisory maximum agent count; never silently overrides hard gates")
    init_parser.add_argument("--early-exit", action="store_true", help="Record that early exit is allowed when convergence is obvious")
    init_parser.add_argument("--delta-from", help="Optional prior session path for targeted/delta review metadata")
    init_parser.add_argument(
        "--decision-runtime",
        choices=sorted(DECISION_RUNTIME_MODES),
        default="off",
        help="Record opt-in to the post-run experimental shadow Decision Runtime",
    )
    init_parser.add_argument("--announce", action="store_true", help="Print one-line dispatch announcement before the session path")
    init_parser.add_argument("--config-root", help="Directory for local consumer profile/history")
    init_parser.add_argument("--context-tokens", type=int, default=0, help="Optional rough context token hint")
    init_parser.add_argument(
        "--frontend-review",
        action="store_true",
        help="Add Leonardo UX/UI review gate and Bob browser evidence runner",
    )
    init_parser.add_argument(
        "--token-budget",
        choices=sorted(TOKEN_BUDGETS),
        default="compact",
        help="Token profile for session scaffolding",
    )
    init_parser.add_argument(
        "--banner",
        action="store_true",
        help="Print a compact ASCII council table before the created session path",
    )
    init_parser.add_argument(
        "--confirm-estimate",
        action="store_true",
        help="Record that the pre-session estimate was shown and accepted",
    )
    init_parser.add_argument(
        "--confirm-expanded",
        action="store_true",
        help="Required explicit confirmation for expanded token profile",
    )

    estimate_parser = subparsers.add_parser("estimate", help="Estimate a council session before running it")
    estimate_parser.add_argument("--topic", required=True)
    estimate_parser.add_argument("--mode", choices=sorted(MODES), default="standard")
    estimate_parser.add_argument("--type", dest="session_type", choices=sorted(SESSION_TYPES), default="general")
    estimate_parser.add_argument("--skill-review", action="store_true")
    estimate_parser.add_argument("--panel", choices=sorted(PANELS), default="full")
    estimate_parser.add_argument("--router", choices=("off", "auto"), default="off")
    estimate_parser.add_argument("--max-agents", type=int)
    estimate_parser.add_argument("--early-exit", action="store_true")
    estimate_parser.add_argument("--token-budget", choices=sorted(TOKEN_BUDGETS), default="compact")
    estimate_parser.add_argument("--frontend-review", action="store_true")
    estimate_parser.add_argument("--context-tokens", type=int, default=0)
    estimate_parser.add_argument("--config-root", help="Directory for local consumer profile/history")
    estimate_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    profile_parser = subparsers.add_parser("profile", help="Manage local consumer profile and compact history")
    profile_parser.add_argument("--config-root", help="Directory for local consumer profile/history")
    profile_parser.add_argument("--show", action="store_true", help="Show profile/history summary")
    profile_parser.add_argument("--reset", action="store_true", help="Delete local consumer profile/history")
    profile_parser.add_argument("--plan", help="Declared Codex/ChatGPT plan, e.g. Plus, Pro, Business")
    profile_parser.add_argument("--model", help="Typical Codex model, e.g. GPT-5.3-Codex")
    profile_parser.add_argument("--reasoning", help="Typical reasoning effort, e.g. low, medium, high")
    profile_parser.add_argument("--five-hour-limit-tokens", type=int, help="Optional self-declared 5-hour token budget")
    profile_parser.add_argument("--weekly-limit-tokens", type=int, help="Optional self-declared weekly token budget")
    profile_parser.add_argument("--credit-budget", type=float, help="Optional self-declared credit budget")
    profile_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    score_parser = subparsers.add_parser("score", help="Aggregate reviewer JSON")
    score_parser.add_argument("--input", required=True)
    score_parser.add_argument("--output")
    score_parser.add_argument("--compact", action="store_true", help="Print minified JSON")

    forge_parser = subparsers.add_parser("forge-convergence", help="Assess Codex Forge convergence JSON")
    forge_parser.add_argument("--input", required=True)
    forge_parser.add_argument("--output")
    forge_parser.add_argument("--compact", action="store_true", help="Print minified JSON")

    validate_parser = subparsers.add_parser("validate", help="Validate the plugin layout")
    validate_parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    validate_parser.add_argument("--strict", action="store_true")

    validate_session_parser = subparsers.add_parser("validate-session", help="Validate a council session folder")
    validate_session_parser.add_argument("--session", required=True)

    stats_parser = subparsers.add_parser(
        "stats",
        help="Report estimated session artifact tokens and useful session statistics",
    )
    stats_parser.add_argument("--session", required=True)
    stats_parser.add_argument("--config-root", help="Directory for local consumer profile/history")
    stats_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    stats_parser.add_argument("--write", action="store_true", help="Write stats.json and stats.md into the session")
    stats_parser.add_argument("--raw-bundle", action="store_true", help="Write path-only raw-output bundle into the session")
    stats_parser.add_argument("--record-history", action="store_true", help="Record compact pre/post estimates locally")

    doctor_parser = subparsers.add_parser("doctor", help="Run read-only health checks for a council session")
    doctor_parser.add_argument("--session", required=True)
    doctor_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_parser = subparsers.add_parser("cells", help="Operate the experimental shadow Decision Runtime")
    cells_subparsers = cells_parser.add_subparsers(dest="cells_action", required=True)

    cells_project = cells_subparsers.add_parser("project", help="Project legacy evidence into Cells and frontier")
    cells_project.add_argument("--session", required=True)
    cells_project.add_argument("--compare", choices=("frontier",), default="frontier")
    cells_project.add_argument("--commit", action="store_true", help="Persist a transactional shadow generation")
    cells_project.add_argument("--plan", action="store_true", help="Include the advisory impact plan in output")
    cells_project.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_apply = cells_subparsers.add_parser("apply", help="Apply a strict standalone JSON Decision Patch")
    cells_apply.add_argument("--session", required=True)
    cells_apply.add_argument("--patch", required=True)
    cells_apply.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_plan = cells_subparsers.add_parser("plan", help="Plan advisory impact from a committed generation")
    cells_plan.add_argument("--session", required=True)
    cells_plan.add_argument("--changed", action="append", default=[], help="Changed Cell ID; repeat as needed")
    cells_plan.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_doctor = cells_subparsers.add_parser("doctor", help="Run a read-only sidecar integrity check")
    cells_doctor.add_argument("--session", required=True)
    cells_doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_recover = cells_subparsers.add_parser("recover", help="Recover one unambiguous committed chain")
    cells_recover.add_argument("--session", required=True)
    cells_recover.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_rollback = cells_subparsers.add_parser("rollback", help="Move shadow HEAD to a verified ancestor")
    cells_rollback.add_argument("--session", required=True)
    cells_rollback.add_argument("--to", required=True, dest="generation")
    cells_rollback.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_purge = cells_subparsers.add_parser("purge", help="Explicitly purge optional sidecar state")
    cells_purge.add_argument("--session", required=True)
    purge_scope = cells_purge.add_mutually_exclusive_group(required=True)
    purge_scope.add_argument("--expired", action="store_true", help="Remove expired non-HEAD sidecar state")
    purge_scope.add_argument("--all", action="store_true", dest="all_runtime", help="Remove the complete sidecar")
    cells_purge.add_argument("--confirm", help="For --all, must equal the session directory name")
    cells_purge.add_argument("--retention-days", type=int, default=30)
    cells_purge.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_replay = cells_subparsers.add_parser("replay", help="Replay a sanitized local evaluation corpus")
    cells_replay.add_argument("--corpus", required=True)
    cells_replay.add_argument("--compare", choices=("frontier",), default="frontier")
    cells_replay.add_argument("--repetitions", type=int, default=10)
    cells_replay.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    cells_fault = cells_subparsers.add_parser("fault-test", help="Exercise transactional durability fault points")
    cells_fault.add_argument("--corpus", required=True)
    cells_fault.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    dashboard_parser = subparsers.add_parser("dashboard", help="Summarize local council session metrics")
    dashboard_parser.add_argument("--state-root", default=str(session_storage_root().parent))
    dashboard_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    compile_parser = subparsers.add_parser("compile-context", help="Compile and deduplicate a compact context capsule")
    compile_parser.add_argument("--topic", required=True)
    compile_parser.add_argument("--constraint", action="append", default=[])
    compile_parser.add_argument("--context", default="")
    compile_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    classify_parser = subparsers.add_parser("classify-invocation", help="Classify council trigger text as invoke/meta/unclear")
    classify_parser.add_argument("--text", required=True)
    classify_parser.add_argument("--explicit", action="store_true")
    classify_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    alters_parser = subparsers.add_parser("alters", help="Manage local council member role tuning")
    alters_parser.add_argument("action", choices=("list", "show", "preview", "configure", "reset"))
    alters_parser.add_argument("--config-root", help="Directory for local alter config")
    alters_parser.add_argument("--role", choices=sorted(ALTER_ROLE_CATALOG), help="Alter role id")
    alters_parser.add_argument("--all", action="store_true", help="Apply reset to all alters")
    alters_parser.add_argument("--domain-focus")
    alters_parser.add_argument("--strictness")
    alters_parser.add_argument("--tone")
    alters_parser.add_argument("--risk-posture")
    alters_parser.add_argument("--evidence-preference")
    alters_parser.add_argument("--extra-check", action="append", default=[])
    alters_parser.add_argument("--instruction", help="Short bounded advisory instruction")
    alters_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    update_parser = subparsers.add_parser("check-update", help="Check GitHub Releases for a newer plugin version")
    update_parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    update_parser.add_argument("--repository", help="Override GitHub repository as owner/repo")
    update_parser.add_argument("--timeout", type=float, default=8.0)
    update_parser.add_argument("--latest-version", help="Bypass network and compare against this version")
    update_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    args = parser.parse_args()

    if args.command == "init":
        config_root = Path(args.config_root).expanduser() if args.config_root else None
        session_type, frontend_review, skill_review = normalize_session_options(
            args.session_type,
            args.frontend_review,
            args.skill_review,
        )
        consumer_data = load_consumer_data(config_root)
        alter_config = load_alter_config(config_root)
        estimate = estimate_pre_session(
            args.topic,
            mode=args.mode,
            token_budget=args.token_budget,
            frontend_review=frontend_review,
            session_type=session_type,
            skill_review=skill_review,
            context_tokens=max(args.context_tokens, 0),
            consumer_data=consumer_data,
            alter_config=alter_config,
            panel=args.panel,
            router=args.router,
            max_agents=args.max_agents,
            early_exit=args.early_exit,
        )
        if args.token_budget == "expanded" and not args.confirm_expanded:
            print(render_pre_session_estimate(estimate))
            raise SystemExit(
                "Expanded mode requires explicit confirmation. Re-run with --confirm-expanded only after accepting the warning."
            )
        confirmation = {
            "estimate_accepted": bool(args.confirm_estimate or args.confirm_expanded),
            "expanded_confirmed": bool(args.confirm_expanded),
            "confirmed_at": utc_now() if (args.confirm_estimate or args.confirm_expanded) else None,
        }
        path = init_session(
            args.topic,
            Path(args.root).expanduser().resolve(),
            mode=args.mode,
            frontend_review=frontend_review,
            token_budget=args.token_budget,
            session_type=session_type,
            skill_review=skill_review,
            pre_session_estimate=estimate,
            confirmation=confirmation,
            session_root=Path(args.session_root).expanduser().resolve() if args.session_root else None,
            config_root=config_root,
            panel=args.panel,
            router=args.router,
            max_agents=args.max_agents,
            early_exit=args.early_exit,
            delta_from=Path(args.delta_from).expanduser().resolve() if args.delta_from else None,
            decision_runtime=args.decision_runtime,
        )
        if args.banner:
            active_panel = estimate.get("panel", args.panel)
            print(render_council_banner(args.mode, args.token_budget, frontend_review, skill_review, session_type, active_panel))
        if args.announce:
            active_panel = estimate.get("panel", args.panel)
            print(render_dispatch_announcement(args.mode, args.token_budget, frontend_review, skill_review, session_type, active_panel))
        print(path)
        return

    if args.command == "estimate":
        config_root = Path(args.config_root).expanduser() if args.config_root else None
        session_type, frontend_review, skill_review = normalize_session_options(
            args.session_type,
            args.frontend_review,
            args.skill_review,
        )
        result = estimate_pre_session(
            args.topic,
            mode=args.mode,
            token_budget=args.token_budget,
            frontend_review=frontend_review,
            session_type=session_type,
            skill_review=skill_review,
            context_tokens=max(args.context_tokens, 0),
            consumer_data=load_consumer_data(config_root),
            alter_config=load_alter_config(config_root),
            panel=args.panel,
            router=args.router,
            max_agents=args.max_agents,
            early_exit=args.early_exit,
        )
        print(json.dumps(result, indent=2) if args.json else render_pre_session_estimate(result))
        return

    if args.command == "profile":
        config_root = Path(args.config_root).expanduser() if args.config_root else None
        path = consumer_file(config_root)
        if args.reset:
            if path.exists():
                path.unlink()
            result = {"ok": True, "path": str(path), "reset": True}
            print(json.dumps(result, indent=2) if args.json else f"Deleted local Codex Council consumer profile: {path}")
            return
        has_updates = any(
            value is not None
            for value in (
                args.plan,
                args.model,
                args.reasoning,
                args.five_hour_limit_tokens,
                args.weekly_limit_tokens,
                args.credit_budget,
            )
        )
        if has_updates:
            data = update_consumer_profile(
                config_root,
                plan=args.plan,
                model=args.model,
                reasoning=args.reasoning,
                five_hour_limit_tokens=args.five_hour_limit_tokens,
                weekly_limit_tokens=args.weekly_limit_tokens,
                credit_budget=args.credit_budget,
                storage_consent=True,
            )
            rendered = data
        else:
            rendered = load_consumer_data(config_root)
        if args.json:
            print(json.dumps(rendered, indent=2))
        elif not path.exists() and not has_updates:
            print(
                "No local Codex Council consumer profile found.\n"
                "Ask the user for: plan, typical Codex model, reasoning effort, and optional self-declared 5-hour/weekly budgets.\n"
                f"Save with: python3 scripts/codex_council.py profile --plan <plan> --model <model> --reasoning <effort>"
            )
        else:
            profile = rendered["profile"]
            summary = rendered["history"]["summary"]
            print(
                "Codex Council consumer profile\n"
                f"- Path: {path}\n"
                f"- Plan: {profile.get('plan')}\n"
                f"- Typical model: {profile.get('typical_model')}\n"
                f"- Reasoning: {profile.get('reasoning')}\n"
                f"- Sessions learned: {summary.get('sessions', 0)}\n"
                f"- Avg post/pre ratio: {summary.get('avg_post_to_pre_ratio', 1.0)}"
            )
        return

    if args.command == "score":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = aggregate(payload)
        rendered = (
            json.dumps(result, separators=(",", ":"))
            if args.compact
            else json.dumps(result, indent=2)
        )
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return

    if args.command == "forge-convergence":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = assess_forge_convergence(payload)
        rendered = (
            json.dumps(result, separators=(",", ":"))
            if args.compact
            else json.dumps(result, indent=2)
        )
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return

    if args.command == "validate":
        result = validate_plugin(Path(args.plugin_root).expanduser().resolve(), strict=args.strict)
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "validate-session":
        result = validate_session(Path(args.session).expanduser().resolve())
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "stats":
        session_dir = Path(args.session).expanduser().resolve()
        result = collect_session_stats(session_dir)
        if args.raw_bundle:
            bundle_path = write_raw_output_bundle(session_dir)
            result["raw_output_bundle"] = {
                "path": bundle_path.relative_to(session_dir).as_posix(),
                "content_policy": "path-only",
            }
        if args.write:
            write_session_stats(session_dir, result)
        if args.record_history:
            config_root = Path(args.config_root).expanduser() if args.config_root else None
            history_path = record_session_history(session_dir, result, config_root)
            result["history_recorded"] = bool(history_path)
            result["history_path"] = str(history_path) if history_path else None
        print(json.dumps(result, indent=2) if args.json else render_session_stats(result))
        return

    if args.command == "doctor":
        result = doctor_session(Path(args.session).expanduser().resolve())
        print(json.dumps(result, indent=2) if args.json else ("OK" if result["ok"] else json.dumps(result, indent=2)))
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "cells":
        try:
            if args.cells_action == "project":
                projected = council_cells.project_session(
                    Path(args.session).expanduser().resolve(),
                    compare=args.compare,
                    commit=args.commit,
                )
                if args.commit:
                    result = dict(projected)
                    result["committed"] = True
                else:
                    result = {
                        "ok": True,
                        "status": "preview",
                        "committed": False,
                        "session_id": projected["session_id"],
                        "comparison": projected["comparison"],
                        "metrics": projected["metrics"],
                        "cell_count": len(projected["cells"]),
                        "edge_count": len(projected["edges"]),
                        "frontier_event_count": len(projected["frontier"]),
                        "authoritative": False,
                    }
                    if args.plan:
                        result["impact_plan"] = projected["impact_plan"]
                if not args.plan:
                    result.pop("impact_plan", None)
            elif args.cells_action == "apply":
                result = council_cells.apply_decision_patch(
                    Path(args.session).expanduser().resolve(),
                    Path(args.patch).expanduser(),
                )
            elif args.cells_action == "plan":
                projection = council_cells.load_head_projection(Path(args.session).expanduser().resolve())
                result = council_cells.plan_impact(
                    projection,
                    changed_cells=args.changed or None,
                    session_metadata=projection.get("session_metadata"),
                )
                result["ok"] = True
                result["status"] = "advisory"
            elif args.cells_action == "doctor":
                result = council_cells.doctor_runtime(Path(args.session).expanduser().resolve())
            elif args.cells_action == "recover":
                result = council_cells.recover_runtime(Path(args.session).expanduser().resolve())
            elif args.cells_action == "rollback":
                result = council_cells.rollback_runtime(
                    Path(args.session).expanduser().resolve(),
                    args.generation,
                )
            elif args.cells_action == "purge":
                result = council_cells.purge_runtime(
                    Path(args.session).expanduser().resolve(),
                    expired=args.expired,
                    all_runtime=args.all_runtime,
                    confirm=args.confirm,
                    retention_days=args.retention_days,
                )
            elif args.cells_action == "replay":
                result = council_cells.replay_corpus(
                    Path(args.corpus).expanduser().resolve(),
                    repetitions=args.repetitions,
                    compare=args.compare,
                )
            else:
                result = council_cells.fault_test_corpus(Path(args.corpus).expanduser().resolve())
        except (council_cells.DecisionRuntimeError, OSError, TypeError, ValueError) as exc:
            failure = {
                "ok": False,
                "status": "failed_closed",
                "error": type(exc).__name__,
                "message": str(exc),
                "fallback": "legacy",
                "authoritative": False,
            }
            print(json.dumps(failure, indent=2) if args.json else render_decision_runtime_result(failure))
            raise SystemExit(1) from exc
        print(json.dumps(result, indent=2) if args.json else render_decision_runtime_result(result))
        if not result.get("ok", True):
            raise SystemExit(1)
        return

    if args.command == "dashboard":
        result = collect_state_dashboard(Path(args.state_root).expanduser().resolve())
        print(json.dumps(result, indent=2) if args.json else render_state_dashboard(result))
        return

    if args.command == "compile-context":
        result = compile_context_capsule(args.topic, constraints=args.constraint, context=args.context)
        print(json.dumps(result, indent=2) if args.json else result["compiled_text"])
        return

    if args.command == "classify-invocation":
        classification = classify_council_invocation(args.text, explicit=args.explicit)
        payload = {"classification": classification, "text_present": bool(args.text.strip())}
        print(json.dumps(payload, indent=2) if args.json else classification)
        return

    if args.command == "alters":
        config_root = Path(args.config_root).expanduser() if args.config_root else None
        if args.action in {"list", "show"}:
            data = load_alter_config(config_root)
            if args.json:
                if args.role:
                    role_id = normalize_alter_role(args.role)
                    print(json.dumps(data.get("alters", {}).get(role_id, {}), indent=2))
                else:
                    print(json.dumps(data, indent=2))
            else:
                print(render_alter_config(data, args.role, config_root))
            return
        if args.action == "preview":
            if args.role is None:
                raise SystemExit("preview requires --role")
            data = load_alter_config(config_root)
            role_id = normalize_alter_role(args.role)
            if any(
                value
                for value in (
                    args.domain_focus,
                    args.strictness,
                    args.tone,
                    args.risk_posture,
                    args.evidence_preference,
                    args.extra_check,
                    args.instruction,
                )
            ):
                entry = build_alter_entry(
                    role_id,
                    domain_focus=args.domain_focus,
                    strictness=args.strictness,
                    tone=args.tone,
                    risk_posture=args.risk_posture,
                    evidence_preference=args.evidence_preference,
                    extra_checks=args.extra_check,
                    instruction=args.instruction,
                )
            else:
                entry = data.get("alters", {}).get(role_id)
                if not entry:
                    raise SystemExit(f"No saved tuning for {role_id}; pass tuning fields to preview a new one.")
            print(json.dumps(entry, indent=2) if args.json else render_alter_preview(entry))
            return
        if args.action == "configure":
            if args.role is None:
                raise SystemExit("configure requires --role")
            result = configure_alter(
                args.role,
                config_root=config_root,
                domain_focus=args.domain_focus,
                strictness=args.strictness,
                tone=args.tone,
                risk_posture=args.risk_posture,
                evidence_preference=args.evidence_preference,
                extra_checks=args.extra_check,
                instruction=args.instruction,
            )
            print(json.dumps(result, indent=2) if args.json else render_alter_preview(result["entry"]) + f"\n\nSaved: {result['path']}")
            return
        if args.action == "reset":
            if not args.all and args.role is None:
                raise SystemExit("reset requires --role or --all")
            result = reset_alter(None if args.all else args.role, config_root)
            print(json.dumps(result, indent=2) if args.json else f"Reset alters: {', '.join(result['removed']) or 'none'}\nSaved: {result['path']}")
            return

    if args.command == "check-update":
        result = check_update(
            Path(args.plugin_root).expanduser().resolve(),
            repository=args.repository,
            timeout=args.timeout,
            latest_version=args.latest_version,
        )
        print(json.dumps(result, indent=2) if args.json else render_update_status(result))


if __name__ == "__main__":
    main()
