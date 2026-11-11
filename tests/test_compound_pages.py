"""Compound pages and the compound directory of a theme build (site-theme
"Compound pages" and "Compound directory", site-build "Hugo
configuration", localization "German compound names").

``CompoundSiteTests`` builds the test collection in English, with the
compound tabs and their pages (site-catalogue "Compound tabs");
``GermanCompoundTests`` builds it in German, and ``FallbackNameTests``
builds it in German after removing one German name.
``ChemicalClassTabsTests``, ``TabsFieldNotAFacetTests`` and
``NoTabsFieldTests`` build modified copies of the collection for the
tab scenarios that say so.
"""

import json
import re
from typing import NamedTuple

import catalogue_support as cs
import field_support as fs
import pipeline_support as ps
import sequence_support as ss
import support
import test_theme_integration as tti
from pipeline_support import Content, Node, Page

PURCHASED = ["acetic-acid", "acetic-anhydride",
             "ethyl-triphenylphosphoranylidene-acetate",
             "phenylboronic-acid", "acetone", "acetophenone",
             "benzaldehyde", "4-bromoacetophenone", "isopentyl-alcohol",
             "methyl-salicylate"]
SYNTHESISED = ["salicylic-acid", "4-acetylbiphenyl", "ethyl-cinnamate",
               "acetylsalicylic-acid", "isopentyl-acetate",
               "1-biphenyl-4-yl-ethanol", "dibenzylideneacetone",
               "cinnamic-acid", "1-phenylethanol", "1-4-bromophenyl-ethanol",
               "new-compound-7"]


class Tab(NamedTuple):
    """A tab page: the key of the tabs field and a top-level value."""
    field: str
    value: str


FACT_KEYS = [("Formula", "formula"), ("MW", "mw"), ("CAS", "cas"),
             ("SMILES", "smiles")]
SEPARATOR = fs.PATH_SEPARATOR
DEPTH = re.compile(r"^--depth:(\d+);?$")
CATALOGUE_TEXTS = {
    "en": {"heading": "Compounds", "many": "{n} compounds",
           "one": "1 compound", "filtered": "{shown} of {total} compounds",
           "noscript": "Search and filters need JavaScript. Without it, "
                       "this page lists every compound.",
           "empty": "No compounds match the search and filters.",
           "ignored": "Ignored in the address: {list}",
           "remove": "Remove {facet}: {value}", "filters": "Filters",
           "clear": "Clear all", "label": "Search compounds",
           "placeholder": "Name, formula, CAS or SMILES",
           "button": "Search", "all": "All compounds",
           "tab_noscript": "Search and filters need JavaScript. Without "
                           "it, this page lists every compound of this "
                           "tab.",
           "tab_label": "Search compounds: {label}"},
    "de": {"heading": "Verbindungen", "many": "{n} Verbindungen",
           "one": "1 Verbindung",
           "filtered": "{shown} von {total} Verbindungen",
           "noscript": "Suche und Filter brauchen JavaScript. Ohne "
                       "JavaScript zeigt diese Seite alle Verbindungen.",
           "empty": "Keine Verbindung passt zu Suche und Filtern.",
           "ignored": "In der Adresse nicht berücksichtigt: {list}",
           "remove": "{facet}: {value} entfernen", "filters": "Filter",
           "clear": "Alles zurücksetzen", "label": "Verbindungen "
           "durchsuchen",
           "placeholder": "Name, Summenformel, CAS oder SMILES",
           "button": "Suchen", "all": "Alle Verbindungen",
           "tab_noscript": "Suche und Filter brauchen JavaScript. Ohne "
                           "JavaScript zeigt diese Seite alle "
                           "Verbindungen dieses Reiters.",
           "tab_label": "Verbindungen durchsuchen: {label}"},
}


ROUTE_TEXTS = {
    "en": {"heading": "Routes",
           "intro": "Ways to make this compound from the collection's "
                    "procedures, each step with the compounds it starts "
                    "from.",
           "entry": "entry", "more": "more steps on its page",
           "status": {"draft": "draft", "checked": "checked",
                      "retired": "retired"}},
    "de": {"heading": "Herstellungswege",
           "intro": "Wege zu dieser Verbindung aus den Vorschriften der "
                    "Sammlung, jede Stufe mit ihren Ausgangsstoffen.",
           "entry": "Eintrag", "more": "weitere Stufen auf ihrer Seite",
           "status": {"draft": "Entwurf", "checked": "Geprüft",
                      "retired": "Zurückgezogen"}},
}
CHAIN_LENGTH = 7


class CompoundCase(tti.SiteCase):
    """Helpers for the scans of compound pages."""

    def compound_page(self, key: str) -> Page:
        path = self.public / "compounds" / key / "index.html"
        self.assertTrue(path.is_file(), f"compounds/{key}/ was not built")
        return ps.load_page(self.public, path)

    def made_by(self, key: str) -> list[Content]:
        return sorted((i for i in self.content()
                       if key in [e["compound"] for e in i.products]),
                      key=lambda i: i.id)

    def made_by_entries(self, key: str) -> list[tuple[Content, int | None,
                                                     int | float]]:
        """The ``Made by`` list of a compound: for each procedure by ID
        its yield of the compound, or for a general procedure each entry
        that makes it, in entry order, with the entry's number and
        yield."""
        found = []
        for item in self.made_by(key):
            if not item.is_general:
                found.append((item, None, next(
                    e["yield_percent"] for e in item.products
                    if e["compound"] == key)))
                continue
            for number, entry in enumerate(item.scope, 1):
                for product in entry["products"]:
                    if product["compound"] == key:
                        found.append((item, number,
                                      product["yield_percent"]))
        return found

    def used_in_by(self, key: str) -> list[Content]:
        return sorted((i for i in self.content() if key in i.substrates),
                      key=lambda i: i.id)

    def shown(self, key: str) -> str:
        return ps.shown_name(self.registry()[key], self.LOCALE)

    def fields(self) -> list[fs.Field]:
        """The four registry fields, in the site's language."""
        return self.compound_fields()

    def declared_pairs(self, key: str) -> list[tuple[str, str]]:
        """The label and value of each registry field the compound has
        that its page shows after the facts, in order, as read from the
        page."""
        page = self.compound_page(key)
        pairs = page.definition_pairs(page.find("dl", "compound-facts"))
        compound = self.registry()[key]
        built_in = sum(bool(compound.get(name)) for _, name in FACT_KEYS)
        return [(p.label, p.definition.norm()) for p in pairs[built_in:]]

    # --- the route trees (synthesis-routes "Routes on compound pages") --

    def route_data(self) -> dict[str, list[dict]]:
        """The route data the build staged, ``build/data/routes.json``."""
        path = self.sandbox.root / "build" / "data" / "routes.json"
        self.assertTrue(path.is_file(), "build/data/routes.json is missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def route_tree(self, page: Page) -> Node:
        """The ``ul.route-tree`` of a compound page."""
        tree = page.find("ul", "route-tree")
        self.assertIsNotNone(tree, f"{page.url} has no ul.route-tree")
        return tree

    @staticmethod
    def own_text(item: Node) -> str:
        """The text of ``item`` outside its nested lists, whitespace
        collapsed."""
        return " ".join("".join(
            c if isinstance(c, str) else c.text() for c in item.children
            if not (isinstance(c, Node) and c.tag == "ul")).split())

    @staticmethod
    def between(item: Node, first: Node, second: Node) -> str:
        """The raw text that lies between two children of ``item``."""
        spot = item.children.index(first) + 1
        end = item.children.index(second)
        found = item.children[spot:end]
        assert all(isinstance(c, str) for c in found), found
        return "".join(found)

    def step_parts(self, step: Node) -> tuple[Node, str, Node, Node | None]:
        """The procedure link, the raw text between it and the status
        badge, the badge and the nested ``ul`` of a ``li.route-step``."""
        self.assertEqual((step.tag, step.classes), ("li", ["route-step"]))
        link, badge, *rest = step.elements()
        self.assertEqual(link.tag, "a")
        self.assertEqual((badge.tag, badge.has_class("badge")),
                         ("span", True))
        self.assertLessEqual(len(rest), 1)
        nested = rest[0] if rest else None
        self.assertTrue(nested is None or nested.tag == "ul", rest)
        return link, self.between(step, link, badge), badge, nested

    def compound_items(self, ul: Node) -> list[Node]:
        """The ``li.route-compound`` items of a list inside a step."""
        self.assertEqual([(n.tag, n.classes) for n in ul.elements()],
                         [("li", ["route-compound"])] * len(ul.elements()))
        self.assertTrue(ul.elements(), "an empty ul")
        return ul.elements()

    def compound_link(self, page: Page, item: Node) -> str:
        """The key of the compound that ``item`` links first."""
        link = item.elements()[0]
        self.assertEqual((link.tag, link.has_class("compound")),
                         ("a", True))
        target = page.resolve(link.attrs["href"])
        self.assertRegex(target, r"^/compounds/[^/]+/$")
        return target.removeprefix("/compounds/").removesuffix("/")

    def check_route_steps(self, page: Page, ul: Node,
                          steps: list[dict]) -> int:
        """The ``li.route-step`` items of ``ul`` follow ``steps``, the
        data's steps, each with its link, entry, yield and badge, and
        each compound below with its link, its note and its steps or its
        ``span.route-more``, recursively. Returns the number of
        ``span.route-more`` found."""
        texts = ROUTE_TEXTS[self.LOCALE]
        by_id = self.by_id()
        self.assertEqual(len(ul.elements()), len(steps))
        found = 0
        for item, step in zip(ul.elements(), steps):
            with self.subTest(page=page.url, step=step["procedure"],
                              entry=step.get("entry")):
                procedure = by_id[step["procedure"]]
                link, between, badge, nested = self.step_parts(item)
                self.assertEqual(page.resolve(link.attrs["href"]),
                                 f"/procedures/{procedure.slug}/")
                self.assertEqual(link.norm(),
                                 f"{procedure.id} {procedure.title}")
                status = procedure.data["status"]
                self.assertTrue(badge.has_class(f"badge--{status}"))
                self.assertEqual(badge.norm(), texts["status"][status])
                entry = (f" · {texts['entry']} {step['entry']}"
                         if "entry" in step else "")
                self.assertEqual(
                    between, f"{entry} · {step['yield_percent']} % · ")
                self.assertEqual(self.own_text(item),
                                 f"{link.norm()}{between}{badge.norm()}")
                self.assertEqual(nested is not None,
                                 bool(step["substrates"]))
                if nested is not None:
                    found += self.check_route_compounds(
                        page, nested, step["substrates"])
        return found

    def check_route_compounds(self, page: Page, ul: Node,
                              compounds: list[dict]) -> int:
        """The ``li.route-compound`` items of ``ul`` follow
        ``compounds``, as ``check_route_steps`` says; returns the
        number of ``span.route-more`` found."""
        texts = ROUTE_TEXTS[self.LOCALE]
        registry, fields = self.registry(), self.compound_fields()
        self.assertEqual(len(self.compound_items(ul)), len(compounds))
        found = 0
        for item, compound in zip(ul.elements(), compounds):
            key = compound["compound"]
            with self.subTest(page=page.url, compound=key):
                self.assertEqual(self.compound_link(page, item), key)
                self.assertFalse(compound["more"] and compound["steps"])
                note = fs.beside_note(fields, registry[key], self.LOCALE)
                text = ps.shown_name(registry[key], self.LOCALE)
                if note:
                    text += f" {note}"
                if compound["more"]:
                    text += f" · {texts['more']}"
                self.assertEqual(self.own_text(item), text)
                more = [n for n in item.elements()
                        if n.tag == "span" and n.has_class("route-more")]
                self.assertEqual(len(more), int(compound["more"]))
                lists = [n for n in item.elements() if n.tag == "ul"]
                self.assertEqual(len(lists), int(bool(compound["steps"])))
                if more:
                    self.assertEqual(more[0].norm(), texts["more"])
                    self.assertIs(item.elements()[-1], more[0])
                    self.assertEqual(
                        self.between(item, item.elements()[-2], more[0])
                        .split()[-1:], ["·"])
                    found += 1
                if lists:
                    found += self.check_route_steps(
                        page, lists[0], compound["steps"])
        return found

    def check_route_trees(self) -> dict[str, dict]:
        """Every compound page has a ``section.compound-routes``, the
        last child of ``main``, exactly when its compound is a key of
        the route data, and its tree follows the data. Returns the
        data."""
        texts = ROUTE_TEXTS[self.LOCALE]
        data = self.route_data()
        for key in self.registry():
            page = self.compound_page(key)
            main = page.find("main")
            with self.subTest(compound=key):
                sections = main.find_all("section", "compound-routes")
                self.assertEqual(len(sections), int(key in data))
                if key not in data:
                    self.assertEqual(page.find_all("ul", "route-tree"), [])
                    continue
                (section,) = sections
                self.assertIs(main.elements()[-1], section)
                heading, intro, tree = section.elements()
                self.assertEqual(
                    (heading.tag, heading.norm(), intro.tag,
                     intro.has_class("routes-intro"), intro.norm(),
                     tree.tag, tree.has_class("route-tree")),
                    ("h2", texts["heading"], "p", True, texts["intro"],
                     "ul", True))
                self.assertEqual(page.find_all("ul", "route-tree"), [tree])
                found = self.check_route_steps(page, tree, data[key])
                self.assertEqual(len(page.find_all("span", "route-more")),
                                 found)
                self.check_notes(page, tree)
        return data

    # --- the compound tabs (site-catalogue "Compound tabs") -------------

    def tabs_field(self) -> fs.Field | None:
        """The field the collection declares with ``tabs = true``."""
        found = [f for f in self.fields() if f.tabs]
        self.assertLessEqual(len(found), 1, "two tabs fields")
        return found[0] if found else None

    def tab_values(self) -> list[str]:
        """The values that have a tab page, in tab order."""
        return fs.tab_values(self.tabs_field(), self.registry())

    def tab_label(self, tab: Tab) -> str:
        field = next(f for f in self.fields() if f.key == tab.field)
        return field.paths[tab.value][-1]

    def tab_url(self, tab: Tab) -> str:
        return f"/compounds/{tab.field}/{tab.value}/"

    def tab_page(self, tab: Tab) -> Page:
        path = (self.public / "compounds" / tab.field / tab.value
                / "index.html")
        self.assertTrue(path.is_file(), f"{self.tab_url(tab)} was not built")
        return ps.load_page(self.public, path)

    def tab_rows(self, tab: Tab) -> list[str]:
        """The keys of the compounds on a tab page, by shown name."""
        field = self.tabs_field()
        return sorted(
            fs.tab_compounds(field, self.registry(), tab.value),
            key=self.shown)

    def check_compound_tabs(self, page: Page, current: Tab | None) -> None:
        """The compound tabs open ``main`` of ``page``: the tab of
        ``current``, or ``All compounds`` for none, is the page's own."""
        texts = CATALOGUE_TEXTS[self.LOCALE]
        field = self.tabs_field()
        self.assertIsNotNone(field, "the collection declares no tabs")
        nav = page.find("main").elements()[0]
        self.assertEqual((nav.tag, nav.classes, nav.attrs.get("aria-label")),
                         ("nav", ["section-tabs"], field.label))
        self.assertEqual(len(page.find_all("nav", "section-tabs")), 1)
        lists = nav.find_all("ul")
        self.assertEqual(len(lists), 1)
        entries = lists[0].find_all("li")
        for entry in entries:
            self.assertEqual(len(entry.find_all("a")), 1, entry.norm())
        wanted = [("/compounds/", texts["all"])] + [
            (self.tab_url(Tab(field.key, v)), field.paths[v][-1])
            for v in self.tab_values()]
        links = page.links(nav)
        self.assertEqual([(l.target, l.node.norm()) for l in links], wanted)
        self.assertEqual(len(entries), len(wanted))
        own = "/compounds/" if current is None else self.tab_url(current)
        marked = {l.target: l.node.attrs["aria-current"]
                  for l in links if "aria-current" in l.node.attrs}
        self.assertEqual(marked, {own: "page"})

    def check_no_compound_tabs(self, page: Page) -> None:
        self.assertEqual(page.find_all("nav", "section-tabs"), [])

    def check_tab_page(self, tab: Tab, *, facets: bool = True) -> Page:
        """Everything the contract states of the tab page of ``tab``: the
        tabs, the catalogue, the rows, the title and the section."""
        page = self.tab_page(tab)
        self.check_compound_tabs(page, tab)
        if facets:
            self.check_compound_catalogue(page, tab)
        self.check_compound_rows(page, tab)
        main = page.find("main")
        self.assertEqual([h.norm() for h in main.find_all("h1")],
                         [self.tab_label(tab)])
        self.assertEqual(page.title(), f"{self.tab_label(tab)} | OrgSynDB")
        self.assertEqual(page.find_all(data_pagefind_body=True), [])
        nav = page.find("header", "site-header").find("nav")
        marked = {l.target: l.node.attrs["aria-current"]
                  for l in page.links(nav) if "aria-current" in l.node.attrs}
        self.assertEqual(marked, {"/compounds/": "true"})
        self.check_compound_header_search(page, tab)
        return page

    # --- the compound catalogue (site-catalogue "Compound catalogue") ----

    def catalogue_page(self) -> ps.Page:
        path = self.public / "compounds" / "index.html"
        self.assertTrue(path.is_file(), "compounds/ was not built")
        return ps.load_page(self.public, path)

    def catalogue_rows(self, page: ps.Page) -> list[ps.Node]:
        table = page.find("table", "compound-table")
        self.assertIsNotNone(table, "no table.compound-table")
        return [row for row in table.find_all("tr") if row.find("td")]

    def check_compound_catalogue(self, page: ps.Page,
                                 tab: Tab | None = None) -> ps.Node:
        """The elements, attributes and texts of ``div.catalogue`` up to
        the table, and the facets with their values and depths, for the
        collection the build holds, on ``/compounds/`` or, with ``tab``,
        on that tab page. Returns the ``div.catalogue``."""
        texts = CATALOGUE_TEXTS[self.LOCALE]
        main = page.find("main")
        if self.tabs_field() is None:
            self.check_no_compound_tabs(page)
        else:
            self.check_compound_tabs(page, tab)
        blocks = main.find_all("div", "catalogue")
        self.assertEqual(len(blocks), 1, "not one div.catalogue")
        block = blocks[0]
        self.assertIn("data-catalogue", block.attrs)
        self.assertEqual(block.attrs.get("data-search"), "text")
        self.assertNotIn("data-fixed", block.attrs)
        self.assertEqual(block.attrs.get("data-text-empty"), texts["empty"])
        self.assertEqual(block.attrs.get("data-text-ignored"),
                         texts["ignored"])
        self.assertEqual(block.attrs.get("data-text-remove"),
                         texts["remove"])
        self.assertEqual(
            [(n.tag, n.classes[:1]) for n in block.elements()],
            [("div", ["list-head"]), ("noscript", []),
             ("div", ["catalogue-layout"])])
        rows = self.catalogue_rows(page)
        head = block.find("div", "list-head")
        self.assertEqual([h.norm() for h in head.find_all("h1")],
                         [texts["heading"] if tab is None
                          else self.tab_label(tab)])
        if tab is not None:
            self.assertEqual(len(rows), len(self.tab_rows(tab)))
        count = head.find("p", "catalogue-count")
        self.assertIsNotNone(count, "no p.catalogue-count")
        self.assertEqual(count.attrs.get("role"), "status")
        self.assertIn("data-catalogue-count", count.attrs)
        self.assertEqual(count.attrs.get("data-filtered"), texts["filtered"])
        self.assertEqual(count.norm(), texts["one" if len(rows) == 1
                                             else "many"].format(
                                                 n=len(rows)))
        note = block.find("noscript").find("p", "catalogue-noscript")
        self.assertIsNotNone(note, "no p.catalogue-noscript")
        self.assertEqual(note.norm(), texts["noscript" if tab is None
                                            else "tab_noscript"])
        facet_fields = [f for f in self.fields() if f.facet]
        layout = block.find("div", "catalogue-layout")
        expected = [("div", ["catalogue-results"])]
        if facet_fields:
            expected.insert(0, ("div", ["catalogue-facets"]))
        self.assertEqual([(n.tag, n.classes[:1]) for n in layout.elements()],
                         expected)
        if facet_fields:
            self.check_compound_facets(page, block, facet_fields, tab)
        self.check_compound_results(page, block, bool(facet_fields))
        self.check_compound_header_search(page, tab)
        scripts = [page.resolve(src) for src in page.script_sources() if src]
        loaded = [src for src in scripts if cs.CATALOGUE_SCRIPT.match(src)]
        self.assertEqual(len(loaded), 1, f"scripts {scripts}")
        script = next(n for n in page.find_all("script")
                      if page.resolve(n.attrs.get("src", "")) == loaded[0])
        self.assertIn("defer", script.attrs)
        return block

    def check_compound_facets(self, page: ps.Page, block: ps.Node,
                              facet_fields: list[fs.Field],
                              tab: Tab | None = None) -> None:
        texts = CATALOGUE_TEXTS[self.LOCALE]
        facets = block.find("div", "catalogue-facets")
        self.assertEqual(facets.attrs.get("id"), "catalogue-facets")
        self.assertIn("data-catalogue-controls", facets.attrs)
        self.assertIn("hidden", facets.attrs)
        heading = facets.find("h2")
        self.assertIsNotNone(heading, "no h2 in the facets")
        self.assertEqual(heading.norm(), texts["filters"])
        groups = facets.find_all("details", "facet")
        self.assertEqual([g.attrs.get("data-facet") for g in groups],
                         [f.key for f in facet_fields])
        self.assertLess(page.index_of(heading), page.index_of(groups[0]))
        registry = self.registry()
        for group, field in zip(groups, facet_fields):
            with self.subTest(facet=field.key):
                self.assertIn("open", group.attrs)
                parts = group.elements()
                self.assertEqual([p.tag for p in parts[:2]],
                                 ["summary", "div"])
                summary, values = parts[0], parts[1]
                self.assertTrue(summary.attrs.get("id"),
                                "summary without an id")
                self.assertEqual(summary.norm(), field.label)
                self.assertEqual(values.attrs.get("role"), "group")
                self.assertEqual(values.attrs.get("aria-labelledby"),
                                 summary.attrs["id"])
                labels = values.find_all("label", "facet-value")
                if tab is None:
                    entries = fs.facet_entries(field, registry, self.LOCALE)
                else:
                    entries = fs.tab_facet_entries(
                        field, self.tabs_field(), tab.value, registry,
                        self.LOCALE)
                self.assertGreater(len(entries), 1 if tab is None else 0)
                self.assertEqual(len(labels), len(entries))
                for label, (value, text, depth) in zip(labels, entries):
                    self.check_compound_facet_value(
                        page, label, field, value, text, depth)

    def check_compound_facet_value(self, page: ps.Page, label: ps.Node,
                                   field: fs.Field, value: str, text: str,
                                   depth: int | None) -> None:
        box = label.find("input")
        self.assertIsNotNone(box, f"{value}: no input")
        self.assertEqual(
            {k: box.attrs.get(k) for k in ("type", "name", "value")},
            {"type": "checkbox", "name": field.key, "value": value})
        name = label.find("span", "facet-label")
        self.assertIsNotNone(name, f"{value}: no span.facet-label")
        self.assertEqual(name.norm(), text)
        count = label.find("span", "facet-count")
        self.assertIsNotNone(count, f"{value}: no span.facet-count")
        self.assertEqual(count.norm(), "")
        order = [page.index_of(n) for n in (box, name, count)]
        self.assertEqual(order, sorted(order))
        if depth is not None:
            found = DEPTH.match(ps.squash(label.attrs.get("style", "")))
            self.assertIsNotNone(
                found, f"{value}: style {label.attrs.get('style')!r}")
            self.assertEqual(int(found.group(1)), depth, value)

    def check_compound_results(self, page: ps.Page, block: ps.Node,
                               faceted: bool) -> None:
        texts = CATALOGUE_TEXTS[self.LOCALE]
        results = block.find("div", "catalogue-results")
        toolbar = results.find("div", "catalogue-toolbar")
        self.assertIsNotNone(toolbar, "no div.catalogue-toolbar")
        self.assertIn("data-catalogue-controls", toolbar.attrs)
        self.assertIn("hidden", toolbar.attrs)
        toggle = toolbar.find("button", "facets-toggle")
        if faceted:
            self.assertIsNotNone(toggle, "no button.facets-toggle")
            self.assertEqual(
                {k: toggle.attrs.get(k) for k in
                 ("type", "aria-controls", "aria-expanded")},
                {"type": "button", "aria-controls": "catalogue-facets",
                 "aria-expanded": "false"})
            self.assertEqual(toggle.norm(), texts["filters"])
        else:
            self.assertIsNone(toggle, "a button.facets-toggle without facets")
        active = toolbar.find("ul", "catalogue-active")
        self.assertIsNotNone(active, "no ul.catalogue-active")
        self.assertEqual((active.norm(), active.find_all("li")), ("", []))
        clear = toolbar.find("button", "clear-all")
        self.assertIsNotNone(clear, "no button.clear-all")
        self.assertEqual((clear.attrs.get("type"), clear.norm()),
                         ("button", texts["clear"]))
        order = ([toggle] if faceted else []) + [active, clear]
        positions = [page.index_of(n) for n in order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(toolbar.find_all("select"), [])
        self.assertEqual(block.find_all("select"), [], "a sort or view")
        message = results.find("p", "catalogue-message")
        self.assertIsNotNone(message, "no p.catalogue-message")
        self.assertIn("data-catalogue-message", message.attrs)
        self.assertEqual(message.attrs.get("role"), "status")
        self.assertIn("hidden", message.attrs)
        self.assertEqual(message.norm(), "")
        table = results.find("table", "compound-table")
        self.assertIsNotNone(table, "no table.compound-table in the results")
        self.assertEqual(block.find_all("table"), [table])
        positions = [page.index_of(n) for n in (toolbar, message, table)]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), 3)
        self.assertEqual(block.find_all("form"), [],
                         "a form inside div.catalogue")

    def check_compound_header_search(self, page: ps.Page,
                                     tab: Tab | None = None) -> None:
        texts = CATALOGUE_TEXTS[self.LOCALE]
        label = texts["label"] if tab is None else texts[
            "tab_label"].format(label=self.tab_label(tab))
        forms = page.find("header", "site-header").find_all("form")
        self.assertEqual(len(forms), 1, "not one form in the site header")
        form = forms[0]
        self.assertTrue(form.has_class("site-search"))
        self.assertIn("data-catalogue-search", form.attrs)
        self.assertNotIn("hidden", form.attrs)
        self.assertEqual(form.attrs.get("role"), "search")
        self.assertEqual(form.attrs.get("method", "").lower(), "get")
        self.assertEqual(page.resolve(form.attrs.get("action", "")),
                         "/compounds/" if tab is None
                         else self.tab_url(tab))
        fields = form.find_all("input")
        self.assertEqual(len(fields), 1)
        self.assertEqual(
            {k: fields[0].attrs.get(k) for k in
             ("type", "name", "id", "aria-label", "placeholder")},
            {"type": "search", "name": "q", "id": "catalogue-q",
             "aria-label": label,
             "placeholder": texts["placeholder"]})
        buttons = form.find_all("button")
        self.assertEqual(len(buttons), 1)
        self.assertEqual((buttons[0].attrs.get("type"), buttons[0].norm()),
                         ("submit", texts["button"]))
        self.assertEqual(len(page.find_all("input", name="q")), 1)

    def check_compound_rows(self, page: ps.Page, tab: Tab | None = None
                            ) -> dict[str, ps.Node]:
        """The rows' ``data-`` attributes against the registry and the
        field data, for every compound or, with ``tab``, for those on
        that tab page; returns the rows by compound key."""
        registry = self.registry()
        fields = self.fields()
        facet_fields = [f for f in fields if f.facet]
        rows = self.catalogue_rows(page)
        keys = sorted(registry, key=self.shown) if tab is None \
            else self.tab_rows(tab)
        self.assertEqual([r.attrs.get("data-id") for r in rows], keys)
        found = {}
        for row in rows:
            key = row.attrs["data-id"]
            found[key] = row
            compound = registry[key]
            with self.subTest(compound=key):
                self.assertEqual(row.attrs.get("data-title"),
                                 self.shown(key))
                self.assertEqual(row.attrs.get("data-text"),
                                 fs.search_text(fields, compound))
                for field in facet_fields:
                    raw = row.attrs.get(f"data-{field.key}")
                    self.assertIsNotNone(raw, f"no data-{field.key}")
                    listed = json.loads(raw)
                    wanted = fs.values_set(field, compound)
                    self.assertEqual(len(listed), len(set(listed)), raw)
                    self.assertEqual(sorted(listed), sorted(wanted), raw)
        return found


class CompoundSiteTests(CompoundCase):
    """The test collection, built in English."""

    def test_a_page_per_compound(self) -> None:
        """Scenario: A page per compound."""
        registry = self.registry()
        self.assertGreater(len(registry), 10)
        built = sorted(p.parent.name for p in
                       (self.public / "compounds").glob("*/index.html"))
        self.assertEqual(built, sorted(registry))
        for key, compound in registry.items():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                main = page.find("main")
                self.assertEqual([h.norm() for h in main.find_all("h1")],
                                 [compound["name"]])
                self.assertEqual(page.title(),
                                 f"{compound['name']} | OrgSynDB")
                self.check_facts(page, compound)
                self.check_figure(page, compound)

    def check_facts(self, page: Page, compound: dict) -> None:
        facts = page.find("main").find("dl", "compound-facts")
        self.assertIsNotNone(facts, "no dl.compound-facts")
        pairs = page.definition_pairs(facts)
        declared = fs.shown(self.fields(), compound, self.LOCALE, page=True)
        wanted = [label for label, name in FACT_KEYS if compound.get(name)]
        wanted += [field.label for field, _ in declared]
        self.assertEqual([p.label for p in pairs], wanted)
        values = {p.label: p.definition for p in pairs}
        for field, text in declared:
            self.assertEqual(values[field.label].norm(), text, field.key)
        if compound.get("formula"):
            self.assertEqual(values["Formula"].norm(), compound["formula"])
            self.assertEqual(
                [s.norm() for s in values["Formula"].find_all("sub")],
                re.findall(r"[0-9]+", compound["formula"]))
        if compound.get("mw"):
            self.assertEqual(values["MW"].norm(), f"{compound['mw']} g/mol")
        if compound.get("cas"):
            self.assertEqual(values["CAS"].norm(), compound["cas"])
        if compound.get("smiles"):
            code = values["SMILES"].find("code", data_smiles=True)
            self.assertIsNotNone(code, "no code[data-smiles]")
            self.assertEqual(code.norm(), compound["smiles"])
            copy = values["SMILES"].find("button", "copy-button")
            self.assertIsNotNone(copy, "no button.copy-button")
            self.assertEqual(copy.attrs.get("type"), "button")
            self.assertIn("data-copy-smiles", copy.attrs)
            self.assertIn("hidden", copy.attrs)
            self.assertEqual(copy.norm(), "Copy")
            self.assertGreater(page.index_of(copy), page.index_of(code))
        for pair in pairs:
            self.assertNotEqual(pair.gap, "", pair.label)
            self.assertEqual(pair.gap.strip(), "", pair.label)

    def check_figure(self, page: Page, compound: dict) -> None:
        main = page.find("main")
        figures = main.find_all("figure")
        image = compound.get("structure_image")
        if image is None:
            self.assertEqual(figures, [], "a figure without an image")
            return
        self.assertEqual(len(figures), 1)
        self.assertTrue(figures[0].has_class("structure"))
        self.assertFalse(figures[0].has_class("structure--placeholder"))
        images = figures[0].find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].attrs.get("alt"),
                         f"Structure of {compound['name']}")
        self.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/" + image)
        self.assertTrue(ps.target_file(self.public, "/" + image).is_file())
        self.assertLess(page.index_of(main.find("h1")),
                        page.index_of(figures[0]))
        self.assertLess(page.index_of(figures[0]),
                        page.index_of(main.find("dl", "compound-facts")))

    def test_registry_fields_follow_the_facts(self) -> None:
        """Scenario: Fields of a numbered substance."""
        sep = SEPARATOR
        expected = {
            "acetylsalicylic-acid": [
                ("Article no.", "CH-0010"), ("Short name", "ASA"),
                ("Chemical class", f"Carbonyl compounds{sep}Carboxylic "
                 f"acids, Carbonyl compounds{sep}Carboxylic acid "
                 f"derivatives{sep}Esters"),
                ("Group", f"Synthesised{sep}Final products")],
            "acetic-acid": [
                ("Short name", "AcOH"),
                ("Chemical class",
                 f"Carbonyl compounds{sep}Carboxylic acids"),
                ("Group", f"Purchased{sep}Reagents")],
            "methyl-salicylate": [
                ("Chemical class", f"Carbonyl compounds{sep}Carboxylic "
                 f"acid derivatives{sep}Esters, Phenols"),
                ("Group", f"Purchased{sep}Starting materials")],
            "new-compound-7": [
                ("Article no.", "NV-0007"),
                ("Chemical class", "Carbonyl compounds"),
                ("Group", f"Synthesised{sep}Final products")],
        }
        for key, pairs in expected.items():
            with self.subTest(compound=key):
                self.assertEqual(self.declared_pairs(key), pairs)

    def test_every_registry_value_is_written_as_stated(self) -> None:
        """Scenario: Registry fields in English (on every compound page
        and in the compound directory)."""
        fields, registry = self.fields(), self.registry()
        columns = [field for field in fields if field.column]
        model = next(m for m in self.catalogue_page().tables()
                     if m.node.has_class("compound-table"))
        rows = {row[0].text: row for row in model.rows[1:]}
        for key, compound in registry.items():
            with self.subTest(compound=key):
                self.assertEqual(
                    self.declared_pairs(key),
                    [(field.label, text) for field, text in fs.shown(
                        fields, compound, self.LOCALE, page=True)])
                cells = rows[self.shown(key)][4:4 + len(columns)]
                self.assertEqual(
                    [cell.text for cell in cells],
                    [fs.value_text(field, compound[field.key],
                                   self.LOCALE, page=False)
                     if field.key in compound else ""
                     for field in columns])

    def test_a_registry_field_shows_only_where_the_substance_has_it(
            self) -> None:
        """Requirement: Registry fields (a substance without a value of
        a field does not have that field)."""
        numbered = 0
        for key, compound in self.registry().items():
            with self.subTest(compound=key):
                labels = [label for label, _ in self.declared_pairs(key)]
                for name, label in (("article_number", "Article no."),
                                    ("short_name", "Short name")):
                    self.assertEqual(name in compound, label in labels)
                numbered += "article_number" in compound
                self.assertEqual(labels[-2:], ["Chemical class", "Group"])
        self.assertEqual(numbered, 7)

    def test_no_page_shows_a_stock_or_a_made_in_house_field(self) -> None:
        """Requirement: Registry fields (no compound field is declared
        or shown beyond the four)."""
        for key in self.registry():
            labels = [label for label, _ in self.declared_pairs(key)]
            with self.subTest(compound=key):
                self.assertFalse({"Stock", "Made in house", "Item no."}
                                 & set(labels))

    def test_the_parts_come_in_order(self) -> None:
        """Scenario: A page per compound (order of the parts)."""
        routed = self.route_data()
        for key in self.registry():
            page = self.compound_page(key)
            main = page.find("main")
            with self.subTest(compound=key):
                parts = [main.find("h1"), main.find("dl", "compound-facts")]
                for cls in ("compound-made-by", "compound-used-in",
                            "compound-sequences", "compound-routes"):
                    wanted = {
                        "compound-made-by": self.made_by(key),
                        "compound-used-in": self.used_in_by(key),
                        "compound-sequences": ss.sequences_making(
                            key, self.sequences()),
                        "compound-routes": key in routed}[cls]
                    section = main.find("section", cls)
                    self.assertEqual(section is not None, bool(wanted), cls)
                    if section is not None:
                        parts.append(section)
                order = [page.index_of(n) for n in parts]
                self.assertEqual(order, sorted(order))
                if key in routed:
                    self.assertIs(main.elements()[-1], parts[-1])

    def test_made_by_and_used_in(self) -> None:
        """Scenario: Made by and used in."""
        salicylic = self.compound_page("salicylic-acid")
        made = salicylic.find("section", "compound-made-by")
        self.assertEqual([h.norm() for h in made.find_all("h2")],
                         ["Made by"])
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylic acid · 80 % · draft"])
        used = salicylic.find("section", "compound-used-in")
        self.assertEqual([h.norm() for h in used.find_all("h2")],
                         ["Used in"])
        self.assertEqual(
            [li.norm() for li in used.find_all("li")],
            ["OSDB-0002 Aspirin (acetylsalicylic acid) · draft"])
        methyl = self.compound_page("methyl-salicylate")
        self.assertIsNone(methyl.find("section", "compound-made-by"))
        used = methyl.find("section", "compound-used-in")
        self.assertEqual([li.norm() for li in used.find_all("li")],
                         ["OSDB-0001 Salicylic acid · draft"])

    def test_every_made_by_and_used_in_list_follows_the_content(
            self) -> None:
        """Scenario: Made by and used in (all compounds)."""
        for key in self.registry():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                for cls, items in (
                        ("compound-made-by", self.made_by_entries(key)),
                        ("compound-used-in",
                         [(i, None, None) for i in self.used_in_by(key)])):
                    section = page.find("section", cls)
                    if not items:
                        self.assertIsNone(section, cls)
                        continue
                    entries = section.find("ul").find_all("li")
                    self.assertEqual(len(entries), len(items))
                    for entry, (item, number, made) in zip(entries, items):
                        link = entry.elements()[0]
                        self.assertEqual(link.tag, "a")
                        self.assertEqual(page.resolve(link.attrs["href"]),
                                         f"/procedures/{item.slug}/")
                        self.assertEqual(link.norm(),
                                         f"{item.id} {item.title}")
                        badge = entry.find("span", "badge")
                        self.assertIsNotNone(badge, "no status badge")
                        self.assertIn(f"badge--{item.data['status']}",
                                      badge.classes)
                        self.assertEqual(badge.norm(), item.data["status"])
                        text = f"{item.id} {item.title}"
                        if number is not None:
                            text += f" · entry {number}"
                        if cls == "compound-made-by":
                            text += f" · {made} %"
                        self.assertEqual(
                            entry.norm(), f"{text} · {badge.norm()}")

    def test_route_trees_follow_the_data(self) -> None:
        """Scenario: Route trees follow the data."""
        data = self.check_route_trees()
        self.assertEqual(set(data), {
            "acetylsalicylic-acid", "1-biphenyl-4-yl-ethanol",
            "cinnamic-acid"})
        for key in ("salicylic-acid", "4-acetylbiphenyl",
                    "methyl-salicylate"):
            with self.subTest(compound=key):
                self.assertIsNone(self.compound_page(key).find(
                    "section", "compound-routes"))

    def test_the_route_of_aspirin(self) -> None:
        """Scenario: The route of aspirin."""
        page = self.compound_page("acetylsalicylic-acid")
        (step,) = self.route_tree(page).elements()
        link, between, badge, nested = self.step_parts(step)
        self.assertEqual(link.norm(),
                         "OSDB-0002 Aspirin (acetylsalicylic acid)")
        self.assertEqual(between, " · 75 % · ")
        self.assertEqual((badge.norm(), badge.has_class("badge--draft")),
                         ("draft", True))
        salicylic, anhydride = self.compound_items(nested)
        self.assertEqual([self.compound_link(page, i)
                          for i in (salicylic, anhydride)],
                         ["salicylic-acid", "acetic-anhydride"])
        self.assertEqual([n.tag for n in anhydride.elements()
                          if n.tag == "ul"], [])
        (inner,) = [n for n in salicylic.elements() if n.tag == "ul"]
        (made,) = inner.elements()
        link, between, _, nested = self.step_parts(made)
        self.assertTrue(link.norm().startswith("OSDB-0001 "), link.norm())
        self.assertEqual(between, " · 80 % · ")
        (methyl,) = self.compound_items(nested)
        self.assertEqual(self.compound_link(page, methyl),
                         "methyl-salicylate")
        self.assertEqual([n for n in methyl.elements() if n.tag == "ul"],
                         [])
        self.assertEqual(page.find_all("span", "route-more"), [])

    def test_two_steps_to_one_compound(self) -> None:
        """Scenario: Two steps to one compound."""
        page = self.compound_page("1-biphenyl-4-yl-ethanol")
        first, second = self.route_tree(page).elements()
        for item, ident, between in (
                (first, "OSDB-0005", " · 90 % · "),
                (second, "OSDB-0009", " · entry 1 · 90 % · ")):
            with self.subTest(step=ident):
                link, found, _, nested = self.step_parts(item)
                self.assertTrue(link.norm().startswith(f"{ident} "),
                                link.norm())
                self.assertEqual(found, between)
                (acetylbiphenyl,) = self.compound_items(nested)
                self.assertEqual(self.compound_link(page, acetylbiphenyl),
                                 "4-acetylbiphenyl")
                (inner,) = [n for n in acetylbiphenyl.elements()
                            if n.tag == "ul"]
                (made,) = inner.elements()
                link, found, _, _ = self.step_parts(made)
                self.assertTrue(link.norm().startswith("OSDB-0004 "),
                                link.norm())
                self.assertEqual(found, " · 85 % · ")

    def test_the_sequences_that_make_a_compound(self) -> None:
        """Scenario: Links to the demo sequence (the compound pages)."""
        sequences = self.sequences()
        self.assertEqual([s.id for s in sequences], ["SEQ-0001", "SEQ-0002"])
        for key in self.registry():
            with self.subTest(compound=key):
                ss.check_compound_sequences(
                    self, self.compound_page(key), key, sequences, "en")
        page = self.compound_page("acetylsalicylic-acid")
        section = page.find("section", "compound-sequences")
        self.assertEqual(
            [(l.target, l.node.norm()) for l in page.links(section)],
            [("/sequences/seq-0001/", "Aspirin from oil of wintergreen")])
        self.assertLess(page.index_of(page.find("dl", "compound-facts")),
                        page.index_of(section))

    def test_made_by_an_entry_of_a_general_procedure(self) -> None:
        """Scenario: Made by an entry of a general procedure."""
        page = self.compound_page("1-biphenyl-4-yl-ethanol")
        made = page.find("section", "compound-made-by")
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · 90 % · draft",
             "OSDB-0009 Secondary benzylic alcohols by sodium borohydride "
             "reduction · entry 1 · 90 % · draft"])
        self.assertIsNone(page.find("section", "compound-used-in"))
        acetylbiphenyl = self.compound_page("4-acetylbiphenyl")
        used = acetylbiphenyl.find("section", "compound-used-in")
        self.assertEqual(
            [li.norm() for li in used.find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · draft",
             "OSDB-0009 Secondary benzylic alcohols by sodium borohydride "
             "reduction · draft"])
        for key in ("acetophenone", "1-phenylethanol",
                    "1-4-bromophenyl-ethanol"):
            self.assertTrue((self.public / "compounds" / key
                             / "index.html").is_file(), key)

    def test_compound_pages_are_not_indexed(self) -> None:
        """Scenario: Compound pages are not indexed."""
        for key in self.registry():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                self.assertEqual(page.find_all(data_pagefind_body=True), [])
                sources = [page.resolve(s) for s in page.script_sources()
                           if s]
                self.assertTrue(sources)
                for source in sources:
                    self.assertRegex(source, r"^/js/site\.")
        page = self.compound_page("isopentyl-acetate")
        image = page.find("figure", "structure").find("img")
        self.assertEqual(
            ps.target_file(self.public, page.resolve(image.attrs["src"])),
            self.public / "structures" / "isopentyl-acetate.svg")
        self.assertTrue((self.public / "structures"
                         / "isopentyl-acetate.svg").is_file())

    def test_the_directory_lists_every_compound(self) -> None:
        """Scenario: Every compound is listed."""
        path = self.public / "compounds" / "index.html"
        self.assertTrue(path.is_file(), "compounds/ was not built")
        page = ps.load_page(self.public, path)
        main = page.find("main")
        self.assertEqual([h.norm() for h in main.find_all("h1")],
                         ["Compounds"])
        self.assertEqual(page.title(), "Compounds | OrgSynDB")
        self.assertEqual(main.find_all("form"), [])
        tables = main.find_all("table", "compound-table")
        self.assertEqual(len(tables), 1)
        model = next(m for m in page.tables() if m.node is tables[0])
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Compound", "Formula", "MW", "CAS", "Article no.",
                          "Chemical class", "Made by", "Used in"])
        columns = [f for f in self.fields() if f.column]
        self.assertEqual([f.key for f in columns],
                         ["article_number", "chemical_class"])
        registry = self.registry()
        names = {self.shown(key): key for key in registry}
        self.assertEqual(len(names), len(registry), "names are not unique")
        rows = [tr for tr in tables[0].find_all("tr") if tr.find("td")]
        self.assertEqual(len(rows), len(registry))
        listed = []
        for row in rows:
            cells = [c for c in row.elements() if c.tag in ("td", "th")]
            self.assertEqual(len(cells), 8)
            link = page.links(cells[0])[0]
            key = names[link.node.norm()]
            listed.append(link.node.norm())
            compound = registry[key]
            with self.subTest(compound=key):
                self.assertEqual(link.target, f"/compounds/{key}/")
                self.assertEqual(cells[1].norm(), compound.get("formula", ""))
                self.assertEqual(
                    [s.norm() for s in cells[1].find_all("sub")],
                    re.findall(r"[0-9]+", compound.get("formula", "")))
                self.assertEqual(
                    cells[2].norm(),
                    f"{compound['mw']} g/mol" if "mw" in compound else "")
                self.assertEqual(cells[3].norm(), compound.get("cas", ""))
                texts = {f.key: text for f, text in fs.shown(
                    columns, compound, self.LOCALE, page=False)}
                for cell, field in zip(cells[4:6], columns):
                    self.assertEqual(cell.norm(), texts.get(field.key, ""),
                                     field.key)
                self.assertEqual(cells[6].norm(),
                                 str(len(self.made_by(key))))
                self.assertEqual(cells[7].norm(),
                                 str(len(self.used_in_by(key))))
        self.assertEqual(listed, sorted(names))
        self.assertEqual(len(set(listed)), len(listed))

    def test_a_substance_without_formula_mass_or_cas_has_empty_cells(
            self) -> None:
        """Scenario: Empty cells."""
        page = ps.load_page(self.public, self.public / "compounds"
                            / "index.html")
        model = next(m for m in page.tables()
                     if m.node.has_class("compound-table"))
        rows = {r[0].text: r for r in model.rows[1:]}
        self.assertEqual([c.text for c in rows["New compound 7"][1:5]],
                         ["", "", "", "NV-0007"])
        self.assertEqual(
            rows["Acetylsalicylic acid"][4].text, "CH-0010")

    def test_the_directory_writes_a_choice_as_its_own_labels(self) -> None:
        """Scenario: Every compound is listed (the column fields)."""
        page = ps.load_page(self.public, self.public / "compounds"
                            / "index.html")
        model = next(m for m in page.tables()
                     if m.node.has_class("compound-table"))
        rows = {r[0].text: r for r in model.rows[1:]}
        self.assertEqual(
            [c.text for c in rows["Acetylsalicylic acid"][4:6]],
            ["CH-0010", "Carboxylic acids, Esters"])
        self.assertEqual(
            [c.text for c in rows[self.shown("4-bromoacetophenone")][4:6]],
            ["", "Aryl halides, Aryl ketones"])
        self.assertEqual(
            [c.text for c in rows["Benzaldehyde"][4:6]],
            ["", "Aldehydes"])

    def test_the_compound_catalogue_in_the_html(self) -> None:
        """Scenario: The compound catalogue in the HTML."""
        page = self.catalogue_page()
        block = self.check_compound_catalogue(page)
        self.assertEqual(
            block.find("p", "catalogue-count").norm(), "21 compounds")
        self.assertEqual(len(self.registry()), 21)
        facets = block.find("div", "catalogue-facets")
        groups = facets.find_all("details", "facet")
        self.assertEqual([(g.attrs.get("data-facet"),
                           g.find("summary").norm()) for g in groups],
                         [("chemical_class", "Chemical class"),
                          ("group", "Group")])

    def test_the_rows_carry_their_values(self) -> None:
        """Scenario: The compound catalogue in the HTML (the rows)."""
        page = self.catalogue_page()
        rows = self.check_compound_rows(page)
        self.assertEqual(len(rows), 21)
        classes = json.loads(
            rows["4-bromoacetophenone"].attrs["data-chemical_class"])
        self.assertEqual(
            sorted(classes),
            sorted(["aryl-ketones", "ketones", "carbonyl-compounds",
                    "aryl-halides"]))
        self.assertEqual(len(classes), 4)

    def test_the_facet_values_and_their_depths(self) -> None:
        """Scenario: The compound catalogue in the HTML (the facet
        values, labels, order and depths)."""
        page = self.catalogue_page()
        group = page.find("details", "facet", data_facet="chemical_class")
        shown = [(box.attrs["value"], label.find("span", "facet-label")
                  .norm(), DEPTH.match(ps.squash(label.attrs["style"]))
                  .group(1))
                 for label in group.find_all("label", "facet-value")
                 for box in [label.find("input")]]
        self.assertEqual(
            {value: (label, depth) for value, label, depth in shown},
            {"carbonyl-compounds": ("Carbonyl compounds", "0"),
             "aldehydes": ("Aldehydes", "1"),
             "ketones": ("Ketones", "1"),
             "aryl-ketones": ("Aryl ketones", "2"),
             "carboxylic-acids": ("Carboxylic acids", "1"),
             "acid-derivatives": ("Carboxylic acid derivatives", "1"),
             "esters": ("Esters", "2"), "anhydrides": ("Anhydrides", "2"),
             "alcohols": ("Alcohols", "0"), "phenols": ("Phenols", "0"),
             "aryl-halides": ("Aryl halides", "0"),
             "organoboron-compounds": ("Organoboron compounds", "0"),
             "organophosphorus-compounds": (
                 "Organophosphorus compounds", "0")})
        self.assertEqual(len(shown), 13)

    def test_a_choice_value_is_listed_when_a_compound_sets_it_or_below(
            self) -> None:
        """Requirement: Compound catalogue (facet values of a choice
        field)."""
        page = self.catalogue_page()
        listed = {value for value, _ in
                  ps.facet_values(page, "chemical_class")}
        field = next(f for f in self.fields() if f.key == "chemical_class")
        sets = {v for c in self.registry().values()
                for v in c.get("chemical_class", [])}
        wanted = set(sets)
        for value in sets:
            wanted |= set(field.ancestors[value])
        self.assertEqual(listed, wanted)
        self.assertIn("carbonyl-compounds", listed)
        self.assertIn("acid-derivatives", listed)
        self.assertNotIn("acid-derivatives", sets)

    def test_the_search_texts(self) -> None:
        """Scenario: The compound catalogue in the HTML (data-text)."""
        rows = self.check_compound_rows(self.catalogue_page())
        text = rows["acetylsalicylic-acid"].attrs["data-text"]
        self.assertEqual(
            text, "Acetylsalicylic acid Acetylsalicylsäure C9H8O4 50-78-2 "
                  "CC(=O)Oc1ccccc1C(=O)O CH-0010 ASA")
        text = rows["salicylic-acid"].attrs["data-text"]
        self.assertEqual(
            text, "Salicylic acid Salicylsäure C7H6O3 69-72-7 "
                  "OC(=O)c1ccccc1O")
        self.assertEqual(rows["new-compound-7"].attrs["data-text"],
                         "New compound 7 Neuverbindung 7 NV-0007")
        for key, row in rows.items():
            self.assertNotIn("  ", row.attrs["data-text"], key)

    def test_the_header_search_searches_compounds(self) -> None:
        """Scenario: The compound catalogue in the HTML (the header's
        form)."""
        self.check_compound_header_search(self.catalogue_page())

    # --- the compound tabs ---------------------------------------------

    def test_the_tab_pages_are_the_top_level_values(self) -> None:
        """Scenario: Tabs in the HTML (no other tab page)."""
        group = self.public / "compounds" / "group"
        self.assertEqual(
            sorted(p.name for p in group.iterdir()),
            ["purchased", "synthesised"])
        self.assertEqual(
            sorted(p.parent.name for p in group.glob("*/index.html")),
            ["purchased", "synthesised"])
        self.assertEqual(self.tab_values(), ["purchased", "synthesised"])

    def test_the_compound_tabs_open_the_catalogue_and_both_tab_pages(
            self) -> None:
        """Scenario: Tabs in the HTML (the tabs)."""
        self.check_compound_tabs(self.catalogue_page(), None)
        for value, label in (("purchased", "Purchased"),
                             ("synthesised", "Synthesised")):
            page = self.tab_page(Tab("group", value))
            with self.subTest(tab=value):
                self.check_compound_tabs(page, Tab("group", value))
                tabs = page.find("main").elements()[0]
                self.assertEqual(
                    [(l.target, l.node.norm()) for l in page.links(tabs)],
                    [("/compounds/", "All compounds"),
                     ("/compounds/group/purchased/", "Purchased"),
                     ("/compounds/group/synthesised/", "Synthesised")])
                self.assertEqual(tabs.attrs.get("aria-label"), "Group")
                self.assertEqual(page.find("h1").norm(), label)

    def test_the_catalogue_page_marks_its_own_tab(self) -> None:
        """Scenario: Tabs in the HTML (the page's own link)."""
        page = self.catalogue_page()
        tabs = page.find("main").elements()[0]
        marked = {l.target: l.node.attrs["aria-current"]
                  for l in page.links(tabs)
                  if "aria-current" in l.node.attrs}
        self.assertEqual(marked, {"/compounds/": "page"})

    def test_the_purchased_page_lists_the_purchased_compounds(self) -> None:
        """Scenario: Tabs in the HTML (the Purchased page's rows, h1,
        count and facets)."""
        tab = Tab("group", "purchased")
        page = self.check_tab_page(tab)
        self.assertEqual(
            [r.attrs["data-id"] for r in self.catalogue_rows(page)],
            sorted(PURCHASED, key=self.shown))
        self.assertEqual(page.find("h1").norm(), "Purchased")
        self.assertEqual(page.find("p", "catalogue-count").norm(),
                         "10 compounds")
        self.assertEqual(dict(ps.facet_values(page, "group")),
                         {"starting-materials": "Starting materials",
                          "reagents": "Reagents"})
        group = page.find("details", "facet", data_facet="group")
        depths = [DEPTH.match(ps.squash(label.attrs["style"])).group(1)
                  for label in group.find_all("label", "facet-value")]
        self.assertEqual(depths, ["0", "0"])
        self.assertNotIn("purchased",
                         [v for v, _ in ps.facet_values(page, "group")])

    def test_the_purchased_page_filters_by_what_its_rows_carry(self) -> None:
        """Scenario: Tabs in the HTML (the chemical_class facet)."""
        page = self.tab_page(Tab("group", "purchased"))
        carried = {value for key in PURCHASED
                   for value in fs.values_set(
                       next(f for f in self.fields()
                            if f.key == "chemical_class"),
                       self.registry()[key])}
        listed = {value for value, _ in
                  ps.facet_values(page, "chemical_class")}
        self.assertEqual(listed, carried)
        self.assertIn("organoboron-compounds", listed)

    def test_the_synthesised_page_lists_the_synthesised_compounds(
            self) -> None:
        """Scenario: Tabs in the HTML (the Synthesised page)."""
        page = self.check_tab_page(Tab("group", "synthesised"))
        self.assertEqual(
            [r.attrs["data-id"] for r in self.catalogue_rows(page)],
            sorted(SYNTHESISED, key=self.shown))
        self.assertEqual(page.find("p", "catalogue-count").norm(),
                         "11 compounds")
        self.assertEqual(dict(ps.facet_values(page, "group")),
                         {"intermediates": "Intermediates",
                          "final-products": "Final products"})
        self.assertEqual(
            {value for value, _ in ps.facet_values(page, "chemical_class")},
            {"carbonyl-compounds", "ketones", "aryl-ketones",
             "carboxylic-acids", "acid-derivatives", "esters", "alcohols",
             "phenols", "aryl-halides"})

    def test_a_row_of_a_tab_carries_the_tabs_own_value(self) -> None:
        """Requirement: Compound tabs (the rows as the catalogue's)."""
        rows = {r.attrs["data-id"]: r for r in self.catalogue_rows(
            self.tab_page(Tab("group", "purchased")))}
        self.assertEqual(
            sorted(json.loads(rows["acetone"].attrs["data-group"])),
            ["purchased", "starting-materials"])
        self.assertEqual(
            sorted(json.loads(rows["acetic-acid"].attrs["data-group"])),
            ["purchased", "reagents"])

    def test_the_catalogue_lists_every_compound_beside_its_tabs(
            self) -> None:
        """Scenario: Tabs in the HTML (the catalogue keeps all rows)."""
        page = self.catalogue_page()
        self.assertEqual(len(self.catalogue_rows(page)), 21)
        self.assertEqual(
            dict(ps.facet_values(page, "group")),
            {"purchased": "Purchased",
             "starting-materials": "Starting materials",
             "reagents": "Reagents", "synthesised": "Synthesised",
             "intermediates": "Intermediates",
             "final-products": "Final products"})
        self.assertEqual(
            page.find("p", "catalogue-noscript").norm(),
            "Search and filters need JavaScript. Without it, this page "
            "lists every compound.")

    def test_a_compound_page_has_no_compound_tabs(self) -> None:
        """Requirement: Compound tabs (only the catalogue and its tab
        pages open with the tabs)."""
        for key in ("acetone", "salicylic-acid"):
            with self.subTest(compound=key):
                self.assertEqual(
                    self.compound_page(key).find_all("nav", "section-tabs"),
                    [])

    def test_the_header_marks_compounds_on_a_tab_page(self) -> None:
        """Scenario: Tabs in the HTML (the Compounds link)."""
        for value in ("purchased", "synthesised"):
            page = self.tab_page(Tab("group", value))
            nav = page.find("header", "site-header").find("nav")
            with self.subTest(tab=value):
                self.assertEqual(
                    {l.target: l.node.attrs["aria-current"]
                     for l in page.links(nav)
                     if "aria-current" in l.node.attrs},
                    {"/compounds/": "true"})

    def test_a_tab_page_is_not_indexed(self) -> None:
        """Requirement: Compound tabs (no data-pagefind-body)."""
        for value in ("purchased", "synthesised"):
            page = self.tab_page(Tab("group", value))
            with self.subTest(tab=value):
                self.assertEqual(page.find_all(data_pagefind_body=True), [])


class GermanCompoundTests(CompoundCase):
    """The test collection, built in German."""

    LOCALE = "de"

    def test_german_names_on_a_german_site(self) -> None:
        """Scenario: German names on a German site."""
        page = self.compound_page("salicylic-acid")
        self.assertEqual(page.find("main").find("h1").norm(), "Salicylsäure")
        self.assertEqual(page.title(), "Salicylsäure | OrgSynDB")
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        registry = self.registry()
        table = directory.find("table", "compound-table")
        links = [directory.links(row)[0] for row in table.find_all("tr")
                 if directory.links(row)]
        names = [l.node.norm() for l in links]
        self.assertIn("Salicylsäure", names)
        self.assertEqual(names, sorted(
            registry[key]["name_de"] for key in registry))
        link = next(l for l in links if l.node.norm() == "Salicylsäure")
        self.assertEqual(link.target, "/compounds/salicylic-acid/")
        procedure = ps.load_page(self.public, self.public / "procedures"
                                 / "osdb-0001" / "index.html")
        product = procedure.find("dl", "metadata")
        pair = next(p for p in procedure.definition_pairs(product)
                    if p.label == "Produkt")
        self.assertEqual([l.norm() for l in pair.definition.find_all("a")],
                         ["Salicylsäure"])


    def test_the_german_compound_catalogue(self) -> None:
        """Scenario: German page shell (the compound catalogue)."""
        page = self.catalogue_page()
        block = self.check_compound_catalogue(page)
        self.assertEqual(
            block.find("p", "catalogue-count").norm(), "21 Verbindungen")
        self.assertEqual(page.find("main").find("h1").norm(), "Verbindungen")
        groups = block.find_all("details", "facet")
        self.assertEqual([(g.attrs.get("data-facet"),
                           g.find("summary").norm()) for g in groups],
                         [("chemical_class", "Stoffklasse"),
                          ("group", "Gruppe")])
        classes = dict(ps.facet_values(page, "chemical_class"))
        self.assertEqual(classes["ketones"], "Ketone")
        self.assertEqual(classes["carbonyl-compounds"],
                         "Carbonylverbindungen")
        self.assertEqual(classes["acid-derivatives"],
                         "Carbonsäurederivate")
        self.assertEqual(block.find("button", "clear-all").norm(),
                         "Alles zurücksetzen")
        self.assertEqual(block.find("button", "facets-toggle").norm(),
                         "Filter")
        self.assertEqual(block.find("div", "catalogue-facets").find("h2")
                         .norm(), "Filter")
    def test_tabs_in_german(self) -> None:
        """Scenario: Tabs in German."""
        page = self.tab_page(Tab("group", "purchased"))
        tabs = page.find("main").elements()[0]
        self.assertEqual([l.node.norm() for l in page.links(tabs)],
                         ["Alle Verbindungen", "Zugekauft",
                          "Selbst hergestellt"])
        self.assertEqual(tabs.attrs.get("aria-label"), "Gruppe")
        self.assertEqual(page.find("main").find("h1").norm(), "Zugekauft")
        field = page.find("header", "site-header").find("input", name="q")
        self.assertEqual(field.get("aria-label"),
                         "Verbindungen durchsuchen: Zugekauft")
        self.assertEqual(
            page.find("p", "catalogue-noscript").norm(),
            "Suche und Filter brauchen JavaScript. Ohne JavaScript zeigt "
            "diese Seite alle Verbindungen dieses Reiters.")

    def test_the_german_tab_pages(self) -> None:
        """Scenario: Tabs in German (every part of both tab pages)."""
        self.check_compound_tabs(self.catalogue_page(), None)
        for value in ("purchased", "synthesised"):
            with self.subTest(tab=value):
                page = self.check_tab_page(Tab("group", value))
                self.assertEqual(
                    page.find("p", "catalogue-count").norm(),
                    {"purchased": "10 Verbindungen",
                     "synthesised": "11 Verbindungen"}[value])
                self.assertEqual(
                    page.find("details", "facet", data_facet="group")
                    .find("summary").norm(), "Gruppe")
        self.assertEqual(
            dict(ps.facet_values(self.tab_page(Tab("group", "purchased")),
                                 "group")),
            {"starting-materials": "Ausgangsstoffe",
             "reagents": "Reagenzien"})

    def test_the_german_rows(self) -> None:
        """Scenario: The compound catalogue in the HTML (a German
        site's rows)."""
        rows = self.check_compound_rows(self.catalogue_page())
        self.assertEqual(rows["salicylic-acid"].attrs["data-title"],
                         "Salicylsäure")
        self.assertEqual(
            rows["salicylic-acid"].attrs["data-text"],
            "Salicylic acid Salicylsäure C7H6O3 69-72-7 OC(=O)c1ccccc1O")

    def test_the_german_header_search(self) -> None:
        """Scenario: German page shell (the header search on
        /compounds/)."""
        page = self.catalogue_page()
        form = page.find("header", "site-header").find("form")
        field = form.find("input", name="q")
        self.assertEqual(
            (field.get("aria-label"), field.get("placeholder"),
             form.find("button").norm()),
            ("Verbindungen durchsuchen",
             "Name, Summenformel, CAS oder SMILES", "Suchen"))
        self.assertEqual(page.resolve(form.attrs.get("action", "")),
                         "/compounds/")

    def test_german_labels_on_compound_pages(self) -> None:
        """Scenario: German page shell (compound pages)."""
        page = self.compound_page("salicylic-acid")
        facts = page.find("dl", "compound-facts")
        self.assertEqual([p.label for p in page.definition_pairs(facts)],
                         ["Summenformel", "Molmasse", "CAS", "SMILES",
                          "Stoffklasse", "Gruppe"])
        values = {p.label: p.definition.norm()
                  for p in page.definition_pairs(facts)}
        self.assertEqual(values["Molmasse"], "138,12 g/mol")
        self.assertEqual(page.find("button", "copy-button").norm(),
                         "Kopieren")
        made = page.find("section", "compound-made-by")
        self.assertEqual([h.norm() for h in made.find_all("h2")],
                         ["Hergestellt nach"])
        used = page.find("section", "compound-used-in")
        self.assertEqual([h.norm() for h in used.find_all("h2")],
                         ["Verwendet in"])
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylsäure · 80 % · Entwurf"])
        aspirin = self.compound_page("acetylsalicylic-acid")
        sequences = aspirin.find("section", "compound-sequences")
        self.assertEqual([h.norm() for h in sequences.find_all("h2")],
                         ["Synthesewege"])
        self.assertEqual(
            [(l.target, l.node.norm()) for l in aspirin.links(sequences)],
            [("/sequences/seq-0001/", "Aspirin aus Wintergrünöl")])
        general = self.compound_page("1-biphenyl-4-yl-ethanol")
        self.assertEqual(
            [li.norm() for li in general.find(
                "section", "compound-made-by").find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · 90 % · Entwurf",
             "OSDB-0009 Sekundäre Benzylalkohole durch Reduktion mit "
             "Natriumborhydrid · Eintrag 1 · 90 % · Entwurf"])
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        table = directory.find("table", "compound-table")
        model = next(m for m in directory.tables() if m.node is table)
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Verbindung", "Summenformel", "Molmasse", "CAS",
                          "Artikelnr.", "Stoffklasse", "Hergestellt nach",
                          "Verwendet in"])
        row = next(m for m in model.rows[1:]
                   if m[0].text == "Salicylsäure")
        self.assertEqual(row[2].text, "138,12 g/mol")
        self.assertEqual([c.text for c in row[4:6]],
                         ["", "Carbonsäuren, Phenole"])
        row = next(m for m in model.rows[1:]
                   if m[0].text == "(E)-Zimtsäure")
        self.assertEqual(row[4].text, "CH-0012")

    def test_a_german_route_tree(self) -> None:
        """Scenario: A German route tree."""
        page = self.compound_page("1-biphenyl-4-yl-ethanol")
        section = page.find("section", "compound-routes")
        self.assertIsNotNone(section, "no section.compound-routes")
        self.assertEqual([h.norm() for h in section.find_all("h2")],
                         ["Herstellungswege"])
        self.assertEqual(
            [p.norm() for p in section.find_all("p", "routes-intro")],
            ["Wege zu dieser Verbindung aus den Vorschriften der Sammlung, "
             "jede Stufe mit ihren Ausgangsstoffen."])
        first, second = self.route_tree(page).elements()
        self.assertEqual(self.step_parts(first)[1], " · 90 % · ")
        self.assertEqual(self.step_parts(second)[1],
                         " · Eintrag 1 · 90 % · ")
        self.check_route_trees()

    def test_registry_fields_in_german(self) -> None:
        """Scenario: Registry fields in German."""
        carbonyl = "Carbonylverbindungen"
        expected = {
            "cinnamic-acid": [
                ("Artikelnr.", "CH-0012"),
                ("Stoffklasse", f"{carbonyl}{SEPARATOR}Carbonsäuren"),
                ("Gruppe", f"Selbst hergestellt{SEPARATOR}Endprodukte")],
            "acetic-acid": [
                ("Kurzname", "AcOH"),
                ("Stoffklasse", f"{carbonyl}{SEPARATOR}Carbonsäuren"),
                ("Gruppe", f"Zugekauft{SEPARATOR}Reagenzien")],
            "salicylic-acid": [
                ("Stoffklasse", f"{carbonyl}{SEPARATOR}Carbonsäuren, "
                                "Phenole"),
                ("Gruppe", f"Selbst hergestellt{SEPARATOR}"
                           "Zwischenprodukte")],
            "methyl-salicylate": [
                ("Stoffklasse", SEPARATOR.join(
                    [carbonyl, "Carbonsäurederivate", "Ester"])
                 + ", Phenole"),
                ("Gruppe", f"Zugekauft{SEPARATOR}Ausgangsstoffe")],
        }
        for key, pairs in expected.items():
            with self.subTest(compound=key):
                self.assertEqual(self.declared_pairs(key), pairs)

    def test_every_registry_value_reads_as_the_fields_say(self) -> None:
        """Scenario: Registry fields in German (every compound)."""
        fields = self.fields()
        self.assertEqual([f.label for f in fields],
                         ["Artikelnr.", "Kurzname", "Stoffklasse",
                          "Gruppe"])
        for key, compound in self.registry().items():
            with self.subTest(compound=key):
                self.assertEqual(
                    self.declared_pairs(key),
                    [(f.label, text) for f, text in fs.shown(
                        fields, compound, "de", page=True)])


class AncestorBesideValueTests(CompoundCase):
    """The test collection in English, with acetone in the chemical
    classes `carbonyl-compounds` and `ketones`."""

    @classmethod
    def prepare(cls) -> None:
        ps.edit_snapshot(cls.sandbox, support.setting_substance(
            "acetone", chemical_classes=["carbonyl-compounds", "ketones"]))

    def test_a_value_set_beside_its_ancestor(self) -> None:
        """Scenario: A value set beside its ancestor."""
        rows = self.check_compound_rows(self.catalogue_page())
        listed = json.loads(rows["acetone"].attrs["data-chemical_class"])
        self.assertEqual(sorted(listed), ["carbonyl-compounds", "ketones"])
        self.assertEqual(len(listed), 2)


class MarkupFieldTests(CompoundCase):
    """The test collection in English, with markup characters in the
    `short_name` of `acetone` and in the label of the chemical class
    `ketones`."""

    LABEL = "Ketones <b>&</b>"
    VALUE = "<i>Me</i>2CO & co"

    @classmethod
    def prepare(cls) -> None:
        def relabel(table: dict) -> None:
            (found,) = [t for t in table["vocabularies"]["chemical-classes"]
                        if t["key"] == "ketones"]
            found["label"] = cls.LABEL
        ps.edit_snapshot(
            cls.sandbox, relabel,
            support.setting_substance("acetone", short_name=cls.VALUE))

    def test_markup_in_a_label_or_a_value_is_text(self) -> None:
        """Scenario: Markup in a label or a value is text."""
        page = self.compound_page("acetone")
        facts = page.find("main").find("dl", "compound-facts")
        pairs = {p.label: p for p in page.definition_pairs(facts)}
        self.assertIn("Short name", pairs, sorted(pairs))
        self.assertEqual(pairs["Short name"].definition.text().strip(),
                         self.VALUE)
        self.assertEqual(facts.find_all("b"), [])
        self.assertEqual(facts.find_all("i"), [])
        ketone = self.compound_page("dibenzylideneacetone")
        facts = ketone.find("main").find("dl", "compound-facts")
        pairs = {p.label: p for p in ketone.definition_pairs(facts)}
        self.assertTrue(
            pairs["Chemical class"].definition.text().strip().endswith(
                self.LABEL))
        self.assertEqual(facts.find_all("b"), [])
        self.assertEqual(facts.find_all("i"), [])

    def starting_materials(self, ident: str) -> tuple[Page, Node]:
        """The page of the procedure ``ident`` and the value of its
        `Starting materials` pair."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / ident.lower() / "index.html")
        pair = self.panel(page)["Starting materials"]
        return page, pair.definition

    def test_markup_in_a_value_beside_a_link_is_text(self) -> None:
        """Scenario: Markup in a value, and a compound without one. The
        build's other change, the label of `short_name`, shows on the
        compound pages only, and so touches no note."""
        page, materials = self.starting_materials("OSDB-0006")
        after = fs.after_link(fs.link_to(page, materials, "acetone"))
        self.assertGreaterEqual(len(after), 2, "no note follows the link")
        self.assertEqual(after[0], " ")
        self.assertEqual((after[1].tag, after[1].classes),
                         ("span", ["compound-beside"]))
        self.assertEqual(after[1].text(), f"({self.VALUE})")
        self.assertEqual(after[1].elements(), [])
        self.assertEqual(materials.find_all("i"), [])
        self.assertEqual(materials.find_all("b"), [])
        self.assertEqual(self.check_notes(page, materials),
                         [None, f"({self.VALUE})"])

    def test_a_compound_without_a_value_beside_has_no_note(self) -> None:
        """Scenario: Markup in a value, and a compound without one (the
        procedure without markup, and the link without a note)."""
        page, materials = self.starting_materials("OSDB-0002")
        self.assertEqual(materials.norm(),
                         "Salicylic acid, Acetic anhydride (Ac2O)")
        after = fs.after_link(fs.link_to(page, materials, "salicylic-acid"))
        self.assertEqual(after[0], ", ")
        self.assertEqual(after[1].tag, "a")
        self.assertEqual(self.check_notes(page, materials),
                         [None, "(Ac2O)"])


CHAIN_PROCEDURE = """\
+++
id = "OSDB-0911"
slug = "osdb-0911"
title = "Chain of seven steps"
date = 2026-10-22T12:00:00+02:00
lastmod = 2026-10-22T12:30:00+02:00
authors = ["A. Example"]
status = "draft"
reaction_types = ["hydrolysis"]
tags = ["sample-data", "route-check"]
scale = "20 mmol"
scope = [
%s]
hazards = ["Water: no hazard"]
+++

## Summary

A fictitious general procedure whose entry n makes chain-n from
chain-(n-1). It is test data for the depth limit of a route tree.

## Reagents

| Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv |
|---|---|---|---|---|---|
| Water | 7732-18-5 | 18.02 | 0.36 g | 20 | 1.0 |

## Procedure

1. Combine the reagents.

## Workup and Purification

Concentrate.

## Characterization

Colourless liquid.

## Notes

1. Fictitious procedure.

## Hazards and Waste Disposal

Collect waste separately.

## References

None.
"""


class CycleAndDepthTests(CompoundCase):
    """A copy of the test collection, built in English after adding
    ``OSDB-0910``, which makes ``salicylic-acid`` from
    ``acetylsalicylic-acid``, and ``OSDB-0911``, a general procedure of
    seven entries, entry ``n`` making ``chain-<n>`` from
    ``chain-<n-1>``, with the substances ``chain-0`` to ``chain-7`` added
    to its registry."""

    FIXTURES = ("OSDB-0910-aspirin-hydrolysis.md",)

    @classmethod
    def prepare(cls) -> None:
        ps.edit_snapshot(cls.sandbox, *(
            support.adding_substance(support.substance(
                f"chain-{number}", f"Chain {number}", formula="C2H6",
                mw=30.07, smiles="CC", chemical_classes=["alcohols"]))
            for number in range(CHAIN_LENGTH + 1)))
        entries = "".join(
            f'  {{ substrates = ["chain-{n - 1}"], products = '
            f'[{{ compound = "chain-{n}", yield_percent = {50 + n} }}] }},\n'
            for n in range(1, CHAIN_LENGTH + 1))
        (cls.sandbox.md_dir() / "OSDB-0911-chain.md").write_text(
            CHAIN_PROCEDURE % entries, encoding="utf-8")

    def test_a_cycle_is_not_followed_on_the_page(self) -> None:
        """Scenario: A cycle and the depth limit on the page (the
        cycle)."""
        salicylic = self.compound_page("salicylic-acid")
        made = salicylic.find("section", "compound-made-by")
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylic acid · 80 % · draft",
             "OSDB-0910 Salicylic acid by hydrolysis of aspirin · 95 % · "
             "draft"])
        self.assertIsNone(salicylic.find("section", "compound-routes"))
        aspirin = self.compound_page("acetylsalicylic-acid")
        tree = self.route_tree(aspirin)
        self.assertEqual(
            [self.step_parts(li)[0].norm().split()[0]
             for li in tree.find_all("li", "route-step")],
            ["OSDB-0002", "OSDB-0001"])
        self.assertNotIn("OSDB-0910", tree.text())

    def test_the_depth_limit_cuts_a_chain_off_on_the_page(self) -> None:
        """Scenario: A cycle and the depth limit on the page (the
        depth limit)."""
        page = self.compound_page(f"chain-{CHAIN_LENGTH}")
        tree = self.route_tree(page)
        steps = tree.find_all("li", "route-step")
        self.assertEqual(len(steps), 6)
        level = tree
        for entry in range(CHAIN_LENGTH, 1, -1):
            with self.subTest(entry=entry):
                (step,) = level.elements()
                link, between, _, nested = self.step_parts(step)
                self.assertEqual(link.norm(),
                                 "OSDB-0911 Chain of seven steps")
                self.assertEqual(
                    between, f" · entry {entry} · {50 + entry} % · ")
                (item,) = self.compound_items(nested)
                self.assertEqual(self.compound_link(page, item),
                                 f"chain-{entry - 1}")
                lists = [n for n in item.elements() if n.tag == "ul"]
                level = lists[0] if lists else None
        self.assertIsNone(level, "chain-1 holds a ul")
        self.assertEqual(item.elements()[-1].tag, "span")
        more = page.find_all("span", "route-more")
        self.assertEqual([m.norm() for m in more],
                         ["more steps on its page"])
        self.assertIs(item.elements()[-1], more[0])
        self.assertTrue(
            self.own_text(item).endswith(" · more steps on its page"),
            self.own_text(item))

    def test_every_route_tree_follows_the_data(self) -> None:
        """Scenario: Route trees follow the data (the copy build)."""
        data = self.check_route_trees()
        self.assertIn("acetylsalicylic-acid", data)
        self.assertIn(f"chain-{CHAIN_LENGTH}", data)
        self.assertNotIn("salicylic-acid", data)
        self.assertNotIn("chain-1", data)


class FallbackNameTests(CompoundCase):
    """The test collection in German, with the German name of `acetone`
    removed from its registry."""

    LOCALE = "de"

    @classmethod
    def prepare(cls) -> None:
        ps.edit_snapshot(cls.sandbox, support.setting_substance(
            "acetone", name_de=None))

    def test_a_compound_without_a_german_name(self) -> None:
        """Scenario: A compound without a German name."""
        page = self.compound_page("acetone")
        name = self.registry()["acetone"]["name"]
        self.assertEqual(name, "Acetone")
        self.assertEqual(page.find("main").find("h1").norm(), name)
        self.assertEqual(page.title(), f"{name} | OrgSynDB")
        procedure = ps.load_page(self.public, self.public / "procedures"
                                 / "osdb-0006" / "index.html")
        materials = next(p for p in procedure.definition_pairs(
            procedure.find("dl", "metadata")) if p.label == "Ausgangsstoffe")
        self.assertEqual([l.norm() for l in materials.definition.find_all(
            "a")], ["Benzaldehyd", "Acetone"])


class MarkupNameTests(CompoundCase):
    """The test collection in English, with a compound whose name holds
    an apostrophe and an ampersand."""

    NAME = "N,N'-Dimethylurea & co"

    @classmethod
    def prepare(cls) -> None:
        ps.edit_snapshot(cls.sandbox, support.adding_substance(
            support.substance(
                "dimethylurea", cls.NAME, formula="C3H8N2O", mw=88.11,
                smiles="CNC(=O)NC", article_number="CH-0099",
                chemical_classes=["ketones"])))

    def test_a_name_is_escaped_once(self) -> None:
        """Scenario: A page per compound (a name with markup characters)."""
        page = self.compound_page("dimethylurea")
        self.assertEqual(page.find("main").find("h1").norm(), self.NAME)
        self.assertEqual(page.title(), f"{self.NAME} | OrgSynDB")
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        self.assertIn(self.NAME, [l.node.norm() for l in directory.links()
                                  if l.target == "/compounds/dimethylurea/"])


class StructureImageByKeyTests(CompoundCase):
    """The test collection in English, with `acetone.png`, and
    `benzaldehyde.svg` beside `benzaldehyde.png`, added to its
    `static/structures/`."""

    @classmethod
    def prepare(cls) -> None:
        structures = cls.sandbox.root / "static" / "structures"
        (structures / "acetone.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (structures / "benzaldehyde.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (structures / "benzaldehyde.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' width='1' "
            "height='1'/>", encoding="utf-8")

    def test_the_image_is_found_by_the_key(self) -> None:
        """Scenario: Image found by key."""
        for key, image in (("acetone", "structures/acetone.png"),
                           ("benzaldehyde", "structures/benzaldehyde.svg"),
                           ("isopentyl-acetate",
                            "structures/isopentyl-acetate.svg")):
            with self.subTest(compound=key):
                page = self.compound_page(key)
                (img,) = page.find("figure", "structure").find_all("img")
                self.assertEqual(page.resolve(img.attrs["src"]),
                                 "/" + image)
                self.assertEqual(self.registry()[key]["structure_image"],
                                 image)

    def test_a_substance_without_a_file_of_its_key_shows_none(self) -> None:
        """Scenario: Image found by key (no file of its key)."""
        for key in ("salicylic-acid", "new-compound-7"):
            with self.subTest(compound=key):
                page = self.compound_page(key)
                self.assertEqual(page.find("main").find_all("figure"), [])
                self.assertEqual(page.find("main").find_all("img"), [])


if __name__ == "__main__":
    import unittest
    unittest.main()
