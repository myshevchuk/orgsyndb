"""Checks of a procedure page's widgets (site-theme "Metadata panel",
"Structure image slot" and "Procedure body sections"), and the reader of
the role table that the layouts use for a section's ``data-section``.

The role table is the Hugo partial ``site/layouts/_partials/
procedure-sections.html``. It holds one ``dict`` call whose arguments are
all double-quoted strings, the section names alternating with their
roles: ``dict "Summary" "summary" "Reagents" "reagents" ...``. A call
may run over several lines; names are compared as validation compares
section names (case ignored, runs of whitespace as one space).
"""

import re
import runpy
import unittest
from pathlib import Path
from typing import NamedTuple

import pipeline_support as ps
from pipeline_support import Node, Page

# The roles of validation's eight sections, by position.
ROLES = ("summary", "reagents", "procedure", "workup", "characterization",
         "notes", "hazards", "references")
ROLE_TABLE = (ps.REPO / "site" / "layouts" / "_partials"
              / "procedure-sections.html")
LAB_SUBSTANCE = (ps.REPO / "webapp" / "registry" / "templates" / "registry"
                 / "substance.html")
_COMMENT = re.compile(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", re.S)
_TABLE_CALL = re.compile(r'\bdict((?:\s+"[^"\\]*")+)\s*(?=\)|-?\}\})')
_ROW_LABEL = re.compile(
    r'<th scope="row">\{% translate "([^"]+)"(?: context "[^"]*")? %\}</th>')


class Widget(NamedTuple):
    node: Node
    title: str
    labels: list[str]
    figures: list[Node]


def fold(name: str) -> str:
    """A section name as validation compares names."""
    return " ".join(name.split()).casefold()


def validation_sections() -> dict[str, tuple[str, ...]]:
    """``SECTIONS_BY_LANGUAGE`` of ``tools/validate.py``."""
    return runpy.run_path(
        str(ps.TOOLS / "validate.py"))["SECTIONS_BY_LANGUAGE"]


def role_of(heading: str) -> str | None:
    """The role validation's position gives the section named
    ``heading`` in any language, or None for any other heading."""
    for names in validation_sections().values():
        for role, name in zip(ROLES, names):
            if fold(name) == fold(heading):
                return role
    return None


def parse_role_table(text: str) -> list[tuple[str, str]]:
    """The (name, role) pairs of the one all-literal ``dict`` call in the
    template ``text``, in source order; comments are ignored."""
    calls = _TABLE_CALL.findall(_COMMENT.sub("", text))
    if len(calls) != 1:
        raise AssertionError(
            f"expected one dict call of string literals, found {len(calls)}")
    literals = re.findall(r'"([^"\\]*)"', calls[0])
    if len(literals) % 2:
        raise AssertionError("the role table has an odd number of strings")
    return list(zip(literals[::2], literals[1::2]))


def read_role_table(path: Path = ROLE_TABLE) -> list[tuple[str, str]]:
    """The role table of the layouts."""
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(ps.REPO)} does not exist")
    return parse_role_table(path.read_text(encoding="utf-8"))


def lab_row_labels() -> list[str]:
    """The labels of the rows of the lab's substance page, in the order
    of its template."""
    return _ROW_LABEL.findall(LAB_SUBSTANCE.read_text(encoding="utf-8"))


def details_widgets(case: unittest.TestCase, page: Page) -> list[Widget]:
    """The widgets of the page's details wrapper, each checked for its
    markup: a ``section.widget`` whose first child is the title bar
    ``div.widget__head`` with ``data-pagefind-ignore`` and one ``h2``,
    whose last child is ``div.widget__body`` with one ``dl.metadata``,
    and between them nothing but ``figure.structure`` elements. Returns
    each widget's title, its panel labels and its figures."""
    details = page.find("div", "procedure-details")
    case.assertIsNotNone(details, "no div.procedure-details")
    found = []
    for node in details.elements():
        case.assertEqual((node.tag, node.has_class("widget")),
                         ("section", True),
                         f"the details wrapper holds a {node.tag}")
        children = node.elements()
        case.assertGreaterEqual(len(children), 2, "a widget without parts")
        head, body = children[0], children[-1]
        case.assertEqual((head.tag, head.has_class("widget__head")),
                         ("div", True), "the first part is no title bar")
        case.assertIn("data-pagefind-ignore", head.attrs)
        titles = head.find_all("h2")
        case.assertEqual(len(titles), 1, "not one h2 in the title bar")
        case.assertEqual((body.tag, body.has_class("widget__body")),
                         ("div", True), "the last part is no body")
        lists = body.find_all("dl", "metadata")
        case.assertEqual(len(lists), 1, "not one dl.metadata in the body")
        for figure in children[1:-1]:
            case.assertEqual((figure.tag, figure.has_class("structure")),
                             ("figure", True),
                             f"a {figure.tag} between title bar and body")
        found.append(Widget(node, titles[0].norm(),
                            [p.label for p in page.definition_pairs(lists[0])],
                            children[1:-1]))
    return found


def compound_widget(case: unittest.TestCase, page: Page) -> Widget:
    """The first widget of the details wrapper, which is the compound
    widget; the only one that holds figures. Every figure of the page
    stands in it, and carries ``data-pagefind-ignore``."""
    widgets = details_widgets(case, page)
    case.assertTrue(widgets, "the details wrapper holds no widget")
    case.assertIn(widgets[0].title, ("Compound", "Products", "Verbindung",
                                     "Produkte"))
    case.assertEqual([w.title for w in widgets[1:]
                      if w.figures], [], "a figure beside the compound")
    for figure in widgets[0].figures:
        case.assertIn("data-pagefind-ignore", figure.attrs)
    case.assertEqual(page.find_all("figure", "structure"),
                     widgets[0].figures)
    header = page.find("header", "procedure-header")
    case.assertIsNotNone(header, "no header.procedure-header")
    case.assertEqual(header.find_all("figure"), [])
    return widgets[0]


def check_sections(case: unittest.TestCase, page: Page
                   ) -> list[tuple[Node, Node]]:
    """The body sections of ``page`` (requirement "Procedure body
    sections"): every ``h2`` of ``div.procedure-content`` stands alone in
    the title bar of a ``section.widget.procedure-section`` that is a
    child of the content, once a section has begun only sections follow,
    and a section's ``data-section`` is the role of its heading, or
    absent for another heading. Returns each section with its ``h2``."""
    content = page.find("div", "procedure-content")
    case.assertIsNotNone(content, "no div.procedure-content")
    case.assertTrue(content.within(page.find("article", "procedure")))
    found = []
    for child in content.elements():
        is_section = (child.tag == "section"
                      and child.has_class("widget", "procedure-section"))
        if found:
            case.assertTrue(is_section,
                            f"a {child.tag} follows a section outside it")
        if not is_section:
            case.assertNotEqual(child.tag, "h2", "an h2 outside a section")
            case.assertEqual(child.find_all("h2"), [],
                             "an h2 outside a section")
            continue
        parts = child.elements()
        case.assertEqual(len(parts), 2, "a section without head and body")
        head, body = parts
        case.assertEqual((head.tag, head.has_class("widget__head")),
                         ("div", True))
        case.assertEqual((body.tag, body.has_class("widget__body")),
                         ("div", True))
        headings = [n for n in head.iter() if re.fullmatch(r"h[1-6]", n.tag)]
        case.assertEqual([h.tag for h in headings], ["h2"])
        case.assertTrue(headings[0].attrs.get("id"), "the h2 lost its id")
        case.assertEqual(body.find_all("h2"), [])
        role = role_of(headings[0].norm())
        if role is None:
            case.assertNotIn("data-section", child.attrs)
        else:
            case.assertEqual(child.attrs.get("data-section"), role,
                             headings[0].norm())
        found.append((child, headings[0]))
    case.assertEqual(len(content.find_all("h2")), len(found))
    return found


def section_of(sections: list[tuple[Node, Node]], role: str) -> Node:
    """The section carrying ``data-section`` ``role``."""
    (found,) = [s for s, _ in sections if s.attrs.get("data-section") == role]
    return found
