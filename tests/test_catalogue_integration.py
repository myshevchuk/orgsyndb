"""Catalogue build tests: HTML scans of the catalogue, term and home pages
(site-catalogue, site-theme "Home page content", site-build "Deployment
under a path prefix").

``PlainCatalogueTests`` builds the test collection alone;
``CatalogueFixtureTests`` adds the catalogue fixtures
(tests/fixtures/catalogue/) to it. Tests skip, naming the missing tool or
cache, as the other integration tests do.
"""

import json
import re
import unittest
import urllib.parse

import catalogue_support as cs
import pipeline_support as ps
from pipeline_support import Content

SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
PREFIX = "/orgsyndb/"
TERM_FACET = {"reaction_types": "type", "tags": "tag", "authors": "author"}


class PlainCatalogueTests(cs.CatalogueCase):
    """The test collection, built in English."""

    def test_the_catalogue_lists_every_procedure_once(self) -> None:
        """Scenario: The catalogue lists every procedure once."""
        page = self.page("procedures/index.html")
        block = self.check_catalogue(page, fixed=None, heading="Procedures")
        count = block.find("p", "catalogue-count")
        self.assertEqual(count.norm(), "9 procedures")
        self.assertEqual(count.attrs.get("data-filtered"),
                         "{shown} of {total} procedures")
        items = self.content()
        self.assertEqual(len(items), 9)
        self.check_rows(page, items)
        self.assertEqual(self.table_ids(page),
                         sorted({item.id for item in items}))

    def test_the_general_procedures_view_lists_the_general_ones(
            self) -> None:
        """Scenario: The view lists the general procedures."""
        page = self.page("general-procedures/index.html")
        self.check_general_view(page, self.content())
        self.assertEqual(self.table_ids(page), ["OSDB-0009"])
        block = page.find("div", "catalogue")
        self.assertEqual(block.attrs.get("data-fixed"), "kind")
        self.assertEqual(block.find("p", "catalogue-count").norm(),
                         "1 procedure")
        form = page.find("header", "site-header").find("form")
        field = form.find("input", name="q")
        self.assertEqual(field.get("aria-label"),
                         "Search general procedures")
        self.assertEqual(field.get("placeholder"), "Search these procedures")
        self.assertEqual(page.resolve(form.attrs.get("action", "")),
                         "/general-procedures/")

    def test_the_kind_facet_of_the_catalogue(self) -> None:
        """Scenario: Controls in the HTML (the kind facet)."""
        page = self.page("procedures/index.html")
        self.assertEqual(
            [g.attrs.get("data-facet")
             for g in page.find_all("details", "facet")],
            ["type", "kind", "status", "tag", "author"])
        group = page.find("details", "facet", data_facet="kind")
        self.assertIn("open", group.attrs)
        self.assertNotIn("data-fixed", group.attrs)
        self.assertEqual(group.find("summary").norm(), "Kind")
        self.assertEqual(ps.facet_values(page, "kind"), [
            ("specific", "Specific procedure"),
            ("general", "General procedure")])
        self.assertEqual(
            [b.attrs.get("name") for b in group.find_all("input")],
            ["kind", "kind"])
        self.assertEqual(group.find_all("a"), [])

    def test_term_pages_carry_the_kind_facet_too(self) -> None:
        """Scenario: Controls in the HTML (term pages)."""
        page = self.page("tags/cinnamate/index.html")
        self.assertEqual(ps.facet_values(page, "kind"), [
            ("specific", "Specific procedure"),
            ("general", "General procedure")])

    def test_term_pages_are_catalogue_pages(self) -> None:
        items = self.content()
        seen = 0
        for taxonomy, facet in TERM_FACET.items():
            names = self.term_names(taxonomy)
            carrying = {name: sorted(i.id for i in items
                                     if key in i.term_keys(taxonomy))
                        for key, name in names.items()}
            directories = sorted((self.public / taxonomy).glob("*/index.html"))
            self.assertEqual(len(directories), len(names), taxonomy)
            shown = []
            for path in directories:
                page = ps.load_page(self.public, path)
                relative = str(path.relative_to(self.public))
                with self.subTest(page=relative):
                    h1 = [t for level, t in page.headings() if level == 1]
                    self.assertEqual(len(h1), 1)
                    self.assertIn(h1[0], carrying)
                    shown.append(h1[0])
                    block = self.check_catalogue(page, fixed=facet,
                                                 heading=h1[0])
                    self.assertEqual(block.attrs.get("data-fixed"), facet)
                    self.assertEqual(self.table_ids(page),
                                     carrying[h1[0]])
                    seen += 1
            self.assertEqual(sorted(shown), sorted(names.values()))
        self.assertGreater(seen, 20)

    def test_controls_are_in_the_html(self) -> None:
        """Scenario: Controls in the HTML."""
        page = self.page("procedures/index.html")
        self.check_controls(page)

    def test_scope_is_in_the_html(self) -> None:
        """Scenario: Scope in the HTML."""
        texts = self.texts
        home = self.page("procedures/index.html")
        cases = [("tags/cinnamate/index.html", "tag", "cinnamate",
                  "cinnamate"),
                 ("reaction_types/hydrolysis/index.html", "type",
                  "hydrolysis", "Hydrolysis"),
                 ("authors/a.-example/index.html", "author", "a. example",
                  "A. Example")]
        for relative, facet, key, name in cases:
            page = self.page(relative)
            with self.subTest(page=relative):
                block = self.check_catalogue(page, fixed=facet, heading=name)
                self.check_controls(page, fixed=facet)
                scope = block.find("p", "catalogue-scope")
                sentence = texts["scope"][facet].format(term=name)
                self.assertEqual(scope.norm(),
                                 f"{sentence} · {texts['browse_all']}")
                links = page.links(scope)
                self.assertEqual(
                    [(l.target, l.node.norm()) for l in links],
                    [("/procedures/", texts["browse_all"])])
                self.assertIn("data-browse-all", links[0].node.attrs)
                fixed = page.find("details", "facet", data_facet=facet)
                self.assertIn("data-fixed", fixed.attrs)
                self.assertIn("open", fixed.attrs)
                boxes = fixed.find_all("input")
                self.assertEqual(len(boxes), 1)
                self.assertEqual(boxes[0].attrs.get("type"), "checkbox")
                self.assertEqual(boxes[0].attrs.get("name"), facet)
                self.assertEqual(boxes[0].attrs.get("value"), key)
                self.assertIn("checked", boxes[0].attrs)
                self.assertIn("disabled", boxes[0].attrs)
                self.assertEqual(ps.facet_values(page, facet),
                                 [(key, name)])
                for other in ps.FACETS:
                    if other != facet:
                        self.assertEqual(ps.facet_values(page, other),
                                         ps.facet_values(home, other))
                        group = page.find("details", "facet",
                                          data_facet=other)
                        self.assertNotIn("data-fixed", group.attrs)

    def test_script_wiring(self) -> None:
        """Scenario: Script wiring."""
        loaded = set()
        for path, page in self.pages():
            relative = str(path.relative_to(self.public))
            with self.subTest(page=relative):
                self.assertNotIn("pagefind-ui", page.source)
                sources = [page.resolve(s) for s in page.script_sources()
                           if s]
                for source in sources:
                    self.assertRegex(source, r"^/js/(site|catalogue)\.")
                found = [s for s in sources if s.startswith("/js/catalogue")]
                if ps.is_catalogue_url(page.url):
                    self.assertEqual(len(found), 1)
                    self.assertRegex(found[0], cs.CATALOGUE_SCRIPT)
                    loaded.add(found[0])
                else:
                    self.assertEqual(found, [])
        self.assertEqual(len(loaded), 1, "the pages load different scripts")
        script = ps.target_file(self.public, loaded.pop()).read_text(
            encoding="utf-8")
        for word in ("OrgSynSearch", "OrgSynCatalogue",
                     "pagefind/pagefind.js"):
            with self.subTest(word=word):
                self.assertIn(word, script)

    def test_the_compound_catalogue_shares_the_script(self) -> None:
        """Scenario: Script wiring (the compound catalogue)."""
        scripts = {}
        for relative in ("procedures/index.html", "compounds/index.html"):
            page = self.page(relative)
            found = [page.resolve(s) for s in page.script_sources()
                     if s and "/js/catalogue" in page.resolve(s)]
            self.assertEqual(len(found), 1, relative)
            self.assertRegex(found[0], cs.CATALOGUE_SCRIPT)
            scripts[relative] = found[0]
        self.assertEqual(scripts["procedures/index.html"],
                         scripts["compounds/index.html"])
        page = self.page("compounds/index.html")
        self.assertNotIn("pagefind-ui", page.source)
        self.assertEqual(len(page.find_all("input", name="q")), 1)

    def test_links_and_assets_resolve_under_a_prefix(self) -> None:
        """Scenario: Links and assets under a prefix."""
        base = f"http://127.0.0.1{PREFIX.rstrip('/')}"
        checked = 0
        for path, page in self.pages():
            relative = str(path.relative_to(self.public))
            for node in page.nodes:
                for attribute in ("href", "src", "action"):
                    value = node.attrs.get(attribute)
                    if value is None:
                        continue
                    with self.subTest(page=relative, attribute=attribute,
                                      value=value):
                        self.assertFalse(value.startswith("/"))
                        if SCHEME.match(value) or value.startswith("#"):
                            continue
                        joined = urllib.parse.urljoin(base + page.url, value)
                        found = urllib.parse.unquote(
                            urllib.parse.urlsplit(joined).path)
                        self.assertTrue(found.startswith(PREFIX), found)
                        target = self.public / found[len(PREFIX):]
                        if found.endswith("/") or target.is_dir():
                            target = target / "index.html"
                        self.assertTrue(target.is_file(), found)
                        checked += 1
        self.assertGreater(checked, 100)


class DetailsChecks:
    """The Details view's markup checks, shared by the build classes that
    add procedures to the test collection. The class that uses them is a
    ``CatalogueCase``."""

    def expected_details(self, item: Content, registry: dict
                         ) -> list[tuple[str, str]]:
        locale = self.LOCALE
        compounds = [registry[e["compound"]] for e in item.products]
        names = [ps.shown_name(c, locale) for c in compounds]
        found = []
        if len(names) > 1:
            found.append(("Products", ", ".join(names)))
        elif names[0] != item.title:
            found.append(("Product", names[0]))
        if len(compounds) == 1:
            compound = compounds[0]
            found.append(("Formula", compound["formula"]))
            found.append(("MW", f"{ps.number_text(compound['mw'], locale)}"
                                " g/mol"))
            if compound.get("cas"):
                found.append(("CAS", compound["cas"]))
        # The Yield of a general procedure's Details block is not fixed
        # by the specification: only its label is checked (None).
        found.append(("Yield", None if item.is_general
                      else ps.yield_text(item, registry, locale)))
        found.append(("Created", item.data["date"].strftime("%Y-%m-%d")))
        return found

    def check_details(self, page: ps.Page, row: ps.Node, item: Content,
                      registry: dict) -> None:
        cell = ps.row_cells(row)[1]
        link = page.links(cell)[0]
        details = cell.find("div", "row-details")
        self.assertIsNotNone(details, "no div.row-details")
        self.assertGreater(page.index_of(details), page.index_of(link.node))
        pairs = page.definition_pairs(details)
        wanted = self.expected_details(item, registry)
        self.assertEqual([p.label for p in pairs], [l for l, _ in wanted])
        for pair, (label, value) in zip(pairs, wanted):
            if value is None:
                self.assertNotEqual(pair.definition.norm(), "", label)
            else:
                self.assertEqual(pair.definition.norm(), value, label)
        for pair in pairs:
            if pair.label == "Formula":
                formula = registry[item.products[0]["compound"]]["formula"]
                self.assertEqual(
                    [s.norm() for s in pair.definition.find_all("sub")],
                    re.findall(r"[0-9]+", formula))
            if pair.label == "Created":
                moment = pair.definition.find("time")
                self.assertIsNotNone(moment, "no time in Created")
                self.assertEqual(moment.attrs.get("datetime"),
                                 ps.rfc3339(item.data["date"]))
        images = row.find_all("img")
        first = next((registry[e["compound"]] for e in item.products
                      if registry[e["compound"]].get("structure_image")),
                     None)
        if first is None:
            self.assertEqual(images, [])
            return
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertTrue(image.within(details))
        self.assertTrue(image.has_class("row-structure"))
        self.assertEqual(page.resolve(image.attrs.get("src", "")),
                         "/" + first["structure_image"])
        self.assertTrue(ps.target_file(
            self.public, "/" + first["structure_image"]).is_file())
        self.assertEqual(image.attrs.get("alt"),
                         f"Structure of {ps.shown_name(first, self.LOCALE)}")
        self.assertEqual(image.attrs.get("loading"), "lazy")
        self.assertEqual(image.attrs.get("decoding"), "async")


class CatalogueFixtureTests(DetailsChecks, cs.CatalogueCase):
    """The test collection plus the catalogue fixtures."""

    CATALOGUE = True

    def test_the_fixtures_are_published_with_the_collection(self) -> None:
        """Harness: the build holds the shipped and the fixture procedures."""
        ids = [item.id for item in self.content()]
        self.assertEqual(len(ids), 15)
        self.assertEqual(sorted(set(ids)), sorted(ids))
        self.assertEqual(sorted(ids)[9:],
                         [f"OSDB-092{n}" for n in range(1, 7)])

    def test_rows_carry_the_records(self) -> None:
        """Scenario: Rows carry the records."""
        page = self.page("procedures/index.html")
        by_id = {item.id: item for item in self.content()}
        rows = ps.catalogue_rows(page)
        self.assertEqual(len(rows), len(by_id))
        for row in rows:
            self.assertIn(row.attrs.get("data-id"), by_id)
            item = by_id[row.attrs["data-id"]]
            with self.subTest(procedure=item.id):
                self.assertEqual(row.attrs.get("data-title"), item.title)
                self.assertEqual(row.attrs.get("data-status"),
                                 item.data["status"])
                self.assertEqual(row.attrs.get("data-kind"), item.kind)
                for facet, taxonomy in cs.FACET_TAXONOMY.items():
                    self.assertEqual(
                        json.loads(row.attrs[f"data-{facet}"]),
                        item.term_keys(taxonomy), facet)
                self.assertEqual(row.attrs.get("data-created"),
                                 ps.rfc3339(item.data["date"]))
                self.assertEqual(row.attrs.get("data-modified"),
                                 ps.rfc3339(item.data["lastmod"]))
        authors = json.loads(page.find("tr", data_id="OSDB-0921")
                             .attrs["data-author"])
        self.assertEqual(authors, ["ä. müller", "a. example"])
        kinds = {row.attrs["data-id"]: row.attrs["data-kind"]
                 for row in rows}
        self.assertEqual(
            sorted(i for i, kind in kinds.items() if kind == "general"),
            ["OSDB-0009"])
        self.assertEqual(set(kinds.values()), {"specific", "general"})

    def test_details_markup(self) -> None:
        """Scenario: Details markup."""
        page = self.page("procedures/index.html")
        by_id = {item.id: item for item in self.content()}
        registry = ps.read_registry(self.sandbox)
        for row in ps.catalogue_rows(page):
            self.assertIn(row.attrs.get("data-id"), by_id)
            item = by_id[row.attrs["data-id"]]
            with self.subTest(procedure=item.id):
                self.check_details(page, row, item, registry)
        withheld = by_id["OSDB-0922"]
        self.assertNotIn("cas", registry[withheld.products[0]["compound"]])
        labels = [p.label for p in page.definition_pairs(
            page.find("tr", data_id="OSDB-0922").find("div", "row-details"))]
        self.assertNotIn("CAS", labels)

    def test_only_osdb_0003_has_a_row_image(self) -> None:
        """Scenario: Details markup (images)."""
        page = self.page("procedures/index.html")
        with_image = [row.attrs.get("data-id") for row in
                      ps.catalogue_rows(page) if row.find_all("img")]
        self.assertEqual(with_image, ["OSDB-0003"])

    def test_home_page_content(self) -> None:
        """Scenario: Home page content."""
        page = self.page("index.html")
        items = self.content()
        self.check_home(page, items)
        newest = [item.id for item in sorted(
            items, key=lambda i: (-cs.instant(i), i.id))[:5]]
        shown = [entry.elements()[0].norm().split()[0]
                 for entry in page.find("ol", "recent-list").find_all("li")]
        self.assertEqual(shown, newest)
        self.assertEqual(shown[:2], ["OSDB-0921", "OSDB-0922"])
        tied = {i.id: i.data["lastmod"] for i in items
                if i.id in ("OSDB-0921", "OSDB-0922")}
        self.assertEqual(tied["OSDB-0921"], tied["OSDB-0922"])
        counts = [entry.find("span", "count").norm() for entry in
                  page.find("ul", "browse-list").find_all("li")]
        self.assertEqual(counts[0], "(15)")
        unchecked = page.find("section", "home-unchecked")
        self.assertEqual(
            [entry.elements()[0].norm().split()[0] for entry in
             unchecked.find("ol", "unchecked-list").find_all("li")],
            [f"OSDB-000{n}" for n in range(1, 6)])
        self.assertEqual(unchecked.find("p").find("span", "count").norm(),
                         "(12)")


    def test_the_sign_off_of_a_checked_procedure(self) -> None:
        """Scenario: Key facts and sign-off (the catalogue fixtures)."""
        checked = self.page("procedures/osdb-0921/index.html")
        identity = checked.find("p", "procedure-id")
        self.assertEqual(identity.norm(), "OSDB-0921 checked by B. Example")
        self.assertEqual(identity.find("span", "sign-off").norm(),
                         "by B. Example")
        labels = [p.label for p in checked.definition_pairs(
            checked.find("dl", "metadata"))]
        self.assertNotIn("Checked by", labels)
        draft = self.page("procedures/osdb-0923/index.html")
        self.assertIsNone(draft.find("span", "sign-off"))


class TwoProductDetailsTests(DetailsChecks, cs.CatalogueCase):
    """The test collection plus the two-product fixture: the Details view
    of a procedure with two products."""

    FIXTURES = ("OSDB-0907-two-products.md",)

    def test_details_markup(self) -> None:
        """Scenario: Details markup (two products)."""
        page = self.page("procedures/index.html")
        registry = ps.read_registry(self.sandbox)
        items = self.content()
        self.assertEqual(len(items), 10)
        row = page.find("tr", data_id="OSDB-0907")
        self.assertIsNotNone(row, "no row for OSDB-0907")
        pairs = [(p.label, p.definition.norm()) for p in
                 page.definition_pairs(row.find("div", "row-details"))]
        self.assertEqual(pairs, [
            ("Products", "trans-Stilbene, cis-Stilbene"),
            ("Yield", "45 % trans-Stilbene, 30 % cis-Stilbene"),
            ("Created", "2026-10-20")])
        images = row.find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].attrs.get("alt"),
                         "Structure of trans-Stilbene")
        self.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/structures/trans-stilbene.svg")
        for item in items:
            with self.subTest(procedure=item.id):
                self.check_details(
                    page, page.find("tr", data_id=item.id), item, registry)

    def test_the_first_product_with_an_image_decides(self) -> None:
        """Scenario: Details markup (images)."""
        page = self.page("procedures/index.html")
        with_image = [row.attrs.get("data-id") for row in
                      ps.catalogue_rows(page) if row.find_all("img")]
        self.assertEqual(with_image, ["OSDB-0003", "OSDB-0907"])


class AllCheckedHomeTests(cs.CatalogueCase):
    """The test collection with every procedure checked."""

    @classmethod
    def prepare(cls) -> None:
        for path in cls.sandbox.md_dir().glob("*.md"):
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('status = "draft"',
                                         'status = "checked"'),
                            encoding="utf-8")

    def test_nothing_waits_for_a_check(self) -> None:
        """Scenario: Nothing waits for a check."""
        self.assertEqual({item.data["status"] for item in self.content()},
                         {"checked"})
        page = self.page("index.html")
        self.check_home(page, self.content())
        self.assertIsNone(page.find("section", "home-unchecked"))


if __name__ == "__main__":
    unittest.main()
