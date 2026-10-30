"""Sequence pages, the sequence directory, the links to sequences and the
staging of sequences in theme builds (synthesis-sequences "Sequence
pages" and "Sequences beside procedures and compounds", site-build
"Hugo configuration", localization "Interface strings").

``SequenceSiteTests`` builds the test collection in English,
``GermanSequenceTests`` in German, ``PartialSequenceTests`` in German
without one German sequence, and ``IntermediateSiteTests`` adds a
sequence whose first step makes two compounds that the next step takes.
The links from the compound pages are also checked in
``test_compound_pages.py``.
"""

import json

import pipeline_support as ps
import sequence_support as ss
import support
import test_theme_integration as tti
from pipeline_support import Page, Sequence

BASELINE_PROCEDURE = ps.FIXTURES / "baseline" / "OSDB-0100-baseline.md"


class SequenceCase(tti.SiteCase):
    """Helpers for the scans of sequence pages."""

    def sequence_page(self, sequence: Sequence) -> Page:
        path = sequence.page_file(self.public)
        self.assertTrue(path.is_file(),
                        f"{path.relative_to(self.public)} was not built")
        return ps.load_page(self.public, path)

    def vocabulary(self) -> dict[str, str]:
        return ps.reaction_labels(self.sandbox.app, self.LOCALE)

    def by_sequence(self, ident: str) -> Sequence:
        return next(s for s in self.sequences() if s.id == ident)

    def check_page(self, sequence: Sequence) -> None:
        ss.check_sequence_page(
            self, self.sequence_page(sequence), sequence, self.by_id(),
            self.registry(), self.vocabulary(), self.LOCALE)

    def directory(self) -> Page:
        path = self.public / "sequences" / "index.html"
        self.assertTrue(path.is_file(), "sequences/ was not built")
        return ps.load_page(self.public, path)

    def check_directory(self) -> None:
        """The directory: its heading and one row per sequence, by ID."""
        texts = ss.TEXTS[self.LOCALE]
        page = self.directory()
        main = page.find("main")
        self.assertEqual([h.norm() for h in main.find_all("h1")],
                         [texts["title"]])
        self.assertEqual(page.title(), f"{texts['title']} | OrgSynDB")
        tables = main.find_all("table", "sequence-table")
        self.assertEqual(len(tables), 1)
        rows = tables[0].find_all("tr")
        header = [c for c in rows[0].elements() if c.tag in ("td", "th")]
        self.assertEqual([c.norm() for c in header], texts["columns"])
        sequences = self.sequences()
        self.assertEqual(len(rows) - 1, len(sequences))
        registry, by_id = self.registry(), self.by_id()
        for row, sequence in zip(rows[1:], sequences):
            cells = [c for c in row.elements() if c.tag in ("td", "th")]
            facts = ss.step_facts(sequence, by_id)
            with self.subTest(sequence=sequence.id):
                self.assertEqual(len(cells), 4)
                self.assertEqual(
                    [(l.target, l.node.norm())
                     for l in page.links(cells[0])],
                    [(f"/sequences/{sequence.slug}/", sequence.title)])
                targets = page.links(cells[1])
                self.assertEqual(
                    [(l.target, l.node.norm()) for l in targets],
                    [(f"/compounds/{sequence.target}/", ps.shown_name(
                        registry[sequence.target], self.LOCALE))])
                self.assertTrue(targets[0].node.has_class("compound"))
                self.assertEqual(cells[2].norm(), str(len(facts)))
                self.assertEqual(cells[3].norm(),
                                 f"{ss.overall_yield(facts)} %")

    def check_staging(self) -> None:
        """``build/content/sequences/`` holds one file per sequence,
        named after the base name, with the front matter of the variant
        for the locale and its language."""
        staged = self.sandbox.root / "build" / "content" / "sequences"
        self.assertTrue(staged.is_dir(), "nothing was staged")
        names = sorted(p.name for p in staged.iterdir())
        sequences = self.sequences()
        self.assertEqual(names, sorted(
            ps.base_name(s.path.name) + ".md" for s in sequences))
        for sequence in sequences:
            path = staged / (ps.base_name(sequence.path.name)
                             + ".md")
            text = path.read_text(encoding="utf-8")
            expected = dict(sequence.data)
            code = ps.language_of(sequence.path.name)
            if code is not None and "language" not in expected:
                expected["language"] = code
            with self.subTest(sequence=sequence.id):
                self.assertEqual(ps.front_matter(text), expected)
                self.assertEqual(ps.body_of(text).strip(),
                                 sequence.body.strip())


class SequenceSiteTests(SequenceCase):
    """The test collection, built in English."""

    def test_one_page_per_sequence(self) -> None:
        """Requirement: Sequence pages (/sequences/<slug>/)."""
        self.assertEqual([s.id for s in self.sequences()],
                         ["SEQ-0001", "SEQ-0002"])
        self.assertEqual(
            [s.path.name for s in self.sequences()],
            ["SEQ-0001-aspirin-from-wintergreen.md",
             "SEQ-0002-biphenylyl-ethanol.md"])
        built = sorted(p.parent.name for p in
                       (self.public / "sequences").glob("*/index.html"))
        self.assertEqual(built, ["seq-0001", "seq-0002"])

    def test_sequence_page_of_the_demo(self) -> None:
        """Scenario: Sequence page of the demo."""
        sequence = self.by_sequence("SEQ-0001")
        page = self.sequence_page(sequence)
        main = page.find("main")
        self.assertEqual(page.title(),
                         "Aspirin from oil of wintergreen | OrgSynDB")
        header = main.find("header", "sequence-header")
        self.assertEqual(header.find("p", "sequence-id").norm(), "SEQ-0001")
        self.assertEqual(header.find("h1").norm(),
                         "Aspirin from oil of wintergreen")
        self.assertEqual(
            [(p.label, p.definition.norm()) for p in
             page.definition_pairs(header.find("dl", "key-facts"))],
            [("Steps", "2"), ("Overall yield", "60 %")])
        scheme = main.find("figure", "sequence-scheme").find("ol")
        items = [n for n in scheme.elements() if n.tag == "li"]
        self.assertEqual([n.classes[0] for n in items], [
            "sequence-compound", "sequence-step", "sequence-compound",
            "sequence-step", "sequence-compound"])
        self.assertEqual(items[0].norm(), "Methyl salicylate")
        self.assertTrue(items[1].norm().startswith("Step 1"))
        self.assertEqual(items[2].norm(), "Salicylic acid")
        self.assertTrue(items[3].norm().startswith("Step 2"))
        self.assertEqual(items[4].norm(), "Acetylsalicylic acid")
        self.assertIn("Hydrolysis", items[1].norm())
        self.assertIn("80 %", items[1].norm())
        self.assertIn("Acylation", items[3].norm())
        self.assertIn("75 %", items[3].norm())
        steps = main.find("ol", "sequence-steps")
        self.assertEqual(
            [(l.target, l.node.norm()) for l in page.links(steps)],
            [("/procedures/osdb-0001/", "OSDB-0001 Salicylic acid"),
             ("/procedures/osdb-0002/",
              "OSDB-0002 Aspirin (acetylsalicylic acid)")])
        self.assertEqual(
            [li.norm() for li in steps.find_all("li")],
            ["OSDB-0001 Salicylic acid · Hydrolysis · 80 % · draft",
             "OSDB-0002 Aspirin (acetylsalicylic acid) · Acylation · "
             "75 % · draft"])
        self.assertEqual(scheme.find_all("img"), [])
        self.assertIsNotNone(page.heading("Notes"))
        self.assertIn("dried before the acetylation", main.norm())

    def test_every_sequence_page_follows_its_data(self) -> None:
        """Requirement: Sequence pages (header, scheme, steps, body)."""
        for sequence in self.sequences():
            with self.subTest(sequence=sequence.id):
                self.check_page(sequence)

    def test_a_step_of_a_general_procedure(self) -> None:
        """Scenario: Step of a general procedure."""
        sequence = self.by_sequence("SEQ-0002")
        page = self.sequence_page(sequence)
        main = page.find("main")
        steps = main.find("ol", "sequence-steps").find_all("li")
        labels = self.vocabulary()
        self.assertEqual(
            steps[1].norm(),
            "OSDB-0009 Secondary benzylic alcohols by sodium borohydride "
            f"reduction · entry 1 · {labels['reduction']} · 90 % · draft")
        self.assertNotIn("entry", steps[0].norm())
        scheme = main.find("figure", "sequence-scheme")
        links = [page.resolve(l.attrs["href"])
                 for l in scheme.find_all("a", "compound")]
        self.assertEqual(links[-1], "/compounds/1-biphenyl-4-yl-ethanol/")
        for other in ("1-phenylethanol", "1-4-bromophenyl-ethanol"):
            self.assertNotIn(f"/compounds/{other}/", links)
        self.assertEqual(
            [(p.label, p.definition.norm()) for p in page.definition_pairs(
                main.find("dl", "key-facts"))],
            [("Steps", "2"), ("Overall yield", "77 %")])

    def test_the_directory_lists_every_sequence(self) -> None:
        """Scenario: Directory lists every sequence."""
        self.check_directory()
        page = self.directory()
        model = next(m for m in page.tables()
                     if m.node.has_class("sequence-table"))
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Sequence", "Target", "Steps", "Overall yield"])
        self.assertEqual([[c.text for c in row[2:]] for row in model.rows[1:]],
                         [["2", "60 %"], ["2", "77 %"]])

    def test_links_from_the_procedure_panels(self) -> None:
        """Scenario: Links to the demo sequence (the panels)."""
        sequences = self.sequences()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                ss.check_panel_sequences(self, page, item, sequences, "en")
        for ident in ("OSDB-0001", "OSDB-0002"):
            page = self.page_of(self.by_id()[ident])
            panel = self.panel(page)
            self.assertEqual(
                [(page.resolve(l.attrs["href"]), l.norm())
                 for l in panel["Sequences"].definition.find_all(
                     "a", "sequence")],
                [("/sequences/seq-0001/",
                  "Aspirin from oil of wintergreen")])
        for ident in ("OSDB-0003", "OSDB-0005"):
            self.assertNotIn("Sequences",
                             self.panel(self.page_of(self.by_id()[ident])))

    def test_the_navigation_leads_to_the_directory(self) -> None:
        """Requirement: Page shell (the Sequences link)."""
        page = self.page_of(self.by_id()["OSDB-0001"])
        nav = page.find("header", "site-header").find("nav")
        self.assertIn(("/sequences/", "Sequences"),
                      [(l.target, l.node.norm()) for l in page.links(nav)])
        self.assertTrue(ps.target_file(self.public, "/sequences/").is_file())

    def test_sequence_pages_are_not_indexed(self) -> None:
        """Requirement: Sequence pages (no data-pagefind-body)."""
        for sequence in self.sequences():
            self.assertEqual(
                self.sequence_page(sequence).find_all(
                    data_pagefind_body=True), [])
        entry = json.loads((self.public / "pagefind"
                            / "pagefind-entry.json").read_text(
                                encoding="utf-8"))
        self.assertEqual(entry["languages"][self.LOCALE]["page_count"],
                         len(self.content()))

    def test_the_chosen_variants_are_staged(self) -> None:
        """Requirement: Sequence files (staged in
        build/content/sequences/)."""
        self.check_staging()
        staged = self.sandbox.root / "build" / "content" / "sequences"
        self.assertEqual(
            sorted(p.name for p in staged.iterdir()),
            ["SEQ-0001-aspirin-from-wintergreen.md",
             "SEQ-0002-biphenylyl-ethanol.md"])
        text = (staged / "SEQ-0001-aspirin-from-wintergreen.md").read_text(
            encoding="utf-8")
        self.assertNotIn("language", ps.front_matter(text))


class GermanSequenceTests(SequenceCase):
    """The test collection, built in German."""

    LOCALE = "de"

    def test_a_german_sequence_page(self) -> None:
        """Scenario: A German sequence page."""
        sequence = self.by_sequence("SEQ-0002")
        self.assertEqual(sequence.path.name,
                         "SEQ-0002-biphenylyl-ethanol.de.md")
        page = self.sequence_page(sequence)
        main = page.find("main")
        self.assertEqual(
            main.find("h1").norm(),
            "1-(Biphenyl-4-yl)ethanol aus 4′-Bromacetophenon")
        self.assertEqual(
            [(p.label, p.definition.norm()) for p in page.definition_pairs(
                main.find("dl", "key-facts"))],
            [("Stufen", "2"), ("Gesamtausbeute", "77 %")])
        steps = main.find("ol", "sequence-steps").find_all("li")
        self.assertIn(" · Eintrag 1 · ", steps[1].norm())
        self.assertNotIn("entry", steps[1].norm())
        scheme = main.find("figure", "sequence-scheme").norm()
        self.assertIn("Stufe 1", scheme)
        self.assertIn("Stufe 2", scheme)

    def test_every_german_sequence_page_follows_its_data(self) -> None:
        """Scenario: A German sequence page (all of them)."""
        for sequence in self.sequences():
            self.assertTrue(sequence.path.name.endswith(".de.md"))
            with self.subTest(sequence=sequence.id):
                self.check_page(sequence)

    def test_the_german_variant_of_the_first_sequence(self) -> None:
        """Scenario: A German sequence page (the first sequence)."""
        page = self.sequence_page(self.by_sequence("SEQ-0001"))
        main = page.find("main")
        self.assertEqual(main.find("h1").norm(), "Aspirin aus Wintergrünöl")
        self.assertEqual(
            [(p.label, p.definition.norm()) for p in page.definition_pairs(
                main.find("dl", "key-facts"))],
            [("Stufen", "2"), ("Gesamtausbeute", "60 %")])
        self.assertIsNotNone(page.heading("Anmerkungen"))

    def test_the_german_directory(self) -> None:
        """Scenario: Directory lists every sequence (German)."""
        self.check_directory()
        model = next(m for m in self.directory().tables()
                     if m.node.has_class("sequence-table"))
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Syntheseweg", "Zielverbindung", "Stufen",
                          "Gesamtausbeute"])
        self.assertEqual(self.directory().find("h1").norm(), "Synthesewege")
        self.assertEqual(self.directory().title(),
                         "Synthesewege | OrgSynDB")

    def test_the_german_links_from_procedures_and_compounds(self) -> None:
        """Scenario: German metadata panel (the Synthesewege pair)."""
        sequences = self.sequences()
        for item, page in self.procedure_pages():
            with self.subTest(procedure=item.id):
                ss.check_panel_sequences(self, page, item, sequences, "de")
        panel = self.panel(self.page_of(self.by_id()["OSDB-0002"]))
        self.assertEqual(
            [l.norm() for l in panel["Synthesewege"].definition.find_all(
                "a", "sequence")], ["Aspirin aus Wintergrünöl"])
        for key in self.registry():
            page = ps.load_page(self.public, self.public / "compounds"
                                / key / "index.html")
            with self.subTest(compound=key):
                ss.check_compound_sequences(self, page, key, sequences, "de")

    def test_the_german_variants_are_staged(self) -> None:
        """Requirement: Sequence files (the chosen variant is staged,
        with its language)."""
        self.check_staging()
        staged = self.sandbox.root / "build" / "content" / "sequences"
        text = (staged / "SEQ-0002-biphenylyl-ethanol.md").read_text(
            encoding="utf-8")
        self.assertEqual(ps.front_matter(text)["language"], "de")
        self.assertEqual(ps.front_matter(text)["title"],
                         "1-(Biphenyl-4-yl)ethanol aus 4′-Bromacetophenon")


class PartialSequenceTests(SequenceCase):
    """German build without the German SEQ-0002."""

    LOCALE = "de"

    @classmethod
    def prepare(cls) -> None:
        (cls.sandbox.root / "md" / "sequences"
         / "SEQ-0002-biphenylyl-ethanol.de.md").unlink()

    def test_a_sequence_without_a_german_variant_is_published(self) -> None:
        """Requirement: Sequence files (the variant is chosen as for a
        procedure)."""
        chosen = {s.id: s.path.name for s in self.sequences()}
        self.assertEqual(chosen, {
            "SEQ-0001": "SEQ-0001-aspirin-from-wintergreen.de.md",
            "SEQ-0002": "SEQ-0002-biphenylyl-ethanol.md"})
        page = self.sequence_page(self.by_sequence("SEQ-0002"))
        self.assertEqual(
            page.find("main").find("h1").norm(),
            "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone")
        for sequence in self.sequences():
            with self.subTest(sequence=sequence.id):
                self.check_page(sequence)
        self.check_directory()
        self.check_staging()


class IntermediateSiteTests(SequenceCase):
    """The test collection plus a sequence whose first step makes two
    compounds, in an order that differs from the order of the substrates
    of the second step, both of which the second step takes."""

    FIXTURES = ("OSDB-0907-two-products.md",)

    @classmethod
    def prepare(cls) -> None:
        text = support.apply_edits(
            BASELINE_PROCEDURE.read_text(encoding="utf-8"),
            [support.insert_line(
                'substrates = ["cis-stilbene", "trans-stilbene"]')])
        (cls.sandbox.md_dir() / BASELINE_PROCEDURE.name).write_text(
            text, encoding="utf-8")
        ps.put_compounds(cls.sandbox, "ethyl-acetate", "cis-stilbene",
                         "trans-stilbene")
        (cls.sandbox.root / "md" / "sequences"
         / "SEQ-0003-stilbenes.md").write_text(
            '+++\nid = "SEQ-0003"\nslug = "seq-0003"\n'
            'title = "Ethyl acetate from the stilbenes"\n'
            "date = 2026-10-24T09:00:00+02:00\n"
            "lastmod = 2026-10-24T09:00:00+02:00\n"
            'target = "ethyl-acetate"\n'
            'steps = [{ procedure = "OSDB-0907" }, '
            '{ procedure = "OSDB-0100" }]\n+++\n\n'
            "## Notes\n\nBoth isomers are carried on.\n", encoding="utf-8")

    def test_the_first_product_in_order_carries_on(self) -> None:
        """Requirement: Sequence pages (the intermediate is the first
        product that the next step takes)."""
        sequence = self.by_sequence("SEQ-0003")
        page = self.sequence_page(sequence)
        scheme = page.find("figure", "sequence-scheme").find("ol")
        items = [n for n in scheme.elements() if n.tag == "li"]
        self.assertEqual(len(items), 4)
        self.assertEqual([n.classes[0] for n in items], [
            "sequence-step", "sequence-compound", "sequence-step",
            "sequence-compound"])
        self.assertEqual(items[1].norm(), "trans-Stilbene")
        self.assertIn("45 %", items[0].norm())
        self.assertEqual(items[3].norm(), "Ethyl acetate")
        images = scheme.find_all("img")
        self.assertEqual(
            [(page.resolve(i.attrs.get("src", "")), i.attrs.get("alt"))
             for i in images],
            [("/structures/trans-stilbene.svg",
              "Structure of trans-Stilbene"),
             ("/structures/ethyl-acetate.svg",
              "Structure of Ethyl acetate")])
        for image in images:
            self.assertTrue(ps.target_file(
                self.public, page.resolve(image.attrs["src"])).is_file())
        self.assertEqual(
            [(p.label, p.definition.norm()) for p in page.definition_pairs(
                page.find("main").find("dl", "key-facts"))],
            [("Steps", "2"), ("Overall yield", "38 %")])
        self.check_page(sequence)


if __name__ == "__main__":
    import unittest
    unittest.main()
