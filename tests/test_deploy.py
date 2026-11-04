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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy"
DOCKER = DEPLOY / "docker"
UPDATER = DOCKER / "orgsyndb-deploy"
WEBAPP_DOCKERFILE = DEPLOY / "webapp" / "Dockerfile"
BACKUP = DEPLOY / "backup" / "orgsyndb-backup"
ENV_EXAMPLE = DEPLOY / "orgsyndb.env.example"

FAKE_ORGSYNDB = """\
#!/usr/bin/env python3
# Fake tool: -C DIR build|pdf|index. A build fails when the collection
# holds `fail` or the application's VERSION reads `broken`, and appends
# one line per run to $FAKE_LOG. `index` logs nothing and prints a
# minimal index; it fails when the collection holds `index-fail` or
# VERSION reads `index-broken`, and sleeps past any timeout when the
# collection holds `index-slow`.
import os, sys, time
from pathlib import Path
app = Path(__file__).resolve().parent.parent
collection = Path(sys.argv[2])
version = (app / "VERSION").read_text().strip()
if sys.argv[3] == "index":
    if (collection / "index-slow").exists():
        time.sleep(600)
    if (collection / "index-fail").exists() or version == "index-broken":
        sys.exit(1)
    print('{"site_language": "de"}')
    sys.exit(0)
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(f"{version} {sys.argv[3]}\\n")
if (collection / "fail").exists() or version == "broken":
    sys.exit(1)
public = collection / "public"
public.mkdir(exist_ok=True)
text = (collection / "content.txt").read_text().strip()
(public / "index.html").write_text(f"{version} {text}\\n")
if sys.argv[3] == "pdf":
    (collection / "pdf").mkdir(exist_ok=True)
    (collection / "pdf" / "a.pdf").write_text("pdf\\n")
"""


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
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.tmp),
            "GIT_CONFIG_NOSYSTEM": "1",
            "FAKE_LOG": str(self.log),
            "ORGSYNDB_DATA": str(self.data),
            "ORGSYNDB_APP": str(self.app),
            "ORGSYNDB_IMAGE_INFO": str(self.image),
            "ORGSYNDB_COLLECTION_REPO": str(self.collection),
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
        self.sync()
        commit_files(self.collection, {"fail": "", "content.txt": "bad"})
        done = self.sync()
        self.assertEqual(done.returncode, 0)
        self.assertIn("published site is unchanged", done.stdout)
        self.assertEqual(self.page(), "v1 first")
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        commit_files(self.collection, {"fail": None, "content.txt": "ok"})
        self.sync()
        self.assertEqual(self.page(), "v1 ok")

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

    def index_text(self) -> str:
        return (self.data / "current" / "index.json").read_text().strip()

    def test_index_is_in_the_release(self) -> None:
        """Scenario: Index in the release."""
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.index_text(), '{"site_language": "de"}')
        commit_files(self.collection, {"content.txt": "second\n"})
        self.sync()
        for release in self.releases():
            with self.subTest(release=release):
                self.assertTrue(
                    (self.data / "releases" / release
                     / "index.json").is_file())
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])

    def test_failing_index_keeps_site_and_is_not_retried(self) -> None:
        """Scenario: Failing index."""
        self.sync()
        bad = commit_files(self.collection, {"index-fail": "",
                                             "content.txt": "bad\n"})
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(self.index_text(), '{"site_language": "de"}')
        self.assertEqual(len(self.releases()), 1)
        state = self.state()
        self.assertEqual(state["deployed"]["collection"], self.col_v1)
        self.assertEqual(len(state["failed"]), 1)
        self.assertIn(bad, state["failed"][0])
        self.sync()
        self.assertEqual(self.builds(), ["v1 build", "v1 build"])
        commit_files(self.collection, {"index-fail": None,
                                       "content.txt": "ok\n"})
        self.sync()
        self.assertEqual(self.page(), "v1 ok")
        self.assertEqual(self.index_text(), '{"site_language": "de"}')

    def test_first_release_needs_a_working_index(self) -> None:
        commit_files(self.collection, {"index-fail": ""})
        self.sync()
        self.assertFalse((self.data / "current").exists())
        self.assertEqual(len(self.state()["failed"]), 1)

    @unittest.skipUnless(os.environ.get("OSDB_SLOW_TESTS"),
                         "set OSDB_SLOW_TESTS: waits out the 60-second "
                         "minimum of ORGSYNDB_BUILD_TIMEOUT")
    def test_index_past_the_timeout_keeps_site(self) -> None:
        """Scenario: Failing index (timeout)."""
        self.sync()
        commit_files(self.collection, {"index-slow": "",
                                       "content.txt": "slow\n"})
        done = self.sync(ORGSYNDB_BUILD_TIMEOUT="60")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 first")
        self.assertEqual(len(self.releases()), 1)
        self.assertEqual(len(self.state()["failed"]), 1)

    def test_application_whose_index_fails_falls_back(self) -> None:
        """Scenario: New application whose index fails."""
        self.sync()
        commit_files(self.upstream, {"VERSION": "index-broken\n"})
        commit_files(self.collection, {"content.txt": "second\n"})
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.page(), "v1 second")
        self.assertEqual(self.index_text(), '{"site_language": "de"}')
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), self.app_v1)
        self.assertEqual(self.state()["deployed"]["app"], self.app_v1)
        self.assertEqual(len(self.releases()), 2)
        self.sync()
        self.assertEqual(self.builds(),
                         ["v1 build", "index-broken build", "v1 build"])
        app_v3 = commit_files(self.upstream, {"VERSION": "v3\n"})
        self.sync()
        self.assertEqual(self.page(), "v3 second")
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), app_v3)

    def test_usage_error(self) -> None:
        done = subprocess.run([sys.executable, str(UPDATER), "frobnicate"],
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr)


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
        self.assertIn('header Cache-Control "no-cache"', text)
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
        self.assertIn('header Cache-Control "no-cache"', text)
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
                         ["app", "backup", "builder", "db", "web"])
        self.assertEqual(services["builder"]["command"],
                         ["orgsyndb-deploy", "run"])
        self.assertEqual(services["builder"]["environment"][
            "ORGSYNDB_COLLECTION_REF"], "main")
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
                    "ORGSYNDB_ALLOWED_HOSTS"):
            with self.subTest(key=key):
                self.assertIn(key, env)
        url = urlsplit(env["ORGSYNDB_DATABASE_URL"])
        self.assertEqual(url.scheme, "postgres")
        self.assertEqual(url.username, env["POSTGRES_USER"])
        self.assertEqual(url.password, env["POSTGRES_PASSWORD"])
        self.assertEqual(url.hostname, "db")
        self.assertEqual(url.path, "/" + env["POSTGRES_DB"])
        self.assertRegex(text, r"(?i)generat")

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
        self.assertRegex(
            text, r"ORGSYNDB_INDEX[= ]\S*/var/lib/orgsyndb/current/"
                  r"index\.json")
        self.assertRegex(text, r"(?:--uid[= ]|-u\s*)1000\b")
        self.assertRegex(text, r"(?m)^\s*(COPY|ADD)\s+.*\bwebapp/?\s")


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
