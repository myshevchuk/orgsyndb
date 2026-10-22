"""German site tests: HTML scans and searches of a sandbox build
(localization). ``GermanSiteTests`` builds the demo collection with its
German translations; ``PartialTranslationTests`` builds it with one
translation removed. Tests skip, naming the missing tool or cache, as the
other integration tests do.
"""

import pipeline_support as ps
from pipeline_support import Page

NAVIGATION = [("/de/procedures/", "Vorschriften"),
              ("/de/reaction_types/", "Reaktionstypen"),
              ("/de/tags/", "Schlagwörter"), ("/de/authors/", "Autoren"),
              ("/de/search/", "Suche")]
FOOTER = "OrgSynDB · interne Vorschriften"
BANNER = "Beispieldaten – Mengenangaben nicht experimentell überprüft."
PANEL_LABELS = ["ID", "Produkt", "Summenformel", "Molmasse", "CAS", "SMILES",
                "Ansatzgröße", "Ausbeute", "Reaktionstyp", "Schlagwörter",
                "Autoren", "Erstellt", "Geändert", "Vorstufen"]


def language_links(page: Page) -> list[tuple[str, str, str]]:
    """(target, hreflang, text) of each link of the language switch."""
    nav = page.find("nav", "language-switch")
    if nav is None:
        return []
    return [(link.target, link.node.get("hreflang"), link.node.norm())
            for link in page.links(nav)]


class GermanSiteTests(ps.ThemeBuildCase):
    """The demo collection with every German translation."""

    def german_page(self, slug: str) -> Page:
        path = self.public / "de" / "procedures" / slug / "index.html"
        self.assertTrue(path.is_file(), f"de/procedures/{slug} not built")
        return ps.load_page(self.public, path)

    def test_every_german_page_has_the_german_shell(self) -> None:
        """Scenario: German page shell."""
        pages = self.pages("de")
        self.assertGreater(len(pages), 20)
        for path, page in pages:
            with self.subTest(page=str(path.relative_to(self.public))):
                self.assertEqual(page.find("html").get("lang"), "de")
                skip = page.find("a", "skip-link")
                self.assertEqual(skip.norm(), "Zum Inhalt springen")
                nav = page.find("header", "site-header").find(
                    "nav", aria_label="Website")
                self.assertIsNotNone(nav, "no nav[aria-label=Website]")
                links = [(l.target, l.node.norm()) for l in page.links(nav)]
                self.assertEqual(links, NAVIGATION)
                self.assertEqual(page.find("footer", "site-footer").norm(),
                                 FOOTER)
                title = page.title()
                self.assertTrue(title == "OrgSynDB"
                                or title.endswith(" | OrgSynDB"), title)

    def test_english_pages_keep_the_english_language(self) -> None:
        """Scenario: German page shell (English pages)."""
        for path, page in self.pages("en"):
            with self.subTest(page=str(path.relative_to(self.public))):
                self.assertEqual(page.find("html").get("lang"), "en")

    def test_translations_link_to_each_other(self) -> None:
        """Scenario: Language switch."""
        english = {item.id: item for item in self.content("en")}
        german = self.content("de")
        self.assertEqual(sorted(item.id for item in german), sorted(english))
        for item in german:
            with self.subTest(procedure=item.id):
                theirs = ps.load_page(self.public,
                                      english[item.id].page_file(self.public))
                ours = ps.load_page(self.public, item.page_file(self.public))
                self.assertEqual(language_links(theirs), [
                    (f"/de/procedures/{item.slug}/", "de", "Deutsch")])
                self.assertEqual(language_links(ours), [
                    (f"/procedures/{item.slug}/", "en", "English")])
        home = ps.load_page(self.public, self.public / "index.html")
        self.assertEqual(language_links(home), [("/de/", "de", "Deutsch")])

    def test_german_panel_of_the_markdown_seed(self) -> None:
        """Scenario: German metadata panel."""
        page = self.german_page("osdb-0002")
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
                         [("/de/reaction_types/acylation/", "Acylierung")])
        self.assertEqual(reaction[0].node.get("data-pagefind-filter"),
                         "Reaktionstyp")
        precursor = page.links(pairs["Vorstufen"])
        self.assertEqual(
            [(l.target, l.node.get("hreflang"), l.node.norm())
             for l in precursor],
            [("/de/procedures/osdb-0001/", None, "OSDB-0001 Salicylsäure")])
        button = page.find("button", "copy-button")
        self.assertEqual((button.norm(), button.get("data-copied")),
                         ("Kopieren", "Kopiert"))
        self.assertIsNotNone(page.heading("Reagenzien"))

    def test_german_term_titles_use_german_labels(self) -> None:
        """Scenario: German labels for reaction types."""
        path = (self.public / "de" / "reaction_types" / "aldol-condensation"
                / "index.html")
        page = ps.load_page(self.public, path)
        self.assertEqual(page.find("h1").norm(), "Aldolkondensation")
        self.assertEqual(page.title(), "Aldolkondensation | OrgSynDB")
        labels = ps.reaction_labels(self.sandbox.app, "de")
        used = {slug for item in self.content("de")
                for slug in item.data["reaction_types"]}
        expected = sorted(labels[slug] for slug in used)
        self.assertIn("Veresterung", expected)
        for relative in ("de/index.html", "de/reaction_types/index.html"):
            page = ps.load_page(self.public, self.public / relative)
            shown = [l.node.norm() for l in page.links()
                     if "/de/reaction_types/" in l.target
                     and l.target != "/de/reaction_types/"]
            with self.subTest(page=relative):
                self.assertEqual(shown, expected)

    def test_german_lists_hold_the_german_procedures(self) -> None:
        """Scenario: German lists."""
        german = sorted(self.content("de"), key=lambda item: item.id)
        page = ps.load_page(self.public, self.public / "de" / "procedures"
                            / "index.html")
        table = page.find("table", "procedure-list")
        rows = [[c.norm() for c in tr.find_all("td")]
                for tr in table.find_all("tr")][1:]
        self.assertEqual([row[:2] for row in rows],
                         [[item.id, item.title] for item in german])
        header = [th.norm() for th in table.find_all("th")]
        self.assertEqual(header, ["ID", "Vorschrift", "Reaktionstyp",
                                  "Status", "Erstellt", "Geändert"])

    def test_german_index_finds_german_words(self) -> None:
        """Scenario: German search index."""
        ps.require_node()
        out = ps.pagefind_search(self.public, [
            {"term": "Zimtsäure", "filters": None, "normalise": True},
            {"term": "Verseifung", "filters": None, "normalise": True},
            {"term": None, "filters": {"Reaktionstyp": "Hydrolyse"},
             "normalise": True},
        ], language="de")
        ids = [sorted({hit["id"] for hit in results})
               for results in out["results"]]
        self.assertIn("OSDB-0008", ids[0])
        self.assertEqual(ids[1], ["OSDB-0001", "OSDB-0008"])
        self.assertEqual(ids[2], ["OSDB-0001", "OSDB-0008"])
        self.assertEqual(sorted(out["filters"]),
                         ["Autor", "Reaktionstyp", "Schlagwort", "Status"])
        titles = {item.title for item in self.content("de")}
        for results in out["results"]:
            for hit in results:
                self.assertIn(hit["title"], titles)


class PartialTranslationTests(ps.ThemeBuildCase):
    """The demo collection without the German OSDB-0001 and OSDB-0004."""

    REMOVED = ("OSDB-0001-salicylic-acid.de.org",
               "OSDB-0004-4-acetylbiphenyl.de.org")

    @classmethod
    def prepare(cls) -> None:
        for name in cls.REMOVED:
            (cls.sandbox.root / "org" / "procedures" / name).unlink()

    def test_an_untranslated_procedure_has_no_language_link(self) -> None:
        """Scenario: Untranslated procedure."""
        self.assertFalse((self.public / "de" / "procedures" / "osdb-0001")
                         .exists())
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0001" / "index.html")
        self.assertEqual(language_links(page), [])

    def test_links_fall_back_to_another_language(self) -> None:
        """Scenario: Links to an untranslated procedure."""
        for slug, cls_name, target in (
                ("osdb-0002", "precursor", "/procedures/osdb-0001/"),
                ("osdb-0005", "precursor", "/procedures/osdb-0004/")):
            page = ps.load_page(self.public, self.public / "de"
                                / "procedures" / slug / "index.html")
            links = [l for l in page.links() if l.node.has_class(cls_name)]
            with self.subTest(page=slug):
                self.assertEqual(
                    [(l.target, l.node.get("hreflang")) for l in links],
                    [(target, "en")])
                self.assertTrue(ps.target_file(self.public, links[0].target)
                                .is_file())
        english = ps.load_page(self.public, self.public / "procedures"
                               / "osdb-0004" / "index.html")
        used_in = [(l.target, l.node.get("hreflang")) for l in english.links()
                   if l.node.has_class("used-in")]
        self.assertEqual(used_in, [("/procedures/osdb-0005/", None)])

    def test_the_german_home_counts_the_german_procedures(self) -> None:
        """Scenario: German lists (partial translation)."""
        page = ps.load_page(self.public, self.public / "de" / "index.html")
        count = len(self.content("de"))
        self.assertEqual(count, 6)
        self.assertIn(f"Alle {count} Vorschriften", page.find("main").norm())
