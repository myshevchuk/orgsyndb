"""The GitHub Actions workflow that publishes the demo collection
(demo-site "Demo site workflow")."""

import re
import unittest

from pipeline_support import REPO

WORKFLOW = REPO / ".github" / "workflows" / "demo-site.yml"


def jobs(text: str) -> dict[str, str]:
    """Split the workflow's ``jobs:`` mapping into each job's text."""
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


def top_level(text: str, key: str) -> str:
    """Return the text of one top-level key, its own line included."""
    match = re.search(rf"(?ms)^{re.escape(key)}:.*?(?=^\S|\Z)", text)
    return match.group(0) if match else ""


class DemoSiteWorkflowTests(unittest.TestCase):
    def test_workflow_is_wired(self) -> None:
        """Scenario: Workflow is wired."""
        self.assertTrue(WORKFLOW.is_file(),
                        ".github/workflows/demo-site.yml does not exist")
        text = WORKFLOW.read_text(encoding="utf-8")

        triggers = top_level(text, "on")
        self.assertRegex(triggers,
                         r"(?s)push:\s*\n\s+branches:\s*\[\s*main\s*\]")
        self.assertRegex(triggers, r"(?m)^\s+pull_request:")
        self.assertRegex(triggers, r"(?m)^\s+workflow_dispatch:")
        self.assertRegex(top_level(text, "permissions"),
                         r"(?m)^\s+contents:\s*read\s*$")

        found = jobs(text)
        self.assertIn("build", found)
        self.assertIn("deploy", found)
        build, deploy = found["build"], found["deploy"]

        self.assertRegex(build, r"(?m)^\s+container:\s*fedora:44\s*$")
        install = re.search(r"dnf install[^\n]*", build)
        self.assertIsNotNone(install, "build job has no dnf install")
        for package in ("emacs-nox", "git", "python3", "hugo"):
            with self.subTest(package=package):
                self.assertRegex(install.group(0), rf"\s{package}(\s|$)")
        self.assertIn("tools/orgsyndb -C examples/demo build", build)
        self.assertIn("actions/upload-pages-artifact", build)
        self.assertRegex(build, r"(?m)^\s+path:\s*examples/demo/public\s*$")

        self.assertRegex(deploy, r"(?m)^\s+needs:\s*build\s*$")
        self.assertIn("actions/deploy-pages", deploy)
        self.assertRegex(deploy, r"(?m)^\s+name:\s*github-pages\s*$")
        condition = re.search(r"(?m)^\s+if:([^\n]*)$", deploy)
        self.assertIsNotNone(condition, "deploy job has no if condition")
        self.assertIn("pull_request", condition.group(1))
        self.assertIn("refs/heads/main", condition.group(1))
        for grant in ("pages: write", "id-token: write"):
            with self.subTest(grant=grant):
                self.assertIn(grant, deploy)
                self.assertEqual(text.count(grant), 1)

        self.assertNotIn("secrets.", text)
