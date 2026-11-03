"""Testable logic behind tools/orgsyndb.

The Org source names the export needs, the recoverable replacement of
``build/export/``, next-ID allocation, slugs, template filling, the Hugo
overlay, the site's field, reaction-type and route data, PDF jobs and
the Pagefind download.
File discovery and the reading of the collection settings come from
``validate.py`` in the same directory. No Org source is read here: of
``org/procedures/`` only the entry names are, and Emacs examines and
exports the sources. Messages printed to stderr name the program
``orgsyndb``.
"""

import datetime as dt
import functools
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
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
# The procedures and sequences Hugo publishes, one variant per ID, under
# build/.
STAGED = Path("content") / "procedures"
SEQUENCES_STAGED = Path("content") / "sequences"
HELP_STAGED = Path("content") / "help"
# The field, reaction-type and route data Hugo reads as
# site.Data.collection, under build/.
FIELDS_STAGED = Path("data") / "fields.json"
REACTION_TYPES_STAGED = Path("data") / "reaction_types.json"
ROUTES_STAGED = Path("data") / "routes.json"
# The depth limit and the step budget of the route trees the build
# derives.
ROUTE_DEPTH = 6
ROUTE_BUDGET = 200

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

PROG = "orgsyndb"

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


# German transliteration, applied to German titles before ASCII folding.
GERMAN_FOLDS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae",
                              "Ö": "Oe", "Ü": "Ue", "ß": "ss", "ẞ": "SS"})


def slugify(title: str, language: str | None = None) -> str:
    """Return the short ASCII slug of ``title``.

    The slug matches ``[a-z0-9]+(-[a-z0-9]+)*`` and has at most 40
    characters; a longer one is cut at its last hyphen within the limit.
    A German title first has its umlauts and ß written out (ä → ae).
    Raises ValueError when no ASCII letter or digit survives.
    """
    if language == "de":
        title = title.translate(GERMAN_FOLDS)
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


def _replace_once(text: str, pattern: str, line: str, what: str,
                  flags: re.RegexFlag = re.NOFLAG) -> str:
    """Replace the one line matching ``pattern`` with ``line``.

    Raises ValueError, naming ``what``, when the line is missing or
    repeated.
    """
    found = re.findall(pattern, text, flags=flags | re.MULTILINE)
    if len(found) != 1:
        state = "missing" if not found else "repeated"
        raise ValueError(f"template line {what} is {state}")
    return re.sub(pattern, lambda _: line, text,
                  flags=flags | re.MULTILINE)


def fill_template(text: str, kind: str, ident: str, title: str,
                  now: dt.datetime) -> str:
    """Fill a procedure template for ``orgsyndb new``.

    ``kind`` is ``"org"`` or ``"md"``. Every ``OSDB-0000`` becomes
    ``ident`` and every ``osdb-0000`` its lowercase form. The title and
    both timestamps (from aware ``now``) are written into their anchor
    lines; ``title`` is a single line, as ``new_procedure`` checks. The
    stub records no AI model: ``#+AI_MODEL`` lines are dropped. Raises
    ValueError for an unknown ``kind`` or a malformed ``ident``, and
    when an anchor line is missing or repeated.
    """
    if kind not in ("org", "md"):
        raise ValueError(f"unknown template kind {kind!r}")
    if validate.id_number(ident) is None:
        raise ValueError(f"{ident!r} is not a procedure ID")
    text = text.replace("OSDB-0000", ident).replace("osdb-0000",
                                                    ident.lower())
    if kind == "org":
        stamp = org_timestamp(now)
        for keyword, value in (("TITLE", title), ("CREATED", stamp),
                               ("LAST_MODIFIED", stamp)):
            text = _replace_once(
                text, rf"^#\+{keyword}:.*$", f"#+{keyword}: {value}",
                f"#+{keyword}:", re.IGNORECASE)
        return re.sub(r"^#\+AI_MODEL:.*\n?", "", text,
                      flags=re.IGNORECASE | re.MULTILINE)
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
    return head + "\n" + rest


def pdf_jobs(files: Iterable[tuple[Path, dict[str, Any]]], public: Path,
             pdf_dir: Path) -> list[PdfJob]:
    """Return the PDF jobs for ``(content path, front matter)`` pairs.

    Each job renders ``public/procedures/<slug>/index.html`` to
    ``pdf_dir/<content file stem>.pdf``, so a published variant such as
    ``OSDB-0001-x.de.md`` gives ``OSDB-0001-x.de.pdf``. The jobs are
    sorted by PDF name. Raises ValueError naming the expected HTML path
    when a page is missing, or when a front matter has no string
    ``slug``.
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


def remove_tree(path: Path) -> None:
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
            remove_tree(previous)
        else:
            os.rename(previous, export)
    remove_tree(build / STAGING)
    tmp = build / "tmp"
    if tmp.is_dir():
        for entry in tmp.iterdir():
            remove_tree(entry)


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


def check_staging(build: Path, stems: Iterable[str]) -> None:
    """Check that the staging directory holds exactly ``<stem>.md`` for
    each of ``stems``.

    Raises ExportError naming the missing and unexpected entries.
    """
    staging = Path(build) / STAGING
    if not staging.is_dir():
        raise ExportError(f"{staging} does not exist")
    expected = {f"{stem}.md" for stem in stems}
    present = {path.name for path in staging.iterdir()}
    missing, extra = sorted(expected - present), sorted(present - expected)
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise ExportError(f"{staging} does not hold one export per Org "
                          "source: " + "; ".join(details))


def has_org_sources(org_root: str) -> bool:
    """Whether the directory ``org_root`` has an entry that the export
    exports or reports: one that ``validate.discover`` returns, with or
    without a problem. A missing ``org_root``, or one that is not a
    directory, has none. Only entry names are read."""
    return os.path.isdir(org_root) and bool(
        validate.discover(org_root, ".org"))


def org_stems(org_root: str) -> list[str]:
    """Return, sorted, the stems of the Org sources in ``org_root``: the
    names without ``.org`` of the entries that ``validate.discover``
    returns without a problem. A missing ``org_root`` has none. Only
    entry names are read."""
    if not os.path.isdir(org_root):
        return []
    return sorted(entry.name.removesuffix(".org")
                  for entry in validate.discover(org_root, ".org")
                  if entry.problem is None)


# The field and severity of a problem line, after its path.
ORG_ERROR_RE = re.compile(
    r"(?:file_name|front_matter|scope|#\+[A-Za-z_]+|:[^:\s]+:): error: ")


def org_error_reported(report: str, paths: Iterable[str]) -> bool:
    """Whether ``report``, the stdout of export.el, holds a problem line
    with severity ``error``. A line counts only when it begins with one
    of ``paths``, the longest that fits, followed by ``:``, a field and
    ``: error: ``; a path may itself contain such text."""
    ordered = sorted(paths, key=len, reverse=True)
    for line in report.splitlines():
        path = next((p for p in ordered if line.startswith(p + ":")), None)
        if path is not None and ORG_ERROR_RE.match(line, len(path) + 1):
            return True
    return False


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


def site_language(site: Path) -> str:
    """Return the language of the ``locale`` in ``site/hugo.toml``.

    That is its language subtag, lowercased: ``de`` for ``de`` or
    ``de-DE``. Raises ValueError when the file cannot be read, or when
    the locale is missing or names no language in ``validate.LANGUAGES``.
    """
    path = Path(site) / "hugo.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from None
    locale = data.get("locale")
    language = (re.split(r"[-_]", locale)[0].lower()
                if isinstance(locale, str) else None)
    if language not in validate.LANGUAGES:
        raise ValueError(f"{path}: locale is {locale!r}; set it to one of "
                         f"{', '.join(validate.LANGUAGES)}")
    return language


def choose_variants(files: Iterable[tuple[Path, dict[str, Any]]],
                    language: str) -> list[tuple[Path, dict[str, Any]]]:
    """Choose the variant of each ID to publish in ``language``.

    ``files`` are ``(content path, front matter)`` pairs. Of the files
    with one ``id``, the first of these is chosen: the one whose name
    carries ``language``, the one whose name carries no language code,
    then the others in ``validate.LANGUAGES`` order. Returns the chosen
    pairs sorted by ID; a front matter without a string ``id`` raises
    ValueError.
    """
    def rank(pair: tuple[Path, dict[str, Any]]) -> tuple[int, str]:
        code = validate.language_of(Path(pair[0]).name)
        if code == language:
            return (0, str(pair[0]))
        if code is None:
            return (1, str(pair[0]))
        return (2 + validate.LANGUAGES.index(code), str(pair[0]))

    by_id: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, data in files:
        ident = data.get("id")
        if not isinstance(ident, str):
            raise ValueError(f"{path}: front matter has no id")
        by_id.setdefault(ident, []).append((Path(path), data))
    return [min(by_id[ident], key=rank) for ident in sorted(by_id)]


def stage_content(chosen: Iterable[tuple[Path, dict[str, Any]]],
                  target: Path) -> None:
    """Copy the chosen content files into ``target`` for Hugo.

    ``target`` is emptied first. Each copy is named after its base name,
    without a language code, so that Hugo, built in one language, reads
    every file alike. A file whose name carries a language code and whose
    front matter has no ``language`` gets ``language = "<code>"`` as the
    first front-matter line. Every copy has its note references linked
    (``link_notes``).
    """
    target = Path(target)
    remove_tree(target)
    target.mkdir(parents=True)
    for path, data in chosen:
        name = Path(path).name
        text = Path(path).read_text(encoding="utf-8-sig")
        code = validate.language_of(name)
        if code is not None and "language" not in data:
            first, _, rest = text.partition("\n")
            text = f"{first}\nlanguage = {toml_string(code)}\n{rest}"
        (target / f"{validate.base_name(name)}.md").write_text(
            link_notes(text), encoding="utf-8")


# --------------------------------------------------------------------------
# Note references

# The heading of the notes section and the word that refers to a note, in
# each procedure language.
NOTES = {"en": ("Notes", "Note"), "de": ("Anmerkungen", "Anmerkung")}
NOTES_HEADINGS = {heading.casefold() for heading, _ in NOTES.values()}
NOTE_REF_RE = re.compile(
    r"\((?P<word>" + "|".join(word for _, word in NOTES.values())
    + r")(?P<space>\s+)(?P<number>\d{1,9})\)")
# A list item at the top level: indent, number, delimiter, spacing.
NOTE_ITEM_RE = re.compile(r"^( {0,3})(\d{1,9})([.)])([ \t]+|(?=\r?\n)|$)")
ATX_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
# A fence line at any indentation: indent, fence.
ANY_FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})")
# A code span: a backtick run neither escaped nor part of a longer run,
# up to the next run of exactly its length.
MD_CODE_RE = re.compile(r"(?<![\\`])(`+)(?!`).+?(?<!`)\1(?!`)", re.S)


def _indent(line: str) -> int:
    """The width of the leading whitespace of ``line``, tabs at four."""
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip(" "))


def _note_items(lines: list[str]) -> dict[int, int]:
    """Map the index of each top-level item line of the notes list in
    ``lines`` to the number the item is rendered with.

    The notes list is the first ordered list after the level-2 notes
    heading and before the next heading. A line indented to an item's
    content, a nested list or fence among them, belongs to that item.
    The list ends at a line that follows a blank line and is neither
    indented so nor one of its items, or at a fence outside its items.
    Empty when there is no notes list.
    """
    found: dict[int, int] = {}
    fence: str | None = None
    section = False
    number: int | None = None
    delimiter = ""
    content = 0
    after_blank = False
    for index, line in enumerate(lines):
        if fence is not None:
            if re.fullmatch(rf"{re.escape(fence[0])}{{{len(fence)},}}",
                            line.strip()):
                fence = None
            continue
        indent = _indent(line)
        opening = ANY_FENCE_RE.match(line)
        if opening:
            if number is not None and indent < content:
                break
            if number is not None or indent <= 3:
                fence = opening.group(2)
                after_blank = False
            continue
        if ATX_HEADING_RE.match(line):
            if number is not None:
                break
            headings = validate.section_headings(line)
            if headings:
                section = headings[0].casefold() in NOTES_HEADINGS
            continue
        if not section:
            continue
        item = NOTE_ITEM_RE.match(line)
        top = item is not None and (number is None or (
            indent < content and item.group(3) == delimiter))
        if top:
            assert item is not None
            if number is None:
                number, delimiter = int(item.group(2)), item.group(3)
            found[index] = number
            number += 1
            spacing = len(item.group(4).expandtabs(4))
            content = item.end(3) + (spacing if 1 <= spacing <= 4 else 1)
            after_blank = False
        elif number is None:
            continue
        elif not line.strip():
            after_blank = True
        elif indent >= content or not after_blank:
            after_blank = False
        else:
            break
    return found


def link_notes(text: str) -> str:
    """Return the Markdown procedure ``text`` with its notes linked.

    Each top-level item of the notes list, the first ordered list of the
    ``Notes`` or ``Anmerkungen`` section, starts with the anchor
    ``<span id="note-<n>"></span>``, ``n`` the number the item is
    rendered with. Outside fenced code and code spans, each
    ``(Note <n>)`` or ``(Anmerkung <n>)`` becomes a link to the anchor
    of note ``n`` when the list has one. The front matter is left alone,
    and a text without a notes list is returned unchanged.
    """
    front = validate.parse_front_matter(text)
    head = "" if isinstance(front, validate.Problem) else text[
        :len(text) - len(front.body)]
    lines = text[len(head):].splitlines(keepends=True)
    numbers = _note_items(lines)
    if not numbers:
        return text
    for index, number in numbers.items():
        item = NOTE_ITEM_RE.match(lines[index])
        assert item is not None
        cut = item.end()
        space = "" if item.group(4) else " "
        lines[index] = (f'{lines[index][:cut]}{space}'
                        f'<span id="note-{number}"></span>'
                        f'{lines[index][cut:]}')
    notes = set(numbers.values())

    def link(match: re.Match[str]) -> str:
        if int(match["number"]) not in notes:
            return match.group(0)
        return (f"([{match['word']}{match['space']}{match['number']}]"
                f"(#note-{int(match['number'])}))")

    return head + outside(
        MD_FENCE_RE, "".join(lines),
        lambda prose: outside(MD_CODE_RE, prose,
                              lambda plain: NOTE_REF_RE.sub(link, plain)))


# --------------------------------------------------------------------------
# Help pages

# A fenced code block of Markdown, from its opening fence to the closing
# one (or the end of the text).
MD_FENCE_RE = re.compile(
    r"^ {0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n.*?(?:^ {0,3}(?P=fence)[`~]*[ \t]*$"
    r"|\Z)", re.M | re.S)
# A code span, or an inline link [text](target), image or not.
MD_LINK_RE = re.compile(r"(?P<code>(`+).+?\2)"
                        r"|(?P<bang>!?)\[(?P<text>[^\]]*)\]"
                        r"\((?P<target>[^()\s]+)\)", re.S)
# An Org block, from #+begin_<name> to #+end_<name>.
ORG_BLOCK_RE = re.compile(r"^[ \t]*#\+begin_(\w+).*?^[ \t]*#\+end_\1[^\n]*$",
                          re.M | re.S | re.I)
# A =verbatim= or ~code~ span, or a bracket link [[target][description]].
ORG_LINK_RE = re.compile(
    r"(?P<code>(?:(?<=[\s({'\"-])|^)([=~])\S(?:[^\n]*?\S)??\2"
    r"(?=[\s.,;:!?')}\"\\-]|$))"
    r"|\[\[(?P<target>[^\]]+)\](?:\[(?P<text>[^\]]+)\])?\]", re.M)
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def help_slug(name: str) -> str:
    """Return the help-page slug of the document file ``name``.

    That is the name without its suffix, lowercased, with every ``.``
    replaced by ``-``: ``authoring-org-de`` for ``AUTHORING-ORG.de.org``.
    """
    return name.rsplit(".", 1)[0].lower().replace(".", "-")


def help_link(target: str, names: set[str]) -> str | None:
    """Return the help-page URL a document link ``target`` leads to.

    A target with a URI scheme, or beginning with ``#``, ``/`` or ``*``,
    is returned unchanged. A target whose path names one of ``names``
    becomes ``/help/<slug>/`` with the target's fragment, if any. Any
    other target names an unpublished file: returns None.
    """
    if URI_SCHEME_RE.match(target) or target[:1] in ("#", "/", "*"):
        return target
    path, hash_, fragment = target.partition("#")
    if path not in names:
        return None
    return f"/help/{help_slug(path)}/{hash_}{fragment}"


def outside(pattern: re.Pattern[str], text: str,
            change: Callable[[str], str]) -> str:
    """Return ``text`` with ``change`` applied to every stretch between
    the matches of ``pattern``; the matches are kept as they are."""
    out, last = [], 0
    for match in pattern.finditer(text):
        out += [change(text[last:match.start()]), match.group(0)]
        last = match.end()
    return "".join(out + [change(text[last:])])


def help_page(name: str, text: str, names: set[str]) -> str:
    """Return the text to stage for the help document ``name``.

    ``text`` is the document's text and ``names`` the names of all
    staged documents. A Markdown document begins with a ``# <title>``
    line; an Org document has a ``#+TITLE:`` line before its first
    heading. That line is replaced by a TOML front matter with
    ``title``, ``help_group`` (``glossaries`` for a name beginning with
    ``GLOSSARY``, else ``guides``), ``help_base`` (the slug of the name
    without its language code) and ``help_language`` (the name's
    language code, or ``en``). Links outside code are rewritten: a link
    to one of ``names`` leads to its help page, and a link to any other
    relative path becomes its text. Raises ValueError when the title
    line is missing.
    """
    if name.endswith(".org"):
        head = re.split(r"(?m)^\*+ ", text, maxsplit=1)[0]
        line = re.search(r"(?im)^#\+title:[ \t]*(.*)$", head)
        if line is None:
            raise ValueError("no #+TITLE: line before the first heading")
        title = line.group(1).strip()
        body = text[:line.start()] + text[line.end() + 1:]

        def link(match: re.Match[str]) -> str:
            if match.group("code"):
                return match.group(0)
            target = match.group("target").removeprefix("file:")
            label = match.group("text") or target
            url = help_link(target, names)
            if url is None:
                return label
            if url == target:
                return match.group(0)
            return f"[[{url}][{label}]]"

        body = outside(ORG_BLOCK_RE, body,
                       lambda part: ORG_LINK_RE.sub(link, part))
    else:
        first, _, body = text.partition("\n")
        title = first.removeprefix("# ").strip()
        if not first.startswith("# ") or not title:
            raise ValueError("the first line is not a '# ' title")

        def link(match: re.Match[str]) -> str:
            if match.group("code") or match.group("bang"):
                return match.group(0)
            url = help_link(match.group("target"), names)
            if url is None:
                return match.group("text")
            return f"[{match.group('text')}]({url})"

        body = outside(MD_FENCE_RE, body,
                       lambda part: MD_LINK_RE.sub(link, part))
    group = "glossaries" if name.startswith("GLOSSARY") else "guides"
    base = validate.base_name(name).lower().replace(".", "-")
    language = validate.language_of(name) or "en"
    return ("+++\n"
            f"title = {toml_string(title)}\n"
            f"help_group = {toml_string(group)}\n"
            f"help_base = {toml_string(base)}\n"
            f"help_language = {toml_string(language)}\n"
            "+++\n" + body)


def stage_help(docs: Path, target: Path) -> int:
    """Stage the documents of ``docs`` as help pages in ``target``.

    The documents are the ``.md`` and ``.org`` files directly in
    ``docs``; none when it does not exist. Each is staged as its
    ``help_slug`` and suffix, with the text ``help_page`` returns.
    ``target`` is emptied first. Returns the number of pages staged.
    Raises ValueError, before ``target`` is touched, when two documents
    have one slug, when a name carries a language code outside
    ``validate.LANGUAGES``, or when a document has no title.
    """
    docs, target = Path(docs), Path(target)
    sources = sorted(p for p in docs.iterdir()
                     if p.is_file() and p.suffix in (".md", ".org")) \
        if docs.is_dir() else []
    names = {path.name for path in sources}
    staged: dict[str, tuple[Path, str]] = {}
    for path in sources:
        code = validate.language_of(path.name)
        if code is not None and code not in validate.LANGUAGES:
            raise ValueError(f"{path}: language code {code} is not one of "
                             f"{', '.join(validate.LANGUAGES)}")
        slug = help_slug(path.name)
        if slug in staged:
            raise ValueError(f"{staged[slug][0]} and {path} both give the "
                             f"help page /help/{slug}/")
        try:
            text = help_page(path.name, path.read_text(encoding="utf-8-sig"),
                             names)
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from None
        staged[slug] = (path, text)
    remove_tree(target)
    target.mkdir(parents=True)
    for slug, (path, text) in staged.items():
        (target / f"{slug}{path.suffix}").write_text(text, encoding="utf-8")
    return len(staged)


def fields_data(settings: Path, language: str) -> dict[str, Any]:
    """Return the field data that the site reads for the collection whose
    settings file is SETTINGS, in the site's LANGUAGE.

    The result is a table of two keys. ``compound`` lists a table per
    declared compound field, in declared order: its ``key``, ``type``
    and ``column``; its ``label`` as LANGUAGE shows it; ``facet`` for a
    boolean or choice field, ``search`` for a text field and ``beside``
    for a text or number field; the ``unit`` of a number field that
    declares one; and for a choice field ``multiple``, ``tabs``,
    ``values`` and ``order``. ``procedure`` lists a table per declared
    procedure field, in declared order, with the same keys except
    ``column``, ``search``, ``tabs`` and ``beside``. ``values`` maps
    every value of the field's vocabulary to its shown ``label``, its
    ``path``, the shown labels of its ancestors, outermost first, then
    its own, and its ``ancestors``, the keys of its ancestors,
    outermost first. ``order`` lists every value's key depth first:
    each top-level value in file order, followed by the values filed
    under it in the same order, recursively. A German label replaces
    the English one on a German site where one is given.
    A SETTINGS that does not exist gives ``{"compound": [],
    "procedure": []}``. Raises ``validate.ConfigError`` when the
    declarations or their vocabularies break a rule of
    ``validate.load_fields``.
    """
    def shown(label: str, label_de: str | None) -> str:
        return label_de if language == "de" and label_de else label

    def ancestors(terms: dict[str, validate.Term], value: str) -> list[str]:
        keys = []
        current = terms[value].parent
        while current is not None:
            keys.insert(0, current)
            current = terms[current].parent
        return keys

    def below(terms: dict[str, validate.Term],
              parent: str | None) -> list[str]:
        order = []
        for value, term in terms.items():
            if term.parent == parent:
                order += [value, *below(terms, value)]
        return order

    def describe(field: validate.Declaration,
                 compound: bool) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "key": field.key, "type": field.type,
            "label": shown(field.label, field.label_de)}
        if compound:
            entry["column"] = field.column
        if field.type in ("boolean", "choice"):
            entry["facet"] = field.facet
        if compound and field.type == "text":
            entry["search"] = field.search
        if compound and field.type in ("text", "number"):
            entry["beside"] = field.beside
        if field.unit is not None:
            entry["unit"] = field.unit
        if field.type == "choice":
            entry["multiple"] = field.multiple
            if compound:
                entry["tabs"] = field.tabs
            labels = {value: shown(term.label, term.label_de)
                      for value, term in field.terms.items()}
            entry["values"] = {}
            for value in field.terms:
                keys = ancestors(field.terms, value)
                entry["values"][value] = {
                    "label": labels[value],
                    "path": [labels[key] for key in [*keys, value]],
                    "ancestors": keys}
            entry["order"] = below(field.terms, None)
        return entry

    fields = validate.load_fields(Path(settings), must_exist=False)
    return {"compound": [describe(f, True) for f in fields.compound],
            "procedure": [describe(f, False) for f in fields.procedure]}


def reaction_types_data(settings: Path,
                        language: str) -> dict[str, dict[str, str]]:
    """Return the reaction-type data that the site reads for the
    collection whose settings file is SETTINGS, in the site's LANGUAGE.

    The result maps every reaction type of the collection, the values of
    ``vocabularies/reaction-types.toml`` beside SETTINGS in file order,
    to a table holding only ``label``: the value's German label when
    LANGUAGE is ``de`` and the value has one, its English label
    otherwise. A collection without that file gives an empty table.
    Raises ``validate.ConfigError`` when the file breaks a rule of
    ``validate.load_reaction_types``.
    """
    return {value: {"label": term.label_de if language == "de"
                    and term.label_de else term.label}
            for value, term in validate.load_reaction_types(
                Path(settings)).items()}


class _Maker(NamedTuple):
    """A step to a compound: a procedure, or one entry of a general
    procedure, that makes it at YIELD_PERCENT from SUBSTRATES."""
    procedure: str
    entry: int | None
    yield_percent: Any
    substrates: tuple[str, ...]


class _OverBudget(Exception):
    """A route tree being built has more steps than its budget."""


def routes_data(files: Iterable[tuple[Path, dict[str, Any]]],
                depth: int = ROUTE_DEPTH,
                budget: int = ROUTE_BUDGET) -> dict[str, list[dict[str, Any]]]:
    """Return the route trees of the compounds that the procedures of
    FILES make, drawn to at most DEPTH steps and within BUDGET steps.

    FILES holds pairs of a path and the front matter of a procedure, of
    which only ``id``, ``products``, ``substrates`` and ``scope`` are
    read. A step to a compound is a specific procedure that lists it
    among its ``products``, or an entry of a general procedure that
    does; it starts from that procedure's or entry's ``substrates``, in
    order, or from nothing when they are unset. The steps to a compound
    come by procedure ID, the entries of one procedure in entry order.

    A tree of a compound R alternates compounds and steps: under a
    compound the steps it keeps, under a step the compounds it starts
    from. A compound keeps every step to it except those that start
    from a compound on its path, the compounds from R down to it, both
    included, so that no cycle is followed. A tree to the depth D
    expands the compounds fewer than D steps below R; a compound D
    steps below R is cut off when it keeps a step, and a plain leaf
    otherwise. R's route tree is its tree to the largest depth from 1
    to DEPTH that holds at most BUDGET steps, counted at every level,
    or its tree to the depth 1 when even that holds more.

    The result maps the key of every compound whose route tree goes
    past one step, that is, one of whose steps starts from a compound
    that is expanded with a step or cut off, to the list of the steps
    it keeps. A step is a table of ``procedure``, the procedure's ID;
    ``entry``, the entry's number counted from 1, only for an entry of
    a general procedure; ``yield_percent``, the yield of the compound it
    makes; and ``substrates``, one table per compound it starts from,
    holding ``compound``, its key, ``steps``, its own steps, empty
    unless it is expanded, and ``more``, true exactly when it is cut
    off. Raises ``KeyError`` when a procedure lacks ``id``, or a product
    lacks ``compound`` or ``yield_percent``.
    """
    makers: dict[str, list[_Maker]] = {}
    for _, data in sorted(files, key=lambda item: item[1]["id"]):
        scope = data.get("scope")
        for number, run in enumerate(scope or [data], 1):
            for product in run.get("products", []):
                makers.setdefault(product["compound"], []).append(_Maker(
                    data["id"], number if scope else None,
                    product["yield_percent"],
                    tuple(run.get("substrates", []))))

    def kept(compound: str, path: frozenset[str]) -> list[_Maker]:
        return [maker for maker in makers.get(compound, [])
                if path.isdisjoint(maker.substrates)]

    def tree(root: str, limit: int,
             cap: int | None) -> tuple[list[dict[str, Any]], bool]:
        # The steps of ROOT's tree to the depth LIMIT, and whether it
        # cuts a compound off; raises _OverBudget past CAP steps.
        size, cut = 0, False

        def grow(compound: str, path: frozenset[str],
                 level: int) -> list[dict[str, Any]]:
            nonlocal size, cut
            steps = []
            for maker in kept(compound, path):
                size += 1
                if cap is not None and size > cap:
                    raise _OverBudget
                substrates = []
                for key in maker.substrates:
                    below = path | {key}
                    substrate: dict[str, Any] = {
                        "compound": key, "steps": [], "more": False}
                    if level + 1 < limit:
                        substrate["steps"] = grow(key, below, level + 1)
                    elif kept(key, below):
                        substrate["more"] = cut = True
                    substrates.append(substrate)
                step: dict[str, Any] = {"procedure": maker.procedure}
                if maker.entry is not None:
                    step["entry"] = maker.entry
                steps.append(step | {"yield_percent": maker.yield_percent,
                                     "substrates": substrates})
            return steps

        return grow(root, frozenset({root}), 0), cut

    # Deepen one level at a time and abandon a tree as soon as it passes
    # the budget, so that no tree much larger than the budget is built.
    # A tree that cuts nothing off is the same at every greater depth.
    routes = {}
    for compound in sorted(makers):
        drawn, cut = tree(compound, 1, None)
        for limit in range(2, depth + 1):
            if not cut:
                break
            try:
                drawn, cut = tree(compound, limit, budget)
            except _OverBudget:
                break
        if any(substrate["steps"] or substrate["more"]
               for step in drawn for substrate in step["substrates"]):
            routes[compound] = drawn
    return routes


def _json_value(value: Any) -> Any:
    """Return ``value``, a parsed TOML value, as a value ``json.dumps``
    writes as strict JSON: dates and times as their ISO 8601 text, and
    a float that is not finite as None, inside arrays and tables too."""
    match value:
        case dict():
            return {key: _json_value(item) for key, item in value.items()}
        case list():
            return [_json_value(item) for item in value]
        case dt.date() | dt.time():
            return value.isoformat()
        case float() if not math.isfinite(value):
            return None
    return value


def _declaration_data(field: validate.Declaration,
                      withheld: Sequence[str]) -> dict[str, Any]:
    """Return the index's table of the declaration FIELD: the options
    every type takes and those of its type, in the validator's order,
    without the options in WITHHELD."""
    values = {"min": field.minimum, "max": field.maximum,
              "pattern": field.pattern and field.pattern.pattern}
    return {option: values[option] if option in values
            else getattr(field, option)
            for option in (*validate.FIELD_OPTIONS,
                           *validate.TYPE_OPTIONS[field.type])
            if option not in withheld}


def _terms_data(terms: dict[str, validate.Term]) -> dict[str, Any]:
    """Return the index's table of the vocabulary values TERMS."""
    return {value: term._asdict() for value, term in terms.items()}


def _content_entries(collection: Path, directory: str, suffix: str,
                     kind: validate.Kind,
                     source: str | None = None) -> list[dict[str, Any]]:
    """Return the index entries of the content files of DIRECTORY of
    COLLECTION, in name order: each file with SUFFIX whose name the
    file-name pattern of KIND accepts. SOURCE, when given, is the
    entries' ``format``. An Org file's ``front_matter`` is None; a
    Markdown file's is parsed."""
    root = collection / directory
    pattern = validate.file_name_pattern(suffix, kind.prefix)
    entries = []
    for name in sorted(os.listdir(root)) if root.is_dir() else ():
        match = pattern.match(name)
        if match is None or (root / name).is_dir():
            continue
        item: dict[str, Any] = {"id": match.group(2),
                                "language": match.group(3),
                                "path": f"{directory}/{name}"}
        if source is not None:
            item["format"] = source
        item["front_matter"] = None
        if suffix == ".md":
            text = validate.read_text(str(root / name))
            parsed = (validate.parse_front_matter(text)
                      if isinstance(text, str) else text)
            if isinstance(parsed, validate.Problem):
                item["error"] = parsed.message
            else:
                item["front_matter"] = _json_value(parsed.data)
        entries.append(item)
    return entries


def _by_id(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the index entries ENTRIES ordered by ID and then by path."""
    return sorted(entries, key=lambda item: (item["id"], item["path"]))


def index_data(collection: Path) -> dict[str, Any]:
    """Return the index of the collection directory COLLECTION, a table
    that ``json.dumps`` writes as strict JSON.

    Its keys are ``site_language``, the language of the application's
    site; ``schema``, the procedure, compound and sequence keys the
    validator knows; ``fields``, the collection's compound and procedure
    declarations, each with the options of its type and its defaults
    applied; ``vocabularies``, the values of every vocabulary a
    declaration names and of the reaction types, each with its
    ``label``, ``label_de`` and ``parent``; and ``compounds``,
    ``procedures`` and ``sequences``, one entry per content file whose
    name the validator accepts, with its parsed table or front matter.
    A content file that cannot be parsed is listed with that value None
    and the reason in ``error``; an Org source is listed by name, with
    ``front_matter`` None. Dates and times appear as ISO 8601 text, and
    floats that are not finite as None. Reads no Org file and writes
    nothing. Raises ``validate.ConfigError`` when the settings, the
    declarations or their vocabularies break a rule of
    ``validate.load_fields``, or the reaction types one of
    ``validate.load_reaction_types``, and ValueError when the site's
    language cannot be read.
    """
    collection = Path(collection)
    settings = collection / validate.DEFAULT_SETTINGS
    fields = validate.load_fields(settings)
    reaction_types = validate.load_reaction_types(settings)
    vocabularies: dict[str, Any] = {}
    for entity in validate.ENTITIES:
        for field in getattr(fields, entity.name):
            if field.vocabulary is not None:
                vocabularies[field.vocabulary] = _terms_data(field.terms)
    if (collection / validate.REACTION_TYPES).exists():
        vocabularies["reaction-types"] = _terms_data(reaction_types)

    registry = collection / validate.DEFAULT_COMPOUNDS
    compounds = []
    for name in sorted(os.listdir(registry)) if registry.is_dir() else ():
        match = validate.COMPOUND_FILE_RE.match(name)
        if match is None or (registry / name).is_dir():
            continue
        item: dict[str, Any] = {
            "key": match.group(1),
            "path": f"{validate.DEFAULT_COMPOUNDS.as_posix()}/{name}"}
        data = validate.read_compound(str(registry / name))
        if isinstance(data, validate.Problem):
            item["data"] = None
            item["error"] = data.message
        else:
            item["data"] = _json_value(data)
        compounds.append(item)

    return {
        "site_language": site_language(APP / "site"),
        "schema": {
            "procedure": {
                "required": list(validate.REQUIRED_KEYS),
                "optional": list(validate.OPTIONAL_KEYS),
                "entry": list(validate.SCOPE_ENTRY_KEYS),
                "product": list(validate.PRODUCT_KEYS),
                "statuses": list(validate.STATUSES),
                "languages": list(validate.LANGUAGES),
                "shared": list(validate.SHARED_FIELDS),
                "sections": {language: list(names) for language, names
                             in validate.SECTIONS_BY_LANGUAGE.items()},
            },
            "compound": {
                "required": list(validate.COMPOUND_REQUIRED_KEYS),
                "optional": list(validate.COMPOUND_OPTIONAL_KEYS),
            },
            "sequence": {
                "keys": list(validate.SEQUENCE_KEYS),
                "step": list(validate.STEP_KEYS),
            },
        },
        "fields": {entity.name: [_declaration_data(field, entity.withheld)
                                 for field in getattr(fields, entity.name)]
                   for entity in validate.ENTITIES},
        "vocabularies": vocabularies,
        "compounds": sorted(compounds, key=lambda item: item["key"]),
        "procedures": _by_id(
            _content_entries(collection, "org/procedures", ".org",
                             validate.PROCEDURE, "org")
            + _content_entries(collection, "md/procedures", ".md",
                               validate.PROCEDURE, "md")),
        "sequences": _by_id(_content_entries(
            collection, validate.DEFAULT_SEQUENCES.as_posix(), ".md",
            validate.SEQUENCE)),
    }


def hugo_overlay(site: Path, collection: Path, language: str) -> str:
    """Return the Hugo configuration overlay for building ``collection``.

    ``site`` is the application's Hugo project and ``collection`` the
    collection directory, both absolute; ``language`` is the site's
    language. The overlay sets ``defaultContentLanguage`` to it, the
    publish and resource directories inside the collection, and seven
    module mounts: the application's pages, the staged procedures of
    ``build/content/procedures/``, the staged help pages of
    ``build/content/help/``, the collection's static files, the
    collection's ``compounds/`` as the data entry ``compounds``, the
    staged sequences of ``build/content/sequences/``, and the staged
    ``build/data/``, which holds the field, reaction-type and route
    data, as the data entry ``collection``. The site has no data entry
    but these two.
    """
    site, collection = Path(site), Path(collection)

    def mount(source: Path, target: str, files: str | None = None) -> str:
        text = (f"\n[[module.mounts]]\nsource = {toml_string(str(source))}\n"
                f"target = {toml_string(target)}\n")
        return text + (f"files = [{toml_string(files)}]\n" if files else "")

    return ("# Generated by tools/orgsyndb for this collection; do not edit.\n"
            f"publishDir = {toml_string(str(collection / 'public'))}\n"
            "resourceDir = "
            f"{toml_string(str(collection / 'build' / 'hugo-resources'))}\n"
            f"defaultContentLanguage = {toml_string(language)}\n"
            + mount(site / "content", "content")
            + mount(collection / "build" / STAGED, "content/procedures",
                    "/OSDB-*.md")
            + mount(collection / "build" / HELP_STAGED, "content/help")
            + mount(collection / "static", "static")
            + mount(collection / "compounds", "data/compounds")
            + mount(collection / "build" / SEQUENCES_STAGED,
                    "content/sequences", "/SEQ-*.md")
            + mount(collection / "build" / FIELDS_STAGED.parent,
                    "data/collection"))


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
        remove_tree(binary)
        remove_tree(download)
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
    """Return ``(path, front matter)`` for each content file of ``roots``.

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
# Procedure stubs


class UsageError(Exception):
    """An argument of ``orgsyndb new`` is wrong; the program exits 2."""


def _new_title(words: Sequence[str]) -> str:
    """Join and check the title words; raise UsageError."""
    title = " ".join(words).strip()
    if not title:
        raise UsageError("the title must not be empty")
    if "\n" in title or "\r" in title:
        raise UsageError("the title must be a single line")
    return title


def _warn(message: str) -> None:
    print(f"{PROG}: warning: {message}", file=sys.stderr)


def template_path(kind: str, language: str | None) -> Path:
    """Return the application's procedure template of ``kind`` in
    ``language``: ``templates/procedure.<kind>`` for English or None,
    ``templates/procedure.<language>.<kind>`` otherwise."""
    if language in (None, validate.DEFAULT_LANGUAGE):
        return TEMPLATES / f"procedure.{kind}"
    return TEMPLATES / f"procedure.{language}.{kind}"


def new_procedure(collection: Path, words: Sequence[str], md: bool,
                  now: dt.datetime | None = None,
                  language: str | None = None) -> Path:
    """Create a procedure stub in ``collection``; return its relative path.

    Without ``language`` the stub is the English template under a name
    without a language code. With one, it is that language's template,
    and the name carries the code, as in ``OSDB-0009-titel.de.org``.
    Raises UsageError for a bad title or language, and
    ValueError when the file exists or the template cannot be filled.
    """
    if language is not None and language not in validate.LANGUAGES:
        raise UsageError(f"--lang {language!r} must be one of "
                         f"{', '.join(validate.LANGUAGES)}")
    title = _new_title(words)
    try:
        slug = slugify(title, language)
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    if now is None:
        now = dt.datetime.now(berlin()).replace(microsecond=0)
    collection = Path(collection)
    kind = "md" if md else "org"
    ident = next_id(candidate_names(collection, _warn))
    template = template_path(kind, language)
    text = fill_template(template.read_text(encoding="utf-8"), kind, ident,
                         title, now)
    code = "" if language is None else f".{language}"
    relative = (Path(SOURCE_TREES[kind == "md"])
                / f"{ident}-{slug}{code}.{kind}")
    target = collection / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        raise ValueError(f"{relative} already exists") from None
    return relative
