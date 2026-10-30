"""German site tests: HTML scans, searches and PDFs of sandbox builds in
the shipped locale, de (localization). ``GermanSiteTests`` builds the test
collection; ``PartialTranslationTests`` builds it with two translations
removed and an English-only variant added; ``GermanPdfTests`` renders
its PDFs. Tests skip, naming the missing tool or cache, as the other
integration tests do.
"""

import catalogue_support as cs
import general_support as gs
import pipeline_support as ps
from pipeline_support import Page

NAVIGATION = [("/procedures/", "Vorschriften"),
              ("/compounds/", "Verbindungen"), ("/help/", "Hilfe")]
TABS = [("/procedures/", "Alle Vorschriften"),
        ("/general-procedures/", "Allgemeine Vorschriften"),
        ("/reaction_types/", "Reaktionstypen"), ("/tags/", "Schlagwörter"),
        ("/authors/", "Autoren")]
FOOTER = (r"^OrgSynDB · interne Vorschriften · Stand "
          r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
BANNER = "Beispieldaten – Mengenangaben nicht experimentell überprüft."
PANEL_LABELS = ["Produkt", "Summenformel", "Molmasse", "CAS", "SMILES",
                "Ausgangsstoffe", "Reaktionstyp", "Schlagwörter", "Autoren",
                "Erstellt", "Geändert", "Vorstufen"]
TITLES = {"procedures/index.html": "Vorschriften",
          "general-procedures/index.html": "Allgemeine Vorschriften",
          "reaction_types/index.html": "Reaktionstypen",
          "tags/index.html": "Schlagwörter",
          "authors/index.html": "Autoren", "compounds/index.html":
          "Verbindungen", "help/index.html": "Hilfe"}


class GermanCase(cs.CatalogueCase):
    LOCALE = "de"


class GermanSiteTests(GermanCase):
    """The test collection, built in German."""

    def test_every_page_has_the_german_shell(self) -> None:
        """Scenario: German page shell."""
        pages = self.pages()
        self.assertGreater(len(pages), 20)
        for path, page in pages:
            with self.subTest(page=str(path.relative_to(self.public))):
                self.assertEqual(page.find("html").get("lang"), "de")
                self.assertEqual(page.find("a", "skip-link").norm(),
                                 "Zum Inhalt springen")
                header = page.find("header", "site-header")
                nav = header.find("nav", aria_label="Website")
                self.assertIsNotNone(nav, "no nav[aria-label=Website]")
                links = [(l.target, l.node.norm()) for l in page.links(nav)]
                self.assertEqual(links, NAVIGATION)
                self.assertEqual(len(header.find_all("nav")), 1,
                                 "the header has a language switch")
                tabs = page.find("nav", "section-tabs")
                if tabs is not None:
                    self.assertEqual(tabs.attrs.get("aria-label"),
                                     "Vorschriften")
                    self.assertEqual([(l.target, l.node.norm())
                                      for l in page.links(tabs)], TABS)
                self.assertRegex(page.find("footer", "site-footer").norm(),
                                 FOOTER)
                self.check_header_search(page, header)
        self.assertFalse((self.public / "de").exists())
        self.assertFalse((self.public / "en").exists())

    def check_header_search(self, page: Page, header: ps.Node) -> None:
        """The German search form; on term pages its label names the
        scope (checked with the catalogue)."""
        forms = header.find_all("form")
        self.assertEqual(len(forms), 1)
        field = forms[0].find("input", name="q")
        self.assertIsNotNone(field, "no input[name=q]")
        if not ps.is_catalogue_url(page.url) or page.url == "/procedures/":
            self.assertEqual(field.get("aria-label"),
                             "Vorschriften durchsuchen")
            self.assertEqual(field.get("placeholder"),
                             "Produkt, CAS, SMILES oder Stichwort")
        elif page.url == "/general-procedures/":
            self.assertEqual(field.get("aria-label"),
                             "Allgemeine Vorschriften durchsuchen")
            self.assertEqual(field.get("placeholder"),
                             "Diese Vorschriften durchsuchen")
        else:
            self.assertRegex(field.get("aria-label"),
                             r"^Vorschriften .+ durchsuchen$")
            self.assertEqual(field.get("placeholder"),
                             "Diese Vorschriften durchsuchen")
        buttons = forms[0].find_all("button")
        self.assertEqual([b.norm() for b in buttons], ["Suchen"])

    def test_site_pages_have_german_titles(self) -> None:
        """Scenario: German page titles."""
        for relative, title in TITLES.items():
            page = self.page(relative)
            with self.subTest(page=relative):
                self.assertEqual(page.find("h1").norm(), title)
                self.assertEqual(page.title(), f"{title} | OrgSynDB")

    def test_german_help_index(self) -> None:
        """Scenario: German help index."""
        page = self.page("help/index.html")
        main = page.find("main")
        self.assertEqual(main.find("h1").norm(), "Hilfe")
        self.assertEqual([h.norm() for h in main.find_all("h2")],
                         ["Anleitungen", "Glossare"])
        first = page.following(main.find("h2"), "li")
        self.assertIsNotNone(first, "the guides list has no entry")
        title = (self.sandbox.app / "docs" / "AUTHORING.de.md").read_text(
            encoding="utf-8").split("\n", 1)[0].removeprefix("# ")
        links = page.links(first)
        self.assertEqual(
            [(l.target, l.node.norm(), l.node.get("hreflang"))
             for l in links],
            [("/help/authoring-de/", title, "de"),
             ("/help/authoring/", "English", "en")])

    def test_the_german_variants_are_published(self) -> None:
        """Scenario: Choosing the variant to publish (test collection)."""
        published = self.content()
        self.assertEqual(len(published), 9)
        for item in published:
            with self.subTest(procedure=item.id):
                self.assertEqual(item.language, "de")
                page = self.page(f"procedures/{item.slug}/index.html")
                self.assertEqual(page.find("h1").norm(), item.title)
                self.assertIsNone(page.find("article").get("lang"))
        dirs = {p.name for p in (self.public / "procedures").iterdir()
                if p.is_dir()}
        self.assertEqual(dirs, {item.slug for item in published})

    def test_german_panel_of_the_markdown_seed(self) -> None:
        """Scenario: German metadata panel."""
        page = self.page("procedures/osdb-0002/index.html")
        self.assertEqual(page.find("p", "sample-banner").norm(), BANNER)
        self.assertEqual(page.find("span", "badge").norm(), "Entwurf")
        self.assertEqual(page.find("button", "print-button").norm(),
                         "Drucken / Als PDF speichern")
        panel = page.find("dl", "metadata")
        pairs = {p.label: p.definition for p in page.definition_pairs(panel)}
        self.assertEqual(list(pairs), PANEL_LABELS)
        self.assertEqual(pairs["Produkt"].norm(), "Acetylsalicylsäure")
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in pairs["Produkt"].find_all("a", "compound")],
            [("/compounds/acetylsalicylic-acid/", "Acetylsalicylsäure")])
        self.assertEqual(pairs["Ausgangsstoffe"].norm(),
                         "Salicylsäure, Essigsäureanhydrid")
        self.assertEqual(pairs["Molmasse"].norm(), "180,16 g/mol")
        key = page.find("dl", "key-facts")
        self.assertEqual([(p.label, p.definition.norm())
                          for p in page.definition_pairs(key)],
                         [("Ansatzgröße", "20 mmol"), ("Ausbeute", "75 %")])
        reaction = page.links(pairs["Reaktionstyp"])
        self.assertEqual([(l.target, l.node.norm()) for l in reaction],
                         [("/reaction_types/acylation/", "Acylierung")])
        precursor = page.links(pairs["Vorstufen"])
        self.assertEqual([(l.target, l.node.norm()) for l in precursor],
                         [("/procedures/osdb-0001/", "OSDB-0001 Salicylsäure")])
        button = page.find("button", "copy-button")
        self.assertEqual((button.norm(), button.get("data-copied")),
                         ("Kopieren", "Kopiert"))
        self.assertIsNotNone(page.heading("Reagenzien"))

    def test_german_labels_for_reaction_types(self) -> None:
        """Scenario: German labels for reaction types."""
        page = self.page("reaction_types/aldol-condensation/index.html")
        self.assertEqual(page.find("h1").norm(), "Aldolkondensation")
        self.assertEqual(page.title(), "Aldolkondensation | OrgSynDB")
        labels = ps.reaction_labels(self.sandbox.app, "de")
        used = {slug for item in self.content()
                for slug in item.data["reaction_types"]}
        expected = sorted(labels[slug] for slug in used)
        self.assertIn("Veresterung", expected)
        directory = self.page("reaction_types/index.html")
        listed = [link.node.norm() for link in directory.links(
            directory.find("ul", "term-list"))]
        self.assertEqual(listed, expected)
        facet = ps.facet_values(self.page("procedures/index.html"), "type")
        self.assertEqual([label for _, label in facet], expected)
        self.assertEqual(sorted(value for value, _ in facet), sorted(used))

    def test_german_catalogue(self) -> None:
        """Scenario: German catalogue and home page (catalogue)."""
        page = self.page("procedures/index.html")
        block = self.check_catalogue(page, fixed=None, heading="Vorschriften")
        self.assertEqual(block.find("p", "catalogue-count").norm(),
                         "9 Vorschriften")
        self.check_controls(page)
        statuses = page.find("details", "facet", data_facet="status")
        self.assertIsNotNone(statuses, "no status facet")
        self.assertEqual(
            [label.norm() for label in
             statuses.find_all("span", "facet-label")],
            ["Entwurf", "Geprüft", "Zurückgezogen"])
        self.assertEqual(self.table_ids(page), sorted(
            item.id for item in self.content()))

    def test_german_general_procedures_view(self) -> None:
        """Scenario: German page titles (the general procedures)."""
        page = self.page("general-procedures/index.html")
        self.assertEqual(page.find("h1").norm(), "Allgemeine Vorschriften")
        self.assertEqual(page.title(), "Allgemeine Vorschriften | OrgSynDB")
        self.check_general_view(page, self.content())
        scope = page.find("p", "catalogue-scope")
        self.assertEqual(
            scope.norm(),
            "Nur allgemeine Vorschriften · Alle Vorschriften anzeigen")
        everything = self.page("procedures/index.html")
        self.assertEqual(
            [label for _, label in ps.facet_values(everything, "kind")],
            ["Einzelvorschrift", "Allgemeine Vorschrift"])
        self.assertEqual(
            everything.find("details", "facet", data_facet="kind")
            .find("summary").norm(), "Art")

    def test_german_page_of_a_general_procedure(self) -> None:
        """Scenario: German metadata panel (a general procedure)."""
        item = {i.id: i for i in self.content()}["OSDB-0009"]
        page = self.page("procedures/osdb-0009/index.html")
        registry = ps.read_registry(self.sandbox)
        table = gs.check_scope_table(self, page, item, registry, "de",
                                     "Zusammenfassung")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows[0], [
            "Eintrag", "Ausgangsstoffe", "Produkte", "Ausbeute",
            "Ansatzgröße", "Zeit", "Anmerkung"])
        self.assertEqual(rows[3][:3], [
            "3", "4′-Bromacetophenon", "1-(4-Bromphenyl)ethanol"])
        self.assertEqual(rows[3][6], item.scope[2]["note"])
        self.assertTrue(rows[3][6].startswith("Das Produkt schmilzt"))
        gs.check_key_facts(self, page, item, registry, "de")
        key = page.find("dl", "key-facts")
        self.assertEqual([(p.label, p.definition.norm())
                          for p in page.definition_pairs(key)],
                         [("Ansatzgröße", "10 mmol"),
                          ("Ausbeute", "85–90 %")])
        gs.check_scheme_figure(self, page, item,
                               "structures/aryl-ketone-reduction.svg", "de")
        self.assertEqual(
            page.find("header", "procedure-header").find("img")
            .attrs.get("alt"),
            "Schema von Sekundäre Benzylalkohole durch Reduktion mit "
            "Natriumborhydrid")
        panel = {p.label: p.definition
                 for p in page.definition_pairs(page.find("dl", "metadata"))}
        self.assertEqual(
            list(panel),
            ["Produkte", "Ausgangsstoffe", "Reaktionstyp", "Schlagwörter",
             "Autoren", "Erstellt", "Geändert", "Vorstufen"])

    def test_german_term_page(self) -> None:
        """Scenario: German catalogue and home page (term page)."""
        page = self.page("tags/cinnamate/index.html")
        block = self.check_catalogue(page, fixed="tag", heading="cinnamate")
        self.check_controls(page, fixed="tag")
        scope = block.find("p", "catalogue-scope")
        self.assertTrue(scope.norm().startswith(
            "Nur Vorschriften mit dem Schlagwort cinnamate"), scope.norm())
        links = page.links(scope)
        self.assertEqual(
            [(l.target, l.node.norm()) for l in links],
            [("/procedures/", "Alle Vorschriften anzeigen")])
        self.assertIn("data-browse-all", links[0].node.attrs)

    def test_german_home_page(self) -> None:
        """Scenario: German catalogue and home page (home page)."""
        page = self.page("index.html")
        items = self.content()
        self.check_home(page, items)
        listed = [e.elements()[0].norm().split()[0]
                  for e in page.find("ol", "recent-list").find_all("li")]
        self.assertEqual(listed, [f"OSDB-000{n}" for n in range(1, 6)])

    def test_the_german_index_finds_german_words(self) -> None:
        """Scenario: German search index."""
        ps.require_node()
        out = ps.pagefind_search(self.public, [
            {"term": "Zimtsäure", "filters": None, "normalise": True},
            {"term": "Verseifung", "filters": None, "normalise": True},
        ], language="de")
        found = []
        for entry in out["searched"]:
            self.assertIsNotNone(entry)
            self.assertNotIn("error", entry, str(entry))
            found.append(entry["ids"])
        self.assertIn("OSDB-0008", found[0])
        self.assertEqual(sorted(found[1]), ["OSDB-0001", "OSDB-0008"])
        self.assertEqual(list(out["filters"]), ["id"])
        titles = {item.title for item in self.content()}
        for results in out["results"]:
            for hit in results:
                self.assertIn(hit["title"], titles)
        self.assertEqual(sorted(hit["id"] for hit in out["results"][1]),
                         ["OSDB-0001", "OSDB-0008"])


class PartialTranslationTests(GermanCase):
    """Without the German OSDB-0001 and OSDB-0004, and with an English
    OSDB-0100 whose only file is tagged .en."""

    REMOVED = ("OSDB-0001-salicylic-acid.de.md",
               "OSDB-0004-4-acetylbiphenyl.de.md")

    @classmethod
    def prepare(cls) -> None:
        for name in cls.REMOVED:
            (cls.sandbox.md_dir() / name).unlink()
        ps.put_baseline(cls.sandbox, "OSDB-0100-baseline.en.md")

    def test_every_procedure_is_published(self) -> None:
        """Scenario: Every procedure in every locale."""
        chosen = {item.id: item.path.name for item in self.content()}
        self.assertEqual(len(chosen), 10)
        self.assertEqual(chosen["OSDB-0001"], "OSDB-0001-salicylic-acid.md")
        self.assertEqual(chosen["OSDB-0100"], "OSDB-0100-baseline.en.md")
        self.assertEqual(chosen["OSDB-0002"], "OSDB-0002-aspirin.de.md")
        page = self.page("procedures/osdb-0001/index.html")
        self.assertEqual(page.find("h1").norm(), "Salicylic acid")
        self.assertEqual(page.find("html").get("lang"), "de")
        home = self.page("index.html")
        browse = home.find("ul", "browse-list")
        self.assertIsNotNone(browse, "no ul.browse-list")
        first = browse.find_all("li")[0]
        self.assertEqual(first.elements()[0].norm(), "Alle Vorschriften")
        self.assertEqual(first.find("span", "count").norm(), "(10)")
        rows = ps.catalogue_rows(self.page("procedures/index.html"))
        ids = [ps.row_cells(row)[0].norm() for row in rows]
        self.assertEqual(len(ids), 10)
        self.assertEqual(sorted(set(ids)), sorted(chosen))

    def test_a_variant_in_another_language_is_marked(self) -> None:
        """Scenario: A procedure in another language is marked."""
        page = self.page("procedures/osdb-0100/index.html")
        self.assertEqual(page.find("article").get("lang"), "en")
        self.assertEqual(page.find("header", "procedure-header").get("lang"),
                         "en")
        self.assertEqual(page.find("main").find("p", "sample-banner").norm(),
                         BANNER)
        untagged = self.page("procedures/osdb-0001/index.html")
        self.assertIsNone(untagged.find("article").get("lang"))

    def test_links_join_the_languages(self) -> None:
        """Scenario: Links between variants of different languages."""
        page = self.page("procedures/osdb-0002/index.html")
        links = [(l.target, l.node.norm()) for l in page.links()
                 if l.node.has_class("precursor")]
        self.assertEqual(links,
                         [("/procedures/osdb-0001/", "OSDB-0001 Salicylic acid")])
        english = self.page("procedures/osdb-0004/index.html")
        used_in = [(l.target, l.node.norm()) for l in english.links()
                   if l.node.has_class("used-in")]
        self.assertEqual(
            used_in,
            [("/procedures/osdb-0005/",
              "OSDB-0005 1-(Biphenyl-4-yl)ethanol"),
             ("/procedures/osdb-0009/",
              "OSDB-0009 Sekundäre Benzylalkohole durch Reduktion mit "
              "Natriumborhydrid")])


class GermanGeneralFixtureTests(GermanCase):
    """The test collection plus the general baseline, built in German:
    numbers with a decimal comma in the scope table and the key facts."""

    @classmethod
    def prepare(cls) -> None:
        ps.put_general_fixture(cls.sandbox)

    def item(self) -> ps.Content:
        return {i.id: i for i in self.content()}["OSDB-0140"]

    def test_the_scope_table_writes_decimal_commas(self) -> None:
        """Requirement: Scope table on the page (decimal separator)."""
        page = self.page("procedures/osdb-0140/index.html")
        registry = ps.read_registry(self.sandbox)
        table = gs.check_scope_table(self, page, self.item(), registry, "de",
                                     "Summary")
        rows = [[c.norm() for c in r.elements() if c.tag in ("td", "th")]
                for r in table.find_all("tr")]
        self.assertEqual(rows[0], [
            "Eintrag", "Ausgangsstoffe", "Produkte", "Ausbeute",
            "Ansatzgröße", "Zeit", "Temperatur", "Anmerkung"])
        self.assertEqual(rows[1][1:5], [
            "Essigsäure, Ethanol", "Ethylacetat", "85 %", "20 mmol"])
        self.assertEqual(rows[1][5:7], ["2 h", "80 °C"])
        self.assertEqual(rows[2][3], "78 %, 64,5 %")
        self.assertEqual(rows[3][3], "72,5 %")
        self.assertEqual(
            [(i.attrs.get("alt"), page.resolve(i.attrs["src"]))
             for i in table.find_all("img", "scope-structure")],
            [("Strukturformel von Ethylacetat",
              "/structures/ethyl-acetate.svg")])

    def test_the_key_facts_write_the_range_with_a_decimal_comma(
            self) -> None:
        """Requirement: Procedure page structure (German range)."""
        page = self.page("procedures/osdb-0140/index.html")
        key = page.find("dl", "key-facts")
        self.assertEqual([(p.label, p.definition.norm())
                          for p in page.definition_pairs(key)],
                         [("Ansatzgröße", "25 mmol"),
                          ("Ausbeute", "64,5–85 %")])

    def test_the_placeholder_is_german(self) -> None:
        """Scenario: Scheme image of a general procedure (German)."""
        page = self.page("procedures/osdb-0140/index.html")
        figure = page.find("header", "procedure-header").find(
            "figure", "structure")
        self.assertTrue(figure.has_class("structure--placeholder"))
        self.assertEqual(figure.find("div", "structure__slot").norm(),
                         "Keine Strukturformel")

    def test_the_compound_page_names_the_entry_in_german(self) -> None:
        """Requirement: Compound pages (German entries)."""
        page = self.page("compounds/propyl-acetate/index.html")
        made = page.find("section", "compound-made-by")
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0140 Acetate Esters · Eintrag 2 · 64,5 % · Entwurf"])


class GermanPdfTests(GermanCase):
    """PDFs of the test collection, built in German."""

    COMMAND = "pdf"

    @classmethod
    def require_tools(cls) -> None:
        ps.require_pdf_tools()

    def test_german_first_page_and_footer(self) -> None:
        """Scenario: German first page."""
        pdf_dir = self.sandbox.root / "pdf"
        self.assertEqual(sorted(p.name for p in pdf_dir.iterdir()),
                         sorted(f"{item.path.stem}.pdf"
                                for item in self.content()))
        pages = ps.pdf_page_texts(pdf_dir / "OSDB-0002-aspirin.de.pdf")
        self.assertIn(
            "http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · "
            "Status Entwurf · zuletzt geändert 2026-10-22 20:20",
            ps.norm_text(pages[0]))
        for number, text in enumerate(pages, 1):
            with self.subTest(page=number):
                lines = [line.strip() for line in text.splitlines()]
                self.assertIn(f"Seite {number} von {len(pages)}", lines)
