"""Recoverable replacement of the export directory (org-export)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline_support import pipeline


class FailingOn:
    """A ``rename`` that counts calls and fails on the chosen ones."""

    def __init__(self, *failing: int) -> None:
        self.failing = set(failing)
        self.calls = 0

    def __call__(self, source, target) -> None:
        self.calls += 1
        if self.calls in self.failing:
            raise OSError(f"injected failure on rename call {self.calls}")
        os.rename(source, target)


def failing_remove(path) -> None:
    raise OSError(f"injected failure removing {path}")


def files(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in directory.iterdir()}


class ReplaceExportTests(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="orgsyndb replace "))
        self.addCleanup(shutil.rmtree, base, True)
        self.build = base / "build dir"
        (self.build / "export").mkdir(parents=True)
        (self.build / ".export-staging").mkdir()
        (self.build / "tmp").mkdir()
        (self.build / "export" / "A.md").write_bytes(b"old export\n")
        (self.build / ".export-staging" / "B.md").write_bytes(
            b"new export\n")
        self.export = self.build / "export"
        self.previous = self.build / ".export-previous"
        self.staging = self.build / ".export-staging"

    def test_second_rename_failure_restores_the_previous_export(
            self) -> None:
        """Scenario: Second rename fails."""
        rename = FailingOn(2)
        module = pipeline()
        with self.assertRaises(Exception):
            module.replace_export(self.build, rename, shutil.rmtree)
        self.assertEqual(files(self.export), {"A.md": b"old export\n"})
        self.assertFalse(self.previous.exists())

    def test_failed_restore_says_the_next_export_will_recover(self) -> None:
        """Scenario: Restore fails too."""
        rename = FailingOn(2, 3)
        module = pipeline()
        with self.assertRaises(Exception) as caught:
            module.replace_export(self.build, rename, shutil.rmtree)
        self.assertIn("recover", str(caught.exception).lower())
        pipeline().recover_export(self.build)
        self.assertEqual(files(self.export), {"A.md": b"old export\n"})
        self.assertFalse(self.previous.exists())
        self.assertFalse(self.staging.exists())

    def test_failed_backup_deletion_leaves_the_new_export_live(self) -> None:
        """Scenario: Backup deletion fails after a successful swap."""
        rename = FailingOn()
        pipeline().replace_export(self.build, rename, failing_remove)
        self.assertEqual(rename.calls, 2)
        self.assertEqual(files(self.export), {"B.md": b"new export\n"})
        pipeline().recover_export(self.build)
        self.assertFalse(self.previous.exists())
        self.assertEqual(files(self.export), {"B.md": b"new export\n"})
