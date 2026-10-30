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
VOCABULARY = FIXTURES / "reaction_types.toml"
STATIC_DIR = FIXTURES / "static"
COMPOUNDS = FIXTURES / "compounds"
COMPOUND_TEMPLATE = REPO / "templates" / "compound.toml"

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
