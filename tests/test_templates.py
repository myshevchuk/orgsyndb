"""Authoring templates (procedure-schema, "Markdown template" and
"Org template")."""

import re
import tempfile
import unittest
from pathlib import Path

from support import REPO, ValidatorTestCase, run_validator

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
            result = run_validator([root], cwd=Path(tmp))
        self.assert_clean(result)

    def test_unsubstituted_markdown_template_is_rejected(self) -> None:
        """Scenario: Unsubstituted Markdown template is rejected."""
        text = read_template(MD_TEMPLATE)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            root.mkdir()
            (root / "OSDB-0000-template.md").write_text(
                text, encoding="utf-8")
            result = run_validator([root], cwd=Path(tmp))
        self.assertEqual(result.returncode, 1, result.stderr)
        ids = [p for p in result.problems
               if p.field == "id" and p.severity == "error"
               and "must be between OSDB-0001 and OSDB-9999" in p.message]
        self.assertEqual(len(ids), 1, result.stdout)


class OrgTemplateTests(ValidatorTestCase):
    def test_org_template_names_its_writing_model(self) -> None:
        """Scenario: Org template names its writing model."""
        text = read_template(ORG_TEMPLATE)
        match = re.search(r"^#\+AI_MODEL:[ \t]*(.*?)[ \t]*$", text,
                          re.M | re.I)
        self.assertIsNotNone(match, "no #+AI_MODEL line")
        self.assertNotEqual(match.group(1), "")
        self.assertNotEqual(match.group(1).lower(), "none")

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
        for key in ["id", "authors", "status", "reaction_types", "product",
                    "scale", "yield_percent", "hazards"]:
            self.assertIn(f":{key}", custom)
        self.assertIn("OSDB-0000", custom)
        custom_lines = custom.splitlines()
        self.assertEqual(
            re.findall(r":([A-Za-z_]+)", custom_lines[-1]), ["product"],
            "product must be alone on the last custom front matter line")
        self.assertFalse(
            any(":product" in ln for ln in custom_lines[:-1]))
        headings = [ln[2:].strip() for ln in lines if ln.startswith("* ")]
        positions = [headings.index(h) for h in CANON if h in headings]
        self.assertEqual(len(positions), len(CANON), headings)
        self.assertEqual(positions, sorted(positions))
        for prefix in ["#+DATE:", "#+HUGO_LASTMOD:",
                       "#+HUGO_AUTO_SET_LASTMOD:", "#+HUGO_DRAFT:",
                       "#+HUGO_BASE_DIR:", "#+HUGO_SECTION:"]:
            self.assertFalse(
                any(ln.upper().startswith(prefix) for ln in lines), prefix)


if __name__ == "__main__":
    unittest.main()
