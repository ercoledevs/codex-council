import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import codex_council as cc
from scripts.codex_council import WEIGHTS, aggregate, init_session, validate_plugin, weighted_score


class CodexCouncilScoringTests(unittest.TestCase):
    def test_weight_invariants_keep_conciseness_below_correctness(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)
        self.assertGreater(WEIGHTS["accuracy"], WEIGHTS["conciseness"])
        self.assertGreater(WEIGHTS["completeness"], WEIGHTS["conciseness"])
        self.assertGreater(WEIGHTS["clarity"], WEIGHTS["conciseness"])

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

    def test_aggregate_rejects_missing_candidate_scores(self):
        payload = {
            "candidates": [{"id": "A"}, {"id": "B"}],
            "reviews": [
                {
                    "reviewer": "compact-reviewer",
                    "scores": {
                        "A": {"accuracy": 8, "completeness": 8, "clarity": 8, "conciseness": 8, "relevance": 8}
                    },
                    "blocking_issues": {"A": []},
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "missing scores"):
            aggregate(payload)

    def test_aggregate_supports_six_candidate_council(self):
        candidates = [{"id": candidate_id} for candidate_id in "ABCDEF"]
        scores = {
            candidate_id: {
                "accuracy": 9 if candidate_id == "F" else 7,
                "completeness": 8,
                "clarity": 8,
                "conciseness": 7,
                "relevance": 8,
            }
            for candidate_id in "ABCDEF"
        }
        payload = {
            "candidates": candidates,
            "reviews": [
                {"reviewer": "rubric-reviewer", "scores": scores, "blocking_issues": {candidate_id: [] for candidate_id in "ABCDEF"}},
                {
                    "reviewer": "performance-impact-reviewer",
                    "scores": {
                        candidate_id: {
                            **scores[candidate_id],
                            "accuracy": 10 if candidate_id == "F" else scores[candidate_id]["accuracy"],
                        }
                        for candidate_id in "ABCDEF"
                    },
                    "blocking_issues": {candidate_id: [] for candidate_id in "ABCDEF"},
                },
            ],
        }
        result = aggregate(payload)
        self.assertEqual(result["winner"], "F")
        self.assertEqual([item["candidate_id"] for item in result["ranking"]], ["F", "A", "B", "C", "D", "E"])
        self.assertTrue(all(item["review_count"] == 2 for item in result["ranking"]))


class CodexCouncilSessionTests(unittest.TestCase):
    def test_init_session_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Architecture Review", Path(tmp))
            self.assertTrue((session / "brief.md").exists())
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["token_budget"], "compact")
            self.assertEqual(len(metadata["roles"]), 6)
            self.assertIn("Seymour Cray - Performance Engineer", metadata["roles"])
            self.assertIn("performance-impact-reviewer", metadata["reviewers"])
            self.assertIn("coverage-integrator", metadata["reviewers"])
            self.assertIn("Token Profile: compact", (session / "brief.md").read_text(encoding="utf-8"))
            member = session / "members" / "01-ada-principal-architect.md"
            self.assertTrue(member.exists())
            self.assertIn("## Non-Blocking Improvements", member.read_text(encoding="utf-8"))
            performance_member = session / "members" / "06-seymour-performance-engineer.md"
            self.assertTrue(performance_member.exists())
            self.assertIn("## Performance Impact", performance_member.read_text(encoding="utf-8"))
            self.assertTrue((session / "reviews" / "performance-impact-reviewer.md").exists())
            self.assertTrue((session / "reviews" / "coverage-integrator.md").exists())
            self.assertFalse((session / "reviews" / "leonardo-ux-ui-critic.md").exists())
            self.assertFalse((session / "evidence-runners" / "bob-browser-customer-tester.md").exists())
            self.assertTrue((session / "reviews" / "reviews.example.json").exists())
            json.loads((session / "reviews" / "reviews.example.json").read_text(encoding="utf-8"))

    def test_init_session_frontend_review_adds_leonardo_and_bob(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Frontend Modal Review", Path(tmp), frontend_review=True)
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(len(metadata["roles"]), 6)
            self.assertIn("Leonardo da Vinci - Brutally Honest UX/UI Critic", metadata["reviewers"])
            self.assertIn("Bob - Browser Customer Tester", metadata["evidence_runners"])
            self.assertIn("frontend-ui-ux", metadata["activation_tags"])

            ux_reviewer = session / "reviews" / "leonardo-ux-ui-critic.md"
            self.assertTrue(ux_reviewer.exists())
            self.assertIn("## Counterintuitive Risk", ux_reviewer.read_text(encoding="utf-8"))

            bob_runner = session / "evidence-runners" / "bob-browser-customer-tester.md"
            self.assertTrue(bob_runner.exists())
            bob_text = bob_runner.read_text(encoding="utf-8")
            self.assertIn("## Scenarios From Council", bob_text)
            self.assertIn("## Browser Evidence", bob_text)
            self.assertIn("## Frontend Evidence", (session / "final.md").read_text(encoding="utf-8"))
            self.assertTrue(cc.validate_session(session)["ok"])

    def test_init_session_rejects_invalid_token_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "token_budget"):
                init_session("Bad Budget", Path(tmp), token_budget="verbose")

    def test_validate_plugin_accepts_current_layout(self):
        plugin_root = Path(__file__).resolve().parents[1]
        result = validate_plugin(plugin_root)
        self.assertTrue(result["ok"], result["problems"])

    def test_strict_validation_accepts_clean_plugin_contract(self):
        plugin_root = Path(__file__).resolve().parents[1]
        result = validate_plugin(plugin_root, strict=True)
        self.assertTrue(result["ok"], result["problems"])
        self.assertTrue((plugin_root / "README.md").exists())

    def test_skill_body_stays_compact(self):
        plugin_root = Path(__file__).resolve().parents[1]
        skill_text = (plugin_root / "skills" / "codex-council" / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill_text.split()), 700)
        self.assertNotIn("```json", skill_text)
        self.assertNotIn("## UX Verdict\nPass, Needs Refinement, or Blocked.", skill_text)

    def test_skill_requires_chat_visible_banner_and_stats(self):
        plugin_root = Path(__file__).resolve().parents[1]
        skill_text = (plugin_root / "skills" / "codex-council" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("paste the ASCII banner directly in chat", skill_text)
        self.assertIn("Do not rely on hidden shell stdout", skill_text)
        self.assertIn("persist compact artifacts", skill_text)
        self.assertIn("relay them in chat", skill_text)

    def test_docs_do_not_retain_five_member_contract(self):
        plugin_root = Path(__file__).resolve().parents[1]
        docs = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                plugin_root / "README.md",
                plugin_root / "skills" / "codex-council" / "SKILL.md",
                plugin_root / "skills" / "codex-council" / "references" / "execution-protocol.md",
                plugin_root / "skills" / "codex-council" / "references" / "frontend-ux-browser.md",
            ]
        )
        self.assertNotIn("five council", docs.lower())
        self.assertNotIn("five-member", docs.lower())
        self.assertNotIn("Candidate A-E", docs)

    def test_init_session_writes_mode_and_audit_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Governance Review", Path(tmp), mode="deep")
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["mode"], "deep")
            self.assertEqual(metadata["topic"], "Governance Review")
            self.assertEqual(metadata["status"], "scaffolded")
            self.assertEqual(len(metadata["roles"]), 6)
            self.assertIn("redaction_notes", metadata)

    def test_deep_session_adds_expanded_reviewer_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Deep Performance Review", Path(tmp), mode="deep")
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(len(metadata["reviewers"]), 5)
            self.assertIn("bias-auditor", metadata["reviewers"])
            self.assertIn("implementation-gatekeeper", metadata["reviewers"])
            self.assertIn("performance-impact-reviewer", metadata["reviewers"])
            self.assertIn("coverage-integrator", metadata["reviewers"])

    def test_validate_session_accepts_scaffolded_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Session Validation", Path(tmp), mode="standard")
            result = cc.validate_session(session)
            self.assertTrue(result["ok"], result["problems"])

    def test_init_command_banner_is_opt_in_and_ascii(self):
        plugin_root = Path(__file__).resolve().parents[1]
        script = plugin_root / "scripts" / "codex_council.py"
        with tempfile.TemporaryDirectory() as tmp:
            no_banner = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "init",
                    "--topic",
                    "No Banner",
                    "--root",
                    tmp,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertNotIn("CODEX COUNCIL", no_banner.stdout)
            self.assertTrue(Path(no_banner.stdout.strip()).exists())

            with_banner = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "init",
                    "--topic",
                    "With Banner",
                    "--root",
                    tmp,
                    "--banner",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("CODEX COUNCIL", with_banner.stdout)
            self.assertTrue(all(ord(character) < 128 for character in with_banner.stdout))
            self.assertTrue(Path(with_banner.stdout.strip().splitlines()[-1]).exists())

    def test_session_stats_are_estimated_and_privacy_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Stats Review", Path(tmp), frontend_review=True)
            stats = cc.collect_session_stats(session)
            rendered = cc.render_session_stats(stats)
            serialized = json.dumps(stats)

        self.assertEqual(stats["estimated_artifact_usage"]["label"], "estimated artifact tokens")
        self.assertFalse(stats["estimated_artifact_usage"]["is_actual_codex_usage"])
        self.assertGreater(stats["estimated_artifact_usage"]["estimated_tokens"], 0)
        self.assertIn("not actual Codex usage", rendered)
        self.assertNotIn(tmp, serialized)
        self.assertTrue(stats["validation"]["ok"], stats["validation"]["problems"])

    def test_stats_command_writes_reports_and_json(self):
        plugin_root = Path(__file__).resolve().parents[1]
        script = plugin_root / "scripts" / "codex_council.py"
        with tempfile.TemporaryDirectory() as tmp:
            session = init_session("Stats Command", Path(tmp))
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "stats",
                    "--session",
                    str(session),
                    "--write",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertTrue((session / "stats.json").exists())
            self.assertTrue((session / "stats.md").exists())

        self.assertEqual(payload["estimated_artifact_usage"]["label"], "estimated artifact tokens")
        self.assertFalse(payload["estimated_artifact_usage"]["is_actual_codex_usage"])

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
