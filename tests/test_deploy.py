"""Tests for the container deployment: deploy/docker/orgsyndb-deploy, the
Dockerfile, the Caddyfile and deploy/compose.yaml (container-deployment).

The updater runs against throwaway Git repositories: a fake application
whose tools/orgsyndb writes public/index.html from the collection, and a
collection. No image is built.
"""

import ast
import json
import os
import py_compile
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from pipeline_support import FakeApp, closed_address, closed_manifest_address
from support import (REGISTRY, load_snapshot, snapshot_digest)

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy"
DOCKER = DEPLOY / "docker"
UPDATER = DOCKER / "orgsyndb-deploy"
WEBAPP_DOCKERFILE = DEPLOY / "webapp" / "Dockerfile"
BACKUP = DEPLOY / "backup" / "orgsyndb-backup"
ENV_EXAMPLE = DEPLOY / "orgsyndb.env.example"

TOKEN = "builder-token"
# What the fake tool's `manifest` prints: the collection half of a
# manifest.
FAKE_MANIFEST = {
    "language": "de",
    "procedures": [{
        "id": "OSDB-0001", "source": "md", "title": "Salicylsäure",
        "title_de": "Salicylsäure", "reaction_type": "hydrolysis",
        "general": False,
        "entries": [{"substrates": ["methyl-salicylate"],
                     "products": [{"compound": "salicylic-acid",
                                   "yield_percent": 80}]}]}],
    "sequences": [{
        "id": "SEQ-0001", "title": "Salicylsäure", "title_de": None,
        "target": "salicylic-acid",
        "steps": [{"procedure": "OSDB-0001", "entry": None}]}],
    "deleted": ["OSDB-0002"],
}
BUILT_KEYS = {"format", "build", "commit", "committed_at", "base",
              "snapshot", "tooling", "trigger", "pusher", "outcome",
              "release", "language", "procedures", "sequences", "deleted"}
REFUSED_KEYS = {"format", "build", "commit", "committed_at", "base",
                "snapshot", "tooling", "trigger", "pusher", "outcome",
                "errors"}
# The line the fake build prints, on standard output, when it fails.
FAKE_PROBLEM = ("md/procedures/OSDB-0001-x.md:title: error: the fake "
                "build was told to fail")

FAKE_ORGSYNDB = """\
#!/usr/bin/env python3
# Fake tool: -C DIR build|pdf|manifest. Every run appends a JSON
# line of the command, $ORGSYNDB_REGISTRY and the text of the file it
# names to $FAKE_REGISTRY_LOG. A build fails when the collection
# holds `fail` or the application's VERSION reads `broken`, printing a
# problem line and an error line, or silently when it holds
# `fail-silent`, and appends one line per run to $FAKE_LOG. `manifest`
# logs nothing and prints the fixed collection half of a manifest; it
# fails when the collection holds `manifest-fail` or VERSION reads
# `manifest-broken`, and sleeps past any timeout when the collection
# holds `manifest-slow`. `index` is a command the builder must never
# run: the fake answers it with a minimal index, so that the run shows
# in the log and in the release. A build also appends the line
# $FAKE_PUSH_LINE, when that is set, to the file $ORGSYNDB_PUSH_LOG: a
# push that Forgejo logs while the build runs.
import json, os, sys, time
from pathlib import Path
app = Path(__file__).resolve().parent.parent
collection = Path(sys.argv[2])
version = (app / "VERSION").read_text().strip()
registry = os.environ.get("ORGSYNDB_REGISTRY", "")
with open(os.environ["FAKE_REGISTRY_LOG"], "a") as log:
    held = Path(registry).read_text() if registry and \\
        Path(registry).is_file() else ""
    log.write(json.dumps([sys.argv[3], registry, held]) + "\\n")
if sys.argv[3] == "index":
    print('{"site_language": "de"}')
    sys.exit(0)
if sys.argv[3] == "manifest":
    if (collection / "manifest-slow").exists():
        time.sleep(600)
    if (collection / "manifest-fail").exists() \\
            or version == "manifest-broken":
        sys.exit(1)
    print(@MANIFEST@)
    sys.exit(0)
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(f"{version} {sys.argv[3]}\\n")
if os.environ.get("FAKE_PUSH_LINE"):
    with open(os.environ["ORGSYNDB_PUSH_LOG"], "a") as pushes:
        pushes.write(os.environ["FAKE_PUSH_LINE"] + "\\n")
if (collection / "fail-silent").exists():
    sys.exit(1)
if (collection / "fail").exists() or version == "broken":
    print(@PROBLEM@)
    print("orgsyndb: error: validation found errors; the site was not "
          "built", file=sys.stderr)
    sys.exit(1)
public = collection / "public"
public.mkdir(exist_ok=True)
text = (collection / "content.txt").read_text().strip()
(public / "index.html").write_text(f"{version} {text}\\n")
if sys.argv[3] == "pdf":
    (collection / "pdf").mkdir(exist_ok=True)
    (collection / "pdf" / "a.pdf").write_text("pdf\\n")
""".replace("@MANIFEST@", repr(json.dumps(FAKE_MANIFEST))).replace(
    "@PROBLEM@", repr(FAKE_PROBLEM))


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c",
         "user.email=t@example.org", "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit_files(repo: Path, files: dict[str, str | None]) -> str:
    for name, text in files.items():
        path = repo / name
        if text is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "change")
    return git(repo, "rev-parse", "HEAD")


def plain(table: dict) -> dict:
    """The snapshot ``table`` without its ``import``."""
    return {key: value for key, value in table.items() if key != "import"}


@unittest.skipIf(shutil.which("git") is None, "git not found")
class UpdaterTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-deploy-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.upstream = self.tmp / "app-upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "--quiet", "--initial-branch", "main")
        self.app_v1 = commit_files(self.upstream, {
            "tools/orgsyndb": FAKE_ORGSYNDB,
            "VERSION": "v1\n",
            "deploy/docker/Dockerfile": "FROM scratch\n",
            ".gitignore": "/.tools/\n"})
        (self.upstream / "tools" / "orgsyndb").chmod(0o755)
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "--quiet", "--amend", "-m", "v1")
        self.app_v1 = git(self.upstream, "rev-parse", "HEAD")
        self.app = self.tmp / "app"
        subprocess.run(["git", "clone", "--quiet", str(self.upstream),
                        str(self.app)], check=True)
        # A fetched-tool cache, ignored by Git, must survive updates.
        (self.app / ".tools").mkdir()
        (self.app / ".tools" / "cached").write_text("x")
        self.image = self.tmp / "image.json"
        self.image.write_text(json.dumps({
            "app_repo": str(self.upstream), "app_ref": "main",
            "deploy_tree": git(self.upstream, "rev-parse",
                               "HEAD:deploy/docker")}))
        self.collection = self.tmp / "collection-upstream"
        self.collection.mkdir()
        git(self.collection, "init", "--quiet", "--initial-branch", "main")
        self.col_v1 = commit_files(self.collection, {
            "orgsyndb.toml": "format = 1\n",
            "content.txt": "first\n",
            ".gitignore": "/build/\n/public/\n/pdf/\n"})
        self.data = self.tmp / "data"
        self.log = self.tmp / "builds.log"
        self.push_log = self.tmp / "pushes.log"
        self.registry_log = self.tmp / "registry.log"
        self.snapshot = load_snapshot(REGISTRY)
        self.server = FakeApp(self.snapshot)
        self.server.token = TOKEN
        self.addCleanup(self.server.stop)
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.tmp),
            "GIT_CONFIG_NOSYSTEM": "1",
            "FAKE_LOG": str(self.log),
            "FAKE_REGISTRY_LOG": str(self.registry_log),
            "ORGSYNDB_REGISTRY_URL": self.server.url,
            "ORGSYNDB_MANIFEST_URL": self.server.manifest_url,
            "ORGSYNDB_BUILDER_TOKEN": TOKEN,
            "ORGSYNDB_DATA": str(self.data),
            "ORGSYNDB_APP": str(self.app),
            "ORGSYNDB_IMAGE_INFO": str(self.image),
            "ORGSYNDB_COLLECTION_REPO": str(self.collection),
            "ORGSYNDB_PUSH_LOG": str(self.push_log),
        }

    def sync(self, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(UPDATER), "sync"],
                              env={**self.env, **extra},
                              capture_output=True, text=True, timeout=120)

    def page(self) -> str:
        return (self.data / "current" / "public"
                / "index.html").read_text().strip()

    def builds(self) -> list[str]:
        if not self.log.exists():
            return []
        return self.log.read_text().splitlines()

    def state(self) -> dict:
        return json.loads((self.data / "state.json").read_text())

    def releases(self) -> list[str]:
        return sorted(entry.name for entry in
                      (self.data / "releases").iterdir())

    def current(self) -> str | None:
        """The name of the release ``current`` points at, or None."""
        link = self.data / "current"
        return os.path.basename(os.readlink(link)) if link.is_symlink() \
            else None

    def sent(self) -> list[dict]:
        """The manifests the fake application received, in order."""
        return [received.body for received in self.server.manifests]

    def test_first_sync_publishes(self) -> None:
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 first")
        self.assertTrue((self.data / "current").is_symlink())
        self.assertFalse(os.path.isabs(os.readlink(self.data / "current")))
        deployed = self.state()["deployed"]
        self.assertEqual(deployed["app"], self.app_v1)
        self.assertEqual(deployed["collection"], self.col_v1)
        self.assertEqual(self.builds(), ["v1 build"])

    def test_unchanged_sources_are_not_rebuilt(self) -> None:
        self.sync()
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.builds(), ["v1 build"])
        self.assertEqual(len(self.releases()), 1)

    def test_new_collection_commit_is_published(self) -> None:
        self.sync()
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(len(self.releases()), 2)

    def test_old_releases_are_pruned(self) -> None:
        self.sync(ORGSYNDB_KEEP_RELEASES="1")
        for text in ("b", "c", "d"):
            commit_files(self.collection, {"content.txt": text})
            self.sync(ORGSYNDB_KEEP_RELEASES="1")
        names = self.releases()
        self.assertEqual(len(names), 2)
        self.assertEqual(os.path.basename(
            os.readlink(self.data / "current")), names[-1])
        self.assertEqual(self.page(), "v1 d")

    def test_failed_collection_keeps_site_and_is_not_retried(self) -> None:
        """Scenario: Failed collection commit."""
        self.sync()
        bad = commit_files(self.collection, {"fail": "",
                                             "content.txt": "bad"})
        done = self.sync()
        self.assertEqual(done.returncode, 0)
        self.assertIn("published site is unchanged", done.stdout)
        self.assertEqual(self.page(), "v1 first")
        first = self.server.imports[0]["id"]
        self.assertEqual(len(self.sent()), 2)
        report = self.sent()[1]
        self.assertEqual(set(report), REFUSED_KEYS)
        self.assertEqual(report["outcome"], "refused")
        self.assertEqual((report["commit"], report["trigger"],
                          report["base"]), (bad, "commit", first))
        self.assertIn(FAKE_PROBLEM, report["errors"])
        self.assertTrue(all(": error: " in line
                            for line in report["errors"]), report["errors"])
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertEqual(len(self.sent()), 2)
        commit_files(self.collection, {"fail": None, "content.txt": "ok"})
        self.sync()
        self.assertEqual(self.page(), "v1 ok")
        self.assertEqual(self.sent()[2]["base"], first)

    def test_application_update_is_published(self) -> None:
        self.sync()
        app_v2 = commit_files(self.upstream, {"VERSION": "v2\n"})
        self.sync()
        self.assertEqual(self.page(), "v2 first")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), app_v2)
        self.assertTrue((self.app / ".tools" / "cached").exists())

    def test_broken_application_falls_back(self) -> None:
        self.sync()
        commit_files(self.upstream, {"VERSION": "broken\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        done = self.sync()
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), self.app_v1)
        self.sync()
        self.assertEqual(self.builds(),
                         ["v1 build", "broken build", "v1 build"])
        app_v3 = commit_files(self.upstream, {"VERSION": "v3\n"})
        self.sync()
        self.assertEqual(self.page(), "v3 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), app_v3)

    def test_application_needing_new_image_is_not_used(self) -> None:
        self.sync()
        commit_files(self.upstream, {"VERSION": "v2\n",
                                     "deploy/docker/Dockerfile": "FROM x\n"})
        done = self.sync()
        self.assertIn("needs a new image", done.stdout)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), self.app_v1)
        self.assertEqual(self.builds(), ["v1 build"])

    def test_application_updates_can_be_turned_off(self) -> None:
        self.sync()
        commit_files(self.upstream, {"VERSION": "v2\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync(ORGSYNDB_APP_UPDATE="false")
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), self.app_v1)

    def test_application_ref_selects_branch(self) -> None:
        git(self.upstream, "checkout", "--quiet", "-b", "stable")
        commit_files(self.upstream, {"VERSION": "stable\n"})
        git(self.upstream, "checkout", "--quiet", "main")
        commit_files(self.upstream, {"VERSION": "main\n"})
        self.sync(ORGSYNDB_APP_REF="stable")
        self.assertEqual(self.page(), "stable first")

    def test_collection_ref_and_path(self) -> None:
        git(self.collection, "checkout", "--quiet", "-b", "release")
        commit_files(self.collection, {
            "lab/orgsyndb.toml": "format = 1\n",
            "lab/content.txt": "nested\n"})
        done = self.sync(ORGSYNDB_COLLECTION_REF="release",
                         ORGSYNDB_COLLECTION_PATH="lab")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 nested")

    def test_missing_settings_file_is_reported(self) -> None:
        done = self.sync(ORGSYNDB_COLLECTION_PATH="nowhere")
        self.assertIn("ORGSYNDB_COLLECTION_PATH", done.stdout)
        self.assertFalse((self.data / "current").exists())
        self.assertEqual(self.builds(), [])
        self.assertEqual(self.sent(), [])

    def test_pdf_is_published(self) -> None:
        self.sync(ORGSYNDB_PDF="true")
        self.assertEqual(self.builds(), ["v1 pdf"])
        self.assertTrue((self.data / "current" / "pdf" / "a.pdf").is_file())

    def test_unreachable_collection_keeps_site(self) -> None:
        self.sync()
        done = self.sync(ORGSYNDB_COLLECTION_REPO=str(self.tmp / "gone"))
        self.assertEqual(done.returncode, 0)
        self.assertIn("cannot fetch the collection", done.stdout)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(self.builds(), ["v1 build"])

    def test_collection_repo_is_required(self) -> None:
        env = dict(self.env)
        del env["ORGSYNDB_COLLECTION_REPO"]
        done = subprocess.run([sys.executable, str(UPDATER), "sync"],
                              env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("ORGSYNDB_COLLECTION_REPO", done.stderr)

    def test_bad_settings_are_errors(self) -> None:
        for name, value in (("ORGSYNDB_INTERVAL", "soon"),
                            ("ORGSYNDB_PDF", "maybe"),
                            ("ORGSYNDB_COLLECTION_PATH", "../x")):
            with self.subTest(name=name):
                done = self.sync(**{name: value})
                self.assertEqual(done.returncode, 1)
                self.assertIn(name, done.stderr)

    def test_status_prints_state(self) -> None:
        self.sync()
        done = subprocess.run([sys.executable, str(UPDATER), "status"],
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(json.loads(done.stdout)["deployed"]["collection"],
                         self.col_v1)

    def test_retry_forgets_failed_builds(self) -> None:
        self.sync()
        commit_files(self.collection, {"fail": ""})
        self.sync()
        (self.collection / "fail").unlink()  # not committed: still fails
        done = subprocess.run([sys.executable, str(UPDATER), "retry"],
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.state()["failed"], [])
        self.sync()
        self.assertEqual(self.builds(), ["v1 build"] * 3)

    def test_no_index_is_run_and_no_release_holds_one(self) -> None:
        """Requirement: Releases (no `index.json` in a release)."""
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse((self.data / "current" / "index.json").exists())
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        self.assertEqual(len(self.releases()), 2)
        for release in self.releases():
            with self.subTest(release=release):
                self.assertFalse(
                    (self.data / "releases" / release
                     / "index.json").exists())
                self.assertTrue(
                    (self.data / "releases" / release / "public"
                     / "index.html").is_file())
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertNotIn("index", [run[0] for run in self.runs()])

    def test_the_index_is_never_run(self) -> None:
        """Requirement: Update cycle (the cycle runs `build` or `pdf`,
        then `manifest`, and no `index`)."""
        self.sync()
        commit_files(self.collection, {"fail": "", "content.txt": "bad\n"})
        self.sync()
        commit_files(self.collection, {"fail": None,
                                       "content.txt": "ok\n"})
        self.sync(ORGSYNDB_PDF="true")
        commands = [run[0] for run in self.runs()]
        self.assertTrue(commands)
        self.assertNotIn("index", commands)
        self.assertLessEqual(set(commands), {"build", "pdf", "manifest"})

    def test_application_whose_manifest_fails_falls_back(self) -> None:
        """Scenario: New application whose manifest fails."""
        self.sync()
        commit_files(self.upstream, {"VERSION": "manifest-broken\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), self.app_v1)
        self.assertEqual(self.state()["deployed"]["app"], self.app_v1)
        self.assertEqual(len(self.releases()), 2)
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "manifest-broken build",
                                         "v1 build"])
        app_v3 = commit_files(self.upstream, {"VERSION": "v3\n"})
        self.sync()
        self.assertEqual(self.page(), "v3 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), app_v3)

    def test_usage_error(self) -> None:
        done = subprocess.run([sys.executable, str(UPDATER), "frobnicate"],
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr)

    # --- the registry (container-deployment "Update cycle") -------------

    def runs(self) -> list[list[str]]:
        """Each run of the fake tool: its command, the value of
        ``ORGSYNDB_REGISTRY`` and the text of the file that names."""
        if not self.registry_log.exists():
            return []
        return [json.loads(line)
                for line in self.registry_log.read_text().splitlines()]

    def change_registry(self, note: str = "changed") -> str:
        """Make the served snapshot another one, whose first substance
        has the note ``note``; return its digest."""
        table = {**self.snapshot, "substances": list(
            self.snapshot["substances"])}
        table["substances"][0] = {**table["substances"][0], "note": note}
        table["digest"] = snapshot_digest(table)
        self.server.table = table
        return table["digest"]

    def test_the_snapshot_is_kept(self) -> None:
        """Requirement: Update cycle (the snapshot goes to
        `<data>/registry.json`; no address is kept)."""
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(
            plain(json.loads((self.data / "registry.json").read_text())),
            self.snapshot)
        self.assertFalse((self.data / "registry.source").exists())

    def test_every_run_of_the_tools_names_the_snapshot_file(self) -> None:
        """Scenario: First publish (every `tools/orgsyndb` run has
        `ORGSYNDB_REGISTRY` naming the file)."""
        done = self.sync(ORGSYNDB_REGISTRY="http://elsewhere.invalid/x")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        runs = self.runs()
        self.assertEqual([r[0] for r in runs], ["build", "manifest"])
        for command, named, held in runs:
            with self.subTest(command=command):
                self.assertEqual(Path(named),
                                 self.data / "registry.json")
                self.assertEqual(plain(json.loads(held)), self.snapshot)

    def test_the_pdf_run_names_the_snapshot_file(self) -> None:
        """Requirement: Update cycle (`pdf` runs too)."""
        self.sync(ORGSYNDB_PDF="true")
        for command, named, _ in self.runs():
            self.assertEqual(Path(named), self.data / "registry.json",
                             command)

    def test_the_build_fetches_nothing_itself(self) -> None:
        """Requirement: Update cycle (the cycle fetches once)."""
        self.sync()
        self.assertEqual(len(self.server.hosts), 1)

    def test_a_changed_registry_is_published_like_a_new_commit(self) -> None:
        """Scenario: Registry change."""
        self.sync()
        first = self.snapshot["digest"]
        second = self.change_registry()
        self.assertNotEqual(first, second)
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.releases()), 2)
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertEqual(
            json.loads(self.runs()[-1][2])["digest"], second)
        self.assertEqual(self.state()["deployed"]["registry"], second)
        self.assertEqual(len(self.sent()), 2)
        self.assertEqual(self.sent()[1]["trigger"], "registry")
        self.assertEqual(self.sent()[1]["snapshot"], second)
        self.assertEqual(self.sent()[1]["base"],
                         self.server.imports[0]["id"])

    def test_an_unchanged_registry_is_not_rebuilt(self) -> None:
        """Requirement: Update cycle (the digest is part of every
        combination)."""
        self.sync()
        self.sync()
        self.assertEqual(self.builds(), ["v1 build"])
        self.assertEqual(len(self.releases()), 1)

    def test_the_host_of_the_request(self) -> None:
        """Scenario: Host of the request."""
        for allowed, host in (("lab.example.org,localhost",
                               "lab.example.org"),
                              ("*", "localhost"),
                              (".example.org", "example.org"),
                              ("*,lab.example.org", "lab.example.org")):
            with self.subTest(allowed=allowed):
                before = len(self.server.hosts)
                done = self.sync(ORGSYNDB_ALLOWED_HOSTS=allowed)
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertEqual(self.server.hosts[before:], [host])

    def test_without_allowed_hosts_the_host_is_localhost(self) -> None:
        """Requirement: Update cycle (`localhost` when there is
        none)."""
        self.sync()
        self.assertEqual(self.server.hosts, ["localhost"])

    def test_the_default_address_of_the_snapshot(self) -> None:
        """Requirement: Updater program (`ORGSYNDB_REGISTRY_URL`,
        default `http://app:8000/lab/registry/snapshot.json`)."""
        self.assertIn("http://app:8000/lab/registry/snapshot.json",
                      UPDATER.read_text(encoding="utf-8"))
        self.assertIn("ORGSYNDB_ALLOWED_HOSTS",
                      UPDATER.read_text(encoding="utf-8"))

    def test_an_unreachable_registry_builds_nothing(self) -> None:
        """Scenario: Registry unreachable (after a publish)."""
        self.sync()
        commit_files(self.collection, {"content.txt": "second\n"})
        for how in ("another address", "stopped"):
            with self.subTest(how=how):
                env = {}
                if how == "stopped":
                    self.server.stop()
                else:
                    env["ORGSYNDB_REGISTRY_URL"] = closed_address()
                done = self.sync(**env)
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertIn("cannot fetch the registry", done.stdout)
                self.assertEqual(self.page(), "v1 first")
                self.assertEqual(self.builds(), ["v1 build"])
                self.assertEqual(len(self.releases()), 1)
                self.assertEqual(len(self.sent()), 1)

    def test_an_answer_that_is_no_snapshot_builds_nothing(self) -> None:
        """Requirement: Update cycle (a status other than 200, or a body
        that is no snapshot, is a failure, and builds nothing)."""
        self.sync()
        commit_files(self.collection, {"content.txt": "second\n"})
        vocabularies = {**self.snapshot["vocabularies"],
                        "projects": [{"key": 1}]}
        malformed = [json.dumps({**self.snapshot, "import": None,
                                 **change}).encode()
                     for change in ({"substances": ["bad"]},
                                    {"vocabularies": vocabularies},
                                    {"import": "accepted"},
                                    {"import": {"id": "one"}})]
        for status, body in ((200, b'{"format": 2}'), (200, b"not json"),
                             (500, None), (404, b"{}"),
                             *((200, body) for body in malformed)):
            with self.subTest(status=status, body=body):
                self.server.status, self.server.body = status, body
                done = self.sync()
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertIn("cannot fetch the registry", done.stdout)
                self.assertEqual(self.page(), "v1 first")
                self.assertEqual(self.builds(), ["v1 build"])
                self.assertEqual(
                    plain(json.loads(
                        (self.data / "registry.json").read_text())),
                    self.snapshot)

    def test_a_relative_data_directory_names_the_snapshot_absolutely(
            self) -> None:
        """Requirement: Update cycle (every run of `tools/orgsyndb` has
        `ORGSYNDB_REGISTRY` naming `<data>/registry.json`)."""
        done = subprocess.run(
            [sys.executable, str(UPDATER), "sync"],
            env={**self.env, "ORGSYNDB_DATA": "data"}, cwd=self.tmp,
            capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for _, registry, held in self.runs():
            self.assertEqual(registry, str(self.data / "registry.json"))
            self.assertEqual(plain(json.loads(held)), self.snapshot)

    def test_a_fresh_data_directory_without_a_registry_builds_nothing(
            self) -> None:
        """Scenario: Registry unreachable (no copy)."""
        done = self.sync(ORGSYNDB_REGISTRY_URL=closed_address())
        self.assertIn("cannot fetch the registry", done.stdout)
        self.assertEqual(self.builds(), [])
        self.assertFalse((self.data / "current").exists())

    # --- the manifest and the application (container-deployment
    # "Manifests", "Update cycle", "Releases") ----------------------------

    def refused_reports(self) -> list[dict]:
        """The manifests that report a failed build."""
        return [m for m in self.sent() if m["outcome"] == "refused"]

    def test_the_default_address_of_the_manifest(self) -> None:
        """Requirement: Updater program (`ORGSYNDB_MANIFEST_URL`,
        default `http://app:8000/lab/collection/manifest/`)."""
        text = UPDATER.read_text(encoding="utf-8")
        self.assertIn("http://app:8000/lab/collection/manifest/", text)
        self.assertIn("ORGSYNDB_MANIFEST_URL", text)
        self.assertIn("ORGSYNDB_BUILDER_TOKEN", text)

    def test_no_token_builds_nothing(self) -> None:
        """Scenario: No token."""
        for value in ("", None):
            with self.subTest(value=value):
                env = {k: v for k, v in self.env.items()
                       if k != "ORGSYNDB_BUILDER_TOKEN"}
                if value is not None:
                    env["ORGSYNDB_BUILDER_TOKEN"] = value
                done = subprocess.run(
                    [sys.executable, str(UPDATER), "sync"], env=env,
                    capture_output=True, text=True, timeout=120)
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertIn("ORGSYNDB_BUILDER_TOKEN", done.stdout)
                self.assertEqual(self.builds(), [])
                self.assertEqual(self.sent(), [])
                self.assertFalse((self.data / "current").exists())

    def test_what_a_manifest_holds(self) -> None:
        """Scenario: What a manifest holds."""
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (received,) = self.server.manifests
        body = received.body
        self.assertEqual(set(body), BUILT_KEYS)
        self.assertEqual(body["format"], 1)
        uuid.UUID(body["build"])
        self.assertEqual(body["commit"], self.col_v1)
        sent = datetime.fromisoformat(body["committed_at"])
        self.assertIsNotNone(sent.utcoffset())
        self.assertEqual(sent, datetime.fromisoformat(git(
            self.collection, "log", "-1", "--format=%cI", self.col_v1)))
        self.assertEqual(body["snapshot"], self.snapshot["digest"])
        self.assertEqual(body["tooling"], self.app_v1)
        self.assertIsNone(body["base"])
        self.assertIsNone(body["pusher"])
        self.assertEqual(body["trigger"], "catch-up")
        self.assertEqual(body["outcome"], "built")
        self.assertEqual(body["release"], self.current())
        for key in ("language", "procedures", "sequences", "deleted"):
            with self.subTest(key=key):
                self.assertEqual(body[key], FAKE_MANIFEST[key])
        self.assertEqual(received.headers["authorization"],
                         f"Bearer {TOKEN}")
        self.assertTrue(received.headers["content-type"].startswith(
            "application/json"), received.headers)
        self.assertEqual(received.host, "localhost")

    def test_the_manifest_has_the_host_of_the_snapshot_request(self) -> None:
        """Requirement: Manifests (the `Host` header of the snapshot
        request)."""
        self.sync(ORGSYNDB_ALLOWED_HOSTS="lab.example.org,localhost")
        self.assertEqual(self.server.hosts, ["lab.example.org"])
        self.assertEqual([m.host for m in self.server.manifests],
                         ["lab.example.org"])

    def test_the_tools_run_in_order(self) -> None:
        """Requirement: Releases (`manifest` runs after the build)."""
        self.sync()
        self.assertEqual([run[0] for run in self.runs()],
                         ["build", "manifest"])

    def test_a_release_is_staged_before_its_manifest_is_sent(self) -> None:
        """Requirement: Releases (`current` moves only once the
        application accepts)."""
        seen = []

        def look(body: dict) -> None:
            release = self.data / "releases" / body["release"]
            seen.append((
                (release / "public" / "index.html").is_file(),
                (release / "index.json").exists(), self.current()))

        self.server.on_manifest = look
        self.sync()
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        names = [m["release"] for m in self.sent()]
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(seen, [(True, False, None),
                                (True, False, names[0])])
        self.assertEqual(self.current(), names[1])

    def test_first_publish_sends_one_manifest(self) -> None:
        """Scenario: First publish."""
        self.sync()
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(self.sent()[0]["trigger"], "catch-up")

    def test_nothing_new_sends_nothing(self) -> None:
        """Scenario: Nothing new."""
        self.sync()
        self.sync()
        self.assertEqual(self.builds(), ["v1 build"])
        self.assertEqual(len(self.releases()), 1)
        self.assertEqual(len(self.sent()), 1)

    def test_a_new_collection_commit_names_its_base(self) -> None:
        """Scenario: New collection commit."""
        self.sync()
        col_v2 = commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        first, second = self.sent()
        self.assertEqual((second["trigger"], second["commit"]),
                         ("commit", col_v2))
        self.assertEqual(second["base"], self.server.imports[0]["id"])
        self.assertNotEqual(second["build"], first["build"])

    def test_an_application_update_triggers_a_build(self) -> None:
        """Scenario: Application update triggers a build."""
        self.sync()
        app_v2 = commit_files(self.upstream, {"VERSION": "v2\n"})
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "v2 build"])
        second = self.sent()[1]
        self.assertEqual((second["trigger"], second["tooling"]),
                         ("tooling", app_v2))
        self.assertEqual(second["base"], self.server.imports[0]["id"])

    def test_the_trigger_names_the_first_change(self) -> None:
        """Requirement: Manifests (`commit`, else `registry`, else
        `tooling`, else `catch-up`)."""
        self.sync()
        commit_files(self.upstream, {"VERSION": "v2\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        self.change_registry()
        self.sync()
        commit_files(self.upstream, {"VERSION": "v3\n"})
        self.change_registry("again")
        self.sync()
        commit_files(self.upstream, {"VERSION": "v4\n"})
        self.sync()
        self.assertEqual([m["trigger"] for m in self.sent()],
                         ["catch-up", "commit", "registry", "tooling"])
        self.assertEqual(self.page(), "v4 second")

    def test_a_missing_release_is_built_again_as_a_catch_up(self) -> None:
        """Requirement: Update cycle (a build whose release is missing)."""
        self.sync()
        shutil.rmtree(self.data / "releases" / self.current())
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        second = self.sent()[1]
        self.assertEqual(second["trigger"], "catch-up")
        self.assertEqual(second["base"], self.server.imports[0]["id"])
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(self.current(), second["release"])

    def test_the_accepted_release_comes_back(self) -> None:
        """Scenario: The accepted release comes back."""
        self.sync()
        first = self.current()
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        second = self.current()
        self.assertNotEqual(first, second)
        link = self.data / "current"
        link.unlink()
        link.symlink_to(Path("releases") / first)
        for lost in ("pointing elsewhere", "missing"):
            with self.subTest(lost=lost):
                if lost == "missing":
                    link.unlink()
                done = self.sync()
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertEqual(self.current(), second)
                self.assertEqual(self.builds(), ["v1 build", "v1 build"])
                self.assertEqual(len(self.sent()), 2)
                self.assertEqual(self.page(), "v1 second")

    def test_a_refused_build_is_not_published(self) -> None:
        """Scenario: Refused by the application."""
        self.sync()
        bad = commit_files(self.collection, {"content.txt": "second\n"})
        self.server.answer("refuse")
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(len(self.releases()), 1)
        state = self.state()
        self.assertEqual(len(state["failed"]), 1)
        self.assertIn(bad, state["failed"][0])
        self.assertEqual(state["deployed"]["collection"], self.col_v1)
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertEqual(len(self.sent()), 2)

    def test_a_stale_manifest_is_built_again(self) -> None:
        """Scenario: Stale."""
        self.server.answer("stale")
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse((self.data / "current").exists())
        self.assertEqual(self.releases(), [])
        self.assertEqual(self.state()["failed"], [])
        self.assertEqual(self.server.imports, [])
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertEqual(self.page(), "v1 first")
        first, second = self.sent()
        self.assertNotEqual(first["build"], second["build"])
        self.assertEqual(len(self.server.hosts), 2)

    def test_a_manifest_that_gets_no_answer_keeps_its_release(self) -> None:
        """Scenario: Application unreachable."""
        for how in ("closed address", "no answer", "another status"):
            with self.subTest(how=how):
                shutil.rmtree(self.data, ignore_errors=True)
                self.server.rules.clear()
                self.server.manifests.clear()
                env = {}
                if how == "closed address":
                    env["ORGSYNDB_MANIFEST_URL"] = closed_manifest_address()
                elif how == "no answer":
                    self.server.answer("drop")
                else:
                    self.server.answer(500)
                done = self.sync(**env)
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertIn("cannot send the manifest", done.stdout)
                self.assertFalse((self.data / "current").exists())
                self.assertEqual(self.state()["failed"], [])
                self.assertEqual(len(self.releases()), 1)

    def test_lost_answers_keep_one_staged_release(self) -> None:
        """Requirement: Releases (a staged release whose answer is lost
        is kept for a later cycle; pruning removes it like any other)."""
        self.server.answer(500, 500, 500)
        for _ in range(3):
            done = self.sync(ORGSYNDB_KEEP_RELEASES="0")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("cannot send the manifest", done.stdout)
            self.assertEqual(len(self.releases()), 1)
        newest = self.releases()[0]
        done = self.sync(ORGSYNDB_KEEP_RELEASES="0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn(newest, self.releases())
        self.assertEqual(len(self.releases()), 1)
        self.assertTrue((self.data / "current").is_dir())

    def test_a_wrong_token_is_an_answer_that_publishes_nothing(
            self) -> None:
        """Requirement: Manifests (any other answer: log it, record
        nothing)."""
        done = self.sync(ORGSYNDB_BUILDER_TOKEN="another-token")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("cannot send the manifest", done.stdout)
        self.assertFalse((self.data / "current").exists())
        self.assertEqual(self.state()["failed"], [])
        self.assertEqual(self.server.imports, [])

    def test_an_accepted_answer_that_is_lost(self) -> None:
        """Scenario: Accepted, answer lost."""
        self.sync()
        commit_files(self.collection, {"content.txt": "second\n"})
        self.server.answer("accept-drop")
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("cannot send the manifest", done.stdout)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(self.state()["failed"], [])
        self.assertEqual(len(self.releases()), 2)
        staged = self.server.imported["release"]
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.current(), staged)
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        self.assertEqual(len(self.sent()), 2)

    def test_a_failed_build_is_reported_late(self) -> None:
        """Scenario: A failed build reported late."""
        self.sync()
        bad = commit_files(self.collection, {"fail": "",
                                             "content.txt": "bad"})
        done = self.sync(ORGSYNDB_MANIFEST_URL=closed_manifest_address())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("cannot send the manifest", done.stdout)
        self.assertEqual(self.state()["failed"], [])
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.builds(), ["v1 build"] * 3)
        (report,) = self.refused_reports()
        self.assertEqual(report["commit"], bad)
        state = self.state()
        self.assertEqual(len(state["failed"]), 1)
        self.assertIn(bad, state["failed"][0])
        self.sync()
        self.assertEqual(self.builds(), ["v1 build"] * 3)

    def test_a_report_answered_by_another_status_is_not_recorded(
            self) -> None:
        """Requirement: Manifests (a failed build is recorded as failed
        once the application answered its report with 200)."""
        self.sync()
        commit_files(self.collection, {"fail": "", "content.txt": "bad"})
        self.server.answer(500)
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("cannot send the manifest", done.stdout)
        self.assertEqual(self.state()["failed"], [])
        self.sync()
        self.assertEqual(self.builds(), ["v1 build"] * 3)
        self.assertEqual(len(self.state()["failed"]), 1)

    def test_a_failure_without_error_lines_is_reported(self) -> None:
        """Requirement: Manifests (`errors` is the failure message when
        the output has no `: error: ` line)."""
        self.sync()
        commit_files(self.collection, {"fail-silent": "",
                                       "content.txt": "bad"})
        self.sync()
        (report,) = self.refused_reports()
        self.assertTrue(report["errors"])
        self.assertTrue(all(isinstance(line, str) and line
                            for line in report["errors"]), report["errors"])
        self.assertEqual(len(self.state()["failed"]), 1)

    def test_a_failing_manifest_is_a_failed_build(self) -> None:
        """Scenario: Failing manifest."""
        self.sync()
        for marker in ("manifest-fail",):
            with self.subTest(marker=marker):
                bad = commit_files(self.collection, {
                    marker: "", "content.txt": marker})
                before = len(self.sent())
                page, releases = self.page(), self.releases()
                done = self.sync()
                self.assertEqual(done.returncode, 0,
                                 done.stdout + done.stderr)
                self.assertEqual(self.page(), page)
                self.assertEqual(self.releases(), releases)
                (report,) = self.sent()[before:]
                self.assertEqual((report["outcome"], report["commit"]),
                                 ("refused", bad))
                self.assertTrue(report["errors"])
                self.assertIn(bad, self.state()["failed"][-1])
                commit_files(self.collection, {marker: None})
                self.sync()

    @unittest.skipUnless(os.environ.get("OSDB_SLOW_TESTS"),
                         "set OSDB_SLOW_TESTS: waits out the 60-second "
                         "minimum of ORGSYNDB_BUILD_TIMEOUT")
    def test_a_manifest_past_the_timeout_is_a_failed_build(self) -> None:
        """Scenario: Failing manifest (timeout)."""
        self.sync()
        commit_files(self.collection, {"manifest-slow": "",
                                       "content.txt": "slow\n"})
        done = self.sync(ORGSYNDB_BUILD_TIMEOUT="60")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(len(self.refused_reports()), 1)
        self.assertEqual(len(self.state()["failed"]), 1)

    def test_a_failed_application_build_is_reported_before_the_fallback(
            self) -> None:
        """Scenario: Broken application (the broken build is
        reported)."""
        self.sync()
        commit_files(self.upstream, {"VERSION": "broken\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        self.assertEqual([m["outcome"] for m in self.sent()],
                         ["built", "refused", "built"])
        broken = self.sent()[1]
        self.assertIn(FAKE_PROBLEM, broken["errors"])
        self.assertEqual(self.sent()[2]["tooling"], self.app_v1)
        self.assertEqual(self.page(), "v1 second")

    # --- the pusher (container-deployment "Push log") --------------------

    OTHER = "1" * 40

    @staticmethod
    def push_line(commit: str, name: str = "jkoch", ident: str = "7",
                  time: str = "2026-11-14T09:30:00Z") -> str:
        """A line of the push log."""
        return f"{time} {commit} {ident} {name}"

    def write_push_log(self, *lines: str | bytes) -> None:
        self.push_log.write_bytes(b"".join(
            (line if isinstance(line, bytes) else line.encode()) + b"\n"
            for line in lines))

    def first_pusher(self, *lines: str | bytes, **extra: str) -> object:
        """Write the push log with ``lines``, unless there are none, run
        ``sync``, and return the ``pusher`` of the manifest it sent."""
        if lines:
            self.write_push_log(*lines)
        done = self.sync(**extra)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (first,) = self.sent()
        self.assertIn("pusher", first)
        return first["pusher"]

    def test_the_pusher_is_the_last_line_naming_the_commit(self) -> None:
        """Scenario: The pusher of a build (`jkoch`, then `abauer`)."""
        self.assertEqual(self.first_pusher(
            self.push_line(self.col_v1, "jkoch", "7"),
            self.push_line(self.OTHER, "mmeier", "9"),
            self.push_line(self.col_v1, "abauer", "8")), "abauer")

    def test_a_line_for_another_commit_names_no_pusher(self) -> None:
        """Scenario: The pusher of a build (no line naming the
        commit)."""
        self.assertIsNone(self.first_pusher(
            self.push_line(self.OTHER, "jkoch")))

    def test_no_log_gives_no_pusher(self) -> None:
        """Scenario: The pusher of a build (no log)."""
        self.assertFalse(self.push_log.exists())
        self.assertIsNone(self.first_pusher())
        self.assertEqual(self.builds(), ["v1 build"])

    def test_an_empty_log_gives_no_pusher(self) -> None:
        """Requirement: Push log (no line names the commit)."""
        self.push_log.write_bytes(b"")
        self.assertIsNone(self.first_pusher())

    def test_a_dash_is_no_pusher(self) -> None:
        """Requirement: Push log (that line's name is `-`): the last
        line decides, though an earlier one named someone."""
        self.assertIsNone(self.first_pusher(
            self.push_line(self.col_v1, "jkoch", "7"),
            self.push_line(self.col_v1, "-", "-")))

    def test_the_name_counts_without_the_id(self) -> None:
        """Requirement: Push log (the name of the last line, whatever
        its id)."""
        self.assertEqual(self.first_pusher(
            self.push_line(self.col_v1, "jkoch", "-")), "jkoch")

    def test_a_line_that_cannot_be_read_is_skipped(self) -> None:
        """Requirement: Push log (a line it cannot read is skipped)."""
        self.assertEqual(self.first_pusher(
            b"not a line of the push log",
            b"\xff\xfe\xfd",
            b"",
            self.push_line(self.col_v1, "jkoch"),
            b"\xff\xfe \xfd",
            self.push_line(self.col_v1, "abauer").encode()[:20]),
            "jkoch")

    def test_a_line_appended_during_the_build_is_used(self) -> None:
        """Scenario: A line appended during the build."""
        self.assertFalse(self.push_log.exists())
        self.assertEqual(self.first_pusher(
            FAKE_PUSH_LINE=self.push_line(self.col_v1, "jkoch")), "jkoch")

    def test_a_line_appended_during_the_build_is_the_last(self) -> None:
        """Requirement: Push log (the log is read after the build's
        commands have run)."""
        self.assertEqual(self.first_pusher(
            self.push_line(self.col_v1, "abauer", "8"),
            FAKE_PUSH_LINE=self.push_line(self.col_v1, "jkoch")), "jkoch")

    def test_a_failed_build_names_its_pusher(self) -> None:
        """Requirement: Manifests (`pusher` of every build, a failed one
        too)."""
        self.sync()
        bad = commit_files(self.collection, {"fail": "",
                                             "content.txt": "bad"})
        self.write_push_log(self.push_line(bad, "abauer", "8"))
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (report,) = self.refused_reports()
        self.assertEqual(report["pusher"], "abauer")
        self.assertIsNone(self.sent()[0]["pusher"])

    def test_a_registry_build_keeps_the_commits_pusher(self) -> None:
        """Scenario: The pusher of a registry build."""
        self.write_push_log(self.push_line(self.col_v1, "jkoch"))
        self.sync()
        self.assertEqual(self.sent()[0]["pusher"], "jkoch")
        self.change_registry()
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.sent()), 2)
        self.assertEqual(self.sent()[1]["trigger"], "registry")
        self.assertEqual(self.sent()[1]["pusher"], "jkoch")

    def test_a_tooling_build_keeps_the_commits_pusher(self) -> None:
        """Requirement: Manifests (the pusher belongs to the commit)."""
        self.write_push_log(self.push_line(self.col_v1, "jkoch"))
        self.sync()
        commit_files(self.upstream, {"VERSION": "v2\n"})
        self.sync()
        self.assertEqual(self.sent()[1]["trigger"], "tooling")
        self.assertEqual(self.sent()[1]["pusher"], "jkoch")

    def test_a_line_appended_after_the_manifest_is_not_used(self) -> None:
        """Requirement: Push log (a line appended after the manifest was
        made is not used; the next import of the commit names it)."""
        self.sync()
        self.assertIsNone(self.sent()[0]["pusher"])
        self.write_push_log(self.push_line(self.col_v1, "jkoch"))
        self.sync()
        self.assertEqual(len(self.sent()), 1)
        self.change_registry()
        self.sync()
        self.assertEqual(len(self.sent()), 2)
        self.assertIsNone(self.sent()[0]["pusher"])
        self.assertEqual(self.sent()[1]["pusher"], "jkoch")

    def test_each_commit_has_its_own_pusher(self) -> None:
        """Requirement: Push log (the last line whose commit is C)."""
        self.write_push_log(self.push_line(self.col_v1, "jkoch"))
        self.sync()
        second = commit_files(self.collection, {"content.txt": "second\n"})
        self.write_push_log(self.push_line(self.col_v1, "jkoch"),
                            self.push_line(second, "abauer", "8"))
        self.sync()
        self.assertEqual([m["pusher"] for m in self.sent()],
                         ["jkoch", "abauer"])

    def test_the_program_names_the_push_log_and_its_default(self) -> None:
        """Requirement: Updater program (`ORGSYNDB_PUSH_LOG`, default
        `/var/lib/orgsyndb-pushes/pushes.log`)."""
        text = UPDATER.read_text(encoding="utf-8")
        self.assertIn("ORGSYNDB_PUSH_LOG", text)
        self.assertIn("/var/lib/orgsyndb-pushes/pushes.log", text)


class FileTests(unittest.TestCase):

    def test_updater_is_stdlib_python(self) -> None:
        self.assertTrue(os.access(UPDATER, os.X_OK))
        self.assertTrue(UPDATER.read_text().startswith(
            "#!/usr/bin/env python3\n"))
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(UPDATER), cfile=f"{tmp}/x.pyc",
                               doraise=True)
        modules = set()
        for node in ast.walk(ast.parse(UPDATER.read_text())):
            if isinstance(node, ast.Import):
                modules |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module.split(".")[0])
        self.assertLessEqual(modules, set(sys.stdlib_module_names))

    def test_image_directory_holds_only_image_inputs(self) -> None:
        self.assertEqual(sorted(p.name for p in DOCKER.iterdir()),
                         ["Caddyfile", "Dockerfile", "orgsyndb-deploy"])

    def test_dockerfile(self) -> None:
        text = (DOCKER / "Dockerfile").read_text()
        self.assertIn("FROM fedora:44", text)
        for tool in ("python3", "hugo", "weasyprint", "emacs-nox", "git",
                     "caddy"):
            self.assertIn(tool, text)
        self.assertIn("HEAD:deploy/docker", text)
        self.assertIn("USER orgsyndb", text)

    def test_caddyfile(self) -> None:
        text = (DOCKER / "Caddyfile").read_text()
        self.assertIn("/var/lib/orgsyndb/current/public", text)
        self.assertRegex(
            text, r'header\s+(@\S+\s+)?Cache-Control\s+"no-cache"')
        if shutil.which("caddy") is None:
            self.skipTest("caddy not found")
        done = subprocess.run(["caddy", "adapt", "--adapter", "caddyfile",
                               "--config", str(DOCKER / "Caddyfile")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_caddyfile_forwards_the_application(self) -> None:
        """Scenario: Caddyfile (application)."""
        text = (DOCKER / "Caddyfile").read_text()
        self.assertIn("/lab/*", text)
        self.assertIn("reverse_proxy", text)
        self.assertIn("ORGSYNDB_APP_UPSTREAM", text)
        self.assertIn("app:8000", text)
        self.assertRegex(text, r"admin\s+off")
        self.assertRegex(
            text, r'header\s+(@\S+\s+)?Cache-Control\s+"no-cache"')
        # The prefix reaches the application unchanged.
        self.assertNotRegex(text, r"handle_path\s+/lab")
        self.assertNotIn("strip_prefix", text)
        if shutil.which("caddy") is None:
            self.skipTest("caddy not found")
        done = subprocess.run(["caddy", "adapt", "--adapter", "caddyfile",
                               "--config", str(DOCKER / "Caddyfile")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("/lab/*", done.stdout)
        self.assertIn("reverse_proxy", done.stdout)

    def test_caddyfile_does_not_forward_the_manifest(self) -> None:
        """Scenario: Caddyfile (`/lab/collection/manifest*` answered
        with `404` ahead of the `/lab/*` route)."""
        text = (DOCKER / "Caddyfile").read_text()
        self.assertRegex(
            text, r"handle\s+/lab/collection/manifest\*\s*\{[^}]*"
                  r"respond[^}\n]*\b404\b")
        self.assertLess(text.index("/lab/collection/manifest*"),
                        text.index("handle /lab/*"))
        if shutil.which("caddy") is None:
            self.skipTest("caddy not found")
        done = subprocess.run(["caddy", "adapt", "--adapter", "caddyfile",
                               "--config", str(DOCKER / "Caddyfile")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("/lab/collection/manifest*", done.stdout)
        self.assertLess(done.stdout.index("/lab/collection/manifest*"),
                        done.stdout.index('"/lab/*"'))
        between = done.stdout[done.stdout.index("/lab/collection/manifest*"):
                              done.stdout.index('"/lab/*"')]
        self.assertRegex(between, r'"status_code":\s*"?404')

    def test_the_builder_links_the_lab(self) -> None:
        """Scenario: Compose file (the builder's ORGSYNDB_LAB, without
        Docker)."""
        text = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        builder = re.search(r"^  builder:\n(.*?)(?=^  \S)", text,
                            re.M | re.S)
        self.assertIsNotNone(builder)
        self.assertRegex(builder.group(1),
                         r"(?m)^      ORGSYNDB_LAB: \"true\"$")

    def test_compose_file(self) -> None:
        """Scenario: Compose file."""
        if shutil.which("docker") is None:
            self.skipTest("docker not found")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "deploy"
            shutil.copytree(DEPLOY, target)
            shutil.copy(target / "orgsyndb.env.example",
                        target / "orgsyndb.env")
            done = subprocess.run(
                ["docker", "compose", "config", "--format", "json"],
                cwd=target, capture_output=True, text=True)
            if done.returncode != 0 and "compose" in done.stderr and (
                    "is not a docker command" in done.stderr):
                self.skipTest("docker compose not found")
            self.assertEqual(done.returncode, 0, done.stderr)
            root = Path(tmp).resolve()
        config = json.loads(done.stdout)
        example = parse_env(ENV_EXAMPLE)
        services = config["services"]
        self.assertEqual(sorted(services),
                         ["app", "backup", "builder", "db", "forge",
                          "forge-db", "web"])
        self.assertEqual(services["builder"]["command"],
                         ["orgsyndb-deploy", "run"])
        self.assertEqual(services["builder"]["environment"][
            "ORGSYNDB_COLLECTION_REF"], "main")
        self.assertEqual(services["builder"]["environment"][
            "ORGSYNDB_LAB"], "true")
        for name in ("web", "app"):
            with self.subTest(service=name):
                mounts = {m["target"]: m for m in services[name]["volumes"]}
                self.assertTrue(mounts["/var/lib/orgsyndb"]["read_only"])
        builder = {m["target"]: m for m in services["builder"]["volumes"]}
        self.assertFalse(builder["/var/lib/orgsyndb"].get("read_only"))

        db = services["db"]
        self.assertEqual(db["image"], "postgres:18")
        self.assertIn("pg_isready", " ".join(db["healthcheck"]["test"]))
        self.assertIn("db", {m.get("source") for m in db["volumes"]
                             if m.get("type") == "volume"})
        for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
            self.assertEqual(db["environment"][key], example[key])

        app = services["app"]
        self.assertEqual(app["depends_on"]["db"]["condition"],
                         "service_healthy")
        self.assertEqual(Path(app["build"]["context"]).resolve(), root)
        self.assertTrue(
            app["build"]["dockerfile"].endswith("deploy/webapp/Dockerfile"))
        self.assertEqual(app["environment"]["ORGSYNDB_DATABASE_URL"],
                         example["ORGSYNDB_DATABASE_URL"])
        self.assertIn("ORGSYNDB_SECRET_KEY", app["environment"])

        backup = services["backup"]
        self.assertEqual(backup["image"], "postgres:18")
        self.assertIn("orgsyndb-backup",
                      " ".join([*_words(backup.get("entrypoint")),
                                *_words(backup.get("command"))]))
        mounts = {m["target"]: m for m in backup["volumes"]}
        self.assertIn("/backups", mounts)
        self.assertTrue(mounts["/backups"]["source"].endswith("/backups"))
        self.assertFalse(mounts["/backups"].get("read_only"))
        script = [m for m in backup["volumes"]
                  if m["source"].rstrip("/").endswith(
                      ("/backup", "/orgsyndb-backup"))]
        self.assertEqual(len(script), 1, backup["volumes"])
        self.assertTrue(script[0]["read_only"])
        for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
            self.assertEqual(backup["environment"][key], example[key])

    def test_env_example_lists_the_application_settings(self) -> None:
        text = ENV_EXAMPLE.read_text()
        env = parse_env(ENV_EXAMPLE)
        for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
                    "ORGSYNDB_DATABASE_URL", "ORGSYNDB_SECRET_KEY",
                    "ORGSYNDB_ALLOWED_HOSTS", "ORGSYNDB_BUILDER_TOKEN"):
            with self.subTest(key=key):
                self.assertIn(key, env)
        url = urlsplit(env["ORGSYNDB_DATABASE_URL"])
        self.assertEqual(url.scheme, "postgres")
        self.assertEqual(url.username, env["POSTGRES_USER"])
        self.assertEqual(url.password, env["POSTGRES_PASSWORD"])
        self.assertEqual(url.hostname, "db")
        self.assertEqual(url.path, "/" + env["POSTGRES_DB"])
        self.assertRegex(text, r"(?i)generat")

    def test_env_example_says_how_to_generate_the_token(self) -> None:
        """Requirement: Web server and Compose file (`orgsyndb.env.example`
        lists `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token)."""
        lines = ENV_EXAMPLE.read_text().splitlines()
        (index,) = [number for number, line in enumerate(lines)
                    if line.startswith("ORGSYNDB_BUILDER_TOKEN=")]
        comment = []
        for line in reversed(lines[:index]):
            if not line.startswith("#"):
                break
            comment.insert(0, line)
        text = "\n".join(comment)
        self.assertRegex(text, r"(?i)generat")
        self.assertRegex(text, r"(?i)token")

    def test_git_ignores_local_deployment_files(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not found")
        for path in ("deploy/orgsyndb.env", "deploy/backups/lab-x.dump",
                     "deploy/backups/anything"):
            with self.subTest(path=path):
                done = subprocess.run(
                    ["git", "-C", str(REPO), "check-ignore", "-q", path])
                self.assertEqual(done.returncode, 0,
                                 f"{path} is not ignored")
        done = subprocess.run(
            ["git", "-C", str(REPO), "check-ignore", "-q",
             "deploy/orgsyndb.env.example"])
        self.assertEqual(done.returncode, 1)

    def test_application_dockerfile(self) -> None:
        """Scenario: Image inputs."""
        self.assertTrue(WEBAPP_DOCKERFILE.is_file(),
                        "deploy/webapp/Dockerfile does not exist")
        text = WEBAPP_DOCKERFILE.read_text()
        for needle in ("FROM fedora:44", "uv sync --frozen --no-dev",
                       "collectstatic", "migrate", "gunicorn",
                       "USER orgsyndb", "orgsyndb_web.wsgi",
                       "0.0.0.0:8000", "EXPOSE 8000", "site/assets/css"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)
        self.assertNotIn("ORGSYNDB_INDEX", text)
        self.assertNotIn("index.json", text)
        self.assertRegex(text, r"(?:--uid[= ]|-u\s*)1000\b")
        self.assertRegex(text, r"(?m)^\s*(COPY|ADD)\s+.*\bwebapp/?\s")
        self.assertIn("demo_data --if-empty", text)
        command = text[text.rindex("CMD"):]
        self.assertLess(command.index("migrate"), command.index("demo_data"))
        self.assertLess(command.index("demo_data"), command.index("gunicorn"))

    def test_env_example_names_the_demo_flag(self) -> None:
        """Scenario: Demo flag in the example settings."""
        text = ENV_EXAMPLE.read_text()
        self.assertIn("#ORGSYNDB_DEMO=false", text.splitlines())
        self.assertNotIn("ORGSYNDB_DEMO", parse_env(ENV_EXAMPLE))

    def test_env_example_names_no_index(self) -> None:
        """Requirement: Application image (no `ORGSYNDB_INDEX` in the
        example settings)."""
        text = ENV_EXAMPLE.read_text()
        self.assertNotIn("ORGSYNDB_INDEX", text)
        self.assertNotIn("index.json", text)


def parse_env(path: Path) -> dict[str, str]:
    """The settings an env file sets, leaving out comments."""
    found = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            found[key.strip()] = value.strip()
    return found


def _words(command: object) -> list[str]:
    if command is None:
        return []
    return [command] if isinstance(command, str) else list(command)


FAKE_PG_DUMP = """\
#!/bin/sh
# Fake pg_dump: records its arguments, PGPASSWORD and the file $PGPASSFILE
# names in $FAKE_PG_LOG, then writes DUMP to the file named by -f or
# --file, or to standard output without one. With $FAKE_PG_FAIL set it
# writes PARTIAL there instead and exits 1.
{
    printf 'PGPASSWORD=%s\\n' "${PGPASSWORD-}"
    if [ -n "${PGPASSFILE-}" ] && [ -f "$PGPASSFILE" ]; then
        cat "$PGPASSFILE"
    fi
    for arg in "$@"; do
        printf 'ARG %s\\n' "$arg"
    done
} >> "$FAKE_PG_LOG"
out=
prev=
for arg in "$@"; do
    case "$prev" in
        -f|--file) out=$arg ;;
    esac
    case "$arg" in
        --file=*) out=${arg#--file=} ;;
        -f?*) out=${arg#-f} ;;
    esac
    prev=$arg
done
if [ -n "${FAKE_PG_FAIL-}" ]; then
    text=PARTIAL
else
    text=DUMP
fi
if [ -n "$out" ]; then
    printf '%s' "$text" > "$out"
else
    printf '%s' "$text"
fi
[ -z "${FAKE_PG_FAIL-}" ]
"""
OLD_DUMPS = [f"lab-202601{day:02d}T030000Z.dump" for day in range(1, 15)]
DUMP_NAME = re.compile(r"^lab-(\d{8}T\d{6}Z)\.dump$")


@unittest.skipIf(shutil.which("sh") is None, "sh not found")
class BackupTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-backup-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        pg_dump = self.bin / "pg_dump"
        pg_dump.write_text(FAKE_PG_DUMP)
        pg_dump.chmod(0o755)
        self.log = self.tmp / "pg_dump.log"
        self.dir = self.tmp / "backups"
        self.dir.mkdir()
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "FAKE_PG_LOG": str(self.log),
            "POSTGRES_USER": "labuser",
            "POSTGRES_PASSWORD": "s3cret",
            "POSTGRES_DB": "labdb",
            "ORGSYNDB_BACKUP_DIR": str(self.dir),
        }

    def fill(self, names: list[str] = OLD_DUMPS) -> None:
        for name in names:
            path = self.dir / name
            path.write_text("old")
            stamp = datetime.strptime(
                DUMP_NAME.match(name).group(1), "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc).timestamp()
            os.utime(path, (stamp, stamp))

    def run_script(self, *args: str, **extra: str
                   ) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", str(BACKUP), *args],
                              env={**self.env, **extra},
                              capture_output=True, text=True, timeout=60)

    def files(self) -> list[str]:
        return sorted(p.name for p in self.dir.iterdir())

    def new_dumps(self) -> list[str]:
        return [n for n in self.files()
                if DUMP_NAME.match(n) and n not in OLD_DUMPS]

    def test_the_script_is_posix_shell(self) -> None:
        self.assertTrue(BACKUP.is_file(),
                        "deploy/backup/orgsyndb-backup does not exist")
        self.assertTrue(os.access(BACKUP, os.X_OK))
        self.assertIn(BACKUP.read_text().splitlines()[0],
                      ("#!/bin/sh", "#!/usr/bin/env sh"))
        for shell in ("sh", "dash"):
            if shutil.which(shell):
                with self.subTest(shell=shell):
                    done = subprocess.run([shell, "-n", str(BACKUP)],
                                          capture_output=True, text=True)
                    self.assertEqual(done.returncode, 0, done.stderr)

    def test_dump_and_pruning(self) -> None:
        """Scenario: Dump and pruning."""
        self.fill()
        before = datetime.now(timezone.utc)
        done = self.run_script("once")
        after = datetime.now(timezone.utc)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        fresh = self.new_dumps()
        self.assertEqual(len(fresh), 1, self.files())
        self.assertEqual((self.dir / fresh[0]).read_text(), "DUMP")
        stamp = datetime.strptime(
            DUMP_NAME.match(fresh[0]).group(1), "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(stamp, before - timedelta(seconds=2))
        self.assertLessEqual(stamp, after + timedelta(seconds=2))
        self.assertEqual(len(self.files()), 14)
        self.assertNotIn(OLD_DUMPS[0], self.files())
        self.assertIn(OLD_DUMPS[1], self.files())

    def test_nothing_but_dumps_is_left_behind(self) -> None:
        self.run_script("once")
        self.assertEqual(len(self.files()), 1)
        self.assertRegex(self.files()[0], DUMP_NAME)

    def test_keep_backups_sets_the_count(self) -> None:
        self.fill()
        (self.dir / "notes.txt").write_text("keep")
        (self.dir / "lab-latest.txt").write_text("keep")
        done = self.run_script("once", ORGSYNDB_KEEP_BACKUPS="3")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        dumps = [n for n in self.files() if DUMP_NAME.match(n)]
        self.assertEqual(dumps, [OLD_DUMPS[-2], OLD_DUMPS[-1],
                                 *self.new_dumps()])
        self.assertEqual(len(dumps), 3)
        self.assertIn("notes.txt", self.files())
        self.assertIn("lab-latest.txt", self.files())

    def test_dump_arguments(self) -> None:
        done = self.run_script("once")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        log = self.log.read_text()
        args = " ".join(line[4:] for line in log.splitlines()
                        if line.startswith("ARG "))
        self.assertRegex(
            args, r"(?:^| )(?:-Fc|-F c|--format[= ]c(?:ustom)?)(?: |$)")
        self.assertRegex(
            args, r"(?:^| )(?:-h ?|--host[= ])db(?: |$)|host=db\b|@db\b")
        self.assertIn("labuser", args)
        self.assertIn("labdb", args)
        self.assertIn("s3cret", log)

    def test_failed_dump(self) -> None:
        """Scenario: Failed dump."""
        self.fill()
        before = self.files()
        done = self.run_script("once", FAKE_PG_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertTrue(done.stderr.startswith("orgsyndb-backup: error:"),
                        done.stderr)
        self.assertEqual(self.files(), before)

    def test_failed_dump_leaves_no_file_in_an_empty_directory(self) -> None:
        done = self.run_script("once", FAKE_PG_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.files(), [])

    def test_unknown_subcommand(self) -> None:
        done = self.run_script("frobnicate")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr.lower())
        self.assertFalse(self.log.exists())
        self.assertEqual(self.files(), [])

    def test_malformed_numbers(self) -> None:
        self.fill()
        for name, value in (("ORGSYNDB_KEEP_BACKUPS", "many"),
                            ("ORGSYNDB_KEEP_BACKUPS", "1.5"),
                            ("ORGSYNDB_KEEP_BACKUPS", "3x")):
            with self.subTest(name=name, value=value):
                done = self.run_script("once", **{name: value})
                self.assertEqual(done.returncode, 1)
                self.assertIn(name, done.stderr)

    def test_malformed_interval(self) -> None:
        for value in ("daily", "2.5", "1h"):
            with self.subTest(value=value):
                done = self.run_script("run", ORGSYNDB_BACKUP_HOURS=value)
                self.assertEqual(done.returncode, 1)
                self.assertIn("ORGSYNDB_BACKUP_HOURS", done.stderr)

    def start(self, *args: str, **extra: str) -> subprocess.Popen:
        out = open(self.tmp / "out.log", "w")
        err = open(self.tmp / "err.log", "w")
        self.addCleanup(out.close)
        self.addCleanup(err.close)
        process = subprocess.Popen(
            ["sh", str(BACKUP), *args], env={**self.env, **extra},
            stdout=out, stderr=err, start_new_session=True)
        self.addCleanup(self.stop, process)
        return process

    def stop(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)

    def wait_for(self, condition, process: subprocess.Popen,
                 seconds: float = 20.0) -> bool:
        """Wait until ``condition`` holds; give up when the script
        exits or the time is up."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return True
            if process.poll() is not None:
                return condition()
            time.sleep(0.1)
        return False

    def output(self) -> str:
        return ((self.tmp / "out.log").read_text()
                + (self.tmp / "err.log").read_text())

    def test_run_dumps_at_once_and_keeps_going(self) -> None:
        process = self.start()
        self.assertTrue(self.wait_for(self.new_dumps, process),
                        self.output())
        self.assertEqual(
            (self.dir / self.new_dumps()[0]).read_text(), "DUMP")
        time.sleep(1)
        self.assertIsNone(process.poll())

    def test_run_logs_a_failed_dump_and_keeps_going(self) -> None:
        process = self.start("run", FAKE_PG_FAIL="1")
        self.assertTrue(self.wait_for(
            lambda: self.output().strip() and not process.poll(), process),
            "nothing was logged")
        time.sleep(1)
        self.assertIsNone(process.poll(), self.output())
        self.assertIn("error", self.output().lower())
        self.assertEqual(self.files(), [])


if __name__ == "__main__":
    unittest.main()
