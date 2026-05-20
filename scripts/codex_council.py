#!/usr/bin/env python3
"""Codex Council utility commands.

This script is intentionally stdlib-only. It creates traceable council session
folders and aggregates reviewer score JSON with normalized score averaging.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


WEIGHTS = {
    "accuracy": 0.35,
    "completeness": 0.20,
    "clarity": 0.20,
    "conciseness": 0.15,
    "relevance": 0.10,
}

ROLE_FILES = {
    "01-principal-architect.md": "Principal Architect",
    "02-reliability-engineer.md": "Reliability Engineer",
    "03-security-governance-reviewer.md": "Security and Governance Reviewer",
    "04-product-operator-advocate.md": "Product and Operator Advocate",
    "05-contrarian-red-team.md": "Contrarian Red Team",
}

MODES = {"fast", "standard", "deep"}

REQUIRED_MEMBER_SECTIONS = [
    "## Recommendation",
    "## Rationale",
    "## Blocking Issues",
    "## Non-Blocking Improvements",
    "## Verification Required",
    "## Confidence",
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

REQUIRED_REFERENCES = [
    "competency-packs.md",
    "governance-preflight.md",
    "method-source-notes.md",
    "output-contract.md",
    "roles-and-rubrics.md",
    "token-budget.md",
    "workflow-recipes.md",
]

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
        per_reviewer_raw: dict[str, float] = {}
        for candidate_id in candidate_ids:
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


def init_session(topic: str, root: Path, mode: str = "standard") -> Path:
    if mode not in MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(MODES))}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_dir = root / ".codex-council" / f"{timestamp}-{slugify(topic)}"
    members_dir = session_dir / "members"
    reviews_dir = session_dir / "reviews"
    members_dir.mkdir(parents=True, exist_ok=False)
    reviews_dir.mkdir(parents=True, exist_ok=False)

    (session_dir / "session.json").write_text(
        json.dumps(
            {
                "topic": topic,
                "mode": mode,
                "status": "scaffolded",
                "created_at": timestamp,
                "workspace_root": str(root),
                "roles": list(ROLE_FILES.values()),
                "reviewers": ["rubric-reviewer", "bias-auditor", "implementation-gatekeeper"]
                if mode == "deep"
                else [],
                "context_files": [],
                "redaction_notes": "",
                "verification_commands": [],
                "final_state": "pending",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (session_dir / "brief.md").write_text(
        f"# Codex Council Brief\n\nTopic: {topic}\nMode: {mode}\n\n## Context\n\n## Constraints\n\n## Success Criteria\n",
        encoding="utf-8",
    )
    for filename, role in ROLE_FILES.items():
        (members_dir / filename).write_text(
            f"# {role}\n\n" + "\n\n".join(REQUIRED_MEMBER_SECTIONS) + "\n",
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
    (session_dir / "final.md").write_text(
        "# Chairman Synthesis\n\n## Recommendation\n\n## Council Result\n\n## Blocking Issues\n\n## Refinements\n\n## Implementation Shape\n\n## Verification\n\n## Audit Notes\n",
        encoding="utf-8",
    )
    return session_dir


def _missing_sections(path: Path, required_sections: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [section for section in required_sections if section not in text]


def validate_session(session_dir: Path) -> dict[str, Any]:
    session_dir = Path(session_dir)
    problems: list[str] = []

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

    for filename in ("brief.md", "final.md"):
        path = session_dir / filename
        if not path.exists():
            problems.append(f"missing {filename}")
    final_path = session_dir / "final.md"
    if final_path.exists():
        for section in _missing_sections(final_path, REQUIRED_FINAL_SECTIONS):
            problems.append(f"final.md missing {section}")

    members_dir = session_dir / "members"
    if not members_dir.is_dir():
        problems.append("missing members directory")
    else:
        for filename in ROLE_FILES:
            path = members_dir / filename
            if not path.exists():
                problems.append(f"missing member file: {filename}")
                continue
            for section in _missing_sections(path, REQUIRED_MEMBER_SECTIONS):
                problems.append(f"{filename} missing {section}")

    reviews_path = session_dir / "reviews" / "reviews.example.json"
    if not reviews_path.exists():
        problems.append("missing reviews/reviews.example.json")
    else:
        try:
            aggregate(json.loads(reviews_path.read_text(encoding="utf-8")))
        except Exception as exc:
            problems.append(f"invalid reviews example: {exc}")

    return {"ok": not problems, "problems": problems}


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
        skill_text = skill_path.read_text(encoding="utf-8")
        for required in ("competency-packs.md", "workflow-recipes.md", "governance-preflight.md"):
            if required not in skill_text:
                problems.append(f"SKILL.md does not reference {required}")
        token_budget_path = references_dir / "token-budget.md"
        if token_budget_path.exists():
            token_text = token_budget_path.read_text(encoding="utf-8")
            for phrase in ("Never remove blocker reporting", "Never remove dissent", "Never skip verification"):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex Council session and scoring utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a council session folder")
    init_parser.add_argument("--topic", required=True)
    init_parser.add_argument("--root", default=".")
    init_parser.add_argument("--mode", choices=sorted(MODES), default="standard")

    score_parser = subparsers.add_parser("score", help="Aggregate reviewer JSON")
    score_parser.add_argument("--input", required=True)
    score_parser.add_argument("--output")
    score_parser.add_argument("--compact", action="store_true", help="Print minified JSON")

    validate_parser = subparsers.add_parser("validate", help="Validate the plugin layout")
    validate_parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    validate_parser.add_argument("--strict", action="store_true")

    validate_session_parser = subparsers.add_parser("validate-session", help="Validate a council session folder")
    validate_session_parser.add_argument("--session", required=True)

    update_parser = subparsers.add_parser("check-update", help="Check GitHub Releases for a newer plugin version")
    update_parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    update_parser.add_argument("--repository", help="Override GitHub repository as owner/repo")
    update_parser.add_argument("--timeout", type=float, default=8.0)
    update_parser.add_argument("--latest-version", help="Bypass network and compare against this version")
    update_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    args = parser.parse_args()

    if args.command == "init":
        path = init_session(args.topic, Path(args.root).expanduser().resolve(), mode=args.mode)
        print(path)
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
