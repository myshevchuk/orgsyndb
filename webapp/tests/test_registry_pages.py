"""Tests of the registry's pages (lab-registry: Registry pages)."""

import re
from typing import Any

from . import (build_index, compound, make_group, make_item, make_lot,
               make_substance, make_task, table)
from .demo_support import SeededCase
from .inventory_support import SUBSTANCE_PAGE
from .planning_support import section
from .registry_support import (REGISTRY, VOCABULARIES, RegistryCase,
                               substance_url, term_url)

COLUMNS_DE = ["Name", "Schlüssel", "Kurzname", "Gruppe", "Stoffklassen",
              "Summenformel", "Molmasse", "Artikelnr."]
COLUMNS_EN = ["Name", "Key", "Short name", "Group", "Chemical classes",
              "Formula", "Molar mass", "Article no."]


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
        self.use_index(build_index("en"))
        heading = self.get(REGISTRY).find("h1")
        self.assertEqual(heading.text(), "Substances")
        self.assertRegex(heading.parent.text(), r"Substances\D{0,5}3\b")

    def test_the_columns(self) -> None:
        header, _rows = table(self.get(REGISTRY))
        self.assertEqual(header, COLUMNS_DE)

    def test_the_english_columns(self) -> None:
        self.use_index(build_index("en"))
        header, _rows = table(self.get(REGISTRY))
        self.assertEqual(header, COLUMNS_EN)

    def test_the_cells_of_a_substance(self) -> None:
        header, rows = table(self.get(REGISTRY))
        row = next(r for r in rows if r["Schlüssel"].text()
                   == "cinnamic-acid")
        self.assertEqual(row["Name"].text(), "(E)-Zimtsäure")
        self.assertEqual(row["Kurzname"].text(), "ZS")
        self.assertIn("Endprodukte", row["Gruppe"].text())
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

    def test_links_lead_to_the_four_vocabularies(self) -> None:
        found = hrefs(self.get(REGISTRY))
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                self.assertIn(term_url(vocabulary), found)

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
        self.use_index(build_index("en"))
        root = self.get(REGISTRY, signed_in=True)
        self.assertTrue([a for a in root.find_all("a")
                         if a.text() == "New substance"])


class SearchTests(RegistryCase):

    def found(self, query: str) -> list[str]:
        header, rows = table(self.get(f"{REGISTRY}?q={query}"))
        return sorted(row["Schlüssel"].text() for row in rows)

    def test_the_search_field_is_labelled(self) -> None:
        search = self.get(REGISTRY).find("input", name="q")
        self.assertIn("Substanzen suchen", search.parent.text())

    def test_the_search_field_in_english(self) -> None:
        self.use_index(build_index("en"))
        search = self.get(REGISTRY).find("input", name="q")
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
        self.use_index(build_index("en"))
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

    def test_the_site_link_needs_the_key_in_the_index(self) -> None:
        self.use_index(build_index("de", [compound("cinnamic-acid")]))
        listed = self.get(substance_url("cinnamic-acid"))
        links = [a for a in listed.find_all("a")
                 if a.text() == "In der Sammlung"]
        self.assertEqual([a.get("href") for a in links],
                         ["/compounds/cinnamic-acid/"])
        unlisted = self.get(substance_url("acetophenone"))
        self.assertFalse([a for a in unlisted.find_all("a")
                          if a.text() == "In der Sammlung"])

    def test_the_site_link_without_an_index(self) -> None:
        root = self.get(substance_url("cinnamic-acid"))
        self.assertNotIn("/compounds/cinnamic-acid/", hrefs(root))

    def test_the_site_link_in_english(self) -> None:
        self.use_index(build_index("en", [compound("cinnamic-acid")]))
        root = self.get(substance_url("cinnamic-acid"))
        self.assertTrue([a for a in root.find_all("a")
                         if a.text() == "In the collection"])

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
    """The sections ``Gebinde``, ``Bulk-Lose`` and ``Aufträge``."""

    def sections(self, key: str) -> dict:
        root = self.get(substance_url(key))
        return {name: section(root, name)
                for name in ("Gebinde", "Bulk-Lose", "Aufträge")}

    def test_empty_sections_say_none(self) -> None:
        for name, held in self.sections("acetophenone").items():
            with self.subTest(section=name):
                self.assertIn("Keine", held.text())
                self.assertFalse(held.find_all("a"))

    def test_the_sections_in_english(self) -> None:
        self.use_index(build_index("en"))
        root = self.get(substance_url("acetophenone"))
        for name in ("Containers", "Bulk lots", "Tasks"):
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

    def test_the_open_lots_and_no_used_up_one(self) -> None:
        cinnamic = self.records["cinnamic"]
        open_lot = make_lot(self.kl, substance=cinnamic, amount="5",
                            batch="B-1")
        make_lot(self.kl, substance=cinnamic, amount="0", batch="B-USED")
        make_lot(self.kl, substance=self.records["acetophenone"],
                 amount="5", batch="B-OTHER")
        held = self.sections("cinnamic-acid")["Bulk-Lose"]
        self.assertEqual([a.get("href") for a in held.find_all("a")],
                         [f"/lab/inventory/bulk/{open_lot.pk}/"])

    def test_the_lots_of_a_substance_without_an_article(self) -> None:
        lot = make_lot(self.kl, substance=self.records["acetophenone"],
                       amount="5", batch="B-1")
        held = self.sections("acetophenone")["Bulk-Lose"]
        self.assertEqual([a.get("href") for a in held.find_all("a")],
                         [f"/lab/inventory/bulk/{lot.pk}/"])
        self.assertIn("Keine", self.sections("acetophenone")["Gebinde"]
                      .text())

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
        self.use_index(build_index("en"))
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
        self.use_index(build_index("en"))
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
        self.use_index(build_index("en"))
        root = self.get(term_url("groups"), signed_in=True)
        self.assertTrue([a for a in root.find_all("a")
                         if a.text() == "New term"])

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
        links = [a for a in root.find_all("a")
                 if a.text() == "In der Sammlung"]
        self.assertEqual([a.get("href") for a in links],
                         ["/compounds/cinnamic-acid/"])
        held = section(root, "Gebinde")
        self.assertTrue(held.find_all("a"))
        self.assertTrue(all(
            re.fullmatch(r"/lab/inventory/items/\d+/", a.get("href"))
            for a in held.find_all("a")))

    def test_not_in_the_collection(self) -> None:
        """Scenario: Not in the collection."""
        make_substance("ethyl-acetate", "Ethyl acetate", classes=["esters"],
                       name_de="Ethylacetat")
        root = self.get("/lab/registry/substances/ethyl-acetate/")
        self.assertEqual(root.find("h1").text(), "Ethylacetat")
        self.assertFalse([a for a in root.find_all("a")
                          if a.text() == "In der Sammlung"])

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
