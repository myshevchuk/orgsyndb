"""Tests of the registry's pages (lab-registry: Registry pages)."""

import re
from typing import Any

from vocabulary.models import Project, ReactionType

from . import (berlin, frozen, make_group, make_batch, make_item,
               make_substance, make_task, make_vessel, table)
from .collection_support import accept, make_import, make_procedure
from .demo_support import SeededCase
from .inventory_support import SUBSTANCE_PAGE
from .planning_support import section
from .registry_support import (REGISTRY, VOCABULARIES, RegistryCase,
                               substance_url, term_url)
from .structure_support import ETHANOL

COLUMNS_DE = ["Name", "Schlüssel", "Kurzname", "Bestandsgruppe",
              "Stoffklassen", "Summenformel", "Molmasse", "Artikelnr."]
COLUMNS_EN = ["Name", "Key", "Short name", "Inventory group",
              "Chemical classes", "Formula", "Molar mass", "Article no."]


def hrefs(root: Any) -> list[str]:
    return [a.get("href") for a in root.find_all("a")]


def names(root: Any) -> list[str]:
    """The names in the list's first column, in order."""
    header, rows = table(root)
    return [row[header[0]].text() for row in rows]


class ListTests(RegistryCase):

    def test_the_page_needs_no_sign_in(self) -> None:
        self.assertEqual(self.client.get(REGISTRY).status_code, 200)

    def test_the_heading_is_followed_by_the_number(self) -> None:
        root = self.get(REGISTRY)
        heading = root.find("h1")
        self.assertEqual(heading.text(), "Substanzen")
        self.assertRegex(heading.parent.text(), r"Substanzen\D{0,5}3\b")

    def test_the_heading_in_english(self) -> None:
        accept(language="en")
        heading = self.get(REGISTRY).find("h1")
        self.assertEqual(heading.text(), "Substances")
        self.assertRegex(heading.parent.text(), r"Substances\D{0,5}3\b")

    def test_the_columns(self) -> None:
        header, _rows = table(self.get(REGISTRY))
        self.assertEqual(header, COLUMNS_DE)

    def test_the_english_columns(self) -> None:
        accept(language="en")
        header, _rows = table(self.get(REGISTRY))
        self.assertEqual(header, COLUMNS_EN)

    def test_the_cells_of_a_substance(self) -> None:
        header, rows = table(self.get(REGISTRY))
        row = next(r for r in rows if r["Schlüssel"].text()
                   == "cinnamic-acid")
        self.assertEqual(row["Name"].text(), "(E)-Zimtsäure")
        self.assertEqual(row["Kurzname"].text(), "ZS")
        self.assertIn("Endprodukte", row["Bestandsgruppe"].text())
        self.assertIn("Carbonsäuren", row["Stoffklassen"].text())
        self.assertEqual(row["Summenformel"].text(), "C9H8O2")
        self.assertRegex(row["Molmasse"].text(), r"148[,.]16")
        self.assertEqual(row["Artikelnr."].text(), "CH-0012")

    def test_the_name_links_to_the_substance(self) -> None:
        header, rows = table(self.get(REGISTRY))
        for row in rows:
            key = row["Schlüssel"].text()
            with self.subTest(key=key):
                self.assertEqual(
                    [a.get("href") for a in row["Name"].find_all("a")],
                    [substance_url(key)])

    def test_the_order_ignores_case(self) -> None:
        make_substance("zinc-acetate", "Zinc acetate")
        make_substance("acetone", "acetone")
        make_substance("benzaldehyde", "Benzaldehyde")
        self.assertEqual(
            [name for name in names(self.get(REGISTRY))
             if name in ("acetone", "Benzaldehyde", "Zinc acetate")],
            ["acetone", "Benzaldehyde", "Zinc acetate"])

    def test_the_content_leaves_the_vocabularies_to_the_menu(self) -> None:
        """Requirement: Registry pages (no links to the vocabularies
        above the table)."""
        main = self.get(REGISTRY).find("main")
        pages = {term_url(vocabulary) for vocabulary in VOCABULARIES}
        self.assertEqual([h for h in hrefs(main) if h in pages], [])

    def test_the_content_leaves_the_notebooks_and_imports_to_the_menu(
            self) -> None:
        """Requirement: Registry pages (no links to the notebooks and
        imports above the table)."""
        main = self.get(REGISTRY).find("main")
        self.assertEqual([h for h in hrefs(main)
                          if h.startswith(("/lab/journal/",
                                           "/lab/collection/"))], [])

    def test_the_new_substance_link_needs_a_sign_in(self) -> None:
        anonymous = self.get(REGISTRY)
        self.assertNotIn(substance_url("new"), hrefs(anonymous))
        self.assertFalse([a for a in anonymous.find_all("a")
                          if a.text() == "Neue Substanz"])
        signed_in = self.get(REGISTRY, signed_in=True)
        link = next(a for a in signed_in.find_all("a")
                    if a.text() == "Neue Substanz")
        self.assertEqual(link.get("href"), substance_url("new"))

    def test_the_new_substance_link_in_english(self) -> None:
        accept(language="en")
        root = self.get(REGISTRY, signed_in=True)
        self.assertTrue([a for a in root.find_all("a")
                         if a.text() == "New substance"])


class SearchTests(RegistryCase):

    def found(self, query: str) -> list[str]:
        header, rows = table(self.get(f"{REGISTRY}?q={query}"))
        return sorted(row["Schlüssel"].text() for row in rows)

    def test_the_search_field_is_labelled(self) -> None:
        search = self.get(REGISTRY).find("main").find("input", name="q")
        self.assertIn("Substanzen suchen", search.parent.text())

    def test_the_search_field_in_english(self) -> None:
        accept(language="en")
        search = self.get(REGISTRY).find("main").find("input", name="q")
        self.assertIn("Search substances", search.parent.text())

    def test_the_key(self) -> None:
        self.assertEqual(self.found("new-comp"), ["new-compound-7"])

    def test_the_name(self) -> None:
        self.assertEqual(self.found("acetoph"), ["acetophenone"])

    def test_the_german_name(self) -> None:
        self.assertEqual(self.found("zimts"), ["cinnamic-acid"])

    def test_the_short_name(self) -> None:
        self.assertEqual(self.found("ZS"), ["cinnamic-acid"])

    def test_the_cas_number(self) -> None:
        self.assertEqual(self.found("140-10"), ["cinnamic-acid"])

    def test_case_does_not_matter(self) -> None:
        self.assertEqual(self.found("ACETOPH"), ["acetophenone"])
        self.assertEqual(self.found("zs"), ["cinnamic-acid"])

    def test_other_fields_are_not_searched(self) -> None:
        self.assertEqual(self.found("C9H8O2"), [])
        self.assertEqual(self.found("Notiz"), [])

    def test_without_text_every_substance_is_listed(self) -> None:
        self.assertEqual(len(self.found("")), 3)

    def test_the_count_follows_the_search(self) -> None:
        root = self.get(f"{REGISTRY}?q=acetoph")
        self.assertRegex(root.find("h1").parent.text(),
                         r"Substanzen\D{0,5}1\b")


class SubstancePageTests(RegistryCase):

    def test_the_page_needs_no_sign_in(self) -> None:
        response = self.client.get(substance_url("cinnamic-acid"))
        self.assertEqual(response.status_code, 200)

    def test_the_name_is_the_heading(self) -> None:
        self.assertEqual(
            self.get(substance_url("cinnamic-acid")).find("h1").text(),
            "(E)-Zimtsäure")
        self.assertEqual(
            self.get(substance_url("acetophenone")).find("h1").text(),
            "Acetophenone")

    def test_the_heading_in_english(self) -> None:
        accept(language="en")
        self.assertEqual(
            self.get(substance_url("cinnamic-acid")).find("h1").text(),
            "(E)-Cinnamic acid")

    def test_every_field_is_shown(self) -> None:
        text = self.get(substance_url("cinnamic-acid")).text()
        for shown in ("cinnamic-acid", "(E)-Cinnamic acid",
                      "(E)-Zimtsäure", "ZS", "Endprodukte", "Carbonsäuren",
                      "C9H8O2", "OC(=O)/C=C/c1ccccc1", "140-10-3", "Notiz",
                      "CH-0012"):
            with self.subTest(shown=shown):
                self.assertIn(shown, text)
        self.assertRegex(text, r"148[,.]16")

    def test_a_missing_value_shows_a_dash(self) -> None:
        text = self.get(substance_url("new-compound-7")).text()
        # German name, short name, classes, formula, molar mass, SMILES,
        # CAS number, note and article number.
        self.assertGreaterEqual(text.count("–"), 9)

    def test_a_full_substance_shows_few_dashes(self) -> None:
        bare = self.get(substance_url("new-compound-7")).text()
        full = self.get(substance_url("cinnamic-acid")).text()
        self.assertLess(full.count("–"), bare.count("–"))

    def site_links(self, key: str) -> list[str]:
        """The targets of the links in the content of the page of
        ``key`` that read ``In der Sammlung`` or ``In the collection``,
        or that lead under ``/compounds/``. The site's menu around the
        content is not the registry's and is left out."""
        return [a.get("href")
                for a in self.get(substance_url(key)).find("main")
                .find_all("a")
                if a.text() in ("In der Sammlung", "In the collection")
                or a.get("href", "").startswith("/compounds/")]

    def test_no_site_link_follows_an_accepted_import(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`, no
        path under `/compounds/`), in both languages."""
        for language in ("de", "en"):
            accept(language=language)
            for key in ("cinnamic-acid", "acetophenone", "new-compound-7"):
                with self.subTest(language=language, key=key):
                    self.assertEqual(self.site_links(key), [])

    def test_no_site_link_without_an_import(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`)."""
        self.assertEqual(self.site_links("cinnamic-acid"), [])

    def test_a_refused_import_gives_no_link(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`)."""
        make_import(outcome="refused")
        self.assertEqual(self.site_links("cinnamic-acid"), [])

    def test_a_substance_added_after_the_import_has_no_link(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`,
        whenever the substance was created)."""
        accept(language="de")
        make_substance("ethyl-acetate", "Ethylacetat")
        root = self.get(substance_url("ethyl-acetate"))
        self.assertEqual(root.find("h1").text(), "Ethylacetat")
        self.assertEqual(self.site_links("ethyl-acetate"), [])

    def test_the_import_and_the_substance_of_one_moment(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`,
        whatever the import and the creation of the substance)."""
        with frozen(berlin(2026, 11, 3)):
            make_substance("same-moment", "Same")
            accept(language="de")
        with frozen(berlin(2026, 11, 3, 12, 1)):
            make_substance("a-minute-later", "Later")
        for key in ("same-moment", "a-minute-later"):
            with self.subTest(key=key):
                self.assertEqual(self.site_links(key), [])

    def test_an_edited_substance_has_no_link(self) -> None:
        """Requirement: Registry pages (no link `In der Sammlung`,
        whatever the substance's history)."""
        with frozen(berlin(2026, 11, 1)):
            made = make_substance("edited-later", "Edited")
        with frozen(berlin(2026, 11, 2)):
            accept(language="de")
        with frozen(berlin(2026, 11, 3)):
            made.note = "Changed after the import"
            made.save()
        self.assertEqual(self.site_links("edited-later"), [])

    def test_the_edit_link_needs_a_sign_in(self) -> None:
        anonymous = self.get(substance_url("cinnamic-acid"))
        self.assertFalse([a for a in anonymous.find_all("a")
                          if a.text() == "Bearbeiten"])
        signed_in = self.get(substance_url("cinnamic-acid"),
                             signed_in=True)
        links = [a for a in signed_in.find_all("a")
                 if a.text() == "Bearbeiten"]
        self.assertEqual([a.get("href") for a in links],
                         [substance_url("cinnamic-acid", "edit")])

    def test_an_unknown_key_answers_404(self) -> None:
        self.assertEqual(
            self.client.get(substance_url("no-such-substance")).status_code,
            404)


class SectionTests(RegistryCase):
    """The sections ``Gebinde``, ``Chargen`` and ``Aufträge``."""

    def sections(self, key: str) -> dict:
        root = self.get(substance_url(key))
        return {name: section(root, name)
                for name in ("Gebinde", "Chargen", "Aufträge")}

    def test_empty_sections_say_none(self) -> None:
        for name, held in self.sections("acetophenone").items():
            with self.subTest(section=name):
                self.assertIn("Keine", held.text())
                self.assertFalse(held.find_all("a"))

    def test_the_sections_in_english(self) -> None:
        accept(language="en")
        root = self.get(substance_url("acetophenone"))
        for name in ("Containers", "Batches", "Tasks"):
            with self.subTest(section=name):
                self.assertIn("None", section(root, name).text())

    def test_the_containers_of_its_article(self) -> None:
        small = make_item(self.kl, "CH-0012", size="10", unit="umol",
                          substance=self.records["cinnamic"])
        large = make_item(self.kl, "CH-0012", size="50", unit="umol",
                          substance=self.records["cinnamic"])
        make_item(self.kl, "CH-0099")
        held = self.sections("cinnamic-acid")["Gebinde"]
        self.assertEqual(
            sorted(a.get("href") for a in held.find_all("a")),
            sorted(f"/lab/inventory/items/{item.pk}/"
                   for item in (small, large)))
        self.assertNotIn("Keine", held.text())

    def test_the_batches_of_the_substance(self) -> None:
        """Requirement: Registry pages (`Chargen`, its batches, each
        linking to its page)."""
        from datetime import date
        cinnamic = self.records["cinnamic"]
        older = make_batch(self.kl, substance=cinnamic, number="B-1",
                           date=date(2026, 1, 1))
        newer = make_batch(self.kl, substance=cinnamic, number="B-2",
                           date=date(2026, 6, 1))
        undated = make_batch(self.kl, substance=cinnamic, number="B-3")
        make_batch(self.kl, substance=self.records["acetophenone"],
                   number="B-OTHER")
        held = self.sections("cinnamic-acid")["Chargen"]
        self.assertEqual(
            [a.get("href") for a in held.find_all("a")],
            [f"/lab/inventory/batches/{batch.pk}/"
             for batch in (newer, older, undated)])
        self.assertNotIn("Keine", held.text())

    def test_a_batch_is_followed_by_the_amount_in_its_open_vessels(
            self) -> None:
        from .inventory_support import has_amount
        cinnamic = self.records["cinnamic"]
        batch = make_batch(self.kl, substance=cinnamic, number="B-1")
        make_vessel(self.kl, batch, unit="g", amount="2", flask=True)
        make_vessel(self.kl, batch, unit="mg", amount="30", location="A")
        make_vessel(self.kl, batch, unit="mg", amount="0", location="B")
        held = self.sections("cinnamic-acid")["Chargen"]
        text = held.text()
        self.assertTrue(has_amount(text, "2", "g"), text)
        self.assertTrue(has_amount(text, "30", "mg"), text)

    def test_a_batch_without_vessels_is_listed(self) -> None:
        batch = make_batch(self.kl, substance=self.records["cinnamic"],
                           number="B-1")
        held = self.sections("cinnamic-acid")["Chargen"]
        self.assertEqual([a.get("href") for a in held.find_all("a")],
                         [f"/lab/inventory/batches/{batch.pk}/"])

    def test_the_batches_of_a_substance_without_an_article(self) -> None:
        batch = make_batch(self.kl,
                           substance=self.records["acetophenone"],
                           number="B-1")
        held = self.sections("acetophenone")["Chargen"]
        self.assertEqual([a.get("href") for a in held.find_all("a")],
                         [f"/lab/inventory/batches/{batch.pk}/"])
        self.assertIn("Keine", self.sections("acetophenone")["Gebinde"]
                      .text())

    def test_no_bulk_lots_section_remains(self) -> None:
        root = self.get(substance_url("cinnamic-acid"))
        self.assertNotIn("Bulk-Lose", root.text())

    def test_the_tasks(self) -> None:
        task = make_task(self.kl, self.records["cinnamic"])
        make_task(self.kl, self.records["acetophenone"])
        held = self.sections("cinnamic-acid")["Aufträge"]
        self.assertEqual([a.get("href") for a in held.find_all("a")],
                         [f"/lab/tasks/{task.number}/"])


class VocabularyPageTests(RegistryCase):

    def rows(self, vocabulary: str, signed_in: bool = False) -> list:
        root = self.get(term_url(vocabulary), signed_in)
        return table(root)[1] if root.find("table") else []

    def test_every_vocabulary_answers_without_a_sign_in(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                self.assertEqual(
                    self.client.get(term_url(vocabulary)).status_code, 200)

    def test_the_heading_is_the_vocabulary(self) -> None:
        for vocabulary, (german, english) in VOCABULARIES.items():
            with self.subTest(vocabulary=vocabulary):
                self.assertEqual(
                    self.get(term_url(vocabulary)).find("h1").text(),
                    german)
        accept(language="en")
        for vocabulary, (german, english) in VOCABULARIES.items():
            with self.subTest(vocabulary=vocabulary, language="en"):
                self.assertEqual(
                    self.get(term_url(vocabulary)).find("h1").text(),
                    english)

    def test_the_columns_of_a_tree(self) -> None:
        for vocabulary in ("chemical-classes", "groups", "projects"):
            with self.subTest(vocabulary=vocabulary):
                header, _ = table(self.get(term_url(vocabulary)))
                self.assertEqual(header, [
                    "Schlüssel", "Bezeichnung", "Bezeichnung deutsch",
                    "Oberbegriff", "Verwendet"])

    def test_the_columns_of_the_reaction_types(self) -> None:
        header, _ = table(self.get(term_url("reaction-types")))
        self.assertEqual(header, ["Schlüssel", "Bezeichnung",
                                  "Bezeichnung deutsch", "Verwendet"])

    def test_the_english_columns(self) -> None:
        accept(language="en")
        header, _ = table(self.get(term_url("groups")))
        self.assertEqual(header, ["Key", "Label", "German label", "Parent",
                                  "In use"])
        header, _ = table(self.get(term_url("reaction-types")))
        self.assertEqual(header, ["Key", "Label", "German label",
                                  "In use"])

    def test_terms_follow_their_parents(self) -> None:
        make_group("buffers", "Buffers", make_group("reagents"))
        keys = [row["Schlüssel"].text() for row in self.rows("groups")]
        self.assertEqual(keys, [
            "purchased", "reagents", "buffers", "starting-materials",
            "synthesised", "final-products", "intermediates"])

    def test_the_classes_follow_their_parents(self) -> None:
        keys = [row["Schlüssel"].text()
                for row in self.rows("chemical-classes")]
        self.assertEqual(keys, ["carbonyl-compounds", "carboxylic-acids",
                                "ketones", "aryl-ketones"])

    def test_a_term_shows_its_labels_and_parent(self) -> None:
        row = next(r for r in self.rows("groups")
                   if r["Schlüssel"].text() == "reagents")
        self.assertEqual(row["Bezeichnung"].text(), "Reagents")
        self.assertEqual(row["Bezeichnung deutsch"].text(), "Reagenzien")
        self.assertTrue(any(shown in row["Oberbegriff"].text()
                            for shown in ("purchased", "Zugekauft")),
                        row["Oberbegriff"].text())
        top = next(r for r in self.rows("groups")
                   if r["Schlüssel"].text() == "purchased")
        self.assertNotIn("purchased", top["Oberbegriff"].text())

    def test_the_count_is_the_substances_naming_the_term(self) -> None:
        counts = {row["Schlüssel"].text(): row["Verwendet"].text()
                  for row in self.rows("groups")}
        self.assertEqual(counts, {
            "purchased": "0", "reagents": "0", "starting-materials": "0",
            "synthesised": "0", "intermediates": "2",
            "final-products": "1"})

    def test_the_count_of_the_classes(self) -> None:
        make_substance("a", classes=["carboxylic-acids", "ketones"])
        counts = {row["Schlüssel"].text(): row["Verwendet"].text()
                  for row in self.rows("chemical-classes")}
        self.assertEqual(counts, {
            "carbonyl-compounds": "0", "carboxylic-acids": "2",
            "ketones": "1", "aryl-ketones": "1"})

    def test_a_vocabulary_without_terms_lists_none(self) -> None:
        self.assertEqual(self.rows("projects"), [])
        self.assertEqual(self.rows("reaction-types"), [])

    def test_keys_link_to_the_forms_for_a_signed_in_user(self) -> None:
        anonymous = self.get(term_url("groups"))
        self.assertFalse([h for h in hrefs(anonymous)
                          if h.endswith("/edit/")])
        self.assertFalse([a for a in anonymous.find_all("a")
                          if a.text() == "Neuer Begriff"])
        for row in self.rows("groups", signed_in=True):
            key = row["Schlüssel"].text()
            with self.subTest(key=key):
                self.assertEqual(
                    [a.get("href") for a in row["Schlüssel"].find_all("a")],
                    [term_url("groups", key, "edit")])

    def test_the_new_term_link_needs_a_sign_in(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                root = self.get(term_url(vocabulary), signed_in=True)
                links = [a for a in root.find_all("a")
                         if a.text() == "Neuer Begriff"]
                self.assertEqual([a.get("href") for a in links],
                                 [term_url(vocabulary, "new")])

    def test_the_new_term_link_in_english(self) -> None:
        accept(language="en")
        root = self.get(term_url("groups"), signed_in=True)
        self.assertTrue([a for a in root.find_all("a")
                         if a.text() == "New term"])

    def test_no_link_back_to_the_substances(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                main = self.get(term_url(vocabulary)).find("main")
                self.assertNotIn(REGISTRY, hrefs(main))

    def test_projects_and_reaction_types_count_procedures(self) -> None:
        """Scenario: Uses of a reaction type."""
        ReactionType.objects.create(key="acylation", label="Acylation")
        esterification = ReactionType.objects.create(
            key="esterification", label="Esterification")
        course = Project.objects.create(key="course", label="Course")
        received = make_import()
        make_procedure(received, "OSDB-0002", reaction_type=esterification,
                       project=course)
        make_procedure(received, "OSDB-0003", reaction_type=esterification,
                       withdrawn=True)
        self.assertEqual(
            {row["Schlüssel"].text(): row["Verwendet"].text()
             for row in self.rows("reaction-types")},
            {"acylation": "0", "esterification": "2"})
        self.assertEqual(
            {row["Schlüssel"].text(): row["Verwendet"].text()
             for row in self.rows("projects")},
            {"course": "1"})

    def test_any_other_vocabulary_answers_404(self) -> None:
        for name in ("substances", "inventory-groups", "Groups", "nope"):
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(f"{REGISTRY}{name}/").status_code, 404)


class DemoRegistryPageTests(SeededCase):
    """The scenarios that name the demo data set."""

    def test_substance_list_and_search(self) -> None:
        """Scenario: Substance list and search."""
        header, rows = table(self.get(f"{REGISTRY}?q=zimt"))
        found = {row["Schlüssel"].text(): row for row in rows}
        self.assertIn("cinnamic-acid", found)
        row = found["cinnamic-acid"]
        self.assertEqual(
            [a.get("href") for a in row["Name"].find_all("a")],
            ["/lab/registry/substances/cinnamic-acid/"])
        self.assertEqual(row["Name"].text(), "(E)-Zimtsäure")
        self.assertEqual(row["Artikelnr."].text(), "CH-0012")
        from registry.models import Substance
        for key in found:
            with self.subTest(key=key):
                substance = Substance.objects.get(key=key)
                self.assertIn("zimt", " ".join([
                    substance.key, substance.name, substance.name_de or "",
                    substance.short_name or "", substance.cas or ""
                ]).lower())
        every = Substance.objects.count()
        self.assertGreater(every, len(found))

    def test_substance_page(self) -> None:
        """Scenario: Substance page."""
        root = self.get("/lab/registry/substances/cinnamic-acid/")
        self.assertEqual(root.find("h1").text(), "(E)-Zimtsäure")
        content = root.find("main")
        self.assertEqual([h for h in hrefs(content)
                          if h.startswith("/compounds/")], [])
        self.assertFalse([a for a in content.find_all("a") if a.text()
                          in ("In der Sammlung", "In the collection")])
        held = section(root, "Gebinde")
        self.assertTrue(held.find_all("a"))
        self.assertTrue(all(
            re.fullmatch(r"/lab/inventory/items/\d+/", a.get("href"))
            for a in held.find_all("a")))

    def test_item_names_link_to_their_substances(self) -> None:
        header, rows = table(self.get("/lab/inventory/end-products/"))
        for row in rows:
            link = row[header[1]].find("a")
            with self.subTest(name=row[header[1]].text()):
                self.assertIsNotNone(link)
                if row[header[0]].text():
                    self.assertRegex(link.get("href"), SUBSTANCE_PAGE)
                else:
                    self.assertTrue(link.get("href").startswith(
                        "/lab/inventory/items/"))


def figures(root: Any) -> list[Any]:
    """The ``figure.structure`` elements of a page."""
    return root.find_all("figure", "structure")


class StructureFigureTests(RegistryCase):
    """Requirement: Registry pages (the substance page's figure, when
    the substance has a structure image)."""

    def figure(self, key: str) -> Any:
        found = figures(self.get(substance_url(key)))
        self.assertEqual(len(found), 1)
        return found[0]

    def test_the_figure_in_german(self) -> None:
        make_substance("cinnamic-acid", molfile=ETHANOL)
        image = self.figure("cinnamic-acid").find_all("img")
        self.assertEqual(len(image), 1)
        self.assertEqual(
            image[0].get("src"),
            "/lab/registry/substances/cinnamic-acid/structure.svg")
        self.assertEqual(image[0].get("alt"),
                         "Strukturformel von (E)-Zimtsäure")

    def test_the_figure_in_english(self) -> None:
        accept(language="en")
        make_substance("cinnamic-acid", molfile=ETHANOL)
        image = self.figure("cinnamic-acid").find("img")
        self.assertEqual(
            image.get("src"),
            "/lab/registry/substances/cinnamic-acid/structure.svg")
        self.assertEqual(image.get("alt"),
                         "Structure of (E)-Cinnamic acid")

    def test_the_alt_names_the_name_the_page_shows(self) -> None:
        make_substance("acetophenone", molfile=ETHANOL)
        self.assertEqual(self.figure("acetophenone").find("img").get("alt"),
                         "Strukturformel von Acetophenone")

    def test_no_figure_without_a_molfile(self) -> None:
        for key in ("cinnamic-acid", "new-compound-7"):
            with self.subTest(key=key):
                self.assertEqual(
                    figures(self.get(substance_url(key))), [])

    def test_no_figure_after_the_molfile_is_removed(self) -> None:
        make_substance("cinnamic-acid", molfile=ETHANOL)
        self.assertEqual(len(figures(self.get(
            substance_url("cinnamic-acid")))), 1)
        make_substance("cinnamic-acid", molfile="")
        self.assertEqual(
            figures(self.get(substance_url("cinnamic-acid"))), [])

    def test_the_image_the_figure_names_is_served(self) -> None:
        make_substance("cinnamic-acid", molfile=ETHANOL)
        src = self.figure("cinnamic-acid").find("img").get("src")
        self.assertEqual(self.client.get(src).status_code, 200)


class DemoStructureFigureTests(SeededCase):
    """Scenario: Structure on the page."""

    def test_the_demos_figure(self) -> None:
        found = figures(self.get(substance_url("isopentyl-acetate")))
        self.assertEqual(len(found), 1)
        images = found[0].find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(
            images[0].get("src"),
            "/lab/registry/substances/isopentyl-acetate/structure.svg")
        self.assertEqual(images[0].get("alt"),
                         "Strukturformel von Isopentylacetat")

    def test_a_substance_without_a_molfile_has_no_figure(self) -> None:
        self.assertEqual(
            figures(self.get(substance_url("new-compound-7"))), [])
