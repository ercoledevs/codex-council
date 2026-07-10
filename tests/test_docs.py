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
    "usage.html",
    "runtime.html",
    "forge.html",
    "mind.html",
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
MIRROR_TAGS = ("section", "article", "h1", "h2", "h3", "pre", "table", "ul", "li")


class ParsedPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.ids = []
        self.hrefs = []
        self.nav_links = []
        self.nav_current = []
        self.canonical = None
        self.alternates = {}
        self.base_href = None
        self.tags = Counter()
        self.text = []
        self.ascii_text = []
        self._nav_links_depth = 0
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

        if self._ascii_depth:
            self._ascii_depth += 1
        elif tag == "pre" and "ascii-art" in self._classes(attrs):
            self._ascii_depth = 1

        if tag == "a" and attrs.get("href"):
            href = attrs["href"]
            self.hrefs.append(href)
            if self._nav_links_depth:
                self.nav_links.append(href)
                if attrs.get("aria-current") == "page":
                    self.nav_current.append(href)

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

    def test_ids_are_unique(self):
        for page, parsed in self.parsed.items():
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(len(parsed.ids), len(set(parsed.ids)))

    def test_navigation_order_is_consistent(self):
        for page, parsed in self.parsed.items():
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(parsed.nav_links, NAV_LINKS)
                if page.name in NAV_LINKS:
                    self.assertEqual(parsed.nav_current, [page.name])
                else:
                    self.assertEqual(parsed.nav_current, [])

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
