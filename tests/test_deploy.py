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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy"
DOCKER = DEPLOY / "docker"
UPDATER = DOCKER / "orgsyndb-deploy"

FAKE_ORGSYNDB = """\
#!/usr/bin/env python3
# Fake build: -C DIR build|pdf. Fails when the collection holds `fail`
# or the application's VERSION reads `broken`; appends one line per run
# to $FAKE_LOG.
import os, sys
from pathlib import Path
app = Path(__file__).resolve().parent.parent
collection = Path(sys.argv[2])
version = (app / "VERSION").read_text().strip()
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

    def test_compose_file(self) -> None:
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
        config = json.loads(done.stdout)
        services = config["services"]
        self.assertEqual(sorted(services), ["builder", "web"])
        self.assertEqual(services["builder"]["command"],
                         ["orgsyndb-deploy", "run"])
        self.assertEqual(services["builder"]["environment"][
            "ORGSYNDB_COLLECTION_REF"], "main")
        web_mounts = {m["target"]: m for m in services["web"]["volumes"]}
        self.assertTrue(web_mounts["/var/lib/orgsyndb"]["read_only"])


if __name__ == "__main__":
    unittest.main()
