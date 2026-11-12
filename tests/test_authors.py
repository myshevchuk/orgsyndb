"""Procedure authors as accounts (procedure-authors): the validator's
check of a procedure's `authors` against the registry's accounts, the
author data `pipeline.authors_data` returns, and the user names that the
authoring templates give.
"""

import json
import re
import unittest

from pipeline_support import TEST_COLLECTION, pipeline_function
from support import (REPO, ValidatorTestCase, edit_registry,
                     registry_variant_run, replace_line, variant_run)

USER_NAME = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")
TEMPLATES = ("procedure.md", "procedure.de.md", "procedure.org",
             "procedure.de.org")


def authors_line(*names: str) -> str:
    """The `authors` line of a baseline variant."""
    return "authors = [" + ", ".join(f'"{name}"' for name in names) + "]"


class AuthorsAreAccountsTests(ValidatorTestCase):
    """Requirement: Authors are accounts."""

    def test_unknown_author(self) -> None:
        """Scenario: Unknown author."""
        result = variant_run(
            "OSDB-0100-unknown-author.md",
            replace_line("authors", authors_line("a.example", "z.nobody")))
        self.assert_one(result, "error", "authors",
                        'unknown author "z.nobody"')

    def test_the_message_says_where_the_name_is_missing(self) -> None:
        """Requirement: Authors are accounts (the message names the
        registry)."""
        result = variant_run(
            "OSDB-0100-unknown-author.md",
            replace_line("authors", authors_line("z.nobody")))
        self.assert_one(
            result, "error", "authors",
            'unknown author "z.nobody"; the registry has no account of '
            "this user name")

    def test_an_author_twice(self) -> None:
        """Scenario: An author twice."""
        result = variant_run(
            "OSDB-0100-author-twice.md",
            replace_line("authors", authors_line("a.example", "a.example")))
        self.assert_one(result, "error", "authors",
                        '"a.example" is named twice')

    def test_two_accounts_are_clean(self) -> None:
        """Requirement: Authors are accounts (each account of the
        registry may be named)."""
        result = variant_run(
            "OSDB-0100-two-authors.md",
            replace_line("authors", authors_line("ae.mueller", "b.example")))
        self.assert_clean(result)

    def test_a_name_as_written_in_the_old_form_is_unknown(self) -> None:
        """Requirement: Authors are accounts (a person's name is no user
        name)."""
        result = variant_run(
            "OSDB-0100-old-author.md",
            replace_line("authors", authors_line("A. Example")))
        self.assert_one(result, "error", "authors",
                        'unknown author "A. Example"')

    def test_each_unknown_author_is_an_error(self) -> None:
        """Requirement: Authors are accounts (a name the registry lacks
        is an error under `authors`)."""
        result = variant_run(
            "OSDB-0100-unknown-authors.md",
            replace_line("authors", authors_line("y.nobody", "z.nobody")))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual({p.field for p in result.problems}, {"authors"})
        self.assertIn('unknown author "y.nobody"', result.stdout)
        self.assertIn('unknown author "z.nobody"', result.stdout)

    def test_a_registry_without_accounts_knows_no_author(self) -> None:
        """Requirement: Authors are accounts (a name the registry lacks
        is an error)."""
        result = registry_variant_run(edit_registry(
            lambda table: table.update(accounts=[])))
        self.assert_one(result, "error", "authors",
                        'unknown author "a.example"')

    def test_an_account_the_registry_lists_is_enough(self) -> None:
        """Requirement: Authors are accounts (an account named as an
        author need not be active, and the snapshot lists accounts alone
        by user name and name)."""
        def only_one(table: dict) -> None:
            table["accounts"] = [{"username": "a.example",
                                  "name": "A. Example"}]
        result = registry_variant_run(edit_registry(only_one))
        self.assert_clean(result)


class AuthorDataTests(unittest.TestCase):
    """Requirement: Author data for the site."""

    def registry(self) -> dict:
        return json.loads((TEST_COLLECTION / "registry.json").read_text(
            encoding="utf-8"))

    def data(self, registry: dict) -> dict:
        return pipeline_function("authors_data")(registry)

    def test_author_data(self) -> None:
        """Scenario: Author data."""
        registry = self.registry()
        data = self.data(registry)
        self.assertIsInstance(data, dict)
        self.assertEqual(data["a.example"], "A. Example")
        self.assertEqual(data["ae.mueller"], "Ä. Müller")
        self.assertEqual(data["klehmann"], "Katrin Lehmann")
        self.assertEqual(
            sorted(data), sorted(a["username"] for a in registry["accounts"]))
        self.assertEqual(len(data), len(registry["accounts"]))

    def test_the_data_maps_every_account_to_its_name(self) -> None:
        """Requirement: Author data for the site (a table mapping the
        user name of every account to its name)."""
        registry = self.registry()
        self.assertEqual(
            self.data(registry),
            {a["username"]: a["name"] for a in registry["accounts"]})

    def test_the_data_is_plain_json(self) -> None:
        """Requirement: Author data for the site (the build stages it as
        JSON)."""
        data = self.data(self.registry())
        self.assertEqual(json.loads(json.dumps(data)), data)

    def test_a_renamed_account_gives_its_new_name(self) -> None:
        """Requirement: Author data for the site (the name of the
        account)."""
        registry = self.registry()
        for account in registry["accounts"]:
            if account["username"] == "tbauer":
                account["name"] = "Tobias Bauer-Weiß"
        self.assertEqual(self.data(registry)["tbauer"], "Tobias Bauer-Weiß")

    def test_no_accounts(self) -> None:
        """Requirement: Author data for the site (every account of the
        registry; none gives an empty table)."""
        registry = self.registry()
        registry["accounts"] = []
        self.assertEqual(self.data(registry), {})


class TemplateAuthorsTests(unittest.TestCase):
    """Requirement: Authors are accounts (what the authoring templates
    give an author is a user name)."""

    def authors(self, name: str) -> list[str]:
        text = (REPO / "templates" / name).read_text(encoding="utf-8")
        if name.endswith(".org"):
            found = re.search(r":authors '\(([^)]*)\)", text)
        else:
            found = re.search(r"(?m)^authors = \[([^\]]*)\]", text)
        self.assertIsNotNone(found, f"{name} sets no authors")
        return re.findall(r'"([^"]*)"', found.group(1))

    def test_the_templates_name_user_names(self) -> None:
        """Requirement: Authors are accounts (a template's placeholder
        author has the form of a user name)."""
        for name in TEMPLATES:
            authors = self.authors(name)
            with self.subTest(template=name):
                self.assertTrue(authors)
                for author in authors:
                    self.assertRegex(author, USER_NAME)


if __name__ == "__main__":
    unittest.main()
