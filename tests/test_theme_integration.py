"""Theme build tests: HTML scans of a sandbox build (site-theme,
site-search static scenarios, print-layout "The URL is text only").

Each class builds once. ``ShippedSiteTests`` builds the test collection
alone, and ``QuotedTitleSiteTests`` adds the quoted-title fixture to it;
``FixtureSiteTests`` builds the demo collection with the Org and Markdown
twin fixtures, and needs Emacs for their export. Tests skip, naming the
missing tool or cache, as the other integration tests do.
"""

import difflib
import re
import tomllib
import unittest
import urllib.parse

import pipeline_support as ps
from pipeline_support import Content, Node, Page

BANNER = "Sample data — quantities not experimentally verified."
FOOTER = "OrgSynDB · internal procedures"
ORIGIN = "http://127.0.0.1:8000"
NAVIGATION = [("/procedures/", "Procedures"),
              ("/reaction_types/", "Reaction types"), ("/tags/", "Tags"),
              ("/authors/", "Authors"), ("/help/", "Help")]
SECTIONS = ["Summary", "Reagents", "Procedure", "Workup and Purification",
            "Characterization", "Notes", "Hazards and Waste Disposal",
            "References"]
REAGENT_HEADER = ["Reagent", "CAS", "MW (g/mol)", "Amount", "mmol", "Equiv"]
LIST_HEADER = ["ID", "Procedure", "Reaction type", "Status", "Created",
               "Modified"]
PANEL_LABELS = ["ID", "Product", "Formula", "MW", "CAS", "SMILES", "Scale",
                "Yield", "Reaction type", "Tags", "Authors", "Checked by",
                "Created", "Modified", "Precursors", "Used in"]
FONT_SUFFIXES = (".woff", ".woff2", ".ttf", ".otf", ".eot")
TAXONOMIES = {"reaction_types": "Reaction types", "tags": "Tags",
              "authors": "Authors"}
SHIPPED_CHAINS = [("OSDB-0001", "OSDB-0002"), ("OSDB-0004", "OSDB-0005"),
                  ("OSDB-0007", "OSDB-0008")]


class SiteCase(ps.ThemeBuildCase):
    """Helpers shared by the build classes."""

    def by_id(self) -> dict[str, Content]:
        return {item.id: item for item in self.content()}

    def labels(self) -> dict[str, str]:
        return ps.reaction_labels(self.sandbox.app)

    def order_by_id(self) -> list[Content]:
        return sorted(self.content(), key=lambda item: item.id)

    def order_by_date(self) -> list[Content]:
        return sorted(self.order_by_id(), key=lambda item: item.data["date"],
                      reverse=True)

    def page_of(self, item: Content) -> Page:
        return ps.load_page(self.public, self.public / "procedures"
                            / item.slug / "index.html")

    def panel(self, page: Page) -> dict[str, ps.DefPair]:
        panel = page.find("dl", "metadata")
        self.assertIsNotNone(panel, f"{page.url} has no dl.metadata")
        return {pair.label: pair for pair in page.definition_pairs(panel)}

    def table_ids(self, table: ps.TableModel) -> list[str]:
        """The first-cell texts of the body rows of a procedure table."""
        return [row[0].text for row in table.rows
                if row and row[0].tag == "td"]

    def procedure_table(self, page: Page, scope: Node | None = None):
        for table in page.tables():
            header = [c.text for c in table.rows[0]] if table.rows else []
            if header == LIST_HEADER and (
                    scope is None or table.node is scope
                    or table.node.within(scope)):
                return table
        self.fail(f"{page.url} has no table with the columns {LIST_HEADER}")

    def used_in(self, item: Content) -> list[str]:
        return sorted(other.id for other in self.content()
                      if item.id in other.data.get("precursors", []))

    def expected_labels(self, item: Content) -> list[str]:
        data, product = item.data, item.product
        wanted = [("ID", True), ("Product", product.get("name")),
                  ("Formula", product.get("formula")),
                  ("MW", product.get("mw") is not None),
                  ("CAS", product.get("cas")),
                  ("SMILES", product.get("smiles")),
                  ("Scale", data.get("scale")),
                  ("Yield", data.get("yield_percent") is not None),
                  ("Reaction type", data.get("reaction_types")),
                  ("Tags", data.get("tags")),
                  ("Authors", data.get("authors")),
                  ("Checked by", data.get("checked_by")),
                  ("Created", data.get("date")),
                  ("Modified", data.get("lastmod")),
                  ("Precursors", data.get("precursors")),
                  ("Used in", self.used_in(item))]
        return [label for label, present in wanted if present]


class ShippedSiteTests(SiteCase):
    """The shipped procedures, built with the theme."""

    # --- site-theme -------------------------------------------------------

    def test_no_third_party_theme_and_no_web_fonts(self) -> None:
        """Scenario: No third-party theme and no web fonts."""
        site = self.sandbox.app / "site"
        config = tomllib.loads(
            (site / "hugo.toml").read_text(encoding="utf-8"))
        self.assertNotIn("theme", config)
        self.assertFalse((site / "themes").exists())
        self.assertTrue(list((self.public / "css").glob("*.css")),
                        "the build published no theme stylesheet")
        css = sorted(self.public.rglob("*.css"))
        for path in css:
            with self.subTest(file=str(path.relative_to(self.public))):
                self.assertNotIn("@font-face",
                                 path.read_text(encoding="utf-8"))
        fonts = [str(p.relative_to(self.public))
                 for p in self.public.rglob("*")
                 if p.suffix.lower() in FONT_SUFFIXES]
        self.assertEqual(fonts, [])

    def test_only_external_local_scripts(self) -> None:
        """Scenario: Only external, local scripts."""
        scripts = 0
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            for node in page.find_all("script"):
                scripts += 1
                with self.subTest(page=name, script=node.attrs):
                    src = node.attrs.get("src")
                    self.assertIsNotNone(src, "inline script")
                    target = page.resolve(src)
                    self.assertRegex(target, r"^/(js|pagefind)/")
                    self.assertTrue(ps.target_file(self.public, target)
                                    .is_file(), target)
            for node in page.nodes:
                for attribute in node.attrs:
                    with self.subTest(page=name, element=node.tag,
                                      attribute=attribute):
                        self.assertFalse(attribute.startswith("on"))
        self.assertGreater(scripts, 0, "no page loads a script")

    def test_every_page_has_the_shell(self) -> None:
        """Scenario: Shell on every page."""
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            with self.subTest(page=name):
                self.check_shell(page)

    def check_shell(self, page: Page) -> None:
        skip = page.find("a", "skip-link")
        self.assertIsNotNone(skip, "no a.skip-link")
        self.assertEqual(skip.attrs.get("href"), "#main")
        header = page.find("header", "site-header")
        self.assertIsNotNone(header, "no header.site-header")
        nav = header.find("nav", aria_label="Site")
        self.assertIsNotNone(nav, "no nav[aria-label=Site]")
        links = [(link.target, link.node.norm())
                 for link in page.links(nav)]
        for entry in NAVIGATION:
            self.assertIn(entry, links)
        mains = page.find_all("main")
        self.assertEqual(len(mains), 1)
        self.assertEqual(mains[0].attrs.get("id"), "main")
        footer = page.find("footer", "site-footer")
        self.assertIsNotNone(footer, "no footer.site-footer")
        self.assertEqual(footer.norm(), FOOTER)
        order = [page.index_of(n) for n in (skip, header, mains[0], footer)]
        self.assertEqual(order, sorted(order), "shell elements out of order")
        viewport = page.find("meta", name="viewport")
        self.assertIsNotNone(viewport, "no viewport meta")
        # Hugo's minifier drops the space after the comma.
        self.assertEqual(ps.squash(viewport.attrs.get("content", "")),
                         "width=device-width,initial-scale=1")
        scheme = page.find("meta", name="color-scheme")
        self.assertIsNotNone(scheme, "no color-scheme meta")
        self.assertEqual(scheme.attrs.get("content"), "light dark")
        levels = [level for level, _ in page.headings()]
        self.assertEqual(levels.count(1), 1, "not exactly one h1")
        for before, after in zip(levels, levels[1:]):
            self.assertLessEqual(after, before + 1, f"heading jump {levels}")
        title = page.title()
        if page.url == "/":
            self.assertEqual(title, "OrgSynDB")
        else:
            self.assertTrue(title.endswith(" | OrgSynDB"), title)

    def test_term_titles_use_labels_and_tags(self) -> None:
        """Scenario: Term titles use labels and tags."""
        for relative, heading, title in (
                ("reaction_types/aldol-condensation", "Aldol condensation",
                 "Aldol condensation | OrgSynDB"),
                ("tags/sample-data", "sample-data",
                 "sample-data | OrgSynDB")):
            path = self.public / relative / "index.html"
            with self.subTest(page=relative):
                self.assertTrue(path.is_file(), f"{relative} not published")
                page = ps.load_page(self.public, path)
                self.assertEqual(
                    [text for level, text in page.headings()
                     if level == 1], [heading])
                self.assertEqual(page.title(), title)

    def test_three_stylesheets_on_every_page(self) -> None:
        """Scenario: Three links on every page."""
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            with self.subTest(page=name):
                sheets = [(page.resolve(href), media)
                          for href, media in page.stylesheets()]
                site = [s for s in sheets
                        if not s[0].startswith("/pagefind/")]
                self.assertEqual([m for _, m in site],
                                 [None, "screen", "print"])
                for target, _ in site:
                    self.assertRegex(target, r"^/css/")
                    self.assertTrue(ps.target_file(self.public, target)
                                    .is_file(), target)
                bundle = [t for t, _ in sheets
                          if t.startswith("/pagefind/")]
                if name == "search/index.html":
                    self.assertEqual(bundle, ["/pagefind/pagefind-ui.css"])
                    self.assertTrue((self.public / "pagefind"
                                     / "pagefind-ui.css").is_file())
                else:
                    self.assertEqual(bundle, [])

    def test_reagents_tables_are_wrapped_and_marked(self) -> None:
        """Scenario: Reagents tables are wrapped and marked."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                heading = page.heading("Reagents")
                self.assertIsNotNone(heading, "no Reagents heading")
                table = page.following(heading, "table")
                self.assertIsNotNone(table, "no table after Reagents")
                wrapper = table.parent
                self.assertEqual(wrapper.tag, "div")
                self.assertIn("table-scroll", wrapper.classes)
                self.assertEqual(wrapper.attrs.get("tabindex"), "0")
                self.assertEqual(wrapper.attrs.get("role"), "region")
                self.assertTrue(wrapper.attrs.get("aria-label", "").strip())
                self.assertEqual(
                    [c for c in wrapper.elements()], [table])
                model = next(t for t in page.tables() if t.node is table)
                header = [c for c in model.rows[0]]
                self.assertEqual([c.text for c in header], REAGENT_HEADER)
                for cell in header:
                    self.assertEqual(cell.node.attrs.get("scope"), "col")
                for row in model.rows:
                    self.assertEqual(
                        [i for i, c in enumerate(row) if "num" in c.classes],
                        [1, 2, 4, 5], f"row {[c.text for c in row]}")

    def test_header_and_body_are_in_order(self) -> None:
        """Scenario: Header and body in order."""
        for slug in ("osdb-0002", "osdb-0001"):
            path = self.public / "procedures" / slug / "index.html"
            with self.subTest(page=slug):
                self.assertTrue(path.is_file())
                self.check_order(ps.load_page(self.public, path),
                                 slug.upper())

    def check_order(self, page: Page, ident: str) -> None:
        main = page.find("main")
        header = page.find("header", "procedure-header")
        article = page.find("article", "procedure")
        self.assertIsNotNone(header, "no header.procedure-header")
        self.assertIsNotNone(article, "no article.procedure")
        self.assertEqual(page.indexed_bodies(), [article])
        banner = page.find("p", "sample-banner")
        self.assertIsNotNone(banner, "sample without a banner")
        self.assertIs(main.elements()[0], banner)
        order = [page.index_of(n) for n in (banner, header, article)]
        self.assertEqual(order, sorted(order))
        identity = header.find("p", "procedure-id")
        self.assertIsNotNone(identity, "no p.procedure-id")
        marked = identity.find(data_pagefind_meta="id")
        self.assertIsNotNone(marked, "no element with meta id")
        self.assertEqual(marked.norm(), ident)
        badge = identity.find("span", "badge")
        self.assertIsNotNone(badge, "no status badge")
        self.assertIn("badge--draft", badge.classes)
        self.assertEqual(badge.norm(), "draft")
        h1 = header.find("h1")
        facts = header.find("p", "print-facts")
        actions = header.find("p", "actions")
        for node, what in ((h1, "h1"), (facts, "p.print-facts"),
                           (actions, "p.actions")):
            self.assertIsNotNone(node, f"header has no {what}")
        parts = [page.index_of(n) for n in (identity, h1, facts, actions)]
        self.assertEqual(parts, sorted(parts), "header parts out of order")
        button = actions.find("button", "print-button")
        self.assertIsNotNone(button, "no button.print-button")
        self.assertEqual(button.attrs.get("type"), "button")
        self.assertIn("data-print", button.attrs)
        self.assertIn("hidden", button.attrs)
        self.assertEqual(button.norm(), "Print / Save as PDF")
        for outside in (h1, marked):
            self.assertFalse(outside.within(article),
                             f"{outside.tag} lies inside the article")
        # The desktop columns wrap the details and body; reading and
        # indexing order still starts with the metadata panel.
        panel = article.find("dl", "metadata")
        self.assertIsNotNone(panel, "no dl.metadata")
        figure = article.find("figure", "structure")
        summary = page.heading("Summary")
        index = article.find("span", data_smiles_index=True)
        for node, what in ((figure, "figure.structure"),
                           (summary, "Summary heading"),
                           (index, "SMILES index")):
            self.assertIsNotNone(node, f"article has no {what}")
        order = [page.index_of(n) for n in (panel, figure, summary, index)]
        self.assertEqual(order, sorted(order))
        self.assertTrue(summary.within(article))

    def test_markdown_seed_panel(self) -> None:
        """Scenario: Panel of the Markdown seed."""
        path = self.public / "procedures" / "osdb-0002" / "index.html"
        self.assertTrue(path.is_file())
        page = ps.load_page(self.public, path)
        panel = self.panel(page)
        self.assertEqual(
            list(panel),
            ["ID", "Product", "Formula", "MW", "CAS", "SMILES", "Scale",
             "Yield", "Reaction type", "Tags", "Authors", "Created",
             "Modified", "Precursors"])
        text = {label: pair.definition.norm()
                for label, pair in panel.items()}
        self.assertEqual(text["ID"], "OSDB-0002")
        self.assertEqual(text["Product"], "Acetylsalicylic acid")
        self.assertEqual(text["Formula"], "C9H8O4")
        self.assertEqual(len(panel["Formula"].definition.find_all("sub")), 3)
        self.assertEqual(text["MW"], "180.16 g/mol")
        self.assertEqual(text["CAS"], "50-78-2")
        smiles = panel["SMILES"].definition
        code = smiles.find("code", data_smiles=True)
        self.assertIsNotNone(code, "no code[data-smiles]")
        self.assertEqual(code.norm(), "CC(=O)Oc1ccccc1C(=O)O")
        copy = smiles.find("button", "copy-button")
        self.assertIsNotNone(copy, "no button.copy-button")
        self.assertEqual(copy.attrs.get("type"), "button")
        self.assertIn("data-copy-smiles", copy.attrs)
        self.assertIn("hidden", copy.attrs)
        self.assertEqual(copy.norm(), "Copy")
        self.assertGreater(page.index_of(copy), page.index_of(code))
        self.assertEqual(text["Scale"], "20 mmol")
        self.assertEqual(text["Yield"], "75 %")
        for label, texts in (("Reaction type", ["Acylation"]),
                             ("Tags", ["sample-data", "acetylation"]),
                             ("Authors", ["A. Example", "C. Example"])):
            links = page.links(panel[label].definition)
            self.assertEqual([l.node.norm() for l in links], texts, label)
            for link in links:
                term = ps.load_page(self.public, ps.target_file(
                    self.public, link.target))
                self.assertEqual(
                    [t for lv, t in term.headings() if lv == 1],
                    [link.node.norm()])
        for label, stamp, shown in (
                ("Created", "2026-10-19T23:46:11+02:00", "2026-10-19 23:46"),
                ("Modified", "2026-10-19T23:50:11+02:00",
                 "2026-10-19 23:50")):
            moment = panel[label].definition.find("time")
            self.assertIsNotNone(moment, f"no time element in {label}")
            self.assertEqual(moment.attrs.get("datetime"), stamp)
            self.assertEqual(moment.norm(), shown)
        precursor = panel["Precursors"].definition.find("a", "precursor")
        self.assertIsNotNone(precursor, "no a.precursor")
        self.assertEqual(precursor.norm(), "OSDB-0001 Salicylic acid")
        for label, pair in panel.items():
            with self.subTest(label=label):
                self.assertNotEqual(pair.gap, "")
                self.assertEqual(pair.gap.strip(), "")

    def test_panel_labels_follow_the_canonical_order(self) -> None:
        """Scenario: Panel labels follow the canonical order on every
        page."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                pairs = self.panel(page)
                shown = list(pairs)
                positions = [PANEL_LABELS.index(label) for label in shown]
                self.assertEqual(positions, sorted(set(positions)))
                self.assertEqual(shown, self.expected_labels(item))
                for label, pair in pairs.items():
                    self.assertNotEqual(pair.gap, "", label)
                    self.assertEqual(pair.gap.strip(), "", label)

    def test_precursor_and_used_in_links_resolve_both_ways(self) -> None:
        """Scenario: Links resolve in both directions."""
        items = self.by_id()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                precursors = [l for l in page.links()
                              if l.node.has_class("precursor")]
                used_in = [l for l in page.links()
                           if l.node.has_class("used-in")]
                self.check_links(page, precursors,
                                 item.data.get("precursors", []), items)
                self.check_links(page, used_in, self.used_in(item), items)
        for path, page in self.pages():
            if "procedures" in path.parts and path.parent.name.startswith(
                    "osdb-"):
                continue
            with self.subTest(page=str(path.relative_to(self.public))):
                self.assertEqual(
                    [l for l in page.links()
                     if l.node.has_class("precursor")
                     or l.node.has_class("used-in")], [])

    def check_links(self, page: Page, links, expected: list[str],
                    items: dict[str, Content]) -> None:
        self.assertEqual([l.target for l in links],
                         [f"/procedures/{items[i].slug}/" for i in expected])
        self.assertEqual([l.node.norm() for l in links],
                         [f"{i} {items[i].title}" for i in expected])
        for link in links:
            self.assertTrue(ps.target_file(self.public, link.target)
                            .is_file(), link.target)

    def test_the_shipped_chains(self) -> None:
        """Scenario: The shipped chains."""
        for first, second in SHIPPED_CHAINS:
            for ident, relation, other in ((first, "used-in", second),
                                           (second, "precursor", first)):
                path = (self.public / "procedures" / ident.lower()
                        / "index.html")
                with self.subTest(procedure=ident, relation=relation):
                    self.assertTrue(path.is_file(), f"{ident} not built")
                    page = ps.load_page(self.public, path)
                    links = [l for l in page.links()
                             if l.node.has_class(relation)]
                    self.assertEqual([l.target for l in links],
                                     [f"/procedures/{other.lower()}/"])
                    other_relation = ("precursor" if relation == "used-in"
                                      else "used-in")
                    self.assertEqual(
                        [l for l in page.links()
                         if l.node.has_class(other_relation)], [])

    def test_every_sample_shows_the_banner(self) -> None:
        """Scenario: Every sample shows the banner."""
        seen = 0
        for item, page in self.procedure_pages():
            if "sample-data" not in item.tags:
                continue
            seen += 1
            with self.subTest(procedure=item.id):
                banners = page.find_all("p", "sample-banner")
                self.assertEqual(len(banners), 1)
                self.assertEqual(banners[0].attrs.get("role"), "note")
                self.assertEqual(banners[0].norm(), BANNER)
                self.assertFalse(banners[0].within(
                    page.find("article", "procedure")))
        self.assertGreater(seen, 0, "no sample procedure was built")

    def test_structure_image_and_placeholder(self) -> None:
        """Scenario: Image and placeholder."""
        path = self.public / "procedures" / "osdb-0003" / "index.html"
        self.assertTrue(path.is_file(), "osdb-0003 is not built")
        page = ps.load_page(self.public, path)
        figure = page.find("figure", "structure")
        self.assertIsNotNone(figure, "no figure.structure")
        self.assertFalse(figure.has_class("structure--placeholder"))
        image = figure.find("img")
        self.assertIsNotNone(image, "no img in the figure")
        self.assertEqual(page.resolve(image.attrs.get("src", "")),
                         "/structures/osdb-0003.svg")
        self.assertTrue(
            (self.public / "structures" / "osdb-0003.svg").is_file())
        self.assertEqual(image.attrs.get("alt"),
                         "Structure of Isopentyl acetate")
        path = self.public / "procedures" / "osdb-0002" / "index.html"
        page = ps.load_page(self.public, path)
        figure = page.find("figure", "structure")
        self.assertIsNotNone(figure, "no figure.structure")
        self.assertTrue(figure.has_class("structure--placeholder"))
        slot = figure.find("div", "structure__slot")
        self.assertIsNotNone(slot, "no div.structure__slot")
        self.assertEqual(slot.norm(), "No structure image")
        self.assertEqual(page.find_all("img"), [])

    def test_both_procedure_lists_are_in_order(self) -> None:
        """Scenario: Both orders."""
        items = {item.id: item for item in self.content()}
        for url, order, other in (
                ("procedures", self.order_by_id(), "/procedures-by-date/"),
                ("procedures-by-date", self.order_by_date(),
                 "/procedures/")):
            path = self.public / url / "index.html"
            with self.subTest(page=url):
                self.assertTrue(path.is_file(), f"{url} not published")
                page = ps.load_page(self.public, path)
                table = self.procedure_table(page)
                self.assertEqual(self.table_ids(table),
                                 [item.id for item in order])
                labels = self.labels()
                for row, item in zip(table.rows[1:], order):
                    self.assertEqual(row[2].text, labels[
                        item.data["reaction_types"][0]])
                    self.assertEqual(row[3].text, item.data["status"])
                    for cell in row[:2]:
                        self.assertEqual(
                            [l.target for l in page.links(cell.node)],
                            [f"/procedures/{item.slug}/"])
                self.assertIn(other, [l.target for l in page.links()])
                current = [l for l in page.links()
                           if l.node.attrs.get("aria-current") == "page"]
                self.assertIn(page.url, [l.target for l in current])
                self.assertNotIn(other, [l.target for l in current])
        self.assertEqual(len(items), len(self.order_by_date()))

    def test_list_tools_on_both_lists(self) -> None:
        """Scenario: List tools."""
        labels = self.labels()
        in_use = sorted({labels[slug] for item in self.content()
                         for slug in item.data["reaction_types"]})
        total = len(self.content())
        for url in ("procedures", "procedures-by-date"):
            path = self.public / url / "index.html"
            with self.subTest(page=url):
                page = ps.load_page(self.public, path)
                main = page.find("main")
                count = main.find("p", "list-count", data_list_count=True)
                self.assertIsNotNone(count, "no p.list-count")
                self.assertEqual(count.norm(), f"{total} entries")
                self.assertEqual(count.attrs.get("data-filtered"),
                                 "{shown} of {total} entries")
                form = main.find("form", role="search")
                self.assertIsNotNone(form, "no form[role=search]")
                self.assertEqual(form.attrs.get("method", "").lower(), "get")
                self.assertEqual(page.resolve(form.attrs.get("action", "")),
                                 "/search/")
                field = form.find("input", name="q")
                self.assertIsNotNone(field, "no input[name=q]")
                self.assertTrue(field.attrs.get("aria-label"))
                submit = form.find("button", type="submit")
                self.assertIsNotNone(submit, "no submit button")
                self.assertNotIn("hidden", submit.attrs)
                filters = main.find("div", "list-filters",
                                    data_list_filters=True)
                self.assertIsNotNone(filters, "no div.list-filters")
                self.assertIn("hidden", filters.attrs)
                kinds = filters.find("select", data_filter="reaction-type")
                options = [(o.attrs.get("value"), o.norm())
                           for o in kinds.find_all("option")]
                self.assertEqual(options[0], ("", "All"))
                self.assertEqual(sorted(text for _, text in options[1:]),
                                 in_use)
                states = filters.find("select", data_filter="status")
                self.assertEqual(
                    [o.attrs.get("value") for o in states.find_all("option")],
                    ["", "draft", "checked", "retired"])
                table = self.procedure_table(page)
                rows = table.node.find("tbody").find_all("tr")
                items = {item.id: item for item in self.content()}
                for row in rows:
                    item = items[row.find("td").norm()]
                    self.assertEqual(row.attrs.get("data-status"),
                                     item.data["status"])
                    self.assertEqual(row.attrs.get("data-reaction-types"),
                                     " ".join(item.data["reaction_types"]))
                scripts = [page.resolve(s.attrs.get("src", ""))
                           for s in page.find_all("script")]
                self.assertTrue(any(re.match(r"^/js/list-filter\b", s)
                                    for s in scripts), scripts)

    def test_navigation_marks_the_current_section(self) -> None:
        """Scenario: Current section in the navigation."""
        cases = {"index.html": {},
                 "procedures/index.html": {"/procedures/": "page"},
                 "procedures-by-date/index.html": {"/procedures/": "true"},
                 "procedures/osdb-0001/index.html": {"/procedures/": "true"},
                 "tags/index.html": {"/tags/": "page"},
                 "tags/sample-data/index.html": {"/tags/": "true"},
                 "search/index.html": {},
                 "help/index.html": {"/help/": "page"},
                 "help/schema/index.html": {"/help/": "true"}}
        for name, expected in cases.items():
            with self.subTest(page=name):
                page = ps.load_page(self.public, self.public / name)
                nav = page.find("header", "site-header").find("nav")
                marked = {l.target: l.node.attrs["aria-current"]
                          for l in page.links(nav)
                          if "aria-current" in l.node.attrs}
                self.assertEqual(marked, expected)

    def help_lists(self, page: Page) -> dict[str, Node]:
        """The ul.help-list after each h2 of a help index, by heading."""
        lists = {}
        for heading in page.find("main").find_all("h2"):
            node = page.following(heading, "ul", "h2")
            self.assertIsNotNone(node, f"no list after {heading.norm()}")
            self.assertTrue(node.has_class("help-list"), heading.norm())
            lists[heading.norm()] = node
        return lists

    def test_english_help_index(self) -> None:
        """Scenario: English help index."""
        page = ps.load_page(self.public, self.public / "help" / "index.html")
        main = page.find("main")
        self.assertEqual([h.norm() for h in main.find_all("h1")], ["Help"])
        lede = main.find("p", "lede")
        self.assertIsNotNone(lede, "no p.lede")
        self.assertEqual(lede.norm(),
                         "Guides to writing procedures, and glossaries.")
        lists = self.help_lists(page)
        self.assertEqual(list(lists), ["Guides", "Glossaries"])
        documents = ps.help_documents(self.sandbox.app)
        names = {"de": "Deutsch", "en": "English"}
        for group, heading in [("guides", "Guides"),
                               ("glossaries", "Glossaries")]:
            versions: dict[str, list[ps.HelpDocument]] = {}
            for doc in documents:
                if doc.group == group:
                    versions.setdefault(doc.base, []).append(doc)
            items = [li for li in lists[heading].elements()
                     if li.tag == "li"]
            self.assertEqual(len(items), len(versions), heading)
            for li, base in zip(items, sorted(versions)):
                with self.subTest(base=base):
                    docs = sorted(versions[base], key=lambda d: d.language)
                    first = next((d for d in docs if d.language == "en"),
                                 docs[0])
                    links = page.links(li)
                    self.assertEqual(links[0].target, f"/help/{first.slug}/")
                    self.assertEqual(links[0].node.norm(), first.title)
                    self.assertEqual(links[0].node.get("hreflang"),
                                     first.language)
                    self.assertEqual(links[0].node.get("lang"),
                                     None if first.language == "en"
                                     else first.language)
                    others = [d for d in docs if d is not first]
                    self.assertEqual(
                        [(l.target, l.node.norm(), l.node.get("hreflang"))
                         for l in links[1:]],
                        [(f"/help/{d.slug}/", names[d.language], d.language)
                         for d in others])

    def test_help_pages_of_a_build(self) -> None:
        """Scenario: Help pages of a build."""
        documents = ps.help_documents(self.sandbox.app)
        pages = (self.public / "help").glob("*/index.html")
        published = sorted(p.parent.name for p in pages)
        self.assertEqual(published, sorted(d.slug for d in documents))
        scheme = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
        for doc in documents:
            with self.subTest(document=doc.name):
                page = ps.load_page(self.public, self.public / "help"
                                    / doc.slug / "index.html")
                articles = page.find("main").find_all("article", "help-page")
                self.assertEqual(len(articles), 1)
                article = articles[0]
                self.assertEqual(article.get("lang"), doc.language)
                self.assertEqual([h.norm() for h in article.find_all("h1")],
                                 [doc.title])
                self.assertEqual(page.indexed_bodies(), [])
                for link in page.links(article):
                    href = link.href
                    self.assertIsNone(
                        re.search(r"\.(md|org)(#|$)", href), href)
                    if scheme.match(href) or href.startswith("#"):
                        continue
                    self.assertTrue(link.target.startswith("/help/"), href)
                    target = ps.target_file(self.public, link.target)
                    self.assertTrue(target.is_file(), href)
                    fragment = urllib.parse.unquote(
                        urllib.parse.urldefrag(href).fragment)
                    if fragment:
                        other = ps.load_page(self.public, target)
                        self.assertIsNotNone(other.find(id=fragment), href)

    def test_home_page_content(self) -> None:
        """Scenario: Home page content."""
        path = self.public / "index.html"
        page = ps.load_page(self.public, path)
        main = page.find("main")
        form = main.find("form", role="search")
        self.assertIsNotNone(form, "no form[role=search]")
        self.assertEqual(form.attrs.get("method", "").lower(), "get")
        self.assertEqual(page.resolve(form.attrs.get("action", "")),
                         "/search/")
        field = form.find("input", name="q")
        self.assertIsNotNone(field, "no input[name=q]")
        label = form.find("label", **{"for": field.attrs.get("id", "-")})
        labelled = label is not None or field.attrs.get("aria-label") or any(
            a.tag == "label" for a in field.ancestors())
        self.assertTrue(labelled, "the input has no label")
        submits = [n for n in form.find_all()
                   if (n.tag == "button" and n.attrs.get(
                       "type", "submit") == "submit")
                   or (n.tag == "input" and n.attrs.get("type") == "submit")]
        self.assertTrue(submits, "no submit control")
        for node in submits:
            self.assertNotIn("hidden", node.attrs)
        recent = self.heading_of(page, "Recent procedures")
        table = self.procedure_table(
            page, page.following(recent, "table"))
        self.assertEqual(self.table_ids(table),
                         [i.id for i in self.order_by_date()[:5]])
        counts = self.term_counts()
        for text, taxonomy, expected in (
                ("Browse by reaction type", "reaction_types",
                 {self.labels()[s]: n for s, n
                  in counts["reaction_types"].items()}),
                ("Browse by tag", "tags", counts["tags"])):
            with self.subTest(heading=text):
                heading = self.heading_of(page, text)
                container = page.following(heading, "ul", "ol")
                self.assertIsNotNone(container, f"no list after {text}")
                links = page.links(container)
                found = {}
                for link in links:
                    entry = next(a for a in link.node.ancestors()
                                 if a.tag == "li")
                    rest = entry.norm().replace(link.node.norm(), "", 1)
                    found[link.node.norm()] = (
                        link.target, re.findall(r"\b\d+\b", rest))
                self.assertEqual(len(found), len(links))
                self.assertEqual(sorted(found), sorted(expected))
                for name, count in expected.items():
                    self.assertIn(str(count), found[name][1], name)
                    self.assertTrue(found[name][0].startswith(
                        f"/{taxonomy}/"))
        self.assertIn("/procedures/", [l.target for l in page.links(main)])

    def heading_of(self, page: Page, text: str) -> Node:
        for level in range(1, 7):
            found = page.heading(text, level)
            if found is not None:
                return found
        self.fail(f"{page.url} has no heading {text!r}")

    def term_counts(self) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {
            "reaction_types": {}, "tags": {}, "authors": {}}
        for item in self.content():
            for taxonomy in counts:
                for term in item.data.get(taxonomy, []):
                    counts[taxonomy][term] = counts[taxonomy].get(term,
                                                                  0) + 1
        return counts

    def test_every_term_page_lists_the_right_procedures(self) -> None:
        """Scenario: Every term page lists the right procedures."""
        labels = self.labels()
        for taxonomy, heading in TAXONOMIES.items():
            path = self.public / taxonomy / "index.html"
            with self.subTest(taxonomy=taxonomy):
                self.assertTrue(path.is_file(), f"{taxonomy} not published")
                page = ps.load_page(self.public, path)
                self.assertEqual(
                    [t for lv, t in page.headings() if lv == 1], [heading])
                main = page.find("main")
                links = [l for l in page.links(main)
                         if l.target.startswith(f"/{taxonomy}/")
                         and l.target != f"/{taxonomy}/"]
                shown = {l.node.norm(): l for l in links}
                self.assertEqual(len(shown), len(links))
                expected = {}
                for term, count in self.term_counts()[taxonomy].items():
                    name = labels[term] if taxonomy == "reaction_types" \
                        else term
                    expected[name] = (term, count)
                self.assertEqual(sorted(shown), sorted(expected))
                for name, (term, count) in expected.items():
                    link = shown[name]
                    entry = next(a for a in link.node.ancestors()
                                 if a.tag == "li")
                    rest = entry.norm().replace(name, "", 1)
                    self.assertIn(str(count), re.findall(r"\b\d+\b", rest))
                    term_path = ps.target_file(self.public, link.target)
                    self.assertTrue(term_path.is_file(), link.target)
                    term_page = ps.load_page(self.public, term_path)
                    self.assertEqual(
                        [t for lv, t in term_page.headings() if lv == 1],
                        [name])
                    table = self.procedure_table(
                        term_page, term_page.find("main"))
                    self.assertEqual(
                        self.table_ids(table),
                        sorted(i.id for i in self.content()
                               if term in i.data.get(taxonomy, [])))

    def test_static_html_holds_the_content(self) -> None:
        """Scenario: Static HTML holds the content."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                panel = page.find("dl", "metadata")
                self.assertIsNotNone(panel, "no dl.metadata")
                text = panel.norm()
                for value in (item.id, item.product.get("name"),
                              item.product.get("cas"),
                              item.product.get("smiles"),
                              f"{item.data.get('yield_percent')} %"):
                    self.assertIn(value, text)
                article = page.find("article", "procedure")
                self.assertEqual(
                    [n.norm() for n in article.find_all("h2")
                     if n.norm() in SECTIONS], SECTIONS)
                self.assertTrue(page.links(panel))
                data_print = page.find_all("button", data_print=True)
                data_copy = page.find_all("button", data_copy_smiles=True)
                self.assertEqual(len(data_print), 1)
                self.assertEqual(len(data_copy), 1)
        for path, page in self.pages():
            for button in page.buttons():
                with self.subTest(page=str(path.relative_to(self.public)),
                                  button=button.norm()):
                    enhanced = ("data-print" in button.attrs
                                or "data-copy-smiles" in button.attrs)
                    self.assertEqual("hidden" in button.attrs, enhanced)

    def test_printed_url_is_text_only(self) -> None:
        """Scenario: The URL is text only."""
        procedure_urls = {f"/procedures/{item.slug}/"
                          for item in self.content()}
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            with self.subTest(page=name):
                spans = page.find_all("span", "page-url")
                inside = sum(s.text().count(ORIGIN) for s in spans)
                source = page.source
                document = page.find("article", "help-page")
                if document is not None:
                    source = (source[:document.start]
                              + source[document.end_tag_end:])
                self.assertEqual(source.count(ORIGIN), inside)
                for node in page.nodes:
                    if document is not None and node.within(document):
                        continue
                    for value in node.attrs.values():
                        self.assertNotIn("127.0.0.1", value)
                if page.url in procedure_urls:
                    self.assertEqual([s.text() for s in spans],
                                     [ORIGIN + page.url])
                else:
                    self.assertEqual(spans, [])

    # --- site-search, static scenarios --------------------------------------

    def test_search_page_wiring(self) -> None:
        """Scenario: Search page wiring."""
        path = self.public / "search" / "index.html"
        self.assertTrue(path.is_file(), "search/index.html not published")
        page = ps.load_page(self.public, path)
        self.assertIn("/pagefind/pagefind-ui.css",
                      [page.resolve(h) for h, _ in page.stylesheets()])
        sources = [page.resolve(s) for s in page.script_sources() if s]
        self.assertIn("/pagefind/pagefind-ui.js", sources)
        bundles = [s for s in sources if s.startswith("/js/")
                   and "PagefindUI" in ps.target_file(
                       self.public, s).read_text(encoding="utf-8")]
        self.assertEqual(len(bundles), 1, f"scripts are {sources}")
        self.assertLess(sources.index("/pagefind/pagefind-ui.js"),
                        sources.index(bundles[0]))
        script = ps.target_file(self.public, bundles[0]).read_text(
            encoding="utf-8")
        for word in ("PagefindUI", "processTerm", "processResult",
                     "triggerSearch"):
            self.assertIn(word, script)
        mounts = page.find_all(data_search=True)
        self.assertEqual(len(mounts), 1)
        self.assertEqual((mounts[0].norm(), mounts[0].elements()), ("", []))
        fallback = page.find("noscript")
        self.assertIsNotNone(fallback, "no noscript element")
        self.assertIn("javascript", fallback.norm().lower())
        targets = {l.target for l in page.links(fallback)}
        self.assertTrue({"/procedures/", "/reaction_types/", "/tags/",
                         "/authors/"} <= targets, targets)
        self.assertEqual(page.indexed_bodies(), [])

    def test_metadata_is_indexed_and_chrome_is_not(self) -> None:
        """Scenario: Metadata inside the body, chrome outside."""
        navigation = " ".join(text for _, text in NAVIGATION)
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                bodies = page.indexed_bodies()
                self.assertEqual(len(bodies), 1)
                text = bodies[0].norm()
                expected = [item.id, item.product.get("name"),
                            item.product.get("smiles"), *item.tags,
                            *item.data.get("authors", [])]
                if item.product.get("cas"):
                    expected.append(item.product["cas"])
                for value in expected:
                    self.assertIn(value, text)
                self.assertNotIn(BANNER, text)
                self.assertNotIn(navigation, text)
                self.assertNotIn(navigation.replace(" ", ""),
                                 text.replace(" ", ""))

    def test_filter_attributes_on_every_procedure_page(self) -> None:
        """Scenario: Filter attributes on every procedure page."""
        labels = self.labels()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                found: dict[str, list[str]] = {}
                for _node, key, text in page.filter_elements():
                    found.setdefault(key, []).append(text)
                expected = {
                    "status": [item.data["status"]],
                    "reaction type": [labels[s] for s
                                      in item.data["reaction_types"]],
                    "tag": item.tags,
                    "author": item.data["authors"]}
                self.assertEqual(
                    {k: sorted(v) for k, v in found.items()},
                    {k: sorted(v) for k, v in expected.items()})
                for node, _key, _text in page.filter_elements():
                    self.assertNotIn(node.tag, ("ul", "ol", "dl"))

    def test_smiles_index_value_of_the_markdown_seed(self) -> None:
        """Scenario: Index value."""
        path = self.public / "procedures" / "osdb-0002" / "index.html"
        self.assertTrue(path.is_file())
        page = ps.load_page(self.public, path)
        index = page.find("span", data_smiles_index=True)
        self.assertIsNotNone(index, "no SMILES index element")
        self.assertEqual(
            index.attrs["data-smiles-index"],
            "ccooc1ccccc1coo cooc1ccccc1coo ooc1ccccc1coo oc1ccccc1coo "
            "c1ccccc1coo 1ccccc1coo ccccc1coo cccc1coo ccc1coo cc1coo "
            "c1coo 1coo coo oo o")

    def test_smiles_index_on_every_procedure_page(self) -> None:
        """Scenario: Index on every procedure page."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                indexes = page.find_all(data_smiles_index=True)
                self.assertEqual(len(indexes), 1)
                index = indexes[0]
                self.assertEqual(index.tag, "span")
                self.assertIn("hidden", index.attrs)
                self.assertEqual(index.attrs.get("data-pagefind-meta"),
                                 "smiles_index[data-smiles-index]")
                self.assertEqual(
                    index.attrs["data-smiles-index"],
                    ps.smiles_suffixes(item.product["smiles"]))
                article = page.find("article", "procedure")
                self.assertIs(article.elements()[-1], index)


class FixtureSiteTests(SiteCase):
    """The demo collection plus the Org and Markdown twin fixtures."""

    COLLECTION = ps.DEMO
    FIXTURES = ("OSDB-0904-twin.org", "OSDB-0905-twin.md")

    @classmethod
    def require_tools(cls) -> None:
        ps.require_exporter()

    def twin(self, ident: str) -> str:
        path = (self.public / "procedures" / ident.lower() / "index.html")
        self.assertTrue(path.is_file(), f"{ident} was not published")
        text = path.read_text(encoding="utf-8")
        for number in ("0904", "0905"):
            text = text.replace(f"OSDB-{number}", "OSDB-NNNN").replace(
                f"osdb-{number}", "osdb-nnnn")
        return text

    def test_org_and_markdown_twins_render_alike(self) -> None:
        """Scenario: Twin fixtures."""
        org, markdown = self.twin("OSDB-0904"), self.twin("OSDB-0905")
        page = Page(markdown)
        self.assertIn("Checked by", self.panel(page))
        self.assertIsNotNone(page.find("p", "sample-banner"))
        difference = "".join(difflib.unified_diff(
            org.splitlines(True), markdown.splitlines(True), n=0))
        self.assertEqual(org, markdown, difference[:2000])


class QuotedTitleSiteTests(SiteCase):
    """The test collection plus the quoted-title fixture."""

    FIXTURES = ("OSDB-0906-quoted-title.md",)

    def test_a_procedure_without_the_tag_has_no_banner(self) -> None:
        """Scenario: A procedure without the tag has none."""
        quoted = self.public / "procedures" / "osdb-0906" / "index.html"
        self.assertTrue(quoted.is_file(), "osdb-0906 was not published")
        self.assertEqual(
            ps.load_page(self.public, quoted).find_all("p", "sample-banner"),
            [])
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                banners = page.find_all("p", "sample-banner")
                self.assertEqual(len(banners),
                                 1 if "sample-data" in item.tags else 0)


if __name__ == "__main__":
    unittest.main()
