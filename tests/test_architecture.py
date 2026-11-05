import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import codex_council as cc, council_interview


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "brief.json"
        self.brief = council_interview.architecture_brief("Recover a job")

    def read(self):
        self.path.write_text(json.dumps(self.brief), encoding="utf-8")
        return council_interview.read_brief(self.path)

    def cli(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(Path(cc.__file__)), *map(str, args)],
            capture_output=True, text=True, check=check,
            env={**os.environ, "CODEX_COUNCIL_STATE_ROOT": str(self.root)},
        )

    def test_partial_answers_unlock_only_independent_decisions(self):
        self.assertEqual([x["id"] for x in self.read()["frontier"]], ["slice", "constraints"])
        self.brief["decisions"][0]["answer"] = "A worker resumes an interrupted job"
        self.assertEqual({x["id"] for x in self.read()["frontier"]}, {"constraints", "acceptance"})
        self.brief["decisions"][1]["assumption"] = "One process for the first slice"
        state = self.read()
        self.assertEqual({x["id"] for x in state["frontier"]}, {"boundary", "acceptance"})
        self.assertIn("Assumption [constraints]", state["brief"])

    def test_invalid_tree_or_unresolved_brief_cannot_create_a_session(self):
        for deps in (["missing"], ["slice"], 7):
            self.brief["decisions"][0]["after"] = deps
            with self.subTest(deps=deps), self.assertRaises(ValueError):
                self.read()
        self.brief["decisions"][0]["after"] = []
        self.read()
        result = self.cli("init", "--topic", "x", "--brief", self.path, "--session-root", self.root/"sessions", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root/"sessions").exists())

    def test_cli_estimate_init_and_manifest_share_real_rosters(self):
        cases = [("simple", "queue", [], 1, 0), ("mid", "queue", [], 3, 1),
                 ("ultra", "queue", [], 6, 5), ("simple", "migrazione", [], 6, 5),
                 ("mid", "form", ["--type", "frontend"], 6, 6),
                 ("mid", "feature", ["--type", "forge"], 5, 0),
                 ("mid", "review", ["--type", "skill"], 3, 0)]
        for effort, topic, flags, members, reviewers in cases:
            with self.subTest(effort=effort, topic=topic):
                opts = ["--topic", topic, "--effort", effort, "--config-root", self.root/"config", *flags]
                estimate = json.loads(self.cli("estimate", *opts, "--json").stdout)
                session = Path(self.cli("init", *opts, "--session-root", self.root/"sessions", "--confirm-estimate").stdout.strip())
                meta = json.loads((session/"session.json").read_text())
                self.assertEqual(meta["effort"], effort)
                self.assertEqual(meta["pre_session_estimate"], estimate)
                self.assertEqual((estimate["role_count"], estimate["reviewer_count"]), (members, reviewers))
                self.assertEqual(len(list((session/"reviews").glob("*.md"))), reviewers)
                self.assertTrue(cc.validate_session(session)["ok"])
                inputs = json.loads((session/"prompts"/cc.SYNTHESIS_INPUT_MANIFEST).read_text())["inputs"]
                for group in ("members", "reviewers", "evidence_runners"):
                    self.assertTrue(all((session/name).is_file() for name in inputs[group]))

    def test_settled_brief_reaches_the_session_and_can_raise_the_risk_floor(self):
        self.brief["decisions"] = [{"id": "retention", "question": "Which data?", "answer": "personal data"}]
        self.read()
        opts = ["--topic", "queue", "--effort", "simple", "--brief", self.path, "--config-root", self.root/"config"]
        session = Path(self.cli("init", *opts, "--session-root", self.root/"sessions").stdout.strip())
        meta = json.loads((session/"session.json").read_text())
        self.assertEqual(meta["mode"], "deep")
        self.assertEqual(meta["panel"], "full")
        self.assertIn("personal data", (session/"brief.md").read_text())
        self.assertIn("personal data", (session/cc.COMPILED_CONTEXT_FILE).read_text())
        self.assertNotIn("personal data", meta["topic"])

    def test_legacy_controls_and_conflicting_presets(self):
        estimate = self.cli("estimate", "--topic", "queue", "--mode", "standard", "--json")
        self.assertEqual(json.loads(estimate.stdout)["role_count"], 6)
        result = self.cli("estimate", "--topic", "queue", "--mode", "fast", "--effort", "simple", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("choose one interface", result.stderr)

    def test_specialist_question_is_bounded_and_reaches_the_actual_member_prompt(self):
        config = self.root / "config"
        opts = ["--role", "ada", "--config-root", config, "--question", "Who owns job state?"]
        self.assertIn("Who owns job state?", self.cli("alters", "preview", *opts).stdout)
        self.assertFalse(config.exists())
        self.cli("alters", "configure", *opts)
        session = Path(self.cli("init", "--topic", "queue", "--effort", "simple",
                                "--session-root", self.root / "sessions", "--config-root", config).stdout.strip())
        prompt = (session / "prompts/members/01-ada.md").read_text()
        self.assertIn("If unresolved, send the lead this question: Who owns job state?", prompt)

    def test_risk_floor_in_english_and_italian(self):
        for topic in ("Plan database migrations", "Eliminare tutti i dati in produzione",
                      "Gestire i permessi di accesso", "Expose access token usage logs", "Persist refresh token usage"):
            with self.subTest(topic=topic):
                result = cc.estimate_pre_session(topic, effort="simple")
                self.assertEqual((result["mode"], result["panel"]), ("deep", "full"))
        result = cc.estimate_pre_session("Estimate token usage", effort="simple")
        self.assertEqual(result["panel"], "solo")

    def test_fixed_lenses_with_identical_caps_have_the_same_forecast(self):
        for kind in ("forge", "skill"):
            with self.subTest(kind=kind):
                costs = [cc.estimate_pre_session("queue", effort=effort, session_type=kind)["estimated_total_tokens"]
                         for effort in ("simple", "mid", "ultra")]
                self.assertEqual(costs[0], costs[1])
                self.assertLess(costs[1], costs[2])

    def test_estimate_summary_retains_risk_and_range_with_details_on_request(self):
        opts = ["estimate", "--effort", "simple", "--topic", "payment"]
        short = self.cli(*opts).stdout
        self.assertIn("simple / general / full panel", short)
        self.assertIn("data_loss", short)
        self.assertIn("local estimate", short)
        self.assertLessEqual(len(short.splitlines()), 4)
        self.assertIn("Pre-execution components", self.cli(*opts, "--details").stdout)
