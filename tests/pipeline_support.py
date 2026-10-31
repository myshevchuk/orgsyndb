"""Shared helpers for the build-pipeline tests.

Pure tests load ``tools/pipeline.py`` lazily, so a missing module fails
the test on an assertion, and call its functions in-process. Program and
integration tests work in a temporary copy of the application and of a
collection, under a path that contains a space, and run
``tools/orgsyndb -C <collection>`` with ``cwd`` set to a third temporary
directory. The collection is the Markdown-only test collection
``tests/fixtures/collection/``, which builds without Emacs, unless a test
exercises the Org export and copies the demo collection instead.
"""

import contextlib
import datetime as dt
import functools
import hashlib
import html as html_lib
import importlib.util
import io
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import tomllib
import unicodedata
import unittest
import urllib.parse
from collections.abc import Iterable, Iterator
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
FIXTURES = REPO / "tests" / "fixtures"
EXPORT_FIXTURES = FIXTURES / "export"
THEME_FIXTURES = FIXTURES / "theme"
CATALOGUE_FIXTURES = FIXTURES / "catalogue"
GENERAL_FIXTURES = FIXTURES / "general"
FIXTURE_COMPOUNDS = FIXTURES / "compounds"
FIXTURE_STATIC = FIXTURES / "static"
PAGEFIND_QUERY = REPO / "tests" / "js" / "pagefind-query.mjs"
SEARCH_TERMS = REPO / "site" / "assets" / "js" / "search-terms.js"
CATALOGUE_CORE = REPO / "site" / "assets" / "js" / "catalogue-core.js"
PIPELINE = TOOLS / "pipeline.py"
ORGSYNDB = TOOLS / "orgsyndb"
HOOK = TOOLS / "hooks" / "pre-commit"
DEMO = REPO / "examples" / "demo"
TEST_COLLECTION = FIXTURES / "collection"

OX_HUGO_PIN = "b7dc44dc28911b9d8e3055a18deac16c3b560b03"
TOMELR_PIN = "670e0a08f625175fd80137cf69e799619bf8a381"
PAGEFIND_RELATIVE = Path(".tools") / "pagefind-1.5.2" / "pagefind"
LANGUAGES = ("de", "en")
BOOTSTRAP_HINT = ("ox-hugo not bootstrapped: run tools/orgsyndb -C "
                  "examples/demo export once (needs network)")
PAGEFIND_HINT = ("pagefind not cached: run tools/orgsyndb -C examples/demo "
                 "build once, or without Emacs build a copy of "
                 "tests/fixtures/collection made outside tests/fixtures "
                 "(needs network)")

# Directories the integration harness copies from the real application.
COPIED = ("tools", "site", "templates", "docs")
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


def pipeline_function(name: str) -> Any:
    """Return ``pipeline.<name>``, failing on an assertion when absent."""
    module = pipeline()
    if not hasattr(module, name):
        raise AssertionError(f"tools/pipeline.py defines no {name}")
    return getattr(module, name)


class Run(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def captured(function: Any, *args: Any) -> tuple[Any, str, str]:
    """Call ``function(*args)`` with stdout and stderr captured.

    Returns the result and both outputs; an exception propagates.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = function(*args)
    return result, out.getvalue(), err.getvalue()


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
    """Skip unless the pinned Pagefind binary is cached in .tools/."""
    if not (REPO / PAGEFIND_RELATIVE).is_file():
        raise unittest.SkipTest(PAGEFIND_HINT)


def require_exporter() -> None:
    """Skip unless Emacs, git and the ox-hugo bootstrap exist."""
    for tool in ("emacs", "git"):
        require_tool(tool)
    require_ox_hugo()


def require_builder() -> None:
    """Skip unless Hugo and the cached Pagefind binary are present.

    Enough to build a collection without Org sources; a test that
    exports Org sources also calls ``require_exporter``.
    """
    require_tool("hugo")
    require_pagefind()


# --- temporary copies of the application and a collection -----------------

class Sandbox:
    """An application copy, a collection copy and a working directory.

    ``root`` is the collection, so that content and output paths read as
    before the split; ``app`` is the application.
    """

    def __init__(self, app: Path, root: Path, work: Path,
                 home: Path) -> None:
        self.app = app
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
        """Run the application copy's tools/orgsyndb on the collection."""
        return run_script(self.app / "tools" / "orgsyndb",
                          ["-C", self.root, *args],
                          cwd=self.work if cwd is None else cwd,
                          env=self.env() if env is None else env,
                          timeout=timeout)

    def program(self, *args: str | Path, cwd: Path | None = None,
                env: dict[str, str] | None = None,
                timeout: int = 900) -> Run:
        """Run the application copy's tools/orgsyndb without ``-C``."""
        return run_script(self.app / "tools" / "orgsyndb", args,
                          cwd=self.work if cwd is None else cwd,
                          env=self.env() if env is None else env,
                          timeout=timeout)

    def validator(self, *args: str | Path) -> Run:
        """Run the copy's tools/validate.py with the collection as cwd."""
        done = subprocess.run(
            [sys.executable, str(self.app / "tools" / "validate.py"),
             *map(str, args)],
            cwd=self.root, env=self.env(), capture_output=True, text=True,
            timeout=120)
        return Run(done.returncode, done.stdout, done.stderr)

    def git(self, *args: str | Path) -> Run:
        done = subprocess.run(
            ["git", *GIT_QUIET, *map(str, args)], cwd=self.root,
            env=self.env(), capture_output=True, text=True, timeout=120)
        return Run(done.returncode, done.stdout, done.stderr)

    def set_locale(self, locale: str) -> None:
        """Set ``locale`` in the application copy's site/hugo.toml."""
        config = self.app / "site" / "hugo.toml"
        text = config.read_text(encoding="utf-8")
        changed = re.sub(r'(?m)^locale = ".*"$', f'locale = "{locale}"',
                         text)
        if changed.count(f'locale = "{locale}"') != 1:
            raise AssertionError("site/hugo.toml has no locale line")
        config.write_text(changed, encoding="utf-8")

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
            f"{script} does not exist")
    done = subprocess.run(
        [str(script), *map(str, args)], cwd=cwd, env=env,
        capture_output=True, text=True, timeout=timeout)
    return Run(done.returncode, done.stdout, done.stderr)


def make_sandbox(case: unittest.TestCase, *,
                 collection: Path = TEST_COLLECTION,
                 copy_emacs: bool = False,
                 link_caches: bool = True) -> Sandbox:
    """Create the copies for ``case``; removed on clean-up.

    Both live under a directory whose name contains a space. The
    application copy holds ``tools/``, ``site/``, ``templates/`` and
    ``docs/``; ``.emacs-batch/`` and ``.tools/`` are symlinked from the
    real application (when they exist), or ``.emacs-batch/`` is copied
    with ``copy_emacs``. The collection copy is a copy of ``collection``, the
    test collection unless ``DEMO`` is passed, without its generated
    directories ``build/``, ``public/`` and ``pdf/``.
    """
    base = Path(tempfile.mkdtemp(prefix="orgsyndb test "))
    case.addCleanup(shutil.rmtree, base, True)
    app = base / "app copy"
    app.mkdir()
    for name in COPIED:
        if (REPO / name).is_dir():
            shutil.copytree(REPO / name, app / name, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
    if copy_emacs and (REPO / ".emacs-batch").is_dir():
        shutil.copytree(REPO / ".emacs-batch", app / ".emacs-batch",
                        symlinks=True,
                        ignore=shutil.ignore_patterns("S.gpg-agent*"))
    if link_caches:
        for name in (".emacs-batch", ".tools"):
            if (REPO / name).is_dir() and not (app / name).exists():
                (app / name).symlink_to(REPO / name)
    root = base / "collection copy"
    shutil.copytree(collection, root, symlinks=True,
                    ignore=shutil.ignore_patterns("build", "public", "pdf"))
    work = base / "work dir"
    work.mkdir()
    home = base / "home"
    home.mkdir()
    return Sandbox(app, root, work, home)


# --- GitHub Actions workflows ---------------------------------------------

def workflow_jobs(text: str) -> dict[str, str]:
    """Split a workflow's ``jobs:`` mapping into each job's text."""
    found: dict[str, str] = {}
    name = None
    inside = False
    for line in text.splitlines():
        if re.match(r"^\S", line):
            inside = line.rstrip() == "jobs:"
            name = None
            continue
        if not inside:
            continue
        key = re.match(r"^  ([\w-]+):\s*$", line)
        if key:
            name = key.group(1)
            found[name] = ""
        elif name is not None:
            found[name] += line + "\n"
    return found


def workflow_key(text: str, key: str) -> str:
    """Return the text of one top-level key, its own line included."""
    match = re.search(rf"(?ms)^{re.escape(key)}:.*?(?=^\S|\Z)", text)
    return match.group(0) if match else ""


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


# --- theme fixtures and builds ---------------------------------------------

def org_scope_rows(text: str) -> list[dict[str, str]]:
    """The rows of the table named ``scope`` in an Org source, each a
    map from a column name to its stripped cell text, in order."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines)
                  if line.strip().lower() == "#+name: scope"), None)
    if start is None:
        return []
    table = []
    for line in lines[start + 1:]:
        if not line.strip().startswith("|"):
            break
        table.append(line.strip())
    cells = [[cell.strip() for cell in line.strip("|").split("|")]
             for line in table if not line.startswith("|-")]
    header = cells[0]
    return [dict(zip(header, row)) for row in cells[1:]]


def fixture_compound_keys(path: Path) -> list[str]:
    """The compound keys a procedure fixture, Markdown or Org, names as
    products or substrates, at the top level or in the entries of its
    scope, in order and without repeats."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".org":
        keys = re.findall(r'\(compound \. "([^"]*)"\)', text)
        for line in re.findall(r"(?m)^#\+HUGO_CUSTOM_FRONT_MATTER:.*"
                               r":substrates '\(([^)]*)\)", text):
            keys += re.findall(r'"([^"]*)"', line)
        for row in org_scope_rows(text):
            keys += row.get("products", "").split()
            keys += row.get("substrates", "").split()
    else:
        data = front_matter(text)
        keys = [e["compound"] for e in data.get("products", [])]
        keys += data.get("substrates", [])
        for entry in data.get("scope", []):
            keys += [e["compound"] for e in entry["products"]]
            keys += entry["substrates"]
    return list(dict.fromkeys(keys))


def required_field_lines(sandbox: Sandbox, registry: Path) -> str:
    """The lines that give a fixture compound a valid value for each
    field that the sandbox collection's ``orgsyndb.toml`` declares
    required: a fresh ``CH-9nnn`` for ``item_number`` and one class for
    ``chemical_class``. The fixture registry sets no declared field."""
    data = tomllib.loads(
        (sandbox.root / "orgsyndb.toml").read_text(encoding="utf-8"))
    lines = ""
    for field in data.get("fields", {}).get("compound", []):
        if not field.get("required"):
            continue
        if field["key"] == "item_number":
            number = 9000 + len(list(registry.glob("*.toml")))
            lines += f'item_number = "CH-{number:04d}"\n'
        elif field["key"] == "chemical_class":
            lines += 'chemical_class = ["alcohols"]\n'
        else:
            raise AssertionError(f"put_compounds cannot set the required "
                                 f"field {field['key']}")
    return lines


def put_compounds(sandbox: Sandbox, *keys: str) -> list[Path]:
    """Copy fixture registry files into the sandbox collection's
    ``compounds/``, with the structure images they name into
    ``static/structures/``. A file the collection already holds is kept.
    Where the collection declares required fields, each copy also sets
    them."""
    copied = []
    registry = sandbox.root / "compounds"
    registry.mkdir(parents=True, exist_ok=True)
    for key in keys:
        source = FIXTURE_COMPOUNDS / f"{key}.toml"
        if not source.is_file():
            raise AssertionError(f"tests/fixtures/compounds/{key}.toml is "
                                 "missing")
        target = registry / source.name
        if target.exists():
            continue
        copied.append(Path(shutil.copy2(source, target)))
        with target.open("a", encoding="utf-8") as handle:
            handle.write(required_field_lines(sandbox, registry))
        image = tomllib.loads(source.read_text(encoding="utf-8")).get(
            "structure_image")
        if image:
            destination = sandbox.root / "static" / image
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(FIXTURE_STATIC / image, destination)
    return copied


def put_theme_fixtures(sandbox: Sandbox, *names: str) -> list[Path]:
    """Copy files of tests/fixtures/theme/ into the sandbox, with the
    fixture-registry compounds they name.

    A ``.org`` file goes to ``org/procedures/`` and a ``.md`` file to
    ``md/procedures/``. Any other suffix is a mistake in the test.
    """
    copied = []
    for name in names:
        source = THEME_FIXTURES / name
        if not source.is_file():
            raise AssertionError(f"tests/fixtures/theme/{name} is missing")
        if source.suffix == ".org":
            target = sandbox.root / "org" / "procedures"
            target.mkdir(parents=True, exist_ok=True)
        elif source.suffix == ".md":
            target = sandbox.md_dir()
        else:
            raise ValueError(f"no procedure directory for {name}")
        copied.append(Path(shutil.copy2(source, target)))
        put_compounds(sandbox, *fixture_compound_keys(source))
    return copied


def put_catalogue_fixtures(sandbox: Sandbox) -> list[Path]:
    """Copy the catalogue fixtures, tests/fixtures/catalogue/*.md, into
    the sandbox's ``md/procedures/``, with their compounds."""
    sources = sorted(CATALOGUE_FIXTURES.glob("OSDB-*.md"))
    if not sources:
        raise AssertionError("tests/fixtures/catalogue/ holds no procedure")
    for source in sources:
        put_compounds(sandbox, *fixture_compound_keys(source))
    return [Path(shutil.copy2(source, sandbox.md_dir()))
            for source in sources]


def put_general_fixture(sandbox: Sandbox) -> Path:
    """Copy the general baseline, tests/fixtures/general/
    OSDB-0140-general.md, into the sandbox's ``md/procedures/``, with
    its compounds."""
    source = GENERAL_FIXTURES / "OSDB-0140-general.md"
    put_compounds(sandbox, *fixture_compound_keys(source))
    return Path(shutil.copy2(source, sandbox.md_dir()))


def put_baseline(sandbox: Sandbox, name: str = "OSDB-0100-baseline.md"
                 ) -> Path:
    """Copy the validator baseline into the sandbox's ``md/procedures/``
    under ``name``, with its compound."""
    source = FIXTURES / "baseline" / "OSDB-0100-baseline.md"
    put_compounds(sandbox, *fixture_compound_keys(source))
    target = sandbox.md_dir() / name
    shutil.copyfile(source, target)
    return target


class _ClassCase:
    """Adapts a test class to the ``addCleanup`` that make_sandbox calls."""

    def __init__(self, cls: type[unittest.TestCase]) -> None:
        self.addCleanup = cls.addClassCleanup


def require_node() -> str:
    """Return the path of node or skip: it is optional and test-only."""
    found = shutil.which("node")
    if found is None:
        raise unittest.SkipTest(
            "node not found (optional; used only by the search tests)")
    return found


def require_pdf_tools() -> None:
    """Skip unless WeasyPrint, pdfinfo and pdftotext exist."""
    require_tool("weasyprint")
    for tool in ("pdfinfo", "pdftotext"):
        if shutil.which(tool) is None:
            raise unittest.SkipTest(f"{tool} not found (poppler-utils)")


class ThemeBuildCase(unittest.TestCase):
    """Base of the integration tests: one build per test class.

    A subclass names the ``COLLECTION`` to copy (the test collection
    unless it sets ``DEMO``, and then calls ``require_exporter`` from
    ``require_tools``), the theme ``FIXTURES`` to copy into the sandbox,
    the build ``COMMAND`` (``build`` or ``pdf``) and extra environment
    variables in ``ENV``. ``CATALOGUE`` adds the catalogue fixtures
    (tests/fixtures/catalogue/) to the collection. A build that fails
    does not error the class: it fails every test on an assertion that
    shows the build output.
    """

    COLLECTION = TEST_COLLECTION
    FIXTURES: tuple[str, ...] = ()
    CATALOGUE = False
    COMMAND = "build"
    LOCALE = "en"
    ENV: dict[str, str] = {}
    sandbox: Sandbox
    result: Run

    @classmethod
    def require_tools(cls) -> None:
        """Skip the class when a tool beyond the builder is missing."""

    @classmethod
    def prepare(cls) -> None:
        """Change the sandbox before the build. Subclasses override."""

    @classmethod
    def setUpClass(cls) -> None:
        require_builder()
        cls.require_tools()
        cls.sandbox = make_sandbox(_ClassCase(cls),
                                   collection=cls.COLLECTION)
        cls.sandbox.set_locale(cls.LOCALE)
        put_theme_fixtures(cls.sandbox, *cls.FIXTURES)
        if cls.CATALOGUE:
            put_catalogue_fixtures(cls.sandbox)
        cls.prepare()
        cls.result = cls.sandbox.build(
            cls.COMMAND, env=cls.sandbox.env(**cls.ENV))

    def setUp(self) -> None:
        self.assertEqual(self.result.returncode, 0,
                         self.result.stdout + self.result.stderr)

    @property
    def public(self) -> Path:
        return self.sandbox.root / "public"

    def content(self) -> list["Content"]:
        """The content files the build published, one per ID."""
        return read_content(self.sandbox, self.LOCALE)

    def pages(self) -> list[tuple[Path, "Page"]]:
        """Every HTML page of the build except the Pagefind bundle."""
        return [(path, load_page(self.public, path))
                for path in html_files(self.public)]

    def procedure_pages(self) -> list[tuple["Content", "Page"]]:
        """Each published content file with its page, by ID."""
        found = []
        for item in self.content():
            path = item.page_file(self.public)
            self.assertTrue(path.is_file(), f"{path.relative_to(self.public)}"
                            " was not published")
            found.append((item, load_page(self.public, path)))
        return found


# --- content files ---------------------------------------------------------

class Content(NamedTuple):
    path: Path
    data: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def slug(self) -> str:
        return self.data["slug"]

    @property
    def title(self) -> str:
        return self.data["title"]

    @property
    def tags(self) -> list[str]:
        return list(self.data.get("tags", []))

    @property
    def scope(self) -> list[dict[str, Any]]:
        """The entries of a general procedure's ``scope``, in order;
        empty for a specific procedure."""
        return list(self.data.get("scope", []))

    @property
    def is_general(self) -> bool:
        return "scope" in self.data

    @property
    def products(self) -> list[dict[str, Any]]:
        """The ``{compound, yield_percent}`` tables, in order: those of a
        specific procedure, or of a general procedure the first table of
        each compound over its entries, in order of first appearance."""
        if not self.is_general:
            return list(self.data.get("products", []))
        found: dict[str, dict[str, Any]] = {}
        for entry in self.scope:
            for product in entry["products"]:
                found.setdefault(product["compound"], product)
        return list(found.values())

    @property
    def substrates(self) -> list[str]:
        """The substrates of a specific procedure, or of a general one
        those of all its entries, each once, in order of first
        appearance."""
        if not self.is_general:
            return list(self.data.get("substrates", []))
        return list(dict.fromkeys(
            key for entry in self.scope for key in entry["substrates"]))

    @property
    def kind(self) -> str:
        """The catalogue's ``kind``: ``general`` or ``specific``."""
        return "general" if self.is_general else "specific"

    @property
    def language(self) -> str | None:
        """The language code of the file name, or None."""
        return language_of(self.path.name)

    def term_keys(self, taxonomy: str) -> list[str]:
        """The taxonomy keys of the procedure's terms, in front-matter
        order: slugs for reaction types, the lowercased term otherwise."""
        return [term_key(taxonomy, term)
                for term in self.data.get(taxonomy, [])]

    def page_file(self, public: Path) -> Path:
        """The procedure's page under ``public``."""
        return public / "procedures" / self.slug / "index.html"


def language_of(name: str) -> str | None:
    """The language code of a file name (``de`` for ``*.de.md``) or
    None."""
    match = re.search(r"\.([a-z]{2})\.(md|org|pdf)$", name)
    return match.group(1) if match else None


def base_name(name: str) -> str:
    """A file name without its suffix and its language code."""
    stem = name.rsplit(".", 1)[0]
    return stem.rsplit(".", 1)[0] if language_of(name) else stem


def variant_rank(name: str, locale: str) -> tuple[int, str]:
    """Order of preference of a variant for a site in ``locale``: the
    file tagged with it, then the untagged file, then the others."""
    code = language_of(name)
    if code == locale:
        return (0, name)
    if code is None:
        return (1, name)
    return (2 + LANGUAGES.index(code), name)


def read_content(sandbox: Sandbox, locale: str | None) -> list[Content]:
    """Front matter and body of the procedure content files, by ID: the
    variant published in ``locale`` of each ID, or every file with None.
    """
    found = []
    for directory in (sandbox.export_dir(), sandbox.md_dir()):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("OSDB-*.md")):
            text = path.read_text(encoding="utf-8")
            found.append(Content(path, front_matter(text), body_of(text)))
    if locale is not None:
        chosen: dict[str, Content] = {}
        for item in found:
            best = chosen.get(item.id)
            if best is None or variant_rank(item.path.name, locale) < \
                    variant_rank(best.path.name, locale):
                chosen[item.id] = item
        found = list(chosen.values())
    return sorted(found, key=lambda item: (item.id, item.path.name))


class Sequence(NamedTuple):
    path: Path
    data: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def slug(self) -> str:
        return self.data["slug"]

    @property
    def title(self) -> str:
        return self.data["title"]

    @property
    def target(self) -> str:
        return self.data["target"]

    @property
    def steps(self) -> list[dict[str, Any]]:
        return list(self.data["steps"])

    def page_file(self, public: Path) -> Path:
        """The sequence's page under ``public``."""
        return public / "sequences" / self.slug / "index.html"


def read_sequences(sandbox: Sandbox, locale: str | None
                   ) -> list[Sequence]:
    """Front matter and body of the sequence files in the sandbox
    collection's ``md/sequences/``, by ID: the variant published in
    ``locale`` of each ID, or every file with None."""
    found = []
    directory = sandbox.root / "md" / "sequences"
    if directory.is_dir():
        for path in sorted(directory.glob("SEQ-*.md")):
            text = path.read_text(encoding="utf-8")
            found.append(Sequence(path, front_matter(text), body_of(text)))
    if locale is not None:
        chosen: dict[str, Sequence] = {}
        for item in found:
            best = chosen.get(item.id)
            if best is None or variant_rank(item.path.name, locale) < \
                    variant_rank(best.path.name, locale):
                chosen[item.id] = item
        found = list(chosen.values())
    return sorted(found, key=lambda item: (item.id, item.path.name))


def term_key(taxonomy: str, term: str) -> str:
    """The key of ``term`` in Hugo's taxonomy: the term as written,
    lowercased. A reaction type's key is its vocabulary slug."""
    return term if taxonomy == "reaction_types" else term.lower()


def rfc3339(moment: dt.datetime) -> str:
    """``2006-01-02T15:04:05Z07:00`` of an aware datetime: ``Z`` for
    offset zero, else ``+HH:MM``."""
    text = moment.isoformat(timespec="seconds")
    return text[:-6] + "Z" if text.endswith("+00:00") else text


class HelpDocument(NamedTuple):
    """A document of an application's docs/, as the help section shows it."""
    name: str
    slug: str
    base: str
    language: str
    group: str
    title: str


def help_documents(app: Path) -> list[HelpDocument]:
    """The documents of ``app``/docs/ by name, read independently of the
    pipeline: the title from the first line (``# ``) or ``#+TITLE:``."""
    found = []
    for path in sorted((app / "docs").iterdir()):
        if not path.is_file() or path.suffix not in (".md", ".org"):
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".md":
            title = text.split("\n", 1)[0].removeprefix("# ")
        else:
            title = re.search(r"(?im)^#\+title:\s*(.*)$", text).group(1)
        code = re.search(r"\.([a-z]{2})\.(md|org)$", path.name)
        stem = path.name.rsplit(".", 1)[0]
        base = stem.rsplit(".", 1)[0] if code else stem
        found.append(HelpDocument(
            path.name, stem.lower().replace(".", "-"), base.lower(),
            code.group(1) if code else "en",
            "glossaries" if path.name.startswith("GLOSSARY") else "guides",
            title.strip()))
    return found


def reaction_labels(root: Path, language: str = "en") -> dict[str, str]:
    """Reaction-type slug to label in ``language``, from the application
    at ``root``."""
    data = tomllib.loads(
        (root / "site" / "data" / "reaction_types.toml")
        .read_text(encoding="utf-8"))
    return {slug: entry.get(f"label_{language}", entry["label"])
            for slug, entry in data.items()}


def read_registry(sandbox: Sandbox) -> dict[str, dict[str, Any]]:
    """Each compound file of the sandbox collection's ``compounds/``, by
    key."""
    registry = sandbox.root / "compounds"
    return {path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
            for path in sorted(registry.glob("*.toml"))}


def shown_name(compound: dict[str, Any], locale: str) -> str:
    """A compound's name on a site in ``locale``: ``name_de`` on a German
    site when set, else ``name``."""
    if locale == "de" and compound.get("name_de"):
        return compound["name_de"]
    return compound["name"]


def number_text(value: int | float, locale: str) -> str:
    """A front-matter number as the site shows it: with a decimal comma
    on a German site."""
    text = str(value)
    return text.replace(".", ",") if locale == "de" else text


def yield_text(item: "Content", registry: dict[str, dict[str, Any]],
               locale: str) -> str:
    """The ``Yield`` value of a procedure's key facts: ``<n> %`` for one
    product, else ``<n> % <name>`` for each, joined by ``, ``; for a
    general procedure the range ``<min>–<max> %`` of all its entries'
    yields, or ``<n> %`` when they are all equal."""
    if item.is_general:
        yields = [product["yield_percent"] for entry in item.scope
                  for product in entry["products"]]
        low, high = min(yields), max(yields)
        if low == high:
            return f"{number_text(low, locale)} %"
        return (f"{number_text(low, locale)}–"
                f"{number_text(high, locale)} %")
    entries = item.products
    if len(entries) == 1:
        return f"{number_text(entries[0]['yield_percent'], locale)} %"
    return ", ".join(
        f"{number_text(entry['yield_percent'], locale)} % "
        f"{shown_name(registry[entry['compound']], locale)}"
        for entry in entries)


def formula_html(formula: str) -> str:
    """A formula with each digit run in ``<sub>``, as the theme writes
    it."""
    return re.sub(r"(\d+)", r"<sub>\1</sub>", formula)


def smiles_key(smiles: str) -> str:
    """N(s): lowercase with every character outside [a-z0-9] removed."""
    return re.sub(r"[^a-z0-9]", "", smiles.lower())


def smiles_suffixes(smiles: str) -> str:
    """The suffixes of N(smiles), longest first, joined by single spaces."""
    key = smiles_key(smiles)
    return " ".join(key[i:] for i in range(len(key)))


# --- an HTML page model ----------------------------------------------------

_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img",
                   "input", "link", "meta", "param", "source", "track",
                   "wbr"})
_INLINE = frozenset({"a", "abbr", "b", "code", "em", "i", "kbd", "mark",
                     "small", "span", "strong", "sub", "sup", "time", "u"})
_BLOCKS = frozenset({"address", "article", "aside", "blockquote", "details",
                     "div", "dl", "fieldset", "figure", "footer", "form",
                     "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
                     "main", "nav", "ol", "p", "pre", "section", "table",
                     "ul"})
_SECTIONS = {"thead", "tbody", "tfoot", "tr", "td", "th"}
# Start tag -> (tags it closes implicitly, tags that stop the search).
_IMPLIED: dict[str, tuple[set[str], set[str]]] = {
    "li": ({"li"}, {"ul", "ol"}),
    "dt": ({"dt", "dd"}, {"dl"}),
    "dd": ({"dt", "dd"}, {"dl"}),
    "tr": ({"tr", "td", "th"}, {"table", "thead", "tbody", "tfoot"}),
    "td": ({"td", "th"}, {"tr", "table"}),
    "th": ({"td", "th"}, {"tr", "table"}),
    "thead": (_SECTIONS, {"table"}),
    "tbody": (_SECTIONS, {"table"}),
    "tfoot": (_SECTIONS, {"table"}),
}
_ORIGIN = "http://page.invalid"


class Node:
    """An element of a parsed page. Offsets index the source string."""

    def __init__(self, tag: str, attrs: dict[str, str],
                 parent: "Node | None", start: int,
                 content_start: int) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []
        self.start = start
        self.content_start = content_start
        self.end = content_start
        self.end_tag_end: int | None = None

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def has_class(self, *names: str) -> bool:
        return all(name in self.classes for name in names)

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def text(self) -> str:
        """All text below this element, unnormalised."""
        return "".join(child if isinstance(child, str) else child.text()
                       for child in self.children)

    def norm(self) -> str:
        """The text with each run of whitespace collapsed to one space."""
        return " ".join(self.text().split())

    def elements(self) -> list["Node"]:
        """The child elements."""
        return [c for c in self.children if isinstance(c, Node)]

    def iter(self) -> Iterator["Node"]:
        """This element and every descendant, in document order."""
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.iter()

    def ancestors(self) -> Iterator["Node"]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def within(self, other: "Node") -> bool:
        return any(a is other for a in self.ancestors())

    def find_all(self, tag: str | None = None, cls: str | None = None,
                 **attrs: bool | str) -> list["Node"]:
        """Descendants matching a tag, a class and attributes.

        An attribute keyword (underscores stand for hyphens) is ``True``
        for present, ``False`` for absent, or a string for equal.
        """
        found = []
        for node in self.iter():
            if node is self:
                continue
            if tag is not None and node.tag != tag:
                continue
            if cls is not None and cls not in node.classes:
                continue
            ok = True
            for key, want in attrs.items():
                name = key.replace("_", "-")
                if want is True:
                    ok = name in node.attrs
                elif want is False:
                    ok = name not in node.attrs
                else:
                    ok = node.attrs.get(name) == want
                if not ok:
                    break
            if ok:
                found.append(node)
        return found

    def find(self, tag: str | None = None, cls: str | None = None,
             **attrs: bool | str) -> "Node | None":
        found = self.find_all(tag, cls, **attrs)
        return found[0] if found else None


class Cell(NamedTuple):
    node: Node
    tag: str
    text: str
    classes: tuple[str, ...]


class TableModel(NamedTuple):
    node: Node
    rows: list[list[Cell]]


class DefPair(NamedTuple):
    label: str
    term: Node
    definition: Node
    gap: str   # raw HTML between the end of the dt and the start of the dd


class Link(NamedTuple):
    node: Node
    href: str
    target: str   # the page URL path it resolves to, or an absolute URL


class _Builder(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.root = Node("#root", {}, None, 0, 0)
        self.stack = [self.root]
        self._line_starts = [0]
        for match in re.finditer("\n", source):
            self._line_starts.append(match.end())

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _close(self, node: Node, end: int) -> None:
        node.end = end

    def _implied_close(self, tag: str) -> None:
        if tag in _BLOCKS:
            for index in range(len(self.stack) - 1, 0, -1):
                name = self.stack[index].tag
                if name == "p":
                    self._pop_to(index, self._offset())
                    break
                if name not in _INLINE:
                    break
        rule = _IMPLIED.get(tag)
        if rule is None:
            return
        closers, boundary = rule
        lowest = None
        for index in range(len(self.stack) - 1, 0, -1):
            name = self.stack[index].tag
            if name in boundary:
                break
            if name in closers:
                lowest = index
        if lowest is not None:
            self._pop_to(lowest, self._offset())

    def _pop_to(self, index: int, end: int) -> None:
        while len(self.stack) > index:
            self._close(self.stack.pop(), end)

    def _attrs(self, attrs) -> dict[str, str]:
        return {name: "" if value is None else value for name, value in attrs}

    def handle_starttag(self, tag, attrs) -> None:
        self._implied_close(tag)
        start = self._offset()
        node = Node(tag, self._attrs(attrs), self.stack[-1], start,
                    start + len(self.get_starttag_text() or ""))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs) -> None:
        self._implied_close(tag)
        start = self._offset()
        node = Node(tag, self._attrs(attrs), self.stack[-1], start,
                    start + len(self.get_starttag_text() or ""))
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag) -> None:
        if tag in _VOID:
            return
        start = self._offset()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                close = self.source.find(">", start) + 1
                node = self.stack[index]
                self._pop_to(index, close)
                node.end_tag_end = close
                return

    def handle_data(self, data) -> None:
        self.stack[-1].children.append(data)

    def finish(self) -> Node:
        self.close()
        self._pop_to(1, len(self.source))
        return self.root


class Page:
    """A parsed HTML page, found at the URL path ``url``."""

    def __init__(self, source: str, url: str = "/") -> None:
        self.source = source
        self.url = url
        builder = _Builder(source)
        builder.feed(source)
        self.root = builder.finish()
        self.nodes = list(self.root.iter())[1:]

    def find_all(self, tag: str | None = None, cls: str | None = None,
                 **attrs: bool | str) -> list[Node]:
        return self.root.find_all(tag, cls, **attrs)

    def find(self, tag: str | None = None, cls: str | None = None,
             **attrs: bool | str) -> Node | None:
        return self.root.find(tag, cls, **attrs)

    def by_class(self, cls: str) -> list[Node]:
        return self.root.find_all(cls=cls)

    def index_of(self, node: Node) -> int:
        """Position of ``node`` in document order."""
        for index, other in enumerate(self.nodes):
            if other is node:
                return index
        raise ValueError("node is not part of this page")

    def following(self, node: Node, *tags: str) -> Node | None:
        """The first element after ``node`` (and its subtree) with a tag."""
        inside = {id(n) for n in node.iter()}
        passed = False
        for other in self.nodes:
            if other is node:
                passed = True
                continue
            if passed and id(other) not in inside and other.tag in tags:
                return other
        return None

    def title(self) -> str:
        node = self.find("title")
        return "" if node is None else node.norm()

    def indexed_bodies(self) -> list[Node]:
        return self.find_all(data_pagefind_body=True)

    def indexed_text(self) -> str:
        """The text of the indexed body, or of every body joined."""
        return "".join(node.text() for node in self.indexed_bodies())

    def headings(self) -> list[tuple[int, str]]:
        return [(int(node.tag[1]), node.norm()) for node in self.nodes
                if re.fullmatch(r"h[1-6]", node.tag)]

    def heading(self, text: str, level: int = 2) -> Node | None:
        for node in self.find_all(f"h{level}"):
            if node.norm() == text:
                return node
        return None

    def definition_pairs(self, scope: Node | None = None) -> list[DefPair]:
        """The dt/dd pairs below ``scope``, with the raw gap between each."""
        pairs = []
        for dt in (scope or self.root).find_all("dt"):
            siblings = dt.parent.children if dt.parent else []
            later = [c for c in siblings[siblings.index(dt) + 1:]
                     if isinstance(c, Node)]
            if not later or later[0].tag != "dd":
                continue
            dd = later[0]
            if dt.end_tag_end is not None:
                gap = self.source[dt.end_tag_end:dd.start]
            else:
                raw = self.source[dt.content_start:dd.start]
                gap = raw[len(raw.rstrip()):]
            pairs.append(DefPair(dt.norm(), dt, dd, gap))
        return pairs

    def resolve(self, ref: str) -> str:
        """The URL path ``ref`` resolves to from this page, followed by
        ``?`` and its query, still encoded, when it has one. A fragment
        is dropped."""
        joined = urllib.parse.urljoin(_ORIGIN + self.url, ref)
        parts = urllib.parse.urlsplit(joined)
        if parts.netloc != "page.invalid":
            return joined
        path = urllib.parse.unquote(parts.path)
        return f"{path}?{parts.query}" if parts.query else path

    def links(self, scope: Node | None = None) -> list[Link]:
        return [Link(node, node.attrs["href"],
                     self.resolve(node.attrs["href"]))
                for node in (scope or self.root).find_all("a", href=True)]

    def filter_elements(self) -> list[tuple[Node, str, str]]:
        """(element, filter key, normalised text) per data-pagefind-filter."""
        return [(n, n.attrs["data-pagefind-filter"], n.norm())
                for n in self.find_all(data_pagefind_filter=True)]

    def meta_elements(self) -> list[tuple[Node, str, str]]:
        """(element, meta spec, normalised text) per data-pagefind-meta."""
        return [(n, n.attrs["data-pagefind-meta"], n.norm())
                for n in self.find_all(data_pagefind_meta=True)]

    def tables(self) -> list[TableModel]:
        models = []
        for table in self.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                rows.append([Cell(c, c.tag, c.norm(), tuple(c.classes))
                             for c in tr.elements()
                             if c.tag in ("td", "th")])
            models.append(TableModel(table, rows))
        return models

    def stylesheets(self) -> list[tuple[str, str | None]]:
        """(href, media) of every stylesheet link, media None if absent."""
        return [(n.attrs.get("href", ""), n.attrs.get("media"))
                for n in self.find_all("link")
                if "stylesheet" in n.attrs.get("rel", "").lower().split()]

    def script_sources(self) -> list[str | None]:
        return [n.attrs.get("src") for n in self.find_all("script")]

    def buttons(self) -> list[Node]:
        return self.find_all("button")


def parse_page(source: str, url: str = "/") -> Page:
    return Page(source, url)


def html_files(public: Path) -> list[Path]:
    """Every HTML file under ``public`` except the Pagefind bundle's."""
    bundle = public / "pagefind"
    return [p for p in sorted(public.rglob("*.html"))
            if bundle not in p.parents]


def page_url(public: Path, path: Path) -> str:
    """The URL path of the page file ``path`` under ``public``."""
    relative = path.relative_to(public).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[:-len("index.html")]
    return "/" + relative


def load_page(public: Path, path: Path) -> Page:
    return Page(path.read_text(encoding="utf-8"), page_url(public, path))


def target_file(public: Path, target: str) -> Path:
    """The file under ``public`` that a URL path ``target`` names."""
    path = public / target.lstrip("/")
    return path / "index.html" if target.endswith("/") or not target \
        else path


def norm_text(text: str) -> str:
    """NFKC-normalise and collapse each run of whitespace to one space."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def squash(text: str) -> str:
    """NFKC-normalise and remove all whitespace."""
    return "".join(unicodedata.normalize("NFKC", text).split())


# --- catalogue pages --------------------------------------------------------

CATALOGUE_HEADER = ["ID", "Procedure", "Reaction type", "Status", "Modified"]
FACETS = ("type", "kind", "status", "tag", "author")
TERM_PAGE = re.compile(r"^/(reaction_types|tags|authors)/[^/]+/$")


def is_catalogue_url(url: str) -> bool:
    """Whether the page at ``url`` carries a catalogue: the procedure
    catalogue, the general procedures' view, a term page or the compound
    catalogue."""
    return (url in ("/procedures/", "/general-procedures/", "/compounds/")
            or TERM_PAGE.match(url) is not None)


def catalogue_rows(page: Page) -> list[Node]:
    """The body rows of the page's ``table.procedure-list``."""
    table = page.find("table", "procedure-list")
    if table is None:
        return []
    body = table.find("tbody")
    return [] if body is None else body.find_all("tr")


def row_cells(row: Node) -> list[Node]:
    """The ``td`` cells of a table row."""
    return [c for c in row.elements() if c.tag == "td"]


def facet_values(page: Page, facet: str) -> list[tuple[str, str]]:
    """The ``(value, label)`` of each ``label.facet-value`` of the
    catalogue facet ``facet``, in document order."""
    group = page.find("details", "facet", data_facet=facet)
    if group is None:
        return []
    found = []
    for label in group.find_all("label", "facet-value"):
        box = label.find("input")
        text = label.find("span", "facet-label")
        found.append((box.attrs.get("value", "") if box else "",
                      "" if text is None else text.norm()))
    return found


# --- a local server and Pagefind searches -----------------------------------

class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


@contextlib.contextmanager
def serve_directory(path: Path) -> Iterator[str]:
    """Serve ``path`` on 127.0.0.1 and a free port; yield the base URL."""
    handler = functools.partial(_QuietHandler, directory=str(path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def pagefind_search(public: Path, requests: list[dict[str, Any]],
                    search_terms: Path = SEARCH_TERMS,
                    language: str = "en",
                    catalogue_core: Path = CATALOGUE_CORE) -> dict[str, Any]:
    """Run searches with the built Pagefind bundle under Node.

    Each request is ``{"term", "filters", "normalise"}``, with an
    optional ``"sort"``, run against the index of ``language``. A plain
    Pagefind search of the term (normalised when the request says so)
    gives the hits, each read with ``data()``. For a term that is not
    null the catalogue searcher, ``OrgSynCatalogue.searcher`` of
    ``catalogue_core``, also searches the raw term. Returns the parsed
    ``{"results": [[{"id", "title", "excerpt", "meta"}, ...], ...],
    "searched": [None | {"ids": [...]} | {"error": "..."}, ...],
    "filters": {...}}``, with one result list and one searched entry per
    request. Skips unless node exists; a missing script or bundle fails
    on an assertion.
    """
    node = require_node()
    for script in (PAGEFIND_QUERY, search_terms, catalogue_core):
        if not script.is_file():
            raise AssertionError(f"{script.relative_to(REPO)} does not exist")
    bundle = public / "pagefind" / "pagefind.js"
    if not bundle.is_file():
        raise AssertionError("public/pagefind/pagefind.js does not exist")
    with tempfile.TemporaryDirectory(prefix="orgsyndb node ") as tmp:
        copy = Path(tmp) / "pagefind.mjs"
        shutil.copy2(bundle, copy)
        with serve_directory(public) as base:
            done = subprocess.run(
                [node, str(PAGEFIND_QUERY), str(copy), f"{base}/pagefind/",
                 str(search_terms), str(catalogue_core), language],
                input=json.dumps(requests), capture_output=True, text=True,
                timeout=600)
    if done.returncode != 0:
        raise AssertionError(
            f"pagefind-query.mjs failed ({done.returncode}): {done.stderr}")
    return json.loads(done.stdout)


# --- PDF helpers ------------------------------------------------------------

MM = 72 / 25.4   # points per millimetre


class PdfInfo(NamedTuple):
    pages: int
    page_size: str


class PdfPage(NamedTuple):
    width: float
    height: float
    words: list[tuple[float, float, str]]   # (xMin, xMax, text)


def pdf_info(path: Path) -> PdfInfo:
    """The page count and page size that ``pdfinfo`` reports."""
    require_pdf_tools()
    done = subprocess.run(["pdfinfo", str(path)], capture_output=True,
                          text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"pdfinfo {path.name}: {done.stderr}")
    pages = re.search(r"^Pages:\s+(\d+)", done.stdout, re.M)
    size = re.search(r"^Page size:\s+(.*)$", done.stdout, re.M)
    if pages is None or size is None:
        raise AssertionError(f"pdfinfo {path.name}: {done.stdout!r}")
    return PdfInfo(int(pages.group(1)), size.group(1).strip())


def pdf_page_texts(path: Path, mode: str = "layout") -> list[str]:
    """The text of each page, from ``pdftotext -layout`` or ``-raw``."""
    if mode not in ("layout", "raw"):
        raise ValueError(mode)
    require_pdf_tools()
    done = subprocess.run(["pdftotext", f"-{mode}", str(path), "-"],
                          capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"pdftotext {path.name}: {done.stderr}")
    pages = done.stdout.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    return pages


_BBOX_PAGE = re.compile(
    r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_BBOX_WORD = re.compile(
    r'<word xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)" '
    r'yMax="[\d.]+">(.*?)</word>', re.S)


def pdf_words(path: Path) -> list[PdfPage]:
    """Per page: its size and the horizontal extent of each word."""
    require_pdf_tools()
    done = subprocess.run(["pdftotext", "-bbox", str(path), "-"],
                          capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"pdftotext {path.name}: {done.stderr}")
    pages = []
    for width, height, inner in _BBOX_PAGE.findall(done.stdout):
        words = [(float(lo), float(hi), html_lib.unescape(text))
                 for lo, hi, text in _BBOX_WORD.findall(inner)]
        pages.append(PdfPage(float(width), float(height), words))
    return pages


def words_outside_margins(pages: list[PdfPage], margin_mm: float = 15.0,
                          tolerance_pt: float = 1.0) -> list[str]:
    """Words whose box leaves the left or right margin, by page."""
    margin = margin_mm * MM
    found = []
    for number, page in enumerate(pages, 1):
        for low, high, text in page.words:
            if low < margin - tolerance_pt or (
                    high > page.width - margin + tolerance_pt):
                found.append(f"page {number}: {text!r} spans "
                             f"{low:.1f}-{high:.1f} of {page.width:.1f}")
    return found


def texts_missing_from_pages(texts: Iterable[str],
                             raw_pages: list[str]) -> list[str]:
    """Texts (whitespace removed) absent from the raw text of every page."""
    squashed = [squash(page) for page in raw_pages]
    return [text for text in texts
            if squash(text) and not any(squash(text) in page
                                        for page in squashed)]


# --- CSS declarations -------------------------------------------------------

class Declaration(NamedTuple):
    selector: str                # "" for an inline style attribute
    prop: str
    value: str
    context: tuple[str, ...]     # enclosing conditional at-rules


_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_CONDITIONAL = ("@media", "@supports", "@layer", "@container")


def _find_delimiter(text: str, pos: int) -> int:
    """Index of the next ``{``, ``;`` or ``}`` outside strings and parens."""
    depth = 0
    quote = ""
    while pos < len(text):
        char = text[pos]
        if quote:
            if char == "\\":
                pos += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and char in "{;}":
            return pos
        pos += 1
    return len(text)


def _parse_items(text: str, pos: int, selector: str,
                 context: tuple[str, ...], out: list[Declaration]) -> int:
    size = len(text)
    while pos < size:
        while pos < size and text[pos].isspace():
            pos += 1
        if pos >= size:
            break
        if text[pos] == "}":
            return pos + 1
        if text[pos] == ";":
            pos += 1
            continue
        end = _find_delimiter(text, pos)
        head = text[pos:end].strip()
        if end < size and text[end] == "{":
            if head.startswith(_CONDITIONAL):
                pos = _parse_items(text, end + 1, selector,
                                   context + (head,), out)
            else:
                nested = f"{selector} {head}".strip() \
                    if head.startswith("@") else head
                pos = _parse_items(text, end + 1, nested, context, out)
            continue
        if head and not head.startswith("@") and ":" in head:
            prop, value = head.split(":", 1)
            prop = prop.strip()
            out.append(Declaration(
                selector, prop if prop.startswith("--") else prop.lower(),
                value.strip(), context))
        pos = end if end < size and text[end] == "}" else end + 1
        if end < size and text[end] == "}":
            return end + 1
    return pos


def parse_css(text: str) -> list[Declaration]:
    """Every declaration of a stylesheet, with its selector and context.

    Rules inside ``@media`` and similar blocks carry the at-rule's prelude
    in ``context``. Rules of ``@page`` and its margin boxes carry
    ``@page`` or ``@page @bottom-center`` as their selector.
    """
    text = _COMMENT.sub("", text)
    out: list[Declaration] = []
    pos = 0
    while pos < len(text):
        pos = _parse_items(text, pos, "", (), out)
    return out


def inline_declarations(style: str) -> list[Declaration]:
    """The declarations of an inline ``style`` attribute value."""
    return [d._replace(selector="") for d in parse_css(f"x {{ {style} }}")]


def read_css(path: Path) -> list[Declaration]:
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO)} does not exist")
    return parse_css(path.read_text(encoding="utf-8"))


def selectors_of(declaration: Declaration) -> list[str]:
    """The comma-separated selectors of a declaration's rule."""
    return [s.strip() for s in declaration.selector.split(",") if s.strip()]


def plain_value(value: str) -> str:
    """A declaration value, lowercased, without ``!important``."""
    return re.sub(r"\s*!important\s*$", "", value.strip(),
                  flags=re.I).strip().lower()


def _subject_is_img(selector: str) -> bool:
    compound = re.split(r"\s*[>+~]\s*|\s+", selector.strip())[-1]
    return re.match(r"img(?:[.#:\[].*)?$", compound) is not None


def clipping_violations(declarations: Iterable[Declaration]) -> list[str]:
    """The declarations print-layout "Nothing is clipped" forbids.

    ``overflow``, ``overflow-x`` and ``overflow-y`` of ``hidden`` or
    ``clip``, and any ``height`` or ``max-height`` other than ``auto`` or
    ``none``, except ``max-height`` on a selector whose subject is ``img``.
    """
    found = []
    for decl in declarations:
        value = plain_value(decl.value)
        label = f"{decl.selector or '<inline>'} {{ {decl.prop}: {value} }}"
        if decl.prop in ("overflow", "overflow-x", "overflow-y"):
            if {"hidden", "clip"} & set(value.split()):
                found.append(label)
        elif decl.prop in ("height", "max-height"):
            if value in ("auto", "none"):
                continue
            selectors = selectors_of(decl)
            if decl.prop == "max-height" and selectors and all(
                    _subject_is_img(s) for s in selectors):
                continue
            found.append(label)
    return found


def hex_rgb(color: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(f"not a six-digit hex colour: {color!r}")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def relative_luminance(color: str) -> float:
    """WCAG 2 relative luminance of a six-digit hex colour."""
    def channel(value: int) -> float:
        value /= 255
        return value / 12.92 if value <= 0.03928 \
            else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(v) for v in hex_rgb(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """WCAG 2 contrast ratio of two six-digit hex colours."""
    high, low = sorted((relative_luminance(first),
                        relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)
