"""Tests of deploy/backup/orgsyndb-backup (container-deployment: Backups).

The script runs against fakes on ``PATH`` for the PostgreSQL programs
(``pg_dump``, ``psql``, ``dropdb``, ``createdb`` and ``pg_restore``),
which record every call in ``$FAKE_LOG``; GNU ``tar`` and ``flock`` are
the real ones. Every path the script reads or writes is a setting
pointing into a temporary directory.

The stand-in for Forgejo is a thread of the test process, ``StandIn``.
It polls the control directory every 0.1 second, writes the id held by
``pause`` into ``paused`` and removes ``paused`` once ``pause`` is gone.
Its switches:

``answer=False``   never answers
``delay=N``        does nothing for the first N seconds after it was
                   started, leaving any `paused` in place
``resume_marker``  when that file appears, removes ``paused`` once and
                   answers nothing further, as a Forgejo that resumed
                   would

The marker is made by the fake ``pg_dump`` when it dumps ``forge`` (set
``FAKE_RESUME_MARKER``), which then waits, up to 5 seconds, for
``paused`` to disappear. So ``paused`` is gone, deterministically,
after the ``forge`` dump and before ``forge.tar`` is written.
"""

import fcntl
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKUP = REPO / "deploy" / "backup" / "orgsyndb-backup"

SET_NAME = re.compile(r"^orgsyndb-(\d{8}T\d{6}Z)$")
STAMP = "%Y%m%dT%H%M%SZ"
CHECKOUT = "git/repositories/lab/collection.git"
LINKS = {
    f"{CHECKOUT}/hooks/pre-receive.d/orgsyndb-gate":
        "/opt/orgsyndb/forge/gate",
    f"{CHECKOUT}/hooks/post-receive.d/orgsyndb-push-log":
        "/opt/orgsyndb/forge/push-log",
}
FILES = {
    "custom/conf/app.ini": ("[security]\nSECRET_KEY = s3\n", 0o640),
    "queues/x": ("pending\n", 0o644),
    ".dotfile": ("dot\n", 0o600),
    f"{CHECKOUT}/HEAD": ("ref: refs/heads/main\n", 0o644),
    f"{CHECKOUT}/config": ("[core]\n\tbare = true\n", 0o644),
    "data/attachments/a file with spaces.txt": ("spaced\n", 0o644),
    "data/attachments/-dash": ("dash\n", 0o600),
}
EMPTY_DIRECTORIES = [f"{CHECKOUT}/objects/pack"]
PRIVATE_DIRECTORIES = {"custom/conf": 0o750}

FAKE_TOOL = """\
#!__PYTHON__
# Fake pg_dump, psql, pg_restore, dropdb and createdb, by the name it is
# run as. It appends to $FAKE_LOG one JSON line: the tool, its arguments,
# its standard input (psql and pg_restore only), the database it names
# with -d, --dbname or a connection string (or, for pg_dump, as its last
# argument), the content of `pause` and `paused` in
# $ORGSYNDB_FORGE_CONTROL at that moment (null when absent), PGPASSWORD,
# the content of the file PGPASSFILE names and, for pg_dump, the names
# in the directory of its output file. pg_dump then writes
# "dump of <database>" and its arguments to the file named by -f; it
# fails for the database $FAKE_FAIL_DB, leaving "PARTIAL". Any tool
# named by $FAKE_FAIL_TOOL fails. For the database forge, pg_dump
# touches $FAKE_RESUME_MARKER, when set, and waits for `paused` to go.
# For the database $FAKE_SLEEP_DB, pg_dump writes its process id to
# $FAKE_SLEEP_PIDFILE and sleeps a minute. With $FAKE_NO_PUSH_MIRROR
# set, psql fails for any SQL naming push_mirror that does not guard
# for the table's existence with to_regclass, as on an empty database.
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

NAME = os.path.basename(sys.argv[0])
ARGS = sys.argv[1:]


def value(short, long):
    for index, arg in enumerate(ARGS):
        if arg in (short, long) and index + 1 < len(ARGS):
            return ARGS[index + 1]
        if arg.startswith(long + "="):
            return arg[len(long) + 1:]
        if arg.startswith(short) and len(arg) > 2 and arg[1] != "-":
            return arg[2:]
    return None


def read(path):
    try:
        return Path(path).read_text()
    except OSError:
        return None


def database():
    name = value("-d", "--dbname")
    if name is None and NAME == "pg_dump":
        rest = [a for i, a in enumerate(ARGS)
                if not a.startswith("-") and (
                    i == 0 or ARGS[i - 1] not in ("-U", "-h", "-p", "-f",
                                                  "-F", "-j", "-d"))]
        name = rest[-1] if rest else None
    if name and "://" in name:
        name = urlsplit(name).path.lstrip("/")
    elif name and "dbname=" in name:
        name = re.search(r"dbname=(\\S+)", name).group(1)
    return name


control = os.environ.get("ORGSYNDB_FORGE_CONTROL", "")
out = value("-f", "--file")
db = database()
passfile = os.environ.get("PGPASSFILE")
record = {
    "tool": NAME, "args": ARGS, "db": db, "out": out,
    "stdin": (sys.stdin.read() if NAME in ("psql", "pg_restore")
              and not sys.stdin.isatty() else ""),
    "pause": read(Path(control, "pause")),
    "paused": read(Path(control, "paused")),
    "password": os.environ.get("PGPASSWORD"),
    "passfile": read(passfile) if passfile else None,
    "siblings": (sorted(p.name for p in Path(out).parent.iterdir())
                 if NAME == "pg_dump" and out else None),
}
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps(record) + "\\n")

if (NAME == "pg_dump" and db is not None
        and db == os.environ.get("FAKE_SLEEP_DB")):
    Path(os.environ["FAKE_SLEEP_PIDFILE"]).write_text(str(os.getpid()))
    time.sleep(60)
if NAME == "psql" and os.environ.get("FAKE_NO_PUSH_MIRROR"):
    text = " ".join(ARGS) + "\\n" + record["stdin"]
    if "push_mirror" in text and "to_regclass" not in text:
        print('ERROR:  relation "push_mirror" does not exist',
              file=sys.stderr)
        sys.exit(1)
if NAME == os.environ.get("FAKE_FAIL_TOOL"):
    print("fake " + NAME + " was told to fail", file=sys.stderr)
    sys.exit(1)
if NAME != "pg_dump":
    sys.exit(0)
marker = os.environ.get("FAKE_RESUME_MARKER")
if marker and db == "forge":
    Path(marker).write_text("resumed")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and Path(control, "paused").exists():
        time.sleep(0.05)
failed = db is not None and db == os.environ.get("FAKE_FAIL_DB")
text = "PARTIAL" if failed else f"dump of {db}\\n" + "\\n".join(ARGS) + "\\n"
if out:
    Path(out).write_text(text)
else:
    sys.stdout.write(text)
if failed:
    print("fake pg_dump of " + str(db) + " was told to fail",
          file=sys.stderr)
    sys.exit(1)
"""


def atomic_write(path: Path, text: str) -> None:
    """Write TEXT to PATH so that a reader sees all of it or none."""
    scratch = path.parent.parent / f".scratch-{path.name}"
    scratch.write_text(text)
    os.replace(scratch, path)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


class StandIn(threading.Thread):
    """Stand-in for Forgejo's side of the pause; see the module text."""

    def __init__(self, control: Path, answer: bool = True,
                 delay: float = 0.0,
                 resume_marker: Path | None = None) -> None:
        super().__init__(daemon=True)
        self.control = control
        self.answer = answer
        self.delay = delay
        self.resume_marker = resume_marker
        self.halt = threading.Event()

    def run(self) -> None:
        began = time.monotonic()
        resumed = False
        pause = self.control / "pause"
        paused = self.control / "paused"
        while not self.halt.wait(0.1):
            if time.monotonic() - began < self.delay:
                continue
            request = (read_text(pause) or "").strip()
            if not request:
                resumed = False
                paused.unlink(missing_ok=True)
                continue
            if resumed:
                continue
            if self.resume_marker and self.resume_marker.exists():
                paused.unlink(missing_ok=True)
                resumed = True
                continue
            if self.answer and (
                    (read_text(paused) or "").strip() != request):
                atomic_write(paused, request + "\n")

    def stop(self) -> None:
        self.halt.set()
        self.join(timeout=5)


def make_tree(root: Path) -> None:
    """The files of a Forgejo directory under ROOT: the application's
    settings and queues, a repository with links in its hooks, files
    with a leading dot, a leading dash and spaces, an empty directory,
    with modes that a restrictive umask would change."""
    for relative, (text, mode) in FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(mode)
    for relative in EMPTY_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative, target in LINKS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
    for directory in sorted(p for p in root.rglob("*")
                            if p.is_dir() and not p.is_symlink()):
        relative = directory.relative_to(root).as_posix()
        directory.chmod(PRIVATE_DIRECTORIES.get(relative, 0o755))


def snapshot(root: Path) -> dict[str, tuple]:
    """Every entry below ROOT with its kind, mode and content (or link
    target), links not followed; ROOT itself is left out."""
    found = {}
    for where, directories, names in os.walk(root):
        for name in [*directories, *names]:
            path = Path(where, name)
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                found[relative] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                found[relative] = ("dir", mode)
            else:
                found[relative] = ("file", mode, path.read_bytes())
    return found


def positionals(args: list[str]) -> list[str]:
    """The arguments of a PostgreSQL program that are neither options
    nor the values of the common ones."""
    takes_value = {"-U", "-h", "-p", "-c", "-f", "-v", "-d", "-o", "-O",
                   "-F", "-j"}
    found = []
    previous = ""
    for arg in args:
        if not arg.startswith("-") and previous not in takes_value:
            found.append(arg)
        previous = arg
    return found


def connects_to(call: dict, name: str) -> bool:
    """Whether the recorded CALL is made on the database NAME: by -d,
    --dbname, a connection string, an argument of its own or a
    ``\\c`` in its input."""
    return (call["db"] == name
            or name in positionals(call["args"])
            or re.search(rf"\\c(onnect)?\s+\"?{re.escape(name)}\b",
                         call["stdin"]) is not None)


def sql(call: dict) -> str:
    """Everything of a recorded CALL that can hold SQL."""
    return " ".join(call["args"]) + "\n" + call["stdin"]


class BackupCase(unittest.TestCase):
    """Fakes, directories and helpers that every group of tests uses."""

    maxDiff = None

    def setUp(self) -> None:
        self.assertTrue(BACKUP.is_file(),
                        "deploy/backup/orgsyndb-backup does not exist")
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-backup-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name in ("pg_dump", "psql", "pg_restore", "dropdb",
                     "createdb"):
            tool = self.bin / name
            tool.write_text(FAKE_TOOL.replace("__PYTHON__", sys.executable))
            tool.chmod(0o755)
        self.log = self.tmp / "calls.log"
        self.dir = self.tmp / "backups"
        self.dir.mkdir()
        self.forge = self.tmp / "forge"
        self.forge.mkdir()
        self.control = self.tmp / "control"
        self.control.mkdir()
        self.pushes = self.tmp / "pushes"
        self.pushes.mkdir()
        self.push_log = self.pushes / "pushes.log"
        self.settings = self.tmp / "orgsyndb.env"
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "FAKE_LOG": str(self.log),
            "POSTGRES_USER": "labuser",
            "POSTGRES_PASSWORD": "s3cret",
            "POSTGRES_DB": "labdb",
            "ORGSYNDB_BACKUP_DIR": str(self.dir),
            "ORGSYNDB_FORGE_DATA": str(self.forge),
            "ORGSYNDB_FORGE_CONTROL": str(self.control),
            "ORGSYNDB_FORGE_PAUSE_TIMEOUT": "20",
            "ORGSYNDB_PUSH_LOG": str(self.push_log),
            "ORGSYNDB_SETTINGS_FILE": str(self.settings),
            "ORGSYNDB_DATA": str(self.data),
        }

    # Fixtures

    def fill_forge(self) -> None:
        make_tree(self.forge)

    def fill_files(self) -> None:
        """A push log and a settings file readable by everyone."""
        self.push_log.write_text("2026-01-01T00:00:00Z abc 7 lena\n")
        self.push_log.chmod(0o644)
        self.settings.write_text("POSTGRES_PASSWORD=s3cret\n")
        self.settings.chmod(0o644)

    def alone(self) -> dict[str, str]:
        """Settings for a deployment without Forgejo: the directory and
        the control directory are missing."""
        return {"ORGSYNDB_FORGE_DATA": str(self.tmp / "no-forge"),
                "ORGSYNDB_FORGE_CONTROL": str(self.tmp / "no-control")}

    def stand_in(self, **switches) -> StandIn:
        thread = StandIn(self.control, **switches)
        thread.start()
        self.addCleanup(thread.stop)
        return thread

    def make_set(self, name: str, parts: tuple[str, ...] = ("lab.dump",),
                 mtime: bool = True) -> Path:
        """A set DIR/NAME with the files PARTS, as the script writes
        them (directory 700, files 600)."""
        target = self.dir / name
        target.mkdir(mode=0o700)
        for part in parts:
            (target / part).write_text(f"old {part}")
            (target / part).chmod(0o600)
        found = SET_NAME.match(name)
        if mtime and found:
            when = datetime.strptime(found.group(1), STAMP).replace(
                tzinfo=timezone.utc).timestamp()
            os.utime(target, (when, when))
        return target

    # Running

    def run_script(self, *args: str, **extra: str
                   ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["sh", str(BACKUP), *args], env={**self.env, **extra},
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=90)

    def once(self, **extra: str) -> subprocess.CompletedProcess:
        return self.run_script("once", **extra)

    def calls(self, *tools: str) -> list[dict]:
        if not self.log.exists():
            return []
        found = [json.loads(line)
                 for line in self.log.read_text().splitlines()]
        return [c for c in found if not tools or c["tool"] in tools]

    # Looking

    def names(self) -> list[str]:
        """The entries of the backup directory but the lock file."""
        return sorted(p.name for p in self.dir.iterdir()
                      if p.name != ".lock")

    def sets(self) -> list[str]:
        return [n for n in self.names() if SET_NAME.match(n)]

    def partials(self) -> list[str]:
        return [n for n in self.names()
                if n.startswith(".orgsyndb-") and n.endswith(".partial")]

    def assert_nothing_written(self) -> None:
        self.assertEqual(self.sets(), [], self.names())
        self.assertEqual(self.partials(), [], self.names())

    def assert_pause_gone(self) -> None:
        self.assertFalse((self.control / "pause").exists(),
                         "the pause request was left behind")

    def output(self, done: subprocess.CompletedProcess) -> str:
        return done.stdout + done.stderr

    def assert_error(self, done: subprocess.CompletedProcess) -> None:
        self.assertEqual(done.returncode, 1, self.output(done))
        self.assertTrue(done.stderr.startswith("orgsyndb-backup: error:"),
                        done.stderr)

    def the_set(self) -> Path:
        self.assertEqual(len(self.sets()), 1, self.names())
        return self.dir / self.sets()[0]


class ScriptTests(BackupCase):
    """Requirement: Backups (the script, its settings and arguments)."""

    def test_the_script_is_posix_shell(self) -> None:
        self.assertTrue(os.access(BACKUP, os.X_OK))
        self.assertIn(BACKUP.read_text().splitlines()[0],
                      ("#!/bin/sh", "#!/usr/bin/env sh"))
        for shell in ("sh", "dash"):
            if shutil.which(shell):
                with self.subTest(shell=shell):
                    done = subprocess.run([shell, "-n", str(BACKUP)],
                                          capture_output=True, text=True)
                    self.assertEqual(done.returncode, 0, done.stderr)

    def test_unknown_subcommand(self) -> None:
        """Scenario: Usage."""
        done = self.run_script("nonsense")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr.lower())
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.names(), [])

    def test_restore_without_a_set(self) -> None:
        """Scenario: Usage."""
        done = self.run_script("restore")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr.lower())
        self.assertEqual(self.calls(), [])

    def test_restore_with_two_sets(self) -> None:
        """Requirement: Backups (`restore` without one set name exits
        2)."""
        self.make_set("orgsyndb-20260101T000000Z")
        self.make_set("orgsyndb-20260102T000000Z")
        done = self.run_script("restore", "orgsyndb-20260101T000000Z",
                               "orgsyndb-20260102T000000Z")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage", done.stderr.lower())
        self.assertEqual(self.calls(), [])

    def test_malformed_numbers(self) -> None:
        """Requirement: Backups (a malformed number exits 1 naming the
        variable)."""
        self.fill_forge()
        for name in ("ORGSYNDB_KEEP_BACKUPS",
                     "ORGSYNDB_FORGE_PAUSE_TIMEOUT"):
            for value in ("many", "1.5", "3x"):
                with self.subTest(name=name, value=value):
                    done = self.once(**{name: value})
                    self.assertEqual(done.returncode, 1, self.output(done))
                    self.assertIn(name, done.stderr)
                    self.assertEqual(self.calls(), [])
                    self.assert_nothing_written()

    def test_malformed_interval(self) -> None:
        """Requirement: Backups (a malformed number exits 1 naming the
        variable)."""
        for value in ("daily", "2.5", "1h"):
            with self.subTest(value=value):
                done = self.run_script(
                    "run", ORGSYNDB_BACKUP_HOURS=value)
                self.assertEqual(done.returncode, 1, self.output(done))
                self.assertIn("ORGSYNDB_BACKUP_HOURS", done.stderr)

    def test_the_dumps_are_custom_format_of_the_right_databases(
            self) -> None:
        """Requirement: Backups (`pg_dump` in custom format of
        `POSTGRES_DB` as `POSTGRES_USER` with `POSTGRES_PASSWORD`, and
        of the database `forge` as `POSTGRES_USER`)."""
        self.fill_forge()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        dumps = self.calls("pg_dump")
        self.assertEqual([c["db"] for c in dumps], ["labdb", "forge"])
        for call in dumps:
            with self.subTest(database=call["db"]):
                args = " ".join(call["args"])
                self.assertRegex(args, r"(?:^| )(?:-Fc|-F c|--format[= ]"
                                       r"c(?:ustom)?)(?: |$)")
                self.assertRegex(
                    args, r"(?:^| )(?:-h ?|--host[= ])db(?: |$)"
                          r"|host=db\b|@db\b")
                self.assertIn("labuser", args)
                self.assertIn("s3cret", f"{call['password']}"
                                        f"{call['passfile']}{args}")


class BackupSetTests(BackupCase):
    """Scenarios: A backup set, Everything inside the pause."""

    def setUp(self) -> None:
        super().setUp()
        self.fill_forge()
        self.fill_files()

    def test_a_backup_set(self) -> None:
        """Scenario: A backup set."""
        self.stand_in()
        before = datetime.now(timezone.utc)
        done = self.once()
        after = datetime.now(timezone.utc)
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.names(), self.sets())
        found = self.the_set()
        stamp = datetime.strptime(
            SET_NAME.match(found.name).group(1), STAMP
        ).replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(stamp, before - timedelta(seconds=2))
        self.assertLessEqual(stamp, after + timedelta(seconds=2))
        self.assertEqual(
            sorted(p.name for p in found.iterdir()),
            ["forge.dump", "forge.tar", "lab.dump", "orgsyndb.env",
             "pushes.log"])
        self.assertTrue((found / "lab.dump").read_text().startswith(
            "dump of labdb\n"))
        self.assertTrue((found / "forge.dump").read_text().startswith(
            "dump of forge\n"))
        self.assertEqual((found / "pushes.log").read_text(),
                         self.push_log.read_text())
        self.assertEqual((found / "orgsyndb.env").read_text(),
                         self.settings.read_text())
        self.assert_pause_gone()

    def test_the_archive_holds_the_whole_directory(self) -> None:
        """Scenario: A backup set (`forge.tar` holding `custom/conf/
        app.ini`, `queues/x`, the repository's files and the link as a
        link); Requirement: Backups (numeric owners, modes and symbolic
        links kept)."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        with tarfile.open(self.the_set() / "forge.tar") as archive:
            members = {m.name.removeprefix("./").rstrip("/"): m
                       for m in archive.getmembers()}
            for relative, (text, mode) in FILES.items():
                with self.subTest(file=relative):
                    member = members[relative]
                    self.assertTrue(member.isreg())
                    self.assertEqual(member.mode & 0o7777, mode)
                    self.assertEqual(
                        archive.extractfile(member).read().decode(), text)
            for relative, target in LINKS.items():
                with self.subTest(link=relative):
                    self.assertTrue(members[relative].issym())
                    self.assertEqual(members[relative].linkname, target)
            for relative in EMPTY_DIRECTORIES:
                self.assertTrue(members[relative].isdir())
            self.assertEqual(members["custom/conf"].mode & 0o7777, 0o750)
            for member in members.values():
                with self.subTest(member=member.name):
                    self.assertEqual(member.uid, os.getuid())
                    self.assertEqual(member.uname, "",
                                     "owners are not numeric")

    def test_no_file_of_the_set_is_readable_by_others(self) -> None:
        """Scenario: A backup set (no file readable by others);
        Requirement: Backups (readable by its owner only)."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        found = self.the_set()
        self.assertEqual(stat.S_IMODE(found.stat().st_mode) & 0o077, 0)
        for path in found.iterdir():
            with self.subTest(file=path.name):
                self.assertEqual(
                    stat.S_IMODE(path.stat().st_mode) & 0o077, 0)

    def test_nothing_but_the_set_is_left_behind(self) -> None:
        """Scenario: A backup set (`pause` is gone, the partial set
        renamed)."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.names(), self.sets())
        self.assertEqual(self.partials(), [])
        self.assert_pause_gone()

    def test_both_databases_are_dumped_while_paused_holds_the_id(
            self) -> None:
        """Scenario: Everything inside the pause."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        dumps = self.calls("pg_dump")
        self.assertEqual(len(dumps), 2, dumps)
        for call in dumps:
            with self.subTest(database=call["db"]):
                request = (call["pause"] or "").strip()
                self.assertTrue(request, "no pause request at the dump")
                self.assertEqual((call["paused"] or "").strip(), request)

    def test_the_parts_are_written_in_order(self) -> None:
        """Requirement: Backups (in this order: `lab.dump`,
        `pushes.log`, `forge.dump`)."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(len(self.calls("pg_dump")), 2, self.calls())
        lab, forge = self.calls("pg_dump")
        self.assertEqual((lab["db"], forge["db"]), ("labdb", "forge"))
        self.assertNotIn("pushes.log", lab["siblings"])
        self.assertNotIn("forge.dump", lab["siblings"])
        self.assertIn("lab.dump", forge["siblings"])
        self.assertIn("pushes.log", forge["siblings"])
        self.assertNotIn("forge.tar", forge["siblings"])

    def test_a_pause_left_by_a_crashed_run_is_replaced(self) -> None:
        """Requirement: Backups (replacing a `pause` a crashed run
        left)."""
        (self.control / "pause").write_text("crashed\n")
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        for call in self.calls("pg_dump"):
            with self.subTest(database=call["db"]):
                self.assertNotEqual((call["pause"] or "").strip(),
                                    "crashed")
                self.assertEqual((call["paused"] or "").strip(),
                                 (call["pause"] or "").strip())
        self.assert_pause_gone()

    def test_a_stale_acknowledgement_is_waited_out(self) -> None:
        """Scenario: A stale acknowledgement (an acknowledgement of
        another id is not the run's)."""
        (self.control / "paused").write_text("old\n")
        self.stand_in(delay=2.0)
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        dumps = self.calls("pg_dump")
        self.assertEqual(len(dumps), 2, dumps)
        for call in dumps:
            with self.subTest(database=call["db"]):
                self.assertNotEqual((call["paused"] or "").strip(), "old")
                self.assertEqual((call["paused"] or "").strip(),
                                 (call["pause"] or "").strip())

    def test_each_run_asks_with_an_id_of_its_own(self) -> None:
        """Requirement: Backups (a request id unique to the run)."""
        self.stand_in()
        ids = []
        for _ in range(2):
            done = self.once()
            self.assertEqual(done.returncode, 0, self.output(done))
            ids.append((self.calls("pg_dump")[-1]["pause"] or "").strip())
        self.assertTrue(all(ids), ids)
        self.assertEqual(len(set(ids)), 2, ids)
        self.assertEqual(len(self.sets()), 2, self.names())

    def test_a_missing_push_log_leaves_it_out_of_the_set(self) -> None:
        """Requirement: Backups (copies the push log, when it
        exists)."""
        self.push_log.unlink()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(
            sorted(p.name for p in self.the_set().iterdir()),
            ["forge.dump", "forge.tar", "lab.dump", "orgsyndb.env"])

    def test_a_missing_settings_file_leaves_it_out_of_the_set(
            self) -> None:
        """Requirement: Backups (copies `ORGSYNDB_SETTINGS_FILE` as
        `orgsyndb.env`, when it exists)."""
        self.settings.unlink()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(
            sorted(p.name for p in self.the_set().iterdir()),
            ["forge.dump", "forge.tar", "lab.dump", "pushes.log"])


FAKE_ID = """\
#!/bin/sh
# Fake id: says the caller is root for -u, otherwise the real answer.
if [ "${1-}" = -u ]; then echo 0; else exec /usr/bin/id "$@"; fi
"""
FAKE_CHOWN = """\
#!/bin/sh
# Fake chown: appends its arguments and whether `pause` exists in
# $ORGSYNDB_FORGE_CONTROL to $FAKE_CHOWN_LOG, and changes nothing.
state=none
[ -e "$ORGSYNDB_FORGE_CONTROL/pause" ] && state=pause
echo "$state $*" >> "$FAKE_CHOWN_LOG"
"""


class ControlOwnerTests(BackupCase):
    """Scenario: The control directory's owner."""

    def setUp(self) -> None:
        super().setUp()
        self.fill_forge()
        self.fill_files()
        self.chown_log = self.tmp / "chown.log"
        self.env["FAKE_CHOWN_LOG"] = str(self.chown_log)
        chown = self.bin / "chown"
        chown.write_text(FAKE_CHOWN)
        chown.chmod(0o755)

    def as_root(self) -> None:
        """Make the script believe it runs as root."""
        fake = self.bin / "id"
        fake.write_text(FAKE_ID)
        fake.chmod(0o755)

    def chowns(self) -> list[list[str]]:
        if not self.chown_log.exists():
            return []
        return [line.split() for line in
                self.chown_log.read_text().splitlines()]

    def test_the_script_hands_the_control_directory_to_uid_1000(
            self) -> None:
        """Scenario: The control directory's owner (read)."""
        text = BACKUP.read_text()
        self.assertRegex(text, r"\bid -u\b")
        self.assertRegex(
            text, r'(?m)\bchown\b[^\n]*\b1000(:1000)?\b[^\n]*'
                  r'"\$\{?control\}?"')

    def test_as_root_the_owner_changes_before_pause_is_written(
            self) -> None:
        """Scenario: The control directory's owner (as root, before
        writing `pause`)."""
        self.as_root()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        found = [c for c in self.chowns() if str(self.control) in c]
        self.assertTrue(found, self.chowns())
        state, *args = found[0]
        self.assertEqual(state, "none", "pause was written first")
        self.assertTrue(any(re.fullmatch(r"1000(:1000)?", a)
                            for a in args), args)

    @unittest.skipIf(os.geteuid() == 0, "runs as root")
    def test_not_as_root_the_owner_is_left_alone(self) -> None:
        """Requirement: Backups (when run as root)."""
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.chowns(), [])

    def test_without_forgejo_the_control_directory_is_left_alone(
            self) -> None:
        """Requirement: Backups (without the Forgejo directory, it
        pauses nothing)."""
        self.as_root()
        self.env.update(self.alone())
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.chowns(), [])
        self.assertFalse((self.tmp / "no-control").exists())


@unittest.skipUnless(os.geteuid() == 0, "needs root")
class ControlOwnerAsRootTests(BackupCase):
    """Scenario: The control directory's owner (really as root)."""

    def test_the_control_directory_belongs_to_uid_1000(self) -> None:
        self.fill_forge()
        self.fill_files()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        info = self.control.stat()
        self.assertEqual((info.st_uid, info.st_gid), (1000, 1000))


class BackupFailureTests(BackupCase):
    """Scenarios: A stale acknowledgement, Forgejo resumes during the
    backup, A failed part."""

    def setUp(self) -> None:
        super().setUp()
        self.fill_forge()
        self.fill_files()

    def assert_failed_cleanly(self, done) -> None:
        self.assert_error(done)
        self.assert_pause_gone()
        self.assert_nothing_written()

    def test_a_stale_acknowledgement(self) -> None:
        """Scenario: A stale acknowledgement."""
        (self.control / "paused").write_text("old\n")
        began = time.monotonic()
        done = self.once(ORGSYNDB_FORGE_PAUSE_TIMEOUT="2")
        elapsed = time.monotonic() - began
        self.assert_failed_cleanly(done)
        self.assertLess(elapsed, 6)
        self.assertGreaterEqual(elapsed, 1.5)
        lowered = done.stderr.lower()
        self.assertIn("forgejo", lowered)
        self.assertIn("pause", lowered)
        self.assertEqual(self.calls(), [], "dumped without a pause")

    def test_forgejo_that_never_answers(self) -> None:
        """Requirement: Backups (`paused` does not hold the request id
        in time)."""
        self.stand_in(answer=False)
        began = time.monotonic()
        done = self.once(ORGSYNDB_FORGE_PAUSE_TIMEOUT="2")
        elapsed = time.monotonic() - began
        self.assert_failed_cleanly(done)
        self.assertLess(elapsed, 6)
        self.assertIn("pause", done.stderr.lower())
        self.assertEqual(self.calls(), [], "dumped without a pause")

    def test_forgejo_resumes_during_the_backup(self) -> None:
        """Scenario: Forgejo resumes during the backup."""
        marker = self.tmp / "resumed"
        self.stand_in(resume_marker=marker)
        done = self.once(FAKE_RESUME_MARKER=str(marker))
        self.assert_failed_cleanly(done)
        self.assertIn("resumed during the backup", done.stderr.lower())
        self.assertEqual([c["db"] for c in self.calls("pg_dump")],
                         ["labdb", "forge"])

    def test_a_failed_forge_dump(self) -> None:
        """Scenario: A failed part."""
        self.stand_in()
        done = self.once(FAKE_FAIL_DB="forge")
        self.assert_failed_cleanly(done)

    def test_a_failed_lab_dump(self) -> None:
        """Scenario: A failed part (the first part)."""
        self.stand_in()
        done = self.once(FAKE_FAIL_DB="labdb")
        self.assert_failed_cleanly(done)

    @unittest.skipIf(os.geteuid() == 0, "root reads every directory")
    def test_a_failed_archive(self) -> None:
        """Scenario: A failed part (the archive of the directory)."""
        hidden = self.forge / "hidden"
        hidden.mkdir()
        (hidden / "x").write_text("x")
        hidden.chmod(0)
        self.addCleanup(hidden.chmod, 0o755)
        self.stand_in()
        done = self.once()
        self.assert_failed_cleanly(done)

    def test_a_failed_run_prunes_nothing(self) -> None:
        """Requirement: Backups (after a complete set, all but the
        newest are removed)."""
        names = [f"orgsyndb-202001{day:02d}T030000Z"
                 for day in range(1, 15)]
        for name in names:
            self.make_set(name)
        self.stand_in()
        done = self.once(FAKE_FAIL_DB="forge")
        self.assert_error(done)
        self.assertEqual(self.sets(), names)
        self.assertEqual(self.partials(), [])

    def test_the_failure_names_the_reason(self) -> None:
        """Requirement: Backups (`orgsyndb-backup: error:` and the
        reason on stderr)."""
        self.stand_in()
        done = self.once(FAKE_FAIL_DB="forge")
        self.assertIn("forge", done.stderr)


class PruningTests(BackupCase):
    """Scenario: Pruning sets."""

    OLD = [f"orgsyndb-202001{day:02d}T030000Z" for day in range(1, 15)]

    def setUp(self) -> None:
        super().setUp()
        self.env.update(self.alone())
        self.fill_files()
        for name in self.OLD:
            self.make_set(name)
        self.partial = self.dir / ".orgsyndb-20200102T000000Z.partial"
        self.partial.mkdir(mode=0o700)
        (self.partial / "lab.dump").write_text("half")
        self.old_dump = self.dir / "lab-20260101T000000Z.dump"
        self.old_dump.write_text("old")

    def test_the_oldest_set_and_the_partial_set_go(self) -> None:
        """Scenario: Pruning sets."""
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        remaining = self.sets()
        self.assertEqual(len(remaining), 14, remaining)
        self.assertNotIn(self.OLD[0], remaining)
        self.assertIn(self.OLD[1], remaining)
        self.assertEqual(remaining[:13], self.OLD[1:])
        self.assertTrue(SET_NAME.match(remaining[-1]))
        self.assertNotIn(remaining[-1], self.OLD)
        self.assertEqual(self.partials(), [])
        self.assertFalse(self.partial.exists())
        self.assertEqual(self.old_dump.read_text(), "old")

    def test_keep_backups_sets_the_count(self) -> None:
        """Requirement: Backups (all but the `ORGSYNDB_KEEP_BACKUPS`
        newest sets are removed; other files are left alone)."""
        (self.dir / "notes.txt").write_text("keep")
        (self.dir / "lab-latest.txt").write_text("keep")
        done = self.once(ORGSYNDB_KEEP_BACKUPS="3")
        self.assertEqual(done.returncode, 0, self.output(done))
        remaining = self.sets()
        self.assertEqual(len(remaining), 3, remaining)
        self.assertEqual(remaining[:2], self.OLD[-2:])
        self.assertEqual(self.partials(), [])
        for name in ("notes.txt", "lab-latest.txt",
                     self.old_dump.name):
            with self.subTest(file=name):
                self.assertIn(name, self.names())

    def test_a_set_is_removed_with_what_it_holds(self) -> None:
        """Requirement: Backups (the sets are removed, not only their
        directories)."""
        self.make_set("orgsyndb-20190101T000000Z",
                      ("lab.dump", "forge.dump", "forge.tar",
                       "pushes.log", "orgsyndb.env"))
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertNotIn("orgsyndb-20190101T000000Z", self.names())
        self.assertNotIn(self.OLD[0], self.names())

    def test_old_dumps_are_never_counted_or_removed(self) -> None:
        """Requirement: Backups (other files in the directory are left
        alone)."""
        for day in range(2, 20):
            (self.dir / f"lab-202601{day:02d}T000000Z.dump").write_text("x")
        done = self.once(ORGSYNDB_KEEP_BACKUPS="1")
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(len(self.sets()), 1)
        self.assertEqual(
            len([n for n in self.names() if n.startswith("lab-")]), 19)


class OneRunAtATimeTests(BackupCase):
    """Scenario: One run at a time."""

    def setUp(self) -> None:
        super().setUp()
        self.env.update(self.alone())
        self.fill_files()

    def start(self, *args: str) -> subprocess.Popen:
        out = open(self.tmp / "out.log", "w")
        self.addCleanup(out.close)
        process = subprocess.Popen(
            ["sh", str(BACKUP), *args], env=self.env,
            stdin=subprocess.DEVNULL, stdout=out, stderr=out,
            start_new_session=True)
        self.addCleanup(self.stop, process)
        return process

    def stop(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)

    def test_a_run_waits_for_the_lock(self) -> None:
        """Scenario: One run at a time (the first part)."""
        with open(self.dir / ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            process = self.start("once")
            time.sleep(2)
            self.assertIsNone(process.poll(), "the run did not wait")
            self.assertEqual(self.sets(), [], self.names())
            self.assertEqual(self.partials(), [], self.names())
            self.assertEqual(self.calls(), [])
            fcntl.flock(lock, fcntl.LOCK_UN)
        self.assertEqual(process.wait(timeout=30), 0,
                         (self.tmp / "out.log").read_text())
        self.assertEqual(len(self.sets()), 1, self.names())

    def test_two_runs_in_a_row(self) -> None:
        """Scenario: One run at a time (the second part)."""
        for _ in range(2):
            done = self.once()
            self.assertEqual(done.returncode, 0, self.output(done))
        found = self.sets()
        self.assertEqual(len(found), 2, self.names())
        for name in found:
            with self.subTest(set=name):
                self.assertTrue((self.dir / name / "lab.dump").is_file())

    def test_two_runs_at_once_write_two_sets(self) -> None:
        """Requirement: Backups (runs follow one another; a name that
        exists waits for the next second)."""
        first = self.start("once")
        second = self.start("once")
        self.assertEqual(first.wait(timeout=60), 0,
                         (self.tmp / "out.log").read_text())
        self.assertEqual(second.wait(timeout=60), 0,
                         (self.tmp / "out.log").read_text())
        self.assertEqual(len(self.sets()), 2, self.names())
        self.assertEqual(self.partials(), [])


class WithoutForgejoTests(BackupCase):
    """Scenario: Without Forgejo."""

    def setUp(self) -> None:
        super().setUp()
        self.env.update(self.alone())
        self.fill_files()

    def test_the_set_holds_the_lab_dump_and_the_settings(self) -> None:
        """Scenario: Without Forgejo."""
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        found = self.the_set()
        self.assertEqual(sorted(p.name for p in found.iterdir()),
                         ["lab.dump", "orgsyndb.env"])
        self.assertTrue((found / "lab.dump").read_text().startswith(
            "dump of labdb\n"))
        self.assertEqual([c["db"] for c in self.calls("pg_dump")],
                         ["labdb"])

    def test_no_pause_is_made_and_the_output_says_so(self) -> None:
        """Scenario: Without Forgejo."""
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertFalse((self.tmp / "no-control").exists(),
                         "a pause was made")
        lowered = self.output(done).lower()
        self.assertIn("forgejo", lowered)
        self.assertIn("not backed up", lowered)

    @unittest.skipIf(os.geteuid() == 0, "root writes everywhere")
    def test_no_pause_is_tried_in_a_control_directory_that_exists(
            self) -> None:
        """Requirement: Backups (without the Forgejo directory, it
        pauses nothing)."""
        self.control.chmod(0o500)
        self.addCleanup(self.control.chmod, 0o755)
        self.env["ORGSYNDB_FORGE_CONTROL"] = str(self.control)
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(sorted(p.name for p in self.the_set().iterdir()),
                         ["lab.dump", "orgsyndb.env"])
        self.assertEqual(list(self.control.iterdir()), [])


class RunTests(BackupCase):
    """Requirement: Backups (`run` writes a set as `once` does, starting
    at once, logs a failed run and keeps going)."""

    def setUp(self) -> None:
        super().setUp()
        self.env.update(self.alone())
        self.fill_files()

    def start(self, *args: str, **extra: str) -> subprocess.Popen:
        self.out = open(self.tmp / "out.log", "w")
        self.err = open(self.tmp / "err.log", "w")
        self.addCleanup(self.out.close)
        self.addCleanup(self.err.close)
        process = subprocess.Popen(
            ["sh", str(BACKUP), *args], env={**self.env, **extra},
            stdin=subprocess.DEVNULL, stdout=self.out, stderr=self.err,
            start_new_session=True)
        self.addCleanup(self.stop, process)
        return process

    def stop(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)

    def wait_for(self, condition, process: subprocess.Popen,
                 seconds: float = 20.0) -> bool:
        """Wait until CONDITION holds; give up when the script exits or
        the time is up."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return True
            if process.poll() is not None:
                return condition()
            time.sleep(0.1)
        return False

    def logged(self) -> str:
        return ((self.tmp / "out.log").read_text()
                + (self.tmp / "err.log").read_text())

    def test_run_writes_a_set_at_once_and_keeps_going(self) -> None:
        process = self.start()
        self.assertTrue(self.wait_for(self.sets, process), self.logged())
        self.assertTrue(
            (self.dir / self.sets()[0] / "lab.dump").is_file())
        time.sleep(1)
        self.assertIsNone(process.poll(), self.logged())

    def test_run_logs_a_failed_run_and_keeps_going(self) -> None:
        process = self.start("run", FAKE_FAIL_DB="labdb")
        self.assertTrue(self.wait_for(
            lambda: self.logged().strip(), process), "nothing was logged")
        time.sleep(1)
        self.assertIsNone(process.poll(), self.logged())
        self.assertIn("error", self.logged().lower())
        self.assert_nothing_written()


UNSHARE = ["unshare", "--user", "--map-root-user", "--pid", "--fork",
           "--mount-proc", "--kill-child"]


def namespaces_work() -> bool:
    """Whether a PID namespace with its own /proc can be made."""
    if shutil.which("unshare") is None:
        return False
    done = subprocess.run([*UNSHARE, "true"], stdin=subprocess.DEVNULL,
                          capture_output=True)
    return done.returncode == 0


def running(pid: int) -> bool:
    """Whether the process PID exists and is not a zombie."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1]
    except OSError:
        return False
    return state.split()[0] != "Z"


def host_pid(namespace_of: int, inner: int) -> int | None:
    """The host's id of the process that has the id INNER in the PID
    namespace of the process NAMESPACE_OF, or None."""
    try:
        wanted = os.readlink(f"/proc/{namespace_of}/ns/pid")
    except OSError:
        return None
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if os.readlink(entry / "ns" / "pid") != wanted:
                continue
            for line in (entry / "status").read_text().splitlines():
                if line.startswith("NSpid:") and line.split()[-1] == str(
                        inner):
                    return int(entry.name)
        except OSError:
            continue
    return None


class StoppingTests(BackupCase):
    """Scenario: Stopping a backup. The fake ``pg_dump`` of ``forge``
    sleeps inside the pause until the script is sent SIGTERM."""

    def setUp(self) -> None:
        super().setUp()
        self.fill_forge()
        self.fill_files()
        self.pidfile = self.tmp / "pg_dump.pid"
        self.env.update(FAKE_SLEEP_DB="forge",
                        FAKE_SLEEP_PIDFILE=str(self.pidfile))
        self.stand_in()
        self.pids: list[int] = []
        self.addCleanup(self.kill_leftovers)

    def kill_leftovers(self) -> None:
        for pid in self.pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    def launch(self, command: list[str]) -> subprocess.Popen:
        out = open(self.tmp / "out.log", "w")
        self.addCleanup(out.close)
        process = subprocess.Popen(
            command, env=self.env, stdin=subprocess.DEVNULL, stdout=out,
            stderr=out, start_new_session=True)
        self.addCleanup(self.stop, process)
        return process

    def stop(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)

    def sleeping_dump(self, process: subprocess.Popen) -> int:
        """Wait until the fake dump of forge sleeps; return its pid as
        the process sees it."""
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not self.pidfile.exists():
            self.assertIsNone(process.poll(),
                              (self.tmp / "out.log").read_text())
            time.sleep(0.05)
        self.assertTrue(self.pidfile.exists(), "the dump did not start")
        self.assertTrue((self.control / "pause").exists())
        return int(self.pidfile.read_text())

    def host_dump(self, process: subprocess.Popen) -> int:
        """Wait until the fake dump of forge sleeps; return its pid,
        to be killed at the end of the test."""
        pid = self.sleeping_dump(process)
        self.pids.append(pid)
        return pid

    def assert_stopped(self, ended, dump: int) -> None:
        """Within about 3 seconds ENDED holds, `pause` is gone, no
        partial set remains and the fake dump no longer runs."""
        began = time.monotonic()
        while time.monotonic() - began < 3.5 and not ended():
            time.sleep(0.05)
        self.assertTrue(ended(), "the script did not exit in time: "
                        + (self.tmp / "out.log").read_text())
        self.assert_pause_gone()
        self.assert_nothing_written()
        time.sleep(0.2)
        self.assertFalse(running(dump), "the fake pg_dump still runs")

    def test_sigterm_stops_once(self) -> None:
        """Scenario: Stopping a backup (`once`)."""
        process = self.launch(["sh", str(BACKUP), "once"])
        dump = self.host_dump(process)
        process.send_signal(signal.SIGTERM)
        self.assert_stopped(lambda: process.poll() is not None, dump)

    def test_sigterm_stops_run(self) -> None:
        """Scenario: Stopping a backup (`run`)."""
        process = self.launch(["sh", str(BACKUP), "run"])
        dump = self.host_dump(process)
        process.send_signal(signal.SIGTERM)
        self.assert_stopped(lambda: process.poll() is not None, dump)

    def test_sigint_and_sighup_stop_once(self) -> None:
        """Requirement: Backups (SIGINT or SIGHUP as well)."""
        for number in (signal.SIGINT, signal.SIGHUP):
            with self.subTest(signal=number.name):
                self.pidfile.unlink(missing_ok=True)
                process = self.launch(["sh", str(BACKUP), "once"])
                dump = self.host_dump(process)
                process.send_signal(number)
                self.assert_stopped(lambda: process.poll() is not None,
                                    dump)

    def test_the_lock_is_free_after_a_stop(self) -> None:
        """Scenario: Stopping a backup (the next run is not kept
        waiting)."""
        process = self.launch(["sh", str(BACKUP), "once"])
        dump = self.host_dump(process)
        process.send_signal(signal.SIGTERM)
        self.assert_stopped(lambda: process.poll() is not None, dump)
        with open(self.dir / ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    @unittest.skipUnless(namespaces_work(), "no PID namespace can be made")
    def test_sigterm_stops_once_as_pid_1(self) -> None:
        """Scenario: Stopping a backup (as the container runs it, the
        script being PID 1 of its PID namespace). A fake ``chown``
        stands in, since the namespace's root cannot hand a directory
        to UID 1000."""
        chown = self.bin / "chown"
        chown.write_text("#!/bin/sh\nexit 0\n")
        chown.chmod(0o755)
        process = self.launch([*UNSHARE, "sh", str(BACKUP), "once"])
        inner = self.sleeping_dump(process)
        children = Path(f"/proc/{process.pid}/task/{process.pid}/children")
        script = int(children.read_text().split()[0])
        dump = host_pid(script, inner)
        self.assertIsNotNone(dump, "the fake dump is not in the namespace")
        self.pids.append(dump)
        os.kill(script, signal.SIGTERM)
        self.assert_stopped(lambda: not running(script), dump)


class RestoreCase(BackupCase):
    """A set built by hand, a Forgejo directory with stray files, and
    the checks of what ``restore`` did."""

    SET = "orgsyndb-20260105T120000Z"

    def setUp(self) -> None:
        super().setUp()
        self.origin = self.tmp / "origin"
        self.origin.mkdir()
        make_tree(self.origin)
        self.expected = snapshot(self.origin)
        self.outside = self.tmp / "outside"
        self.outside.mkdir()
        (self.outside / "keep.txt").write_text("keep")
        self.set_push_log = "2026-01-04T00:00:00Z def 9 omar\n"

    def make_full_set(self, **omit: bool) -> Path:
        """A set as ``once`` writes it, from ORIGIN, leaving out the
        parts named in OMIT."""
        target = self.make_set(self.SET, parts=(), mtime=False)
        for name, text in (("lab.dump", "dump of labdb\n"),
                           ("forge.dump", "dump of forge\n"),
                           ("pushes.log", self.set_push_log),
                           ("orgsyndb.env", "POSTGRES_USER=x\n")):
            if not omit.get(name):
                (target / name).write_text(text)
                (target / name).chmod(0o600)
        if not omit.get("forge.tar"):
            subprocess.run(
                ["tar", "-c", "--numeric-owner", "-p", "-f",
                 str(target / "forge.tar"), "-C", str(self.origin), "."],
                check=True, stdin=subprocess.DEVNULL)
            (target / "forge.tar").chmod(0o600)
        return target

    def fill_strays(self) -> None:
        """What a restore must empty out of the Forgejo directory, and
        what must stay."""
        (self.forge / "stray.txt").write_text("stray")
        (self.forge / ".hidden-stray").write_text("stray")
        (self.forge / "..odd").write_text("stray")
        (self.forge / "-stray").write_text("stray")
        (self.forge / "stray dir").mkdir()
        (self.forge / "stray dir" / "inner").write_text("stray")
        (self.forge / "custom").mkdir()
        (self.forge / "custom" / "newer.ini").write_text("newer")
        (self.forge / "link-out").symlink_to(self.outside)
        self.push_log.write_text("")
        (self.data / "collection").mkdir()
        (self.data / "collection" / "x").write_text("clone")
        (self.data / "releases").mkdir()
        (self.data / "releases" / "r1").write_text("release")
        (self.data / "state.json").write_text("{}")

    def restore(self, name: str | None = None, **extra: str
                ) -> subprocess.CompletedProcess:
        return self.run_script("restore", name or self.SET, **extra)

    def database_calls(self) -> list[dict]:
        return self.calls("psql", "dropdb", "createdb", "pg_restore",
                          "pg_dump")

    def position(self, kind: str, database: str, owner: str = ""):
        """Where in the recorded calls the database DATABASE is dropped
        (with its connections), created owned by OWNER, restored or has
        its ``push_mirror`` rows deleted: (call, offset) or None."""
        for number, call in enumerate(self.calls()):
            text = sql(call)
            tool = call["tool"]
            name = re.escape(database)
            if kind == "drop":
                found = re.search(
                    rf'(?is)\bDROP\s+DATABASE\s+(IF\s+EXISTS\s+)?"?{name}'
                    rf'"?\b[^;]*', text)
                if tool == "psql" and found:
                    forced = re.search(r"(?i)\bFORCE\b",
                                       found.group(0)) or (
                        "pg_terminate_backend" in text[:found.start()])
                    self.assertTrue(forced, f"not forced: {text}")
                    return number, found.start()
                if tool == "dropdb" and database in call["args"]:
                    self.assertTrue(
                        {"--force", "-f"} & set(call["args"]),
                        f"not forced: {call['args']}")
                    return number, 0
            elif kind == "create":
                found = re.search(
                    rf'(?is)\bCREATE\s+DATABASE\s+"?{name}"?\b[^;]*'
                    rf'\bOWNER\s*=?\s*"?{re.escape(owner)}"?\b', text)
                if tool == "psql" and found:
                    return number, found.start()
                args = call["args"]
                if (tool == "createdb" and database in args and (
                        {"-O", "--owner"} & set(args) and owner in args
                        or f"--owner={owner}" in args
                        or f"-O{owner}" in args)):
                    return number, 0
            elif kind == "restore":
                if tool == "pg_restore" and connects_to(call, database):
                    dump = "forge" if database == "forge" else "lab"
                    if (any(a.endswith(f"{dump}.dump")
                            for a in call["args"])
                            or f"dump of {database}" in call["stdin"]):
                        return number, 0
            elif kind == "delete":
                found = re.search(
                    r'(?is)\bDELETE\s+FROM\s+(ONLY\s+)?("?public"?\.)?'
                    r'"?push_mirror"?\b[^;]*', text)
                if tool == "psql" and found and connects_to(call, database):
                    self.assertNotRegex(found.group(0), r"(?i)\bWHERE\b")
                    return number, found.start()
        return None

    def assert_restored_in_order(self, with_forge: bool = True) -> None:
        steps = [("drop", "labdb", ""), ("create", "labdb", "labuser"),
                 ("restore", "labdb", "")]
        if with_forge:
            steps += [("drop", "forge", ""), ("create", "forge", "forge"),
                      ("restore", "forge", ""),
                      ("delete", "forge", "")]
        found = [self.position(*step) for step in steps]
        for step, place in zip(steps, found):
            self.assertIsNotNone(place, f"{step} not found in "
                                        f"{self.calls()}")
        self.assertEqual(found, sorted(found), f"out of order: {steps}")

    def assert_unchanged(self, forge_before, log_before, data_before
                         ) -> None:
        self.assertEqual(self.database_calls(), [])
        self.assertEqual(snapshot(self.forge), forge_before)
        self.assertEqual(self.push_log.read_text(), log_before)
        self.assertEqual(snapshot(self.data), data_before)


class RestoreTests(RestoreCase):
    """Scenario: A restore."""

    def setUp(self) -> None:
        super().setUp()
        self.make_full_set()
        self.fill_strays()

    def test_both_databases_are_dropped_created_and_restored(self) -> None:
        """Scenario: A restore (databases)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assert_restored_in_order()

    def test_the_directory_is_emptied_and_extracted(self) -> None:
        """Scenario: A restore (the stray file is gone, the files and
        the link are back)."""
        inode = self.forge.stat().st_ino
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(snapshot(self.forge), self.expected)
        self.assertEqual(self.forge.stat().st_ino, inode,
                         "the directory itself was replaced")

    def test_links_come_back_as_links_and_modes_are_kept(self) -> None:
        """Requirement: Backups (extracts `forge.tar` with its numeric
        owners, modes and symbolic links)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        for relative, target in LINKS.items():
            with self.subTest(link=relative):
                path = self.forge / relative
                self.assertTrue(path.is_symlink())
                self.assertEqual(os.readlink(path), target)
        for relative, (_text, mode) in FILES.items():
            with self.subTest(file=relative):
                self.assertEqual(
                    stat.S_IMODE((self.forge / relative).stat().st_mode),
                    mode)
        self.assertEqual(
            stat.S_IMODE((self.forge / "custom/conf").stat().st_mode),
            0o750)

    def test_a_link_out_of_the_directory_is_removed_not_followed(
            self) -> None:
        """Requirement: Backups (empties `ORGSYNDB_FORGE_DATA`)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertFalse((self.forge / "link-out").is_symlink())
        self.assertEqual((self.outside / "keep.txt").read_text(), "keep")

    def test_the_push_log_is_back(self) -> None:
        """Scenario: A restore (the push log equals the saved one)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.push_log.read_text(), self.set_push_log)
        if os.geteuid() == 0:
            self.assertEqual(self.push_log.stat().st_uid, 1000)

    def test_the_builders_clone_is_removed(self) -> None:
        """Scenario: A restore (`collection` is gone from
        `ORGSYNDB_DATA`)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertFalse((self.data / "collection").exists())
        self.assertEqual(
            (self.data / "releases" / "r1").read_text(), "release")
        self.assertTrue((self.data / "state.json").is_file())

    def test_the_next_steps_are_printed(self) -> None:
        """Scenario: A restore (the output names `web`, `builder`,
        `orgsyndb-deploy retry`, the ID reconciliation and
        `forge-setup`)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        text = self.output(done)
        self.assertRegex(text, r"\bweb\b")
        self.assertRegex(text, r"\bbuilder\b")
        self.assertIn("orgsyndb-deploy retry", text)
        self.assertIn("forge-setup", text)
        reconcile = re.search(r"(?i)reconcil|adopt_ids", text)
        self.assertIsNotNone(reconcile, "no ID reconciliation named")
        self.assertLess(text.index("orgsyndb-deploy retry"),
                        reconcile.start())
        self.assertLess(reconcile.start(), text.rindex("forge-setup"))

    def test_builder_starts_before_the_reconciliation(self) -> None:
        """Scenario: A restore (`builder` is started on its own before
        the IDs are reconciled, since the gate asks it about every push
        to `main`, the recovered commits are pushed over SSH, and `web`
        is started on its own after)."""
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        text = self.output(done)
        builder = re.search(r"docker compose up -d builder$", text, re.M)
        web = re.search(r"docker compose up -d web$", text, re.M)
        reconcile = re.search(r"(?i)reconcil|adopt_ids", text)
        self.assertIsNotNone(builder, "builder is not started on its own")
        self.assertIsNotNone(web, "web is not started on its own")
        self.assertIsNotNone(reconcile, "no ID reconciliation named")
        self.assertLess(builder.start(), reconcile.start())
        self.assertLess(reconcile.start(), web.start())
        self.assertRegex(text[reconcile.start():web.start()], r"\bSSH\b")

    def test_a_failed_database_step_exits_1(self) -> None:
        """Requirement: Backups (a failed step exits 1 naming it)."""
        done = self.restore(FAKE_FAIL_TOOL="pg_restore")
        self.assert_error(done)
        self.assertRegex(done.stderr, r"(?i)restor|lab\.dump|labdb")


class RoundTripTests(RestoreCase):
    """Scenario: A restore (on the set of A backup set)."""

    def test_a_set_made_by_once_restores_what_it_backed_up(self) -> None:
        shutil.rmtree(self.forge)
        shutil.copytree(self.origin, self.forge, symlinks=True)
        self.fill_files()
        self.stand_in()
        done = self.once()
        self.assertEqual(done.returncode, 0, self.output(done))
        name = self.the_set().name
        shutil.rmtree(self.forge)
        self.forge.mkdir()
        self.fill_strays()
        self.log.unlink(missing_ok=True)
        done = self.restore(name)
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assert_restored_in_order()
        self.assertEqual(snapshot(self.forge), self.expected)
        self.assertEqual(self.push_log.read_text(),
                         "2026-01-01T00:00:00Z abc 7 lena\n")
        self.assertFalse((self.data / "collection").exists())


class NeverStartedForgejoTests(RestoreCase):
    """Scenario: A set of a Forgejo never started."""

    def test_the_rows_are_deleted_only_when_the_table_exists(
            self) -> None:
        self.make_full_set()
        self.fill_strays()
        done = self.restore(FAKE_NO_PUSH_MIRROR="1")
        self.assertEqual(done.returncode, 0, self.output(done))
        found = [sql(c) for c in self.calls("psql")
                 if connects_to(c, "forge") and "push_mirror" in sql(c)]
        self.assertEqual(len(found), 1, self.calls("psql"))
        self.assertRegex(
            found[0], r"(?is)to_regclass\(\s*'(public\.)?push_mirror'\s*\)"
                      r".*\bDELETE\s+FROM\b[^;]*\bpush_mirror\b")
        self.assertEqual(snapshot(self.forge), self.expected)


class RestoreWithoutForgejoTests(RestoreCase):
    """Requirement: Backups (a set without Forgejo's parts restores the
    rest and says so)."""

    def setUp(self) -> None:
        super().setUp()
        self.make_full_set(**{"forge.dump": True, "forge.tar": True,
                              "pushes.log": True})
        self.fill_strays()

    def test_only_the_lab_database_is_restored(self) -> None:
        forge_before = snapshot(self.forge)
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assert_restored_in_order(with_forge=False)
        for call in self.calls():
            with self.subTest(call=call["tool"]):
                self.assertFalse(connects_to(call, "forge"), call)
                self.assertNotRegex(sql(call), r"(?i)\bpush_mirror\b")
        self.assertEqual(snapshot(self.forge), forge_before)
        self.assertEqual(self.push_log.read_text(), "")
        self.assertFalse((self.data / "collection").exists())

    def test_the_output_says_forgejo_was_not_restored(self) -> None:
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        lines = [line for line in self.output(done).lower().splitlines()
                 if "forgejo" in line]
        self.assertTrue(
            any(re.search(r"\b(without|no|not|skip\w*|only|lacks?)\b", line)
                for line in lines), self.output(done))

    def test_the_push_log_of_such_a_set_is_copied(self) -> None:
        """Requirement: Backups (copies `pushes.log`, when the set has
        it)."""
        (self.dir / self.SET / "pushes.log").write_text("kept\n")
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.push_log.read_text(), "kept\n")


class RestoreWithoutPushLogTests(RestoreCase):
    """Requirement: Backups (copies `pushes.log`, when the set has it)."""

    def test_a_set_without_a_push_log_leaves_the_log_alone(self) -> None:
        self.make_full_set(**{"pushes.log": True})
        self.fill_strays()
        self.push_log.write_text("newer\n")
        done = self.restore()
        self.assertEqual(done.returncode, 0, self.output(done))
        self.assertEqual(self.push_log.read_text(), "newer\n")
        self.assertEqual(snapshot(self.forge), self.expected)
        self.assert_restored_in_order()


class IncompleteSetTests(RestoreCase):
    """Scenario: An incomplete set."""

    def setUp(self) -> None:
        super().setUp()
        self.fill_strays()
        self.before = (snapshot(self.forge), self.push_log.read_text(),
                       snapshot(self.data))

    def assert_refused(self, name: str) -> None:
        done = self.restore(name)
        self.assertEqual(done.returncode, 1, self.output(done))
        self.assertTrue(done.stderr.strip(), "nothing was said")
        self.assert_unchanged(*self.before)

    def test_a_set_that_does_not_exist(self) -> None:
        self.assert_refused("orgsyndb-20260101T000000Z")

    def test_a_set_without_a_lab_dump(self) -> None:
        self.make_full_set(**{"lab.dump": True})
        self.assert_refused(self.SET)

    def test_a_forge_dump_without_an_archive(self) -> None:
        self.make_full_set(**{"forge.tar": True})
        self.assert_refused(self.SET)

    def test_an_archive_without_a_forge_dump(self) -> None:
        self.make_full_set(**{"forge.dump": True})
        self.assert_refused(self.SET)

    def test_a_file_in_place_of_a_set(self) -> None:
        (self.dir / "orgsyndb-notes").write_text("not a set")
        self.assert_refused("orgsyndb-notes")


if __name__ == "__main__":
    unittest.main()
