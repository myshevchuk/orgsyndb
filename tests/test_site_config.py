"""Hugo configuration and its overlay, ignore rules, the demo collection
and the Caddyfile example (site-build, build-script, sample-procedures)."""

import re
import shutil
import subprocess
import tomllib
import unittest
from pathlib import Path

from pipeline_support import DEMO, ORGSYNDB, PIPELINE, REPO, pipeline

HUGO_TOML = REPO / "site" / "hugo.toml"
CADDYFILE = REPO / "deploy" / "Caddyfile.example"
GITIGNORE = REPO / ".gitignore"

SITE_URL = "http://127.0.0.1:8000"


def strings(value):
    """Yield every string in a parsed TOML value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


class HugoConfigurationTests(unittest.TestCase):
    def test_configuration_parses_to_the_contract(self) -> None:
        """Scenario: Configuration parses to the contract."""
        self.assertTrue(HUGO_TOML.is_file(), "site/hugo.toml does not exist")
        config = tomllib.loads(HUGO_TOML.read_text(encoding="utf-8"))
        self.assertEqual(config.get("baseURL"), "/")
        self.assertEqual(config.get("locale"), "de")
        for key in ("languages", "defaultContentLanguage"):
            self.assertNotIn(key, config)
        self.assertIs(config.get("relativeURLs"), True)
        self.assertIs(config.get("buildFuture"), True)
        self.assertIs(config.get("buildExpired"), True)
        self.assertIn("rss", config.get("disableKinds", []))
        self.assertIn("sitemap", config.get("disableKinds", []))
        self.assertEqual(config.get("taxonomies"), {
            "author": "authors", "reaction_type": "reaction_types",
            "tag": "tags"})
        self.assertEqual(
            config.get("permalinks", {}).get("page", {}).get("procedures"),
            "/procedures/:slug/")
        goldmark = config.get("markup", {}).get("goldmark", {})
        self.assertIs(goldmark.get("renderer", {}).get("unsafe"), True)
        highlight = config.get("markup", {}).get("highlight", {})
        self.assertIs(highlight.get("noClasses"), False)
        html_minify = config.get("minify", {}).get("tdewolff", {}).get(
            "html", {})
        self.assertIs(html_minify.get("keepWhitespace"), True)
        self.assertEqual(config.get("params", {}).get("siteurl"), SITE_URL)
        for key in ("publishDir", "resourceDir", "module"):
            self.assertNotIn(key, config)
        self.assertFalse((REPO / "site" / "static").exists(),
                         "the overlay's static mount hides site/static/")

    def test_configuration_names_no_host(self) -> None:
        """Scenario: Configuration parses to the contract (no host)."""
        self.assertTrue(HUGO_TOML.is_file(), "site/hugo.toml does not exist")
        config = tomllib.loads(HUGO_TOML.read_text(encoding="utf-8"))
        hosts = [s for s in strings(config) if re.search(r"://|^//", s)]
        self.assertEqual(hosts, [SITE_URL])
        self.assertEqual(config.get("params", {}).get("siteurl"), SITE_URL)


class OverlayTests(unittest.TestCase):
    def test_overlay_parses_to_the_contract(self) -> None:
        """Scenario: Overlay parses to the contract."""
        site = Path('/srv/app "one"/site')
        collection = Path('/srv/data "two", here')
        overlay = tomllib.loads(pipeline().hugo_overlay(site, collection,
                                                         "de"))
        self.assertEqual(set(overlay), {"publishDir", "resourceDir",
                                        "defaultContentLanguage", "module"})
        self.assertEqual(overlay["defaultContentLanguage"], "de")
        self.assertEqual(overlay["publishDir"], f"{collection}/public")
        self.assertEqual(overlay["resourceDir"],
                         f"{collection}/build/hugo-resources")
        files = ["/OSDB-*.md"]
        self.assertEqual(overlay["module"], {"mounts": [
            {"source": f"{site}/content", "target": "content"},
            {"source": f"{collection}/build/content/procedures",
             "target": "content/procedures", "files": files},
            {"source": f"{collection}/build/content/help",
             "target": "content/help"},
            {"source": f"{collection}/static", "target": "static"},
        ]})


class DemoCollectionTests(unittest.TestCase):
    def test_samples_live_in_the_demo_collection(self) -> None:
        """Scenario: Samples live in the demo collection."""
        self.assertTrue((DEMO / "orgsyndb.toml").is_file())
        for path in ("org/procedures/OSDB-0001-salicylic-acid.org",
                     "md/procedures/OSDB-0002-aspirin.md"):
            self.assertTrue((DEMO / path).is_file(), path)
        for path in ("org", "md", "site/static"):
            self.assertFalse((REPO / path).exists(), path)


@unittest.skipUnless(shutil.which("git"), "git not found")
class IgnoreRuleTests(unittest.TestCase):
    IGNORED = ["examples/demo/build/export/x.md",
               "examples/demo/public/index.html", "examples/demo/pdf/x.pdf",
               ".emacs-batch/elpa", ".tools/pagefind-1.5.2/pagefind"]
    TRACKED = ["examples/demo/org/procedures/OSDB-0001-salicylic-acid.org",
               "examples/demo/md/procedures/OSDB-0002-aspirin.md",
               "examples/demo/static/structures/osdb-0003.svg",
               "site/hugo.toml", "site/.hugo_build.lock", "build/x",
               "tests/fixtures/export/build/x"]

    def ignored(self, path: str) -> bool:
        done = subprocess.run(["git", "-C", str(REPO), "check-ignore",
                               "-q", "--", path], capture_output=True,
                              timeout=60)
        self.assertIn(done.returncode, (0, 1), done.stderr)
        return done.returncode == 0

    def test_generated_paths_are_ignored_and_sources_are_not(self) -> None:
        """Scenario: Generated paths ignored, sources not."""
        for path in self.IGNORED:
            with self.subTest(path=path):
                self.assertTrue(self.ignored(path), f"{path} not ignored")
        for path in self.TRACKED:
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path), f"{path} is ignored")

    def test_python_caches_stay_ignored(self) -> None:
        """Scenario: Generated paths ignored, sources not (kept rules)."""
        lines = GITIGNORE.read_text(encoding="utf-8").splitlines()
        self.assertIn("__pycache__/", lines)
        self.assertIn(".pytest_cache/", lines)


class CaddyfileTests(unittest.TestCase):
    def test_example_is_generic(self) -> None:
        """Scenario: Example is generic."""
        self.assertTrue(CADDYFILE.is_file(),
                        "deploy/Caddyfile.example does not exist")
        text = CADDYFILE.read_text(encoding="utf-8")
        self.assertIn("file_server", text)
        self.assertRegex(text, r'(?m)^\s*header\s+Cache-Control\s+"no-cache"\s*$')
        self.assertRegex(text, r"(?m)^\s*root\s+\S")
        self.assertNotIn("/home/", text)
        self.assertNotRegex(text, r"\.(local|lan|home\.arpa)\b")

    def test_example_parses_when_caddy_is_installed(self) -> None:
        """Scenario: Example parses when Caddy is installed."""
        caddy = shutil.which("caddy")
        if caddy is None:
            self.skipTest("caddy not found")
        self.assertTrue(CADDYFILE.is_file(),
                        "deploy/Caddyfile.example does not exist")
        done = subprocess.run(
            [caddy, "adapt", "--adapter", "caddyfile", "--config",
             str(CADDYFILE)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)


class NothingEnablesTheHookTests(unittest.TestCase):
    def test_scripts_never_touch_hook_configuration(self) -> None:
        """Scenario: Nothing enables the hook."""
        for script in (ORGSYNDB, PIPELINE):
            self.assertTrue(script.is_file(),
                            f"tools/{script.name} does not exist")
            text = script.read_text(encoding="utf-8")
            for needle in ("hooksPath", ".git/hooks"):
                with self.subTest(script=script.name, needle=needle):
                    self.assertNotIn(needle, text)
