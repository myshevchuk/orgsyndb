"""Shared helpers for the build-pipeline tests.

Pure tests load ``tools/pipeline.py`` lazily, so a missing module fails
the test on an assertion. Fish and integration tests work in a temporary
copy of the repository whose path contains a space, and run
``tools/build.fish`` with ``cwd`` set to another temporary directory.
"""

import contextlib
import hashlib
import importlib.util
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
FIXTURES = REPO / "tests" / "fixtures"
EXPORT_FIXTURES = FIXTURES / "export"
PIPELINE = TOOLS / "pipeline.py"
BUILD_FISH = TOOLS / "build.fish"

OX_HUGO_PIN = "b7dc44dc28911b9d8e3055a18deac16c3b560b03"
TOMELR_PIN = "670e0a08f625175fd80137cf69e799619bf8a381"
PAGEFIND_RELATIVE = Path(".tools") / "pagefind-1.5.2" / "pagefind"
BOOTSTRAP_HINT = ("ox-hugo not bootstrapped: run tools/build.fish export "
                  "once (needs network)")
PAGEFIND_HINT = ("pagefind not cached: run tools/build.fish build once "
                 "(needs network)")

# Directories the integration harness copies from the real repository.
COPIED = ("tools", "site", "templates", "org", "md")
GIT_QUIET = ["-c", "user.name=Test Author",
             "-c", "user.email=author@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]

_module: ModuleType | None = None


# --- tools/pipeline.py -----------------------------------------------------

def pipeline() -> ModuleType:
    """Import tools/pipeline.py, failing on an assertion when it is absent."""
    global _module
    if _module is not None:
        return _module
    if not PIPELINE.is_file():
        raise AssertionError("tools/pipeline.py does not exist")
    spec = importlib.util.spec_from_file_location("pipeline", PIPELINE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    sys.modules["pipeline"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        del sys.modules["pipeline"]
        raise AssertionError(
            f"tools/pipeline.py does not import: {exc!r}") from exc
    finally:
        sys.path.remove(str(TOOLS))
    _module = module
    return module


class Run(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def run_pipeline(args: list[str | Path], *, cwd: Path | None = None,
                 env: dict[str, str] | None = None) -> Run:
    """Run tools/pipeline.py as a subprocess."""
    if not PIPELINE.is_file():
        raise AssertionError("tools/pipeline.py does not exist")
    done = subprocess.run(
        [sys.executable, str(PIPELINE), *map(str, args)],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    return Run(done.returncode, done.stdout, done.stderr)


# --- small file helpers ----------------------------------------------------

def snapshot(root: Path) -> dict[str, bytes]:
    """Map every file below ``root`` (relative, sorted) to its bytes."""
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def front_matter(text: str) -> dict[str, Any]:
    """Parse the ``+++`` TOML front matter at the top of ``text``."""
    lines = text.split("\n")
    if lines[0] != "+++":
        raise AssertionError("no +++ front matter")
    end = lines.index("+++", 1)
    return tomllib.loads("\n".join(lines[1:end]))


def body_of(text: str) -> str:
    """Return ``text`` after the closing ``+++`` of the front matter."""
    lines = text.split("\n")
    end = lines.index("+++", 1)
    return "\n".join(lines[end + 1:])


def free_port() -> int:
    """Return a TCP port on 127.0.0.1 that is free right now."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def read_only_dir(path: Path):
    """Make ``path`` mode 0555 and restore its mode on exit."""
    original = stat.S_IMODE(path.stat().st_mode)
    path.chmod(0o555)
    try:
        yield path
    finally:
        path.chmod(original)


# --- skips -----------------------------------------------------------------

def require_tool(name: str) -> str:
    """Return the path of ``name`` or skip, naming the missing tool."""
    found = shutil.which(name)
    if found is None:
        raise unittest.SkipTest(f"{name} not found")
    return found


def require_ox_hugo() -> None:
    """Skip unless ox-hugo and tomelr are checked out in .emacs-batch/."""
    elpa = REPO / ".emacs-batch" / "elpa"
    if not (elpa / "ox-hugo").is_dir() or not (elpa / "tomelr").is_dir():
        raise unittest.SkipTest(BOOTSTRAP_HINT)


def require_pagefind() -> None:
    if not (REPO / PAGEFIND_RELATIVE).is_file():
        raise unittest.SkipTest(PAGEFIND_HINT)


def require_exporter() -> None:
    """Skip unless fish, Emacs, git and the ox-hugo bootstrap exist."""
    for tool in ("fish", "emacs", "git"):
        require_tool(tool)
    require_ox_hugo()


def require_builder() -> None:
    """Skip unless export works and Hugo and Pagefind are present."""
    require_exporter()
    require_tool("hugo")
    require_pagefind()


# --- a temporary copy of the repository -------------------------------------

class Sandbox:
    """A temporary repository copy and a separate working directory."""

    def __init__(self, root: Path, work: Path, home: Path) -> None:
        self.root = root
        self.work = work
        self.home = home

    def env(self, **extra: str) -> dict[str, str]:
        """The inherited environment with HOME replaced."""
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"):
            env.pop(name, None)
        env.update(extra)
        return env

    def build(self, *args: str | Path, cwd: Path | None = None,
              env: dict[str, str] | None = None,
              timeout: int = 900) -> Run:
        """Run the copy's tools/build.fish."""
        return run_script(self.root / "tools" / "build.fish", args,
                          cwd=self.work if cwd is None else cwd,
                          env=self.env() if env is None else env,
                          timeout=timeout)

    def validator(self, *args: str | Path) -> Run:
        """Run the copy's tools/validate.py with the copy as cwd."""
        done = subprocess.run(
            [sys.executable, str(self.root / "tools" / "validate.py"),
             *map(str, args)],
            cwd=self.root, env=self.env(), capture_output=True, text=True,
            timeout=120)
        return Run(done.returncode, done.stdout, done.stderr)

    def git(self, *args: str | Path) -> Run:
        done = subprocess.run(
            ["git", *GIT_QUIET, *map(str, args)], cwd=self.root,
            env=self.env(), capture_output=True, text=True, timeout=120)
        return Run(done.returncode, done.stdout, done.stderr)

    def put_fixture(self, name: str) -> Path:
        """Copy a tests/fixtures/export file into org/procedures/."""
        target = self.root / "org" / "procedures"
        target.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy2(EXPORT_FIXTURES / name, target))

    def clear_org(self) -> None:
        """Remove every file from org/procedures/, keeping the directory."""
        target = self.root / "org" / "procedures"
        target.mkdir(parents=True, exist_ok=True)
        for path in target.iterdir():
            path.unlink()

    def md_dir(self) -> Path:
        target = self.root / "md" / "procedures"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def export_dir(self) -> Path:
        return self.root / "build" / "export"


def run_script(script: Path, args, *, cwd: Path,
               env: dict[str, str] | None = None,
               timeout: int = 900) -> Run:
    """Run an executable script directly. Absent scripts fail the test."""
    if not script.exists() and not script.is_symlink():
        raise AssertionError(
            f"tools/{script.name} does not exist")
    done = subprocess.run(
        [str(script), *map(str, args)], cwd=cwd, env=env,
        capture_output=True, text=True, timeout=timeout)
    return Run(done.returncode, done.stdout, done.stderr)


def make_sandbox(case: unittest.TestCase, *, copy_emacs: bool = False,
                 link_caches: bool = True) -> Sandbox:
    """Create the repository copy for ``case``; removed on clean-up.

    The copy lives under a directory whose name contains a space. It holds
    ``tools/``, ``site/``, ``templates/``, ``org/``, ``md/`` and
    ``tests/fixtures/export/``. ``.emacs-batch/`` and ``.tools/`` are
    symlinked from the real repository (when they exist), or
    ``.emacs-batch/`` is copied with ``copy_emacs``.
    """
    base = Path(tempfile.mkdtemp(prefix="orgsyndb test "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "repo copy"
    root.mkdir()
    for name in COPIED:
        if (REPO / name).is_dir():
            shutil.copytree(REPO / name, root / name, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tests" / "fixtures").mkdir(parents=True)
    shutil.copytree(EXPORT_FIXTURES, root / "tests" / "fixtures" / "export")
    if copy_emacs and (REPO / ".emacs-batch").is_dir():
        shutil.copytree(REPO / ".emacs-batch", root / ".emacs-batch",
                        symlinks=True)
    if link_caches:
        for name in (".emacs-batch", ".tools"):
            if (REPO / name).is_dir() and not (root / name).exists():
                (root / name).symlink_to(REPO / name)
    work = base / "work dir"
    work.mkdir()
    home = base / "home"
    home.mkdir()
    return Sandbox(root, work, home)


# --- a reduced PATH ----------------------------------------------------------

class PathDir(NamedTuple):
    directory: Path
    sudo_log: Path

    def sudo_calls(self) -> list[str]:
        """The argument lines the fake ``sudo`` recorded."""
        if not self.sudo_log.exists():
            return []
        return self.sudo_log.read_text().splitlines()


def make_path(case: unittest.TestCase, tools: tuple[str, ...],
              stubs: tuple[str, ...] = ()) -> PathDir:
    """Build a directory holding only the named tools and a fake sudo.

    ``tools`` are symlinked from their real locations (the test is skipped
    when one is missing). ``stubs`` become executables that only print a
    line. The fake ``sudo`` appends its arguments to a log and succeeds.
    """
    base = Path(tempfile.mkdtemp(prefix="orgsyndb path "))
    case.addCleanup(shutil.rmtree, base, True)
    directory = base / "bin"
    directory.mkdir()
    for name in tools:
        (directory / name).symlink_to(require_tool(name))
    for name in stubs:
        stub = directory / name
        stub.write_text(f"#!/bin/sh\necho '{name} stub 0.0.0'\n")
        stub.chmod(0o755)
    log = base / "sudo.log"
    sudo = directory / "sudo"
    quoted = "'" + str(log).replace("'", "'\\''") + "'"
    sudo.write_text(f"#!/bin/sh\necho \"$*\" >> {quoted}\nexit 0\n")
    sudo.chmod(0o755)
    return PathDir(directory, log)


# --- HTML checks -----------------------------------------------------------

class IndexedBody(NamedTuple):
    text: str
    headings: list[str]


class PageScan(NamedTuple):
    bodies: list[IndexedBody]
    outside_text: str


class _PageParser(HTMLParser):
    """Find elements carrying data-pagefind-body, and the text outside."""

    HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.bodies: list[IndexedBody] = []
        self.outside: list[str] = []
        self._tag: str | None = None
        self._depth = 0
        self._text: list[str] = []
        self._headings: list[str] = []
        self._heading: list[str] | None = None

    def handle_starttag(self, tag, attrs) -> None:
        if self._tag is None:
            if any(k == "data-pagefind-body" for k, _ in attrs):
                self._tag, self._depth = tag, 1
                self._text, self._headings = [], []
            return
        if tag == self._tag:
            self._depth += 1
        if tag in self.HEADINGS:
            self._heading = []

    def handle_endtag(self, tag) -> None:
        if self._tag is None:
            return
        if tag in self.HEADINGS and self._heading is not None:
            self._headings.append("".join(self._heading).strip())
            self._heading = None
        if tag == self._tag:
            self._depth -= 1
            if self._depth == 0:
                self.bodies.append(
                    IndexedBody("".join(self._text), self._headings))
                self._tag = None

    def handle_data(self, data) -> None:
        if self._tag is None:
            self.outside.append(data)
            return
        self._text.append(data)
        if self._heading is not None:
            self._heading.append(data)


def scan_page(html: str) -> PageScan:
    """Return the indexed bodies of ``html`` and the text outside them."""
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return PageScan(parser.bodies, "".join(parser.outside))


_REMOTE = re.compile(r"^\s*(https?:|//)", re.I)
_CSS_URL = re.compile(r"url\(\s*['\"]?\s*(https?:|//)", re.I)
_CSS_IMPORT = re.compile(r"@import\s+['\"]?\s*(https?:|//)", re.I)


def css_remote_fetches(css: str) -> list[str]:
    """Return ``url(...)`` and ``@import`` targets that name another host."""
    return ([m.group(0) for m in _CSS_URL.finditer(css)]
            + [m.group(0) for m in _CSS_IMPORT.finditer(css)])


class _FetchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag, attrs) -> None:
        for name, value in attrs:
            value = value or ""
            if name in ("src", "srcset", "poster", "data") or (
                    name == "href" and tag == "link"):
                if _REMOTE.match(value):
                    self.found.append(f"<{tag} {name}={value!r}>")
            elif name == "style":
                self.found += css_remote_fetches(value)
        self._in_style = tag == "style"

    def handle_endtag(self, tag) -> None:
        if tag == "style":
            self._in_style = False

    def handle_data(self, data) -> None:
        if self._in_style:
            self.found += css_remote_fetches(data)


def html_remote_fetches(html: str) -> list[str]:
    """Return references in ``html`` that fetch from another host.

    ``<a href>`` links are not fetches and are never reported.
    """
    parser = _FetchParser()
    parser.feed(html)
    parser.close()
    return parser.found
