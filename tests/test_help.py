"""Help pages without a build (site-help): slugs, the staged text of a
document with its front matter and rewritten links, and the staging of a
docs directory."""

import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline_support import body_of, front_matter, pipeline_function

MARKDOWN = """\
# Writing things

See [B](B.de.md#x-y) and the [glossary](GLOSSARY.de.md).
Start from [template](../templates/p.md), not [web](https://example.org/a.md).
Back to [top](#z) or [root](/help/); code `[c](B.de.md)` stays.

```
[d](B.de.md)
```
"""

ORG = """\
#+title: Glossar
#+AI_MODEL: m

Read [[file:S.md][the schema]] or [[file:S.md]].
Copy [[file:../templates/p.org][the template]] and [[file:../x.org]].
Online: [[https://example.org][web]]; literal =[[file:S.md]]= stays.

#+BEGIN_SRC org
[[file:S.md]]
#+END_SRC
"""


def stage(docs: Path, target: Path) -> int:
    return pipeline_function("stage_help")(docs, target)


class HelpSlugTests(unittest.TestCase):
    def test_slugs(self) -> None:
        """Scenario: Slugs."""
        slug = pipeline_function("help_slug")
        for name, expected in [("AUTHORING.md", "authoring"),
                               ("AUTHORING.de.md", "authoring-de"),
                               ("AUTHORING-ORG.de.org", "authoring-org-de"),
                               ("GLOSSARY.de.md", "glossary-de")]:
            with self.subTest(name=name):
                self.assertEqual(slug(name), expected)


class HelpPageTests(unittest.TestCase):
    def test_markdown_page(self) -> None:
        """Scenario: Markdown page."""
        text = pipeline_function("help_page")(
            "A.md", MARKDOWN, {"A.md", "B.de.md", "GLOSSARY.de.md"})
        self.assertEqual(front_matter(text), {
            "title": "Writing things", "help_group": "guides",
            "help_base": "a", "help_language": "en"})
        body = body_of(text)
        self.assertNotIn("# Writing things", body)
        self.assertIn("[B](/help/b-de/#x-y)", body)
        self.assertIn("[glossary](/help/glossary-de/)", body)
        self.assertIn("Start from template, not "
                      "[web](https://example.org/a.md).", body)
        self.assertIn("Back to [top](#z) or [root](/help/); "
                      "code `[c](B.de.md)` stays.", body)
        self.assertIn("```\n[d](B.de.md)\n```\n", body)

    def test_org_page(self) -> None:
        """Scenario: Org page."""
        text = pipeline_function("help_page")(
            "GLOSSARY.de.org", ORG, {"GLOSSARY.de.org", "S.md"})
        self.assertEqual(front_matter(text), {
            "title": "Glossar", "help_group": "glossaries",
            "help_base": "glossary", "help_language": "de"})
        body = body_of(text)
        self.assertNotIn("#+title:", body)
        self.assertIn("#+AI_MODEL: m\n", body)
        self.assertIn("Read [[/help/s/][the schema]] or "
                      "[[/help/s/][S.md]].", body)
        self.assertIn("Copy the template and ../x.org.", body)
        self.assertIn("Online: [[https://example.org][web]]; literal "
                      "=[[file:S.md]]= stays.", body)
        self.assertIn("#+BEGIN_SRC org\n[[file:S.md]]\n#+END_SRC\n", body)

    def test_a_document_without_a_title_is_refused(self) -> None:
        """Scenario: Staging errors (help_page)."""
        page = pipeline_function("help_page")
        for name, text in [("A.md", "Intro\n\n# Late title\n"),
                           ("A.org", "* Heading\n#+TITLE: Late\n")]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    page(name, text, {name})


class StageHelpTests(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="orgsyndb help "))
        self.addCleanup(shutil.rmtree, base)
        self.docs = base / "docs"
        self.docs.mkdir()
        self.target = base / "build" / "content" / "help"
        self.target.mkdir(parents=True)
        (self.target / "stale.md").write_text("old\n", encoding="utf-8")

    def write(self, name: str, text: str) -> None:
        path = self.docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_staging_a_docs_directory(self) -> None:
        """Scenario: Staging a docs directory."""
        self.write("A.md", "﻿# A\n\nText.\n")
        self.write("B.de.org", "#+TITLE: B\n\nText.\n")
        self.write("notes.txt", "not a document\n")
        self.write("sub/C.md", "# C\n")
        self.assertEqual(stage(self.docs, self.target), 2)
        self.assertEqual(sorted(p.name for p in self.target.iterdir()),
                         ["a.md", "b-de.org"])
        staged = (self.target / "a.md").read_text(encoding="utf-8")
        self.assertEqual(front_matter(staged)["title"], "A")

    def test_staging_errors(self) -> None:
        """Scenario: Staging errors."""
        cases = [({"A.md": "# A\n", "a.md": "# a\n"}, ["A.md", "a.md"]),
                 ({"A.fr.md": "# A\n"}, ["A.fr.md", "fr"]),
                 ({"A.md": "Intro\n"}, ["A.md"])]
        for files, named in cases:
            with self.subTest(files=sorted(files)):
                for path in self.docs.iterdir():
                    path.unlink()
                for name, text in files.items():
                    self.write(name, text)
                if len(list(self.docs.iterdir())) != len(files):
                    self.skipTest("the file system folds case")
                with self.assertRaises(ValueError) as caught:
                    stage(self.docs, self.target)
                for word in named:
                    self.assertIn(word, str(caught.exception))
                self.assertTrue((self.target / "stale.md").is_file())

    def test_no_docs_directory(self) -> None:
        """Scenario: No docs directory."""
        self.assertEqual(stage(self.docs / "absent", self.target), 0)
        self.assertTrue(self.target.is_dir())
        self.assertEqual(list(self.target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
