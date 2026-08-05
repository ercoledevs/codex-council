import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE_URL = "https://ercoledevs.github.io/codex-council/"
NAV_LINKS = [
    "use-cases.html",
    "examples.html",
    "wiki.html",
    "usage.html",
]
CELL_COMMANDS = [
    "project",
    "apply",
    "plan",
    "doctor",
    "recover",
    "rollback",
    "purge",
    "replay",
    "fault-test",
]
MIRROR_TAGS = (
    "section",
    "article",
    "h1",
    "h2",
    "h3",
    "h4",
    "pre",
    "table",
    "ul",
    "li",
)


class ParsedPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.ids = []
        self.hrefs = []
        self.srcs = []
        self.nav_links = []
        self.nav_current = []
        self.nav_aria_current = []
        self.nav_location = []
        self.canonical = None
        self.alternates = {}
        self.base_href = None
        self.tags = Counter()
        self.text = []
        self.ascii_text = []
        self._nav_links_depth = 0
        self._nav_depth = 0
        self._ascii_depth = 0

    @staticmethod
    def _classes(attrs):
        return set(attrs.get("class", "").split())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag] += 1
        if tag == "html":
            self.lang = attrs.get("lang")
        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)

        if self._nav_links_depth:
            self._nav_links_depth += 1
        elif tag == "div" and "nav-links" in self._classes(attrs):
            self._nav_links_depth = 1

        if self._nav_depth:
            self._nav_depth += 1
        elif tag == "nav":
            self._nav_depth = 1

        if self._ascii_depth:
            self._ascii_depth += 1
        elif tag == "pre" and "ascii-art" in self._classes(attrs):
            self._ascii_depth = 1

        if tag == "a" and attrs.get("href"):
            href = attrs["href"]
            self.hrefs.append(href)
            if self._nav_depth and attrs.get("aria-current") == "page":
                self.nav_aria_current.append(href)
            if self._nav_depth and attrs.get("aria-current") == "location":
                self.nav_location.append(href)
            if self._nav_links_depth:
                self.nav_links.append(href)
                if attrs.get("aria-current") == "page":
                    self.nav_current.append(href)

        if tag in {"img", "script"} and attrs.get("src"):
            self.srcs.append(attrs["src"])

        if tag == "link":
            rel = set(attrs.get("rel", "").split())
            if "canonical" in rel:
                self.canonical = attrs.get("href")
            if "alternate" in rel and attrs.get("hreflang"):
                self.alternates[attrs["hreflang"]] = attrs.get("href")
        if tag == "base":
            self.base_href = attrs.get("href")

    def handle_endtag(self, tag):
        if self._nav_links_depth:
            self._nav_links_depth -= 1
        if self._nav_depth:
            self._nav_depth -= 1
        if self._ascii_depth:
            self._ascii_depth -= 1

    def handle_data(self, data):
        self.text.append(data)
        if self._ascii_depth:
            self.ascii_text.append(data)


def parse_page(path):
    parser = ParsedPage()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def paired_urls(filename):
    if filename == "index.html":
        return SITE_URL, SITE_URL + "it/"
    return SITE_URL + filename, SITE_URL + "it/" + filename


class DocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_pages = sorted(DOCS.glob("*.html"))
        cls.it_pages = sorted((DOCS / "it").glob("*.html"))
        cls.all_pages = cls.root_pages + cls.it_pages
        cls.parsed = {path: parse_page(path) for path in cls.all_pages}

    def test_every_english_content_page_has_an_italian_mirror(self):
        english = {path.name for path in self.root_pages if path.name != "404.html"}
        italian = {path.name for path in self.it_pages}
        self.assertEqual(english, italian)

    def test_mirrored_pages_keep_the_same_semantic_structure(self):
        for english in self.root_pages:
            if english.name == "404.html":
                continue
            italian = DOCS / "it" / english.name
            with self.subTest(page=english.name):
                en_tags = self.parsed[english].tags
                it_tags = self.parsed[italian].tags
                self.assertEqual(
                    {tag: en_tags[tag] for tag in MIRROR_TAGS},
                    {tag: it_tags[tag] for tag in MIRROR_TAGS},
                )

    def test_internal_links_and_fragments_resolve(self):
        for page, parsed in self.parsed.items():
            for href in parsed.hrefs:
                split = urlsplit(href)
                if split.scheme or href.startswith("//") or href.startswith("mailto:"):
                    continue
                target = page.parent / split.path if split.path else page
                with self.subTest(page=str(page.relative_to(ROOT)), href=href):
                    self.assertTrue(target.is_file(), f"missing target: {target}")
                    if split.fragment:
                        target_page = self.parsed.get(target) or parse_page(target)
                        self.assertIn(split.fragment, target_page.ids)

    def test_local_assets_resolve(self):
        for page, parsed in self.parsed.items():
            for src in parsed.srcs:
                split = urlsplit(src)
                if split.scheme or src.startswith("//"):
                    continue
                target = page.parent / split.path
                with self.subTest(page=str(page.relative_to(ROOT)), src=src):
                    self.assertTrue(target.is_file(), f"missing asset: {target}")

        css = (DOCS / "styles.css").read_text(encoding="utf-8")
        for asset in re.findall(r'url\(["\']?([^)"\']+)', css):
            if asset.startswith(("data:", "http://", "https://")):
                continue
            with self.subTest(page="docs/styles.css", src=asset):
                self.assertTrue((DOCS / asset).is_file(), f"missing CSS asset: {asset}")

    def test_ids_are_unique(self):
        for page, parsed in self.parsed.items():
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(len(parsed.ids), len(set(parsed.ids)))

    def test_navigation_order_is_consistent(self):
        location_parent = {
            "alters.html": "wiki.html",
            "runtime.html": "wiki.html",
            "limits.html": "wiki.html",
        }
        for page, parsed in self.parsed.items():
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(parsed.nav_links, NAV_LINKS)
                if page.name in NAV_LINKS:
                    self.assertEqual(parsed.nav_current, [page.name])
                    self.assertEqual(parsed.nav_aria_current, [page.name])
                else:
                    self.assertEqual(parsed.nav_current, [])
                    self.assertEqual(parsed.nav_aria_current, [])
                expected_location = location_parent.get(page.name)
                self.assertEqual(
                    parsed.nav_location,
                    [expected_location] if expected_location else [],
                )

    def test_every_page_defaults_to_dark_and_preserves_the_saved_theme(self):
        bootstrap = (
            'var t = localStorage.getItem("cc-theme");\n'
            '          document.documentElement.setAttribute("data-theme", t || "dark");\n'
            '        } catch (e) {\n'
            '          document.documentElement.setAttribute("data-theme", "dark");\n'
            '        }'
        )
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertIn(bootstrap, source)

    def test_homepages_are_compact_product_landings(self):
        expected_positioning = {
            "index.html": (
                "Take an idea to reviewed, verified code.",
                "Hyper applies the authorized change",
            ),
            "it/index.html": (
                "Dall’idea al codice revisionato e verificato.",
                "Hyper applica la modifica autorizzata",
            ),
        }
        for relative, expected in expected_positioning.items():
            page = DOCS / relative
            source = page.read_text(encoding="utf-8")
            parsed = self.parsed[page]
            text = " ".join("".join(parsed.text).split())
            with self.subTest(page=relative):
                self.assertRegex(
                    source,
                    r'<body[^>]*class="[^"]*\bhome-noir\b[^"]*"',
                )
                self.assertEqual(parsed.tags["section"], 3)
                for workflow in ("Council", "Forge", "Mind", "Hyper"):
                    self.assertIn(workflow, text)
                for phrase in expected:
                    self.assertIn(phrase, text)
                workflow_bento = source.split('<div class="workflow-bento">', 1)[1].split(
                    '<div class="proof-strip"', 1
                )[0]
                self.assertLess(workflow_bento.index("<h3>Forge"), workflow_bento.index("<h3>Council"))
                self.assertLess(workflow_bento.index("<h3>Council"), workflow_bento.index("<h3>Mind"))
                self.assertLess(workflow_bento.index("<h3>Mind"), workflow_bento.index("<h3>Hyper"))

    def test_language_and_hreflang_contract(self):
        for english in self.root_pages:
            parsed = self.parsed[english]
            if english.name == "404.html":
                self.assertEqual(parsed.lang, "en")
                continue
            italian = DOCS / "it" / english.name
            en_url, it_url = paired_urls(english.name)
            for path, lang, canonical in (
                (english, "en", en_url),
                (italian, "it", it_url),
            ):
                page = self.parsed[path]
                with self.subTest(page=str(path.relative_to(ROOT))):
                    self.assertEqual(page.lang, lang)
                    self.assertEqual(page.canonical, canonical)
                    self.assertEqual(
                        page.alternates,
                        {"en": en_url, "it": it_url, "x-default": en_url},
                    )

    def test_runtime_banner_is_identical_and_eighty_columns(self):
        banners = []
        for path in (DOCS / "runtime.html", DOCS / "it" / "runtime.html"):
            banner = "".join(self.parsed[path].ascii_text).strip("\n")
            lines = banner.splitlines()
            with self.subTest(page=str(path.relative_to(ROOT))):
                self.assertEqual(len(lines), 14)
                self.assertTrue(all(len(line) == 80 for line in lines))
            banners.append(banner)
        self.assertEqual(banners[0], banners[1])

    def test_runtime_commands_are_documented_in_the_technical_wiki(self):
        pages = [
            DOCS / "wiki.html",
            DOCS / "it" / "wiki.html",
        ]
        for page in pages:
            text = "".join(self.parsed[page].text)
            for command in CELL_COMMANDS:
                with self.subTest(page=str(page.relative_to(ROOT)), command=command):
                    self.assertIn(f"cells {command} --help", text)

    def test_runtime_pages_remain_product_showcases(self):
        forbidden = (
            "<figcaption>",
            "cells fault-test",
            "tests/fixtures/council_cells",
        )
        for page in (DOCS / "runtime.html", DOCS / "it" / "runtime.html"):
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(self.parsed[page].tags["section"], 5)
                for phrase in forbidden:
                    self.assertNotIn(phrase, source)

    def test_wiki_exposes_six_sections_and_thirty_labeled_templates(self):
        section_ids = {
            "choose",
            "method",
            "evidence-lab",
            "recipes",
            "operations",
            "reference",
        }
        for relative in ("wiki.html", "it/wiki.html"):
            path = DOCS / relative
            source = path.read_text(encoding="utf-8")
            parsed = self.parsed[path]
            with self.subTest(page=relative):
                self.assertTrue(section_ids.issubset(set(parsed.ids)))
                self.assertEqual(source.count('class="recipe-family"'), 5)
                self.assertEqual(source.count("<article><h3>"), 30)
                label = (
                    "Prompt example"
                    if relative == "wiki.html"
                    else "Esempio di prompt"
                )
                cookbook = re.search(
                    r'<div id="cookbook" class="recipe-catalog">(.*?)</section>',
                    source,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(cookbook)
                self.assertEqual(
                    cookbook.group(1).count(
                        f'<span class="prompt-tag">{label}</span>'
                    ),
                    30,
                )
                stage_heading = (
                    "Hyper’s six stages"
                    if relative == "wiki.html"
                    else "Le sei fasi di Hyper"
                )
                stage_rail = re.search(
                    rf"<h3>{re.escape(stage_heading)}</h3>\s*"
                    r'<ol class="method-rail">(.*?)</ol>',
                    source,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(stage_rail)
                self.assertEqual(stage_rail.group(1).count("<li>"), 6)

    def test_evidence_lab_records_are_replayable_and_honest(self):
        evidence = DOCS / "evidence"
        node = evidence / "2026-07-23-node-scheduler"
        self.assertEqual(
            sorted(path.name for path in evidence.iterdir() if path.is_dir()),
            ["2026-07-23-node-scheduler"],
        )

        manifest = json.loads((node / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["status"], "PASS_WITH_PARTIAL_WORKFLOW_PROVENANCE")
        self.assertEqual(manifest["workflow"]["name"], "codex-hyper")
        self.assertEqual(manifest["workflow"]["route"], "Relay")
        self.assertEqual(
            manifest["product"]["hyper_release_status"],
            "BUNDLED_PLUGIN_SKILL",
        )
        self.assertEqual(manifest["outcome"]["verdict"], "PASS_AGAINST_FINAL_CONTRACT")
        self.assertEqual(manifest["outcome"]["tests"], {
            "passed": 13,
            "failed": 0,
            "node_options": "--unhandled-rejections=strict",
        })
        self.assertEqual(manifest["outcome"]["syntax"], "PASS")
        self.assertEqual(manifest["outcome"]["fresh_verifier"], "PASS")
        self.assertEqual(manifest["outcome"]["published_patch_replay"], "PASS")
        self.assertEqual(manifest["provenance"]["outcome_replay"], "PASS")
        self.assertEqual(manifest["provenance"]["workflow_provenance"], "PARTIAL")
        self.assertFalse(manifest["limits"]["general_benchmark_claim"])
        self.assertIn("AbortSignal", manifest["limits"]["known_behavior"])

        for name in (
            "README.md",
            "task.md",
            "hyper.patch",
            "hyper-verifier.md",
            "checks.md",
            "manifest.json",
            "provenance.md",
        ):
            artifact = node / name
            self.assertTrue(artifact.is_file(), f"missing evidence: {artifact}")
            self.assertGreater(artifact.stat().st_size, 20)
        for hidden_failure in ("normal.patch", "normal-verifier.md", "task-v2.md"):
            self.assertFalse((node / hidden_failure).exists())
        self.assertIn(
            "diff --git",
            (node / "hyper.patch").read_text(encoding="utf-8"),
        )

        for relative, expected in manifest["baseline"]["sha256"].items():
            baseline_file = node / "baseline" / relative
            self.assertTrue(baseline_file.is_file())
            self.assertEqual(
                hashlib.sha256(baseline_file.read_bytes()).hexdigest(),
                expected,
            )
        for relative, expected in manifest["evidence_sha256"].items():
            artifact = node / relative
            self.assertEqual(
                hashlib.sha256(artifact.read_bytes()).hexdigest(),
                expected,
            )
        self.assertEqual(
            hashlib.sha256((node / "task.md").read_bytes()).hexdigest(),
            manifest["task"]["sha256"],
        )

        with tempfile.TemporaryDirectory(prefix="council-evidence-") as temp:
            candidate = Path(temp) / node.name
            shutil.copytree(node / "baseline", candidate)
            patch = node / "hyper.patch"
            for args in (
                ("git", "apply", "--check", str(patch)),
                ("git", "apply", str(patch)),
            ):
                result = subprocess.run(
                    args,
                    cwd=candidate,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{' '.join(args)}\n{result.stdout}\n{result.stderr}",
                )

            env = os.environ.copy()
            env["NODE_OPTIONS"] = "--unhandled-rejections=strict"
            tests = subprocess.run(
                ("npm", "test"),
                cwd=candidate,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                tests.returncode,
                0,
                f"{tests.stdout}\n{tests.stderr}",
            )
            self.assertRegex(tests.stdout, r"(?:#\s*)?pass\s+13\b")

            syntax = subprocess.run(
                ("node", "--check", "src/scheduler.js"),
                cwd=candidate,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(syntax.returncode, 0, syntax.stderr)

        for relative in ("examples.html", "it/examples.html"):
            source = (DOCS / relative).read_text(encoding="utf-8")
            text = "".join(self.parsed[DOCS / relative].text)
            self.assertIn("13/13", text)
            self.assertIn(
                "partial" if relative == "examples.html" else "parzial",
                text.lower(),
            )
            self.assertNotIn("12220", text)
            for forbidden in (
                "result-fail",
                "status-warn",
                "INCOMPLETE",
                "planned-runs",
                "normal.patch",
                "url-state",
                "Plain Codex",
            ):
                self.assertNotIn(forbidden, source)

        for relative in ("wiki.html", "it/wiki.html"):
            source = (DOCS / relative).read_text(encoding="utf-8")
            for forbidden in (
                "normal.patch",
                "url-state",
                "Browser unknown",
            ):
                self.assertNotIn(forbidden, source)

    def test_comparison_panels_have_real_headings(self):
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertNotIn('<div class="panel-title">', source)

    def test_public_copy_keeps_failed_and_incomplete_cases_out_of_the_site(self):
        forbidden = (
            "normal.patch",
            "normal-verifier",
            "url-state",
            "INCOMPLETE_BROWSER_UNKNOWN",
            "planned-runs",
            "Template · not run",
            "Template · non eseguito",
            "result-fail",
            "status-warn",
            "independent role lenses",
            "always ships",
        )
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                for phrase in forbidden:
                    self.assertNotIn(phrase, source)

        released_pages = (
            "examples.html",
            "hyper.html",
            "mind.html",
            "usage.html",
            "wiki.html",
            "it/examples.html",
            "it/hyper.html",
            "it/mind.html",
            "it/usage.html",
            "it/wiki.html",
        )
        for relative in released_pages:
            text = (DOCS / relative).read_text(encoding="utf-8").lower()
            with self.subTest(page=relative):
                self.assertIn("hyper", text)
                self.assertNotRegex(
                    text,
                    r"(?:unreleased|non rilasciat|non ancora rilasciat|"
                    r"development preview|preview di sviluppo|anteprima di sviluppo)",
                )

    def test_open_source_trust_signals_are_visible(self):
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            if '<footer class="footer">' not in source:
                continue
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertIn("@ercoledevs", source)
                self.assertRegex(source, r"(?:MIT licensed|Licenza MIT)")

        for relative in ("index.html", "it/index.html"):
            source = (DOCS / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertIn(
                    "https://github.com/ercoledevs/codex-council",
                    source,
                )
                self.assertIn(
                    "https://github.com/ercoledevs/codex-council/releases",
                    source,
                )
                self.assertIn(
                    "https://github.com/ercoledevs/codex-council/issues",
                    source,
                )
                self.assertIn("CHANGELOG.md", source)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Why I built it", readme)
        self.assertIn("I maintain the project independently", readme)
        self.assertIn("github.com/ercoledevs/codex-council/releases", readme)
        self.assertIn("github.com/ercoledevs/codex-council/issues", readme)
        self.assertIn("30\npaste-ready prompt templates", readme)
        self.assertIn("Included in the current release", readme)
        self.assertIn("Council, Forge, Mind, Hyper", readme)
        self.assertNotRegex(readme, r"16.?recipe")

    def test_all_documentation_tables_have_captions_and_scoped_headers(self):
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            for index, table in enumerate(
                re.findall(r"<table\b[^>]*>.*?</table>", source, flags=re.DOTALL)
            ):
                with self.subTest(page=str(page.relative_to(ROOT)), table=index):
                    self.assertIn("<caption>", table)
                    headers = re.findall(r"<th\b([^>]*)>", table)
                    self.assertTrue(headers)
                    self.assertTrue(
                        all(re.search(r'\bscope="(?:col|row)"', attrs) for attrs in headers)
                    )

    def test_intelligence_cli_is_documented_in_usage_and_wiki(self):
        required = (
            "--router auto --panel auto",
            "compile-context",
            "doctor --session",
            "dashboard",
        )
        for relative in ("usage.html", "wiki.html", "it/usage.html", "it/wiki.html"):
            page = DOCS / relative
            text = "".join(self.parsed[page].text)
            for phrase in required:
                with self.subTest(page=relative, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_mind_docs_present_hyper_as_an_optional_bundled_stage(self):
        english_path = DOCS / "mind.html"
        italian_path = DOCS / "it" / "mind.html"
        english = " ".join("".join(self.parsed[english_path].text).lower().split())
        italian = " ".join("".join(self.parsed[italian_path].text).lower().split())

        for page, text in (("mind.html", english), ("it/mind.html", italian)):
            with self.subTest(page=page):
                self.assertIn("codex hyper", text)
                self.assertIn("$codex-council:codex-hyper", text)

        self.assertIn("optional", english)
        self.assertIn("bundled", english)
        self.assertRegex(italian, r"opzional")
        self.assertRegex(italian, r"(?:inclus[oa].{0,40}(?:plugin|bundle)|dentro.{0,40}plugin)")
        self.assertRegex(
            english,
            r"(?:separate|dedicated|its own)[^.]{0,140}preflight|preflight[^.]{0,140}(?:separate|dedicated|its own)",
        )
        self.assertRegex(
            italian,
            r"(?:separat|dedicat|propri)[^.]{0,140}preflight|preflight[^.]{0,140}(?:separat|dedicat|propri)",
        )
        self.assertIn("every mind handoff enters relay", english)
        self.assertIn("ogni handoff da mind entra in relay", italian)
        for outcome in ("pass", "fail", "unknown"):
            self.assertIn(outcome, english)
            self.assertIn(outcome, italian)

        forbidden = (
            r"\bexternal\b",
            r"\bestern[oaie]\b",
            r"separately installed",
            r"installed separately",
            r"separate installation",
            r"installat[oa] separatamente",
            r"installazione separata",
        )
        for page in (english_path, italian_path):
            source = page.read_text(encoding="utf-8").lower()
            for pattern in forbidden:
                with self.subTest(page=str(page.relative_to(ROOT)), pattern=pattern):
                    self.assertNotRegex(source, pattern)

    def test_hyper_docs_explain_the_execution_method(self):
        common = (
            "solo",
            "relay",
            "read-only",
            "$codex-council:codex-hyper",
        )
        stages = {
            "hyper.html": ("contract", "observe", "orient", "act", "falsify", "close"),
            "it/hyper.html": ("contratto", "osserva", "orienta", "agisci", "falsifica", "chiudi"),
        }
        for relative, stage_names in stages.items():
            path = DOCS / relative
            text = " ".join("".join(self.parsed[path].text).lower().split())
            with self.subTest(page=relative):
                self.assertEqual(self.parsed[path].tags["section"], 5)
                for phrase in common + stage_names:
                    self.assertIn(phrase, text)

        english = " ".join("".join(self.parsed[DOCS / "hyper.html"].text).lower().split())
        italian = " ".join("".join(self.parsed[DOCS / "it" / "hyper.html"].text).lower().split())
        self.assertIn("one writer", english)
        self.assertIn("never uses parallel writers", english)
        self.assertIn("any unmet required gate blocks completion", english)
        self.assertIn("hyper is bundled with codex council", english)
        self.assertIn("relay adds a fresh read-only verifier", english)
        self.assertIn("invoke hyper directly", english)
        self.assertIn("every mind handoff enters relay", english)
        self.assertIn("un solo writer", italian)
        self.assertIn("non usa mai writer paralleli", italian)
        self.assertIn(
            "qualsiasi gate richiesto non soddisfatto impedisce il completamento",
            italian,
        )
        self.assertIn("hyper è incluso in codex council", italian)
        self.assertIn("relay aggiunge un verifier read-only nuovo", italian)
        self.assertIn("invoca hyper direttamente", italian)
        self.assertIn("ogni handoff da mind entra in relay", italian)

        for relative in ("index.html", "it/index.html"):
            source = (DOCS / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertIn('class="workflow-link" href="hyper.html"', source)

        for relative in ("mind.html", "it/mind.html"):
            source = (DOCS / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertIn('<a href="hyper.html">', source)

    def test_font_query_strings_are_html_escaped(self):
        for page in self.all_pages:
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertNotIn("&display=swap", source)
                self.assertIn("&amp;display=swap", source)

    def test_custom_404_resolves_assets_from_the_pages_root(self):
        self.assertEqual(self.parsed[DOCS / "404.html"].base_href, "/codex-council/")


if __name__ == "__main__":
    unittest.main()
