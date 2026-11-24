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
from pathlib import Path

import field_support as fs
import general_support as gs
import navigation_support as ns
import pipeline_support as ps
import sequence_support as ss
import widget_support as ws
from pipeline_support import Content, Node, Page, Sequence

BANNER = "Sample data — quantities not experimentally verified."
# The footer ends with the build time, YYYY-MM-DD HH:MM, in its time
# element.
FOOTER = re.compile(r"OrgSynDB · internal procedures · built "
                    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
ORIGIN = "http://127.0.0.1:8000"
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                     r"(Z|[+-]\d{2}:\d{2})$")
TABS = [("/procedures/", "All procedures"),
        ("/general-procedures/", "General procedures"),
        ("/reaction_types/", "Reaction types"), ("/tags/", "Tags"),
        ("/authors/", "Authors")]
REAGENT_HEADER = ["Reagent", "CAS", "MW (g/mol)", "Amount", "mmol", "Equiv"]
# "Products" takes the place of "Product" for a procedure with several.
# The labels of the compound widget, then those of the details widget,
# then those of the context widget.
COMPOUND_LABELS = ["Product", "Formula", "MW", "CAS", "SMILES"]
DETAILS_LABELS = ["Reaction type", "Tags", "Authors", "Checked by",
                  "Created", "Modified"]
CONTEXT_LABELS = ["Starting materials", "Precursors", "Used in",
                  "Sequences"]
PANEL_LABELS = [*COMPOUND_LABELS, *DETAILS_LABELS, *CONTEXT_LABELS]
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


class SiteCase(fs.ProcedureFieldsMixin, ps.ThemeBuildCase):
    """Helpers shared by the build classes."""

    def canonical_labels(self) -> list[str]:
        """The panel's labels in their canonical order, the declared
        procedure fields' shown labels standing between ``Checked by``
        and ``Created``."""
        at = PANEL_LABELS.index("Created")
        return [*PANEL_LABELS[:at],
                *(field.label for field in self.procedure_fields()),
                *PANEL_LABELS[at:]]

    def by_id(self) -> dict[str, Content]:
        return {item.id: item for item in self.content()}

    @property
    def site(self) -> Path:
        return self.sandbox.app / "site"

    @property
    def lab(self) -> bool:
        return getattr(self, "ENV", {}).get("ORGSYNDB_LAB") == "true"

    def navigation(self) -> list[ns.Entry]:
        """The navigation this build's pages show."""
        return ns.expected(self.site, "en", self.lab)

    def labels(self) -> dict[str, str]:
        return ps.reaction_labels(self.sandbox.root)

    def order_by_id(self) -> list[Content]:
        return sorted(self.content(), key=lambda item: item.id)

    def page_of(self, item: Content) -> Page:
        return ps.load_page(self.public, self.public / "procedures"
                            / item.slug / "index.html")

    def panel(self, page: Page) -> dict[str, ps.DefPair]:
        """The metadata panel: the pairs of every list of the details
        wrapper, in document order."""
        pairs = page.panel_pairs()
        self.assertTrue(pairs, f"{page.url} has no metadata panel")
        return {pair.label: pair for pair in pairs}

    def table_ids(self, page: Page) -> list[str]:
        """The ID cells of the body rows of the page's procedure table."""
        return [ps.row_cells(row)[0].norm()
                for row in ps.catalogue_rows(page)]

    def registry(self) -> dict[str, dict]:
        return ps.read_registry(self.sandbox)

    def sequences(self) -> list[Sequence]:
        """The sequences the build published, one per ID."""
        return ps.read_sequences(self.sandbox, self.LOCALE)

    def sequences_of(self, item: Content) -> list[str]:
        """The IDs of the sequences that have ``item`` as a step, by
        ID."""
        return [s.id for s in ss.sequences_of(item, self.sequences())]

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
        declared = [(label, True)
                    for label, _ in self.declared_pairs(data)]
        wanted = [("Product" if single else "Products", True),
                  ("Formula", single),
                  ("MW", single),
                  ("CAS", single and compound.get("cas")),
                  ("SMILES", single),
                  ("Reaction type", data.get("reaction_types")),
                  ("Tags", data.get("tags")),
                  ("Authors", data.get("authors")),
                  ("Checked by", data.get("checked_by")
                   and data.get("status") != "checked"),
                  *declared,
                  ("Created", data.get("date")),
                  ("Modified", data.get("lastmod")),
                  ("Starting materials", item.substrates),
                  ("Precursors", self.precursors(item)),
                  ("Used in", self.used_in(item)),
                  ("Sequences", self.sequences_of(item))]
        return [label for label, present in wanted if present]

    def expected_widgets(self, item: Content) -> list[tuple[str, list[str]]]:
        """The title and the labels of each details widget of ``item``:
        the compound widget always, the others when they have a pair."""
        labels = self.expected_labels(item)
        compound = [l for l in labels if l in [*COMPOUND_LABELS, "Products"]]
        context = [l for l in labels if l in CONTEXT_LABELS]
        details = [l for l in labels if l not in compound + context]
        found = [("Compound" if len(item.products) == 1 else "Products",
                  compound)]
        found += [(title, shown) for title, shown in (
            ("Details", details), ("Synthesis context", context)) if shown]
        return found

    def widgets_of(self, page: Page) -> list[tuple[str, list[str]]]:
        """The title and the labels of each details widget of ``page``,
        after the checks of its markup."""
        return [(w.title, w.labels) for w in ws.details_widgets(self, page)]


class ShippedSiteTests(SiteCase):
    """The shipped procedures, built with the theme."""

    # --- site-theme -------------------------------------------------------

    def test_no_lab_on_the_home_page(self) -> None:
        """Scenario: The lab's summary on the home page (without the
        lab)."""
        page = ps.load_page(self.public, self.public / "index.html")
        self.assertEqual(page.find_all("section", "home-lab"), [])
        self.assertEqual(page.find_all("iframe"), [])

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

    def test_the_site_script_and_the_sidebar_toggle(self) -> None:
        text = ns.strings(self.site, "en")["nav_toggle"]
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                scripts = page.find_all("script")
                self.assertTrue(scripts, "no script")
                self.assertRegex(page.resolve(scripts[0].get("src", "")),
                                 r"^/js/site\.")
                self.assertEqual(scripts[0].parent.tag, "head")
                self.assertNotIn("defer", scripts[0].attrs)
                header = page.find("header", "site-header")
                toggles = header.find_all("button", data_sidebar_toggle=True)
                self.assertEqual(len(toggles), 1)
                self.assertEqual((toggles[0].get("type"),
                                  toggles[0].get("aria-expanded"),
                                  toggles[0].norm()),
                                 ("button", "true", text))
                brand = toggles[0].parent
                self.assertTrue(brand.has_class("site-brand"))
                self.assertEqual([(n.tag, n.classes[:1])
                                  for n in brand.elements()],
                                 [("button", ["sidebar-toggle"]),
                                  ("a", ["site-title"])])

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
        self.assertEqual(ns.shown(page, nav), self.navigation())
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
                              "Product, CAS or SMILES"))
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
        for node, what in ((h1, "h1"), (key, "dl.key-facts"),
                           (facts, "p.print-facts"), (actions, "p.actions")):
            self.assertIsNotNone(node, f"header has no {what}")
        parts = [page.index_of(n)
                 for n in (identity, h1, key, facts, actions)]
        self.assertEqual(parts, sorted(parts), "header parts out of order")
        self.assertIs(header.elements()[-1], actions)
        self.assertEqual(header.find_all("figure"), [])
        button = actions.find("button", "print-button")
        self.assertIsNotNone(button, "no button.print-button")
        self.assertEqual(button.attrs.get("type"), "button")
        self.assertIn("data-print", button.attrs)
        self.assertIn("hidden", button.attrs)
        self.assertEqual(button.norm(), "Print / Save as PDF")
        for outside in (h1, marked, key):
            self.assertFalse(outside.within(article),
                             f"{outside.tag} lies inside the article")
        # The details wrapper starts the article, so reading and indexing
        # order begin with the metadata panel.
        panel = article.find("div", "procedure-details")
        self.assertIsNotNone(panel, "no div.procedure-details")
        self.assertIs(article.elements()[0], panel)
        self.assertTrue(page.panel_lists(), "no dl.metadata in the details")
        for lists in page.panel_lists():
            self.assertTrue(lists.within(panel))
        self.assertTrue(
            ws.compound_widget(self, page).node.within(article))
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
            self.widgets_of(page),
            [("Compound", ["Product", "Formula", "MW", "CAS", "SMILES"]),
             ("Details", ["Reaction type", "Tags", "Authors",
                          "Lab notebook", "Project", "Working time",
                          "Inert atmosphere", "Created", "Modified"]),
             ("Synthesis context",
              ["Starting materials", "Precursors", "Sequences"])])
        self.assertEqual(
            list(panel),
            ["Product", "Formula", "MW", "CAS", "SMILES",
             "Reaction type", "Tags", "Authors",
             "Lab notebook", "Project", "Working time", "Inert atmosphere",
             "Created", "Modified", "Starting materials", "Precursors",
             "Sequences"])
        text = {label: pair.definition.norm()
                for label, pair in panel.items()}
        self.assertEqual(
            [text[label] for label in ("Lab notebook", "Project",
                                       "Working time", "Inert atmosphere")],
            ["AE-1/2", "Teaching › First-year practical", "2.5 h", "No"])
        self.assertEqual(
            [(label, text[label]) for label in panel
             if label in ("Lab notebook", "Project", "Working time",
                          "Inert atmosphere")],
            self.declared_pairs(self.by_id()["OSDB-0002"].data))
        product = panel["Product"].definition.find_all("a", "compound")
        self.assertEqual([l.norm() for l in product],
                         ["Acetylsalicylic acid"])
        self.assertEqual(page.resolve(product[0].attrs["href"]),
                         "/lab/registry/substances/acetylsalicylic-acid/")
        self.assertEqual(text["Product"],
                         self.linked("acetylsalicylic-acid"))
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
                         ["/lab/registry/substances/salicylic-acid/",
                          "/lab/registry/substances/acetic-anhydride/"])
        self.assertEqual([l.norm() for l in links],
                         ["Salicylic acid", "Acetic anhydride"])
        self.assertEqual(
            text["Starting materials"],
            ", ".join(self.linked(key)
                      for key in ("salicylic-acid", "acetic-anhydride")))
        for label, texts in (("Reaction type", ["Acylation"]),
                             ("Tags", ["sample-data", "acetylation"]),
                             ("Authors", ["Katrin Lehmann", "Anna Schmidt"])):
            links = page.links(panel[label].definition)
            self.assertEqual([l.node.norm() for l in links], texts, label)
            for link in links:
                term = ps.load_page(self.public, ps.target_file(
                    self.public, link.target))
                self.assertEqual(
                    [t for lv, t in term.headings() if lv == 1],
                    [link.node.norm()])
        self.assertEqual(
            [page.resolve(l.attrs["href"]) for l in
             panel["Authors"].definition.find_all("a")],
            ["/authors/klehmann/", "/authors/aschmidt/"])
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
        sequence = panel["Sequences"].definition.find_all("a", "sequence")
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm()) for l in sequence],
            [("/sequences/seq-0001/", "Aspirin from oil of wintergreen")])
        for label, pair in panel.items():
            with self.subTest(label=label):
                self.assertNotEqual(pair.gap, "")
                self.assertEqual(pair.gap.strip(), "")

    def test_the_compound_rows_follow_the_labs_order(self) -> None:
        """Scenario: Compound rows in the lab's order."""
        page = self.page_of(self.by_id()["OSDB-0002"])
        shown = [l for l in ws.compound_widget(self, page).labels
                 if l != "Product"]
        self.assertEqual(shown, ["Formula", "MW", "CAS", "SMILES"])
        lab = {"Formula": "Formula", "MW": "Molar mass",
               "CAS": "CAS number", "SMILES": "SMILES"}
        rows = ws.lab_row_labels()
        for label in lab.values():
            self.assertIn(label, rows, "the lab template lost a row")
        self.assertEqual(sorted(shown, key=lambda l: rows.index(lab[l])),
                         shown)

    def test_the_context_widget_exists_only_with_a_pair(self) -> None:
        """Scenario: No context widget without links (every page)."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                widgets = ws.details_widgets(self, page)
                titles = [w.title for w in widgets]
                self.assertIn(titles[0], ("Compound", "Products"))
                self.assertEqual(
                    [t for t in titles if t in ("Compound", "Products")],
                    titles[:1], "not one compound widget, first")
                pairs = [l for w in widgets for l in w.labels]
                has_pair = any(l in CONTEXT_LABELS for l in pairs)
                self.assertEqual("Synthesis context" in titles, has_pair)
                if has_pair:
                    self.assertEqual(titles[-1], "Synthesis context")
                    self.assertTrue(all(
                        l in CONTEXT_LABELS for l in widgets[-1].labels))
                self.assertEqual(len(page.panel_lists()), len(widgets))

    def test_notes_after_every_compound_link(self) -> None:
        """Scenario: Notes after every compound link. Every page is
        scanned, a superset of the procedure pages, the sequence pages
        and the sequence directory, so that a stray note or link shows
        too."""
        beside = [f.key for f in self.compound_fields() if f.beside]
        self.assertEqual(beside, ["article_number", "short_name"])
        noted: dict[str, int] = {}
        for path, page in self.pages():
            where = path.relative_to(self.public).as_posix()
            notes = self.check_notes(page, page.root)
            self.assertEqual(
                [n.text() for n in page.find_all("span", "compound-beside")],
                [note for note in notes if note is not None], where)
            noted[where] = len(notes)
        for where in ("procedures/osdb-0002/index.html",
                      "procedures/osdb-0009/index.html",
                      "sequences/seq-0001/index.html",
                      "sequences/seq-0002/index.html",
                      "sequences/index.html"):
            with self.subTest(page=where):
                self.assertGreater(noted[where], 0)

    def test_notes_in_each_place_a_compound_is_linked(self) -> None:
        """Scenario: Notes after every compound link (the metadata panel,
        the scope table, the sequence scheme and the sequence
        directory)."""
        registry, fields = self.registry(), self.compound_fields()
        page = self.page_of(self.by_id()["OSDB-0002"])
        panel = self.panel(page)
        expected = {"Product": ["(CH-0010, ASA)"],
                    "Starting materials": [None, "(Ac2O)"]}
        for label, wanted in expected.items():
            with self.subTest(label=label):
                notes = self.check_notes(page, panel[label].definition)
                self.assertEqual(notes, wanted)
        page = self.page_of(self.by_id()["OSDB-0009"])
        table = page.find("table", "scope-table")
        notes = self.check_notes(page, table)
        self.assertTrue(any(notes), notes)
        sequence = self.sequences()[0]
        page = ps.load_page(self.public, sequence.page_file(self.public))
        scheme = page.find("figure", "sequence-scheme")
        notes = self.check_notes(page, scheme)
        self.assertTrue(any(notes), notes)
        page = ps.load_page(self.public,
                            self.public / "sequences" / "index.html")
        table = page.find("table", "sequence-table")
        notes = self.check_notes(page, table)
        self.assertEqual(len(notes), len(self.sequences()))
        self.assertEqual(
            [n.text() for n in table.find_all("span", "compound-beside")],
            [fs.beside_note(fields, registry[s.target], "en")
             for s in self.sequences()])

    def test_the_starting_materials_of_the_markdown_seed_have_notes(
            self) -> None:
        """Scenario: Notes after every compound link (the stated
        value)."""
        page = self.page_of(self.by_id()["OSDB-0002"])
        panel = self.panel(page)
        self.assertEqual(panel["Product"].definition.norm(),
                         "Acetylsalicylic acid (CH-0010, ASA)")
        self.assertEqual(panel["Starting materials"].definition.norm(),
                         "Salicylic acid, Acetic anhydride (Ac2O)")

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
                         "/lab/registry/substances/salicylic-acid/")
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
                canonical = self.canonical_labels()
                positions = [canonical.index(
                    "Product" if label == "Products" else label)
                    for label in shown]
                self.assertEqual(positions, sorted(set(positions)))
                self.assertEqual(shown, self.expected_labels(item))
                self.assertEqual(self.widgets_of(page),
                                 self.expected_widgets(item))
                for label, pair in pairs.items():
                    self.assertNotEqual(pair.gap, "", label)
                    self.assertEqual(pair.gap.strip(), "", label)

    def test_declared_fields_are_written_as_the_field_data_says(
            self) -> None:
        """Scenario: Panel labels follow the canonical order on every
        page (the written values)."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                declared = {label for label, _ in
                            self.declared_pairs(item.data)}
                self.assertEqual(
                    [(label, pair.definition.norm())
                     for label, pair in self.panel(page).items()
                     if label in declared],
                    self.declared_pairs(item.data))
                self.assertTrue(declared, "the procedure sets no field")

    def test_the_notebook_links_the_journal(self) -> None:
        """Scenario: The notebook links the journal."""
        page = self.page_of(self.by_id()["OSDB-0002"])
        panel = self.panel(page)
        links = panel["Lab notebook"].definition.find_all("a")
        self.assertEqual([(page.resolve(l.attrs["href"]), l.norm())
                          for l in links],
                         [("/lab/journal/AE-1/", "AE-1/2")])
        self.assertEqual(panel["Lab notebook"].definition.norm(), "AE-1/2")
        for label in ("Project", "Working time", "Inert atmosphere"):
            with self.subTest(label=label):
                self.assertEqual(panel[label].definition.find_all("a"), [])

    def test_every_notebook_value_links_the_notebook_of_its_code(
            self) -> None:
        """Requirement: Metadata panel (the code is the value before the
        last `/`)."""
        checked = 0
        for item in self.order_by_id():
            value = item.data.get("notebook")
            if value is None:
                continue
            with self.subTest(procedure=item.id):
                page = self.page_of(item)
                links = self.panel(page)["Lab notebook"].definition \
                    .find_all("a")
                self.assertEqual(
                    [(page.resolve(l.attrs["href"]), l.norm())
                     for l in links],
                    [(f"/lab/journal/{value.rsplit('/', 1)[0]}/", value)])
                self.assertFalse(links[0].attrs["href"].startswith("/"))
                checked += 1
        self.assertGreaterEqual(checked, 9)

    def test_a_field_a_procedure_does_not_set_is_not_shown(self) -> None:
        """Requirement: Metadata panel (each pair present only when the
        field is set)."""
        by_id = self.by_id()
        third = self.panel(self.page_of(by_id["OSDB-0003"]))
        self.assertEqual(third["Working time"].definition.norm(), "4 h")
        self.assertNotIn("Inert atmosphere", third)
        eighth = self.panel(self.page_of(by_id["OSDB-0008"]))
        self.assertEqual(eighth["Lab notebook"].definition.norm(),
                         "AE-2/12")
        self.assertEqual(eighth["Project"].definition.norm(),
                         "Research › Cinnamates")
        for label in ("Working time", "Inert atmosphere"):
            self.assertNotIn(label, eighth)
        fourth = self.panel(self.page_of(by_id["OSDB-0004"]))
        self.assertEqual(fourth["Inert atmosphere"].definition.norm(),
                         "Yes")
        self.assertEqual(fourth["Working time"].definition.norm(), "6 h")

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
        figures = ws.compound_widget(self, page).figures
        self.assertEqual(len(figures), 1, "not one figure.structure")
        figure = figures[0]
        self.assertIn("data-pagefind-ignore", figure.attrs)
        self.assertFalse(figure.has_class("structure--placeholder"))
        image = figure.find("img")
        self.assertIsNotNone(image, "no img in the figure")
        self.assertEqual(page.resolve(image.attrs.get("src", "")),
                         "/substances/isopentyl-acetate/structure.svg")
        self.assertTrue((self.public / "substances" / "isopentyl-acetate"
                         / "structure.svg").is_file())
        self.assertFalse(
            (self.public / "structures" / "osdb-0003.svg").exists())
        self.assertEqual(image.attrs.get("alt"),
                         "Structure of Isopentyl acetate")
        path = self.public / "procedures" / "osdb-0002" / "index.html"
        page = ps.load_page(self.public, path)
        figures = ws.compound_widget(self, page).figures
        self.assertEqual(len(figures), 1, "not one figure.structure")
        figure = figures[0]
        self.assertIn("data-pagefind-ignore", figure.attrs)
        self.assertTrue(figure.has_class("structure--placeholder"))
        slot = figure.find("div", "structure__slot")
        self.assertIsNotNone(slot, "no div.structure__slot")
        self.assertEqual(slot.norm(), "No structure image")
        self.assertEqual(page.find_all("img"), [])

    # --- procedure body sections ---------------------------------------

    SECTION_NAMES = ["Summary", "Reagents", "Procedure",
                     "Workup and Purification", "Characterization", "Notes",
                     "Hazards and Waste Disposal", "References"]

    def test_sections_of_the_markdown_seed(self) -> None:
        """Scenario: Sections of the Markdown seed."""
        page = self.page_of(self.by_id()["OSDB-0002"])
        sections = ws.check_sections(self, page)
        self.assertEqual(len(sections), 8)
        self.assertEqual([h.norm() for _, h in sections], self.SECTION_NAMES)
        self.assertEqual([s.attrs.get("data-section") for s, _ in sections],
                         list(ws.ROLES))
        self.assertEqual(
            [h.attrs.get("id") for _, h in sections],
            [name.lower().replace(" ", "-") for name in self.SECTION_NAMES])
        for section, heading in sections:
            self.assertIs(heading.parent.parent, section)
            self.assertIn("widget__head", heading.parent.classes)

    def test_every_h2_of_a_body_stands_in_its_own_section(self) -> None:
        """Scenario: Sections of the Markdown seed (every page, one h2 per
        section and none outside)."""
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                sections = ws.check_sections(self, page)
                self.assertEqual(
                    [h.norm() for _, h in sections],
                    re.findall(r"(?m)^## (.+?)\s*$", item.body))
                self.assertEqual([s.attrs.get("data-section")
                                  for s, _ in sections], list(ws.ROLES))
                article = page.find("article", "procedure")
                details = article.find("div", "procedure-details")
                self.assertEqual(
                    len(article.find_all("h2")),
                    len(sections) + len(details.find_all("h2"))
                    + (1 if item.is_general else 0))

    def test_note_links_lie_in_their_sections(self) -> None:
        """Scenario: Note links still resolve."""
        page = self.page_of(self.by_id()["OSDB-0003"])
        sections = ws.check_sections(self, page)
        notes = ws.section_of(sections, "notes")
        for number in (1, 2):
            found = page.find_all(id=f"note-{number}")
            self.assertEqual(len(found), 1, f"#note-{number}")
            self.assertTrue(found[0].within(notes), f"#note-{number}")
        for number, role in ((1, "procedure"), (2, "workup")):
            section = ws.section_of(sections, role)
            links = [l for l in page.links(section)
                     if l.href == f"#note-{number}"]
            self.assertEqual(len(links), 1, f"link to #note-{number}")
        article = page.find("article", "procedure")
        self.assertEqual(
            sorted(l.href for l in page.links(article)
                   if l.href.startswith("#note-")),
            ["#note-1", "#note-2"])

    # --- general procedures --------------------------------------------

    def general_items(self) -> list[Content]:
        return [item for item in self.content() if item.is_general]

    def test_scope_table_of_a_general_procedure(self) -> None:
        """Scenario: Scope table of a general procedure."""
        general = self.general_items()
        self.assertEqual([item.id for item in general], ["OSDB-0009"])
        registry = self.registry()
        page = self.page_of(general[0])
        table = gs.check_scope_table(
            self, page, general[0], registry, self.compound_fields(), "en",
            "Summary")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows[0], [
            "Entry", "Starting materials", "Products", "Yield", "Scale",
            "Time", "Note"])
        self.assertEqual(rows[1], [
            "1", self.linked("4-acetylbiphenyl"),
            self.linked("1-biphenyl-4-yl-ethanol"), "90 %", "", "30 min",
            ""])
        self.assertEqual(rows[2], [
            "2", self.linked("acetophenone"), self.linked("1-phenylethanol"),
            "85 %", "", "20 min", ""])
        self.assertEqual(rows[3][:6], [
            "3", self.linked("4-bromoacetophenone"),
            self.linked("1-4-bromophenyl-ethanol"), "88 %", "5 mmol",
            "30 min"])
        self.assertEqual(rows[3][6], general[0].scope[2]["note"])
        links = page.links(table)
        self.assertEqual(
            [l.target for l in links],
            [fs.substance_url(key) for key in (
                "4-acetylbiphenyl", "1-biphenyl-4-yl-ethanol",
                "acetophenone", "1-phenylethanol", "4-bromoacetophenone",
                "1-4-bromophenyl-ethanol")])

    def test_the_scope_is_a_widget(self) -> None:
        """Scenario: Scope widget."""
        item = self.by_id()["OSDB-0009"]
        page = self.page_of(item)
        scope = page.find("section", "scope")
        self.assertIsNotNone(scope, "no section.scope")
        self.assertTrue(scope.has_class("widget"))
        head, body = scope.elements()
        self.assertEqual((head.tag, head.has_class("widget__head")),
                         ("div", True))
        self.assertEqual((body.tag, body.has_class("widget__body")),
                         ("div", True))
        self.assertEqual([h.tag for h in head.elements()], ["h2"])
        self.assertEqual(len(body.find_all("table", "scope-table")), 1)
        article = page.find("article", "procedure")
        children = article.elements()
        order = [children.index(page.find(tag, cls)) for tag, cls in (
            ("div", "procedure-details"), ("section", "scope"),
            ("div", "procedure-content"))]
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(set(order)), 3)

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
        self.assertEqual(
            checked, sum(not item.is_general for item in self.content()))

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
        image = ws.compound_widget(self, page).figures[0].find("img")
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
            "Products", "Reaction type", "Tags", "Authors", "Lab notebook",
            "Project", "Working time", "Inert atmosphere", "Created",
            "Modified", "Starting materials", "Precursors", "Sequences"])
        self.assertEqual([title for title, _ in self.widgets_of(page)],
                         ["Products", "Details", "Synthesis context"])
        self.assertEqual(
            [(label, panel[label].definition.norm())
             for label in ("Lab notebook", "Project", "Working time",
                           "Inert atmosphere")],
            [("Lab notebook", "CE-3/1"),
             ("Project", "Teaching › Advanced practical"),
             ("Working time", "3.5 h"), ("Inert atmosphere", "No")])
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in panel["Products"].definition.find_all("a", "compound")],
            [(fs.substance_url("1-biphenyl-4-yl-ethanol"),
              "1-(Biphenyl-4-yl)ethanol"),
             (fs.substance_url("1-phenylethanol"), "1-Phenylethanol"),
             (fs.substance_url("1-4-bromophenyl-ethanol"),
              "1-(4-Bromophenyl)ethanol")])
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in panel["Starting materials"].definition.find_all(
                 "a", "compound")],
            [(fs.substance_url("4-acetylbiphenyl"), "4-Acetylbiphenyl"),
             (fs.substance_url("acetophenone"), "Acetophenone"),
             (fs.substance_url("4-bromoacetophenone"),
              "4′-Bromoacetophenone")])
        self.assertEqual(list(panel), self.expected_labels(item))
        self.assertEqual(
            [l.norm() for l in
             panel["Precursors"].definition.find_all("a", "precursor")],
            ["OSDB-0004 4-Acetylbiphenyl"])
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm()) for l in
             panel["Sequences"].definition.find_all("a", "sequence")],
            [("/sequences/seq-0002/",
              "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone")])
        self.assertEqual(page.find_all("button", data_copy_smiles=True), [])

    def test_current_link(self) -> None:
        """Scenario: Current link."""
        marked_pages = 0
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                nav = page.find("header", "site-header").find("nav")
                marked = {l.target: l.node.attrs["aria-current"]
                          for l in page.links(nav)
                          if "aria-current" in l.node.attrs}
                expected = ns.marks(self.site, self.lab, page.url)
                self.assertEqual(marked, expected)
                marked_pages += bool(expected)
        self.assertGreater(marked_pages, 0, "no page marks a link")

    def test_no_link_under_the_lab(self) -> None:
        """Scenario: A build without the lab."""
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                header = page.find("header", "site-header")
                self.assertEqual([l.target for l in page.links(header)
                                  if l.target.startswith("/lab/")], [])

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
        """Scenario: No tabs elsewhere (the procedure tabs are the only
        section tabs)."""
        listing = set(self.listing_pages())
        built = set()
        for path, page in self.pages():
            name = str(path.relative_to(self.public))
            built.add(name)
            with self.subTest(page=name):
                tabs = page.find_all("nav", "section-tabs")
                self.assertEqual(len(tabs), int(name in listing))
                for tab in tabs:
                    self.assertEqual(tab.attrs.get("aria-label"),
                                     "Procedures")
        self.assertLessEqual(listing, built)

    def test_no_compound_pages(self) -> None:
        """Scenario: No compound pages (nothing is built under
        `/compounds/`, and no page links there)."""
        self.assertFalse((self.public / "compounds").exists())
        self.assertEqual(
            [str(path.relative_to(self.public))
             for path, _ in self.pages()
             if "compounds" in path.relative_to(self.public).parts], [])
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                self.assertEqual(
                    [l.target for l in page.links()
                     if l.target.startswith("/compounds/")], [])

    def test_every_compound_link_leads_to_the_labs_substance(self) -> None:
        """Scenario: every `a.compound` links the substance's lab page,
        in a build without the lab (site-theme "Metadata panel",
        compound-fields "Values beside compound links")."""
        registry = self.registry()
        linked: set[str] = set()
        for path, page in self.pages():
            where = path.relative_to(self.public).as_posix()
            for link in page.find_all("a", "compound"):
                with self.subTest(page=where, href=link.attrs["href"]):
                    self.assertFalse(link.attrs["href"].startswith("/"))
                    key = fs.substance_key(
                        page.resolve(link.attrs["href"]))
                    self.assertIn(key, registry)
                    linked.add(key)
        self.assertGreater(len(linked), 10)

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
        accounts = ps.account_names(self.sandbox)
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
                    name = (labels[term] if taxonomy == "reaction_types"
                            else ps.author_name(accounts, term)
                            if taxonomy == "authors" else term)
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
                        if taxonomy == "authors":
                            self.assertEqual(link.target,
                                             f"/authors/{term.lower()}/")
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
        navigation = " ".join(ns.texts(self.navigation()))
        registry = self.registry()
        accounts = ps.account_names(self.sandbox)
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                bodies = page.indexed_bodies()
                self.assertEqual(len(bodies), 1)
                text = bodies[0].norm()
                compounds = [registry[e["compound"]] for e in item.products]
                expected = [item.id, *item.tags,
                            *(ps.author_name(accounts, author) for author
                              in item.data.get("authors", []))]
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
        widget = ws.compound_widget(self, page)
        self.assertEqual(widget.title, "Products")
        figures = widget.figures
        self.assertEqual(len(figures), 1)
        self.assertIn("data-pagefind-ignore", figures[0].attrs)
        self.assertTrue(figures[0].has_class("structure--placeholder"))
        slot = figures[0].find("div", "structure__slot")
        self.assertIsNotNone(slot, "no div.structure__slot")
        self.assertEqual(slot.norm(), "No structure image")
        self.assertEqual(widget.node.find_all("img"), [])
        registry = self.registry()
        self.assertTrue(registry["ethyl-acetate"].get("structure_image"),
                        "no product sets a structure image")
        demo = self.page_of(self.by_id()["OSDB-0009"])
        figure = ws.compound_widget(self, demo).figures[0]
        self.assertFalse(figure.has_class("structure--placeholder"))
        self.assertEqual(figure.find("img").attrs.get("alt"),
                         "Scheme of " + self.by_id()["OSDB-0009"].title)

    def test_the_scope_table_with_every_column_and_an_image(self) -> None:
        """Scenario: Scope table of a general procedure (the fixture)."""
        item = self.item()
        page = self.page_of(item)
        table = gs.check_scope_table(
            self, page, item, self.registry(), self.compound_fields(), "en",
            "Summary")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows, [
            ["Entry", "Starting materials", "Products", "Yield", "Scale",
             "Time", "Temperature", "Note"],
            ["1", f"{self.linked('acetic-acid')}, {self.linked('ethanol')}",
             self.linked("ethyl-acetate"), "85 %", "20 mmol", "2 h",
             "80 °C", "Reflux."],
            ["2", self.linked("acetic-acid"),
             f"{self.linked('benzyl-acetate')}, "
             f"{self.linked('propyl-acetate')}",
             "78 %, 64.5 %", "", "", "", ""],
            ["3", self.linked("ethanol"), self.linked("methyl-benzoate"),
             "72.5 %", "", "", "", ""]])
        images = table.find_all("img", "scope-structure")
        self.assertEqual([(i.attrs.get("alt"), page.resolve(i.attrs["src"]))
                          for i in images],
                         [("Structure of Ethyl acetate",
                           "/substances/ethyl-acetate/structure.svg")])
        self.assertTrue((self.public / "substances" / "ethyl-acetate"
                         / "structure.svg").is_file())

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
            ", ".join(self.linked(key) for key in (
                "ethyl-acetate", "benzyl-acetate", "propyl-acetate",
                "methyl-benzoate")))
        self.assertEqual(
            panel["Starting materials"].definition.norm(),
            ", ".join(self.linked(key)
                      for key in ("acetic-acid", "ethanol")))
        self.assertEqual(
            [l.target for l in page.links(panel["Products"].definition)],
            [fs.substance_url(key) for key in (
                "ethyl-acetate", "benzyl-acetate", "propyl-acetate",
                "methyl-benzoate")])

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
        self.assertEqual(
            self.widgets_of(page),
            [("Products", ["Products"]),
             ("Details", ["Reaction type", "Tags", "Authors", "Created",
                          "Modified"])])
        links = panel["Products"].definition.find_all("a", "compound")
        self.assertEqual([(page.resolve(l.attrs["href"]), l.norm())
                          for l in links],
                         [(fs.substance_url("trans-stilbene"),
                           "trans-Stilbene"),
                          (fs.substance_url("cis-stilbene"),
                           "cis-Stilbene")])
        self.assertEqual(
            panel["Products"].definition.norm(),
            ", ".join(self.linked(key)
                      for key in ("trans-stilbene", "cis-stilbene")))
        self.assertEqual(self.expected_labels(
            self.by_id()["OSDB-0907"]), list(panel))

    def test_one_figure_per_product_with_an_image(self) -> None:
        """Scenario: One figure per product with an image."""
        page = self.page_0907()
        widget = ws.compound_widget(self, page)
        self.assertEqual(widget.title, "Products")
        figures = widget.figures
        self.assertEqual(len(figures), 1)
        self.assertIn("data-pagefind-ignore", figures[0].attrs)
        self.assertFalse(figures[0].has_class("structure--placeholder"))
        images = figures[0].find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].attrs.get("alt"),
                         "Structure of trans-Stilbene")
        self.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/substances/trans-stilbene/structure.svg")
        self.assertTrue((self.public / "substances" / "trans-stilbene"
                         / "structure.svg").is_file())
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

    def test_the_panel_names_the_starting_material(self) -> None:
        """Scenario: A second route (starting materials)."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0908" / "index.html")
        panel = self.panel(page)
        self.assertEqual(panel["Starting materials"].definition.norm(),
                         self.linked("phenyl-salicylate"))
        self.assertEqual(
            [page.resolve(l.attrs["href"]) for l in
             panel["Starting materials"].definition.find_all("a")],
            [fs.substance_url("phenyl-salicylate")])
        self.assertEqual(list(panel), self.expected_labels(
            self.by_id()["OSDB-0908"]))


if __name__ == "__main__":
    unittest.main()


class LabNavigationTests(SiteCase):
    """The test collection built with ORGSYNDB_LAB=true."""

    ENV = {"ORGSYNDB_LAB": "true"}

    def test_one_navigation_from_the_menu(self) -> None:
        """Scenario: One navigation from the menu."""
        navigation = self.navigation()
        self.assertTrue([e for e in ns.links(self.site, True)
                         if e["url"].startswith("/lab/")], "no lab link")
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                header = page.find("header", "site-header")
                self.assertEqual(len(header.find_all("nav")), 1)
                nav = header.find("nav", aria_label="Site")
                self.assertIsNotNone(nav, "no nav[aria-label=Site]")
                self.assertEqual(ns.shown(page, nav), navigation)

    def test_current_link_with_the_lab(self) -> None:
        """Scenario: Current link (with the lab)."""
        for path, page in self.pages():
            with self.subTest(page=str(path.relative_to(self.public))):
                nav = page.find("header", "site-header").find("nav")
                marked = {l.target: l.node.attrs["aria-current"]
                          for l in page.links(nav)
                          if "aria-current" in l.node.attrs}
                self.assertEqual(marked,
                                 ns.marks(self.site, True, page.url))

    def test_the_labs_summary_on_the_home_page(self) -> None:
        """Scenario: The lab's summary on the home page."""
        page = ps.load_page(self.public, self.public / "index.html")
        main = page.find("main")
        order = [node for node in main.find_all()
                 if node.parent is main]
        names = [(node.tag, node.classes) for node in order]
        self.assertEqual([tag for tag, _ in names][:3],
                         ["div", "section", "div"])
        self.assertIn("home-intro", names[0][1])
        self.assertIn("home-lab", names[1][1])
        self.assertIn("home-layout", names[2][1])
        section = order[1]
        self.assertEqual(section.find("h2").norm(), "Lab at a glance")
        frame = section.find("iframe")
        self.assertIn("home-lab-frame", frame.classes)
        self.assertEqual(page.resolve(frame.attrs["src"]), "/lab/summary/")
        self.assertEqual(frame.attrs.get("title"), "Lab at a glance")
        self.assertEqual([(link.target, link.node.norm())
                          for link in page.links(section)],
                         [("/lab/", "Open the lab overview")])

    def test_lab_references_at_the_root(self) -> None:
        """Scenario: Lab references at the root (the notebook pages of
        the registry among them)."""
        lab = {"/lab/", "/lab/summary/", "/lab/registry/",
               *(entry["url"] for entry in ns.links(self.site, True)
                 if entry["url"].startswith("/lab/"))}
        substances = {fs.substance_url(key) for key in self.registry()}
        notebooks = {f"/lab/journal/{notebook['code']}/" for notebook in
                     ps.read_snapshot(self.sandbox)["notebooks"]}
        scheme = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
        found_lab: set[str] = set()
        problems = []
        for path, page in self.pages():
            for node in page.nodes:
                for attribute in ("href", "src", "action"):
                    value = node.attrs.get(attribute)
                    if value is None:
                        continue
                    if value.startswith("/"):
                        problems.append((page.url, value))
                    if scheme.match(value) or value.startswith("#"):
                        continue
                    joined = urllib.parse.urljoin(
                        "http://127.0.0.1" + page.url, value)
                    target = urllib.parse.unquote(
                        urllib.parse.urlsplit(joined).path)
                    if target.startswith("/lab/") or target == "/lab":
                        found_lab.add(target)
                        if target not in lab | substances | notebooks:
                            problems.append((page.url, value))
                        continue
                    if not ps.target_file(self.public, target).is_file():
                        problems.append((page.url, value))
        self.assertEqual(problems, [])
        self.assertLessEqual(lab, found_lab)
        self.assertLessEqual(found_lab, lab | substances | notebooks)
        self.assertIn(fs.substance_url("salicylic-acid"), found_lab)
        self.assertIn("/lab/journal/AE-1/", found_lab)

    def test_compound_links_are_the_same_with_the_lab(self) -> None:
        """Scenario: every `a.compound` links the substance's lab page
        whatever `ORGSYNDB_LAB` says, and no compound page is built."""
        self.assertFalse((self.public / "compounds").exists())
        registry = self.registry()
        links = [(path, page, link) for path, page in self.pages()
                 for link in page.find_all("a", "compound")]
        self.assertGreater(len(links), 30)
        for path, page, link in links:
            with self.subTest(page=str(path.relative_to(self.public)),
                              href=link.attrs["href"]):
                self.assertFalse(link.attrs["href"].startswith("/"))
                self.assertIn(fs.substance_key(
                    page.resolve(link.attrs["href"])), registry)
        navigation = [e["url"] for e in ns.links(self.site, True)]
        self.assertNotIn("/compounds/", navigation)

    def test_the_overlay_sets_the_lab(self) -> None:
        """Scenario: Lab views on request (the overlay)."""
        overlay = self.sandbox.root / "build" / "hugo-config" / "_default"
        config = tomllib.loads((overlay / "hugo.toml").read_text(
            encoding="utf-8"))
        self.assertEqual(config.get("params"), {"lab": True})
