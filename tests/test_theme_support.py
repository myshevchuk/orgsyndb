"""The theme tests' own helpers (tests/pipeline_support.py): the HTML page
model, the CSS parser and the SMILES index. These are harness checks, not
spec scenarios, so each docstring starts with "Harness:". Pure, no build.
"""

import unittest

import pipeline_support as ps


class PageModelTests(unittest.TestCase):
    def test_optional_end_tags_close_their_elements(self) -> None:
        """Harness: omitted end tags of li, dt, dd, td and tr."""
        page = ps.parse_page(
            "<dl><dt>A<dd>x<dt>B<dd>y</dl><ul><li>a<li>b<ul><li>c</ul></ul>"
            "<table><tr><td>1<td>2<tr><td>3</table><p>hi<div>d</div>")
        self.assertEqual([(d.label, d.definition.norm())
                          for d in page.definition_pairs()],
                         [("A", "x"), ("B", "y")])
        self.assertEqual([li.norm() for li in page.find_all("li")],
                         ["a", "bc", "c"])
        self.assertEqual([[c.text for c in row]
                          for row in page.tables()[0].rows],
                         [["1", "2"], ["3"]])
        self.assertEqual(page.find("p").norm(), "hi")

    def test_the_gap_between_dt_and_dd_is_raw_whitespace(self) -> None:
        """Harness: the raw gap of a dt/dd pair."""
        page = ps.parse_page(
            "<dl><dt>A</dt>\n<dd>x</dd><dt>B </dt><dd>y</dd><dt>C<dd>z"
            "</dl>")
        self.assertEqual([d.gap for d in page.definition_pairs()],
                         ["\n", "", ""])

    def test_links_resolve_against_the_page_url(self) -> None:
        """Harness: link targets, attributes and class lookups."""
        page = ps.parse_page(
            '<a class="x y" href="../osdb-0001/">A</a>'
            '<a href="#main">B</a><a href="https://example.invalid/">C</a>'
            '<button hidden data-print>P</button>',
            "/procedures/osdb-0002/")
        self.assertEqual([link.target for link in page.links()],
                         ["/procedures/osdb-0001/",
                          "/procedures/osdb-0002/",
                          "https://example.invalid/"])
        self.assertEqual(len(page.by_class("y")), 1)
        self.assertEqual(len(page.find_all("button", hidden=True)), 1)
        self.assertEqual(page.find_all("button", hidden=False), [])

    def test_following_skips_the_subtree(self) -> None:
        """Harness: the first element after a heading."""
        page = ps.parse_page(
            "<h2>One</h2><table id=a></table><h2>Two</h2><table id=b>"
            "</table>")
        self.assertEqual(
            page.following(page.heading("Two"), "table").attrs["id"], "b")


class CssParserTests(unittest.TestCase):
    def test_nested_blocks_and_margin_boxes(self) -> None:
        """Harness: media contexts and @page margin boxes."""
        found = ps.parse_css(
            '/* c */ @page { size: A4; @bottom-center { content: "Page "'
            ' counter(page) ";" } }\n'
            "@media (prefers-color-scheme: dark) { :root { --bg: #15171a; }"
            " } html, body { color: #000 !important } "
            "a { background: url(data:image/svg+xml;base64,AA==) }")
        self.assertEqual(
            [(d.selector, d.prop, d.value, d.context) for d in found],
            [("@page", "size", "A4", ()),
             ("@page @bottom-center", "content",
              '"Page " counter(page) ";"', ()),
             (":root", "--bg", "#15171a",
              ("@media (prefers-color-scheme: dark)",)),
             ("html, body", "color", "#000 !important", ()),
             ("a", "background", "url(data:image/svg+xml;base64,AA==)",
              ())])

    def test_inline_style_declarations(self) -> None:
        """Harness: the declarations of a style attribute."""
        self.assertEqual(
            [(d.prop, d.value) for d in
             ps.inline_declarations("height:1px; overflow:hidden")],
            [("height", "1px"), ("overflow", "hidden")])


class SmilesIndexTests(unittest.TestCase):
    def test_suffixes_match_the_specification_example(self) -> None:
        """Harness: the SMILES index of aspirin."""
        self.assertEqual(
            ps.smiles_suffixes("CC(=O)Oc1ccccc1C(=O)O"),
            "ccooc1ccccc1coo cooc1ccccc1coo ooc1ccccc1coo oc1ccccc1coo "
            "c1ccccc1coo 1ccccc1coo ccccc1coo cccc1coo ccc1coo cc1coo "
            "c1coo 1coo coo oo o")
