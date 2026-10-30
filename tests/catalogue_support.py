"""Shared checks of the catalogue, term and home pages (site-catalogue,
site-theme "Home page content", localization).

``CatalogueCase`` is a build case whose helpers state the markup
contract once for both interface languages: the texts of each language
are in ``TEXTS``. The English and German test modules subclass it, and
reach it as ``cs.CatalogueCase``, so that the base is not collected.
"""

import re
from typing import Any

import pipeline_support as ps
from pipeline_support import Content, Node, Page

DATA_TEXTS = ("searching", "unavailable", "error", "error-action", "empty",
              "ignored", "remove")
DIRECTORIES = {"type": "/reaction_types/", "tag": "/tags/",
               "author": "/authors/"}
FACET_TAXONOMY = {"type": "reaction_types", "tag": "tags",
                  "author": "authors"}
TAXONOMY_FACET = {taxonomy: facet
                  for facet, taxonomy in FACET_TAXONOMY.items()}
CATALOGUE_SCRIPT = re.compile(r"^/js/catalogue\.(?:min\.)?[0-9a-f]{16,}\.js$")

TEXTS: dict[str, dict[str, Any]] = {
    "en": {
        "heading": "Procedures",
        "count_one": "1 procedure", "count_many": "{n} procedures",
        "filtered": "{shown} of {total} procedures",
        "noscript": "Search, filters and sorting need JavaScript. Without "
                    "it, this page lists its procedures by ID. Browse them "
                    "by reaction type, tag or author.",
        "noscript_links": ["reaction type", "tag", "author"],
        "header": ps.CATALOGUE_HEADER, "region": "Procedures",
        "search_label": "Search procedures",
        "placeholder": "Product, CAS, SMILES or keyword",
        "search_button": "Search",
        "search_scope": {
            "type": "Search procedures of the reaction type {term}",
            "tag": "Search procedures with the tag {term}",
            "author": "Search procedures by {term}",
            "kind": "Search general procedures"},
        "scoped_placeholder": "Search these procedures",
        "filters": "Filters",
        "facets": {"type": "Reaction type", "kind": "Kind",
                   "status": "Status", "tag": "Tag", "author": "Author"},
        "kinds": {"specific": "Specific procedure",
                  "general": "General procedure"},
        "general_heading": "General procedures",
        "directories": {"type": "All reaction types", "tag": "All tags",
                        "author": "All authors"},
        "clear": "Clear all",
        "sort_label": "Sort by",
        "sorts": [("relevance", "Relevance"), ("id", "ID"),
                  ("title", "Title (A–Z)"),
                  ("created", "Created (newest first)"),
                  ("modified", "Modified (newest first)")],
        "view_label": "View",
        "views": [("table", "Table"), ("details", "Details")],
        "status": {"draft": "draft", "checked": "checked",
                   "retired": "retired"},
        "data_text": {
            "searching": "Searching…",
            "unavailable": "Search unavailable",
            "error": "The search index could not be loaded, so the search "
                     "was not applied.",
            "error-action": "Show the list without the search",
            "empty": "No procedures match the search and filters.",
            "ignored": "Ignored in the address: {list}",
            "remove": "Remove {facet}: {value}"},
        "scope": {"type": "Only procedures of the reaction type {term}",
                  "tag": "Only procedures with the tag {term}",
                  "author": "Only procedures by {term}",
                  "kind": "Only general procedures"},
        "browse_all": "Browse all procedures",
        "home_title": "Synthetic procedures",
        "lede": "The group's procedures, written in Org or Markdown to "
                "one schema.",
        "recent": "Recently updated", "browse": "Browse",
        "recent_link": "All procedures, recently updated first",
        "unchecked": "Not yet checked",
        "unchecked_link": "All draft procedures",
        "entries": ["All procedures", "Reaction types", "Tags", "Authors",
                    "Compounds", "Sequences"],
        "thousands": ",",
    },
    "de": {
        "heading": "Vorschriften",
        "count_one": "1 Vorschrift", "count_many": "{n} Vorschriften",
        "filtered": "{shown} von {total} Vorschriften",
        "noscript": "Suche, Filter und Sortierung brauchen JavaScript. "
                    "Ohne JavaScript zeigt diese Seite ihre Vorschriften "
                    "nach ID. Weitere Listen gibt es nach Reaktionstyp, "
                    "Schlagwort oder Autor.",
        "noscript_links": None,
        "header": None, "region": None,
        "search_label": "Vorschriften durchsuchen",
        "placeholder": "Produkt, CAS, SMILES oder Stichwort",
        "search_button": "Suchen",
        "search_scope": {
            "type": "Vorschriften des Reaktionstyps {term} durchsuchen",
            "tag": "Vorschriften mit dem Schlagwort {term} durchsuchen",
            "author": "Vorschriften von {term} durchsuchen",
            "kind": "Allgemeine Vorschriften durchsuchen"},
        "scoped_placeholder": "Diese Vorschriften durchsuchen",
        "filters": "Filter",
        "facets": {"type": "Reaktionstyp", "kind": "Art",
                   "status": "Status", "tag": "Schlagwort",
                   "author": "Autor"},
        "kinds": {"specific": "Einzelvorschrift",
                  "general": "Allgemeine Vorschrift"},
        "general_heading": "Allgemeine Vorschriften",
        "directories": {"type": "Alle Reaktionstypen",
                        "tag": "Alle Schlagwörter", "author": "Alle Autoren"},
        "clear": "Alles zurücksetzen",
        "sort_label": "Sortieren nach",
        "sorts": [("relevance", "Relevanz"), ("id", "ID"),
                  ("title", "Titel (A–Z)"),
                  ("created", "Erstellt (neueste zuerst)"),
                  ("modified", "Geändert (neueste zuerst)")],
        "view_label": "Ansicht",
        "views": [("table", "Tabelle"), ("details", "Details")],
        "status": {"draft": "Entwurf", "checked": "Geprüft",
                   "retired": "Zurückgezogen"},
        "data_text": {
            "searching": "Suche läuft …",
            "unavailable": "Suche nicht verfügbar",
            "error": "Der Suchindex konnte nicht geladen werden; die Suche "
                     "wurde nicht angewendet.",
            "error-action": "Liste ohne Suche anzeigen",
            "empty": "Keine Vorschrift passt zu Suche und Filtern.",
            "ignored": "In der Adresse nicht berücksichtigt: {list}",
            "remove": "{facet}: {value} entfernen"},
        "scope": {"type": "Nur Vorschriften des Reaktionstyps {term}",
                  "tag": "Nur Vorschriften mit dem Schlagwort {term}",
                  "author": "Nur Vorschriften von {term}",
                  "kind": "Nur allgemeine Vorschriften"},
        "browse_all": "Alle Vorschriften anzeigen",
        "home_title": "Synthesevorschriften",
        "lede": "Die Vorschriften der Arbeitsgruppe, in Org oder Markdown "
                "nach einem gemeinsamen Schema geschrieben.",
        "recent": "Zuletzt geändert", "browse": "Übersicht",
        "recent_link": "Alle Vorschriften, zuletzt geänderte zuerst",
        "unchecked": "Noch nicht geprüft",
        "unchecked_link": "Alle Entwürfe",
        "entries": ["Alle Vorschriften", "Reaktionstypen", "Schlagwörter",
                    "Autoren", "Verbindungen", "Synthesewege"],
        "thousands": ".",
    },
}


def instant(item: Content) -> float:
    """The ``lastmod`` of a content file as a timestamp."""
    return item.data["lastmod"].timestamp()


class CatalogueCase(ps.ThemeBuildCase):
    """A build case with the catalogue's markup checks."""

    @property
    def texts(self) -> dict[str, Any]:
        return TEXTS[self.LOCALE]

    def labels(self) -> dict[str, str]:
        """Reaction-type slug to label in the build's language."""
        return ps.reaction_labels(self.sandbox.app, self.LOCALE)

    def page(self, relative: str) -> Page:
        """The page at ``public/<relative>``, failing when absent."""
        path = self.public / relative
        self.assertTrue(path.is_file(), f"{relative} was not published")
        return ps.load_page(self.public, path)

    def table_ids(self, page: Page) -> list[str]:
        """The ID cells of the page's procedure table, in order."""
        return [ps.row_cells(row)[0].norm()
                for row in ps.catalogue_rows(page)]

    def count_text(self, rows: int) -> str:
        key = "count_one" if rows == 1 else "count_many"
        return self.texts[key].format(n=rows)

    # --- what the content files say --------------------------------------

    def facet_labels(self) -> dict[str, dict[str, str]]:
        """Per facet, each value some published procedure carries (and
        the three statuses) with its display label."""
        labels = self.labels()
        found: dict[str, dict[str, str]] = {
            "type": {}, "kind": dict(self.texts["kinds"]),
            "status": dict(self.texts["status"]), "tag": {}, "author": {}}
        for item in self.content():
            for slug in item.data["reaction_types"]:
                found["type"][slug] = labels[slug]
            for tag in item.tags:
                found["tag"][ps.term_key("tags", tag)] = tag
            for author in item.data["authors"]:
                found["author"].setdefault(
                    ps.term_key("authors", author), author)
        return found

    def term_names(self, taxonomy: str) -> dict[str, str]:
        """Term key to display name, for the terms in use."""
        return self.facet_labels()[TAXONOMY_FACET[taxonomy]]

    # --- the catalogue block ---------------------------------------------

    def check_catalogue(self, page: Page, *, fixed: str | None,
                        heading: str) -> Node:
        """The order and content of ``div.catalogue`` up to the controls.

        Returns the ``div.catalogue``.
        """
        texts = self.texts
        mains = page.find_all("main")
        self.assertEqual(len(mains), 1)
        found = mains[0].find_all("div", "catalogue")
        self.assertEqual(len(found), 1, f"{page.url}: not one div.catalogue")
        block = found[0]
        self.assertIn("data-catalogue", block.attrs)
        if fixed is None:
            self.assertNotIn("data-fixed", block.attrs)
        else:
            self.assertEqual(block.attrs.get("data-fixed"), fixed)
        rows = ps.catalogue_rows(page)
        parts = [block.find("div", "list-head")]
        if fixed is not None:
            parts.append(block.find("p", "catalogue-scope"))
        parts += [block.find("noscript"),
                  block.find("div", "catalogue-layout")]
        for part in parts:
            self.assertIsNotNone(part, f"{page.url}: a catalogue part is "
                                 "missing")
            self.assertIs(part.parent, block)
        positions = [page.index_of(part) for part in parts]
        self.assertEqual(positions, sorted(positions))
        head = parts[0]
        self.assertEqual([h.norm() for h in head.find_all("h1")], [heading])
        count = head.find("p", "catalogue-count")
        self.assertIsNotNone(count, "no p.catalogue-count")
        self.assertEqual(count.attrs.get("role"), "status")
        self.assertIn("data-catalogue-count", count.attrs)
        self.assertEqual(count.attrs.get("data-filtered"), texts["filtered"])
        self.assertEqual(count.norm(), self.count_text(len(rows)))
        self.check_noscript(page, block.find("noscript"))
        self.check_layout(page, block)
        self.assertEqual(len(page.find_all("input", name="q")), 1)
        scripts = [page.resolve(src) for src in page.script_sources() if src]
        loaded = [s for s in scripts if CATALOGUE_SCRIPT.match(s)]
        self.assertEqual(len(loaded), 1, f"{page.url}: scripts {scripts}")
        script = next(n for n in page.find_all("script")
                      if page.resolve(n.attrs.get("src", "")) == loaded[0])
        self.assertIn("defer", script.attrs)
        return block

    def check_noscript(self, page: Page, noscript: Node) -> None:
        note = noscript.find("p", "catalogue-noscript")
        self.assertIsNotNone(note, "no p.catalogue-noscript")
        self.assertEqual(note.norm(), self.texts["noscript"])
        links = page.links(note)
        self.assertEqual([link.target for link in links],
                         ["/reaction_types/", "/tags/", "/authors/"])
        words = self.texts["noscript_links"]
        if words is not None:
            self.assertEqual([link.node.norm() for link in links], words)

    def check_layout(self, page: Page, block: Node) -> None:
        layout = block.find("div", "catalogue-layout")
        self.assertEqual([(n.tag, n.classes[:1])
                          for n in layout.elements()],
                         [("div", ["catalogue-facets"]),
                          ("div", ["catalogue-results"])])
        results = layout.elements()[1]
        toolbar = results.find("div", "catalogue-toolbar")
        message = results.find("p", "catalogue-message")
        region = results.find("div", "table-scroll")
        for part in (toolbar, message, region):
            self.assertIsNotNone(part, "a part of the results is missing")
            self.assertIs(part.parent, results)
        positions = [page.index_of(n) for n in (toolbar, message, region)]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(region.attrs.get("tabindex"), "0")
        self.assertEqual(region.attrs.get("role"), "region")
        if self.texts["region"] is None:
            self.assertTrue(region.attrs.get("aria-label", "").strip())
        else:
            self.assertEqual(region.attrs.get("aria-label"),
                             self.texts["region"])
        self.assertEqual([(n.tag, n.classes) for n in region.elements()],
                         [("table", ["procedure-list"])])
        header = self.texts["header"]
        table = page.tables()[0]
        self.assertIs(table.node, region.elements()[0])
        cells = table.rows[0]
        for cell in cells:
            self.assertEqual((cell.tag, cell.node.attrs.get("scope")),
                             ("th", "col"))
        if header is not None:
            self.assertEqual([c.text for c in cells], header)
        else:
            self.assertEqual(len(cells), 5)

    def check_general_view(self, page: Page, items: list[Content]) -> None:
        """``/general-procedures/``: a catalogue page whose rows are the
        general procedures, with the ``kind`` facet fixed to ``general``
        (general-procedures "General procedures view")."""
        texts = self.texts
        block = self.check_catalogue(page, fixed="kind",
                                     heading=texts["general_heading"])
        self.check_controls(page, fixed="kind")
        general = [item for item in items if item.is_general]
        self.assertTrue(general, "the build has no general procedure")
        self.assertEqual(page.title(),
                         f"{texts['general_heading']} | OrgSynDB")
        self.assertEqual(self.table_ids(page),
                         sorted(item.id for item in general))
        self.check_rows(page, general)
        scope = block.find("p", "catalogue-scope")
        self.assertEqual(
            scope.norm(), f"{texts['scope']['kind']} · {texts['browse_all']}")
        links = page.links(scope)
        self.assertEqual([(l.target, l.node.norm()) for l in links],
                         [("/procedures/", texts["browse_all"])])
        self.assertIn("data-browse-all", links[0].node.attrs)
        fixed = page.find("details", "facet", data_facet="kind")
        self.assertIn("data-fixed", fixed.attrs)
        self.assertIn("open", fixed.attrs)
        boxes = fixed.find_all("input")
        self.assertEqual(len(boxes), 1)
        self.assertEqual(
            {k: boxes[0].attrs.get(k) for k in ("type", "name", "value")},
            {"type": "checkbox", "name": "kind", "value": "general"})
        self.assertIn("checked", boxes[0].attrs)
        self.assertIn("disabled", boxes[0].attrs)
        self.assertEqual(ps.facet_values(page, "kind"),
                         [("general", texts["kinds"]["general"])])
        everything = self.page("procedures/index.html")
        for other in ps.FACETS:
            if other != "kind":
                self.assertEqual(ps.facet_values(page, other),
                                 ps.facet_values(everything, other), other)
                group = page.find("details", "facet", data_facet=other)
                self.assertNotIn("data-fixed", group.attrs)

    # --- controls --------------------------------------------------------

    def check_controls(self, page: Page, *, fixed: str | None = None
                       ) -> None:
        """The header's search form, the facets, toolbar, message and
        texts."""
        texts = self.texts
        block = page.find("div", "catalogue")
        self.assertIsNotNone(block, f"{page.url} has no div.catalogue")
        self.assertEqual(block.find_all("form"), [],
                         "a form inside div.catalogue")
        forms = page.find("header", "site-header").find_all("form")
        self.assertEqual(len(forms), 1, "not one form in the site header")
        form = forms[0]
        self.assertTrue(form.has_class("site-search"))
        self.assertIn("data-catalogue-search", form.attrs)
        self.assertNotIn("hidden", form.attrs)
        self.assertEqual(form.attrs.get("role"), "search")
        self.assertEqual(form.attrs.get("method", "").lower(), "get")
        self.assertEqual(page.resolve(form.attrs.get("action", "")),
                         page.url)
        if fixed is None:
            name, hint = texts["search_label"], texts["placeholder"]
        else:
            term = page.find("main").find("h1").norm()
            name = texts["search_scope"][fixed].format(term=term)
            hint = texts["scoped_placeholder"]
        fields = form.find_all("input")
        self.assertEqual(len(fields), 1)
        self.assertEqual(
            {k: fields[0].attrs.get(k) for k in
             ("type", "name", "id", "aria-label", "placeholder")},
            {"type": "search", "name": "q", "id": "catalogue-q",
             "aria-label": name, "placeholder": hint})
        buttons = form.find_all("button")
        self.assertEqual(len(buttons), 1)
        self.assertEqual((buttons[0].attrs.get("type"), buttons[0].norm()),
                         ("submit", texts["search_button"]))
        self.check_facets(page, block, fixed)
        self.check_toolbar(page, block)
        message = block.find("p", "catalogue-message")
        self.assertIn("data-catalogue-message", message.attrs)
        self.assertEqual(message.attrs.get("role"), "status")
        self.assertIn("hidden", message.attrs)
        self.assertEqual(message.norm(), "")
        for name in DATA_TEXTS:
            with self.subTest(text=name):
                self.assertEqual(block.attrs.get(f"data-text-{name}"),
                                 texts["data_text"][name])

    def hidden_controls(self, node: Node) -> None:
        self.assertIn("data-catalogue-controls", node.attrs)
        self.assertIn("hidden", node.attrs)

    def check_facets(self, page: Page, block: Node, fixed: str | None
                     ) -> None:
        texts = self.texts
        facets = block.find("div", "catalogue-facets")
        self.assertEqual(facets.attrs.get("id"), "catalogue-facets")
        self.hidden_controls(facets)
        heading = facets.find("h2")
        self.assertIsNotNone(heading, "no h2 in the facets")
        self.assertEqual(heading.norm(), texts["filters"])
        groups = facets.find_all("details", "facet")
        self.assertEqual([g.attrs.get("data-facet") for g in groups],
                         list(ps.FACETS))
        self.assertLess(page.index_of(heading), page.index_of(groups[0]))
        expected = self.facet_labels()
        for group in groups:
            facet = group.attrs["data-facet"]
            with self.subTest(facet=facet):
                self.check_facet(page, group, facet, fixed)
                if facet != fixed:
                    self.assert_facet_values(page, facet, expected[facet])

    def check_facet(self, page: Page, group: Node, facet: str,
                    fixed: str | None) -> None:
        texts = self.texts
        parts = group.elements()
        summary = parts[0]
        self.assertEqual(summary.tag, "summary")
        self.assertTrue(summary.attrs.get("id"), "summary without an id")
        self.assertEqual(summary.norm(), texts["facets"][facet])
        values = parts[1]
        self.assertEqual(values.tag, "div")
        self.assertEqual(values.attrs.get("role"), "group")
        self.assertEqual(values.attrs.get("aria-labelledby"),
                         summary.attrs["id"])
        opens = facet in ("type", "kind", "status") or facet == fixed
        self.assertEqual("open" in group.attrs, opens)
        if facet == fixed:
            self.assertIn("data-fixed", group.attrs)
        else:
            self.assertNotIn("data-fixed", group.attrs)
        for label in values.find_all("label", "facet-value"):
            box = label.find("input")
            self.assertEqual((box.attrs.get("type"), box.attrs.get("name")),
                             ("checkbox", facet))
            name = label.find("span", "facet-label")
            self.assertIsNotNone(name, "no span.facet-label")
            count = label.find("span", "facet-count")
            self.assertIsNotNone(count, "no span.facet-count")
            self.assertEqual(count.norm(), "")
            order = [page.index_of(n) for n in (box, name, count)]
            self.assertEqual(order, sorted(order))
        links = [link for link in page.links(group)
                 if not link.node.within(values)]
        if facet in DIRECTORIES:
            self.assertEqual([(l.target, l.node.norm()) for l in links],
                             [(DIRECTORIES[facet],
                               texts["directories"][facet])])
            self.assertGreater(page.index_of(links[0].node),
                               page.index_of(values))
        else:
            self.assertEqual(links, [])

    def assert_facet_values(self, page: Page, facet: str,
                            expected: dict[str, str]) -> None:
        """The facet lists exactly ``expected`` (value to label): the
        kinds and statuses in their fixed order, other values ordered by
        label.
        Order is checked among ASCII labels only, as collation of other
        letters is Hugo's."""
        shown = ps.facet_values(page, facet)
        if facet in ("kind", "status"):
            self.assertEqual(shown, [(k, v) for k, v in expected.items()])
            return
        self.assertEqual(sorted(shown), sorted(expected.items()))
        names = [label for _, label in shown if label.isascii()]
        self.assertEqual(names, sorted(names))

    def check_toolbar(self, page: Page, block: Node) -> None:
        texts = self.texts
        toolbar = block.find("div", "catalogue-toolbar")
        self.hidden_controls(toolbar)
        toggle = toolbar.find("button", "facets-toggle")
        self.assertEqual(
            {k: toggle.attrs.get(k) for k in
             ("type", "aria-controls", "aria-expanded")},
            {"type": "button", "aria-controls": "catalogue-facets",
             "aria-expanded": "false"})
        self.assertEqual(toggle.norm(), texts["filters"])
        active = toolbar.find("ul", "catalogue-active")
        self.assertIsNotNone(active, "no ul.catalogue-active")
        self.assertEqual((active.norm(), active.find_all("li")), ("", []))
        clear = toolbar.find("button", "clear-all")
        self.assertEqual((clear.attrs.get("type"), clear.norm()),
                         ("button", texts["clear"]))
        order = [toggle, active, clear]
        for name, label_key, options_key in (
                ("catalogue-sort", "sort_label", "sorts"),
                ("catalogue-view", "view_label", "views")):
            select = toolbar.find("select", id=name)
            self.assertIsNotNone(select, f"no select#{name}")
            label = toolbar.find("label", **{"for": name})
            self.assertIsNotNone(label, f"no label for {name}")
            self.assertEqual(label.norm(), texts[label_key])
            self.assertEqual([(o.attrs.get("value"), o.norm())
                              for o in select.find_all("option")],
                             texts[options_key])
            order += [label, select]
        positions = [page.index_of(n) for n in order]
        self.assertEqual(positions, sorted(positions))

    # --- rows ------------------------------------------------------------

    def check_rows(self, page: Page, items: list[Content]) -> None:
        """One row per item, by ID, with the five cells."""
        labels = self.labels()
        rows = ps.catalogue_rows(page)
        wanted = sorted(items, key=lambda item: item.id)
        self.assertEqual([ps.row_cells(r)[0].norm() for r in rows],
                         [item.id for item in wanted])
        for row, item in zip(rows, wanted):
            cells = ps.row_cells(row)
            with self.subTest(procedure=item.id):
                self.assertEqual(len(cells), 5)
                target = f"/procedures/{item.slug}/"
                for cell, text in ((cells[0], item.id),
                                   (cells[1], item.title)):
                    link = page.links(cell)[0]
                    self.assertEqual(link.target, target)
                    self.assertEqual(link.node.norm(), text)
                self.assertEqual(
                    cells[2].norm(),
                    ", ".join(labels[s] for s in item.data["reaction_types"]))
                badge = cells[3].find("span", "badge")
                self.assertIsNotNone(badge, "no span.badge")
                self.assertIn(f"badge--{item.data['status']}", badge.classes)
                self.assertEqual(
                    badge.norm(), self.texts["status"][item.data["status"]])
                moment = cells[4].find("time")
                self.assertIsNotNone(moment, "no time in the Modified cell")
                self.assertEqual(moment.attrs.get("datetime"),
                                 ps.rfc3339(item.data["lastmod"]))
                self.assertEqual(moment.norm(),
                                 item.data["lastmod"].strftime("%Y-%m-%d"))

    # --- the home page ---------------------------------------------------

    def grouped(self, number: int) -> str:
        return f"{number:,}".replace(",", self.texts["thousands"])

    def check_home(self, page: Page, items: list[Content]) -> None:
        """Intro, recent list and browse list of the home page."""
        texts = self.texts
        main = page.find("main")
        parts = [(n.tag, n.classes[:1]) for n in main.elements()]
        self.assertEqual(parts[:2], [("div", ["home-intro"]),
                                     ("div", ["home-layout"])])
        intro, layout = main.elements()[:2]
        self.assertEqual([h.norm() for h in intro.find_all("h1")],
                         [texts["home_title"]])
        lede = intro.find("p", "lede")
        self.assertIsNotNone(lede, "no p.lede")
        self.assertEqual(lede.norm(), texts["lede"])
        drafts = sorted((i for i in items if i.data["status"] == "draft"),
                        key=lambda i: i.id)
        sections = ["home-recent", "home-unchecked", "home-browse"]
        if not drafts:
            sections.remove("home-unchecked")
        self.assertEqual([(n.tag, n.classes[:1])
                          for n in layout.elements()],
                         [("section", [name]) for name in sections])
        parts = layout.elements()
        self.check_recent(page, parts[0], items)
        if drafts:
            self.check_unchecked(page, parts[1], drafts)
        self.check_browse(page, parts[-1], items)
        self.assertEqual(main.find_all("form"), [])
        self.assertEqual(main.find_all("input"), [])
        self.assertEqual(main.find_all("table"), [])
        targets = [link.target for link in page.links(main)]
        self.assertIn("/procedures/?sort=modified", targets)
        self.assertEqual("/procedures/?status=draft" in targets, bool(drafts))

    def check_unchecked(self, page: Page, section: Node,
                        drafts: list[Content]) -> None:
        """The first five drafts by ID, with their creation dates, and
        the link to every draft with their count."""
        texts = self.texts
        self.assertEqual([h.norm() for h in section.find_all("h2")],
                         [texts["unchecked"]])
        listing = section.find("ol", "unchecked-list")
        self.assertIsNotNone(listing, "no ol.unchecked-list")
        entries = listing.find_all("li")
        self.assertEqual(len(entries), min(5, len(drafts)))
        for entry, item in zip(entries, drafts):
            with self.subTest(procedure=item.id):
                link = entry.elements()[0]
                self.assertEqual(link.tag, "a")
                self.assertEqual(page.resolve(link.attrs["href"]),
                                 f"/procedures/{item.slug}/")
                self.assertEqual(link.norm(), f"{item.id} {item.title}")
                moment = entry.find("time")
                self.assertIsNotNone(moment, "no time in the list item")
                self.assertGreater(page.index_of(moment),
                                   page.index_of(link))
                self.assertEqual(moment.attrs.get("datetime"),
                                 ps.rfc3339(item.data["date"]))
                self.assertEqual(moment.norm(),
                                 item.data["date"].strftime("%Y-%m-%d"))
        after = page.following(listing, "p")
        self.assertIsNotNone(after, "no p after the unchecked list")
        self.assertEqual([(l.target, l.node.norm())
                          for l in page.links(after)],
                         [("/procedures/?status=draft",
                           texts["unchecked_link"])])
        count = f"({self.grouped(len(drafts))})"
        self.assertEqual(after.find("span", "count").norm(), count)
        self.assertEqual(after.norm(), f"{texts['unchecked_link']} {count}")

    def check_recent(self, page: Page, section: Node,
                     items: list[Content]) -> None:
        texts = self.texts
        self.assertEqual([h.norm() for h in section.find_all("h2")],
                         [texts["recent"]])
        listing = section.find("ol", "recent-list")
        self.assertIsNotNone(listing, "no ol.recent-list")
        newest = sorted(items, key=lambda i: (-instant(i), i.id))[:5]
        entries = listing.find_all("li")
        self.assertEqual(len(entries), len(newest))
        for entry, item in zip(entries, newest):
            with self.subTest(procedure=item.id):
                link = entry.elements()[0]
                self.assertEqual(link.tag, "a")
                self.assertEqual(page.resolve(link.attrs["href"]),
                                 f"/procedures/{item.slug}/")
                self.assertEqual(link.norm(), f"{item.id} {item.title}")
                moment = entry.find("time")
                self.assertIsNotNone(moment, "no time in the list item")
                self.assertGreater(page.index_of(moment),
                                   page.index_of(link))
                self.assertEqual(moment.attrs.get("datetime"),
                                 ps.rfc3339(item.data["lastmod"]))
                self.assertEqual(moment.norm(),
                                 item.data["lastmod"].strftime("%Y-%m-%d"))
        self.assertEqual([i.id for i in newest],
                         [e.elements()[0].norm().split()[0]
                          for e in entries])
        after = page.following(listing, "p")
        self.assertIsNotNone(after, "no p after the recent list")
        links = page.links(after)
        self.assertEqual([(l.target, l.node.norm()) for l in links],
                         [("/procedures/?sort=modified",
                           texts["recent_link"])])

    def check_browse(self, page: Page, section: Node,
                     items: list[Content]) -> None:
        texts = self.texts
        self.assertEqual([h.norm() for h in section.find_all("h2")],
                         [texts["browse"]])
        listing = section.find("ul", "browse-list")
        self.assertIsNotNone(listing, "no ul.browse-list")
        terms = {taxonomy: {t for i in items for t in i.data[taxonomy]}
                 for taxonomy in ("reaction_types", "tags", "authors")}
        wanted = [
            ("/procedures/", len(items)),
            ("/reaction_types/", len(terms["reaction_types"])),
            ("/tags/", len(terms["tags"])),
            ("/authors/", len(terms["authors"])),
            ("/compounds/", len(ps.read_registry(self.sandbox))),
            ("/sequences/", len(ps.read_sequences(self.sandbox,
                                                  self.LOCALE)))]
        entries = listing.find_all("li")
        self.assertEqual(len(entries), len(wanted))
        for entry, label, (target, count) in zip(
                entries, texts["entries"], wanted):
            with self.subTest(entry=label):
                link = entry.elements()[0]
                self.assertEqual(link.tag, "a")
                self.assertEqual(page.resolve(link.attrs["href"]), target)
                self.assertEqual(link.norm(), label)
                number = entry.find("span", "count")
                self.assertIsNotNone(number, "no span.count")
                self.assertEqual(number.norm(), f"({self.grouped(count)})")
                self.assertEqual(entry.norm(),
                                 f"{label} ({self.grouped(count)})")
