"""Tests of the builder's check server (container-deployment: Gate):
``orgsyndb-deploy run`` serves ``POST /check`` for the hook of
``lab/collection``, which sends the pack of a commit with its history.

Each test starts ``orgsyndb-deploy run`` as a subprocess against throwaway
Git repositories, a fake lab application (``GateApp``) and a fake
``tools/orgsyndb`` in a fake application clone, as ``UpdaterTests`` does.
The cycles of ``run`` stay idle but where a test needs one: the
collection repository the process is given does not exist, so that a
cycle ends after the failed fetch. Every process a test starts is stopped
when the test ends.
"""

import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable

from pipeline_support import FakeApp, Received, closed_address, free_port
from support import REGISTRY, load_snapshot
from test_deploy import (FAKE_MANIFEST, FAKE_PROBLEM, TOKEN, UPDATER,
                         commit_files, git)

GATE_TOKEN = "gate-token"
CHECK_PATH = "/lab/collection/check/"
HOST = "lab.example.org"
BAD_LINE = ("bad-procedure.md:title: error: the fake validator rejects "
            "this file")
QUIET_LINE = "the vocabulary file is unreadable"
HALF = ("language", "procedures", "sequences", "deleted")

GATE_TOOL = """\
#!/usr/bin/env python3
# Fake tool: -C DIR validate|manifest|build. Every run appends a JSON
# line about itself to $FAKE_GATE_LOG. `validate` waits while the file
# $FAKE_HOLD exists, hangs (with a child in its process group, whose
# pids go to $FAKE_PIDS) when the collection holds `validate-hang`, and
# fails when it holds `bad-procedure.md` (a file `.gitattributes` may
# mark export-ignore), `fail-validate` or `fail-quiet`. `manifest` hangs
# when the collection holds `manifest-hang`, fails when it holds
# `manifest-fail` and prints the fixed collection half of a manifest.
# `build` writes public/index.html as the cycle's tool does.
import json, os, subprocess, sys, time
from pathlib import Path
app = Path(__file__).resolve().parent.parent
collection = Path(sys.argv[2])
command = sys.argv[3]
registry = os.environ.get("ORGSYNDB_REGISTRY", "")
cache = app / ".tools" / "cached"
had_cache = cache.exists()
cache.parent.mkdir(exist_ok=True)
cache.write_text("x")


def git(*args):
    done = subprocess.run(["git", "-C", str(collection), *args],
                          capture_output=True, text=True)
    return done.stdout.strip()


record = {
    "command": command, "argv": sys.argv[1:], "app": str(app),
    "version": (app / "VERSION").read_text().strip(),
    "collection": str(collection), "registry": registry,
    "registry_text": (Path(registry).read_text() if registry
                      and Path(registry).is_file() else ""),
    "had_cache": had_cache, "pid": os.getpid(), "pgid": os.getpgid(0),
    "top": (sorted(os.listdir(collection)) if collection.is_dir()
            else None),
    "head": git("rev-parse", "HEAD"),
    "branch": git("symbolic-ref", "--short", "-q", "HEAD"),
    "commits": git("rev-list", "--count", "HEAD"),
}
with open(os.environ["FAKE_GATE_LOG"], "a") as log:
    log.write(json.dumps(record) + "\\n")


def hang():
    child = subprocess.Popen(["sleep", "600"])
    with open(os.environ["FAKE_PIDS"], "a") as pids:
        pids.write(json.dumps({"pid": os.getpid(), "child": child.pid,
                               "pgid": os.getpgid(0)}) + "\\n")
    time.sleep(600)


if command == "validate":
    held = os.environ.get("FAKE_HOLD", "")
    deadline = time.time() + 120
    while held and os.path.exists(held) and time.time() < deadline:
        time.sleep(0.05)
    if (collection / "validate-hang").exists():
        hang()
    if (collection / "bad-procedure.md").exists():
        print(@BAD@)
        print("orgsyndb: error: validation found errors; the site was "
              "not built", file=sys.stderr)
        sys.exit(1)
    if (collection / "fail-validate").exists():
        print(@PROBLEM@)
        print("orgsyndb: error: validation found errors; the site was "
              "not built", file=sys.stderr)
        sys.exit(1)
    if (collection / "fail-quiet").exists():
        print(@QUIET@)
        print(@QUIET@, file=sys.stderr)
        sys.exit(2)
elif command == "manifest":
    if (collection / "manifest-hang").exists():
        hang()
    if (collection / "manifest-fail").exists():
        print(@PROBLEM@)
        print("orgsyndb: error: the manifest failed", file=sys.stderr)
        sys.exit(1)
    print(@MANIFEST@)
elif command == "build":
    public = collection / "public"
    public.mkdir(exist_ok=True)
    text = (collection / "content.txt").read_text().strip()
    version = (app / "VERSION").read_text().strip()
    (public / "index.html").write_text(f"{version} {text}\\n")
""".replace("@BAD@", repr(BAD_LINE)).replace(
    "@PROBLEM@", repr(FAKE_PROBLEM)).replace(
    "@QUIET@", repr(QUIET_LINE)).replace(
    "@MANIFEST@", repr(json.dumps(FAKE_MANIFEST)))


class GateApp(FakeApp):
    """``FakeApp`` that also answers ``POST /lab/collection/check/``.

    Each request to the check path is kept in ``checks``, a ``Received``
    with its parsed body and its headers by lower-case name, and answered
    200 with ``{"errors": check_errors}``, or with ``check_status`` and a
    JSON error when that is set. With ``check_wait`` set it first waits
    that many seconds, or until ``release`` is set.
    """

    def __init__(self, table: dict[str, Any]) -> None:
        self.checks: list[Received] = []
        self.check_errors: list[str] = []
        self.check_status: int | None = None
        self.check_wait = 0.0
        self.release = threading.Event()
        super().__init__(table)

    @property
    def check_url(self) -> str:
        return self.origin + CHECK_PATH

    def post(self, handler: BaseHTTPRequestHandler) -> None:
        if handler.path != CHECK_PATH:
            super().post(handler)
            return
        length = int(handler.headers.get("Content-Length", "0"))
        raw = handler.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            body = raw.decode("utf-8", "replace")
        headers = {name.lower(): value
                   for name, value in handler.headers.items()}
        self.checks.append(Received(body, headers, None))
        if self.check_wait:
            self.release.wait(self.check_wait)
        if (self.token is not None
                and headers.get("authorization") != f"Bearer {self.token}"):
            self.reply(handler, 403, {"error": "wrong token"})
        elif self.check_status is not None:
            self.reply(handler, self.check_status,
                       {"error": "answered by the test"})
        else:
            self.reply(handler, 200, {"errors": self.check_errors})

    def stop(self) -> None:
        self.release.set()
        super().stop()


def wait_for(condition: Callable[[], Any], seconds: float = 20.0) -> bool:
    """Wait until ``condition`` is true; give up after ``seconds``."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return bool(condition())


def alive(pid: int) -> bool:
    """Whether the process ``pid`` runs, a zombie not counting."""
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return text.rpartition(")")[2].split()[0] != "Z"


def pack_of(repo: Path, commit: str) -> bytes:
    """The pack the hook sends for ``commit``: its history as
    ``git pack-objects --stdout --revs`` writes it."""
    done = subprocess.run(
        ["git", "-C", str(repo), "pack-objects", "--stdout", "--revs"],
        input=f"{commit}\n".encode(), capture_output=True, check=True)
    return done.stdout


def post_check(port: int, body: bytes | None, commit: str | None,
               token: str | None = GATE_TOKEN, path: str = "/check",
               method: str = "POST", timeout: float = 60,
               length: int | None = None) -> tuple[int, str]:
    """Send a request to the check server on ``port``; return the status
    and the text of the answer. With ``length``, send that
    ``Content-Length`` and no body."""
    connection = http.client.HTTPConnection("127.0.0.1", port,
                                            timeout=timeout)
    try:
        connection.putrequest(method, path)
        if token is not None:
            connection.putheader("Authorization", f"Bearer {token}")
        if commit is not None:
            connection.putheader("X-Orgsyndb-Commit", commit)
        connection.putheader("Content-Type", "application/octet-stream")
        if length is not None:
            connection.putheader("Content-Length", str(length))
            connection.endheaders()
        else:
            data = b"" if body is None else body
            connection.putheader("Content-Length", str(len(data)))
            connection.endheaders(data)
        answer = connection.getresponse()
        return answer.status, answer.read().decode("utf-8", "replace")
    finally:
        connection.close()


@unittest.skipIf(shutil.which("git") is None, "git not found")
class GateCase(unittest.TestCase):
    """A fake application, a fake lab application, a collection
    repository and the means to run the check server."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.upstream = self.tmp / "app-upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "--quiet", "--initial-branch", "main")
        commit_files(self.upstream, {
            "tools/orgsyndb": GATE_TOOL, "VERSION": "v1\n",
            "deploy/docker/Dockerfile": "FROM scratch\n",
            ".gitignore": "/.tools/\n"})
        (self.upstream / "tools" / "orgsyndb").chmod(0o755)
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "--quiet", "--amend", "-m", "v1")
        self.app_v1 = git(self.upstream, "rev-parse", "HEAD")
        self.app = self.tmp / "app"
        subprocess.run(["git", "clone", "--quiet", str(self.upstream),
                        str(self.app)], check=True)
        self.image = self.tmp / "image.json"
        self.image.write_text(json.dumps({
            "app_repo": str(self.upstream), "app_ref": "main",
            "deploy_tree": git(self.upstream, "rev-parse",
                               "HEAD:deploy/docker")}))
        self.collection = self.tmp / "collection-upstream"
        self.collection.mkdir()
        git(self.collection, "init", "--quiet", "--initial-branch", "main")
        self.col_v1 = commit_files(self.collection, {
            "orgsyndb.toml": "format = 1\n", "content.txt": "first\n",
            ".gitignore": "/build/\n/public/\n/pdf/\n"})
        self.data = self.tmp / "data"
        self.log = self.tmp / "gate.log"
        self.pids = self.tmp / "pids.log"
        self.hold = self.tmp / "hold"
        self.port = free_port()
        self.server = GateApp(load_snapshot(REGISTRY))
        self.server.token = TOKEN
        self.addCleanup(self.server.stop)
        self.processes: list[subprocess.Popen] = []
        self.addCleanup(self.kill_tools)
        self.env = {
            "PATH": os.environ["PATH"], "HOME": str(self.tmp),
            "GIT_CONFIG_NOSYSTEM": "1",
            "FAKE_GATE_LOG": str(self.log), "FAKE_PIDS": str(self.pids),
            "FAKE_HOLD": str(self.hold),
            "ORGSYNDB_REGISTRY_URL": self.server.url,
            "ORGSYNDB_MANIFEST_URL": self.server.manifest_url,
            "ORGSYNDB_CHECK_URL": self.server.check_url,
            "ORGSYNDB_BUILDER_TOKEN": TOKEN,
            "ORGSYNDB_ALLOWED_HOSTS": f"{HOST},app",
            "ORGSYNDB_DATA": str(self.data), "ORGSYNDB_APP": str(self.app),
            "ORGSYNDB_APP_UPDATE": "false",
            "ORGSYNDB_IMAGE_INFO": str(self.image),
            # No collection: a cycle ends after its failed fetch.
            "ORGSYNDB_COLLECTION_REPO": str(self.tmp / "no-collection"),
            "ORGSYNDB_GATE_TOKEN": GATE_TOKEN,
            "ORGSYNDB_GATE_PORT": str(self.port),
            "ORGSYNDB_GATE_BIND": "127.0.0.1",
        }

    # --- processes -------------------------------------------------------

    def start(self, **extra: str) -> subprocess.Popen:
        """Start ``orgsyndb-deploy run`` with ``extra`` on top of the
        environment; return once its check server accepts connections
        (when ``ORGSYNDB_GATE_TOKEN`` is set)."""
        out = open(self.tmp / "run.log", "w")
        self.addCleanup(out.close)
        env = {**self.env, **extra}
        process = subprocess.Popen(
            [sys.executable, str(UPDATER), "run"], env=env,
            stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
            start_new_session=True)
        self.processes.append(process)
        self.addCleanup(self.stop, process)
        if env.get("ORGSYNDB_GATE_TOKEN"):
            self.assertTrue(
                wait_for(lambda: process.poll() is not None
                         or self.listening(int(env["ORGSYNDB_GATE_PORT"])),
                         6),
                "the check server does not listen\n" + self.output())
            self.assertIsNone(process.poll(), self.output())
        return process

    def output(self) -> str:
        return (self.tmp / "run.log").read_text()

    @staticmethod
    def listening(port: int) -> bool:
        try:
            socket.create_connection(("127.0.0.1", port), 0.5).close()
        except OSError:
            return False
        return True

    def stop(self, process: subprocess.Popen) -> None:
        """End ``process`` with SIGTERM; kill its group when it does not
        exit."""
        try:
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)

    def kill_tools(self) -> None:
        """Kill the process groups of the fake tool's hanging runs and
        let go of a held validation, whatever the test did."""
        self.hold.unlink(missing_ok=True)
        for line in self.pid_lines():
            try:
                os.killpg(line["pgid"], signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        for run in self.runs():
            if run["command"] == "validate" and alive(run["pid"]):
                try:
                    os.killpg(run["pgid"], signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def pid_lines(self) -> list[dict]:
        if not self.pids.exists():
            return []
        return [json.loads(line) for line in
                self.pids.read_text().splitlines()]

    # --- what the fake tool and the fake application saw ----------------

    def runs(self) -> list[dict]:
        """Every run of the fake tool, in order."""
        if not self.log.exists():
            return []
        return [json.loads(line) for line in
                self.log.read_text().splitlines()]

    @property
    def check_app(self) -> Path:
        return (self.data / "check" / "app").resolve()

    def check_runs(self) -> list[dict]:
        """The runs of the check, those from the check's own clone."""
        return [run for run in self.runs()
                if Path(run["app"]).resolve() == self.check_app]

    def leftovers(self) -> list[str]:
        """The names under ``<data>/check/`` but for the check's clone
        of the application."""
        check = self.data / "check"
        if not check.is_dir():
            return []
        return sorted(entry.name for entry in check.iterdir()
                      if entry.name != "app")

    def assert_no_check_directory(self) -> None:
        self.assertTrue(wait_for(lambda: not self.leftovers(), 5),
                        f"left over: {self.leftovers()}")

    # --- requests ---------------------------------------------------------

    def head(self) -> str:
        return git(self.collection, "rev-parse", "HEAD")

    def check(self, header: str | None = None, **extra: Any
              ) -> tuple[int, str]:
        """Post the pack of the collection's tip, with the tip's id in
        ``X-Orgsyndb-Commit``, or with ``header`` in its place, and the
        token; ``extra`` goes to ``post_check``."""
        tip = self.head()
        return post_check(self.port, pack_of(self.collection, tip),
                          **{"commit": header or tip, **extra})

    def commit(self, files: dict[str, str | None]) -> str:
        """Commit ``files`` to the collection; return the commit."""
        return commit_files(self.collection, files)

    def set_state(self, app: str) -> None:
        """Save a state whose published release was built with the
        application commit ``app``."""
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "state.json").write_text(json.dumps({
            "deployed": {"app": app, "collection": "c" * 40,
                         "registry": "d" * 64, "release": "000001-x-y",
                         "time": "2026-11-13T10:00:00+0100"},
            "failed": [], "unsent": None}))

    def in_thread(self, call: Callable[[], Any]) -> list:
        """Run ``call`` in a thread; the list gets its result, or the
        exception it raised, when it ends."""
        result: list = []

        def run() -> None:
            try:
                result.append(call())
            except Exception as error:
                result.append(error)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return result

    def start_held_check(self) -> list:
        """Hold the validation, start a check in a thread and wait until
        the fake tool is validating; return the thread's result list."""
        self.hold.write_text("")
        result = self.in_thread(self.check)
        self.assertTrue(wait_for(lambda: any(
            run["command"] == "validate" for run in self.check_runs())),
            "the check did not reach validate\n" + self.output())
        return result


class ValidCheckTests(GateCase):

    def test_a_valid_push_is_answered_200(self) -> None:
        """Scenario: A valid push."""
        self.start()
        status, body = self.check()
        self.assertEqual((status, body), (200, ""), self.output())
        self.assertEqual(len(self.server.checks), 1)
        received = self.server.checks[0]
        self.assertEqual(received.body, FAKE_MANIFEST)
        self.assertEqual(set(received.body), set(HALF))
        self.assertEqual(received.headers["authorization"],
                         f"Bearer {TOKEN}")
        self.assertEqual(received.host, HOST)
        self.assert_no_check_directory()

    def test_the_steps_run_in_order_on_the_commit(self) -> None:
        """Requirement: Gate (it checks the commit out and runs
        `validate` and `manifest`)."""
        self.start()
        self.commit({"content.txt": "second\n"})
        tip = self.head()
        self.assertEqual(self.check()[0], 200, self.output())
        runs = self.check_runs()
        self.assertEqual([run["command"] for run in runs],
                         ["validate", "manifest"])
        for run in runs:
            with self.subTest(command=run["command"]):
                self.assertEqual(run["argv"][0], "-C")
                self.assertIn("content.txt", run["top"])
                self.assertIn("orgsyndb.toml", run["top"])
                self.assertEqual(run["head"], tip)

    def test_the_checkout_is_a_repository_with_the_history(self) -> None:
        """Requirement: Gate (it indexes the pack into a new repository,
        points `main` at the commit and checks it out)."""
        self.start()
        self.commit({"content.txt": "second\n"})
        self.commit({"content.txt": "third\n"})
        self.assertEqual(self.check()[0], 200, self.output())
        for run in self.check_runs():
            with self.subTest(command=run["command"]):
                self.assertEqual(run["commits"], "3")
                self.assertEqual(run["branch"], "main")

    def test_the_history_comes_whatever_the_old_tip(self) -> None:
        """Requirement: Gate (the pack holds the commit with its
        history)."""
        self.start()
        self.commit({"content.txt": "second\n"})
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual(self.check_runs()[0]["commits"], "2")

    def test_the_steps_run_from_the_checks_own_clone(self) -> None:
        """Requirement: Gate (`<data>/check/app/`, not the cycle's
        clone)."""
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual(len(self.check_runs()), 2)
        self.assertEqual(len(self.runs()), 2)
        self.assertNotEqual(self.check_app, self.app.resolve())
        self.assertEqual(git(self.check_app, "rev-parse", "HEAD"),
                         self.app_v1)

    def test_the_snapshot_is_the_checks_own(self) -> None:
        """Requirement: Gate (it fetches its own snapshot into the
        check's directory)."""
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual(self.server.hosts, [HOST])
        for run in self.check_runs():
            with self.subTest(command=run["command"]):
                registry = Path(run["registry"])
                self.assertTrue(registry.is_absolute(), registry)
                self.assertTrue(
                    registry.is_relative_to(self.data / "check"), registry)
                self.assertNotEqual(registry, self.data / "registry.json")
                self.assertEqual(run["registry_text"],
                                 self.server.snapshot_body().decode())

    def test_the_cycles_files_are_left_alone(self) -> None:
        """Requirement: Gate (a check shares no file with the cycle)."""
        self.start()
        before = git(self.app, "rev-parse", "HEAD")
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertFalse((self.data / "registry.json").exists())
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), before)
        self.assertEqual(self.runs()[0]["app"], str(self.check_app))

    def test_the_collection_path_is_taken_inside_the_checkout(self) -> None:
        """Requirement: Gate (`-C <checkout>/<ORGSYNDB_COLLECTION_PATH>`)."""
        self.start(ORGSYNDB_COLLECTION_PATH="lab")
        self.commit({"lab/orgsyndb.toml": "format = 1\n",
                     "lab/content.txt": "nested\n"})
        self.assertEqual(self.check()[0], 200, self.output())
        for run in self.check_runs():
            with self.subTest(command=run["command"]):
                self.assertEqual(Path(run["collection"]).name, "lab")
                self.assertIn("content.txt", run["top"])

    def test_a_second_check_runs_after_the_first(self) -> None:
        """Requirement: Gate (the directory of a check is removed when
        it ends; the next check starts afresh)."""
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assert_no_check_directory()
        self.commit({"content.txt": "second\n"})
        self.assertEqual(self.check()[0], 200, self.output())
        self.assert_no_check_directory()
        self.assertEqual(len(self.server.checks), 2)

    def test_no_check_server_without_the_token(self) -> None:
        """Requirement: Gate (when `ORGSYNDB_GATE_TOKEN` is set): the
        same settings with the token serve; without it nothing does."""
        served = self.start()
        self.assertTrue(self.listening(self.port))
        self.stop(served)
        self.assertFalse(self.listening(self.port))
        self.start(ORGSYNDB_GATE_TOKEN="")
        self.assertTrue(wait_for(
            lambda: self.output().count("every") > 0), self.output())
        time.sleep(1)
        self.assertFalse(self.listening(self.port))

    def test_the_program_names_the_settings(self) -> None:
        """Requirement: Gate (the settings and their defaults)."""
        text = UPDATER.read_text(encoding="utf-8")
        for name in ("ORGSYNDB_GATE_TOKEN", "ORGSYNDB_GATE_TIMEOUT",
                     "ORGSYNDB_CHECK_URL",
                     "http://app:8000/lab/collection/check/", "8091"):
            with self.subTest(name=name):
                self.assertIn(name, text)


class AppCommitTests(GateCase):
    """Requirement: Gate (the application commit of the published
    release the saved state names, or the cycle's checked-out commit when
    none is published)."""

    def make_v2(self) -> str:
        """Commit a second application version upstream, fetch it into
        the cycle's clone and check it out there."""
        app_v2 = commit_files(self.upstream, {"VERSION": "v2\n"})
        git(self.app, "fetch", "--quiet", "origin")
        git(self.app, "checkout", "--quiet", "--detach", app_v2)
        return app_v2

    def test_the_published_release_names_the_commit(self) -> None:
        """Requirement: Gate (the published release's application
        commit)."""
        self.make_v2()
        self.set_state(self.app_v1)
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual({run["version"] for run in self.check_runs()},
                         {"v1"})
        self.assertEqual(git(self.check_app, "rev-parse", "HEAD"),
                         self.app_v1)

    def test_without_a_published_release_the_cycles_commit(self) -> None:
        """Requirement: Gate (or the cycle's checked-out commit when
        none is published)."""
        app_v2 = self.make_v2()
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual({run["version"] for run in self.check_runs()},
                         {"v2"})
        self.assertEqual(git(self.check_app, "rev-parse", "HEAD"), app_v2)

    def test_the_state_is_read_at_each_check(self) -> None:
        """Requirement: Gate (before each check it fetches from the
        cycle's clone and checks out the commit the state names)."""
        app_v2 = self.make_v2()
        self.set_state(self.app_v1)
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.set_state(app_v2)
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual([run["version"] for run in self.check_runs()],
                         ["v1", "v1", "v2", "v2"])
        self.assertEqual(git(self.check_app, "rev-parse", "HEAD"), app_v2)

    def test_the_clone_keeps_its_ignored_files(self) -> None:
        """Requirement: Gate (it keeps ignored files)."""
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertEqual([run["had_cache"] for run in self.check_runs()],
                         [False, True, True, True])


class FailedCheckTests(GateCase):

    def test_a_collection_that_fails_validation(self) -> None:
        """Scenario: A collection that fails validation."""
        self.start()
        self.commit({"fail-validate": ""})
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertIn(FAKE_PROBLEM, body.splitlines())
        for line in body.splitlines():
            self.assertIn(": error: ", line)
        self.assertEqual(self.server.checks, [])
        self.assertEqual([run["command"] for run in self.check_runs()],
                         ["validate"])
        self.assert_no_check_directory()

    def test_a_file_that_export_ignore_leaves_out_of_an_archive(
            self) -> None:
        """Scenario: Files a committed .gitattributes leaves out of an
        archive."""
        self.start()
        tip = self.commit({
            ".gitattributes": "bad-procedure.md export-ignore\n",
            "bad-procedure.md": "invalid\n"})
        archive = subprocess.run(
            ["git", "-C", str(self.collection), "archive", tip],
            capture_output=True, check=True).stdout
        names = subprocess.run(["tar", "-t"], input=archive,
                               capture_output=True, check=True).stdout
        self.assertNotIn(b"bad-procedure.md", names, "the control fails")
        status, body = self.check()
        self.assertEqual(status, 422, self.output())
        self.assertIn(BAD_LINE, body.splitlines())
        self.assertEqual(self.server.checks, [])
        self.assert_no_check_directory()

    def test_without_error_lines_the_last_line_is_the_error(self) -> None:
        """Requirement: Gate (the step's error lines, or its last line
        when none does)."""
        self.start()
        self.commit({"fail-quiet": ""})
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertEqual(body.splitlines(), [QUIET_LINE])
        self.assertEqual(self.server.checks, [])

    def test_a_manifest_that_fails(self) -> None:
        """Requirement: Gate (when a step exits non-zero, `422` with
        its error lines): the manifest's step."""
        self.start()
        self.commit({"manifest-fail": ""})
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertIn(FAKE_PROBLEM, body.splitlines())
        self.assertEqual(self.server.checks, [])
        self.assertEqual([run["command"] for run in self.check_runs()],
                         ["validate", "manifest"])
        self.assert_no_check_directory()

    def test_a_collection_the_import_would_refuse(self) -> None:
        """Scenario: A collection the import would refuse."""
        self.start()
        self.server.check_errors = ["OSDB-0099: not issued"]
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertEqual(body.splitlines(), ["OSDB-0099: not issued"])
        self.assertEqual(len(self.server.checks), 1)
        self.assert_no_check_directory()

    def test_every_error_of_the_application_is_a_line(self) -> None:
        """Requirement: Gate (the errors the application returned, one
        per line)."""
        self.start()
        self.server.check_errors = [
            "OSDB-0099: not issued", 'OSDB-0002: unknown author "nobody"',
            "SEQ-0002: step 2 names no entry of OSDB-0009"]
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertEqual(body.splitlines(), self.server.check_errors)

    def test_a_pack_that_lacks_the_commit(self) -> None:
        """Requirement: Gate (the pack does not hold the commit: `422`)."""
        self.start()
        status, body = self.check(header="1" * 40)
        self.assertEqual(status, 422, body)
        self.assertTrue(body.strip())
        self.assertEqual(self.server.checks, [])
        self.assert_no_check_directory()

    def test_a_body_that_is_no_pack(self) -> None:
        """Requirement: Gate (a step exits non-zero: `422`)."""
        self.start()
        status, body = post_check(self.port, b"this is no pack",
                                  self.head())
        self.assertEqual(status, 422, body)
        self.assertEqual(self.server.checks, [])
        self.assert_no_check_directory()

    def test_an_application_that_answers_another_status(self) -> None:
        """Requirement: Gate (the application gives no answer of status
        200: `503` with the reason)."""
        self.start()
        self.server.check_status = 500
        status, body = self.check()
        self.assertEqual(status, 503, body)
        self.assertTrue(body.strip())
        self.assert_no_check_directory()

    def test_an_application_that_does_not_answer(self) -> None:
        """Requirement: Gate (the application gives no answer: `503`)."""
        closed = closed_address().replace(
            "/lab/registry/snapshot.json", CHECK_PATH)
        self.start(ORGSYNDB_CHECK_URL=closed)
        status, body = self.check()
        self.assertEqual(status, 503, body)
        self.assertTrue(body.strip())
        self.assert_no_check_directory()

    def test_a_snapshot_that_cannot_be_fetched(self) -> None:
        """Requirement: Gate (the snapshot cannot be fetched: `503` with
        the reason)."""
        self.start(ORGSYNDB_REGISTRY_URL=closed_address())
        status, body = self.check()
        self.assertEqual(status, 503, body)
        self.assertTrue(body.strip())
        self.assertEqual(self.check_runs(), [])
        self.assertEqual(self.server.checks, [])
        self.assert_no_check_directory()

    def test_a_failed_check_does_not_block_the_next(self) -> None:
        """Requirement: Gate (one check at a time; a failed one ends)."""
        self.start()
        self.commit({"fail-validate": ""})
        self.assertEqual(self.check()[0], 422)
        self.commit({"fail-validate": None})
        self.assertEqual(self.check()[0], 200, self.output())


class RequestTests(GateCase):

    def test_without_the_token(self) -> None:
        """Scenario: Without the token (and with a wrong one)."""
        self.start()
        for name, token in (("none", None), ("wrong", "other"),
                            ("close", GATE_TOKEN[:-1]),
                            ("longer", GATE_TOKEN + "x"),
                            ("empty", ""),
                            ("the builder's", TOKEN)):
            with self.subTest(token=name):
                status, _body = self.check(token=token)
                self.assertEqual(status, 401)
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.server.checks, [])
        self.assertEqual(self.server.hosts, [])
        self.assertEqual(self.leftovers(), [])

    def test_the_token_is_a_bearer_token(self) -> None:
        """Requirement: Gate (`Authorization: Bearer
        <ORGSYNDB_GATE_TOKEN>`)."""
        self.start()
        pack = pack_of(self.collection, self.head())
        for header in (GATE_TOKEN, f"Basic {GATE_TOKEN}",
                       f"Token {GATE_TOKEN}"):
            with self.subTest(header=header):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", self.port, timeout=30)
                try:
                    connection.request("POST", "/check", pack, {
                        "Authorization": header,
                        "X-Orgsyndb-Commit": self.head()})
                    self.assertEqual(connection.getresponse().status, 401)
                finally:
                    connection.close()
        self.assertEqual(self.runs(), [])

    def test_another_path_or_method(self) -> None:
        """Requirement: Gate (another path or method answers 404 or
        405)."""
        self.start()
        for method, path in (("GET", "/check"), ("PUT", "/check"),
                             ("DELETE", "/check"), ("POST", "/"),
                             ("POST", "/other"), ("GET", "/"),
                             ("POST", "/check/extra")):
            with self.subTest(method=method, path=path):
                status, _body = post_check(
                    self.port, b"", self.head(), method=method, path=path)
                self.assertIn(status, (404, 405))
        self.assertEqual(self.runs(), [])

    def test_a_body_over_200_mb(self) -> None:
        """Requirement: Gate (a body over 200 MB answers 413): the
        length is judged before the body is read, so none is sent."""
        self.start()
        status, _body = post_check(self.port, None, self.head(),
                                   length=300_000_000, timeout=20)
        self.assertEqual(status, 413)
        self.assertEqual(self.runs(), [])

    def test_a_commit_that_is_missing_or_not_40_hex_digits(self) -> None:
        """Requirement: Gate (one without a commit id of 40 hexadecimal
        digits in `X-Orgsyndb-Commit` answers 400)."""
        self.start()
        pack = pack_of(self.collection, self.head())
        for name, commit in (("missing", None), ("empty", ""),
                             ("39 digits", "a" * 39),
                             ("41 digits", "a" * 41),
                             ("not hexadecimal", "g" * 40),
                             ("a name", "main"),
                             ("a path", "../" * 13 + "a")):
            with self.subTest(commit=name):
                status, _body = post_check(self.port, pack, commit)
                self.assertEqual(status, 400)
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.server.checks, [])

    def test_a_request_is_judged_for_its_token_first(self) -> None:
        """Requirement: Gate (a request without the bearer token answers
        401, whatever else is wrong with it)."""
        self.start()
        status, _body = post_check(self.port, b"", None, token=None)
        self.assertEqual(status, 401)


class BusyTests(GateCase):

    def test_a_second_check_while_one_runs(self) -> None:
        """Scenario: Busy."""
        self.start()
        first = self.start_held_check()
        began = time.monotonic()
        status, body = self.check()
        self.assertLess(time.monotonic() - began, 3)
        self.assertEqual(status, 503, body)
        self.assertIn("busy", body.lower())
        self.assertIn("push again", body.lower())
        self.assertEqual(first, [], "the first check ended")
        self.hold.unlink()
        self.assertTrue(wait_for(lambda: first), "the first never ended")
        self.assertEqual(first[0][0], 200, first[0])
        self.assertEqual(len(self.server.checks), 1)

    def test_the_gate_is_free_again_after_a_check(self) -> None:
        """Requirement: Gate (one check at a time, not one only)."""
        self.start()
        first = self.start_held_check()
        self.assertEqual(self.check()[0], 503)
        self.hold.unlink()
        self.assertTrue(wait_for(lambda: first))
        self.assertEqual(self.check()[0], 200, self.output())

    def test_a_busy_answer_starts_nothing(self) -> None:
        """Requirement: Gate (503 at once)."""
        self.start()
        self.start_held_check()
        runs = len(self.runs())
        self.check()
        time.sleep(0.5)
        self.assertEqual(len(self.runs()), runs)
        self.assertEqual(self.server.hosts, [HOST])


class TooSlowTests(GateCase):
    """Scenario: Too slow, with `ORGSYNDB_GATE_TIMEOUT` of 12, a
    deadline of 2 seconds."""

    def answers_late(self, files: dict[str, str | None]
                     ) -> tuple[int, str, float]:
        """Commit ``files``, post the check; return its status, its body
        and the seconds it took."""
        self.commit(files)
        began = time.monotonic()
        status, body = self.check(timeout=30)
        return status, body, time.monotonic() - began

    def assert_processes_gone(self) -> None:
        self.assertTrue(self.pid_lines(), "nothing hung")
        for line in self.pid_lines():
            for pid in (line["pid"], line["child"]):
                with self.subTest(pid=pid):
                    self.assertTrue(wait_for(lambda: not alive(pid), 5),
                                    f"process {pid} runs")

    def test_a_hanging_validation(self) -> None:
        """Scenario: Too slow."""
        self.start(ORGSYNDB_GATE_TIMEOUT="12")
        status, body, seconds = self.answers_late({"validate-hang": ""})
        self.assertEqual(status, 503, body)
        self.assertIn("took too long", body)
        self.assertGreaterEqual(seconds, 1.0)
        self.assertLess(seconds, 6.0)
        self.assert_processes_gone()
        self.assert_no_check_directory()
        self.assertEqual(self.server.checks, [])

    def test_a_hanging_manifest(self) -> None:
        """Scenario: Too slow (the manifest's step)."""
        self.start(ORGSYNDB_GATE_TIMEOUT="12")
        status, body, seconds = self.answers_late({"manifest-hang": ""})
        self.assertEqual(status, 503, body)
        self.assertIn("took too long", body)
        self.assertGreaterEqual(seconds, 1.0)
        self.assertLess(seconds, 6.0)
        self.assert_processes_gone()
        self.assert_no_check_directory()

    def test_one_deadline_for_every_step(self) -> None:
        """Requirement: Gate (each step may take only the time left):
        the application that answers late is a step too."""
        self.start(ORGSYNDB_GATE_TIMEOUT="12")
        self.server.check_wait = 60
        began = time.monotonic()
        status, body = self.check(timeout=30)
        seconds = time.monotonic() - began
        self.assertEqual(status, 503, body)
        self.assertIn("took too long", body)
        self.assertLess(seconds, 6.0)
        self.assert_no_check_directory()

    def test_the_gate_is_free_after_a_check_too_slow(self) -> None:
        """Requirement: Gate (the next check runs)."""
        self.start(ORGSYNDB_GATE_TIMEOUT="12")
        self.answers_late({"validate-hang": ""})
        self.commit({"validate-hang": None})
        self.assertEqual(self.check()[0], 200, self.output())

    def test_the_deadline_follows_the_setting(self) -> None:
        """Requirement: Gate (`ORGSYNDB_GATE_TIMEOUT` less 10 seconds):
        a check that takes 3 seconds passes with a timeout of 20 s."""
        self.start(ORGSYNDB_GATE_TIMEOUT="20")
        self.server.check_wait = 3
        status, body = self.check(timeout=30)
        self.assertEqual(status, 200, body)


class CycleMeanwhileTests(GateCase):
    """Scenario: The cycle meanwhile."""

    def test_a_cycle_does_not_touch_the_check(self) -> None:
        self.env["ORGSYNDB_COLLECTION_REPO"] = str(self.collection)
        self.env["ORGSYNDB_APP_UPDATE"] = "true"
        self.env.update(ORGSYNDB_ALLOWED_HOSTS=f"{HOST},app")
        done = subprocess.run(
            [sys.executable, str(UPDATER), "sync"], env=self.env,
            capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        state = json.loads((self.data / "state.json").read_text())
        self.assertEqual(state["deployed"]["app"], self.app_v1)
        sync_runs = len(self.runs())
        process = self.start()
        first = self.start_held_check()
        (held,) = [run for run in self.check_runs()]
        self.assertEqual(held["version"], "v1")
        self.assertNotEqual(Path(held["app"]).resolve(),
                            self.app.resolve())
        self.assertNotEqual(Path(held["registry"]),
                            self.data / "registry.json")
        # The cycle meanwhile: a new application commit, a new
        # collection commit and another snapshot.
        app_v2 = commit_files(self.upstream, {"VERSION": "v2\n"})
        self.commit({"content.txt": "second\n"})
        self.server.table = {**self.server.table, "digest": "e" * 64}
        os.kill(process.pid, signal.SIGHUP)

        def published() -> bool:
            found = json.loads((self.data / "state.json").read_text())
            return (found.get("deployed") or {}).get("app") == app_v2

        self.assertTrue(wait_for(published, 60),
                        "the cycle did not publish\n" + self.output())
        self.assertEqual(git(self.app, "rev-parse", "HEAD"), app_v2)
        self.assertTrue(
            any(Path(run["app"]).resolve() == self.app.resolve()
                and run["version"] == "v2"
                for run in self.runs()[sync_runs:]),
            "the cycle did not build with v2")
        self.assertIn("e" * 64, (self.data / "registry.json").read_text())
        # The check's own files are as they were.
        self.assertEqual(git(self.check_app, "rev-parse", "HEAD"),
                         self.app_v1)
        self.assertEqual(Path(held["registry"]).read_text(),
                         held["registry_text"])
        self.assertNotIn("e" * 64, Path(held["registry"]).read_text())
        self.assertEqual(first, [], "the check ended early")
        self.hold.unlink()
        self.assertTrue(wait_for(lambda: first), "the check never ended")
        self.assertEqual(first[0][0], 200, first[0])
        manifest_run = [run for run in self.check_runs()
                        if run["command"] == "manifest"][0]
        self.assertEqual(manifest_run["version"], "v1")
        self.assertEqual(manifest_run["registry_text"],
                         held["registry_text"])
        self.assertEqual(Path(manifest_run["registry"]),
                         Path(held["registry"]))


class ShutdownTests(GateCase):
    """Requirement: Gate (on `SIGTERM` the main thread stops the server,
    kills a running check's process group and removes its directory
    before the program exits)."""

    def test_sigterm_during_a_check(self) -> None:
        """Scenario: SIGTERM during a check."""
        process = self.start()
        result = self.start_held_check()
        self.assertTrue(self.leftovers(), "the check has no directory")
        (held,) = self.check_runs()
        os.kill(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.fail("the process did not exit\n" + self.output())
        self.assertEqual(self.leftovers(), [])
        self.assertTrue(wait_for(lambda: not alive(held["pid"]), 5),
                        "the step still runs")
        self.assertFalse(self.listening(self.port))
        wait_for(lambda: result, 10)

    def test_sigterm_kills_the_whole_process_group_of_a_step(self) -> None:
        """Requirement: Gate (it kills a running check's process
        group)."""
        process = self.start()
        self.commit({"validate-hang": ""})
        result = self.in_thread(self.check)
        self.assertTrue(wait_for(lambda: self.pid_lines()), self.output())
        (line,) = self.pid_lines()
        os.kill(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.fail("the process did not exit\n" + self.output())
        for pid in (line["pid"], line["child"]):
            with self.subTest(pid=pid):
                self.assertTrue(wait_for(lambda: not alive(pid), 5),
                                f"process {pid} runs")
        self.assertEqual(self.leftovers(), [])
        wait_for(lambda: result, 10)

    def test_sigterm_when_idle(self) -> None:
        """Requirement: Gate (the program exits on `SIGTERM`)."""
        process = self.start()
        os.kill(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.fail("the process did not exit\n" + self.output())
        self.assertFalse(self.listening(self.port))

    def test_a_check_leaves_nothing_when_it_ends_by_an_error(self) -> None:
        """Requirement: Gate (the directory is removed when the check
        ends)."""
        self.start()
        self.commit({"fail-validate": ""})
        self.assertEqual(self.check()[0], 422)
        self.assert_no_check_directory()



def raw_request(port: int, commit: str, length: int,
                token: str = GATE_TOKEN) -> socket.socket:
    """Open a connection to the check server on ``port`` and send the
    head of a check of ``commit`` that announces a body of ``length``
    bytes, without the body; return the connection."""
    connection = socket.create_connection(("127.0.0.1", port), 10)
    connection.sendall((
        "POST /check HTTP/1.1\r\n"
        "Host: builder\r\n"
        f"Authorization: Bearer {token}\r\n"
        f"X-Orgsyndb-Commit: {commit}\r\n"
        "Content-Type: application/octet-stream\r\n"
        f"Content-Length: {length}\r\n\r\n").encode("ascii"))
    return connection


def read_answer(connection: socket.socket, seconds: float
                ) -> tuple[int, str]:
    """Read the answer to the request sent on ``connection``, waiting at
    most ``seconds`` for each part; return its status and text."""
    connection.settimeout(seconds)
    answer = http.client.HTTPResponse(connection)
    answer.begin()
    return answer.status, answer.read().decode("utf-8", "replace")


class SymbolicLinkTests(GateCase):
    """Scenario: A symbolic link."""

    def test_a_symbolic_link_is_refused_before_checkout(self) -> None:
        self.start()
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep\n")
        (self.collection / "build").mkdir()
        (self.collection / "build" / "tmp").symlink_to(outside)
        (self.collection / "notes").mkdir()
        (self.collection / "notes" / "link.md").symlink_to("../content.txt")
        git(self.collection, "add", "-f", "build/tmp", "notes/link.md")
        git(self.collection, "commit", "--quiet", "-m", "links")
        status, body = self.check()
        self.assertEqual(status, 422, body)
        self.assertEqual(sorted(body.splitlines()), [
            "symbolic links are not allowed: build/tmp",
            "symbolic links are not allowed: notes/link.md"])
        self.assertEqual(self.check_runs(), [])
        self.assertEqual(self.server.checks, [])
        self.assertEqual(sorted(os.listdir(outside)), ["keep.txt"])
        self.assertEqual((outside / "keep.txt").read_text(), "keep\n")
        self.assert_no_check_directory()

    def test_a_tree_without_links_still_passes(self) -> None:
        """Requirement: Gate (only a symbolic link is refused)."""
        self.start()
        self.commit({"build-notes/tmp.txt": "not a link\n"})
        self.assertEqual(self.check()[0], 200, self.output())


class TrickleTests(GateCase):
    """Scenario: A body that trickles."""

    def test_a_body_that_trickles(self) -> None:
        self.start(ORGSYNDB_GATE_TIMEOUT="12")
        connection = raw_request(self.port, self.head(), 60)
        self.addCleanup(connection.close)
        stop = threading.Event()

        def trickle() -> None:
            for _ in range(60):
                if stop.wait(1):
                    return
                try:
                    connection.send(b"P")
                except OSError:
                    return

        threading.Thread(target=trickle, daemon=True).start()
        self.addCleanup(stop.set)
        began = time.monotonic()
        status, body = read_answer(connection, 15)
        seconds = time.monotonic() - began
        self.assertEqual(status, 503, body)
        self.assertIn("took too long", body)
        self.assertLess(seconds, 6.0)
        self.assertEqual(self.runs(), [])
        self.assert_no_check_directory()


class BusyLargeBodyTests(GateCase):
    """Scenario: Busy with a large body."""

    def test_the_busy_answer_comes_before_the_body(self) -> None:
        self.start()
        first = self.start_held_check()
        size = 50_000_000
        connection = raw_request(self.port, self.head(), size)
        self.addCleanup(connection.close)
        sent = threading.Event()
        stop = threading.Event()
        self.addCleanup(stop.set)

        def slowly() -> None:
            chunk = b"x" * 65536
            for _ in range(size // len(chunk) + 1):
                if stop.wait(0.05):
                    return
                try:
                    connection.sendall(chunk)
                except OSError:
                    return
            sent.set()

        threading.Thread(target=slowly, daemon=True).start()
        began = time.monotonic()
        status, body = read_answer(connection, 10)
        self.assertLess(time.monotonic() - began, 3)
        self.assertEqual(status, 503, body)
        self.assertIn("busy", body.lower())
        self.assertFalse(sent.is_set(), "the body was sent first")
        self.hold.unlink()
        self.assertTrue(wait_for(lambda: first), "the first never ended")
        self.assertEqual(first[0][0], 200, first[0])
        self.assertEqual(len(self.server.checks), 1)


class NotTwoHundredTests(GateCase):
    """Scenario: An answer that is not 200."""

    def test_another_success_status_is_no_verdict(self) -> None:
        self.start()
        reply = self.server.reply
        answered: list[int] = []

        def other(handler: BaseHTTPRequestHandler, status: int,
                  payload: dict[str, Any]) -> None:
            if handler.path == CHECK_PATH and status == 200:
                status = answered[-1]
            reply(handler, status, payload)

        self.server.reply = other  # type: ignore[method-assign]
        for status in (201, 202, 206):
            with self.subTest(status=status):
                answered.append(status)
                before = len(self.server.checks)
                code, body = self.check()
                self.assertEqual(code, 503, body)
                self.assertTrue(body.strip())
                self.assertEqual(len(self.server.checks), before + 1)
        self.assert_no_check_directory()


class ToolCacheTests(GateCase):
    """Scenario: Tool caches."""

    def test_the_check_clone_gets_the_cycle_clones_caches(self) -> None:
        tools = self.app / ".tools"
        tools.mkdir()
        (tools / "cached").write_text("from the cycle")
        batch = self.app / ".emacs-batch" / "elpa"
        batch.mkdir(parents=True)
        (batch / "ox-hugo.el").write_text("(provide 'ox-hugo)\n")
        script = batch / "run"
        script.write_text("#!/bin/sh\n")
        script.chmod(0o750)
        self.start()
        self.assertEqual(self.check()[0], 200, self.output())
        self.assertTrue(self.check_runs()[0]["had_cache"],
                        "the export ran without the cache")
        copied = self.check_app / ".emacs-batch" / "elpa"
        self.assertEqual((copied / "ox-hugo.el").read_text(),
                         "(provide 'ox-hugo)\n")
        self.assertEqual((copied / "run").stat().st_mode & 0o777, 0o750)
        self.assertTrue((self.check_app / ".tools" / "cached").is_file())
        self.assertEqual((tools / "cached").read_text(), "from the cycle")
        self.assertFalse((copied / "run").is_symlink())


if __name__ == "__main__":
    unittest.main()
