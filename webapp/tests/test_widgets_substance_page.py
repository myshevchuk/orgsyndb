"""Tests of the substance page as widgets: the compound widget, the
tables of containers, batches and tasks, of the procedures and sequences
beside the substance, and the collapsible route tree (lab-registry:
Registry pages; web-app: Widgets)."""

import re
from datetime import date
from decimal import Decimal

from . import (Element, make_batch, make_item, make_substance, make_task,
               make_vessel)
from .collection_support import accept
from .demo_support import SeededCase
from .inventory_support import has_amount, has_number
from .main_lists_support import (lists_records, key_number, unsorted_reasons)
from .registry_support import RegistryCase, substance_url
from .structure_support import ETHANOL
from .widget_support import (count_of, kv, kv_rows, title_of, widget,
                             widget_grid, widgets)

COMPOUND = ("Verbindung", "Compound")
GROUPS = "/lab/registry/groups/"
EMPTY_WIDGETS = ("Hergestellt nach", "Verwendet in", "Synthesewege",
                 "Herstellungswege")
LABELS_DE = ["Artikelnr.", "Summenformel", "Molmasse", "CAS-Nummer",
             "SMILES", "Bestandsgruppe", "Stoffklassen", "Schlüssel",
             "Name", "Name deutsch", "Kurzname"]
LABELS_EN = ["Article no.", "Formula", "Molar mass", "CAS number",
             "SMILES", "Inventory group", "Chemical classes", "Key",
             "Name", "German name", "Short name", "Note"]
# The registry's catalogue has no entry for the note; the label comes
# from whichever catalogue answers for ``Note``.
NOTE_LABELS_DE = ("Notiz", "Bemerkung")


def titles(root: Element) -> list[str | None]:
    return [title_of(w) for w in widgets(root)]


def link_of(cell: Element) -> Element:
    found = cell.find("a")
    assert found is not None, f"the cell {cell.text()!r} holds no link"
    return found


class SubstanceCase(RegistryCase):

    def show(self, key: str, signed_in: bool = False) -> Element:
        return self.get(substance_url(key), signed_in=signed_in)


class CompoundWidgetTests(SubstanceCase):

    def compound(self, key: str = "cinnamic-acid") -> Element:
        return widget(self.show(key), *COMPOUND)

    def test_the_compound_widget_has_the_key_as_its_note(self) -> None:
        found = self.compound()
        self.assertEqual(found.tag, "section")
        note = found.find(cls="widget__head").find(cls="widget__note")
        self.assertIsNotNone(note)
        self.assertEqual(note.text(), "cinnamic-acid")

    def test_the_widget_holds_the_figure_then_the_table(self) -> None:
        make_substance("cinnamic-acid", molfile=ETHANOL)
        found = self.compound()
        (figure,) = found.find_all("figure", cls="structure")
        table = found.find("table", cls="kv-table")
        self.assertIsNotNone(table)
        order = list(found.walk())
        self.assertLess(order.index(figure), order.index(table))

    def test_the_values_of_a_full_substance(self) -> None:
        shown = kv(self.compound())
        for label in LABELS_DE:
            with self.subTest(label=label):
                self.assertIn(label, shown)
        self.assertEqual(shown["Artikelnr."].text(), "CH-0012")
        self.assertEqual(shown["Summenformel"].text(), "C9H8O2")
        self.assertRegex(shown["Molmasse"].text(), r"^148,16 g/mol$")
        self.assertEqual(shown["CAS-Nummer"].text(), "140-10-3")
        self.assertEqual(shown["Stoffklassen"].text(), "Carbonsäuren")
        self.assertEqual(shown["Schlüssel"].text(), "cinnamic-acid")
        self.assertEqual(shown["Name"].text(), "(E)-Cinnamic acid")
        self.assertEqual(shown["Name deutsch"].text(), "(E)-Zimtsäure")
        self.assertEqual(shown["Kurzname"].text(), "ZS")
        self.assertIn("OC(=O)/C=C/c1ccccc1", shown["SMILES"].text())

    def test_the_note_is_a_row_of_its_own(self) -> None:
        rows = kv_rows(self.compound())
        self.assertEqual(len(rows), len(LABELS_DE) + 1, rows)
        (note,) = [(key, cell) for key, cell in rows
                   if key not in LABELS_DE]
        self.assertIn(note[0], NOTE_LABELS_DE)
        self.assertEqual(note[1].text(), "Notiz")

    def test_the_group_links_to_the_groups(self) -> None:
        cell = kv(self.compound())["Bestandsgruppe"]
        self.assertEqual(link_of(cell).get("href"), GROUPS)
        self.assertEqual(cell.text(), "Endprodukte")

    def test_the_smiles_has_its_copy_button_beside_it(self) -> None:
        cell = kv(self.compound())["SMILES"]
        code = cell.find("code", attrs={"data-smiles": True})
        self.assertEqual(code.text(), "OC(=O)/C=C/c1ccccc1")
        (button,) = cell.find_all("button",
                                  attrs={"data-copy-smiles": True})
        self.assertIs(code.parent, button.parent)

    def test_a_missing_value_shows_a_dash(self) -> None:
        shown = kv(self.compound("new-compound-7"))
        for label in ("Name deutsch", "Kurzname", "Stoffklassen",
                      "Summenformel", "Molmasse", "SMILES", "CAS-Nummer",
                      "Artikelnr."):
            with self.subTest(label=label):
                self.assertEqual(shown[label].text(), "–")
        self.assertEqual(shown["Schlüssel"].text(), "new-compound-7")
        self.assertEqual(shown["Name"].text(), "New compound 7")
        (note,) = [cell for key, cell in kv_rows(self.compound(
            "new-compound-7")) if key not in LABELS_DE]
        self.assertEqual(note.text(), "–")

    def test_without_smiles_there_is_no_code_and_no_button(self) -> None:
        found = self.compound("new-compound-7")
        self.assertFalse(found.find_all("code"))
        self.assertFalse(found.find_all("button"))

    def test_the_figure_is_in_the_widget_only(self) -> None:
        make_substance("cinnamic-acid", molfile=ETHANOL)
        root = self.show("cinnamic-acid")
        self.assertEqual(len(root.find_all("figure", cls="structure")), 1)
        (inside,) = widget(root, *COMPOUND).find_all(
            "figure", cls="structure")
        self.assertEqual(inside.find("img").get("src"),
                         "/lab/registry/substances/cinnamic-acid/"
                         "structure.svg")
        self.assertEqual(inside.find("img").get("alt"),
                         "Strukturformel von (E)-Zimtsäure")

    def test_no_metadata_list_remains(self) -> None:
        main = self.show("cinnamic-acid").find("main")
        self.assertFalse(main.find_all("dl", cls="metadata"))

    def test_the_labels_in_english(self) -> None:
        accept(language="en")
        found = self.compound()
        self.assertEqual(title_of(found), "Compound")
        shown = kv(found)
        for label in LABELS_EN:
            with self.subTest(label=label):
                self.assertIn(label, shown)
        self.assertEqual(shown["Name"].text(), "(E)-Cinnamic acid")
        self.assertEqual(shown["Note"].text(), "Notiz")
        self.assertRegex(shown["Molar mass"].text(), r"^148\.16 g/mol$")


class ContainersBatchesTasksTests(SubstanceCase):

    def widget_of(self, title: str, key: str = "cinnamic-acid",
                  ) -> Element:
        return widget(self.show(key), title)

    def test_the_three_widgets_are_sections(self) -> None:
        root = self.show("cinnamic-acid")
        for title in ("Gebinde", "Chargen", "Aufträge"):
            with self.subTest(title=title):
                self.assertEqual(widget(root, title).tag, "section")

    def test_empty_widgets_read_none_without_a_count(self) -> None:
        root = self.show("acetophenone")
        for title in ("Gebinde", "Chargen", "Aufträge"):
            with self.subTest(title=title):
                found = widget(root, title)
                self.assertIn("Keine", found.text())
                self.assertIsNone(count_of(found))
                self.assertFalse(found.find_all("a"))

    def test_empty_widgets_in_english(self) -> None:
        accept(language="en")
        root = self.show("acetophenone")
        for title in ("Containers", "Batches", "Tasks"):
            with self.subTest(title=title):
                found = widget(root, title)
                self.assertIn("None", found.text())
                self.assertIsNone(count_of(found))

    def test_the_containers_with_article_size_and_number(self) -> None:
        cinnamic = self.records["cinnamic"]
        small = make_item(self.kl, "CH-0012", size="10", unit="umol",
                          quantity=3, substance=cinnamic)
        large = make_item(self.kl, "CH-0012", size="50", unit="umol",
                          quantity=1, substance=cinnamic)
        found = self.widget_of("Gebinde")
        header, rows = widget_grid(found)
        self.assertEqual(header, ["Artikel / Gebinde", "Bestand"])
        shown = {link_of(row["Artikel / Gebinde"]).get("href"): row
                 for row in rows}
        self.assertEqual(set(shown), {f"/lab/inventory/items/{i.pk}/"
                                      for i in (small, large)})
        first = shown[f"/lab/inventory/items/{small.pk}/"]
        self.assertIn("CH-0012", first["Artikel / Gebinde"].text())
        self.assertTrue(has_number(first["Artikel / Gebinde"].text(),
                                   "10"))
        self.assertEqual(first["Bestand"].text(), "3 Gebinde")
        second = shown[f"/lab/inventory/items/{large.pk}/"]
        self.assertTrue(has_number(second["Artikel / Gebinde"].text(),
                                   "50"))
        self.assertEqual(second["Bestand"].text(), "1 Gebinde")
        self.assertNotIn("Keine", found.text())

    def test_the_count_is_the_number_of_rows(self) -> None:
        cinnamic = self.records["cinnamic"]
        make_item(self.kl, "CH-0012", size="10", quantity=3,
                  substance=cinnamic)
        make_item(self.kl, "CH-0012", size="50", quantity=4,
                  substance=cinnamic)
        self.assertEqual(count_of(self.widget_of("Gebinde")), 2)

    def test_the_containers_in_english(self) -> None:
        accept(language="en")
        make_item(self.kl, "CH-0012", size="10", quantity=3,
                  substance=self.records["cinnamic"])
        make_item(self.kl, "CH-0012", size="50", quantity=1,
                  substance=self.records["cinnamic"])
        header, rows = widget_grid(self.widget_of("Containers"))
        self.assertEqual(header, ["Article / size", "Stock"])
        self.assertEqual(sorted(row["Stock"].text() for row in rows),
                         ["1 container", "3 containers"])

    def test_the_batches_newest_first_with_their_amounts(self) -> None:
        cinnamic = self.records["cinnamic"]
        older = make_batch(self.kl, substance=cinnamic, number="B-1",
                           date=date(2026, 1, 1))
        newer = make_batch(self.kl, substance=cinnamic, number="B-2",
                           date=date(2026, 6, 1))
        undated = make_batch(self.kl, substance=cinnamic, number="B-3")
        make_batch(self.kl, substance=self.records["acetophenone"],
                   number="B-OTHER")
        make_vessel(self.kl, newer, unit="g", amount="2", flask=True)
        make_vessel(self.kl, newer, unit="mg", amount="30", location="A")
        found = self.widget_of("Chargen")
        header, rows = widget_grid(found)
        self.assertEqual(header, ["Charge", "Bestand"])
        links = [link_of(row["Charge"]) for row in rows]
        self.assertEqual(
            [a.get("href") for a in links],
            [f"/lab/inventory/batches/{b.pk}/"
             for b in (newer, older, undated)])
        self.assertEqual([a.text() for a in links],
                         [str(b) for b in (newer, older, undated)])
        amounts = rows[0]["Bestand"].text()
        self.assertTrue(has_amount(amounts, "2", "g"), amounts)
        self.assertTrue(has_amount(amounts, "30", "mg"), amounts)
        self.assertEqual(count_of(found), 3)
        self.assertNotIn("Keine", found.text())

    def test_a_batch_without_vessels_has_a_dash_for_stock(self) -> None:
        batch = make_batch(self.kl, substance=self.records["cinnamic"],
                           number="B-1")
        _header, rows = widget_grid(self.widget_of("Chargen"))
        (row,) = rows
        self.assertEqual(link_of(row["Charge"]).get("href"),
                         f"/lab/inventory/batches/{batch.pk}/")
        self.assertEqual(row["Bestand"].text(), "–")

    def test_the_batches_in_english(self) -> None:
        accept(language="en")
        make_batch(self.kl, substance=self.records["cinnamic"],
                   number="B-1")
        header, rows = widget_grid(self.widget_of("Batches"))
        self.assertEqual(header, ["Batch", "Stock"])
        self.assertEqual(len(rows), 1)

    def test_the_tasks_with_their_state(self) -> None:
        task = make_task(self.kl, self.records["cinnamic"])
        make_task(self.kl, self.records["acetophenone"])
        found = self.widget_of("Aufträge")
        header, rows = widget_grid(found)
        self.assertEqual(header, ["Auftrag", "Status"])
        (row,) = rows
        link = link_of(row["Auftrag"])
        self.assertEqual(link.get("href"), f"/lab/tasks/{task.number}/")
        self.assertEqual(link.text(), str(task.number))
        badge = row["Status"].find("span", cls="badge")
        self.assertIn(f"badge--{task.state}", badge.classes)
        self.assertTrue(badge.text())
        self.assertEqual(count_of(found), 1)
        self.assertNotIn("Keine", found.text())

    def test_the_tasks_in_english(self) -> None:
        accept(language="en")
        make_task(self.kl, self.records["cinnamic"])
        header, rows = widget_grid(self.widget_of("Tasks"))
        self.assertEqual(header, ["Task", "Status"])
        self.assertEqual(len(rows), 1)


class SortableTablesTests(SubstanceCase):
    """The tables that list records one per row sort in the browser
    (web-app: Widgets, "Widget and pane tables sort in the browser")."""

    def test_every_record_table_is_sortable_and_auxiliary(self) -> None:
        cinnamic = self.records["cinnamic"]
        make_item(self.kl, "CH-0012", size="10", quantity=3,
                  substance=cinnamic)
        batch = make_batch(self.kl, substance=cinnamic, number="B-1",
                           date=date(2026, 1, 1))
        make_vessel(self.kl, batch, unit="mg", amount="30")
        make_task(self.kl, cinnamic)
        root = self.show("cinnamic-acid")
        self.assertEqual(unsorted_reasons(root), [])
        self.assertEqual(
            len([t for t in root.find_all("table") if lists_records(t)]), 3)

    def test_the_key_value_table_is_no_sortable_table(self) -> None:
        root = self.show("cinnamic-acid")
        found = root.find_all("table", cls="kv-table")
        self.assertTrue(found)
        for one in found:
            self.assertIn("aux-table", one.classes)
            self.assertNotIn("data-sortable", one.attrs)

    def test_a_container_count_keys_on_its_number(self) -> None:
        cinnamic = self.records["cinnamic"]
        make_item(self.kl, "CH-0012", size="10", quantity=3,
                  substance=cinnamic)
        make_item(self.kl, "CH-0012", size="50", quantity=12,
                  substance=cinnamic)
        _, rows = widget_grid(widget(self.show("cinnamic-acid"), "Gebinde"))
        self.assertEqual(
            sorted((row["Bestand"].text(), row["Bestand"].get("data-sort"))
                   for row in rows),
            [("12 Gebinde", "12"), ("3 Gebinde", "3")])

    def test_a_batch_stock_keys_on_its_masses_in_mg(self) -> None:
        cinnamic = self.records["cinnamic"]
        masses = make_batch(self.kl, substance=cinnamic, number="B-1")
        make_vessel(self.kl, masses, unit="g", amount="2")
        make_vessel(self.kl, masses, unit="mg", amount="30")
        make_vessel(self.kl, masses, unit="umol", amount="7")
        moles = make_batch(self.kl, substance=cinnamic, number="B-2")
        make_vessel(self.kl, moles, unit="umol", amount="20")
        make_vessel(self.kl, moles, unit="mmol", amount="1")
        make_batch(self.kl, substance=cinnamic, number="B-3")
        _, rows = widget_grid(widget(self.show("cinnamic-acid"), "Chargen"))
        keys = {link_of(row["Charge"]).text(): row["Bestand"].get("data-sort")
                for row in rows}
        self.assertEqual(key_number(keys["B-1"]), Decimal(2030))
        self.assertEqual(key_number(keys["B-2"]), Decimal(1020))
        self.assertNotRegex(keys["B-3"] or "", r"\d")


class EmptyWidgetsTests(SubstanceCase):
    """Scenario: Empty widgets of a substance."""

    def test_the_optional_widgets_are_left_out(self) -> None:
        for key in ("acetophenone", "new-compound-7"):
            root = self.show(key)
            with self.subTest(key=key):
                self.assertIn("Verbindung", titles(root))
                for title in EMPTY_WIDGETS:
                    self.assertNotIn(title, titles(root))
                for title in ("Gebinde", "Chargen", "Aufträge"):
                    self.assertIn("Keine", widget(root, title).text())

    def test_the_optional_widgets_in_english(self) -> None:
        accept(language="en")
        root = self.show("acetophenone")
        self.assertIn("Compound", titles(root))
        for title in ("Made by", "Used in", "Sequences", "Routes"):
            self.assertNotIn(title, titles(root))


class ProcedureTablesTests(SeededCase):
    """Scenario: Procedures beside a substance."""

    def show(self, key: str) -> Element:
        return self.get(substance_url(key))

    def test_made_by_columns_and_cells(self) -> None:
        found = widget(self.show("acetylsalicylic-acid"),
                       "Hergestellt nach")
        self.assertEqual(found.tag, "section")
        header, rows = widget_grid(found)
        self.assertEqual(header,
                         ["Vorschrift", "Eintrag", "Ausbeute", "Status"])
        (row,) = rows
        link = link_of(row["Vorschrift"])
        self.assertEqual(link.get("href"), "/procedures/osdb-0002/")
        self.assertEqual(link.text(),
                         "OSDB-0002 Aspirin (Acetylsalicylsäure)")
        self.assertEqual(row["Eintrag"].text(), "–")
        self.assertEqual(row["Ausbeute"].text(), "75 %")
        badge = row["Status"].find("span", cls="badge")
        self.assertEqual(badge.text(), "Entwurf")
        self.assertIn("badge--draft", badge.classes)
        self.assertEqual(count_of(found), 1)

    def test_an_entry_of_a_general_procedure(self) -> None:
        found = widget(self.show("1-biphenyl-4-yl-ethanol"),
                       "Hergestellt nach")
        _header, rows = widget_grid(found)
        self.assertEqual(
            [link_of(row["Vorschrift"]).get("href") for row in rows],
            ["/procedures/osdb-0005/", "/procedures/osdb-0009/"])
        self.assertEqual([row["Eintrag"].text() for row in rows],
                         ["–", "Eintrag 1"])
        self.assertEqual([row["Ausbeute"].text() for row in rows],
                         ["90 %", "90 %"])
        self.assertEqual(count_of(found), 2)

    def test_the_cells_of_the_made_by_table_key_on_their_values(
            self) -> None:
        """Compound cells key on their value (web-app: Widgets)."""
        _header, rows = widget_grid(widget(
            self.show("1-biphenyl-4-yl-ethanol"), "Hergestellt nach"))
        self.assertEqual([row["Eintrag"].text() for row in rows],
                         ["–", "Eintrag 1"])
        self.assertIn(rows[0]["Eintrag"].get("data-sort"), (None, "", "–"))
        self.assertEqual(rows[1]["Eintrag"].get("data-sort"), "1")
        self.assertEqual([row["Ausbeute"].get("data-sort") for row in rows],
                         ["90", "90"])

    def test_every_record_table_of_a_demo_substance_is_sortable(
            self) -> None:
        for key in ("acetylsalicylic-acid", "salicylic-acid",
                    "1-biphenyl-4-yl-ethanol", "cinnamic-acid"):
            with self.subTest(key=key):
                root = self.show(key)
                self.assertEqual(unsorted_reasons(root), [])
                self.assertTrue([t for t in root.find_all("table")
                                 if lists_records(t)])

    def test_an_unknown_yield_is_a_dash(self) -> None:
        from collection.models import EntrySubstance
        EntrySubstance.objects.filter(
            entry__procedure__key="OSDB-0001", role="product",
            substance__key="salicylic-acid").update(yield_percent=None)
        _header, rows = widget_grid(widget(self.show("salicylic-acid"),
                                           "Hergestellt nach"))
        (row,) = rows
        self.assertEqual(row["Ausbeute"].text(), "–")

    def test_a_procedure_without_a_status_has_a_dash(self) -> None:
        from collection.models import Procedure
        Procedure.objects.filter(key="OSDB-0001").update(status="")
        _header, rows = widget_grid(widget(self.show("salicylic-acid"),
                                           "Hergestellt nach"))
        (row,) = rows
        self.assertIsNone(row["Status"].find("span", cls="badge"))
        self.assertEqual(row["Status"].text(), "–")

    def test_used_in_columns_and_cells(self) -> None:
        found = widget(self.show("salicylic-acid"), "Verwendet in")
        self.assertEqual(found.tag, "section")
        header, rows = widget_grid(found)
        self.assertEqual(header, ["Vorschrift", "Status"])
        (row,) = rows
        self.assertEqual(link_of(row["Vorschrift"]).get("href"),
                         "/procedures/osdb-0002/")
        self.assertEqual(row["Status"].find("span", cls="badge").text(),
                         "Entwurf")
        self.assertEqual(count_of(found), 1)

    def test_a_substance_made_and_used_has_no_route_widget(self) -> None:
        root = self.show("salicylic-acid")
        self.assertIn("Hergestellt nach", titles(root))
        self.assertIn("Verwendet in", titles(root))
        self.assertNotIn("Herstellungswege", titles(root))

    def test_the_sequences(self) -> None:
        found = widget(self.show("acetylsalicylic-acid"), "Synthesewege")
        self.assertEqual(found.tag, "section")
        header, rows = widget_grid(found)
        self.assertEqual(header, ["Syntheseweg"])
        (row,) = rows
        link = link_of(row["Syntheseweg"])
        self.assertEqual(link.get("href"), "/sequences/seq-0001/")
        self.assertTrue(link.text().startswith("SEQ-0001 "), link.text())
        self.assertIn("Aspirin", link.text())
        self.assertEqual(count_of(found), 1)

    def test_the_english_columns(self) -> None:
        accept(language="en")
        root = self.show("1-biphenyl-4-yl-ethanol")
        header, rows = widget_grid(widget(root, "Made by"))
        self.assertEqual(header, ["Procedure", "Entry", "Yield", "Status"])
        self.assertEqual([row["Entry"].text() for row in rows],
                         ["–", "entry 1"])
        self.assertEqual(rows[0]["Status"].find("span", cls="badge").text(),
                         "draft")
        header, _rows = widget_grid(widget(self.show("salicylic-acid"),
                                           "Used in"))
        self.assertEqual(header, ["Procedure", "Status"])
        header, _rows = widget_grid(widget(
            self.show("acetylsalicylic-acid"), "Sequences"))
        self.assertEqual(header, ["Sequence"])

    def test_a_widget_without_rows_is_left_out(self) -> None:
        from collection.models import Procedure
        Procedure.objects.filter(key="OSDB-0002").update(withdrawn=True)
        root = self.show("acetylsalicylic-acid")
        self.assertIn("Verbindung", titles(root))
        self.assertNotIn("Hergestellt nach", titles(root))
        self.assertNotIn("Herstellungswege", titles(root))


class RouteWidgetTests(SeededCase):
    """The widget ``Herstellungswege``."""

    def route(self, key: str = "acetylsalicylic-acid") -> Element:
        return widget(self.get(substance_url(key)), "Herstellungswege")

    def test_it_is_a_collapsible_widget_open_on_load(self) -> None:
        found = self.route()
        self.assertEqual(found.tag, "details")
        self.assertIn("open", found.attrs)
        self.assertTrue(found.get("id"))
        head = found.find(cls="widget__head")
        self.assertEqual(head.tag, "summary")

    def test_its_id_is_not_another_elements(self) -> None:
        root = self.get(substance_url("acetylsalicylic-acid"))
        wanted = self.route().get("id")
        self.assertTrue(wanted)
        self.assertEqual(
            len([e for e in root.walk() if e.get("id") == wanted]), 1)

    def test_it_holds_the_tree(self) -> None:
        tree = self.route().find("ul", cls="route-tree")
        self.assertIsNotNone(tree)
        (top,) = [li for li in tree.children
                  if isinstance(li, Element) and li.tag == "li"]
        self.assertIn("route-step", top.classes)
        self.assertEqual(link_of(top).get("href"), "/procedures/osdb-0002/")
        self.assertEqual(
            [link_of(li).get("href") for li in top.find_all("li")
             if "route-compound" in li.classes and li.parent.parent is top],
            [substance_url("salicylic-acid"),
             substance_url("acetic-anhydride")])
        inner = [li for li in top.find_all("li")
                 if "route-step" in li.classes]
        self.assertEqual(len(inner), 1)
        self.assertEqual(link_of(inner[0]).get("href"),
                         "/procedures/osdb-0001/")
        self.assertIn(" · 80 % · ", inner[0].text())

    def test_it_is_not_a_table(self) -> None:
        self.assertFalse(self.route().find_all("table"))

    def test_no_route_widget_without_a_tree(self) -> None:
        for key in ("salicylic-acid", "new-compound-7"):
            with self.subTest(key=key):
                root = self.get(substance_url(key))
                self.assertIn("Verbindung", titles(root))
                self.assertNotIn("Herstellungswege", titles(root))

    def test_the_title_in_english(self) -> None:
        accept(language="en")
        found = widget(self.get(substance_url("acetylsalicylic-acid")),
                       "Routes")
        self.assertEqual(found.tag, "details")
        self.assertIn("open", found.attrs)


class DemoSubstancePageTests(SeededCase):
    """Scenarios: Substance page, Structure on the page."""

    def test_the_compound_widget_of_the_demo_substance(self) -> None:
        root = self.get(substance_url("cinnamic-acid"))
        self.assertEqual(root.find("h1").text(), "(E)-Zimtsäure")
        found = widget(root, *COMPOUND)
        self.assertEqual(kv(found)["Artikelnr."].text(), "CH-0012")
        self.assertTrue(re.fullmatch(
            r"/lab/inventory/items/\d+/",
            link_of(widget_grid(widget(root, "Gebinde"))[1][0]
                    ["Artikel / Gebinde"]).get("href")))

    def test_the_figure_of_the_demo_substance(self) -> None:
        root = self.get(substance_url("isopentyl-acetate"))
        (figure,) = widget(root, *COMPOUND).find_all("figure",
                                                     cls="structure")
        (image,) = figure.find_all("img")
        self.assertEqual(
            image.get("src"),
            "/lab/registry/substances/isopentyl-acetate/structure.svg")
        self.assertEqual(image.get("alt"),
                         "Strukturformel von Isopentylacetat")

    def test_no_figure_for_a_substance_without_a_molfile(self) -> None:
        root = self.get(substance_url("new-compound-7"))
        self.assertFalse(widget(root, *COMPOUND).find_all(
            "figure", cls="structure"))
        self.assertFalse(root.find("main").find_all("figure",
                                                    cls="structure"))

    def test_the_demo_containers_are_items_of_its_article(self) -> None:
        _header, rows = widget_grid(widget(
            self.get(substance_url("cinnamic-acid")), "Gebinde"))
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(row=row["Artikel / Gebinde"].text()):
                self.assertIn("CH-0012", row["Artikel / Gebinde"].text())
                self.assertRegex(row["Bestand"].text(),
                                 r"^\d+ Gebinde$")

