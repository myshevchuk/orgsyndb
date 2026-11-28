"""Static tests of what lab.css prints of widgets (web-app: Widgets,
printing a page from a browser)."""

import re
from pathlib import Path

from django.test import SimpleTestCase

from . import REPO

CSS = REPO / "webapp" / "orgsyndb_web" / "static" / "lab.css"
SITE_CSS = REPO / "site" / "assets" / "css" / "screen.css"


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


def screen_blocks(text: str) -> list[str]:
    """The contents of the stylesheet's ``@media screen`` blocks."""
    blocks, position = [], 0
    for found in re.finditer(r"@media\s+screen\s*\{", text):
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

    def test_main_table_text_cells_wrap_on_paper(self) -> None:
        """print-layout "Wide tables": only number cells keep one line."""
        found = self.declarations(".main-table td:not(.num):not(.number)")
        self.assertTrue(any(d.get("white-space") == "normal"
                            for d in found), found)


class ScreenOnlyLayoutTests(SimpleTestCase):
    """A layout grid for the screen leaves the print layout alone."""

    def test_the_item_grid_is_a_grid_on_the_screen_only(self) -> None:
        text = CSS.read_text(encoding="utf-8")
        for names, declarations in rules(text):
            if ".item-grid" in names:
                with self.subTest(selectors=names):
                    self.assertNotEqual(declarations.get("display"), "grid")


class SubstanceLayoutTests(SimpleTestCase):
    """The substance page's grid is for the screen, and the page's
    structure figure has no rule of its own outside its widget."""

    def test_the_substance_grid_is_a_grid_on_the_screen_only(self) -> None:
        text = CSS.read_text(encoding="utf-8")
        for names, declarations in rules(text):
            if ".substance-grid" in names:
                with self.subTest(selectors=names):
                    self.assertNotEqual(declarations.get("display"), "grid")
        shown = [declarations for block in screen_blocks(text)
                 for names, declarations in rules(block)
                 if ".substance-grid" in names]
        self.assertTrue(any(d.get("display") == "grid" for d in shown),
                        f"no @media screen rule sets .substance-grid "
                        f"to display: grid: {shown}")

    def test_no_rule_styles_a_figure_directly_in_main(self) -> None:
        text = re.sub(r"/\*.*?\*/", "",
                      CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
        self.assertIsNone(re.search(r"main\s*>\s*\.structure", text))


class OverviewLayoutTests(SimpleTestCase):
    """The overview's grid is for the screen, and the rules of the
    overview's former markup are gone."""

    def test_the_overview_grid_is_a_grid_on_the_screen_only(self) -> None:
        text = CSS.read_text(encoding="utf-8")
        for names, declarations in rules(text):
            if ".overview-grid" in names:
                with self.subTest(selectors=names):
                    self.assertNotEqual(declarations.get("display"), "grid")
        shown = [declarations for block in screen_blocks(text)
                 for names, declarations in rules(block)
                 if ".overview-grid" in names]
        self.assertTrue(any(d.get("display") == "grid" for d in shown),
                        f"no @media screen rule sets .overview-grid "
                        f"to display: grid: {shown}")

    def test_no_rule_styles_the_former_overview_markup(self) -> None:
        text = re.sub(r"/\*.*?\*/", "",
                      CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
        for name in (".overview-part", ".overview-stock", ".overview-next",
                     ".overview-months", ".lab-figures", ".overview-list",
                     ".deliveries-chart figcaption"):
            with self.subTest(selector=name):
                self.assertNotIn(name, text)


def stripped(path: Path) -> str:
    """The stylesheet at PATH without its comments."""
    return re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"),
                  flags=re.DOTALL)


class PlanningLayoutTests(SimpleTestCase):
    """The rules of the planning page's former markup are gone: its grid,
    its list widget, its inspector and its filter buttons."""

    def test_no_rule_styles_the_former_planning_markup(self) -> None:
        text = stripped(CSS)
        for name in (".lab-parameters", ".planning-cell", ".planning-grid",
                     ".planning-list", ".planning-inspector",
                     ".planning-block", ".planning-filter",
                     ".planning-select", ".planning-table",
                     ".planning-status", ".planning-no-match"):
            with self.subTest(selector=name):
                self.assertNotIn(name, text)


class TableStyleTests(SimpleTestCase):
    """Two table styles, ``main-table`` and ``aux-table`` (web-app: Main
    lists, "Table styles")."""

    REMOVED = ("inventory-table", "item-table", "task-table",
               "widget-table", "detail-table", "planning-table")

    def test_both_styles_have_their_rules(self) -> None:
        text = stripped(CSS)
        for name in (".main-table", ".aux-table"):
            with self.subTest(selector=name):
                self.assertRegex(text, rf"(?<![\w-]){re.escape(name)}\b")

    def test_the_main_table_has_a_strong_modifier_and_no_fill_one(
            self) -> None:
        text = stripped(CSS)
        self.assertRegex(text, r"\.col-strong\b")
        for name in (".col-fill", ".col-note"):
            with self.subTest(selector=name):
                self.assertNotRegex(text, rf"{re.escape(name)}\b")

    def test_the_removed_table_classes_are_styled_no_more(self) -> None:
        text = stripped(CSS)
        for name in self.REMOVED:
            with self.subTest(selector=name):
                self.assertNotRegex(text, rf"(?<![\w-]){name}\b")

    def test_no_rule_names_the_movements_table_by_its_id(self) -> None:
        self.assertNotIn("#movements", stripped(CSS))

    def test_the_key_value_table_and_the_sort_button_stay_in_the_lab(
            self) -> None:
        text = stripped(CSS)
        self.assertRegex(text, r"(?<![\w-])\.kv-table\b")
        self.assertRegex(text, r"button\.sort-header")

    def test_the_site_stylesheet_holds_no_lab_table_rules(self) -> None:
        text = stripped(SITE_CSS)
        for name in (".widget-table", ".kv-table", "sort-header"):
            with self.subTest(selector=name):
                self.assertNotIn(name, text)

    def test_the_sort_buttons_print_so_that_the_headers_do(self) -> None:
        """The print rule for the headers' buttons outlives the table
        classes it once sat beside."""
        text = stripped(CSS)
        self.assertRegex(text, r"th\s*>\s*button\.sort-header")
