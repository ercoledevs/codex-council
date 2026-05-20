import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import codex_council as cc
from scripts.codex_council import aggregate, init_session, validate_plugin, weighted_score


class CodexCouncilScoringTests(unittest.TestCase):
    def test_weighted_score_applies_accuracy_ceiling(self):
        score = weighted_score(
            {
                "accuracy": 4,
                "completeness": 10,
                "clarity": 10,
                "conciseness": 10,
                "relevance": 10,
            }
        )
        self.assertEqual(score, 4.0)

    def test_aggregate_selects_unblocked_highest_normalized_candidate(self):
        payload = {
            "candidates": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "reviews": [
                {
                    "reviewer": "r1",
                    "scores": {
                        "A": {"accuracy": 9, "completeness": 9, "clarity": 9, "conciseness": 8, "relevance": 9},
                        "B": {"accuracy": 7, "completeness": 7, "clarity": 8, "conciseness": 8, "relevance": 8},
                        "C": {"accuracy": 6, "completeness": 10, "clarity": 10, "conciseness": 10, "relevance": 10},
                    },
                    "blocking_issues": {"A": [], "B": [], "C": []},
                },
                {
                    "reviewer": "r2",
                    "scores": {
                        "A": {"accuracy": 8, "completeness": 9, "clarity": 8, "conciseness": 8, "relevance": 9},
                        "B": {"accuracy": 7, "completeness": 8, "clarity": 8, "conciseness": 8, "relevance": 7},
                        "C": {"accuracy": 5, "completeness": 10, "clarity": 10, "conciseness": 10, "relevance": 10},
                    },
                    "blocking_issues": {"A": [], "B": [], "C": []},
                },
            ],
        }
        result = aggregate(payload)
        self.assertEqual(result["winner"], "A")
        self.assertIn(result["confidence"], {"high", "medium"})
        self.assertEqual(result["ranking"][0]["candidate_id"], "A")

    def test_blocking_issue_demotes_candidate_without_blocking_winner(self):
        payload = {
            "candidates": [{"id": "A"}, {"id": "B"}],
            "reviews": [
                {
                    "reviewer": "gatekeeper",
                    "scores": {
                        "A": {"accuracy": 9, "completeness": 9, "clarity": 9, "conciseness": 9, "relevance": 9},
                        "B": {"accuracy": 8, "completeness": 8, "clarity": 8, "conciseness": 8, "relevance": 8},
                    },
                    "blocking_issues": {"A": ["Unsafe migration"], "B": []},
                }
            ],
        }
        result = aggregate(payload)
        self.assertEqual(result["winner"], "B")
        self.assertNotEqual(result["confidence"], "blocked")
        self.assertTrue(result["ranking"][1]["blocked"])

    def test_all_blocked_candidates_produce_blocked_confidence(self):
        payload = {
            "candidates": [{"id": "A"}, {"id": "B"}],
            "reviews": [
                {
                    "reviewer": "gatekeeper",
                    "scores": {
                        "A": {"accuracy": 9, "completeness": 9, "clarity": 9, "conciseness": 9, "relevance": 9},
                        "B": {"accuracy": 8, "completeness": 8, "clarity": 8, "conciseness": 8, "relevance": 8},
                    },
                    "blocking_issues": {"A": ["Unsafe migration"], "B": ["No rollback path"]},
                }
            ],
        }
        result = aggregate(payload)
        self.assertEqual(result["confidence"], "blocked")
        self.assertTrue(result["ranking"][0]["blocked"])


class CodexCouncilSessionTests(unittest.TestCase):
    def test_init_session_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Architecture Review", Path(tmp))
            self.assertTrue((session / "brief.md").exists())
            member = session / "members" / "01-principal-architect.md"
            self.assertTrue(member.exists())
            self.assertIn("## Non-Blocking Improvements", member.read_text(encoding="utf-8"))
            self.assertTrue((session / "reviews" / "reviews.example.json").exists())
            json.loads((session / "reviews" / "reviews.example.json").read_text(encoding="utf-8"))

    def test_validate_plugin_accepts_current_layout(self):
        plugin_root = Path(__file__).resolve().parents[1]
        result = validate_plugin(plugin_root)
        self.assertTrue(result["ok"], result["problems"])

    def test_strict_validation_accepts_clean_plugin_contract(self):
        plugin_root = Path(__file__).resolve().parents[1]
        result = validate_plugin(plugin_root, strict=True)
        self.assertTrue(result["ok"], result["problems"])
        self.assertTrue((plugin_root / "README.md").exists())

    def test_init_session_writes_mode_and_audit_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Governance Review", Path(tmp), mode="deep")
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["mode"], "deep")
            self.assertEqual(metadata["topic"], "Governance Review")
            self.assertEqual(metadata["status"], "scaffolded")
            self.assertEqual(len(metadata["roles"]), 5)
            self.assertIn("redaction_notes", metadata)

    def test_validate_session_accepts_scaffolded_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Session Validation", Path(tmp), mode="standard")
            result = cc.validate_session(session)
            self.assertTrue(result["ok"], result["problems"])

    def test_score_command_supports_compact_json(self):
        plugin_root = Path(__file__).resolve().parents[1]
        script = plugin_root / "scripts" / "codex_council.py"
        payload = {
            "candidates": [{"id": "A"}, {"id": "B"}],
            "reviews": [
                {
                    "reviewer": "r1",
                    "scores": {
                        "A": {"accuracy": 8, "completeness": 8, "clarity": 8, "conciseness": 8, "relevance": 8},
                        "B": {"accuracy": 7, "completeness": 7, "clarity": 7, "conciseness": 7, "relevance": 7},
                    },
                    "blocking_issues": {"A": [], "B": []},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "reviews.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), "score", "--input", str(input_path), "--compact"],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertNotIn("\n  ", result.stdout)
        self.assertEqual(json.loads(result.stdout)["winner"], "A")

    def test_check_update_reports_available_release_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_dir = root / ".codex-plugin"
            manifest_dir.mkdir()
            (manifest_dir / "plugin.json").write_text(
                json.dumps(
                    {
                        "name": "codex-council",
                        "version": "0.1.0",
                        "repository": "https://github.com/ercoledevs/codex-council",
                    }
                ),
                encoding="utf-8",
            )

            result = cc.check_update(
                root,
                fetch_latest=lambda repo, timeout: {
                    "tag_name": "v0.2.0",
                    "html_url": "https://github.com/ercoledevs/codex-council/releases/tag/v0.2.0",
                },
            )

        self.assertTrue(result["update_available"])
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["local_version"], "0.1.0")
        self.assertEqual(result["latest_version"], "0.2.0")

    def test_check_update_command_outputs_json(self):
        plugin_root = Path(__file__).resolve().parents[1]
        script = plugin_root / "scripts" / "codex_council.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_dir = root / ".codex-plugin"
            manifest_dir.mkdir()
            (manifest_dir / "plugin.json").write_text(
                json.dumps(
                    {
                        "name": "codex-council",
                        "version": "0.1.0",
                        "repository": "https://github.com/ercoledevs/codex-council",
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "check-update",
                    "--plugin-root",
                    str(root),
                    "--latest-version",
                    "v0.1.1",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "update_available")
        self.assertEqual(payload["latest_version"], "0.1.1")


if __name__ == "__main__":
    unittest.main()
