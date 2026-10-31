"""Shared helpers for the validator tests.

Tests drive tools/validate.py as a subprocess with ``cwd`` set to a
temporary directory, and locate the repository from this file.
"""

import contextlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
VALIDATOR = REPO / "tools" / "validate.py"
BASELINE = FIXTURES / "baseline" / "OSDB-0100-baseline.md"
GENERAL = FIXTURES / "general" / "OSDB-0140-general.md"
SEQUENCES = FIXTURES / "sequences"
SEQUENCE_BASELINE = SEQUENCES / "SEQ-0001-baseline.md"
SEQUENCE_TEMPLATE = REPO / "templates" / "sequence.md"
VOCABULARY = FIXTURES / "reaction_types.toml"
STATIC_DIR = FIXTURES / "static"
COMPOUNDS = FIXTURES / "compounds"
COMPOUND_TEMPLATE = REPO / "templates" / "compound.toml"
FIELDS = FIXTURES / "fields"

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
                compounds: Path = COMPOUNDS) -> Result:
    """Fixture run: roots are relative to tests/fixtures/ unless absolute.

    ``compounds`` is the registry the run reads, the fixture registry
    unless a registry variant names another.
    """
    args: list[str | Path] = [
        "--vocabulary", VOCABULARY, "--static-dir", STATIC_DIR,
        "--compounds", compounds,
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
                         compounds: Path = COMPOUNDS) -> Result:
    """Sequence fixture run: a fixture run on ``roots`` and ``general``
    with ``--sequences`` naming ``sequences``, relative to
    tests/fixtures/ unless absolute."""
    return fixture_run(
        *roots, "general", compounds=compounds,
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


@contextlib.contextmanager
def registry_copy() -> Iterator[Path]:
    """A fresh temporary copy of the fixture registry."""
    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / "compounds"
        shutil.copytree(COMPOUNDS, registry)
        yield registry


def registry_variant_run(change: Callable[[Path], None]) -> Result:
    """Registry variant run: ``change`` edits a copy of the registry, then
    a fixture run on ``baseline`` reads that copy."""
    with registry_copy() as registry:
        change(registry)
        return fixture_run("baseline", compounds=registry)


def edit_compound(key: str, *edits: Edit) -> Callable[[Path], None]:
    """A registry change applying text edits to ``<key>.toml``."""
    def change(registry: Path) -> None:
        path = registry / f"{key}.toml"
        path.write_text(apply_edits(path.read_text(encoding="utf-8"),
                                    edits), encoding="utf-8")
    return change


@contextlib.contextmanager
def template_registry() -> Iterator[Path]:
    """A temporary registry holding ``templates/compound.toml`` as
    ``example-compound.toml``, the compound the procedure templates name."""
    if not COMPOUND_TEMPLATE.is_file():
        raise AssertionError("templates/compound.toml does not exist")
    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / "compounds"
        registry.mkdir()
        shutil.copy2(COMPOUND_TEMPLATE, registry / "example-compound.toml")
        yield registry


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


def declaration(key: str, type_: str, label: str, *lines: str) -> str:
    """The text of one ``[[fields.compound]]`` table, after a blank
    line, with the extra assignment ``lines``."""
    body = "".join(f"{line}\n" for line in lines)
    return (f'\n[[fields.compound]]\nkey = "{key}"\ntype = "{type_}"\n'
            f'label = "{label}"\n{body}')


class FieldCopy(NamedTuple):
    """The temporary copies of a field-declaration run."""
    settings: Path
    vocabularies: Path
    registry: Path


@contextlib.contextmanager
def fields_copy() -> Iterator[FieldCopy]:
    """Fresh temporary copies of ``tests/fixtures/fields/`` and of the
    fixture registry."""
    with tempfile.TemporaryDirectory() as tmp:
        fields = Path(tmp) / "fields"
        shutil.copytree(FIELDS, fields)
        registry = Path(tmp) / "compounds"
        shutil.copytree(COMPOUNDS, registry)
        yield FieldCopy(fields / "orgsyndb.toml", fields / "vocabularies",
                        registry)


FieldChange = Callable[[FieldCopy], None]


def field_variant_run(*steps: FieldChange,
                      extra: Sequence[str | Path] = ()) -> Result:
    """Field-declaration run: each of ``steps`` edits the copies, then a
    fixture run on ``baseline`` reads the registry copy and, through
    ``--settings``, the copy of ``orgsyndb.toml``."""
    with fields_copy() as copy:
        for step in steps:
            step(copy)
        return fixture_run(
            "baseline", compounds=copy.registry,
            extra=["--settings", copy.settings, *extra])


def edit_settings(*edits: Edit) -> FieldChange:
    """A field change applying text edits to ``orgsyndb.toml``."""
    def change(copy: FieldCopy) -> None:
        copy.settings.write_text(
            apply_edits(copy.settings.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change


def edit_field_compound(key: str, *edits: Edit) -> FieldChange:
    """A field change applying text edits to the registry copy's
    ``<key>.toml``."""
    def change(copy: FieldCopy) -> None:
        edit_compound(key, *edits)(copy.registry)
    return change


def edit_vocabulary(name: str, *edits: Edit) -> FieldChange:
    """A field change applying text edits to ``vocabularies/<name>.toml``
    of the fields copy."""
    def change(copy: FieldCopy) -> None:
        path = copy.vocabularies / f"{name}.toml"
        path.write_text(
            apply_edits(path.read_text(encoding="utf-8"), edits),
            encoding="utf-8")
    return change


def write_vocabulary(name: str, content: str | bytes) -> FieldChange:
    """A field change writing ``vocabularies/<name>.toml`` of the fields
    copy, replacing or adding the file."""
    def change(copy: FieldCopy) -> None:
        path = copy.vocabularies / f"{name}.toml"
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return change
