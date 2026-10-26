"""The ERT suite of tools/osdb-org.el under pytest (org-export "ERT
suite")."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline_support import REPO, make_path, require_tool

SUITE = REPO / "tests" / "el" / "osdb-org-tests.el"
SUMMARY = re.compile(r"Ran (\d+) tests, (\d+) results as expected, "
                     r"(\d+) unexpected(?:, (\d+) skipped)?")


class ErtSuiteTests(unittest.TestCase):
    def test_ert_suite_passes(self) -> None:
        """Scenario: ERT suite under pytest."""
        emacs = require_tool("emacs")
        self.assertTrue(SUITE.is_file(),
                        "tests/el/osdb-org-tests.el does not exist")
        with tempfile.TemporaryDirectory(prefix="orgsyndb ert ") as cwd:
            done = subprocess.run(
                [emacs, "-Q", "--batch", "-l", str(SUITE),
                 "-f", "ert-run-tests-batch-and-exit"],
                cwd=cwd, capture_output=True, text=True, timeout=600)
        output = done.stdout + done.stderr
        self.assertEqual(done.returncode, 0, output)
        summary = SUMMARY.search(output)
        self.assertIsNotNone(summary, output)
        ran, _, unexpected, skipped = summary.groups(default="0")
        self.assertGreater(int(ran), 0, output)
        self.assertEqual(int(unexpected), 0, output)
        if os.geteuid() != 0:
            # The unreadable-source test skips itself for root only.
            self.assertEqual(int(skipped), 0, output)

    def test_ert_suite_is_skipped_without_emacs(self) -> None:
        """Scenario: ERT suite without Emacs."""
        # A pytest plugin may call git, so keep it when it is installed.
        path = make_path(self, tuple(tool for tool in ("python3", "git")
                                     if shutil.which(tool)))
        env = dict(os.environ, PATH=str(path.directory))
        # The inner run selects the other test, so that it cannot recurse.
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-rs", "-p",
             "no:cacheprovider", "-k", "test_ert_suite_passes",
             str(Path(__file__).resolve())],
            cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
        output = done.stdout + done.stderr
        self.assertEqual(done.returncode, 0, output)
        self.assertRegex(output, r"SKIPPED.*emacs")
        self.assertIn("1 skipped", output)


if __name__ == "__main__":
    unittest.main()
