"""Static checks of the Django application's place in the repository
(web-app: Application project, Settings from the environment). They need
neither Django nor a database.
"""

import ast
import os
import re
import shutil
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEBAPP = REPO / "webapp"
FIVE = {"django", "django-simple-history", "psycopg", "gunicorn",
        "whitenoise"}


def requirement_names(requirements: list) -> set[str]:
    names = set()
    for requirement in requirements:
        if isinstance(requirement, str):
            match = re.match(r"[A-Za-z0-9][A-Za-z0-9_.-]*", requirement)
            if match:
                names.add(match.group(0).lower().replace("_", "-"))
    return names


def pyproject() -> dict:
    path = WEBAPP / "pyproject.toml"
    assert path.is_file(), "webapp/pyproject.toml does not exist"
    return tomllib.loads(path.read_text(encoding="utf-8"))


class ProjectFileTests(unittest.TestCase):

    def test_project_file(self) -> None:
        """Scenario: Project file."""
        project = pyproject()["project"]
        self.assertEqual(project["requires-python"], ">=3.14")
        self.assertLessEqual(FIVE, requirement_names(
            project["dependencies"]))

    def test_tests_are_development_dependencies(self) -> None:
        data = pyproject()
        development: set[str] = set()
        for group in data.get("dependency-groups", {}).values():
            development |= requirement_names(group)
        for group in data["project"].get(
                "optional-dependencies", {}).values():
            development |= requirement_names(group)
        development |= requirement_names(
            data.get("tool", {}).get("uv", {}).get("dev-dependencies", []))
        self.assertLessEqual({"pytest", "pytest-django"}, development)
        runtime = requirement_names(data["project"]["dependencies"])
        self.assertFalse({"pytest", "pytest-django"} & runtime)

    def test_lock_file_names_the_dependencies(self) -> None:
        path = WEBAPP / "uv.lock"
        self.assertTrue(path.is_file(), "webapp/uv.lock does not exist")
        names = set(re.findall(r'(?m)^name = "([^"]+)"',
                               path.read_text(encoding="utf-8")))
        self.assertLessEqual(FIVE | {"pytest", "pytest-django"}, names)

    def test_packages(self) -> None:
        self.assertTrue((WEBAPP / "manage.py").is_file())
        for package in ("orgsyndb_web", "accounts", "tasks"):
            with self.subTest(package=package):
                self.assertTrue(
                    (WEBAPP / package / "__init__.py").is_file())
        for module in ("settings.py", "urls.py", "wsgi.py", "index.py",
                       "config.py"):
            with self.subTest(module=module):
                self.assertTrue(
                    (WEBAPP / "orgsyndb_web" / module).is_file())
        self.assertTrue((WEBAPP / "tests" / "__init__.py").is_file())

    def test_database_file_is_ignored(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not found")
        done = subprocess.run(
            ["git", "-C", str(REPO), "check-ignore", "-q",
             "webapp/db.sqlite3"])
        self.assertEqual(done.returncode, 0,
                         "webapp/db.sqlite3 is not ignored")


class RootSuiteTests(unittest.TestCase):

    def test_root_suite_leaves_the_application_out(self) -> None:
        """Scenario: Root suite leaves the application out."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST")}
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider"],
            cwd=REPO, env=env, capture_output=True, text=True,
            timeout=300)
        lines = done.stdout.splitlines() + done.stderr.splitlines()
        collected = [line for line in done.stdout.splitlines()
                     if "::" in line]
        self.assertTrue(collected, done.stdout + done.stderr)
        self.assertTrue(all(line.startswith("tests/")
                            for line in collected), collected[:5])
        self.assertFalse([line for line in lines if "webapp/" in line],
                         "\n".join(lines[-20:]))

    def test_the_program_does_not_import_the_application(self) -> None:
        forbidden = {"webapp", "orgsyndb_web", "accounts", "tasks",
                     "django"}
        sources = [p for p in (REPO / "tools").rglob("*")
                   if p.is_file() and (p.suffix == ".py"
                                       or p.name == "orgsyndb")]
        self.assertTrue(sources)
        for path in sources:
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                modules = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules |= {a.name.split(".")[0]
                                    for a in node.names}
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules.add(node.module.split(".")[0])
                self.assertFalse(modules & forbidden)


if __name__ == "__main__":
    unittest.main()
