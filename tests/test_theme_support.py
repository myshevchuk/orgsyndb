"""The theme tests' own helpers (tests/pipeline_support.py): the HTML page
model, the CSS parser and the SMILES index. These are harness checks, not
spec scenarios, so each docstring starts with "Harness:". Pure, no build.
"""

import datetime as dt
import unittest
from pathlib import Path

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

    def test_a_resolved_link_keeps_its_query(self) -> None:
        """Harness: the query of a link target, without the fragment."""
        page = ps.parse_page(
            '<a href="?sort=modified">A</a>'
            '<a href="../x/?status=draft&amp;author=a.+example#f">B</a>'
            '<a href="/y/%C3%A4/">C</a>', "/procedures/")
        self.assertEqual([link.target for link in page.links()],
                         ["/procedures/?sort=modified",
                          "/x/?status=draft&author=a.+example", "/y/ä/"])

    def test_following_skips_the_subtree(self) -> None:
        """Harness: the first element after a heading."""
        page = ps.parse_page(
            "<h2>One</h2><table id=a></table><h2>Two</h2><table id=b>"
            "</table>")
        self.assertEqual(
            page.following(page.heading("Two"), "table").attrs["id"], "b")


class CatalogueHelperTests(unittest.TestCase):
    def test_timestamps_are_written_as_rfc_3339(self) -> None:
        """Harness: rfc3339 of an offset and of UTC."""
        east = dt.timezone(dt.timedelta(hours=2))
        self.assertEqual(
            ps.rfc3339(dt.datetime(2026, 10, 24, 10, tzinfo=east)),
            "2026-10-24T10:00:00+02:00")
        self.assertEqual(
            ps.rfc3339(dt.datetime(2026, 10, 24, 8, tzinfo=dt.UTC)),
            "2026-10-24T08:00:00Z")

    def test_term_keys_are_lowercased_but_slugs(self) -> None:
        """Harness: the taxonomy key of a term."""
        self.assertEqual(ps.term_key("authors", "Ä. Müller"), "ä. müller")
        self.assertEqual(ps.term_key("tags", "sample-data"), "sample-data")
        self.assertEqual(ps.term_key("reaction_types", "Hydrolysis"),
                         "Hydrolysis")

    def test_catalogue_urls(self) -> None:
        """Harness: the pages that carry a catalogue."""
        for url in ("/procedures/", "/general-procedures/", "/compounds/",
                    "/tags/sample-data/", "/authors/a.-example/",
                    "/reaction_types/hydrolysis/"):
            self.assertTrue(ps.is_catalogue_url(url), url)
        for url in ("/", "/tags/", "/authors/", "/reaction_types/",
                    "/help/schema/", "/procedures/osdb-0001/",
                    "/compounds/acetone/", "/sequences/"):
            self.assertFalse(ps.is_catalogue_url(url), url)

    def test_rows_cells_and_facet_values_of_a_catalogue(self) -> None:
        """Harness: catalogue_rows, row_cells and facet_values."""
        page = ps.parse_page(
            '<details class="facet" data-facet="tag"><summary id="s">T'
            '</summary><div role="group"><label class="facet-value">'
            '<input type="checkbox" name="tag" value="a b">'
            '<span class="facet-label">A B</span>'
            '<span class="facet-count"></span></label></div></details>'
            '<table class="procedure-list"><thead><tr><th>ID</th></tr>'
            '</thead><tbody><tr data-id="x"><td>1<td>2</tr><tr><td>3</tr>'
            '</tbody></table>')
        rows = ps.catalogue_rows(page)
        self.assertEqual([[c.norm() for c in ps.row_cells(r)]
                          for r in rows], [["1", "2"], ["3"]])
        self.assertEqual(ps.facet_values(page, "tag"), [("a b", "A B")])
        self.assertEqual(ps.facet_values(page, "type"), [])


class GeneralHelperTests(unittest.TestCase):
    """The helpers that read general procedures."""

    SCOPE = [
        {"substrates": ["a", "b"],
         "products": [{"compound": "x", "yield_percent": 85}]},
        {"substrates": ["b", "c"],
         "products": [{"compound": "y", "yield_percent": 64.5},
                      {"compound": "x", "yield_percent": 70}]},
    ]

    def content(self, scope: list[dict] | None = None) -> ps.Content:
        return ps.Content(Path("OSDB-0001-x.md"),
                          {"scope": scope or self.SCOPE}, "")

    def test_products_and_substrates_are_the_union_in_order(self) -> None:
        """Harness: the union over the entries of a scope."""
        item = self.content()
        self.assertTrue(item.is_general)
        self.assertEqual([e["compound"] for e in item.products], ["x", "y"])
        self.assertEqual(item.products[0]["yield_percent"], 85)
        self.assertEqual(item.substrates, ["a", "b", "c"])
        self.assertEqual(item.kind, "general")
        specific = ps.Content(Path("OSDB-0002-x.md"), {"products": [
            {"compound": "x", "yield_percent": 5}]}, "")
        self.assertEqual((specific.kind, specific.substrates), ("specific",
                                                                []))

    def test_the_yield_of_a_general_procedure_is_a_range(self) -> None:
        """Harness: the range of the yields, with a decimal comma in
        German."""
        item = self.content()
        self.assertEqual(ps.yield_text(item, {}, "en"), "64.5–85 %")
        self.assertEqual(ps.yield_text(item, {}, "de"), "64,5–85 %")
        equal = self.content([{"substrates": ["a"], "products": [
            {"compound": "x", "yield_percent": 85},
            {"compound": "y", "yield_percent": 85.0}]}])
        self.assertEqual(ps.yield_text(equal, {}, "en"), "85 %")

    def test_the_scope_table_of_an_org_source_is_read(self) -> None:
        """Harness: the rows of the table named scope."""
        text = ("* S\n#+name: Scope\n| substrates | products |\n"
                "|---+---|\n| a b | x |\n|  | y |\n\n| other |\n")
        self.assertEqual(ps.org_scope_rows(text),
                         [{"substrates": "a b", "products": "x"},
                          {"substrates": "", "products": "y"}])
        self.assertEqual(ps.org_scope_rows("* S\n| a |\n"), [])


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
