#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Testable logic behind tools/orgsyndb.

The export plan and its timestamp rule, the recoverable replacement of
``build/export/``, next-ID allocation, slugs, template filling, the Hugo
overlay, PDF jobs and the Pagefind download. File discovery and Org
timestamp parsing come from ``validate.py`` in the same directory. The
command-line interface is low-level plumbing for tests and debugging; it
exits 0 on success, 1 on failure and 2 on a usage error, and writes
errors to stderr as ``pipeline.py: error: <message>``.
"""

import argparse
import datetime as dt
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import validate

APP = Path(__file__).resolve().parent.parent
TEMPLATES = APP / "templates"

ID_PREFIX_RE = re.compile(r"^OSDB-(\d{4})", re.IGNORECASE)
SLUG_LIMIT = 40
SOURCE_TREES = ("org/procedures", "md/procedures")

EXPORT = "export"
STAGING = ".export-staging"
PREVIOUS = ".export-previous"
PLAN_NAME = "export-plan.json"

PAGEFIND_VERSION = "1.5.2"
PAGEFIND_TARBALL = (f"pagefind-v{PAGEFIND_VERSION}-x86_64-unknown-linux-"
                    "musl.tar.gz")
PAGEFIND_URL = ("https://github.com/Pagefind/pagefind/releases/download/"
                f"v{PAGEFIND_VERSION}/{PAGEFIND_TARBALL}")
PAGEFIND_TAR_SHA256 = ("afb824a9e7f64905a934900481cea5be"
                       "679c03975e527329e0e5e6cc70f5feda")
PAGEFIND_BIN_SHA256 = ("c4b86009ce5420dc2a1748ab2705bef6"
                       "ba730ed883f684fd52ef6008bd600532")

WEASYPRINT_WARNING_FILTER = "ignore:pkg_resources is deprecated:UserWarning"

# The program named in the messages this module prints; tools/orgsyndb
# sets it to its own name.
PROG = "pipeline.py"

Rename = Callable[[Path, Path], None]
Remove = Callable[[Path], None]


class ExportError(Exception):
    """Installing or recovering the export directory failed."""


class PagefindError(Exception):
    """The Pagefind download or its verification failed."""


class PdfJob(NamedTuple):
    """One page to render: the HTML input and the PDF output."""

    html: Path
    pdf: Path


@functools.cache
def berlin() -> dt.tzinfo:
    """Return the Europe/Berlin zone; raise ``validate.ConfigError``."""
    return validate.load_zone()


# --------------------------------------------------------------------------
# Pure functions


def slugify(title: str) -> str:
    """Return the short ASCII slug of ``title``.

    The slug matches ``[a-z0-9]+(-[a-z0-9]+)*`` and has at most 40
    characters; a longer one is cut at its last hyphen within the limit.
    Raises ValueError when no ASCII letter or digit survives.
    """
    folded = unicodedata.normalize("NFKD", title).encode(
        "ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    if len(slug) > SLUG_LIMIT:
        cut = slug.rfind("-", 0, SLUG_LIMIT + 1)
        slug = slug[:cut if cut > 0 else SLUG_LIMIT].strip("-")
    if not slug:
        raise ValueError("the title needs at least one letter or digit")
    return slug


def next_id(names: Iterable[str]) -> str:
    """Return the ID one above the highest found at the start of ``names``.

    A name counts when it begins with ``OSDB-NNNN``, in any case. Returns
    ``OSDB-0001`` when none does, and raises ValueError when the highest
    is ``OSDB-9999``.
    """
    numbers = [int(m.group(1)) for m in map(ID_PREFIX_RE.match, names) if m]
    highest = max(numbers, default=0)
    if highest >= 9999:
        raise ValueError("no procedure ID is left above OSDB-9999")
    return f"OSDB-{highest + 1:04d}"


def _berlin_local(moment: dt.datetime) -> dt.datetime:
    """Return aware ``moment`` in Europe/Berlin; raise ValueError if naive."""
    if moment.utcoffset() is None:
        raise ValueError(f"{moment.isoformat()} has no UTC offset")
    return moment.astimezone(berlin())


def org_timestamp(moment: dt.datetime) -> str:
    """Format aware ``moment`` as ``[YYYY-MM-DD Day hh:mm:ss]`` in Berlin.

    The weekday is English whatever the locale. Raises ValueError for a
    naive datetime.
    """
    local = _berlin_local(moment)
    weekday = validate.WEEKDAYS[local.weekday()]
    return f"[{local:%Y-%m-%d} {weekday} {local:%H:%M:%S}]"


def rfc3339(moment: dt.datetime) -> str:
    """Format aware ``moment`` as ``YYYY-MM-DDThh:mm:ss+HH:MM`` in Berlin.

    Raises ValueError for a naive datetime.
    """
    local = _berlin_local(moment)
    offset = validate.format_offset(local.utcoffset() or dt.timedelta())
    return f"{local:%Y-%m-%dT%H:%M:%S}{offset}"


def export_instants(created: Sequence[dt.datetime],
                    last_modified: Sequence[dt.datetime]
                    ) -> tuple[dt.datetime, dt.datetime]:
    """Choose the exported ``(date, lastmod)`` from the named instants.

    Both arguments are non-empty lists of aware instants. ``date`` is the
    earliest of ``created``. ``lastmod`` is the earliest of
    ``last_modified`` not earlier than ``date``, or the latest of
    ``last_modified`` when there is none.
    """
    def instant(moment: dt.datetime) -> dt.datetime:
        return moment.astimezone(dt.UTC)

    date = min(created, key=instant)
    later = [m for m in last_modified if instant(m) >= instant(date)]
    lastmod = (min(later, key=instant) if later
               else max(last_modified, key=instant))
    return date, lastmod


def toml_string(value: str) -> str:
    """Return ``value`` as a TOML basic string, quotes included."""
    out = []
    for char in value:
        if char in '"\\':
            out.append("\\" + char)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def _replace_once(text: str, pattern: str, line: str | None, what: str,
                  flags: re.RegexFlag = re.NOFLAG) -> str:
    """Replace the one line matching ``pattern`` with ``line``.

    A ``line`` of None keeps the matched line. Raises ValueError, naming
    ``what``, when the line is missing or repeated.
    """
    found = re.findall(pattern, text, flags=flags | re.MULTILINE)
    if len(found) != 1:
        state = "missing" if not found else "repeated"
        raise ValueError(f"template line {what} is {state}")
    if line is None:
        return text
    return re.sub(pattern, lambda _: line, text,
                  flags=flags | re.MULTILINE)


def fill_template(text: str, kind: str, ident: str, title: str,
                  now: dt.datetime, ai_model: str | None) -> str:
    """Fill a procedure template for ``orgsyndb new``.

    ``kind`` is ``"org"`` or ``"md"``. Every ``OSDB-0000`` becomes
    ``ident`` and every ``osdb-0000`` its lowercase form. The title,
    both timestamps (from aware ``now``) and the AI model (``None`` for a
    human author) are written into their anchor lines. Raises ValueError
    when an anchor line is missing or repeated, when ``title`` holds a
    line break, or when ``ai_model`` is not a model identifier.
    """
    if kind not in ("org", "md"):
        raise ValueError(f"unknown template kind {kind!r}")
    if not validate.ID_RE.match(ident):
        raise ValueError(f"{ident!r} is not a procedure ID")
    if "\n" in title or "\r" in title:
        raise ValueError("the title must be a single line")
    if ai_model is not None and not validate.AI_MODEL_RE.match(ai_model):
        raise ValueError(f"{ai_model!r} is not a model identifier")
    text = text.replace("OSDB-0000", ident).replace("osdb-0000",
                                                    ident.lower())
    if kind == "org":
        stamp = org_timestamp(now)
        for keyword, value in (("TITLE", title), ("CREATED", stamp),
                               ("LAST_MODIFIED", stamp),
                               ("AI_MODEL", ai_model or "none")):
            text = _replace_once(
                text, rf"^#\+{keyword}:.*$", f"#+{keyword}: {value}",
                f"#+{keyword}:", re.IGNORECASE)
        return text
    lines = text.split("\n")
    if not lines or lines[0] != "+++" or "+++" not in lines[1:]:
        raise ValueError("template has no +++ front matter")
    end = lines.index("+++", 1)
    head, rest = "\n".join(lines[:end]), "\n".join(lines[end:])
    stamp = rfc3339(now)
    head = _replace_once(head, r"^title = .*$",
                         f"title = {toml_string(title)}", "title =")
    head = _replace_once(head, r"^date = .*$", f"date = {stamp}", "date =")
    head = _replace_once(head, r"^lastmod = .*$", f"lastmod = {stamp}",
                         "lastmod =")
    # Without a model the commented line stays, but must still be there.
    head = _replace_once(
        head, r"^# ai_model = .*$",
        f"ai_model = {toml_string(ai_model)}" if ai_model else None,
        "# ai_model =")
    return head + "\n" + rest


def pdf_jobs(files: Iterable[tuple[Path, dict[str, Any]]], public: Path,
             pdf_dir: Path) -> list[PdfJob]:
    """Return the PDF jobs for ``(content path, front matter)`` pairs.

    Each job renders ``public/procedures/<slug>/index.html`` to
    ``pdf_dir/<content file stem>.pdf``. The jobs are sorted by PDF name.
    Raises ValueError naming the expected HTML path when a page is
    missing, or when a front matter has no string ``slug``.
    """
    jobs = []
    for path, data in files:
        slug = data.get("slug")
        if not isinstance(slug, str) or not slug:
            raise ValueError(f"{path}: front matter has no slug")
        html = Path(public) / "procedures" / slug / "index.html"
        if not html.is_file():
            raise ValueError(f"{path}: page {html} does not exist; build "
                             "the site first")
        jobs.append(PdfJob(html, Path(pdf_dir) / f"{Path(path).stem}.pdf"))
    return sorted(jobs, key=lambda job: job.pdf.name)


# --------------------------------------------------------------------------
# The export directory


def _remove_tree(path: Path) -> None:
    """Remove ``path``, a directory tree or a single file, if it exists."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def recover_export(build: Path) -> None:
    """Repair what an interrupted export replacement left in ``build``.

    A backup without a live export is renamed back to ``export/``; a
    backup beside a live export is deleted. Any staging directory is
    deleted, and ``build/tmp/`` is emptied. Raises OSError when a step
    fails.
    """
    build = Path(build)
    export, previous = build / EXPORT, build / PREVIOUS
    if previous.exists():
        if export.exists():
            _remove_tree(previous)
        else:
            os.rename(previous, export)
    _remove_tree(build / STAGING)
    tmp = build / "tmp"
    if tmp.is_dir():
        for entry in tmp.iterdir():
            _remove_tree(entry)


def replace_export(build: Path, rename: Rename = os.rename,
                   remove: Remove = shutil.rmtree) -> None:
    """Replace ``build/export/`` with ``build/.export-staging/``.

    The live export is renamed to ``.export-previous/``, the staging
    directory is renamed into place, and the backup is deleted. When the
    second rename fails, the backup is renamed back before ExportError is
    raised; when that fails too, the ExportError says that the next
    export will recover. A failure to delete the backup only prints a
    warning to stderr, because the new export is already live.
    """
    build = Path(build)
    export, staging = build / EXPORT, build / STAGING
    previous = build / PREVIOUS
    had_export = export.exists()
    if had_export:
        try:
            rename(export, previous)
        except OSError as exc:
            raise ExportError(f"cannot move {export} aside: {exc}; the "
                              "previous export is unchanged") from exc
    try:
        rename(staging, export)
    except OSError as exc:
        if not had_export:
            raise ExportError(f"cannot install {staging}: {exc}") from exc
        try:
            rename(previous, export)
        except OSError as again:
            raise ExportError(
                f"cannot install {staging} ({exc}) nor restore {export} "
                f"from {previous} ({again}); the next export will recover "
                "it") from again
        raise ExportError(f"cannot install {staging}: {exc}; the previous "
                          "export is restored") from exc
    if had_export:
        try:
            remove(previous)
        except OSError as exc:
            print(f"{PROG}: warning: cannot delete {previous}: {exc}; "
                  "the next export removes it", file=sys.stderr)


def check_staging(build: Path, plan: Sequence[dict[str, Any]]) -> None:
    """Check that the staging directory holds exactly the planned files.

    Raises ExportError naming the missing and unexpected entries.
    """
    staging = Path(build) / STAGING
    if not staging.is_dir():
        raise ExportError(f"{staging} does not exist")
    expected = {f"{entry['stem']}.md" for entry in plan}
    present = {path.name for path in staging.iterdir()}
    missing, extra = sorted(expected - present), sorted(present - expected)
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise ExportError(f"{staging} does not hold the planned files: "
                          + "; ".join(details))


def plan_export(org_root: str) -> tuple[list[dict[str, Any]],
                                        list[tuple[str, validate.Problem]]]:
    """Plan the export of the Org procedures in ``org_root``.

    Returns the plan entries, sorted by file name, and the lint problems
    found, as ``(path, problem)`` pairs. Only entries that
    ``validate.discover`` returns without a problem are planned. A
    missing ``org_root`` gives an empty plan.
    """
    if not os.path.exists(org_root):
        return [], []
    plan: list[dict[str, Any]] = []
    problems: list[tuple[str, validate.Problem]] = []
    for entry in validate.discover(org_root, ".org"):
        if entry.problem is not None:
            continue
        text = validate.read_text(entry.path)
        if isinstance(text, validate.Problem):
            problems.append((entry.path, text))
            continue
        found, source = validate.lint_org(text, berlin())
        if found or source.created is None or source.last_modified is None:
            problems += [(entry.path, problem) for problem in found]
            continue
        date, lastmod = export_instants(source.created,
                                        source.last_modified)
        plan.append({
            "source": os.path.abspath(entry.path),
            "stem": entry.name.removesuffix(".org"),
            "date": rfc3339(date),
            "lastmod": rfc3339(lastmod),
            "ai_model": (None if source.ai_model == "none"
                         else source.ai_model),
        })
    return plan, problems


# --------------------------------------------------------------------------
# Next ID


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C repo ARGS`` and capture its output."""
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120)


def candidate_names(collection: Path,
                    warn: Callable[[str], None]) -> list[str]:
    """Return every name ``next_id`` must stay above, for ``collection``.

    These are the top-level entries of the source trees and of
    ``build/export/``, and the base names of every source-tree path in
    the git history of all refs. The collection may be anywhere inside a
    work tree; the history paths are relative to it. Without usable git
    history, or in a shallow clone, ``warn`` is called with the reason.
    """
    repo = Path(collection)
    names: list[str] = []
    for tree in (*SOURCE_TREES, "build/export"):
        if (repo / tree).is_dir():
            names += os.listdir(repo / tree)
    if shutil.which("git") is None:
        warn("git not found; IDs of deleted procedures cannot be seen")
        return names
    inside = _git(repo, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        warn(f"{repo} is not inside a git work tree; IDs of deleted "
             "procedures cannot be seen")
        return names
    shallow = _git(repo, "rev-parse", "--is-shallow-repository")
    if shallow.stdout.strip() == "true":
        warn("this is a shallow clone; IDs deleted before its oldest "
             "commit cannot be seen")
    log = _git(repo, "-c", "core.quotePath=false", "log", "--all",
               "--no-renames", "--format=", "--name-only", "-z", "--",
               *SOURCE_TREES)
    if log.returncode != 0:
        warn("cannot read the git history: " + log.stderr.strip())
        return names
    names += [Path(p).name for p in log.stdout.split("\0") if p.strip()]
    return names


# --------------------------------------------------------------------------
# Hugo


def hugo_overlay(site: Path, collection: Path) -> str:
    """Return the Hugo configuration overlay for building ``collection``.

    ``site`` is the application's Hugo project and ``collection`` the
    collection directory, both absolute. The overlay sets the publish and
    resource directories inside the collection and the four module
    mounts: the application's pages, the Org export, the Markdown
    procedures and the collection's static files.
    """
    site, collection = Path(site), Path(collection)

    def mount(source: Path, target: str, files: bool) -> str:
        text = (f"\n[[module.mounts]]\nsource = {toml_string(str(source))}\n"
                f"target = {toml_string(target)}\n")
        return text + ('files = ["/OSDB-*.md"]\n' if files else "")

    return ("# Generated by tools/orgsyndb for this collection; do not edit.\n"
            f"publishDir = {toml_string(str(collection / 'public'))}\n"
            "resourceDir = "
            f"{toml_string(str(collection / 'build' / 'hugo-resources'))}\n"
            + mount(site / "content", "content", False)
            + mount(collection / "build" / "export", "content/procedures",
                    True)
            + mount(collection / "md" / "procedures", "content/procedures",
                    True)
            + mount(collection / "static", "static", False))


# --------------------------------------------------------------------------
# Pagefind


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of the file at ``path``."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_pagefind(tarball: Path, tar_sha256: str, bin_sha256: str,
                     dest: Path) -> Path:
    """Verify ``tarball`` and install its ``pagefind`` binary in ``dest``.

    The tarball must have SHA-256 ``tar_sha256`` and hold a regular-file
    member ``pagefind`` with SHA-256 ``bin_sha256``. Only that member is
    read. Returns the path of the installed, executable binary. Raises
    PagefindError, naming the expected and actual hash on a mismatch,
    and leaves no ``pagefind`` in ``dest`` on failure.
    """
    dest = Path(dest)
    actual = sha256_file(tarball)
    if actual != tar_sha256:
        raise PagefindError(f"{tarball}: SHA-256 is {actual}, expected "
                            f"{tar_sha256}")
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            try:
                member = tar.getmember("pagefind")
            except KeyError:
                raise PagefindError(
                    f"{tarball} holds no member named pagefind") from None
            if not member.isreg():
                raise PagefindError(f"{tarball}: member pagefind is not a "
                                    "regular file")
            handle = tar.extractfile(member)
            if handle is None:
                raise PagefindError(f"{tarball}: cannot read member "
                                    "pagefind")
            data = handle.read()
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise PagefindError(f"cannot read {tarball}: {exc}") from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != bin_sha256:
        raise PagefindError(f"{tarball}: binary pagefind has SHA-256 "
                            f"{actual}, expected {bin_sha256}")
    binary, partial = dest / "pagefind", dest / ".pagefind.partial"
    try:
        partial.write_bytes(data)
        partial.chmod(0o755)
        partial.replace(binary)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise PagefindError(f"cannot install {binary}: {exc}") from exc
    return binary


def ensure_pagefind(tools_dir: Path) -> Path:
    """Return the verified Pagefind binary under ``tools_dir``.

    A cached ``pagefind-1.5.2/pagefind`` is used when its SHA-256 is the
    pinned one; otherwise the pinned release is downloaded and installed
    through ``install_pagefind``. Raises PagefindError naming the URL or
    the hashes, after deleting whatever this call wrote.
    """
    home = Path(tools_dir) / f"pagefind-{PAGEFIND_VERSION}"
    binary = home / "pagefind"
    if binary.is_file() and sha256_file(binary) == PAGEFIND_BIN_SHA256:
        return binary
    created = not home.exists()
    download = home / "download"
    try:
        _remove_tree(binary)
        _remove_tree(download)
        download.mkdir(parents=True)
        tarball = download / PAGEFIND_TARBALL
        try:
            with (urllib.request.urlopen(PAGEFIND_URL, timeout=120)
                  as response, open(tarball, "wb") as handle):
                shutil.copyfileobj(response, handle)
        except (urllib.error.URLError, OSError) as exc:
            raise PagefindError(f"cannot download {PAGEFIND_URL}: "
                                f"{exc}") from exc
        return install_pagefind(tarball, PAGEFIND_TAR_SHA256,
                                PAGEFIND_BIN_SHA256, home)
    except BaseException:
        if created:
            shutil.rmtree(home, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(download, ignore_errors=True)


# --------------------------------------------------------------------------
# PDF rendering


def content_files(roots: Iterable[str]) -> list[tuple[Path, dict[str, Any]]]:
    """Return ``(path, front matter)`` for each procedure file of ``roots``.

    Files are those ``validate.discover`` accepts. Raises ValueError when
    a file cannot be read or has no valid front matter.
    """
    found = []
    for root in roots:
        for entry in validate.discover(root, ".md"):
            if entry.problem is not None:
                continue
            text = validate.read_text(entry.path)
            parsed = (validate.parse_front_matter(text)
                      if isinstance(text, str) else text)
            if isinstance(parsed, validate.Problem):
                raise ValueError(f"{entry.path}: {parsed.message}")
            found.append((Path(entry.path), parsed.data))
    return found


def render_pdfs(jobs: Sequence[PdfJob]) -> list[PdfJob]:
    """Render each job with WeasyPrint and return the jobs that failed.

    WeasyPrint may fetch only ``file:`` URLs. A job fails when WeasyPrint
    exits non-zero or writes a line beginning ``ERROR:``; its output file
    is then deleted. WeasyPrint's stderr is passed on to stderr.
    """
    env = dict(os.environ)
    env["PYTHONWARNINGS"] = ",".join(
        filter(None, (env.get("PYTHONWARNINGS"), WEASYPRINT_WARNING_FILTER)))
    failed = []
    for job in jobs:
        print(f"pdf: {job.pdf.name}", flush=True)
        done = subprocess.run(
            ["weasyprint", "--allowed-protocols", "file", str(job.html),
             str(job.pdf)], env=env, capture_output=True, text=True)
        output = done.stdout + done.stderr
        if output:
            sys.stderr.write(output if output.endswith("\n")
                             else output + "\n")
        errors = [ln for ln in output.splitlines()
                  if ln.startswith("ERROR:")]
        if done.returncode != 0 or errors:
            job.pdf.unlink(missing_ok=True)
            reason = (errors[0] if errors
                      else f"weasyprint exited {done.returncode}")
            print(f"{PROG}: error: {job.pdf.name}: {reason}",
                  file=sys.stderr, flush=True)
            failed.append(job)
    return failed


# --------------------------------------------------------------------------
# Command line


class UsageError(Exception):
    """A command-line argument is wrong; the CLI exits 2."""


def _load_plan(path: Path) -> list[dict[str, Any]]:
    """Read an export plan written by ``export-plan``."""
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ExportError(f"cannot read the export plan {path}: "
                          f"{exc}") from exc
    if not isinstance(plan, list) or not all(
            isinstance(e, dict) and isinstance(e.get("stem"), str)
            for e in plan):
        raise ExportError(f"{path} is not an export plan")
    return plan


def write_export_plan(org_root: str, plan_path: Path
                      ) -> list[dict[str, Any]] | None:
    """Plan the export of ``org_root`` and write the plan to ``plan_path``.

    Returns the plan. When the sources have lint problems, prints them to
    stderr, deletes any old plan and returns None.
    """
    plan_path = Path(plan_path)
    plan, problems = plan_export(org_root)
    if problems:
        plan_path.unlink(missing_ok=True)
        for path, problem in sorted(problems, key=lambda p: p[0]):
            print(f"{path}:{problem.field}: {problem.severity}: "
                  f"{problem.message}", file=sys.stderr)
        return None
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False)
                         + "\n", encoding="utf-8")
    return plan


def cmd_export_plan(args: argparse.Namespace) -> int:
    """Write the export plan, or print lint errors and return 1."""
    plan = write_export_plan(args.org_root, Path(args.plan))
    return 0 if plan is not None else 1


def cmd_recover_export(args: argparse.Namespace) -> int:
    """Repair the leftovers of an interrupted export."""
    recover_export(Path(args.build))
    return 0


def cmd_install_export(args: argparse.Namespace) -> int:
    """Check the staging directory against the plan, then install it."""
    build = Path(args.build)
    check_staging(build, _load_plan(build / PLAN_NAME))
    replace_export(build)
    return 0


def _new_title(words: Sequence[str]) -> str:
    """Join and check the title words; raise UsageError."""
    title = " ".join(words).strip()
    if not title:
        raise UsageError("the title must not be empty")
    if "\n" in title or "\r" in title:
        raise UsageError("the title must be a single line")
    return title


def _now(value: str | None) -> dt.datetime:
    """Return ``--now`` as an aware datetime, or the current second."""
    if value is None:
        return dt.datetime.now(berlin()).replace(microsecond=0)
    try:
        moment = dt.datetime.fromisoformat(value)
    except ValueError:
        raise UsageError(f"--now {value!r} is not an ISO 8601 date and "
                         "time") from None
    if moment.utcoffset() is None:
        raise UsageError(f"--now {value!r} needs a UTC offset")
    return moment


def _warn(message: str) -> None:
    print(f"{PROG}: warning: {message}", file=sys.stderr)


def cmd_next_id(args: argparse.Namespace) -> int:
    """Print the next free procedure ID of the collection."""
    print(next_id(candidate_names(Path(args.collection), _warn)))
    return 0


def new_procedure(collection: Path, words: Sequence[str], md: bool,
                  ai_model: str | None, now: dt.datetime | None = None
                  ) -> Path:
    """Create a procedure stub in ``collection``; return its relative path.

    Raises UsageError for a bad title or model identifier, and ValueError
    when the file exists or the template cannot be filled.
    """
    if ai_model is not None and not validate.AI_MODEL_RE.match(ai_model):
        raise UsageError(f"--ai-model {ai_model!r} must match "
                         f"{validate.AI_MODEL_RE.pattern}")
    title = _new_title(words)
    try:
        slug = slugify(title)
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    if now is None:
        now = dt.datetime.now(berlin()).replace(microsecond=0)
    collection = Path(collection)
    kind = "md" if md else "org"
    ident = next_id(candidate_names(collection, _warn))
    template = TEMPLATES / f"procedure.{kind}"
    text = fill_template(template.read_text(encoding="utf-8"), kind, ident,
                         title, now, ai_model)
    relative = Path(SOURCE_TREES[kind == "md"]) / f"{ident}-{slug}.{kind}"
    target = collection / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        raise ValueError(f"{relative} already exists") from None
    return relative


def cmd_new(args: argparse.Namespace) -> int:
    """Create a procedure stub and print its collection-relative path."""
    relative = new_procedure(Path(args.collection), args.title, args.md,
                             args.ai_model, _now(args.now))
    print(relative.as_posix())
    return 0


def cmd_pdf(args: argparse.Namespace) -> int:
    """Render every procedure page to a PDF; return 1 if any job failed."""
    pdf_dir = Path(args.pdf_dir)
    jobs = pdf_jobs(content_files(args.roots), Path(args.public), pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    failed = render_pdfs(jobs)
    print(f"pdf: {len(jobs) - len(failed)} of {len(jobs)} files written")
    if failed:
        print("pipeline.py: error: failed: "
              + ", ".join(job.pdf.name for job in failed), file=sys.stderr)
        return 1
    return 0


def cmd_ensure_pagefind(args: argparse.Namespace) -> int:
    """Print the path of the verified Pagefind binary."""
    print(ensure_pagefind(Path(args.tools_dir)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Build-pipeline plumbing behind tools/orgsyndb. "
        "Exits 0 on success, 1 on failure and 2 on a usage error.")
    sub = parser.add_subparsers(dest="command", required=True,
                                metavar="COMMAND")

    plan = sub.add_parser(
        "export-plan", help="plan the export of an Org root",
        description="Write a JSON export plan for the Org procedures of "
        "ORG_ROOT, or print lint errors to stderr and exit 1.")
    plan.add_argument("org_root", metavar="ORG_ROOT")
    plan.add_argument("plan", metavar="PLAN_JSON")
    plan.set_defaults(func=cmd_export_plan)

    recover = sub.add_parser(
        "recover-export", help="repair an interrupted export",
        description="Repair the export directories under BUILD left by an "
        "interrupted run, and empty BUILD/tmp/.")
    recover.add_argument("build", metavar="BUILD")
    recover.set_defaults(func=cmd_recover_export)

    install = sub.add_parser(
        "install-export", help="install the staged export",
        description="Check that BUILD/.export-staging/ holds exactly the "
        f"files planned in BUILD/{PLAN_NAME}, then replace BUILD/export/ "
        "with it.")
    install.add_argument("build", metavar="BUILD")
    install.set_defaults(func=cmd_install_export)

    nxt = sub.add_parser(
        "next-id", help="print the next free procedure ID",
        description="Print the ID one above the highest in the source "
        "trees, the export directory and the git history of COLLECTION.")
    nxt.add_argument("--collection", required=True, metavar="COLLECTION")
    nxt.set_defaults(func=cmd_next_id)

    new = sub.add_parser(
        "new", help="create a procedure stub",
        description="Create org/procedures/<ID>-<slug>.org, or "
        "md/procedures/<ID>-<slug>.md with --md, in COLLECTION from the "
        "application's template, and print its path relative to "
        "COLLECTION.")
    new.add_argument("--collection", required=True, metavar="COLLECTION")
    new.add_argument("--md", action="store_true",
                     help="create a Markdown procedure")
    new.add_argument("--ai-model", metavar="ID",
                     help="identifier of the AI model writing it (default: "
                     "a human author)")
    new.add_argument("--now", metavar="DATETIME",
                     help="ISO 8601 date and time with offset to use "
                     "instead of the current time")
    new.add_argument("title", nargs="+", metavar="TITLE")
    new.set_defaults(func=cmd_new)

    pdf = sub.add_parser(
        "pdf", help="render procedure pages to PDF",
        description="Render public/procedures/<slug>/index.html of every "
        "procedure in ROOT... to PDF_DIR/<file stem>.pdf with WeasyPrint.")
    pdf.add_argument("--public", required=True, metavar="DIR")
    pdf.add_argument("--pdf-dir", required=True, metavar="DIR")
    pdf.add_argument("roots", nargs="+", metavar="ROOT")
    pdf.set_defaults(func=cmd_pdf)

    pagefind = sub.add_parser(
        "ensure-pagefind", help="print the path of a verified Pagefind",
        description=f"Print the path of Pagefind {PAGEFIND_VERSION} under "
        "TOOLS_DIR, downloading and verifying it first when needed.")
    pagefind.add_argument("--tools-dir", required=True, metavar="TOOLS_DIR")
    pagefind.set_defaults(func=cmd_ensure_pagefind)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line on ``argv`` and return the exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UsageError as exc:
        parser.print_usage(sys.stderr)
        print(f"pipeline.py: error: {exc}", file=sys.stderr)
        return 2
    except (ExportError, PagefindError, validate.ConfigError, ValueError,
            OSError) as exc:
        print(f"pipeline.py: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
