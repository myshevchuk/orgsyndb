"""The GitHub Actions workflow that checks the export on Emacs 29
(org-export "Export checked on Emacs 29")."""

import re
import unittest

from pipeline_support import REPO, workflow_jobs, workflow_key

WORKFLOW = REPO / ".github" / "workflows" / "emacs-29.yml"


class Emacs29WorkflowTests(unittest.TestCase):
    def test_workflow_is_wired(self) -> None:
        """Scenario: Workflow is wired."""
        self.assertTrue(WORKFLOW.is_file(),
                        ".github/workflows/emacs-29.yml does not exist")
        text = WORKFLOW.read_text(encoding="utf-8")

        triggers = workflow_key(text, "on")
        self.assertRegex(triggers,
                         r"(?s)push:\s*\n\s+branches:\s*\[\s*main\s*\]")
        self.assertRegex(triggers, r"(?m)^\s+pull_request:")
        self.assertRegex(triggers, r"(?m)^\s+workflow_dispatch:")
        self.assertRegex(workflow_key(text, "permissions"),
                         r"(?m)^\s+contents:\s*read\s*$")

        job = workflow_jobs(text).get("export")
        self.assertIsNotNone(job, "the workflow has no export job")
        self.assertRegex(job, r"(?m)^\s+runs-on:\s*ubuntu-24\.04\s*$")
        install = re.search(r"apt-get install[^\n]*", job)
        self.assertIsNotNone(install, "export job has no apt-get install")
        for package in ("emacs-nox", "git"):
            with self.subTest(package=package):
                self.assertRegex(install.group(0), rf"\s{package}(\s|$)")
        self.assertIn("actions/setup-python", job)
        self.assertRegex(job, r"(?m)^\s+python-version:\s*['\"]?3\.14['\"]?")
        export = job.find("tools/orgsyndb -C examples/demo export")
        tests = job.find("python -m pytest tests/test_export_integration.py "
                         "tests/test_elisp.py")
        self.assertNotEqual(export, -1, "export job does not export")
        self.assertNotEqual(tests, -1, "export job does not run the tests")
        self.assertLess(export, tests)
