"""Tests of the hook ``deploy/forge/push-log`` (container-deployment: Push
log): the post-receive hook of ``lab/collection``, which appends a line
for each update of ``main`` to the push log and wakes the builder.

The hook runs with ``sh`` against a fake wake-up server in a thread, and
is fed the lines Git gives a post-receive hook. It needs neither a Git
repository nor Forgejo: its environment holds ``ORGSYNDB_PUSH_LOG``,
``ORGSYNDB_WAKE_URL``, ``ORGSYNDB_GATE_TOKEN``, ``GITEA_PUSHER_ID`` and
``GITEA_PUSHER_NAME``.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pipeline_support import free_port
from test_forge_gate import FakeCheck

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "deploy" / "forge" / "push-log"
ZERO = "0" * 40
TOKEN = "gate-token"
MAIN = "refs/heads/main"
LINE = re.compile(
    r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ [0-9a-f]{40} \S+ \S+")
NOT_WOKEN = ("Push log: the builder was not woken; it builds this push "
             "at its next check")
NOT_RECORDED = "Push log: cannot record this push:"


def commit(number: int) -> str:
    """A commit ID, 40 hexadecimal digits, for ``number``."""
    return hashlib.sha1(str(number).encode()).hexdigest()


class FakeWake(FakeCheck):
    """The builder's wake-up path as the hook sees it: every request is
    kept in ``requests`` and answered with ``status``, 202 by default."""

    def __init__(self, status: int = 202, delay: float = 0.0) -> None:
        super().__init__(status=status, delay=delay)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/wake"


@unittest.skipIf(shutil.which("curl") is None, "curl not found")
class HookCase(unittest.TestCase):
    """A directory for the push log and a fake wake-up server."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-pushlog-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "pushes.log"
        self.fake = FakeWake()
        self.addCleanup(self.fake.stop)

    def environment(self, **over: str | None) -> dict[str, str]:
        """The environment of a post-receive hook of Forgejo, with the
        hook's settings pointing at the push log and the fake, and a
        pusher; ``over`` replaces a setting, and None removes it."""
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp),
               "ORGSYNDB_PUSH_LOG": str(self.log),
               "ORGSYNDB_WAKE_URL": self.fake.url,
               "ORGSYNDB_GATE_TOKEN": TOKEN,
               "GITEA_PUSHER_ID": "7", "GITEA_PUSHER_NAME": "jkoch"}
        for name, value in over.items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value
        return env

    @staticmethod
    def feed(*updates: tuple[str, str, str]) -> str:
        return "".join(f"{old} {new} {ref}\n" for old, new, ref in updates)

    def hook(self, *updates: tuple[str, str, str],
             **over: str | None) -> subprocess.CompletedProcess:
        """Run the hook with the updates ``(old, new, ref)`` on its
        standard input."""
        return subprocess.run(
            ["sh", str(HOOK)], input=self.feed(*updates), cwd=self.tmp,
            env=self.environment(**over), capture_output=True, text=True,
            timeout=60)

    def lines(self) -> list[str]:
        """The lines of the push log, none when it does not exist."""
        if not self.log.exists():
            return []
        return self.log.read_text(encoding="utf-8").splitlines()

    def requests(self) -> list[dict[str, Any]]:
        return self.fake.requests


class FileTests(unittest.TestCase):
    """Requirement: Push log (the file `deploy/forge/push-log`)."""

    def test_the_hook_is_an_executable_posix_shell_script(self) -> None:
        self.assertTrue(HOOK.is_file(), "deploy/forge/push-log is missing")
        self.assertTrue(HOOK.stat().st_mode & stat.S_IXUSR,
                        "Forgejo runs only executable hooks")
        first = HOOK.read_text(encoding="utf-8").splitlines()[0]
        self.assertIn(first, ("#!/bin/sh", "#!/usr/bin/env sh"))
        done = subprocess.run(["sh", "-n", str(HOOK)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_hook_names_its_settings_and_defaults(self) -> None:
        """Requirement: Push log (`ORGSYNDB_PUSH_LOG`,
        `/var/lib/orgsyndb-pushes/pushes.log` by default;
        `ORGSYNDB_WAKE_URL`, `http://builder:8091/wake` by default)."""
        self.assertTrue(HOOK.is_file(), "deploy/forge/push-log is missing")
        text = HOOK.read_text(encoding="utf-8")
        for name in ("ORGSYNDB_PUSH_LOG", "ORGSYNDB_WAKE_URL",
                     "ORGSYNDB_GATE_TOKEN", "GITEA_PUSHER_ID",
                     "GITEA_PUSHER_NAME", "refs/heads/main",
                     "/var/lib/orgsyndb-pushes/pushes.log",
                     "http://builder:8091/wake", NOT_WOKEN, NOT_RECORDED):
            with self.subTest(name=name):
                self.assertIn(name, text)


class MainTests(HookCase):

    def test_a_push_to_main(self) -> None:
        """Scenario: A push to main."""
        new = commit(1)
        done = self.hook((commit(0), new, MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        (line,) = self.lines()
        time_, found, ident, name = line.split(" ")
        self.assertEqual((found, ident, name), (new, "7", "jkoch"))
        self.assertRegex(time_, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        (request,) = self.requests()
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["path"], "/wake")
        self.assertEqual(request["headers"]["authorization"],
                         f"Bearer {TOKEN}")
        self.assertNotIn("Push log", done.stderr)

    def test_a_line_has_four_fields_separated_by_single_spaces(
            self) -> None:
        """Requirement: Push log (one line `<time> <commit> <id>
        <name>`)."""
        self.hook((commit(0), commit(1), MAIN))
        raw = self.log.read_bytes()
        self.assertTrue(raw.endswith(b"\n"), raw)
        self.assertEqual(raw.count(b"\n"), 1, raw)
        self.assertRegex(raw.decode().rstrip("\n"), f"^{LINE.pattern}$")

    def test_the_time_is_utc_whatever_the_zone(self) -> None:
        """Requirement: Push log (the time in UTC as
        `YYYY-MM-DDTHH:MM:SSZ`)."""
        before = datetime.now(timezone.utc).replace(microsecond=0)
        self.hook((commit(0), commit(1), MAIN), TZ="JST-9")
        after = datetime.now(timezone.utc)
        (line,) = self.lines()
        stamp = datetime.strptime(
            line.split(" ")[0], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        self.assertGreaterEqual(stamp, before - timedelta(seconds=1))
        self.assertLessEqual(stamp, after + timedelta(seconds=1))

    def test_a_line_is_appended_to_the_log(self) -> None:
        """Requirement: Push log (it appends to the file)."""
        self.log.write_text(
            f"2026-11-14T09:30:00Z {commit(5)} 3 abauer\n")
        self.hook((commit(0), commit(1), MAIN))
        self.hook((commit(1), commit(2), MAIN), GITEA_PUSHER_NAME="mwolf",
                  GITEA_PUSHER_ID="9")
        lines = self.lines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].endswith(f"{commit(5)} 3 abauer"))
        self.assertEqual([line.split(" ")[1:] for line in lines[1:]],
                         [[commit(1), "7", "jkoch"],
                          [commit(2), "9", "mwolf"]])

    def test_several_updates_of_main_give_a_line_each_and_one_wake_up(
            self) -> None:
        """Requirement: Push log (a line for each update; after the
        lines it wakes the builder once)."""
        done = self.hook((commit(0), commit(1), MAIN),
                         (commit(1), commit(2), MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([line.split(" ")[1] for line in self.lines()],
                         [commit(1), commit(2)])
        self.assertEqual(len(self.requests()), 1)

    def test_the_wake_up_comes_after_the_lines(self) -> None:
        """Requirement: Push log (after the lines it wakes the builder):
        the log holds the line when the fake receives the request."""
        seen = []
        original = self.fake.requests

        class Watching(list):
            def append(self_, item: Any) -> None:
                seen.append(self.lines())
                super().append(item)

        self.fake.requests = Watching(original)
        self.hook((commit(0), commit(1), MAIN))
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(seen[0]), 1, seen)

    def test_a_new_branch_is_an_update_too(self) -> None:
        """Requirement: Push log (each update of `refs/heads/main` that
        does not delete it): the first push has an old ID of zeros."""
        self.hook((ZERO, commit(1), MAIN))
        (line,) = self.lines()
        self.assertEqual(line.split(" ")[1], commit(1))
        self.assertEqual(len(self.requests()), 1)


class NoPusherTests(HookCase):

    def test_a_push_without_a_pusher(self) -> None:
        """Scenario: No pusher (the environment lacks both)."""
        done = self.hook((commit(0), commit(1), MAIN),
                         GITEA_PUSHER_ID=None, GITEA_PUSHER_NAME=None)
        self.assertEqual(done.returncode, 0, done.stderr)
        (line,) = self.lines()
        self.assertRegex(line, f"^{LINE.pattern}$")
        self.assertEqual(line.split(" ")[2:], ["-", "-"])
        self.assertEqual(len(self.requests()), 1)

    def test_an_empty_pusher_is_a_dash_too(self) -> None:
        """Requirement: Push log (each `-` when unset or empty)."""
        self.hook((commit(0), commit(1), MAIN),
                  GITEA_PUSHER_ID="", GITEA_PUSHER_NAME="")
        (line,) = self.lines()
        self.assertEqual(line.split(" ")[2:], ["-", "-"])

    def test_each_field_is_a_dash_on_its_own(self) -> None:
        """Requirement: Push log (`GITEA_PUSHER_ID` and
        `GITEA_PUSHER_NAME`, each `-` when unset or empty)."""
        self.hook((commit(0), commit(1), MAIN), GITEA_PUSHER_ID=None)
        self.hook((commit(1), commit(2), MAIN), GITEA_PUSHER_NAME="")
        self.assertEqual([line.split(" ")[2:] for line in self.lines()],
                         [["-", "jkoch"], ["7", "-"]])


class OtherUpdateTests(HookCase):

    def test_other_refs_and_deletions(self) -> None:
        """Scenario: Other refs and deletions."""
        done = self.hook((commit(0), commit(1), "refs/heads/draft"),
                         (commit(1), ZERO, MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.requests(), [])
        self.assertEqual(done.stderr, "")

    def test_refs_that_only_look_like_main(self) -> None:
        """Requirement: Push log (updates of other refs append
        nothing)."""
        for ref in ("refs/heads/main2", "refs/heads/maintenance",
                    "refs/heads/feature/main", "refs/tags/main",
                    "refs/tags/v1", "refs/notes/commits", "refs/for/main",
                    "refs/remotes/origin/main", "main"):
            with self.subTest(ref=ref):
                done = self.hook((ZERO, commit(1), ref))
                self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.requests(), [])

    def test_main_among_other_updates(self) -> None:
        """Requirement: Push log (only `main` is logged, whatever else
        is pushed)."""
        done = self.hook((ZERO, commit(1), "refs/heads/draft"),
                         (commit(0), commit(2), MAIN),
                         (ZERO, commit(3), "refs/tags/v1"),
                         (commit(4), ZERO, "refs/heads/old"))
        self.assertEqual(done.returncode, 0, done.stderr)
        (line,) = self.lines()
        self.assertEqual(line.split(" ")[1], commit(2))
        self.assertEqual(len(self.requests()), 1)

    def test_no_update_at_all(self) -> None:
        """Requirement: Push log (it sends no wake-up when it appended
        nothing)."""
        done = self.hook()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.requests(), [])

    def test_a_deleted_main_creates_no_log(
            self) -> None:
        """Requirement: Push log (a deletion appends nothing)."""
        done = self.hook((commit(1), ZERO, MAIN))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse(self.log.exists(), "the log was created")


class BuilderDoesNotAnswerTests(HookCase):
    """Scenario: The builder does not answer."""

    def run_unanswered(self, **over: str | None) -> tuple[Any, float]:
        started = time.monotonic()
        done = self.hook((commit(0), commit(1), MAIN), **over)
        return done, time.monotonic() - started

    def test_an_address_that_refuses_connections(self) -> None:
        done, seconds = self.run_unanswered(
            ORGSYNDB_WAKE_URL=f"http://127.0.0.1:{free_port()}/wake")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertLess(seconds, 8)
        self.assertEqual(len(self.lines()), 1)
        self.assertIn(NOT_WOKEN, done.stderr)

    def test_an_address_that_does_not_answer(self) -> None:
        """Requirement: Push log (waiting at most 5 seconds)."""
        self.fake.delay = 60
        done, seconds = self.run_unanswered()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertLess(seconds, 9)
        self.assertGreater(seconds, 2, "the hook did not wait for it")
        self.assertEqual(len(self.lines()), 1)
        self.assertIn(NOT_WOKEN, done.stderr)

    def test_an_answer_that_is_not_202(self) -> None:
        """Requirement: Push log (when the builder does not answer
        `202`)."""
        for status in (401, 404, 500, 503, 200):
            with self.subTest(status=status):
                self.fake.status = status
                self.log.unlink(missing_ok=True)
                done, _seconds = self.run_unanswered()
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(len(self.lines()), 1)
                self.assertIn(NOT_WOKEN, done.stderr)

    def test_an_answer_of_202_says_nothing(self) -> None:
        done, _seconds = self.run_unanswered()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(NOT_WOKEN, done.stderr)
        self.assertNotIn("Push log", done.stderr)

    def test_an_address_that_does_not_resolve(self) -> None:
        """Requirement: Push log (the push is already accepted)."""
        done, seconds = self.run_unanswered(
            ORGSYNDB_WAKE_URL="http://no-such-host.invalid:8091/wake")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertLess(seconds, 9)
        self.assertEqual(len(self.lines()), 1)
        self.assertIn(NOT_WOKEN, done.stderr)


class UnwritableLogTests(HookCase):
    """Scenario: An unwritable log."""

    def assertNotRecorded(self, done: Any) -> None:
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertRegex(done.stderr,
                         re.escape(NOT_RECORDED) + r"\s*\S")
        self.assertEqual(self.requests(), [])

    def test_a_directory_that_does_not_exist(self) -> None:
        done = self.hook((commit(0), commit(1), MAIN),
                         ORGSYNDB_PUSH_LOG=str(self.tmp / "gone" / "x.log"))
        self.assertNotRecorded(done)
        self.assertFalse((self.tmp / "gone").exists())

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root writes where it pleases")
    def test_a_directory_the_hook_cannot_write(self) -> None:
        directory = self.tmp / "read-only"
        directory.mkdir()
        directory.chmod(0o555)
        self.addCleanup(directory.chmod, 0o755)
        done = self.hook((commit(0), commit(1), MAIN),
                         ORGSYNDB_PUSH_LOG=str(directory / "x.log"))
        self.assertNotRecorded(done)

    def test_a_file_the_hook_cannot_append_to(self) -> None:
        """Requirement: Push log (when it cannot append, the reason goes
        to standard error): the name is a directory."""
        done = self.hook((commit(0), commit(1), MAIN),
                         ORGSYNDB_PUSH_LOG=str(self.tmp))
        self.assertNotRecorded(done)

    def test_the_push_is_still_accepted_with_several_updates(self) -> None:
        """Requirement: Push log (it exits 0, since the push is already
        accepted)."""
        done = self.hook((commit(0), commit(1), MAIN),
                         (commit(1), commit(2), MAIN),
                         ORGSYNDB_PUSH_LOG=str(self.tmp / "gone" / "x.log"))
        self.assertNotRecorded(done)

    def test_other_updates_need_no_log(self) -> None:
        """Requirement: Push log (updates of other refs append
        nothing): they say nothing about an unwritable log."""
        done = self.hook((commit(0), commit(1), "refs/heads/draft"),
                         ORGSYNDB_PUSH_LOG=str(self.tmp / "gone" / "x.log"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(NOT_RECORDED, done.stderr)


class ConcurrentTests(HookCase):
    """Scenario: Concurrent pushes."""

    COUNT = 20

    def test_twenty_hooks_at_once_give_twenty_whole_lines(self) -> None:
        commits = [commit(100 + number) for number in range(self.COUNT)]
        processes = [
            subprocess.Popen(
                ["sh", str(HOOK)], cwd=self.tmp,
                env=self.environment(GITEA_PUSHER_NAME=f"pusher-{number}",
                                     GITEA_PUSHER_ID=str(number + 1)),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
            for number in range(self.COUNT)]
        self.addCleanup(lambda: [p.kill() for p in processes
                                 if p.poll() is None])
        for process, new in zip(processes, commits):
            process.stdin.write(self.feed((ZERO, new, MAIN)))
            process.stdin.close()
        for process in processes:
            process.wait(timeout=60)
            self.assertEqual(process.returncode, 0,
                             process.stderr.read())
        raw = self.log.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        lines = raw.decode("utf-8").splitlines()
        self.assertEqual(len(lines), self.COUNT, lines)
        for line in lines:
            self.assertRegex(line, f"^{LINE.pattern}$")
        self.assertEqual(sorted(line.split(" ")[1] for line in lines),
                         sorted(commits))
        by_commit = {line.split(" ")[1]: line.split(" ")[2:]
                     for line in lines}
        for number, new in enumerate(commits):
            self.assertEqual(by_commit[new],
                             [str(number + 1), f"pusher-{number}"])
        self.assertEqual(len(self.requests()), self.COUNT)
