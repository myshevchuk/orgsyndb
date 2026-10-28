"""German site tests: HTML scans, searches and PDFs of sandbox builds in
the shipped locale, de (localization). ``GermanSiteTests`` builds the test
collection; ``PartialTranslationTests`` builds it with two translations
removed and an English-only variant added; ``GermanPdfTests`` renders
its PDFs. Tests skip, naming the missing tool or cache, as the other
integration tests do.
"""

import catalogue_support as cs
import pipeline_support as ps
from pipeline_support import Page

NAVIGATION = [("/procedures/", "Vorschriften"),
              ("/reaction_types/", "Reaktionstypen"), ("/help/", "Hilfe")]
FOOTER = "OrgSynDB · interne Vorschriften"
BANNER = "Beispieldaten – Mengenangaben nicht experimentell überprüft."
PANEL_LABELS = ["ID", "Produkt", "Summenformel", "Molmasse", "CAS", "SMILES",
                "Ansatzgröße", "Ausbeute", "Reaktionstyp", "Schlagwörter",
                "Autoren", "Erstellt", "Geändert", "Vorstufen"]
TITLES = {"procedures/index.html": "Vorschriften",
          "reaction_types/index.html": "Reaktionstypen",
          "tags/index.html": "Schlagwörter",
          "authors/index.html": "Autoren", "help/index.html": "Hilfe"}


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
                self.assertEqual(page.find("footer", "site-footer").norm(),
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
        else:
            self.assertRegex(field.get("aria-label"),
                             r"^Vorschriften .+ durchsuchen$")
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
        self.assertEqual(len(published), 8)
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
        self.assertEqual(pairs["Molmasse"].norm(), "180,16 g/mol")
        self.assertEqual(pairs["Ausbeute"].norm(), "75 %")
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
                         "8 Vorschriften")
        self.check_controls(page)
        statuses = page.find("details", "facet", data_facet="status")
        self.assertIsNotNone(statuses, "no status facet")
        self.assertEqual(
            [label.norm() for label in
             statuses.find_all("span", "facet-label")],
            ["Entwurf", "geprüft", "zurückgezogen"])
        self.assertEqual(self.table_ids(page), sorted(
            item.id for item in self.content()))

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
            [("/procedures/", "Alle Vorschriften anzeigen"),
             ("/tags/", "Alle Schlagwörter")])
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
        baseline = ps.FIXTURES / "baseline" / "OSDB-0100-baseline.md"
        (cls.sandbox.md_dir() / "OSDB-0100-baseline.en.md").write_text(
            baseline.read_text(encoding="utf-8"), encoding="utf-8")

    def test_every_procedure_is_published(self) -> None:
        """Scenario: Every procedure in every locale."""
        chosen = {item.id: item.path.name for item in self.content()}
        self.assertEqual(len(chosen), 9)
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
        self.assertEqual(first.find("span", "count").norm(), "(9)")
        rows = ps.catalogue_rows(self.page("procedures/index.html"))
        ids = [ps.row_cells(row)[0].norm() for row in rows]
        self.assertEqual(len(ids), 9)
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
        self.assertEqual(used_in, [("/procedures/osdb-0005/",
                                    "OSDB-0005 1-(Biphenyl-4-yl)ethanol")])


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
