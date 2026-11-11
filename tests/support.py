"""Shared helpers for the validator tests.

Tests drive tools/validate.py as a subprocess with ``cwd`` set to a
temporary directory, and locate the repository from this file.
"""

import contextlib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
VALIDATOR = REPO / "tools" / "validate.py"
BASELINE = FIXTURES / "baseline" / "OSDB-0100-baseline.md"
GENERAL = FIXTURES / "general" / "OSDB-0140-general.md"
SEQUENCES = FIXTURES / "sequences"
SEQUENCE_BASELINE = SEQUENCES / "SEQ-0001-baseline.md"
SEQUENCE_TEMPLATE = REPO / "templates" / "sequence.md"
SETTINGS_DIR = FIXTURES / "settings"
SETTINGS = SETTINGS_DIR / "orgsyndb.toml"
STATIC_DIR = FIXTURES / "static"
REGISTRY = FIXTURES / "registry.json"
PROCEDURE_TEMPLATE = REPO / "templates" / "procedure.md"
PROCEDURE_FIELDS = FIXTURES / "procedure-fields"

_LINE = re.compile(
    r"^(?P<path>.+?):(?P<field>[^:\s]+): "
    r"(?P<severity>error|warning): (?P<message>.*)$"
)


class Problem(NamedTuple):
    path: str
    field: str
    severity: str
    message: str


class Result(NamedTuple):
    returncode: int
    stdout: str
    stderr: str
    problems: list[Problem]


def parse_problems(stdout: str) -> list[Problem]:
    """Parse stdout lines into (path, field, severity, message)."""
    found = []
    for line in stdout.splitlines():
        match = _LINE.match(line)
        if match is None:
            raise AssertionError(f"unparseable problem line: {line!r}")
        found.append(Problem(*match.group("path", "field", "severity",
                                          "message")))
    return found


def run_validator(args: Sequence[str | Path],
                  cwd: Path | None = None) -> Result:
    """Run tools/validate.py as a subprocess in a temporary directory."""
    if not VALIDATOR.is_file():
        raise AssertionError("tools/validate.py does not exist")
    with contextlib.ExitStack() as stack:
        if cwd is None:
            cwd = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        done = subprocess.run(
            [sys.executable, str(VALIDATOR), *map(str, args)],
            cwd=cwd, capture_output=True, text=True, timeout=60,
        )
    stdout = done.stdout
    try:
        problems = parse_problems(stdout)
    except AssertionError:
        problems = []
    return Result(done.returncode, stdout, done.stderr, problems)


def fixture_run(*roots: str | Path,
                extra: Sequence[str | Path] = (),
                registry: Path = REGISTRY,
                settings: Path = SETTINGS) -> Result:
    """Fixture run: roots are relative to tests/fixtures/ unless absolute.

    ``registry`` is the snapshot file the run reads, the fixture registry
    unless a registry variant names another; ``settings`` is the
    settings file, the fixture settings file unless a variant names
    another.
    """
    args: list[str | Path] = [
        "--settings", settings, "--static-dir", STATIC_DIR,
        "--registry", registry,
    ]
    args += extra
    args += [FIXTURES / root for root in roots]
    return run_validator(args)


def valid_set_run() -> Result:
    """Fixture run on valid/md and valid/export."""
    return fixture_run("valid/md", "valid/export")


# Textual edits on the baseline. Each takes and returns the full text.
Edit = Callable[[str], str]


def replace_line(key: str, new_line: str) -> Edit:
    """Replace the single line that assigns ``key``."""
    def edit(text: str) -> str:
        pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.M)
        if len(pattern.findall(text)) != 1:
            raise AssertionError(f"baseline has no unique line for {key}")
        return pattern.sub(lambda _: new_line, text, count=1)
    return edit


def remove_line(key: str) -> Edit:
    """Remove the single line that assigns ``key``."""
    def edit(text: str) -> str:
        pattern = re.compile(rf"^{re.escape(key)}\s*=.*\n", re.M)
        if len(pattern.findall(text)) != 1:
            raise AssertionError(f"baseline has no unique line for {key}")
        return pattern.sub("", text, count=1)
    return edit


def insert_line(new_line: str) -> Edit:
    """Insert a line among the top-level keys, before the closing ``+++``."""
    def edit(text: str) -> str:
        lines = text.split("\n")
        closing = [i for i, ln in enumerate(lines) if ln == "+++"][1]
        lines.insert(closing, new_line)
        return "\n".join(lines)
    return edit


def products_line(*entries: str) -> str:
    """The ``products`` line of a baseline variant, one entry per table.

    Each entry is the inside of an inline table, such as
    ``compound = "ethanol", yield_percent = 10``.
    """
    return "products = [" + ", ".join(
        "{ " + entry + " }" for entry in entries) + "]"


def swap_delimiters() -> Edit:
    """Turn both ``+++`` delimiter lines into ``---``."""
    def edit(text: str) -> str:
        lines = text.split("\n")
        for i in [i for i, ln in enumerate(lines) if ln == "+++"][:2]:
            lines[i] = "---"
        return "\n".join(lines)
    return edit


def move_section(name: str, before: str) -> Edit:
    """Move the ``## name`` section, with content, before ``## before``."""
    def edit(text: str) -> str:
        head = f"## {name}\n"
        start = text.index(head)
        end = text.find("\n## ", start + 1)
        section = text[start:end + 1]
        text = text[:start] + text[end + 1:]
        at = text.index(f"## {before}\n")
        return text[:at] + section + text[at:]
    return edit


def fence_heading(line: str) -> Edit:
    """Wrap the heading line in a fenced code block."""
    def edit(text: str) -> str:
        if text.count(f"\n{line}\n") != 1:
            raise AssertionError(f"baseline has no unique {line!r}")
        return text.replace(f"\n{line}\n", f"\n```\n{line}\n```\n", 1)
    return edit


def apply_edits(text: str, edits: Sequence[Edit]) -> str:
    for edit in edits:
        text = edit(text)
    return text


def replace_text(old: str, new: str) -> Edit:
    """Replace the one occurrence of ``old`` in the text by ``new``."""
    def edit(text: str) -> str:
        if text.count(old) != 1:
            raise AssertionError(f"the text has no unique {old!r}")
        return text.replace(old, new, 1)
    return edit


def replace_block(key: str, new_text: str) -> Edit:
    """Replace the top-level assignment of ``key``, which may span
    several lines and ends at a line that closes its array, by
    ``new_text``."""
    def edit(text: str) -> str:
        pattern = re.compile(
            rf"^{re.escape(key)} = \[.*?^\]$|^{re.escape(key)}\s*=.*$",
            re.M | re.S)
        found = pattern.search(text)
        if found is None:
            raise AssertionError(f"the text has no assignment of {key}")
        return text[:found.start()] + new_text + text[found.end():]
    return edit


@contextlib.contextmanager
def _edited_root(source: Path, file_name: str,
                 edits: Sequence[Edit]) -> Iterator[Path]:
    text = apply_edits(source.read_text(encoding="utf-8"), edits)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "content"
        root.mkdir()
        (root / file_name).write_text(text, encoding="utf-8")
        yield root


def variant_root(file_name: str, *edits: Edit
                 ) -> contextlib.AbstractContextManager[Path]:
    """Write the edited baseline as the only file of a fresh root."""
    return _edited_root(BASELINE, file_name, edits)


def variant_run(file_name: str, *edits: Edit) -> Result:
    """Variant run: the edited baseline under ``file_name``."""
    with variant_root(file_name, *edits) as root:
        return fixture_run(root)


def general_variant_root(file_name: str, *edits: Edit
                         ) -> contextlib.AbstractContextManager[Path]:
    """Write the edited general baseline as the only file of a fresh
    root."""
    return _edited_root(GENERAL, file_name, edits)


def general_variant_run(file_name: str, *edits: Edit) -> Result:
    """General variant run: the edited general baseline,
    ``tests/fixtures/general/OSDB-0140-general.md``, under ``file_name``,
    as the only file of a fresh content root."""
    with general_variant_root(file_name, *edits) as root:
        return fixture_run(root)


def sequence_fixture_run(*roots: str | Path, sequences: str | Path,
                         extra: Sequence[str | Path] = (),
                         registry: Path = REGISTRY) -> Result:
    """Sequence fixture run: a fixture run on ``roots`` and ``general``
    with ``--sequences`` naming ``sequences``, relative to
    tests/fixtures/ unless absolute."""
    return fixture_run(
        *roots, "general", registry=registry,
        extra=["--sequences", FIXTURES / sequences, *extra])


@contextlib.contextmanager
def sequences_copy() -> Iterator[Path]:
    """A fresh temporary copy of tests/fixtures/sequences/."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp) / "sequences"
        shutil.copytree(SEQUENCES, directory)
        yield directory


def sequence_variant_run(change: Callable[[Path], None]) -> Result:
    """Sequence variant run: ``change`` edits a copy of
    tests/fixtures/sequences/, then a sequence fixture run on
    ``valid/md`` and ``sequences-procedures`` reads that copy."""
    with sequences_copy() as directory:
        change(directory)
        return sequence_fixture_run(
            "valid/md", "sequences-procedures", sequences=directory)


def edit_sequence(name: str, *edits: Edit,
                  rename: str | None = None) -> Callable[[Path], None]:
    """A sequence change applying text edits to the sequence ``name``,
    which is then moved to ``rename`` when that is given."""
    def change(directory: Path) -> None:
        path = directory / name
        path.write_text(apply_edits(path.read_text(encoding="utf-8"),
                                    edits), encoding="utf-8")
        if rename is not None:
            path.rename(directory / rename)
    return change


def add_sequence(file_name: str, *edits: Edit,
                 source: str = "SEQ-0001-baseline.md"
                 ) -> Callable[[Path], None]:
    """A sequence change adding ``file_name``, a copy of the sequence
    ``source`` with the text edits applied."""
    def change(directory: Path) -> None:
        text = (directory / source).read_text(encoding="utf-8")
        (directory / file_name).write_text(apply_edits(text, edits),
                                           encoding="utf-8")
    return change


def remove_sequence(name: str) -> Callable[[Path], None]:
    """A sequence change deleting the sequence ``name``."""
    def change(directory: Path) -> None:
        (directory / name).unlink()
    return change


def add_file(name: str, text: str) -> Callable[[Path], None]:
    """A sequence change writing the file ``name`` with ``text``."""
    def change(directory: Path) -> None:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return change


def changes(*steps: Callable[[Path], None]) -> Callable[[Path], None]:
    """The sequence changes ``steps`` made one after the other."""
    def change(directory: Path) -> None:
        for step in steps:
            step(directory)
    return change


class ValidatorTestCase(unittest.TestCase):
    """Assertions shared by the validator tests."""

    def assert_ran(self, result: Result) -> None:
        """The validator ran to completion and printed its summary."""
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertIn("validated", result.stderr)

    def assert_one(self, result: Result, severity: str, field: str,
                   text: str, path_suffix: str | None = None) -> Problem:
        """Exactly one stdout line, with the given severity, field, text.

        Exit status is 1 for an error and 0 for a warning.
        """
        self.assertEqual(
            result.returncode, 1 if severity == "error" else 0,
            f"stdout={result.stdout!r} stderr={result.stderr!r}")
        self.assertEqual(
            len(result.stdout.splitlines()), 1,
            f"expected exactly one line, got: {result.stdout!r}")
        self.assertEqual(len(result.problems), 1, result.stdout)
        problem = result.problems[0]
        self.assertEqual(problem.severity, severity, result.stdout)
        self.assertEqual(problem.field, field, result.stdout)
        self.assertIn(text, problem.message, result.stdout)
        if path_suffix is not None:
            self.assertTrue(problem.path.endswith(path_suffix),
                            result.stdout)
        return problem

    def assert_clean(self, result: Result) -> None:
        """Exit status 0 and nothing on stdout."""
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def assert_no_lines_for(self, result: Result, needle: str) -> None:
        """No stdout line mentions ``needle``; the run did complete."""
        self.assert_ran(result)
        self.assertEqual(
            [ln for ln in result.stdout.splitlines() if needle in ln], [])


class FieldTestCase(ValidatorTestCase):
    """Assertions of the procedure-field tests."""

    def assert_configuration_error(self, result: Result,
                                   *needles: str) -> None:
        """Exit status 2, nothing on stdout, and a message on stderr that
        begins ``validate.py: error:`` and contains every needle."""
        self.assertEqual(result.returncode, 2,
                         f"stdout={result.stdout!r} "
                         f"stderr={result.stderr!r}")
        self.assertEqual(result.stdout, "")
        self.assertIn("validate.py: error:", result.stderr)
        self.assertNotIn("unrecognized arguments", result.stderr)
        for needle in needles:
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stderr)

    def assert_errors(self, result: Result, field: str, text: str,
                      count: int) -> None:
        """Exit status 1 and exactly ``count`` lines, all errors with
        ``field`` and a message containing ``text``."""
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), count,
                         result.stdout)
        self.assertEqual(len(result.problems), count, result.stdout)
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, field, result.stdout)
            self.assertIn(text, problem.message, result.stdout)


Table = dict[str, Any]


def snapshot_digest(table: Table) -> str:
    """The digest of a snapshot as lab-registry "Snapshot" states it:
    the SHA-256 of the table without ``digest`` and ``import``,
    serialized with sorted keys, no spaces and ASCII escapes."""
    rest = {key: value for key, value in table.items()
            if key not in ("digest", "import")}
    return hashlib.sha256(json.dumps(
        rest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()


def load_snapshot(path: Path = REGISTRY) -> Table:
    """The snapshot file ``path`` as a table."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_snapshot(path: Path, table: Table) -> None:
    """Write ``table`` to ``path`` as a snapshot, with its ``digest``
    made to agree with the rest."""
    table = {**table, "digest": snapshot_digest(table)}
    path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def term(key: str, label: str, label_de: str | None = None,
         parent: str | None = None, tree: bool = True) -> Table:
    """A term of a snapshot's vocabulary; ``tree`` terms carry a
    ``parent``."""
    entry: Table = {"key": key, "label": label, "label_de": label_de}
    if tree:
        entry["parent"] = parent
    return entry


def substance(key: str, name: str | None = None, **values: Any) -> Table:
    """A substance of a snapshot: the fixture registry's kind, in the
    group ``reagents`` and the class ``organic-compounds``, with the
    ``values`` that replace the defaults."""
    entry: Table = {
        "key": key, "name": name or key, "name_de": None,
        "short_name": None, "formula": None, "smiles": None, "cas": None,
        "note": None, "group": "reagents",
        "chemical_classes": ["organic-compounds"], "mw": None,
        "article_number": None}
    entry.update(values)
    return entry


@contextlib.contextmanager
def registry_copy() -> Iterator[Path]:
    """A fresh temporary copy of the fixture registry, the file
    ``registry.json``."""
    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / "registry.json"
        shutil.copyfile(REGISTRY, registry)
        yield registry


RegistryChange = Callable[[Path], None]


def registry_variant_run(change: RegistryChange) -> Result:
    """Registry variant run: ``change`` edits a copy of the registry, then
    a fixture run on ``baseline`` reads that copy."""
    with registry_copy() as registry:
        change(registry)
        return fixture_run("baseline", registry=registry)


def edit_registry(*steps: Callable[[Table], None]) -> RegistryChange:
    """A registry change applying ``steps`` to the snapshot's table,
    which is written back with its digest made to agree."""
    def change(registry: Path) -> None:
        table = load_snapshot(registry)
        for step in steps:
            step(table)
        write_snapshot(registry, table)
    return change


def edit_registry_text(*edits: Edit) -> RegistryChange:
    """A registry change applying text edits to the snapshot file."""
    def change(registry: Path) -> None:
        registry.write_text(
            apply_edits(registry.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change


def without_substance(key: str) -> Callable[[Table], None]:
    """A snapshot step removing the substance ``key``."""
    def step(table: Table) -> None:
        table["substances"] = [s for s in table["substances"]
                               if s["key"] != key]
    return step


def adding_substance(entry: Table) -> Callable[[Table], None]:
    """A snapshot step adding the substance ``entry`` in key order."""
    def step(table: Table) -> None:
        table["substances"] = sorted(
            [*table["substances"], entry], key=lambda s: s["key"])
    return step


def setting_substance(key: str, **values: Any) -> Callable[[Table], None]:
    """A snapshot step setting ``values`` of the substance ``key``; a
    value ``None`` removes the value."""
    def step(table: Table) -> None:
        (found,) = [s for s in table["substances"] if s["key"] == key]
        found.update(values)
    return step


def setting_terms(vocabulary: str, *terms: Table
                  ) -> Callable[[Table], None]:
    """A snapshot step making ``terms`` the whole vocabulary."""
    def step(table: Table) -> None:
        table["vocabularies"][vocabulary] = list(terms)
    return step


def canonical_terms(terms: list[Table]) -> list[Table]:
    """``terms`` in the order a snapshot lists a vocabulary: a parent
    before the terms filed under it, and siblings in key order."""
    known = {entry["key"] for entry in terms}
    children: dict[str | None, list[Table]] = {}
    for entry in terms:
        parent = entry.get("parent")
        children.setdefault(parent if parent in known else None,
                            []).append(entry)
    found: list[Table] = []

    def visit(parent: str | None) -> None:
        for entry in sorted(children.get(parent, []),
                            key=lambda each: each["key"]):
            found.append(entry)
            visit(entry["key"])

    visit(None)
    return found


def with_fixture_substances(table: Table, *keys: str) -> list[str]:
    """Add to the snapshot ``table`` the substances ``keys`` of the
    fixture registry that it lacks, with the terms of their group and
    classes that it lacks, and keep its vocabularies in snapshot order.
    Returns the keys added."""
    fixture = load_snapshot(REGISTRY)
    offered = {entry["key"]: entry for entry in fixture["substances"]}
    held = {entry["key"] for entry in table["substances"]}
    added = []
    for key in keys:
        if key in held:
            continue
        if key not in offered:
            raise AssertionError(
                f"tests/fixtures/registry.json has no substance {key}")
        table["substances"].append(offered[key])
        held.add(key)
        added.append(key)
    table["substances"].sort(key=lambda entry: entry["key"])
    wanted = {
        "inventory-groups": {entry["group"] for entry in
                             table["substances"] if entry["key"] in added},
        "chemical-classes": {name for entry in table["substances"]
                             if entry["key"] in added
                             for name in entry["chemical_classes"]}}
    for name, keys_wanted in wanted.items():
        known = {entry["key"] for entry in table["vocabularies"][name]}
        table["vocabularies"][name] = canonical_terms(
            table["vocabularies"][name]
            + [entry for entry in fixture["vocabularies"][name]
               if entry["key"] in keys_wanted - known])
    return added


def append_text(line: str) -> Edit:
    """A text edit appending ``line`` and a newline to a file."""
    return lambda text: text + line + "\n"


def insert_after(anchor: str, line: str) -> Edit:
    """A text edit inserting ``line`` on the line after the unique line
    ``anchor``."""
    def edit(text: str) -> str:
        if text.count(f"{anchor}\n") != 1:
            raise AssertionError(f"the text has no unique line {anchor!r}")
        return text.replace(f"{anchor}\n", f"{anchor}\n{line}\n", 1)
    return edit


@contextlib.contextmanager
def template_registry() -> Iterator[Path]:
    """A temporary snapshot file holding the substance
    ``example-compound`` and the reaction type that
    ``templates/procedure.md`` names."""
    text = PROCEDURE_TEMPLATE.read_text(encoding="utf-8")
    found = re.search(r'(?m)^reaction_types\s*=\s*\["([^"]+)"\]', text)
    if found is None:
        raise AssertionError("the template names no reaction type")
    table: Table = {
        "format": 1,
        "vocabularies": {
            "chemical-classes": [term("organic-compounds",
                                      "Organic compounds")],
            "inventory-groups": [term("reagents", "Reagents")],
            "projects": [],
            "reaction-types": [term(found.group(1), found.group(1),
                                    tree=False)]},
        "substances": [substance("example-compound", "Example compound",
                                 formula="C2H6O", mw=46.07,
                                 smiles="CCO")]}
    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / "registry.json"
        write_snapshot(registry, table)
        yield registry


@contextlib.contextmanager
def format_settings() -> Iterator[Path]:
    """A temporary settings file ``orgsyndb.toml`` holding
    ``format = 1`` alone."""
    with tempfile.TemporaryDirectory() as tmp:
        settings = Path(tmp) / "orgsyndb.toml"
        settings.write_text("format = 1\n", encoding="utf-8")
        yield settings


def declaration(key: str, type_: str, label: str, *lines: str) -> str:
    """The text of one ``[[fields.compound]]`` table, after a blank
    line, with the extra assignment ``lines``."""
    body = "".join(f"{line}\n" for line in lines)
    return (f'\n[[fields.compound]]\nkey = "{key}"\ntype = "{type_}"\n'
            f'label = "{label}"\n{body}')


def procedure_declaration(key: str, type_: str, label: str,
                          *lines: str) -> str:
    """The text of one ``[[fields.procedure]]`` table, after a blank
    line, with the extra assignment ``lines``."""
    return declaration(key, type_, label, *lines).replace(
        "[[fields.compound]]", "[[fields.procedure]]")


class ProcedureFieldCopy(NamedTuple):
    """The temporary copies of a procedure-field run."""
    settings: Path
    registry: Path
    content: Path


@contextlib.contextmanager
def procedure_fields_copy() -> Iterator[ProcedureFieldCopy]:
    """Fresh temporary copies of ``tests/fixtures/procedure-fields/`` and
    of the fixture registry, and a fresh content root holding the
    baseline as its only file."""
    with tempfile.TemporaryDirectory() as tmp:
        fields = Path(tmp) / "procedure-fields"
        shutil.copytree(PROCEDURE_FIELDS, fields)
        registry = Path(tmp) / "registry.json"
        shutil.copyfile(REGISTRY, registry)
        content = Path(tmp) / "content"
        content.mkdir()
        shutil.copyfile(BASELINE, content / BASELINE.name)
        yield ProcedureFieldCopy(fields / "orgsyndb.toml", registry,
                                 content)


ProcedureFieldChange = Callable[[ProcedureFieldCopy], None]


def procedure_field_run(*steps: ProcedureFieldChange,
                        extra: Sequence[str | Path] = ()) -> Result:
    """Procedure-field run: each of ``steps`` edits the copies, then a
    fixture run on the content root reads the registry copy and, through
    ``--settings``, the copy of ``orgsyndb.toml``."""
    with procedure_fields_copy() as copy:
        for step in steps:
            step(copy)
        return fixture_run(
            copy.content, registry=copy.registry,
            settings=copy.settings, extra=extra)


def edit_procedure_settings(*edits: Edit) -> ProcedureFieldChange:
    """A procedure-field change applying text edits to
    ``orgsyndb.toml``."""
    def change(copy: ProcedureFieldCopy) -> None:
        copy.settings.write_text(
            apply_edits(copy.settings.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change


def edit_procedure_registry(*steps: Callable[[Table], None]
                            ) -> ProcedureFieldChange:
    """A procedure-field change applying ``steps`` to the registry
    copy's table."""
    def change(copy: ProcedureFieldCopy) -> None:
        edit_registry(*steps)(copy.registry)
    return change


def edit_procedure(name: str, *edits: Edit) -> ProcedureFieldChange:
    """A procedure-field change applying text edits to the file ``name``
    of the content root."""
    def change(copy: ProcedureFieldCopy) -> None:
        path = copy.content / name
        path.write_text(
            apply_edits(path.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change


def add_procedure(name: str, *edits: Edit,
                  source: str | Path = BASELINE.name
                  ) -> ProcedureFieldChange:
    """A procedure-field change adding ``name`` to the content root: a
    copy of ``source``, a file of the content root named alone or a path,
    with the text edits applied."""
    def change(copy: ProcedureFieldCopy) -> None:
        path = Path(source)
        if not path.is_absolute():
            path = copy.content / path
        (copy.content / name).write_text(
            apply_edits(path.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change
