"""Theme build tests: HTML scans of a sandbox build (site-theme,
site-search static scenarios, print-layout "The URL is text only").

Each class builds once. ``ShippedSiteTests`` builds the test collection
alone, and ``QuotedTitleSiteTests`` adds the quoted-title fixture to it;
``FixtureSiteTests`` builds the demo collection with the Org and Markdown
twin fixtures, and needs Emacs for their export. The catalogue's own
scans are in ``test_catalogue_integration.py``. Tests skip, naming the
missing tool or cache, as the other integration tests do.
"""

import difflib
import re
import tomllib
import unittest
import urllib.parse

import general_support as gs
import pipeline_support as ps
from pipeline_support import Content, Node, Page

BANNER = "Sample data — quantities not experimentally verified."
# The footer ends with the build time, YYYY-MM-DD HH:MM, in its time
# element.
FOOTER = re.compile(r"OrgSynDB · internal procedures · built "
                    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
ORIGIN = "http://127.0.0.1:8000"
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                     r"(Z|[+-]\d{2}:\d{2})$")
NAVIGATION = [("/procedures/", "Procedures"), ("/compounds/", "Compounds"),
              ("/help/", "Help")]
TABS = [("/procedures/", "All procedures"),
        ("/general-procedures/", "General procedures"),
        ("/reaction_types/", "Reaction types"), ("/tags/", "Tags"),
        ("/authors/", "Authors")]
SECTIONS = ["Summary", "Reagents", "Procedure", "Workup and Purification",
            "Characterization", "Notes", "Hazards and Waste Disposal",
            "References"]
REAGENT_HEADER = ["Reagent", "CAS", "MW (g/mol)", "Amount", "mmol", "Equiv"]
# "Products" takes the place of "Product" for a procedure with several.
PANEL_LABELS = ["Product", "Formula", "MW", "CAS", "SMILES",
                "Starting materials", "Reaction type", "Tags", "Authors",
                "Checked by", "Created", "Modified", "Precursors",
                "Used in"]
FONT_SUFFIXES = (".woff", ".woff2", ".ttf", ".otf", ".eot")
TAXONOMIES = {"reaction_types": "Reaction types", "tags": "Tags",
              "authors": "Authors"}
# The precursor of each procedure that has one, and the procedures that
# each used-in link leads to.
SHIPPED_PRECURSORS = {"OSDB-0002": "OSDB-0001", "OSDB-0005": "OSDB-0004",
                      "OSDB-0008": "OSDB-0007", "OSDB-0009": "OSDB-0004"}
SHIPPED_USED_IN = {"OSDB-0001": ["OSDB-0002"],
                   "OSDB-0004": ["OSDB-0005", "OSDB-0009"],
                   "OSDB-0007": ["OSDB-0008"]}


class SiteCase(ps.ThemeBuildCase):
    """Helpers shared by the build classes."""

    def by_id(self) -> dict[str, Content]:
        return {item.id: item for item in self.content()}

    def labels(self) -> dict[str, str]:
        return ps.reaction_labels(self.sandbox.app)

    def order_by_id(self) -> list[Content]:
        return sorted(self.content(), key=lambda item: item.id)

    def page_of(self, item: Content) -> Page:
        return ps.load_page(self.public, self.public / "procedures"
                            / item.slug / "index.html")

    def panel(self, page: Page) -> dict[str, ps.DefPair]:
        panel = page.find("dl", "metadata")
        self.assertIsNotNone(panel, f"{page.url} has no dl.metadata")
        return {pair.label: pair for pair in page.definition_pairs(panel)}

    def table_ids(self, page: Page) -> list[str]:
        """The ID cells of the body rows of the page's procedure table."""
        return [ps.row_cells(row)[0].norm()
                for row in ps.catalogue_rows(page)]

    def registry(self) -> dict[str, dict]:
        return ps.read_registry(self.sandbox)

    def precursors(self, item: Content) -> list[str]:
        """The IDs of the other published procedures that make a
        substrate of ``item``, by ID."""
        wanted = set(item.substrates)
        return sorted(other.id for other in self.content()
                      if other.id != item.id
                      and wanted & {e["compound"] for e in other.products})

    def used_in(self, item: Content) -> list[str]:
        """The IDs of the other published procedures that take a product
        of ``item`` as a substrate, by ID."""
        made = {e["compound"] for e in item.products}
        return sorted(other.id for other in self.content()
                      if other.id != item.id
                      and made & set(other.substrates))

    def expected_labels(self, item: Content) -> list[str]:
        data = item.data
        single = len(item.products) == 1
        compound = self.registry()[item.products[0]["compound"]]
        wanted = [("Product" if single else "Products", True),
                  ("Formula", single),
                  ("MW", single),
                  ("CAS", single and compound.get("cas")),
                  ("SMILES", single),
                  ("Starting materials", item.substrates),
                  ("Reaction type", data.get("reaction_types")),
                  ("Tags", data.get("tags")),
                  ("Authors", data.get("authors")),
                  ("Checked by", data.get("checked_by")
                   and data.get("status") != "checked"),
                  ("Created", data.get("date")),
                  ("Modified", data.get("lastmod")),
                  ("Precursors", self.precursors(item)),
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
        built = set()
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            with self.subTest(page=name):
                built.add(self.check_shell(page))
        self.assertEqual(len(built), 1, f"footers show {sorted(built)}")

    def check_shell(self, page: Page) -> str:
        """Check the page shell; return the footer's build time."""
        skip = page.find("a", "skip-link")
        self.assertIsNotNone(skip, "no a.skip-link")
        self.assertEqual(skip.attrs.get("href"), "#main")
        header = page.find("header", "site-header")
        self.assertIsNotNone(header, "no header.site-header")
        title = header.find("a", "site-title")
        self.assertIsNotNone(title, "no a.site-title")
        self.assertEqual((page.resolve(title.attrs.get("href", "")),
                          title.norm()), ("/", "OrgSynDB"))
        self.assertEqual(len(header.find_all("nav")), 1)
        nav = header.find("nav", aria_label="Site")
        self.assertIsNotNone(nav, "no nav[aria-label=Site]")
        self.assertEqual([(link.target, link.node.norm())
                          for link in page.links(nav)], NAVIGATION)
        mains = page.find_all("main")
        self.assertEqual(len(mains), 1)
        self.assertEqual(mains[0].attrs.get("id"), "main")
        footer = page.find("footer", "site-footer")
        self.assertIsNotNone(footer, "no footer.site-footer")
        self.assertRegex(footer.norm(), f"^{FOOTER.pattern}$")
        moments = footer.find_all("time")
        self.assertEqual(len(moments), 1, "not one time in the footer")
        built = moments[0].attrs.get("datetime", "")
        self.assertRegex(built, RFC3339)
        self.assertEqual(moments[0].norm(), f"{built[:10]} {built[11:16]}")
        order = [page.index_of(n) for n in (skip, header, mains[0], footer)]
        self.assertEqual(order, sorted(order), "shell elements out of order")
        self.check_header_search(page, header, nav)
        self.assertEqual(len(page.find_all("input", name="q")), 1,
                         "not exactly one input[name=q]")
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
        return built

    def check_header_search(self, page: Page, header: Node,
                            nav: Node) -> None:
        """The header holds the search form on every page; on a
        catalogue page it is the catalogue's (catalogue_support)."""
        catalogue = ps.is_catalogue_url(page.url)
        self.assertEqual(page.find("div", "catalogue") is not None,
                         catalogue, f"{page.url} is {'not ' * (not catalogue)}"
                         "a catalogue page")
        forms = header.find_all("form")
        self.assertEqual(len(forms), 1)
        form = forms[0]
        self.assertTrue(form.has_class("site-search"))
        self.assertEqual(form.attrs.get("role"), "search")
        self.assertEqual(form.attrs.get("method", "").lower(), "get")
        self.assertGreater(page.index_of(form), page.index_of(nav))
        self.assertFalse(form.within(nav))
        fields = form.find_all("input")
        self.assertEqual(len(fields), 1)
        self.assertEqual((fields[0].attrs.get("type"),
                          fields[0].attrs.get("name")), ("search", "q"))
        self.assertEqual("data-catalogue-search" in form.attrs, catalogue)
        if not catalogue:
            self.assertEqual(page.resolve(form.attrs.get("action", "")),
                             "/procedures/")
            self.assertEqual((fields[0].attrs.get("aria-label"),
                              fields[0].attrs.get("placeholder")),
                             ("Search procedures",
                              "Product, CAS, SMILES or keyword"))
        buttons = form.find_all("button")
        self.assertEqual(len(buttons), 1)
        self.assertEqual((buttons[0].attrs.get("type"), buttons[0].norm()),
                         ("submit", "Search"))
        self.assertNotIn("hidden", buttons[0].attrs)

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
                self.assertEqual([m for _, m in sheets],
                                 [None, "screen", "print"])
                for target, _ in sheets:
                    self.assertRegex(target, r"^/css/")
                    self.assertTrue(ps.target_file(self.public, target)
                                    .is_file(), target)

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
        for slug in ("osdb-0002", "osdb-0001", "osdb-0009"):
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
        self.assertIsNone(identity.find("span", "sign-off"))
        h1 = header.find("h1")
        key = header.find("dl", "key-facts")
        facts = header.find("p", "print-facts")
        actions = header.find("p", "actions")
        figure = header.find("figure", "structure")
        for node, what in ((h1, "h1"), (key, "dl.key-facts"),
                           (facts, "p.print-facts"), (actions, "p.actions"),
                           (figure, "figure.structure")):
            self.assertIsNotNone(node, f"header has no {what}")
        parts = [page.index_of(n)
                 for n in (identity, h1, key, facts, actions, figure)]
        self.assertEqual(parts, sorted(parts), "header parts out of order")
        self.assertIs(header.elements()[-1], figure)
        button = actions.find("button", "print-button")
        self.assertIsNotNone(button, "no button.print-button")
        self.assertEqual(button.attrs.get("type"), "button")
        self.assertIn("data-print", button.attrs)
        self.assertIn("hidden", button.attrs)
        self.assertEqual(button.norm(), "Print / Save as PDF")
        for outside in (h1, marked, key, figure):
            self.assertFalse(outside.within(article),
                             f"{outside.tag} lies inside the article")
        self.assertEqual(article.find_all("figure"), [])
        # The desktop columns wrap the details and body; reading and
        # indexing order still starts with the metadata panel.
        panel = article.find("dl", "metadata")
        self.assertIsNotNone(panel, "no dl.metadata")
        summary = page.heading("Summary")
        terms = article.find("span", "index-terms")
        index = article.find("span", data_smiles_index=True)
        for node, what in ((summary, "Summary heading"),
                           (terms, "index-terms element"),
                           (index, "SMILES index")):
            self.assertIsNotNone(node, f"article has no {what}")
        order = [page.index_of(n) for n in (panel, summary, terms, index)]
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
            ["Product", "Formula", "MW", "CAS", "SMILES",
             "Starting materials", "Reaction type", "Tags", "Authors",
             "Created", "Modified", "Precursors"])
        text = {label: pair.definition.norm()
                for label, pair in panel.items()}
        product = panel["Product"].definition.find_all("a", "compound")
        self.assertEqual([l.norm() for l in product],
                         ["Acetylsalicylic acid"])
        self.assertEqual(page.resolve(product[0].attrs["href"]),
                         "/compounds/acetylsalicylic-acid/")
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
        materials = panel["Starting materials"].definition
        links = materials.find_all("a", "compound")
        self.assertEqual([page.resolve(l.attrs["href"]) for l in links],
                         ["/compounds/salicylic-acid/",
                          "/compounds/acetic-anhydride/"])
        self.assertEqual([l.norm() for l in links],
                         ["Salicylic acid", "Acetic anhydride"])
        self.assertEqual(text["Starting materials"],
                         "Salicylic acid, Acetic anhydride")
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

    def test_key_facts_of_the_markdown_seed(self) -> None:
        """Scenario: Key facts and sign-off (the Markdown seed)."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0002" / "index.html")
        key = page.find("header", "procedure-header").find("dl", "key-facts")
        self.assertIsNotNone(key, "no dl.key-facts")
        pairs = page.definition_pairs(key)
        self.assertEqual([(p.label, p.definition.norm()) for p in pairs],
                         [("Scale", "20 mmol"), ("Yield", "75 %")])
        for pair in pairs:
            self.assertNotEqual(pair.gap, "")
            self.assertEqual(pair.gap.strip(), "")
        self.assertIsNone(page.find("span", "sign-off"))

    def test_a_product_named_like_its_procedure(self) -> None:
        """Scenario: A product named like its procedure is linked."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0001" / "index.html")
        self.assertEqual(page.find("main").find("h1").norm(),
                         "Salicylic acid")
        pair = self.panel(page)["Product"]
        links = pair.definition.find_all("a", "compound")
        self.assertEqual(len(links), 1)
        self.assertEqual(page.resolve(links[0].attrs["href"]),
                         "/compounds/salicylic-acid/")
        self.assertEqual(links[0].norm(), "Salicylic acid")
        terms = page.find("article", "procedure").find("span", "index-terms")
        self.assertIsNotNone(terms, "no span.index-terms")
        self.assertEqual(terms.norm(), "OSDB-0001 Salicylic acid C7H6O3 "
                         "69-72-7 OC(=O)c1ccccc1O")

    def test_linked_notes_on_a_procedure_page(self) -> None:
        """Scenario: Linked notes on a procedure page."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0003" / "index.html")
        article = page.find("article", "procedure")
        links = {l.node.norm(): l.href for l in page.links(article)
                 if l.href.startswith("#note-")}
        self.assertEqual(links, {"Note 1": "#note-1", "Note 2": "#note-2"})
        notes = page.following(page.heading("Notes"), "ol")
        self.assertIsNotNone(notes, "no list after the Notes heading")
        items = [n for n in notes.elements() if n.tag == "li"]
        for number, item in enumerate(items[:2], start=1):
            with self.subTest(note=number):
                anchor = item.find(id=f"note-{number}")
                self.assertIsNotNone(anchor, f"no #note-{number} in item")
        self.assertEqual(len(page.find_all(id="note-1")), 1)

    def test_panel_labels_follow_the_canonical_order(self) -> None:
        """Scenario: Panel labels follow the canonical order on every
        page."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                pairs = self.panel(page)
                shown = list(pairs)
                positions = [PANEL_LABELS.index(
                    "Product" if label == "Products" else label)
                    for label in shown]
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
                self.check_links(page, precursors, self.precursors(item),
                                 items)
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
        for ident in ("OSDB-0001", "OSDB-0002", "OSDB-0004", "OSDB-0005",
                      "OSDB-0007", "OSDB-0008", "OSDB-0009"):
            path = (self.public / "procedures" / ident.lower()
                    / "index.html")
            with self.subTest(procedure=ident):
                self.assertTrue(path.is_file(), f"{ident} not built")
                page = ps.load_page(self.public, path)
                precursors = [l.target for l in page.links()
                              if l.node.has_class("precursor")]
                used_in = [l.target for l in page.links()
                           if l.node.has_class("used-in")]
                self.assertEqual(
                    precursors,
                    [f"/procedures/{SHIPPED_PRECURSORS[ident].lower()}/"]
                    if ident in SHIPPED_PRECURSORS else [])
                self.assertEqual(
                    used_in,
                    [f"/procedures/{other.lower()}/"
                     for other in SHIPPED_USED_IN.get(ident, [])])
                self.assertFalse(precursors and used_in,
                                 "needs both a precursor and a used-in link")

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
        self.assertTrue(figure.within(
            page.find("header", "procedure-header")))
        self.assertFalse(figure.has_class("structure--placeholder"))
        image = figure.find("img")
        self.assertIsNotNone(image, "no img in the figure")
        self.assertEqual(page.resolve(image.attrs.get("src", "")),
                         "/structures/isopentyl-acetate.svg")
        self.assertTrue(
            (self.public / "structures" / "isopentyl-acetate.svg").is_file())
        self.assertFalse(
            (self.public / "structures" / "osdb-0003.svg").exists())
        self.assertEqual(image.attrs.get("alt"),
                         "Structure of Isopentyl acetate")
        path = self.public / "procedures" / "osdb-0002" / "index.html"
        page = ps.load_page(self.public, path)
        figure = page.find("figure", "structure")
        self.assertIsNotNone(figure, "no figure.structure")
        self.assertTrue(figure.within(
            page.find("header", "procedure-header")))
        self.assertTrue(figure.has_class("structure--placeholder"))
        slot = figure.find("div", "structure__slot")
        self.assertIsNotNone(slot, "no div.structure__slot")
        self.assertEqual(slot.norm(), "No structure image")
        self.assertEqual(page.find_all("img"), [])

    # --- general procedures --------------------------------------------

    def general_items(self) -> list[Content]:
        return [item for item in self.content() if item.is_general]

    def test_scope_table_of_a_general_procedure(self) -> None:
        """Scenario: Scope table of a general procedure."""
        general = self.general_items()
        self.assertEqual([item.id for item in general], ["OSDB-0009"])
        registry = self.registry()
        page = self.page_of(general[0])
        table = gs.check_scope_table(self, page, general[0], registry, "en",
                                     "Summary")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows[0], [
            "Entry", "Starting materials", "Products", "Yield", "Scale",
            "Time", "Note"])
        self.assertEqual(rows[1], [
            "1", "4-Acetylbiphenyl", "1-(Biphenyl-4-yl)ethanol", "90 %", "",
            "30 min", ""])
        self.assertEqual(rows[2], [
            "2", "Acetophenone", "1-Phenylethanol", "85 %", "", "20 min",
            ""])
        self.assertEqual(rows[3][:6], [
            "3", "4′-Bromoacetophenone", "1-(4-Bromophenyl)ethanol",
            "88 %", "5 mmol", "30 min"])
        self.assertEqual(rows[3][6], general[0].scope[2]["note"])
        links = page.links(table)
        self.assertEqual(
            [l.target for l in links],
            ["/compounds/4-acetylbiphenyl/",
             "/compounds/1-biphenyl-4-yl-ethanol/",
             "/compounds/acetophenone/", "/compounds/1-phenylethanol/",
             "/compounds/4-bromoacetophenone/",
             "/compounds/1-4-bromophenyl-ethanol/"])
        for link in links:
            self.assertTrue(ps.target_file(self.public, link.target)
                            .is_file(), link.target)

    def test_no_scope_table_on_a_specific_procedure(self) -> None:
        """Scenario: No scope table on a specific procedure."""
        checked = 0
        for item, page in self.procedure_pages():
            if item.is_general:
                continue
            checked += 1
            with self.subTest(procedure=item.id):
                self.assertIsNone(page.find("section", "scope"))
                self.assertIsNone(page.find("table", "scope-table"))
        self.assertEqual(checked, 8)

    def test_yields_of_a_general_procedure(self) -> None:
        """Scenario: Yields of a general procedure."""
        item = self.by_id()["OSDB-0009"]
        page = self.page_of(item)
        gs.check_key_facts(self, page, item, self.registry(), "en")
        key = page.find("header", "procedure-header").find("dl", "key-facts")
        self.assertEqual(
            [(p.label, p.definition.norm())
             for p in page.definition_pairs(key)],
            [("Scale", "10 mmol"), ("Yield", "85–90 %")])
        for pair in page.definition_pairs(key):
            self.assertNotEqual(pair.gap, "")
            self.assertEqual(pair.gap.strip(), "")

    def test_scheme_image_of_the_demo_general_procedure(self) -> None:
        """Scenario: Scheme image of a general procedure (the collection's
        procedure)."""
        item = self.by_id()["OSDB-0009"]
        page = self.page_of(item)
        gs.check_scheme_figure(self, page, item,
                               "structures/aryl-ketone-reduction.svg", "en")
        image = page.find("header", "procedure-header").find("img")
        self.assertEqual(
            image.attrs.get("alt"),
            "Scheme of Secondary benzylic alcohols by sodium borohydride "
            "reduction")
        self.assertTrue((self.public / "structures"
                         / "aryl-ketone-reduction.svg").is_file())

    def test_panel_and_links_of_a_general_procedure(self) -> None:
        """Requirement: General procedures (products and substrates over
        every entry)."""
        item = self.by_id()["OSDB-0009"]
        page = self.page_of(item)
        panel = self.panel(page)
        self.assertEqual(list(panel), [
            "Products", "Starting materials", "Reaction type", "Tags",
            "Authors", "Created", "Modified", "Precursors"])
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in panel["Products"].definition.find_all("a", "compound")],
            [("/compounds/1-biphenyl-4-yl-ethanol/",
              "1-(Biphenyl-4-yl)ethanol"),
             ("/compounds/1-phenylethanol/", "1-Phenylethanol"),
             ("/compounds/1-4-bromophenyl-ethanol/",
              "1-(4-Bromophenyl)ethanol")])
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in panel["Starting materials"].definition.find_all(
                 "a", "compound")],
            [("/compounds/4-acetylbiphenyl/", "4-Acetylbiphenyl"),
             ("/compounds/acetophenone/", "Acetophenone"),
             ("/compounds/4-bromoacetophenone/", "4′-Bromoacetophenone")])
        self.assertEqual(list(panel), self.expected_labels(item))
        self.assertEqual(
            [l.norm() for l in
             panel["Precursors"].definition.find_all("a", "precursor")],
            ["OSDB-0004 4-Acetylbiphenyl"])
        self.assertEqual(page.find_all("button", data_copy_smiles=True), [])

    def test_navigation_marks_the_current_section(self) -> None:
        """Scenario: Current section in the navigation."""
        within = {"/procedures/": "true"}
        cases = {"index.html": {},
                 "procedures/index.html": {"/procedures/": "page"},
                 "procedures/osdb-0001/index.html": within,
                 "general-procedures/index.html": within,
                 "procedures/osdb-0009/index.html": within,
                 "tags/index.html": within,
                 "authors/index.html": within,
                 "reaction_types/index.html": within,
                 "tags/sample-data/index.html": within,
                 "authors/a.-example/index.html": within,
                 "reaction_types/hydrolysis/index.html": within,
                 "compounds/index.html": {"/compounds/": "page"},
                 "compounds/salicylic-acid/index.html": {
                     "/compounds/": "true"},
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

    def listing_pages(self) -> dict[str, dict[str, str]]:
        """The pages that carry the tabs, with the tabs they mark."""
        cases = {"procedures/index.html": {"/procedures/": "page"},
                 "general-procedures/index.html":
                 {"/general-procedures/": "page"}}
        for taxonomy in TAXONOMIES:
            cases[f"{taxonomy}/index.html"] = {f"/{taxonomy}/": "page"}
            terms = sorted((self.public / taxonomy).glob("*/index.html"))
            self.assertTrue(terms, f"no {taxonomy} term pages")
            for path in terms:
                cases[str(path.relative_to(self.public))] = {
                    f"/{taxonomy}/": "true"}
        return cases

    def test_tabs_on_the_listing_pages(self) -> None:
        """Scenario: Tabs on the listing pages."""
        for name, expected in self.listing_pages().items():
            with self.subTest(page=name):
                page = ps.load_page(self.public, self.public / name)
                tabs = page.find("main").elements()[0]
                self.assertEqual((tabs.tag, tabs.classes,
                                  tabs.attrs.get("aria-label")),
                                 ("nav", ["section-tabs"], "Procedures"))
                links = page.links(tabs)
                self.assertEqual([(l.target, l.node.norm()) for l in links],
                                 TABS)
                marked = {l.target: l.node.attrs["aria-current"]
                          for l in links if "aria-current" in l.node.attrs}
                self.assertEqual(marked, expected)

    def test_no_tabs_elsewhere(self) -> None:
        """Scenario: No tabs elsewhere."""
        listing = set(self.listing_pages())
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            if name not in listing:
                with self.subTest(page=name):
                    self.assertIsNone(page.find("nav", "section-tabs"))

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
                listing = page.find("main").find("ul", "term-list")
                self.assertIsNotNone(listing, "no ul.term-list")
                entries = listing.find_all("li")
                expected = {}
                for term, count in self.term_counts()[taxonomy].items():
                    name = labels[term] if taxonomy == "reaction_types" \
                        else term
                    expected[name] = (term, count)
                shown = [page.links(entry)[0] for entry in entries]
                self.assertEqual([l.node.norm() for l in shown],
                                 sorted(expected))
                for entry, link in zip(entries, shown):
                    name = link.node.norm()
                    term, count = expected[name]
                    with self.subTest(term=name):
                        self.assertEqual(entry.norm(), f"{name} ({count})")
                        counter = entry.find("span", "count")
                        self.assertIsNotNone(counter, "no span.count")
                        self.assertEqual(counter.norm(), f"({count})")
                        self.assertIs(entry.elements()[0], link.node)
                        self.check_term_page(link.target, name, taxonomy,
                                             term)

    def check_term_page(self, target: str, name: str, taxonomy: str,
                        term: str) -> None:
        path = ps.target_file(self.public, target)
        self.assertTrue(path.is_file(), target)
        page = ps.load_page(self.public, path)
        self.assertEqual([t for lv, t in page.headings() if lv == 1], [name])
        table = page.find("table", "procedure-list")
        self.assertIsNotNone(table, f"{target} has no table.procedure-list")
        self.assertEqual([c.text for c in page.tables()[0].rows[0]],
                         ps.CATALOGUE_HEADER)
        wanted = sorted(i.id for i in self.content()
                        if term in i.data.get(taxonomy, []))
        self.assertEqual(self.table_ids(page), wanted)
        count = page.find("p", "catalogue-count")
        self.assertIsNotNone(count, "no p.catalogue-count")
        self.assertEqual(count.norm(), f"{len(wanted)} procedure"
                         + ("" if len(wanted) == 1 else "s"))

    def test_static_html_holds_the_content(self) -> None:
        """Scenario: Static HTML holds the content."""
        registry = self.registry()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                panel = page.find("dl", "metadata")
                self.assertIsNotNone(panel, "no dl.metadata")
                text = panel.norm()
                header = page.find("header", "procedure-header").norm()
                self.assertIn(item.id, header)
                single = len(item.products) == 1
                for entry in item.products:
                    compound = registry[entry["compound"]]
                    self.assertIn(compound["name"], text)
                    for value in (compound.get("cas"), compound["smiles"]):
                        if value and single:
                            self.assertIn(value, text)
                        elif value:
                            self.assertNotIn(value, text)
                self.assertIn(ps.yield_text(item, registry, "en"),
                              page.find("dl", "key-facts").norm())
                article = page.find("article", "procedure")
                self.assertEqual(
                    [n.norm() for n in article.find_all("h2")
                     if n.norm() in SECTIONS], SECTIONS)
                self.assertTrue(page.links(panel))
                data_print = page.find_all("button", data_print=True)
                data_copy = page.find_all("button", data_copy_smiles=True)
                self.assertEqual(len(data_print), 1)
                self.assertEqual(len(data_copy), 1 if single else 0)
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            for button in page.buttons():
                with self.subTest(page=name, button=button.norm()):
                    enhanced = ("data-print" in button.attrs
                                or "data-copy-smiles" in button.attrs)
                    self.assertEqual("hidden" in button.attrs, enhanced)
            catalogue = page.find("div", "catalogue")
            for button in () if catalogue is None else catalogue.find_all(
                    "button"):
                with self.subTest(page=name, catalogue_button=button.norm()):
                    hidden = [a for a in button.ancestors()
                              if a.within(catalogue)
                              and "data-catalogue-controls" in a.attrs
                              and "hidden" in a.attrs]
                    self.assertTrue(hidden, "the button is not inside a "
                                    "hidden catalogue control")

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

    def test_metadata_is_indexed_and_chrome_is_not(self) -> None:
        """Scenario: Metadata inside the body, chrome outside."""
        navigation = " ".join(text for _, text in NAVIGATION)
        registry = self.registry()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                bodies = page.indexed_bodies()
                self.assertEqual(len(bodies), 1)
                text = bodies[0].norm()
                compounds = [registry[e["compound"]] for e in item.products]
                expected = [item.id, *item.tags,
                            *item.data.get("authors", [])]
                expected += [registry[key]["name"]
                             for key in item.substrates]
                terms_text = [item.id]
                for compound in compounds:
                    expected += [compound["name"], compound["smiles"]]
                    terms_text += [compound["name"], compound["formula"]]
                    if compound.get("cas"):
                        expected.append(compound["cas"])
                        terms_text.append(compound["cas"])
                    terms_text.append(compound["smiles"])
                for value in expected:
                    self.assertIn(value, text)
                terms = bodies[0].find_all("span", "index-terms")
                self.assertEqual(len(terms), 1, "not one span.index-terms")
                self.assertIn("hidden", terms[0].attrs)
                self.assertEqual(terms[0].norm(), " ".join(terms_text))
                self.assertNotIn(BANNER, text)
                self.assertNotIn(navigation, text)
                self.assertNotIn(navigation.replace(" ", ""),
                                 text.replace(" ", ""))

    def test_filter_attributes_on_every_procedure_page(self) -> None:
        """Scenario: Filter attributes on every procedure page."""
        urls = set()
        for item, page in self.procedure_pages():
            urls.add(page.url)
            with self.subTest(procedure=item.id):
                filters = page.find_all(data_pagefind_filter=True)
                sorts = page.find_all(data_pagefind_sort=True)
                self.assertEqual(len(filters), 1)
                self.assertEqual(len(sorts), 1)
                self.assertIs(filters[0], sorts[0])
                element = filters[0]
                self.assertEqual(element.attrs["data-pagefind-filter"], "id")
                self.assertEqual(element.attrs["data-pagefind-sort"], "id")
                self.assertEqual(element.attrs.get("data-pagefind-meta"),
                                 "id")
                self.assertTrue(element.within(
                    page.find("header", "procedure-header")))
                self.assertEqual(element.norm(), item.id)
        self.assertTrue(urls)
        for path, page in self.pages():
            if page.url not in urls:
                with self.subTest(page=str(path.relative_to(self.public))):
                    self.assertEqual(
                        page.find_all(data_pagefind_filter=True), [])
                    self.assertEqual(
                        page.find_all(data_pagefind_sort=True), [])

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
                registry = self.registry()
                self.assertEqual(
                    index.attrs["data-smiles-index"],
                    " ".join(ps.smiles_suffixes(
                        registry[e["compound"]]["smiles"])
                        for e in item.products))
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


class GeneralFixtureSiteTests(SiteCase):
    """The test collection plus the general baseline
    ``tests/fixtures/general/OSDB-0140-general.md``, which sets no
    scheme image and whose products' compounds include one with a
    structure image."""

    @classmethod
    def prepare(cls) -> None:
        ps.put_general_fixture(cls.sandbox)

    def item(self) -> Content:
        return self.by_id()["OSDB-0140"]

    def test_a_general_procedure_without_a_scheme_shows_the_placeholder(
            self) -> None:
        """Scenario: Scheme image of a general procedure (the
        placeholder)."""
        page = self.page_of(self.item())
        header = page.find("header", "procedure-header")
        figures = header.find_all("figure", "structure")
        self.assertEqual(len(figures), 1)
        self.assertIs(header.elements()[-1], figures[0])
        self.assertTrue(figures[0].has_class("structure--placeholder"))
        slot = figures[0].find("div", "structure__slot")
        self.assertIsNotNone(slot, "no div.structure__slot")
        self.assertEqual(slot.norm(), "No structure image")
        self.assertEqual(header.find_all("img"), [])
        registry = self.registry()
        self.assertTrue(registry["ethyl-acetate"].get("structure_image"),
                        "no product sets a structure image")
        demo = self.page_of(self.by_id()["OSDB-0009"])
        figure = demo.find("header", "procedure-header").find(
            "figure", "structure")
        self.assertFalse(figure.has_class("structure--placeholder"))
        self.assertEqual(figure.find("img").attrs.get("alt"),
                         "Scheme of " + self.by_id()["OSDB-0009"].title)

    def test_the_scope_table_with_every_column_and_an_image(self) -> None:
        """Scenario: Scope table of a general procedure (the fixture)."""
        item = self.item()
        page = self.page_of(item)
        table = gs.check_scope_table(self, page, item, self.registry(),
                                     "en", "Summary")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows, [
            ["Entry", "Starting materials", "Products", "Yield", "Scale",
             "Time", "Temperature", "Note"],
            ["1", "Acetic acid, Ethanol", "Ethyl acetate", "85 %",
             "20 mmol", "2 h", "80 °C", "Reflux."],
            ["2", "Acetic acid", "Benzyl acetate, Propyl acetate",
             "78 %, 64.5 %", "", "", "", ""],
            ["3", "Ethanol", "Methyl benzoate", "72.5 %", "", "", "", ""]])
        images = table.find_all("img", "scope-structure")
        self.assertEqual([(i.attrs.get("alt"), page.resolve(i.attrs["src"]))
                          for i in images],
                         [("Structure of Ethyl acetate",
                           "/structures/ethyl-acetate.svg")])
        self.assertTrue((self.public / "structures"
                         / "ethyl-acetate.svg").is_file())

    def test_the_yield_is_the_range_of_all_entries(self) -> None:
        """Scenario: Yields of a general procedure (the fixture)."""
        item = self.item()
        page = self.page_of(item)
        key = page.find("header", "procedure-header").find("dl", "key-facts")
        self.assertEqual(
            [(p.label, p.definition.norm())
             for p in page.definition_pairs(key)],
            [("Scale", "25 mmol"), ("Yield", "64.5–85 %")])

    def test_the_panel_names_the_union_over_the_entries(self) -> None:
        """Requirement: General procedures (panel, union in order of first
        appearance)."""
        item = self.item()
        page = self.page_of(item)
        panel = self.panel(page)
        self.assertEqual(list(panel), self.expected_labels(item))
        self.assertEqual(
            panel["Products"].definition.norm(),
            "Ethyl acetate, Benzyl acetate, Propyl acetate, "
            "Methyl benzoate")
        self.assertEqual(panel["Starting materials"].definition.norm(),
                         "Acetic acid, Ethanol")
        for link in page.links(panel["Products"].definition):
            self.assertTrue(ps.target_file(self.public, link.target)
                            .is_file(), link.target)

    def test_the_index_follows_the_union_of_the_entries(self) -> None:
        """Requirement: General procedures (index terms and SMILES
        index)."""
        item = self.item()
        page = self.page_of(item)
        registry = self.registry()
        article = page.find("article", "procedure")
        terms = ["OSDB-0140"]
        for key in ("ethyl-acetate", "benzyl-acetate", "propyl-acetate",
                    "methyl-benzoate"):
            compound = registry[key]
            terms += [compound["name"], compound["formula"],
                      compound["cas"], compound["smiles"]]
        self.assertEqual(article.find("span", "index-terms").norm(),
                         " ".join(terms))
        self.assertEqual(
            article.find("span", data_smiles_index=True)
            .attrs["data-smiles-index"],
            " ".join(ps.smiles_suffixes(registry[key]["smiles"])
                     for key in ("ethyl-acetate", "benzyl-acetate",
                                 "propyl-acetate", "methyl-benzoate")))

    def test_the_compound_pages_name_the_entry(self) -> None:
        """Requirement: Compound pages (entries of a general procedure)."""
        cases = {
            "ethyl-acetate": ["OSDB-0140 Acetate Esters · entry 1 · 85 % · "
                              "draft"],
            "benzyl-acetate": ["OSDB-0140 Acetate Esters · entry 2 · 78 % · "
                               "draft"],
            "propyl-acetate": ["OSDB-0140 Acetate Esters · entry 2 · "
                               "64.5 % · draft"],
            "methyl-benzoate": ["OSDB-0140 Acetate Esters · entry 3 · "
                                "72.5 % · draft"]}
        for key, expected in cases.items():
            page = ps.load_page(self.public, self.public / "compounds" / key
                                / "index.html")
            made = page.find("section", "compound-made-by")
            with self.subTest(compound=key):
                self.assertIsNotNone(made, "no section.compound-made-by")
                self.assertEqual([li.norm() for li in made.find_all("li")],
                                 expected)
        used = ps.load_page(self.public, self.public / "compounds"
                            / "acetic-acid" / "index.html").find(
            "section", "compound-used-in")
        self.assertIn("OSDB-0140 Acetate Esters · draft",
                      [li.norm() for li in used.find_all("li")])
        self.assertEqual(
            [li.norm() for li in used.find_all("li")].count(
                "OSDB-0140 Acetate Esters · draft"), 1,
            "once for each procedure, however many entries use it")


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


class TwoProductSiteTests(SiteCase):
    """The test collection plus the two-product fixture."""

    FIXTURES = ("OSDB-0907-two-products.md",)

    def page_0907(self) -> Page:
        path = self.public / "procedures" / "osdb-0907" / "index.html"
        self.assertTrue(path.is_file(), "osdb-0907 was not published")
        return ps.load_page(self.public, path)

    def test_yields_of_two_products(self) -> None:
        """Scenario: Yields of two products."""
        page = self.page_0907()
        key = page.find("header", "procedure-header").find("dl", "key-facts")
        self.assertIsNotNone(key, "no dl.key-facts")
        self.assertEqual(
            [(p.label, p.definition.norm())
             for p in page.definition_pairs(key)],
            [("Scale", "10 mmol"),
             ("Yield", "45 % trans-Stilbene, 30 % cis-Stilbene")])

    def test_panel_of_a_procedure_with_two_products(self) -> None:
        """Scenario: Panel of a procedure with two products."""
        page = self.page_0907()
        panel = self.panel(page)
        self.assertEqual(list(panel), [
            "Products", "Reaction type", "Tags", "Authors", "Created",
            "Modified"])
        links = panel["Products"].definition.find_all("a", "compound")
        self.assertEqual([(page.resolve(l.attrs["href"]), l.norm())
                          for l in links],
                         [("/compounds/trans-stilbene/", "trans-Stilbene"),
                          ("/compounds/cis-stilbene/", "cis-Stilbene")])
        self.assertEqual(panel["Products"].definition.norm(),
                         "trans-Stilbene, cis-Stilbene")
        self.assertEqual(self.expected_labels(
            self.by_id()["OSDB-0907"]), list(panel))

    def test_one_figure_per_product_with_an_image(self) -> None:
        """Scenario: One figure per product with an image."""
        page = self.page_0907()
        header = page.find("header", "procedure-header")
        figures = header.find_all("figure", "structure")
        self.assertEqual(len(figures), 1)
        self.assertIs(header.elements()[-1], figures[0])
        self.assertFalse(figures[0].has_class("structure--placeholder"))
        images = figures[0].find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].attrs.get("alt"),
                         "Structure of trans-Stilbene")
        self.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/structures/trans-stilbene.svg")
        self.assertTrue((self.public / "structures"
                         / "trans-stilbene.svg").is_file())
        self.assertEqual(page.find_all("figure", "structure--placeholder"),
                         [])

    def test_the_index_follows_both_products(self) -> None:
        """Scenario: Metadata inside the body (two products)."""
        page = self.page_0907()
        article = page.find("article", "procedure")
        terms = article.find("span", "index-terms")
        self.assertEqual(
            terms.norm(),
            "OSDB-0907 trans-Stilbene C14H12 103-30-0 "
            "c1ccc(cc1)/C=C/c1ccccc1 cis-Stilbene C14H12 645-49-8 "
            "c1ccc(cc1)/C=C\\c1ccccc1")
        self.assertEqual(page.find_all("button", data_copy_smiles=True), [])

    def test_the_compound_pages_give_each_yield(self) -> None:
        """Scenario: Made by and used in (two products)."""
        for key, name, yield_text in (("trans-stilbene", "trans-Stilbene",
                                       "45 %"),
                                      ("cis-stilbene", "cis-Stilbene",
                                       "30 %")):
            path = self.public / "compounds" / key / "index.html"
            with self.subTest(compound=key):
                self.assertTrue(path.is_file(), f"{key} has no page")
                page = ps.load_page(self.public, path)
                section = page.find("section", "compound-made-by")
                self.assertIsNotNone(section, "no section.compound-made-by")
                self.assertEqual(
                    [li.norm() for li in section.find_all("li")],
                    [f"OSDB-0907 Stilbene isomers · {yield_text} · draft"])
                self.assertIsNone(page.find("section",
                                            "compound-used-in"))
                self.assertEqual(page.find("main").find("h1").norm(), name)
        cis = ps.load_page(self.public, self.public / "compounds"
                           / "cis-stilbene" / "index.html")
        self.assertEqual(cis.find_all("figure"), [])
        trans = ps.load_page(self.public, self.public / "compounds"
                             / "trans-stilbene" / "index.html")
        image = trans.find("figure", "structure").find("img")
        self.assertEqual(image.attrs.get("alt"),
                         "Structure of trans-Stilbene")
        self.assertEqual(trans.resolve(image.attrs["src"]),
                         "/structures/trans-stilbene.svg")


class SecondRouteSiteTests(SiteCase):
    """The test collection plus a second route to salicylic acid."""

    FIXTURES = ("OSDB-0908-second-route.md",)

    def links(self, ident: str, relation: str) -> list[str]:
        path = self.public / "procedures" / ident.lower() / "index.html"
        self.assertTrue(path.is_file(), f"{ident} was not published")
        page = ps.load_page(self.public, path)
        return [l.target for l in page.links() if l.node.has_class(relation)]

    def test_a_second_route(self) -> None:
        """Scenario: A second route."""
        self.assertEqual(self.links("OSDB-0002", "precursor"),
                         ["/procedures/osdb-0001/",
                          "/procedures/osdb-0908/"])
        self.assertEqual(self.links("OSDB-0908", "used-in"),
                         ["/procedures/osdb-0002/"])
        self.assertEqual(self.links("OSDB-0908", "precursor"), [])
        self.assertEqual(self.links("OSDB-0001", "used-in"),
                         ["/procedures/osdb-0002/"])

    def test_the_precursor_text_names_the_id_and_title(self) -> None:
        """Scenario: A second route (link texts)."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0002" / "index.html")
        links = page.find_all("a", "precursor")
        self.assertEqual([l.norm() for l in links],
                         ["OSDB-0001 Salicylic acid",
                          "OSDB-0908 Salicylic acid, second route"])

    def test_the_compound_page_lists_both_routes(self) -> None:
        """Scenario: Made by and used in (a second route)."""
        page = ps.load_page(self.public, self.public / "compounds"
                            / "salicylic-acid" / "index.html")
        made = page.find("section", "compound-made-by")
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylic acid · 80 % · draft",
             "OSDB-0908 Salicylic acid, second route · 70 % · draft"])
        used = page.find("section", "compound-used-in")
        self.assertEqual([li.norm() for li in used.find_all("li")],
                         ["OSDB-0002 Aspirin (acetylsalicylic acid) · "
                          "draft"])

    def test_the_panel_names_the_starting_material(self) -> None:
        """Scenario: A second route (starting materials)."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0908" / "index.html")
        panel = self.panel(page)
        self.assertEqual(panel["Starting materials"].definition.norm(),
                         "Phenyl salicylate")
        self.assertEqual(
            [page.resolve(l.attrs["href"]) for l in
             panel["Starting materials"].definition.find_all("a")],
            ["/compounds/phenyl-salicylate/"])
        self.assertEqual(list(panel), self.expected_labels(
            self.by_id()["OSDB-0908"]))


if __name__ == "__main__":
    unittest.main()
