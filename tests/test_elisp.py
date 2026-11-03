"""The ERT suites of emacs/osdb-org.el (org-export "ERT suite") and of
the Emacs package (emacs-mode "Package ERT suite") under pytest, and the
byte compilation of the package's files (emacs-mode "Package files")."""

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
PACKAGE_SUITE = REPO / "tests" / "el" / "orgsyndb-tests.el"
PACKAGE = REPO / "emacs"
OX_HUGO = REPO / ".emacs-batch" / "elpa" / "ox-hugo"
SUMMARY = re.compile(r"Ran (\d+) tests, (\d+) results as expected, "
                     r"(\d+) unexpected(?:, (\d+) skipped)?")


def run_suite(case: unittest.TestCase, suite: Path,
              timeout: int = 600) -> tuple[str, int]:
    """Run the ERT SUITE from a temporary working directory and check
    that it exits 0 with no unexpected result. Return its output and the
    number of skipped tests."""
    emacs = require_tool("emacs")
    case.assertTrue(suite.is_file(), f"{suite} does not exist")
    with tempfile.TemporaryDirectory(prefix="orgsyndb ert ") as cwd:
        done = subprocess.run(
            [emacs, "-Q", "--batch", "-l", str(suite),
             "-f", "ert-run-tests-batch-and-exit"],
            cwd=cwd, capture_output=True, text=True, timeout=timeout)
    output = done.stdout + done.stderr
    case.assertEqual(done.returncode, 0, output)
    summary = SUMMARY.search(output)
    case.assertIsNotNone(summary, output)
    ran, _, unexpected, skipped = summary.groups(default="0")
    case.assertGreater(int(ran), 0, output)
    case.assertEqual(int(unexpected), 0, output)
    return output, int(skipped)


class ErtSuiteTests(unittest.TestCase):
    def test_ert_suite_passes(self) -> None:
        """Scenario: ERT suite under pytest."""
        output, skipped = run_suite(self, SUITE)
        if os.geteuid() != 0:
            # The unreadable-source test skips itself for root only.
            self.assertEqual(skipped, 0, output)

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


class PackageSuiteTests(unittest.TestCase):
    def test_package_suite_passes(self) -> None:
        """Scenario: Package suite under pytest."""
        output, skipped = run_suite(self, PACKAGE_SUITE, timeout=900)
        if OX_HUGO.is_dir():
            self.assertEqual(skipped, 0, output)

    def test_clean_byte_compilation(self) -> None:
        """Scenario: Clean byte compilation."""
        emacs = require_tool("emacs")
        files = sorted(PACKAGE.glob("*.el"))
        self.assertIn(PACKAGE / "orgsyndb.el", files)
        with tempfile.TemporaryDirectory(prefix="orgsyndb elc ") as target:
            for file in files:
                # The compiled file goes to TARGET, not beside the source.
                setup = ("(setq byte-compile-error-on-warn t "
                         "byte-compile-dest-file-function (lambda (f) "
                         "(expand-file-name (concat (file-name-nondirectory "
                         f"f) \"c\") {lisp_string(target)})))")
                done = subprocess.run(
                    [emacs, "-Q", "--batch", "-L", str(PACKAGE),
                     "--eval", setup, "-f", "batch-byte-compile", str(file)],
                    cwd=target, capture_output=True, text=True, timeout=300)
                with self.subTest(file=file.name):
                    self.assertEqual(done.returncode, 0,
                                     done.stdout + done.stderr)
        self.assertEqual(sorted(path.name for path in PACKAGE.iterdir()),
                         sorted(file.name for file in files))


def lisp_string(text: str) -> str:
    """Return TEXT as an Emacs Lisp string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


if __name__ == "__main__":
    unittest.main()
