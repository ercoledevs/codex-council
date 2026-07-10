from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import council_cells as cells


FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class CouncilCellsTests(unittest.TestCase):
    def make_session(
        self,
        root: Path,
        name: str = "session",
        *,
        final: str | None = None,
        risk_flags: list[str] | None = None,
        mode: str = "standard",
        session_type: str = "general",
    ) -> Path:
        session = root / name
        session.mkdir(mode=0o700)
        metadata = {
            "topic": "Decision Runtime Test",
            "mode": mode,
            "session_type": session_type,
            "activation_tags": [],
            "route_decision": {"risk_flags": risk_flags or []},
        }
        (session / "session.json").write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
        (session / "final.md").write_text(
            final
            or (
                "# Chairman Synthesis\n\n"
                "## Recommendation\n\n- Adopt the reversible architecture.\n\n"
                "## Blocking Issues\n\n- Recovery must remain atomic.\n\n"
                "## Persistent Dissent\n\n- A simpler append-only log may be sufficient.\n\n"
                "## Verification\n\n- Run deterministic crash-recovery tests.\n"
            ),
            encoding="utf-8",
        )
        return session

    def legacy_hashes(self, session: Path) -> dict[str, str]:
        import hashlib

        return {
            path.relative_to(session).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(session.rglob("*"))
            if path.is_file() and cells.RUNTIME_DIRNAME not in path.parts
        }

    def base_patch(self, session: Path, generation: str, operations: list[dict]) -> dict:
        return {
            "schema_version": 1,
            "session_id": session.name,
            "base_generation": generation,
            "source_ref": "operator",
            "operations": operations,
        }

    def make_corpus(self, root: Path) -> Path:
        corpus = root / "corpus"
        corpus.mkdir()
        case = {
            "schema_version": 1,
            "name": "standard-recovery",
            "session": {
                "topic": "Recovery",
                "mode": "standard",
                "session_type": "general",
                "risk_flags": [],
                "frontend_review": False,
            },
            "artifacts": {
                "final.md": (
                    "# Chairman\n\n"
                    "## Recommendation\n\n- Use an atomic local runtime.\n\n"
                    "## Blocking Issues\n\n- Recovery must be atomic.\n\n"
                    "## Persistent Dissent\n\n- A simple log remains viable.\n\n"
                    "## Verification\n\n- Run crash tests.\n"
                )
            },
            "expected": {"blockers": 1, "dissent": 1, "verification": 1, "forced_full": True},
        }
        (corpus / "case-standard.json").write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")
        (corpus / "manifest.json").write_text(
            json.dumps({"schema_version": 1, "cases": ["case-standard.json"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        return corpus

    def test_public_api_is_complete_and_runtime_root_is_read_only(self):
        expected = {
            "runtime_root",
            "project_session",
            "commit_projection",
            "load_head_projection",
            "apply_decision_patch",
            "plan_impact",
            "doctor_runtime",
            "recover_runtime",
            "rollback_runtime",
            "purge_runtime",
            "replay_corpus",
            "fault_test_corpus",
        }
        self.assertTrue(expected.issubset(set(cells.__all__)))
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            path = cells.runtime_root(session)
            self.assertEqual(path, session.resolve() / cells.RUNTIME_DIRNAME)
            self.assertFalse(path.exists())

    def test_project_commit_load_and_doctor_preserve_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            before = self.legacy_hashes(session)
            result = cells.project_session(session, now=FIXED_TIME)
            loaded = cells.load_head_projection(session)
            health = cells.doctor_runtime(session)
            after = self.legacy_hashes(session)

            self.assertTrue(result["ok"])
            self.assertFalse(result["authoritative"])
            self.assertEqual(before, after)
            self.assertEqual(len(loaded["cells"]), 4)
            self.assertTrue(loaded["comparison"]["semantic_equivalence"])
            self.assertEqual(loaded["comparison"]["recall"], {"blocker": 1.0, "dissent": 1.0, "verification": 1.0})
            self.assertEqual(loaded["impact_plan"]["coverage"], "full")
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["read_only"])
            self.assertFalse(health["authoritative"])

    def test_runtime_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            runtime = cells.runtime_root(session)
            for current, directories, files in os.walk(runtime):
                self.assertEqual(stat.S_IMODE(os.stat(current, follow_symlinks=False).st_mode), 0o700)
                for name in files:
                    self.assertEqual(stat.S_IMODE(os.stat(Path(current) / name, follow_symlinks=False).st_mode), 0o600)

    def test_same_session_ids_are_stable_and_cross_session_ids_are_salted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.make_session(root, "first")
            second = self.make_session(root, "second")
            first_result = cells.project_session(first, now=FIXED_TIME)
            first_ids = [cell["cid"] for cell in cells.load_head_projection(first)["cells"]]
            repeated = cells.project_session(first, now=FIXED_TIME)
            second_result = cells.project_session(second, now=FIXED_TIME)
            second_ids = [cell["cid"] for cell in cells.load_head_projection(second)["cells"]]

            self.assertFalse(first_result["idempotent"])
            self.assertTrue(repeated["idempotent"])
            self.assertFalse(second_result["idempotent"])
            self.assertNotEqual(first_ids, second_ids)

    def test_commit_projection_api_accepts_uncommitted_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            projection = cells.project_session(session, commit=False, now=FIXED_TIME)
            result = cells.commit_projection(session, projection, now=FIXED_TIME)
            self.assertTrue(result["ok"])
            self.assertEqual(cells.load_head_projection(session)["generation"], result["generation"])

    def test_stale_public_commit_cannot_overwrite_a_newer_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            stale = cells.project_session(session, commit=False, now=FIXED_TIME)
            cells.commit_projection(session, stale, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "newer",
                        "cell": {
                            "kind": "counterfactual",
                            "state": "open",
                            "text": "What if the rollback path is unavailable",
                            "domains": ["reliability"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            applied = cells.apply_decision_patch(session, patch, now=FIXED_TIME)

            with self.assertRaisesRegex(cells.RuntimeConflictError, "parent generation"):
                cells.commit_projection(session, stale, now=FIXED_TIME)

            current = cells.load_head_projection(session)
            self.assertEqual(current["generation"], applied["generation"])
            self.assertEqual(len(current["patches"]), 1)

    def test_reproject_is_idempotent_after_patch_and_never_discards_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "preserved",
                        "cell": {
                            "kind": "claim",
                            "state": "open",
                            "text": "Preserve the typed patch across repeated projection",
                            "domains": ["testing"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            applied = cells.apply_decision_patch(session, patch, now=FIXED_TIME)
            repeated = cells.project_session(session, now=FIXED_TIME)

            self.assertTrue(repeated["idempotent"])
            self.assertEqual(repeated["generation"], applied["generation"])
            self.assertEqual(repeated["patches_preserved"], 1)
            self.assertEqual(len(cells.load_head_projection(session)["patches"]), 1)

    def test_patch_history_is_an_ordered_single_generation_append(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            for local_id, text in (("firstPatch", "First ordered patch"), ("secondPatch", "Second ordered patch")):
                current = cells.load_head_projection(session)
                patch = self.base_patch(
                    session,
                    current["generation"],
                    [
                        {
                            "op": "add_cell",
                            "local_id": local_id,
                            "cell": {"kind": "claim", "state": "open", "text": text},
                        }
                    ],
                )
                cells.apply_decision_patch(session, patch, now=FIXED_TIME)
            current = cells.load_head_projection(session)
            reordered = json.loads(json.dumps(current))
            reordered["patches"] = list(reversed(reordered["patches"]))

            with self.assertRaisesRegex(cells.RuntimeConflictError, "ordered single-generation append"):
                cells.commit_projection(
                    session,
                    reordered,
                    parent_generation=current["generation"],
                    now=FIXED_TIME,
                )

    def test_strict_json_rejects_duplicates_nan_and_unknown_patch_fields(self):
        with self.assertRaises(cells.SchemaValidationError):
            cells.strict_json_loads('{"a":1,"a":2}')
        with self.assertRaises(cells.SchemaValidationError):
            cells.strict_json_loads('{"a":NaN}')

        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            head = cells.load_head_projection(session)
            patch = self.base_patch(
                session,
                head["generation"],
                [{"op": "add_cell", "local_id": "newCell", "cell": {"kind": "claim", "state": "open", "text": "A bounded documentation change", "unexpected": True}}],
            )
            with self.assertRaisesRegex(cells.SchemaValidationError, "unknown fields"):
                cells.apply_decision_patch(session, patch)

            malformed = self.base_patch(
                session,
                head["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "badDomains",
                        "cell": {"kind": "claim", "state": "open", "text": "Bad domains", "domains": [{}]},
                    }
                ],
            )
            with self.assertRaisesRegex(cells.SchemaValidationError, "domains"):
                cells.apply_decision_patch(session, malformed)

            first, second = [cell["cid"] for cell in head["cells"][:2]]
            ambiguous_supersede = self.base_patch(
                session,
                head["generation"],
                [{"op": "add_edge", "relation": "supersedes", "from": first, "to": second}],
            )
            with self.assertRaisesRegex(cells.SchemaValidationError, "use supersede_cell"):
                cells.apply_decision_patch(session, ambiguous_supersede)

            spoofed = self.base_patch(
                session,
                head["generation"],
                [{"op": "add_cell", "local_id": "spoof", "cell": {"kind": "claim", "state": "open", "text": "Spoofed provenance"}}],
            )
            spoofed["source_ref"] = "chairman"
            with self.assertRaisesRegex(cells.RuntimeSecurityError, "reserved legacy provenance"):
                cells.apply_decision_patch(session, spoofed)

    def test_commit_rejects_frontier_patch_and_metrics_tampering(self):
        mutations = {
            "frontier": lambda projection: projection["frontier"][0].__setitem__("text", "Mismatched text"),
            "patches": lambda projection: projection["patches"].append({"unexpected": "sk-not-persisted-123456789"}),
            "metrics": lambda projection: projection["metrics"].__setitem__("secret", "sk-not-persisted-123456789"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                session = self.make_session(Path(temporary))
                projection = cells.project_session(session, commit=False, now=FIXED_TIME)
                mutate(projection)
                with self.assertRaises(cells.DecisionRuntimeError):
                    cells.commit_projection(session, projection, now=FIXED_TIME)
                self.assertFalse((cells.runtime_root(session) / cells.HEAD_FILE).exists())

    def test_privacy_scan_blocks_sidecar_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(
                Path(temporary),
                final="# Chairman\n\n## Blocking Issues\n\n- Contact alice@example.com before shipping.\n",
            )
            before = self.legacy_hashes(session)
            with self.assertRaises(cells.PrivacyViolation):
                cells.project_session(session, now=FIXED_TIME)
            self.assertEqual(before, self.legacy_hashes(session))
            self.assertFalse((cells.runtime_root(session) / cells.HEAD_FILE).exists())

    def test_patch_add_edge_supersede_idempotence_and_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            first = cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            target = base["cells"][0]["cid"]
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "newClaim",
                        "cell": {
                            "kind": "claim",
                            "state": "open",
                            "text": "Documentation output remains byte stable",
                            "confidence": "unknown",
                            "sensitivity": "internal",
                            "domains": ["documentation"],
                            "risk_flags": [],
                        },
                    },
                    {"op": "add_edge", "relation": "depends_on", "from": "$newClaim", "to": target},
                ],
            )
            applied = cells.apply_decision_patch(session, patch, now=FIXED_TIME)
            second = cells.load_head_projection(session)
            patch["patch_id"] = applied["patch_id"]
            retried = cells.apply_decision_patch(session, patch, now=FIXED_TIME)
            replacement_patch = self.base_patch(
                session,
                second["generation"],
                [
                    {
                        "op": "supersede_cell",
                        "target": next(cell["cid"] for cell in second["cells"] if cell["text"] == "Documentation output remains byte stable"),
                        "local_id": "replacement",
                        "cell": {
                            "kind": "claim",
                            "state": "accepted",
                            "text": "Documentation output is verified byte stable",
                            "domains": ["documentation", "testing"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            third_result = cells.apply_decision_patch(session, replacement_patch, now=FIXED_TIME)
            third = cells.load_head_projection(session)
            rollback = cells.rollback_runtime(session, second["generation"])

            self.assertNotEqual(first["generation"], applied["generation"])
            self.assertTrue(retried["idempotent"])
            self.assertTrue(any(edge["relation"] == "supersedes" for edge in third["edges"]))
            self.assertTrue(third["comparison"]["semantic_equivalence"])
            self.assertEqual(third_result["generation"], third["generation"])
            self.assertEqual(rollback["generation"], second["generation"])
            self.assertEqual(cells.load_head_projection(session)["head_reason"], "rollback")
            self.assertFalse(rollback["evidence_deleted"])

    def test_dependency_cycle_is_rejected_without_head_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            first_target, second_target = [cell["cid"] for cell in base["cells"][:2]]
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {"op": "add_edge", "relation": "depends_on", "from": first_target, "to": second_target},
                    {"op": "add_edge", "relation": "depends_on", "from": second_target, "to": first_target},
                ],
            )
            with self.assertRaisesRegex(cells.SchemaValidationError, "cycle"):
                cells.apply_decision_patch(session, patch)
            self.assertEqual(cells.load_head_projection(session)["generation"], base["generation"])

    def test_impact_closure_includes_dependents_of_a_changed_dependency(self):
        projection = {
            "cells": [
                {
                    "cid": "dependent",
                    "kind": "claim",
                    "state": "open",
                    "domains": ["architecture"],
                    "risk_flags": [],
                },
                {
                    "cid": "dependency",
                    "kind": "evidence",
                    "state": "open",
                    "domains": ["documentation"],
                    "risk_flags": [],
                },
            ],
            "edges": [{"relation": "depends_on", "from": "dependent", "to": "dependency"}],
            "session_metadata": {"mode": "standard", "session_type": "general", "risk_flags": []},
        }

        plan = cells.plan_impact(projection, changed_cells=["dependency"])

        self.assertEqual(plan["coverage"], "targeted")
        self.assertEqual(plan["dependency_closure"], ["dependency", "dependent"])

    def test_legacy_source_drift_blocks_patch_until_reprojection(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "stale",
                        "cell": {
                            "kind": "claim",
                            "state": "open",
                            "text": "This patch is based on stale legacy evidence",
                            "domains": ["testing"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            with (session / "final.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## Refinements\n\n- Add a new bounded refinement.\n")

            with self.assertRaisesRegex(cells.RuntimeConflictError, "legacy artifacts changed"):
                cells.apply_decision_patch(session, patch)
            health = cells.doctor_runtime(session)
            self.assertEqual(health["status"], "quarantined")
            self.assertEqual(health["fallback_reason"], "legacy_source_changed")

            refreshed = cells.project_session(session, now=FIXED_TIME)
            self.assertNotEqual(refreshed["generation"], base["generation"])
            self.assertEqual(cells.doctor_runtime(session)["status"], "healthy")

    def test_stale_preview_cannot_be_committed_after_legacy_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            preview = cells.project_session(session, commit=False, now=FIXED_TIME)
            with (session / "final.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## Refinements\n\n- Evidence changed after preview.\n")

            with self.assertRaisesRegex(cells.RuntimeConflictError, "legacy artifacts changed"):
                cells.commit_projection(session, preview, now=FIXED_TIME)
            self.assertFalse((cells.runtime_root(session) / cells.HEAD_FILE).exists())

    def test_planner_targets_only_known_low_risk_and_fails_closed(self):
        low_risk_final = "# Chairman\n\n## Recommendation\n\n- Update documentation and adoption guidance.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            low = self.make_session(root, "low", final=low_risk_final)
            hard = self.make_session(root, "hard", final=low_risk_final, risk_flags=["privacy"])
            cells.project_session(low, now=FIXED_TIME)
            cells.project_session(hard, now=FIXED_TIME)
            low_plan = cells.load_head_projection(low)["impact_plan"]
            hard_plan = cells.load_head_projection(hard)["impact_plan"]

            self.assertEqual(low_plan["coverage"], "targeted")
            self.assertFalse(low_plan["forced_full"])
            self.assertLessEqual(len(low_plan["members"]), 4)
            self.assertEqual(hard_plan["coverage"], "full")
            self.assertIn("hard_risk:privacy", hard_plan["fallback_reasons"])
            self.assertTrue(hard_plan["advisory_only"])
            self.assertFalse(hard_plan["authoritative"])

    def test_missing_legacy_risk_metadata_and_underdeclared_patch_force_full(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = self.make_session(
                root,
                "legacy",
                final="# Chairman\n\n## Recommendation\n\n- Update the documentation.\n",
            )
            metadata = json.loads((legacy / "session.json").read_text(encoding="utf-8"))
            metadata.pop("route_decision")
            (legacy / "session.json").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            cells.project_session(legacy, now=FIXED_TIME)
            legacy_plan = cells.load_head_projection(legacy)["impact_plan"]

            patched = self.make_session(
                root,
                "patched",
                final="# Chairman\n\n## Recommendation\n\n- Update the documentation.\n",
            )
            cells.project_session(patched, now=FIXED_TIME)
            base = cells.load_head_projection(patched)
            patch = self.base_patch(
                patched,
                base["generation"],
                [
                    {
                        "op": "add_cell",
                        "local_id": "securityChange",
                        "cell": {
                            "kind": "claim",
                            "state": "open",
                            "text": "Change authentication permissions in production",
                            "domains": ["documentation"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            applied = cells.apply_decision_patch(patched, patch, now=FIXED_TIME)

            self.assertEqual(legacy_plan["coverage"], "full")
            self.assertIn("unknown_session_risk", legacy_plan["fallback_reasons"])
            self.assertEqual(applied["impact_plan"]["coverage"], "full")
            self.assertIn("hypatia", applied["impact_plan"]["members"])
            self.assertIn("hard_risk:security", applied["impact_plan"]["fallback_reasons"])

    def test_superseding_hard_risk_cell_stays_full_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(
                Path(temporary),
                final="# Chairman\n\n## Blocking Issues\n\n- Authentication permissions are unsafe.\n",
            )
            cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            target = base["cells"][0]["cid"]
            patch = self.base_patch(
                session,
                base["generation"],
                [
                    {
                        "op": "supersede_cell",
                        "target": target,
                        "local_id": "resolution",
                        "cell": {
                            "kind": "decision",
                            "state": "accepted",
                            "text": "Keep the documentation-only path",
                            "domains": ["documentation"],
                            "risk_flags": [],
                        },
                    }
                ],
            )
            applied = cells.apply_decision_patch(session, patch, now=FIXED_TIME)
            current = cells.load_head_projection(session)
            repeat = self.base_patch(
                session,
                current["generation"],
                [
                    {
                        "op": "supersede_cell",
                        "target": target,
                        "local_id": "again",
                        "cell": {"kind": "claim", "state": "open", "text": "Try again"},
                    }
                ],
            )

            self.assertEqual(applied["impact_plan"]["coverage"], "full")
            self.assertIn("hypatia", applied["impact_plan"]["members"])
            with self.assertRaisesRegex(cells.SchemaValidationError, "only once"):
                cells.apply_decision_patch(session, repeat)

    def test_fault_after_committed_is_recoverable_and_legacy_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            base = cells.load_head_projection(session)
            before = self.legacy_hashes(session)
            patch = self.base_patch(
                session,
                base["generation"],
                [{"op": "add_cell", "local_id": "probe", "cell": {"kind": "claim", "state": "open", "text": "Recovery probe", "domains": ["testing"], "risk_flags": []}}],
            )

            def fail(point: str) -> None:
                if point == "after_committed":
                    raise cells.InjectedFault(point)

            with self.assertRaises(cells.InjectedFault):
                cells.apply_decision_patch(session, patch, fault_hook=fail)
            health = cells.doctor_runtime(session)
            recovered = cells.recover_runtime(session)
            self.assertEqual(health["status"], "quarantined")
            self.assertTrue(health["recovery_available"])
            self.assertEqual(recovered["status"], "recovered")
            self.assertEqual(cells.doctor_runtime(session)["status"], "recovered")
            self.assertNotEqual(cells.load_head_projection(session)["generation"], base["generation"])
            self.assertEqual(before, self.legacy_hashes(session))

    def test_doctor_detects_permission_tampering_without_repairing(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            runtime_file = cells.runtime_root(session) / cells.RUNTIME_FILE
            runtime_file.chmod(0o644)
            health = cells.doctor_runtime(session)
            self.assertFalse(health["ok"])
            self.assertEqual(health["status"], "quarantined")
            self.assertEqual(health["fallback_reason"], "permission_unsafe")
            self.assertEqual(stat.S_IMODE(runtime_file.stat().st_mode), 0o644)

    def test_doctor_handles_missing_structure_and_reports_manual_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            healthy = cells.doctor_runtime(session, now=datetime(2026, 3, 1, tzinfo=timezone.utc))
            (cells.runtime_root(session) / cells.GENERATIONS_DIR).rename(cells.runtime_root(session) / "missing-generations")
            broken = cells.doctor_runtime(session)

            self.assertEqual(healthy["retention"]["policy"], "manual")
            self.assertFalse(healthy["retention"]["automatic_deletion"])
            self.assertEqual(healthy["retention"]["protected_generations"], 1)
            self.assertEqual(broken["status"], "quarantined")
            self.assertEqual(broken["fallback_reason"], "runtime_structure_invalid")

    def test_doctor_quarantines_wrong_typed_head_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            head_path = cells.runtime_root(session) / cells.HEAD_FILE
            head = json.loads(head_path.read_text(encoding="utf-8"))
            head["reason"] = []
            head_path.write_text(json.dumps(head) + "\n", encoding="utf-8")
            head_path.chmod(0o600)

            health = cells.doctor_runtime(session)

            self.assertEqual(health["status"], "quarantined")
            self.assertEqual(health["fallback_reason"], "head_corrupt")

    def test_full_purge_cannot_enter_while_another_writer_holds_the_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            cells.project_session(session, now=FIXED_TIME)
            script = Path(__file__).resolve().parents[1] / "scripts" / "codex_council.py"
            with cells._writer_lock(cells.runtime_root(session)):
                blocked = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "cells",
                        "purge",
                        "--session",
                        str(session),
                        "--all",
                        "--confirm",
                        session.name,
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertTrue(cells.runtime_root(session).exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_legacy_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session = self.make_session(root)
            external = root / "external.md"
            external.write_text("## Recommendation\n\n- External\n", encoding="utf-8")
            (session / "final.md").unlink()
            (session / "final.md").symlink_to(external)
            with self.assertRaises(cells.RuntimeSecurityError):
                cells.project_session(session)

    def test_purge_is_explicit_confirmed_and_never_deletes_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_session(Path(temporary))
            before = self.legacy_hashes(session)
            cells.project_session(session, now=FIXED_TIME)
            with self.assertRaises(cells.RuntimeSecurityError):
                cells.purge_runtime(session, all_runtime=True, confirm="wrong")
            result = cells.purge_runtime(session, all_runtime=True, confirm=session.name)
            self.assertEqual(result["status"], "ignored")
            self.assertFalse(cells.runtime_root(session).exists())
            self.assertEqual(before, self.legacy_hashes(session))

    def test_replay_and_fault_harnesses_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = self.make_corpus(Path(temporary))
            replay = cells.replay_corpus(corpus, repetitions=3)
            fault = cells.fault_test_corpus(corpus)
            self.assertTrue(replay["ok"], replay)
            self.assertEqual(replay["case_count"], 1)
            self.assertTrue(replay["cases"][0]["deterministic"])
            self.assertTrue(fault["ok"], fault)
            self.assertEqual(len(fault["points"]), len(cells.FAULT_POINTS))
            self.assertTrue(all(point["legacy_unchanged"] for point in fault["points"]))


if __name__ == "__main__":
    unittest.main()
