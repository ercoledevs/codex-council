"""Offline decision frontier shared by the interview, estimate and init commands."""

from __future__ import annotations

import json
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Any


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return " ".join(value.split())


def read_brief(path: Path) -> dict:
    """Validate the entire graph before presenting a question or writing a session."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("brief must be an object")
    outcome = _text(data.get("outcome"), "outcome")
    decisions = data.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("decisions must be a non-empty list")
    nodes = {}
    graph = {}
    for row in decisions:
        if not isinstance(row, dict):
            raise ValueError("each decision must be an object")
        key = _text(row.get("id"), "id")
        if key in nodes:
            raise ValueError(f"duplicate decision: {key}")
        deps = row.get("after", [])
        if not isinstance(deps, list):
            raise ValueError(f"{key}.after must be a list of decision IDs")
        graph[key] = [_text(dep, "prerequisite") for dep in deps]
        node = {"id": key, "question": _text(row.get("question"), "question")}
        for field in ("answer", "assumption", "recommendation"):
            if field in row:
                node[field] = _text(row[field], field)
        if "answer" in node and "assumption" in node:
            raise ValueError(f"{key}: choose answer or reversible assumption")
        nodes[key] = node
    unknown = {dep for deps in graph.values() for dep in deps} - nodes.keys()
    if unknown:
        raise ValueError(f"unknown prerequisites: {', '.join(sorted(unknown))}")
    try:
        order = tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise ValueError(f"cyclic prerequisites: {exc.args[1]}") from exc
    settled = set()
    frontier = []
    blocked = []
    brief = [f"Outcome: {outcome}"]
    for key in order:
        node = nodes[key]
        decision = node.get("answer") or node.get("assumption")
        if not settled.issuperset(graph[key]):
            if decision:
                raise ValueError(f"{key}: resolve prerequisites before recording this decision")
            blocked.append(key)
        elif decision:
            settled.add(key)
            kind = "Assumption" if "assumption" in node else "Decision"
            brief.append(f"{kind} [{key}] {node['question']} — {decision}")
        else:
            frontier.append(node)
    return {"status": "ask" if frontier else "ready", "frontier": frontier,
            "waiting": blocked, "brief": "\n".join(brief)}


def architecture_brief(outcome: str) -> dict:
    """A starting tree; the facilitator removes irrelevant branches before asking."""
    questions = [
        ("slice", "Who needs the first working slice, and what will they be able to do?", []),
        ("constraints", "Which existing contracts, resources or deadlines bind the design?", []),
        ("boundary", "Which component owns the state and the public contract?", ["slice", "constraints"]),
        ("failure", "Which failure must the caller be able to recover from?", ["boundary"]),
        ("acceptance", "What observable result would make this slice acceptable?", ["slice"]),
        ("recovery", "How will the operator detect failure and restore service?", ["failure"]),
    ]
    return {"outcome": _text(outcome, "outcome"), "decisions": [
        {"id": key, "question": question, "after": deps} for key, question, deps in questions
    ]}
