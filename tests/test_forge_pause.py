"""Tests of how ``deploy/forge/forge-start`` runs Forgejo and pauses it
for a backup (container-deployment: Forgejo).

The image's entrypoint is a stand-in, ``ENTRYPOINT`` below, which
appends a line to ``$FAKE_ENTRYPOINT_LOG`` at start (``start``, whether
``paused`` exists at that moment, and the two settings the script
exports), one at SIGTERM (``term``, then ``exit``) and one when it ends
by itself (``exit by itself``), and sleeps in between. Switches, all
environment variables: ``FAKE_EXIT_AFTER`` and ``FAKE_EXIT_STATUS`` make
it end by itself; ``FAKE_HOOK_SECONDS`` makes its first start leave
behind a detached process, standing for the hook of a push in flight,
that ignores every signal, records the signals it got, and ends after
that many seconds (``FAKE_HOOK_DONE`` names the file it then writes).

The pause waits until no other process of the container but its init
process and ``forge-start`` itself remains (Forgejo). Tests of that wait
therefore run ``forge-start`` as it runs in the container, in a PID
namespace of its own (``unshare --pid`` in a user namespace) under
``INIT``, a Python init process that starts ``forge-start``, reaps every
orphan, sends it SIGTERM when the file ``term`` appears in its control
directory and writes its exit status to ``status`` there; they skip when
the namespace cannot be made. The tests that do not touch the pause run
``forge-start`` directly.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_forge_deploy import START

ENTRYPOINT = """\
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

log = os.environ["FAKE_ENTRYPOINT_LOG"]
control = Path(os.environ["FAKE_CONTROL"])


def note(text):
    with open(log, "a") as handle:
        handle.write(text + "\\n")


def on_term(number, frame):
    note("term")
    note("exit")
    sys.exit(0)


signal.signal(signal.SIGTERM, on_term)
note("start paused=%s root=%s passwd=%s" % (
    "yes" if (control / "paused").exists() else "no",
    os.environ.get("FORGEJO__server__ROOT_URL"),
    os.environ.get("FORGEJO__database__PASSWD")))
seconds = os.environ.get("FAKE_HOOK_SECONDS")
done = os.environ.get("FAKE_HOOK_DONE")
if seconds and not Path(done + ".started").exists():
    Path(done + ".started").write_text("1")
    subprocess.Popen([sys.executable, "-c", __HOOK__, seconds, done],
                     start_new_session=True)
after = os.environ.get("FAKE_EXIT_AFTER")
began = time.monotonic()
while True:
    time.sleep(0.05)
    if after and time.monotonic() - began >= float(after):
        note("exit by itself")
        sys.exit(int(os.environ.get("FAKE_EXIT_STATUS", "0")))
"""
HOOK = """\
import signal, sys, time
from pathlib import Path
seconds, done = float(sys.argv[1]), Path(sys.argv[2])
def got(number, frame):
    Path(str(done) + ".signalled").write_text(str(number))
for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP,
               signal.SIGQUIT):
    signal.signal(number, got)
end = time.monotonic() + seconds
while time.monotonic() < end:
    time.sleep(0.05)
done.write_text("done")
"""
INIT = """\
import os
import signal
import subprocess
import sys
import time

control = sys.argv[1]
child = subprocess.Popen(sys.argv[2:])
sent = False
while True:
    if not sent and os.path.exists(control + "/term"):
        os.kill(child.pid, signal.SIGTERM)
        sent = True
    try:
        pid, status = os.waitpid(-1, os.WNOHANG)
    except ChildProcessError:
        break
    if pid == child.pid:
        with open(control + "/status", "w") as handle:
            handle.write(str(os.waitstatus_to_exitcode(status)))
        break
    if pid == 0:
        time.sleep(0.05)
"""
UNSHARE = ["unshare", "--user", "--map-root-user", "--pid", "--fork",
           "--mount-proc", "--kill-child"]


def namespaces_work() -> bool:
    """Whether a PID namespace with its own /proc can be made."""
    if shutil.which("unshare") is None:
        return False
    done = subprocess.run([*UNSHARE, "true"], stdin=subprocess.DEVNULL,
                          capture_output=True)
    return done.returncode == 0


def atomic_write(path: Path, text: str) -> None:
    """Write TEXT to PATH so that a reader sees all of it or none."""
    scratch = path.parent.parent / f".scratch-{path.name}"
    scratch.write_text(text)
    os.replace(scratch, path)


class ForgeStartCase(unittest.TestCase):
    """The directories, the stand-in and the ways to start the script."""

    def setUp(self) -> None:
        self.assertTrue(START.is_file(),
                        "deploy/forge/forge-start is missing")
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-start-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.control = self.tmp / "control"
        self.control.mkdir()
        self.watch = self.tmp / "watch"
        self.watch.mkdir()
        self.log = self.tmp / "entrypoint.log"
        self.out = self.tmp / "out.log"
        self.hook_done = self.tmp / "hook"
        (self.tmp / "entrypoint.py").write_text(
            ENTRYPOINT.replace("__HOOK__", repr(HOOK)))
        (self.tmp / "init.py").write_text(INIT)
        self.env = {
            "PATH": os.environ["PATH"],
            "ORGSYNDB_URL": "http://localhost:8080",
            "FORGE_DB_PASSWORD": "x",
            "ORGSYNDB_FORGE_CONTROL": str(self.control),
            "FAKE_ENTRYPOINT_LOG": str(self.log),
            "FAKE_CONTROL": str(self.control),
            "FAKE_HOOK_DONE": str(self.hook_done),
        }
        self.processes: list[subprocess.Popen] = []

    def command(self) -> list[str]:
        return ["sh", str(START), sys.executable,
                str(self.tmp / "entrypoint.py")]

    def launch(self, command: list[str], **env: str) -> subprocess.Popen:
        handle = open(self.out, "a")
        self.addCleanup(handle.close)
        process = subprocess.Popen(
            command, env={**self.env, **env}, stdin=subprocess.DEVNULL,
            stdout=handle, stderr=handle, start_new_session=True)
        self.addCleanup(self.kill, process)
        return process

    def kill(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)

    def start(self, **env: str) -> subprocess.Popen:
        """Run forge-start directly."""
        return self.launch(self.command(), **env)

    def until(self, condition, what: str, seconds: float = 12.0) -> None:
        """Wait until CONDITION holds, or fail saying WHAT did not."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        self.fail(f"{what}: not within {seconds} seconds\n{self.report()}")

    def report(self) -> str:
        def text(path: Path) -> str:
            return path.read_text() if path.exists() else "(none)"
        return (f"entrypoint log:\n{text(self.log)}\n"
                f"output:\n{text(self.out)}\n"
                f"control: {sorted(p.name for p in self.control.iterdir())}")

    # Looking

    def lines(self) -> list[str]:
        return (self.log.read_text().splitlines()
                if self.log.exists() else [])

    def starts(self) -> int:
        return len([l for l in self.lines() if l.startswith("start ")])

    def terms(self) -> int:
        return self.lines().count("term")

    def paused(self) -> str | None:
        try:
            return (self.control / "paused").read_text().strip()
        except OSError:
            return None

    def output(self) -> str:
        return self.out.read_text() if self.out.exists() else ""

    def ask(self, request: str) -> None:
        atomic_write(self.control / "pause", request + "\n")

    def withdraw(self) -> None:
        (self.control / "pause").unlink()


class StartTests(ForgeStartCase):
    """Scenarios that need no PID namespace."""

    def test_the_script_is_posix_shell(self) -> None:
        self.assertIn(START.read_text().splitlines()[0],
                      ("#!/bin/sh", "#!/usr/bin/env sh"))
        done = subprocess.run(["sh", "-n", str(START)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_command_runs_as_a_child(self) -> None:
        """Requirement: Forgejo (runs the image's own entrypoint as a
        child, no longer replacing the script)."""
        text = START.read_text()
        self.assertNotRegex(text, r'(?m)^\s*exec\s+"\$@"')

    def test_the_child_gets_the_exported_settings(self) -> None:
        """Scenario: The start script."""
        process = self.start()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.assertIn("root=http://localhost:8080/git/ passwd=x",
                      self.lines()[0])
        self.kill(process)

    def test_a_stale_acknowledgement_at_start_is_removed(self) -> None:
        """Scenario: A stale acknowledgement at start."""
        (self.control / "paused").write_text("old\n")
        process = self.start()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.assertIn("paused=no", self.lines()[0])
        self.assertIsNone(self.paused())
        self.assertIsNone(process.poll(), "forge-start ended")

    def test_the_status_of_a_child_that_ends_by_itself_is_the_scripts(
            self) -> None:
        """Scenario: Forgejo exits by itself."""
        for status in (3, 1, 0):
            with self.subTest(status=status):
                self.log.unlink(missing_ok=True)
                process = self.start(FAKE_EXIT_AFTER="0.5",
                                     FAKE_EXIT_STATUS=str(status))
                self.assertEqual(process.wait(timeout=20), status,
                                 self.report())
                self.assertEqual(self.starts(), 1, self.report())

    def test_a_signal_stops_the_child_and_the_script(self) -> None:
        """Scenario: Stopping the container (SIGTERM; SIGINT as
        well)."""
        for number in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=number.name):
                self.log.unlink(missing_ok=True)
                process = self.start()
                self.until(lambda: self.starts() == 1,
                           "the child did not start")
                began = time.monotonic()
                process.send_signal(number)
                self.assertEqual(process.wait(timeout=10), 0,
                                 self.report())
                self.assertLess(time.monotonic() - began, 4)
                self.assertEqual(self.terms(), 1, self.report())
                self.assertEqual(self.starts(), 1, self.report())


@unittest.skipUnless(namespaces_work(), "no PID namespace can be made")
class PauseTests(ForgeStartCase):
    """Scenarios: Pausing Forgejo, A pause that lasts too long, and
    the rest of the pause, with forge-start run in a PID namespace."""

    def setUp(self) -> None:
        super().setUp()
        self.ctl = self.tmp / "init"
        self.ctl.mkdir()
        self.process: subprocess.Popen | None = None

    def boot(self, **env: str) -> subprocess.Popen:
        self.process = self.launch(
            [*UNSHARE, sys.executable, str(self.tmp / "init.py"),
             str(self.ctl), *self.command()], **env)
        return self.process

    def status(self) -> str | None:
        try:
            return (self.ctl / "status").read_text().strip()
        except OSError:
            return None

    def terminate(self) -> None:
        (self.ctl / "term").write_text("1")

    def assert_running(self) -> None:
        self.assertIsNone(self.status(), self.report())
        self.assertIsNone(self.process.poll(), self.report())

    def test_pausing_forgejo(self) -> None:
        """Scenario: Pausing Forgejo."""
        self.boot()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.ask("r1")
        self.until(lambda: self.paused() == "r1", "no acknowledgement")
        lines = self.lines()
        self.assertEqual(self.starts(), 1, lines)
        self.assertEqual(lines[1:], ["term", "exit"],
                         "the child was not stopped before `paused`")
        time.sleep(1)
        self.assertEqual(self.starts(), 1, "the child ran during the pause")
        self.assertEqual(self.paused(), "r1")
        self.withdraw()
        self.until(lambda: self.paused() is None, "`paused` stayed")
        self.until(lambda: self.starts() == 2, "the child did not return")
        self.assert_running()

    def test_the_child_returns_with_the_same_settings(self) -> None:
        """Scenario: Pausing Forgejo (the stand-in has started twice)."""
        self.boot()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.ask("r1")
        self.until(lambda: self.paused() == "r1", "no acknowledgement")
        self.withdraw()
        self.until(lambda: self.starts() == 2, "the child did not return")
        starts = [l for l in self.lines() if l.startswith("start ")]
        self.assertIn("paused=no root=http://localhost:8080/git/ passwd=x",
                      starts[1])

    def test_a_second_pause_works_as_the_first_did(self) -> None:
        """Requirement: Forgejo (once `pause` is gone, it starts the
        child again; the next request is answered)."""
        self.boot()
        self.until(lambda: self.starts() == 1, "the child did not start")
        for number, request in enumerate(("r1", "r2"), start=1):
            self.ask(request)
            self.until(lambda: self.paused() == request,
                       f"no acknowledgement of {request}")
            self.assertEqual(self.terms(), number, self.report())
            self.withdraw()
            self.until(lambda: self.starts() == number + 1,
                       "the child did not return")
        self.assert_running()

    def test_a_pause_that_exists_at_start_keeps_the_child_down(
            self) -> None:
        """Requirement: Forgejo (does not start the child while a
        `pause` exists)."""
        self.ask("r0")
        self.boot()
        self.until(lambda: self.paused() == "r0", "no acknowledgement")
        time.sleep(1)
        self.assertEqual(self.starts(), 0, "the child ran in the pause")
        self.withdraw()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.assertIsNone(self.paused())

    def test_a_hook_in_flight_finishes_before_the_acknowledgement(
            self) -> None:
        """Requirement: Forgejo (waits, without signalling them, until
        no other process of the container but its init process and
        itself remains; a process that ends late delays `paused`)."""
        self.boot(FAKE_HOOK_SECONDS="4")
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.until(lambda: Path(f"{self.hook_done}.started").exists(),
                   "the hook did not start")
        self.ask("r1")
        self.until(lambda: self.terms() == 1, "the child was not stopped")
        time.sleep(1)
        self.assertFalse(self.hook_done.exists(), "the hook ended early")
        self.assertIsNone(self.paused(),
                          "acknowledged while a hook was running")
        self.until(lambda: self.paused() == "r1", "no acknowledgement")
        self.assertTrue(self.hook_done.exists(),
                        "acknowledged before the hook ended")
        self.assertFalse(Path(f"{self.hook_done}.signalled").exists(),
                         "the hook was signalled")

    def test_a_process_that_never_ends_leaves_the_pause_unanswered(
            self) -> None:
        """Requirement: Forgejo (a process that never ends leaves the
        request unacknowledged)."""
        self.boot(FAKE_HOOK_SECONDS="600")
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.until(lambda: Path(f"{self.hook_done}.started").exists(),
                   "the hook did not start")
        self.ask("r1")
        self.until(lambda: self.terms() == 1, "the child was not stopped")
        time.sleep(5)
        self.assertIsNone(self.paused())
        self.assertFalse(Path(f"{self.hook_done}.signalled").exists())
        self.assert_running()

    def test_a_pause_that_lasts_too_long_ends(self) -> None:
        """Scenario: A pause that lasts too long."""
        self.boot(ORGSYNDB_FORGE_PAUSE_LIMIT="3")
        self.until(lambda: self.starts() == 1, "the child did not start")
        began = time.monotonic()
        self.ask("r2")
        self.until(lambda: self.paused() == "r2", "no acknowledgement")
        self.until(lambda: self.paused() is None
                   and not (self.control / "pause").exists(),
                   "the pause did not end", seconds=9)
        self.assertLess(time.monotonic() - began, 9)
        self.until(lambda: self.starts() == 2, "the child did not return")
        self.assertRegex(
            self.output().lower(),
            r"pause\b[^\n]*\b(ended|ends|limit|expired|over)\b"
            r"|\b(ended|ends|limit|expired|over)\b[^\n]*\bpause\b")
        self.assert_running()

    def test_a_pause_inside_its_limit_is_kept(self) -> None:
        """Requirement: Forgejo (a pause ends after
        `ORGSYNDB_FORGE_PAUSE_LIMIT` seconds, not before)."""
        self.boot(ORGSYNDB_FORGE_PAUSE_LIMIT="30")
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.ask("r2")
        self.until(lambda: self.paused() == "r2", "no acknowledgement")
        time.sleep(4)
        self.assertEqual(self.paused(), "r2")
        self.assertTrue((self.control / "pause").exists())
        self.assertEqual(self.starts(), 1)

    def test_a_signal_during_a_pause_stops_the_script(self) -> None:
        """Scenario: Stopping the container (while Forgejo is
        paused)."""
        self.boot()
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.ask("r1")
        self.until(lambda: self.paused() == "r1", "no acknowledgement")
        began = time.monotonic()
        self.terminate()
        self.until(lambda: self.status() is not None,
                   "forge-start did not end", seconds=8)
        self.assertEqual(self.status(), "0", self.report())
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual(self.starts(), 1, self.report())

    def test_sigterm_stops_the_child_and_the_script(self) -> None:
        """Scenario: Stopping the container (in the container's own
        process tree)."""
        self.boot()
        self.until(lambda: self.starts() == 1, "the child did not start")
        began = time.monotonic()
        self.terminate()
        self.until(lambda: self.status() is not None,
                   "forge-start did not end", seconds=8)
        self.assertEqual(self.status(), "0", self.report())
        self.assertLess(time.monotonic() - began, 4)
        self.assertEqual(self.terms(), 1, self.report())

    def test_a_child_that_ends_by_itself_ends_the_script_with_its_status(
            self) -> None:
        """Scenario: Forgejo exits by itself."""
        self.boot(FAKE_EXIT_AFTER="0.5", FAKE_EXIT_STATUS="3")
        self.until(lambda: self.status() is not None,
                   "forge-start did not end", seconds=10)
        self.assertEqual(self.status(), "3", self.report())


PUSH_ENTRYPOINT = """\
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

log = os.environ["FAKE_ENTRYPOINT_LOG"]
control = os.environ["FAKE_CONTROL"]
started = Path(log + ".push-started")


def note(text):
    with open(log, "a") as handle:
        handle.write(text + "\\n")


def on_term(number, frame):
    note("term")
    sys.exit(0)


signal.signal(signal.SIGTERM, on_term)
note("start with a push")
if not started.exists():
    started.write_text("1")
    subprocess.Popen([sys.executable, "-c", __PUSH__, "git-receive-pack",
                      control, log, os.environ["FAKE_PUSH_SECONDS"]],
                     start_new_session=True)
while True:
    time.sleep(0.05)
"""
PUSH = """\
import os, sys, time
control, log, seconds = sys.argv[2], sys.argv[3], float(sys.argv[4])
while not os.path.exists(os.path.join(control, "pause")):
    time.sleep(0.05)
time.sleep(seconds)
with open(log, "a") as handle:
    handle.write("push done\\n")
"""


@unittest.skipUnless(namespaces_work(), "no PID namespace can be made")
class PushInFlightTests(ForgeStartCase):
    """Scenario: A push in flight. The stand-in leaves behind a process
    whose command line holds ``git-receive-pack``; it ends a given time
    after ``pause`` appears, writing ``push done`` to the stand-in's
    log."""

    def setUp(self) -> None:
        super().setUp()
        self.ctl = self.tmp / "init"
        self.ctl.mkdir()
        (self.tmp / "push-entrypoint.py").write_text(
            PUSH_ENTRYPOINT.replace("__PUSH__", repr(PUSH)))

    def boot(self, **env: str) -> subprocess.Popen:
        return self.launch(
            [*UNSHARE, sys.executable, str(self.tmp / "init.py"),
             str(self.ctl), "sh", str(START), sys.executable,
             str(self.tmp / "push-entrypoint.py")], **env)

    def test_the_child_is_stopped_only_after_the_push(self) -> None:
        """Scenario: A push in flight."""
        self.boot(FAKE_PUSH_SECONDS="3")
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.until(lambda: Path(f"{self.log}.push-started").exists(),
                   "the push did not start")
        self.ask("r3")
        self.until(lambda: self.paused() == "r3", "no acknowledgement",
                   seconds=20)
        lines = self.lines()
        self.assertIn("push done", lines, self.report())
        self.assertIn("term", lines, self.report())
        self.assertLess(lines.index("push done"), lines.index("term"),
                        "the child was stopped during the push")

    def test_the_child_runs_while_the_push_does(self) -> None:
        """Requirement: Forgejo (it first waits until no push is in
        flight)."""
        self.boot(FAKE_PUSH_SECONDS="4")
        self.until(lambda: self.starts() == 1, "the child did not start")
        self.until(lambda: Path(f"{self.log}.push-started").exists(),
                   "the push did not start")
        self.ask("r3")
        time.sleep(2.5)
        self.assertEqual(self.terms(), 0, self.report())
        self.assertIsNone(self.paused())


if __name__ == "__main__":
    unittest.main()
