"""Authoring templates (procedure-schema, "Markdown template" and
"Org template")."""

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from support import (COMPOUND_TEMPLATE, REPO, ValidatorTestCase,
                     run_validator, template_registry)

MD_TEMPLATE = REPO / "templates" / "procedure.md"
ORG_TEMPLATE = REPO / "templates" / "procedure.org"
CANON = ["Summary", "Reagents", "Procedure", "Workup and Purification",
         "Characterization", "Notes", "Hazards and Waste Disposal",
         "References"]


def read_template(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO)} does not exist")
    return path.read_text(encoding="utf-8")


def substituted(text: str) -> str:
    """Fill the placeholders as ``orgsyndb new`` will."""
    return text.replace("OSDB-0000", "OSDB-0001").replace(
        "osdb-0000", "osdb-0001")


class MarkdownTemplateTests(ValidatorTestCase):
    def test_substituted_markdown_template_is_clean(self) -> None:
        """Scenario: Substituted Markdown template is clean."""
        text = substituted(read_template(MD_TEMPLATE))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            root.mkdir()
            (root / "OSDB-0001-template.md").write_text(
                text, encoding="utf-8")
            with template_registry() as registry:
                result = run_validator(["--compounds", registry, root],
                                       cwd=Path(tmp))
        self.assert_clean(result)

    def test_template_names_the_example_compound(self) -> None:
        """Requirement: Markdown template (products and substrates)."""
        text = read_template(MD_TEMPLATE)
        front = tomllib.loads(text.split("+++\n")[1])
        self.assertEqual([e["compound"] for e in front["products"]],
                         ["example-compound"])
        self.assertEqual(set(front) & {"product", "yield_percent",
                                       "precursors", "structure_image"},
                         set())
        self.assertRegex(text, r'(?m)^#\s*substrates\s*=\s*\[[^\]]*'
                         r'"example-compound"')


class OrgTemplateTests(ValidatorTestCase):
    def test_org_template_carries_the_schema_keywords_and_sections(
            self) -> None:
        """Scenario: Org template carries the schema keywords and
        sections."""
        text = read_template(ORG_TEMPLATE)
        lines = text.splitlines()
        self.assertIn("#+HUGO_SLUG: osdb-0000", lines)
        self.assertTrue(any(ln.startswith("#+HUGO_TAGS:") for ln in lines))
        custom = "\n".join(
            ln for ln in lines
            if ln.upper().startswith("#+HUGO_CUSTOM_FRONT_MATTER:"))
        for key in ["id", "authors", "status", "reaction_types", "scale",
                    "hazards", "products"]:
            self.assertIn(f":{key}", custom)
        for old in ["product ", "yield_percent", "precursors",
                    "structure_image"]:
            self.assertNotIn(f":{old}", custom)
        self.assertIn("OSDB-0000", custom)
        self.assertIn('(compound . "example-compound")', custom)
        self.assertRegex(text, r'(?m)^# #\+HUGO_CUSTOM_FRONT_MATTER: '
                         r""":substrates '\("example-compound"\)""")
        custom_lines = custom.splitlines()
        self.assertEqual(
            re.findall(r":([A-Za-z_]+)", custom_lines[-1]), ["products"],
            "products must be alone on the last custom front matter line")
        self.assertFalse(
            any(":products" in ln for ln in custom_lines[:-1]))
        headings = [ln[2:].strip() for ln in lines if ln.startswith("* ")]
        positions = [headings.index(h) for h in CANON if h in headings]
        self.assertEqual(len(positions), len(CANON), headings)
        self.assertEqual(positions, sorted(positions))
        for prefix in ["#+DATE:", "#+HUGO_LASTMOD:",
                       "#+HUGO_AUTO_SET_LASTMOD:", "#+HUGO_DRAFT:",
                       "#+HUGO_BASE_DIR:", "#+HUGO_SECTION:"]:
            self.assertFalse(
                any(ln.upper().startswith(prefix) for ln in lines), prefix)


class CompoundTemplateTests(ValidatorTestCase):
    REQUIRED = ["name", "formula", "mw", "smiles"]
    OPTIONAL = ["name_de", "cas", "structure_image"]

    def test_template_validates_as_a_registry_file(self) -> None:
        """Scenario: Template validates."""
        read_template(COMPOUND_TEMPLATE)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            root.mkdir()
            with template_registry() as registry:
                result = run_validator(["--compounds", registry, root],
                                       cwd=Path(tmp))
        self.assert_clean(result)

    def test_template_explains_every_key_and_sets_the_required_ones(
            self) -> None:
        """Requirement: Compound template."""
        lines = read_template(COMPOUND_TEMPLATE).splitlines()
        comments = [ln for ln in lines if ln.startswith("#")]
        for key in self.REQUIRED:
            with self.subTest(key=key):
                self.assertTrue(any(re.match(rf"{key}\s*=", ln)
                                    for ln in lines), "not set")
                self.assertTrue(any(re.search(rf"\b{key}\b", ln)
                                    for ln in comments), "not explained")
        for key in self.OPTIONAL:
            with self.subTest(key=key):
                self.assertFalse(any(re.match(rf"{key}\s*=", ln)
                                     for ln in lines), "is set")
                self.assertTrue(any(re.match(rf"#\s*{key}\s*=", ln)
                                    for ln in comments),
                                "not shown commented out")
                self.assertTrue(any(re.search(rf"\b{key}\b", ln)
                                    for ln in comments))


if __name__ == "__main__":
    unittest.main()
