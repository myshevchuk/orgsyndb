"""Static tests of what lab.css prints of widgets (web-app: Widgets,
printing a page from a browser)."""

import re

from django.test import SimpleTestCase

from . import REPO

CSS = REPO / "webapp" / "orgsyndb_web" / "static" / "lab.css"


def balanced(text: str, start: int) -> tuple[str, int]:
    """The text inside the braces that open at or after ``start``, and
    the index after the closing brace."""
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    raise AssertionError("unbalanced braces in lab.css")


def print_blocks(text: str) -> list[str]:
    """The contents of the stylesheet's ``@media print`` blocks."""
    blocks, position = [], 0
    for found in re.finditer(r"@media\s+print\s*\{", text):
        if found.start() < position:
            continue
        body, position = balanced(text, found.start())
        blocks.append(body)
    return blocks


def rules(block: str) -> list[tuple[list[str], dict[str, str]]]:
    """The style rules directly in ``block``, each as its selectors,
    with white space made single and the space around ``>`` kept
    single, and its declarations."""
    found, position = [], 0
    block = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
    while "{" in block[position:]:
        opening = block.index("{", position)
        selector = block[position:opening].strip()
        body, position = balanced(block, opening)
        if selector.startswith("@"):
            continue
        names = [re.sub(r"\s*>\s*", " > ", " ".join(one.split()))
                 for one in selector.split(",")]
        declarations = {}
        for declaration in body.split(";"):
            if ":" in declaration:
                name, value = declaration.split(":", 1)
                declarations[name.strip()] = " ".join(value.split())
        found.append((names, declarations))
    return found


class PrintRuleTests(SimpleTestCase):

    def printed(self) -> list[tuple[list[str], dict[str, str]]]:
        blocks = print_blocks(CSS.read_text(encoding="utf-8"))
        self.assertTrue(blocks, "lab.css has no @media print block")
        return [rule for block in blocks for rule in rules(block)]

    def declarations(self, selector: str) -> list[dict[str, str]]:
        return [declared for names, declared in self.printed()
                if selector in names]

    def test_a_closed_widget_prints_its_content(self) -> None:
        found = self.declarations("details.widget::details-content")
        self.assertTrue(found, "the print block has no rule for "
                        "details.widget::details-content")
        self.assertTrue(any(d.get("content-visibility") == "visible"
                            for d in found), found)

    def test_the_sort_buttons_print_so_that_the_headers_do(self) -> None:
        """print.css hides every button; the headers' buttons come back."""
        found = self.declarations("th > button.sort-header")
        self.assertTrue(found, "the print block has no rule for "
                        "th > button.sort-header")
        shown = [d for d in found if d.get("display", "none") != "none"]
        self.assertTrue(shown, f"no rule shows the buttons: {found}")
