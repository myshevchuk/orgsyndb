"""Tests of the hook ``deploy/forge/gate`` (container-deployment: Gate):
the pre-receive hook of ``lab/collection``, which sends the pack of the
new tip of ``main`` to the builder's check and refuses the push when the
check does not answer 200.

The hook runs with ``sh`` inside a Git repository, against a fake check
server in a thread, and is fed the lines Git gives a pre-receive hook.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from pipeline_support import free_port
from test_deploy import commit_files, git

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "deploy" / "forge" / "gate"
ZERO = "0" * 40
TOKEN = "gate-token"
MAIN = "refs/heads/main"


class FakeCheck:
    """The builder's check server as the hook sees it: every request it
    receives is kept in ``requests``, a table of its ``method``,
    ``path``, lower-case ``headers`` and ``body`` bytes, and answered
    with ``status`` and the text ``body``. With ``delay`` it waits that
    many seconds, or until ``stop``, before it answers."""

    def __init__(self, status: int = 200, body: str = "",
                 delay: float = 0.0) -> None:
        self.status = status
        self.body = body
        self.delay = delay
        self.requests: list[dict[str, Any]] = []
        self.released = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                data = self.rfile.read(length)
                owner.requests.append({
                    "method": "POST", "path": self.path, "body": data,
                    "headers": {name.lower(): value
                                for name, value in self.headers.items()}})
                if owner.delay:
                    owner.released.wait(owner.delay)
                text = owner.body.encode("utf-8")
                try:
                    self.send_response(owner.status)
                    self.send_header("Content-Length", str(len(text)))
                    self.end_headers()
                    self.wfile.write(text)
                except OSError:
                    pass

            def log_message(self, *args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/check"

    def stop(self) -> None:
        self.released.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


@unittest.skipIf(shutil.which("git") is None, "git not found")
@unittest.skipIf(shutil.which("curl") is None, "curl not found")
class GateHookCase(unittest.TestCase):
    """A bare repository holding two commits, ``self.old`` and
    ``self.new``, where Git runs the hook."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-hook-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        work = self.tmp / "work"
        work.mkdir()
        git(work, "init", "--quiet", "--initial-branch", "main")
        self.old = commit_files(work, {"a.txt": "one\n"})
        self.new = commit_files(work, {"a.txt": "two\n", "b.txt": "x\n"})
        self.repo = self.tmp / "collection.git"
        subprocess.run(["git", "clone", "--quiet", "--bare", str(work),
                        str(self.repo)], check=True)
        self.fake = FakeCheck()
        self.addCleanup(self.fake.stop)

    def environment(self, **over: str | None) -> dict[str, str]:
        """The environment of a pre-receive hook, with the gate's
        settings pointing at the fake; ``over`` replaces a setting, and
        None removes it."""
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp),
               "GIT_CONFIG_NOSYSTEM": "1",
               "ORGSYNDB_GATE_TOKEN": TOKEN,
               "ORGSYNDB_GATE_URL": self.fake.url,
               "ORGSYNDB_GATE_TIMEOUT": "20"}
        for name, value in over.items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value
        return env

    def hook(self, *updates: tuple[str, str, str],
             **over: str | None) -> subprocess.CompletedProcess:
        """Run the hook with the updates ``(old, new, ref)`` on its
        standard input."""
        text = "".join(f"{old} {new} {ref}\n"
                       for old, new, ref in updates)
        return subprocess.run(
            ["sh", str(GATE)], input=text, cwd=self.repo,
            env=self.environment(**over), capture_output=True, text=True,
            timeout=60)

    def requests(self) -> list[dict[str, Any]]:
        return self.fake.requests

    def unpack(self, data: bytes) -> Path:
        """Index the pack ``data`` into a new repository; return it."""
        target = self.tmp / f"received-{len(list(self.tmp.iterdir()))}"
        target.mkdir()
        git(target, "init", "--quiet")
        done = subprocess.run(["git", "-C", str(target), "index-pack",
                               "--stdin"], input=data, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return target


class FileTests(unittest.TestCase):
    """Requirement: Gate (the file `deploy/forge/gate`)."""

    def test_the_hook_is_an_executable_posix_shell_script(self) -> None:
        self.assertTrue(GATE.is_file(), "deploy/forge/gate is missing")
        self.assertTrue(GATE.stat().st_mode & stat.S_IXUSR,
                        "Forgejo runs only executable hooks")
        first = GATE.read_text(encoding="utf-8").splitlines()[0]
        self.assertIn(first, ("#!/bin/sh", "#!/usr/bin/env sh"))
        done = subprocess.run(["sh", "-n", str(GATE)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_hook_names_its_settings_and_defaults(self) -> None:
        """Requirement: Gate (`ORGSYNDB_GATE_URL`, `http://builder:8091/
        check` by default; `ORGSYNDB_GATE_TIMEOUT`, 150 by default)."""
        self.assertTrue(GATE.is_file(), "deploy/forge/gate is missing")
        text = GATE.read_text(encoding="utf-8")
        for name in ("ORGSYNDB_GATE_URL", "ORGSYNDB_GATE_TOKEN",
                     "ORGSYNDB_GATE_TIMEOUT", "X-Orgsyndb-Commit",
                     "http://builder:8091/check", "150",
                     "pack-objects", "refs/heads/main"):
            with self.subTest(name=name):
                self.assertIn(name, text)

    def test_the_hook_sends_with_curl(self) -> None:
        """Requirement: Gate (the image has `curl`)."""
        self.assertTrue(GATE.is_file(), "deploy/forge/gate is missing")
        self.assertIn("curl", GATE.read_text(encoding="utf-8"))


class MainTests(GateHookCase):

    def test_a_push_to_main_is_checked_and_passes_on_200(self) -> None:
        """Scenario: The hook (the update of `main` passes on 200)."""
        done = self.hook((self.old, self.new, MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        (request,) = self.requests()
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["path"], "/check")
        self.assertEqual(request["headers"]["x-orgsyndb-commit"], self.new)
        self.assertEqual(request["headers"]["authorization"],
                         f"Bearer {TOKEN}")

    def test_the_request_is_a_pack_of_the_commit_with_its_history(
            self) -> None:
        """Scenario: The hook (a pack holding the commit)."""
        self.hook((self.old, self.new, MAIN))
        (request,) = self.requests()
        received = self.unpack(request["body"])
        self.assertEqual(git(received, "cat-file", "-t", self.new),
                         "commit")
        self.assertEqual(git(received, "rev-list", self.new).split(),
                         [self.new, self.old])

    def test_the_pack_holds_the_whole_history_of_a_new_branch(self) -> None:
        """Requirement: Gate (the commit with its history, whatever the
        old tip)."""
        self.hook((ZERO, self.new, MAIN))
        (request,) = self.requests()
        received = self.unpack(request["body"])
        self.assertEqual(git(received, "rev-list", "--count", self.new),
                         "2")
        self.assertEqual(git(received, "show", f"{self.new}:b.txt"), "x")

    def test_the_body_is_the_pack_itself(self) -> None:
        """Requirement: Gate (the output of `git pack-objects --stdout
        --revs`, posted as it is)."""
        self.hook((self.old, self.new, MAIN))
        (request,) = self.requests()
        self.assertTrue(request["body"].startswith(b"PACK"),
                        request["body"][:20])
        self.assertEqual(
            request["headers"]["content-length"],
            str(len(request["body"])))

    def test_the_objects_are_read_from_the_quarantine(self) -> None:
        """Requirement: Gate (the hook reads objects from the
        quarantine Forgejo's Git receives a push into): the new commit
        is in a quarantine directory only, the old ones in the
        repository."""
        work = self.tmp / "work"
        tip = commit_files(work, {"c.txt": "three\n"})
        quarantine = self.tmp / "quarantine"
        (quarantine / "objects" / "pack").mkdir(parents=True)
        pack = subprocess.run(
            ["git", "-C", str(work), "pack-objects", "--stdout",
             "--revs"], input=f"{tip}\n^{self.new}\n".encode(),
            capture_output=True, check=True).stdout
        env = {"GIT_DIR": str(self.repo),
               "GIT_OBJECT_DIRECTORY": str(quarantine / "objects"),
               "GIT_ALTERNATE_OBJECT_DIRECTORIES":
                   str(self.repo / "objects"),
               "GIT_QUARANTINE_PATH": str(quarantine)}
        subprocess.run(["git", "index-pack", "--stdin"], input=pack,
                       env={**os.environ, **env}, capture_output=True,
                       check=True)
        self.assertNotEqual(subprocess.run(
            ["git", "-C", str(self.repo), "cat-file", "-e", tip],
            capture_output=True).returncode, 0, "the control fails")
        done = subprocess.run(
            ["sh", str(GATE)], input=f"{self.new} {tip} {MAIN}\n",
            cwd=self.repo, env={**self.environment(), **env},
            capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        (request,) = self.requests()
        self.assertEqual(request["headers"]["x-orgsyndb-commit"], tip)
        received = self.unpack(request["body"])
        self.assertEqual(git(received, "rev-list", tip).split(),
                         [tip, self.new, self.old])

    def test_the_pack_of_the_new_tip_not_the_old_one(self) -> None:
        """Requirement: Gate (the new commit)."""
        self.hook((self.new, self.old, MAIN))
        (request,) = self.requests()
        self.assertEqual(request["headers"]["x-orgsyndb-commit"], self.old)
        received = self.unpack(request["body"])
        self.assertEqual(git(received, "rev-list", self.old).split(),
                         [self.old])
        done = subprocess.run(
            ["git", "-C", str(received), "cat-file", "-e", self.new],
            capture_output=True)
        self.assertNotEqual(done.returncode, 0)


class OtherRefTests(GateHookCase):

    def test_other_refs_pass_without_a_request(self) -> None:
        """Scenario: The hook (the update of `refs/heads/draft` passes
        without a request)."""
        for ref in ("refs/heads/draft", "refs/heads/main2",
                    "refs/heads/maintenance", "refs/heads/feature/main",
                    "refs/tags/main", "refs/tags/v1", "refs/notes/commits",
                    "refs/for/main"):
            with self.subTest(ref=ref):
                done = self.hook((ZERO, self.new, ref))
                self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.requests(), [])

    def test_other_refs_pass_even_when_the_gate_refuses(self) -> None:
        """Requirement: Gate (updates of other refs pass unchecked)."""
        self.fake.status = 422
        done = self.hook((ZERO, self.new, "refs/heads/draft"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.requests(), [])

    def test_other_refs_pass_without_the_token_too(self) -> None:
        """Requirement: Gate (updates of other refs pass unchecked)."""
        done = self.hook((ZERO, self.new, "refs/heads/draft"),
                         ORGSYNDB_GATE_TOKEN=None)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_deletion_of_main_is_not_checked(self) -> None:
        """Requirement: Gate (each update of `refs/heads/main` that does
        not delete it)."""
        done = self.hook((self.new, ZERO, MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.requests(), [])

    def test_main_among_other_updates_is_the_only_one_checked(self) -> None:
        """Requirement: Gate (only `main`, whatever else is pushed)."""
        done = self.hook((ZERO, self.new, "refs/heads/draft"),
                         (self.old, self.new, MAIN),
                         (ZERO, self.new, "refs/tags/v1"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(self.requests()), 1)
        self.fake.status = 422
        self.fake.body = "an error\n"
        again = self.hook((ZERO, self.new, "refs/heads/draft"),
                          (self.old, self.new, MAIN))
        self.assertNotEqual(again.returncode, 0)


class RefusalTests(GateHookCase):

    def test_a_refusal_shows_both_lines(self) -> None:
        """Scenario: The hook (on 422 the hook exits non-zero and its
        standard error holds both lines)."""
        self.fake.status = 422
        self.fake.body = ("OSDB-0002: unknown substance \"x\"\n"
                          "OSDB-0099: not issued by the lab "
                          "application\n")
        done = self.hook((self.old, self.new, MAIN))
        self.assertNotEqual(done.returncode, 0)
        lines = done.stderr.splitlines()
        self.assertIn('OSDB-0002: unknown substance "x"', lines)
        self.assertIn("OSDB-0099: not issued by the lab application",
                      lines)

    def test_the_reason_comes_first(self) -> None:
        """Requirement: Gate (`Gate: <reason>` and then each line of the
        answer's body)."""
        self.fake.status = 422
        self.fake.body = "first error\nsecond error\n"
        done = self.hook((self.old, self.new, MAIN))
        lines = done.stderr.splitlines()
        reasons = [number for number, line in enumerate(lines)
                   if line.startswith("Gate: ")]
        self.assertTrue(reasons, done.stderr)
        self.assertLess(reasons[0], lines.index("first error"))
        self.assertLess(lines.index("first error"),
                        lines.index("second error"))

    def test_a_body_without_a_final_newline_keeps_its_last_line(
            self) -> None:
        """Requirement: Gate (each line of the answer's body)."""
        self.fake.status = 422
        self.fake.body = "first error\nlast error"
        done = self.hook((self.old, self.new, MAIN))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("first error", done.stderr.splitlines())
        self.assertIn("last error", done.stderr.splitlines())

    def test_every_other_status_refuses_with_its_body(self) -> None:
        """Requirement: Gate (on any other answer than 200 the hook
        exits non-zero)."""
        for status in (400, 401, 404, 413, 500, 503):
            with self.subTest(status=status):
                self.fake.status = status
                self.fake.body = f"the answer {status}\n"
                done = self.hook((self.old, self.new, MAIN))
                self.assertNotEqual(done.returncode, 0)
                self.assertIn(f"the answer {status}",
                              done.stderr.splitlines())
                self.assertTrue(any(line.startswith("Gate: ")
                                    for line in done.stderr.splitlines()))

    def test_a_busy_gate_says_to_push_again(self) -> None:
        """Requirement: Gate (the busy answer reaches the pusher)."""
        self.fake.status = 503
        self.fake.body = "the gate is busy; push again\n"
        done = self.hook((self.old, self.new, MAIN))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("the gate is busy; push again",
                      done.stderr.splitlines())

    def test_a_refusal_prints_nothing_to_standard_output(self) -> None:
        """Requirement: Gate (the lines go to standard error)."""
        self.fake.status = 422
        self.fake.body = "an error\n"
        done = self.hook((self.old, self.new, MAIN))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("an error", done.stderr.splitlines())
        self.assertNotIn("an error", done.stdout)

    def test_a_pass_says_nothing_in_error(self) -> None:
        """Requirement: Gate (on `200` the update passes)."""
        done = self.hook((self.old, self.new, MAIN))
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("Gate:", done.stderr)


class NoAnswerTests(GateHookCase):

    def test_no_answer_in_time_refuses(self) -> None:
        """Scenario: The hook (without an answer it exits non-zero and
        says the gate gave no answer)."""
        self.fake.delay = 30
        began = time.monotonic()
        done = self.hook((self.old, self.new, MAIN),
                         ORGSYNDB_GATE_TIMEOUT="1")
        seconds = time.monotonic() - began
        self.assertNotEqual(done.returncode, 0)
        self.assertRegex(done.stderr, r"(?i)gave no answer")
        self.assertTrue(any(line.startswith("Gate: ")
                            for line in done.stderr.splitlines()))
        self.assertLess(seconds, 10)

    def test_the_hook_waits_the_time_it_is_given(self) -> None:
        """Requirement: Gate (waiting at most `ORGSYNDB_GATE_TIMEOUT`
        seconds)."""
        self.fake.delay = 2
        done = self.hook((self.old, self.new, MAIN),
                         ORGSYNDB_GATE_TIMEOUT="20")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_builder_that_is_down_refuses(self) -> None:
        """Requirement: Gate (no answer at all, so that `main` never
        takes an unchecked commit)."""
        done = self.hook(
            (self.old, self.new, MAIN),
            ORGSYNDB_GATE_URL=f"http://127.0.0.1:{free_port()}/check")
        self.assertNotEqual(done.returncode, 0)
        self.assertTrue(any(line.startswith("Gate: ")
                            for line in done.stderr.splitlines()),
                        done.stderr)

    def test_the_url_is_the_setting(self) -> None:
        """Requirement: Gate (`ORGSYNDB_GATE_URL`)."""
        self.hook((self.old, self.new, MAIN),
                  ORGSYNDB_GATE_URL=self.fake.url + "?x=1")
        self.assertEqual(self.requests()[0]["path"], "/check?x=1")


class NoTokenTests(GateHookCase):

    def test_without_the_token_main_is_refused(self) -> None:
        """Requirement: Gate (without `ORGSYNDB_GATE_TOKEN` the hook
        refuses every update of `main`, saying that the gate is not
        configured)."""
        for name, over in (("unset", None), ("empty", "")):
            with self.subTest(token=name):
                done = self.hook((self.old, self.new, MAIN),
                                 ORGSYNDB_GATE_TOKEN=over)
                self.assertNotEqual(done.returncode, 0)
                self.assertRegex(done.stderr, r"(?i)not configured")
                self.assertTrue(any(
                    line.startswith("Gate: ")
                    for line in done.stderr.splitlines()), done.stderr)
        self.assertEqual(self.requests(), [])

    def test_a_new_branch_named_main_is_refused_too(self) -> None:
        """Requirement: Gate (every update of `main`)."""
        done = self.hook((ZERO, self.new, MAIN), ORGSYNDB_GATE_TOKEN=None)
        self.assertNotEqual(done.returncode, 0)
        self.assertRegex(done.stderr, r"(?i)not configured")


class SettingsTests(GateHookCase):

    def test_the_token_goes_in_a_bearer_header_exactly(self) -> None:
        """Requirement: Gate (`Authorization: Bearer
        <ORGSYNDB_GATE_TOKEN>`)."""
        token = "a-token/with+odd=chars"
        self.hook((self.old, self.new, MAIN), ORGSYNDB_GATE_TOKEN=token)
        self.assertEqual(self.requests()[0]["headers"]["authorization"],
                         f"Bearer {token}")

    def test_the_commit_is_the_new_value_of_the_update(self) -> None:
        """Requirement: Gate (`X-Orgsyndb-Commit: <commit>`)."""
        self.hook((self.old, self.new, MAIN))
        self.assertEqual(
            self.requests()[0]["headers"]["x-orgsyndb-commit"], self.new)
        self.assertEqual(len(self.new), 40)


if __name__ == "__main__":
    unittest.main()
