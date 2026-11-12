"""``orgsyndb new`` and the IDs the lab application issues: ``take_id``
and the subcommand (build-script "new subcommand")."""

import datetime as dt
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

from pipeline_support import (FIXTURE_REGISTRY, IdApp, Run, captured,
                              closed_address, front_matter, make_sandbox,
                              name_registry, pipeline, pipeline_function,
                              snapshot)

NOW = "2026-10-19T17:42:05+02:00"
TOKEN = "osdb_test-token-0123456789"


def make_root(case: unittest.TestCase, registry: str | None) -> Path:
    """A temporary collection whose ``orgsyndb.toml`` names ``registry``
    (none when it is None), with its source trees empty."""
    base = Path(tempfile.mkdtemp(prefix="orgsyndb ids "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "collection copy"
    root.mkdir()
    text = "format = 1\n"
    if registry is not None:
        text += f'registry = "{registry}"\n'
    (root / "orgsyndb.toml").write_text(text, encoding="utf-8")
    for tree in ("org/procedures", "md/procedures", "md/sequences"):
        (root / tree).mkdir(parents=True)
    return root


def serve(case: unittest.TestCase, **options: Any) -> IdApp:
    """Serve an ID endpoint until ``case`` cleans up."""
    server = IdApp(**options)
    case.addCleanup(server.stop)
    return server


def environment(case: unittest.TestCase, **variables: str) -> None:
    """Make ``os.environ`` hold ``variables`` and none of the three
    variables ``take_id`` reads, until ``case`` cleans up."""
    patch = unittest.mock.patch.dict(os.environ)
    patch.start()
    case.addCleanup(patch.stop)
    for name in ("ORGSYNDB_TOKEN", "ORGSYNDB_REGISTRY", "XDG_CONFIG_HOME"):
        os.environ.pop(name, None)
    os.environ.update(variables)
    home = Path(tempfile.mkdtemp(prefix="orgsyndb home "))
    case.addCleanup(shutil.rmtree, home, True)
    os.environ["HOME"] = str(home)


def write_token_file(directory: Path, text: str) -> Path:
    """Write ``text`` as ``orgsyndb/token`` under ``directory``."""
    path = directory / "orgsyndb" / "token"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


class TakeIdTests(unittest.TestCase):
    """``pipeline.take_id`` (build-script "new subcommand")."""

    def setUp(self) -> None:
        environment(self, ORGSYNDB_TOKEN=TOKEN)
        self.server = serve(self)
        self.root = make_root(self, self.server.url)

    def take(self, kind: str = "procedure", root: Path | None = None
             ) -> Any:
        return pipeline_function("take_id")(root or self.root, kind)

    def error(self) -> Any:
        return pipeline().validate.ConfigError

    def test_the_application_issues_the_id(self) -> None:
        """Requirement: new subcommand (`take_id` posts the kind to the
        application)."""
        self.assertEqual(self.take(), "OSDB-0042")
        (request,) = self.server.requests
        self.assertEqual(request.body, {"kind": "procedure"})
        self.assertEqual(request.headers["authorization"],
                         f"Bearer {TOKEN}")

    def test_a_sequence_is_asked_for_by_its_kind(self) -> None:
        """Requirement: new subcommand (the kind `procedure` or
        `sequence`)."""
        self.server.payload = {"id": "SEQ-0007"}
        self.assertEqual(self.take("sequence"), "SEQ-0007")
        self.assertEqual(self.server.requests[0].body,
                         {"kind": "sequence"})

    def test_the_origin_is_the_address_without_its_path(self) -> None:
        """Requirement: new subcommand (`<origin>` being the address's
        scheme, host and port)."""
        root = make_root(self, f"{self.server.origin}/elsewhere/x.json?a=1")
        self.assertEqual(self.take(root=root), "OSDB-0042")
        self.assertEqual(len(self.server.requests), 1)

    def test_the_environment_token_wins_over_the_file(self) -> None:
        """Requirement: new subcommand (the token is `ORGSYNDB_TOKEN`
        when it is set and not empty, else the first line of the
        file)."""
        write_token_file(Path(os.environ["HOME"]) / ".config",
                         "from-the-file\n")
        self.take()
        self.assertEqual(self.server.requests[0].headers["authorization"],
                         f"Bearer {TOKEN}")

    def test_an_empty_token_falls_back_to_the_file(self) -> None:
        """Requirement: new subcommand (set and not empty)."""
        os.environ["ORGSYNDB_TOKEN"] = ""
        write_token_file(Path(os.environ["HOME"]) / ".config",
                         "from-the-file\nsecond line\n")
        self.take()
        self.assertEqual(self.server.requests[0].headers["authorization"],
                         "Bearer from-the-file")

    def test_the_file_is_under_xdg_config_home(self) -> None:
        """Requirement: new subcommand (`$XDG_CONFIG_HOME/orgsyndb/
        token`)."""
        del os.environ["ORGSYNDB_TOKEN"]
        elsewhere = Path(os.environ["HOME"]) / "elsewhere"
        write_token_file(elsewhere, "from-xdg\n")
        write_token_file(Path(os.environ["HOME"]) / ".config",
                         "from-home\n")
        os.environ["XDG_CONFIG_HOME"] = str(elsewhere)
        self.take()
        self.assertEqual(self.server.requests[0].headers["authorization"],
                         "Bearer from-xdg")

    def test_an_empty_xdg_config_home_means_the_default(self) -> None:
        """Requirement: new subcommand (`XDG_CONFIG_HOME` being
        `~/.config` when unset or empty)."""
        del os.environ["ORGSYNDB_TOKEN"]
        write_token_file(Path(os.environ["HOME"]) / ".config",
                         "from-home\n")
        os.environ["XDG_CONFIG_HOME"] = ""
        self.take()
        self.assertEqual(self.server.requests[0].headers["authorization"],
                         "Bearer from-home")

    def test_no_token(self) -> None:
        """Scenario: No token (`take_id` fails with a message naming
        both)."""
        del os.environ["ORGSYNDB_TOKEN"]
        with self.assertRaises(self.error()) as caught:
            self.take()
        self.assertIn("ORGSYNDB_TOKEN", str(caught.exception))
        self.assertIn("~/.config/orgsyndb/token", str(caught.exception))
        self.assertEqual(self.server.requests, [])

    def test_an_answer_of_409(self) -> None:
        """Scenario: Refused by the application."""
        self.server.status = 409
        self.server.payload = {"error": "no import yet"}
        with self.assertRaises(self.error()) as caught:
            self.take()
        message = str(caught.exception)
        for text in (self.server.origin, "409", "no import yet"):
            self.assertIn(text, message)

    def test_an_answer_without_an_error_names_the_status(self) -> None:
        """Requirement: new subcommand (the answer's `error` when it has
        one)."""
        self.server.status = 500
        self.server.payload = "<html>broken</html>"
        with self.assertRaises(self.error()) as caught:
            self.take()
        self.assertIn("500", str(caught.exception))
        self.assertIn(self.server.origin, str(caught.exception))

    def test_only_a_201_with_an_id_of_the_kind_is_taken(self) -> None:
        """Requirement: new subcommand (an answer other than 201 with an
        `id` of the kind fails)."""
        answers: dict[str, tuple[int, Any, str]] = {
            "a 200": (200, {"id": "OSDB-0042"}, "procedure"),
            "a 202": (202, {"id": "OSDB-0042"}, "procedure"),
            "a sequence ID for a procedure": (
                201, {"id": "SEQ-0003"}, "procedure"),
            "a procedure ID for a sequence": (
                201, {"id": "OSDB-0003"}, "sequence"),
            "no id": (201, {}, "procedure"),
            "an id that is no ID": (201, {"id": "OSDB-12"}, "procedure"),
            "an id that is a number": (201, {"id": 42}, "procedure"),
            "text that is no JSON": (201, "created", "procedure"),
            "a list": (201, '["OSDB-0042"]', "procedure"),
        }
        for name, (status, payload, kind) in answers.items():
            with self.subTest(name=name):
                self.server.status = status
                self.server.payload = payload
                with self.assertRaises(self.error()) as caught:
                    self.take(kind)
                self.assertIn(self.server.origin, str(caught.exception))

    def test_an_address_nobody_answers(self) -> None:
        """Requirement: new subcommand (a failing request fails
        `take_id`, naming the address)."""
        address = closed_address()
        root = make_root(self, address)
        with self.assertRaises(self.error()) as caught:
            self.take(root=root)
        self.assertIn(address.split("/lab/")[0], str(caught.exception))

    def test_a_path_is_taken_from_the_clone(self) -> None:
        """Requirement: new subcommand (when the collection's `registry`
        is a path, `ID` is `next_id` of the candidate names)."""
        root = make_root(self, "registry.json")
        (root / "md" / "procedures" / "OSDB-0003-a.md").write_text("x\n")
        (root / "md" / "sequences" / "SEQ-0005-b.md").write_text("x\n")
        (root / "org" / "procedures" / "OSDB-0007-c.org").write_text("x\n")
        got, _out, _err = captured(self.take, "procedure", root)
        self.assertEqual(got, "OSDB-0008")
        got, _out, _err = captured(self.take, "sequence", root)
        self.assertEqual(got, "SEQ-0006")
        self.assertEqual(self.server.requests, [])

    def test_no_registry_named_is_taken_from_the_clone(self) -> None:
        """Requirement: new subcommand (when the collection's `registry`
        is a path or is not named)."""
        root = make_root(self, None)
        got, _out, _err = captured(self.take, "sequence", root)
        self.assertEqual(got, "SEQ-0001")
        self.assertEqual(self.server.requests, [])

    def test_the_environment_registry_does_not_decide(self) -> None:
        """Requirement: new subcommand (whatever `ORGSYNDB_REGISTRY`
        holds)."""
        root = make_root(self, "registry.json")
        os.environ["ORGSYNDB_REGISTRY"] = self.server.url
        got, _out, _err = captured(self.take, "procedure", root)
        self.assertEqual(got, "OSDB-0001")
        self.assertEqual(self.server.requests, [])
        os.environ["ORGSYNDB_REGISTRY"] = str(FIXTURE_REGISTRY)
        self.assertEqual(self.take(), "OSDB-0042")


class NewProgramTests(unittest.TestCase):
    """``tools/orgsyndb new`` with the application's address."""

    def setUp(self) -> None:
        self.server = serve(self)
        self.sandbox = make_sandbox(self)
        name_registry(self.sandbox.root, self.server.url)
        self.before = snapshot(self.sandbox.root)

    def new(self, *args: str, token: str | None = TOKEN,
            **variables: str) -> Run:
        env = self.sandbox.env()
        env.pop("ORGSYNDB_TOKEN", None)
        env.update(variables)
        if token is not None:
            env["ORGSYNDB_TOKEN"] = token
        return self.sandbox.build("new", *args, env=env)

    def nothing_created(self) -> None:
        self.assertEqual(snapshot(self.sandbox.root), self.before)

    def test_an_id_from_the_application(self) -> None:
        """Scenario: An ID from the application."""
        result = self.new("--md", "Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/procedures/OSDB-0042-test-product.md\n")
        stub = (self.sandbox.root / "md" / "procedures"
                / "OSDB-0042-test-product.md")
        self.assertEqual(front_matter(stub.read_text(encoding="utf-8"))[
            "id"], "OSDB-0042")
        (request,) = self.server.requests
        self.assertEqual(request.body, {"kind": "procedure"})
        self.assertEqual(request.headers["authorization"],
                         f"Bearer {TOKEN}")

    def test_an_org_stub_takes_the_issued_id_too(self) -> None:
        """Requirement: new subcommand (`ID` is `take_id`, the kind
        `procedure`)."""
        result = self.new("Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "org/procedures/OSDB-0042-test-product.org\n")
        text = (self.sandbox.root / "org" / "procedures"
                / "OSDB-0042-test-product.org").read_text(encoding="utf-8")
        self.assertIn("#+HUGO_SLUG: osdb-0042", text)
        self.assertNotIn("OSDB-0000", text)

    def test_a_german_stub_takes_the_issued_id_too(self) -> None:
        """Requirement: new subcommand (`ID` is `take_id`)."""
        result = self.new("--lang", "de", "Prüfprodukt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "org/procedures/OSDB-0042-pruefprodukt.de.org\n")

    def test_a_sequence_from_the_application(self) -> None:
        """Requirement: new subcommand (`--sequence` makes a sequence
        stub the same way)."""
        self.server.payload = {"id": "SEQ-0042"}
        result = self.new("--sequence", "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0042-aspirin-route.md\n")
        data = front_matter((self.sandbox.root / "md" / "sequences"
                             / "SEQ-0042-aspirin-route.md").read_text(
                                 encoding="utf-8"))
        self.assertEqual((data["id"], data["slug"], data["title"]),
                         ("SEQ-0042", "seq-0042", "Aspirin route"))
        (request,) = self.server.requests
        self.assertEqual(request.body, {"kind": "sequence"})

    def test_no_token(self) -> None:
        """Scenario: No token."""
        result = self.new("--md", "Test product", token=None)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn("ORGSYNDB_TOKEN", result.stderr)
        self.assertIn("~/.config/orgsyndb/token", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.server.requests, [])
        self.nothing_created()

    def test_the_token_file(self) -> None:
        """Requirement: new subcommand (else the first line of
        `~/.config/orgsyndb/token`)."""
        write_token_file(self.sandbox.home / ".config", "from-the-file\n")
        result = self.new("--md", "Test product", token=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0].headers["authorization"],
                         "Bearer from-the-file")

    def test_refused_by_the_application(self) -> None:
        """Scenario: Refused by the application."""
        self.server.status = 409
        self.server.payload = {"error": "no import yet"}
        result = self.new("--md", "Test product")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn("409", result.stderr)
        self.assertIn("no import yet", result.stderr)
        self.assertEqual(result.stdout, "")
        self.nothing_created()

    def test_an_application_that_does_not_answer(self) -> None:
        """Requirement: new subcommand (when no ID can be had, it
        creates nothing and exits 1)."""
        name_registry(self.sandbox.root, closed_address())
        self.before = snapshot(self.sandbox.root)
        result = self.new("--md", "Test product")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.nothing_created()

    def test_the_registry_setting_decides(self) -> None:
        """Scenario: The registry setting decides."""
        result = self.new("--md", "Test product",
                          ORGSYNDB_REGISTRY=str(FIXTURE_REGISTRY))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/procedures/OSDB-0042-test-product.md\n")
        self.assertEqual(len(self.server.requests), 1)

    def test_a_bad_title_is_refused_before_an_id_is_taken(self) -> None:
        """Requirement: new subcommand (`new_procedure` and
        `new_sequence` check the title; a bad value exits 2)."""
        made = self.new("--md", "Test product")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.before = snapshot(self.sandbox.root)
        for args in (["--md", ""], ["--md", "  "], ["--md", "αβγ"],
                     ["--sequence", ""], ["--sequence", "αβγ"]):
            with self.subTest(args=args):
                result = self.new(*args)
                self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.nothing_created()

    def test_a_bad_language_is_refused_before_an_id_is_taken(self) -> None:
        """Requirement: new subcommand (`new_procedure` checks the
        `--lang` value)."""
        made = self.new("--lang", "de", "Test product")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.before = snapshot(self.sandbox.root)
        result = self.new("--lang", "fr", "Test product")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.nothing_created()


class RegistryFileTests(unittest.TestCase):
    """``tools/orgsyndb new`` in a collection whose registry is a file,
    with an application that would answer."""

    def setUp(self) -> None:
        self.server = serve(self)
        self.sandbox = make_sandbox(self)
        self.before = snapshot(self.sandbox.root)

    def new(self, *args: str, **variables: str) -> Run:
        env = self.sandbox.env()
        env.pop("ORGSYNDB_TOKEN", None)
        env.update(variables)
        return self.sandbox.build("new", *args, env=env)

    def test_a_registry_file_takes_the_next_free_id(self) -> None:
        """Requirement: new subcommand (when the collection's `registry`
        is a path, `ID` is `next_id` of the candidate names)."""
        result = self.new("--md", "Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/procedures/OSDB-0010-test-product.md\n")

    def test_the_address_in_the_environment_does_not_decide(self) -> None:
        """Requirement: new subcommand (whatever `ORGSYNDB_REGISTRY`
        holds)."""
        result = self.new("--md", "Test product",
                          ORGSYNDB_REGISTRY=self.server.url,
                          ORGSYNDB_TOKEN=TOKEN)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/procedures/OSDB-0010-test-product.md\n")
        self.assertEqual(self.server.requests, [])

    def test_a_sequence_stub_from_the_clone(self) -> None:
        """Requirement: new subcommand (sequences get IDs the same way,
        from `md/sequences/` when local)."""
        result = self.new("--sequence", "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0003-aspirin-route.md\n")
        data = front_matter((self.sandbox.root / "md" / "sequences"
                             / "SEQ-0003-aspirin-route.md").read_text(
                                 encoding="utf-8"))
        self.assertEqual((data["id"], data["slug"], data["title"]),
                         ("SEQ-0003", "seq-0003", "Aspirin route"))
        self.assertNotIn("ai_model", data)

    def test_a_sequence_with_the_markdown_option(self) -> None:
        """Scenario: A sequence stub (`new --sequence --md` exits 2 and
        creates nothing)."""
        made = self.new("--sequence", "Aspirin route")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.before = snapshot(self.sandbox.root)
        result = self.new("--sequence", "--md", "Another route")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("usage", result.stderr.lower())
        self.assertEqual(snapshot(self.sandbox.root), self.before)

    def test_a_sequence_with_a_language(self) -> None:
        """Requirement: new subcommand (`--sequence` with `--lang` is a
        usage error)."""
        made = self.new("--sequence", "Aspirin route")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.before = snapshot(self.sandbox.root)
        result = self.new("--sequence", "--lang", "de", "Another route")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("usage", result.stderr.lower())
        self.assertEqual(snapshot(self.sandbox.root), self.before)

    def test_the_title_of_a_sequence_is_the_joined_words(self) -> None:
        """Requirement: new subcommand (the title is the words of
        `TITLE...` joined by single spaces and trimmed)."""
        result = self.new("--sequence", "Aspirin", "  route ")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0003-aspirin-route.md\n")


class NewSequenceTests(unittest.TestCase):
    """``pipeline.new_sequence`` on temporary collections."""

    def setUp(self) -> None:
        environment(self)

    def make(self, registry: str | None = "registry.json") -> Path:
        return make_root(self, registry)

    def new(self, root: Path, *words: str) -> Run:
        function = pipeline_function("new_sequence")
        try:
            relative, _, err = captured(
                function, root, words, dt.datetime.fromisoformat(NOW))
        except pipeline().UsageError as exc:
            return Run(2, "", str(exc))
        return Run(0, Path(relative).as_posix() + "\n", err)

    def test_a_sequence_stub(self) -> None:
        """Scenario: A sequence stub."""
        root = self.make()
        sequences = root / "md" / "sequences"
        (sequences / "SEQ-0002-a.md").write_text("x\n")
        (sequences / "SEQ-0004-old.md").write_text("x\n")
        git = ["git", "-c", "user.name=Test Author", "-c",
               "user.email=author@example.invalid", "-c",
               "commit.gpgsign=false", "-c", "init.defaultBranch=main",
               "-C", str(root)]
        for step in (["init", "-q"], ["add", "-A"],
                     ["commit", "-q", "-m", "add"]):
            subprocess.run([*git, *step], check=True, capture_output=True)
        (sequences / "SEQ-0004-old.md").unlink()
        for step in (["add", "-A"], ["commit", "-q", "-m", "delete"]):
            subprocess.run([*git, *step], check=True, capture_output=True)
        result = self.new(root, "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0005-aspirin-route.md\n")
        data = front_matter((sequences / "SEQ-0005-aspirin-route.md"
                             ).read_text(encoding="utf-8"))
        moment = dt.datetime.fromisoformat(NOW)
        self.assertEqual(
            (data["id"], data["slug"], data["title"], data["date"],
             data["lastmod"]),
            ("SEQ-0005", "seq-0005", "Aspirin route", moment, moment))
        self.assertNotIn("ai_model", data)

    def test_the_first_sequence(self) -> None:
        """Requirement: new subcommand (`SEQ-0001` when none is
        taken)."""
        root = self.make()
        shutil.rmtree(root / "md" / "sequences")
        result = self.new(root, "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0001-aspirin-route.md\n")

    def test_a_title_with_quotes(self) -> None:
        """Requirement: new subcommand (the `title` line takes the
        title as in a Markdown procedure stub)."""
        root = self.make()
        result = self.new(root, 'Bob\'s "best" route')
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "md" / "sequences" / "SEQ-0001-bob-s-best-route.md"
        self.assertEqual(front_matter(stub.read_text(encoding="utf-8"))[
            "title"], 'Bob\'s "best" route')

    def test_the_title_is_checked(self) -> None:
        """Requirement: new subcommand (a bad title raises
        `UsageError`)."""
        root = self.make()
        for words in ((), ("",), ("  ",), ("two\nlines",), ("αβγ",)):
            with self.subTest(words=words):
                self.assertEqual(self.new(root, *words).returncode, 2)
        self.assertEqual(list((root / "md" / "sequences").iterdir()), [])

    def test_procedure_files_do_not_count(self) -> None:
        """Requirement: new subcommand (the candidate names of a
        sequence are those of `md/sequences/`)."""
        root = self.make()
        (root / "md" / "procedures" / "SEQ-0009-stray.md").write_text("x\n")
        (root / "md" / "procedures" / "OSDB-0007-a.md").write_text("x\n")
        result = self.new(root, "Aspirin route")
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0001-aspirin-route.md\n")

    def test_sequence_files_do_not_count_for_a_procedure(self) -> None:
        """Requirement: new subcommand (the candidate names of a
        procedure are those of its trees)."""
        root = self.make()
        (root / "md" / "sequences" / "SEQ-0009-a.md").write_text("x\n")
        module = pipeline()
        relative, _out, _err = captured(
            module.new_procedure, root, ["Test product"], True,
            dt.datetime.fromisoformat(NOW), None)
        self.assertEqual(Path(relative).as_posix(),
                         "md/procedures/OSDB-0001-test-product.md")

    def test_a_shallow_clone_warns(self) -> None:
        """Requirement: new subcommand (a shallow clone still scans the
        history it has, and warns with `shallow`)."""
        origin = self.make()
        git = ["git", "-c", "user.name=Test Author", "-c",
               "user.email=author@example.invalid", "-c",
               "commit.gpgsign=false", "-c", "init.defaultBranch=main"]
        (origin / "md" / "sequences" / "SEQ-0002-a.md").write_text("x\n")
        for step in (["init", "-q"], ["add", "-A"],
                     ["commit", "-q", "-m", "one"],
                     ["commit", "-q", "--allow-empty", "-m", "two"]):
            subprocess.run([*git, "-C", str(origin), *step], check=True,
                           capture_output=True)
        clone = origin.parent / "shallow clone"
        subprocess.run([*git, "clone", "-q", "--depth", "1",
                        origin.as_uri(), str(clone)], check=True,
                       capture_output=True)
        result = self.new(clone, "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0003-aspirin-route.md\n")
        self.assertIn("shallow", result.stderr)

    def test_an_address_asks_the_application(self) -> None:
        """Requirement: new subcommand (`ID` is `take_id`, the kind
        `sequence`)."""
        os.environ["ORGSYNDB_TOKEN"] = TOKEN
        server = serve(self, payload={"id": "SEQ-0042"})
        root = self.make(server.url)
        result = self.new(root, "Aspirin route")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "md/sequences/SEQ-0042-aspirin-route.md\n")
        (request,) = server.requests
        self.assertEqual(request.body, {"kind": "sequence"})

    def test_no_id_can_be_had(self) -> None:
        """Requirement: new subcommand (`validate.ConfigError`, nothing
        created)."""
        server = serve(self)
        root = self.make(server.url)
        with self.assertRaises(pipeline().validate.ConfigError):
            captured(pipeline_function("new_sequence"), root,
                     ["Aspirin route"], dt.datetime.fromisoformat(NOW))
        self.assertEqual(list((root / "md" / "sequences").iterdir()), [])


class NewProcedureWithAnAddressTests(unittest.TestCase):
    """``pipeline.new_procedure`` takes its ID from ``take_id``."""

    def test_an_address_asks_the_application(self) -> None:
        """Requirement: new subcommand (`ID` is `take_id`, the kind
        `procedure`)."""
        environment(self, ORGSYNDB_TOKEN=TOKEN)
        server = serve(self, payload={"id": "OSDB-0123"})
        root = make_root(self, server.url)
        relative, _out, _err = captured(
            pipeline().new_procedure, root, ["Test product"], True,
            dt.datetime.fromisoformat(NOW), None)
        self.assertEqual(Path(relative).as_posix(),
                         "md/procedures/OSDB-0123-test-product.md")
        self.assertEqual(server.requests[0].body, {"kind": "procedure"})

    def test_no_id_can_be_had(self) -> None:
        """Requirement: new subcommand (`validate.ConfigError`, nothing
        created)."""
        environment(self)
        server = serve(self)
        root = make_root(self, server.url)
        with self.assertRaises(pipeline().validate.ConfigError):
            captured(pipeline().new_procedure, root, ["Test product"],
                     True, dt.datetime.fromisoformat(NOW), None)
        self.assertEqual(list((root / "md" / "procedures").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
