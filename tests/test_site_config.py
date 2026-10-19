"""Hugo configuration, ignore rules and the Caddyfile example
(site-build, build-script)."""

import re
import shutil
import subprocess
import tomllib
import unittest

from pipeline_support import BUILD_FISH, PIPELINE, REPO

HUGO_TOML = REPO / "site" / "hugo.toml"
CADDYFILE = REPO / "deploy" / "Caddyfile.example"
GITIGNORE = REPO / ".gitignore"

MOUNTS = [
    {"source": "content", "target": "content"},
    {"source": "../build/export", "target": "content/procedures",
     "files": ["/OSDB-*.md"]},
    {"source": "../md/procedures", "target": "content/procedures",
     "files": ["/OSDB-*.md"]},
]


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
        self.assertEqual(config.get("locale"), "en")
        self.assertEqual(config.get("publishDir"), "../public")
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
        self.assertEqual(config.get("module", {}).get("mounts"), MOUNTS)

    def test_configuration_names_no_host(self) -> None:
        """Scenario: Configuration parses to the contract (no host)."""
        self.assertTrue(HUGO_TOML.is_file(), "site/hugo.toml does not exist")
        config = tomllib.loads(HUGO_TOML.read_text(encoding="utf-8"))
        hosts = [s for s in strings(config) if re.search(r"://|^//", s)]
        self.assertEqual(hosts, [])


@unittest.skipUnless(shutil.which("git"), "git not found")
class IgnoreRuleTests(unittest.TestCase):
    IGNORED = ["build/export/x.md", "public/index.html", "pdf/x.pdf",
               ".emacs-batch/elpa", ".tools/pagefind-1.5.2/pagefind",
               "site/.hugo_build.lock", "site/resources/_gen/x"]
    TRACKED = ["org/procedures/OSDB-0001-salicylic-acid.org",
               "md/procedures/OSDB-0002-aspirin.md", "site/hugo.toml",
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
        for script in (BUILD_FISH, PIPELINE):
            self.assertTrue(script.is_file(),
                            f"tools/{script.name} does not exist")
            text = script.read_text(encoding="utf-8")
            for needle in ("hooksPath", ".git/hooks"):
                with self.subTest(script=script.name, needle=needle):
                    self.assertNotIn(needle, text)
