"""Tests of stock categories, the intermediate and commercial chemical
lists by substance, their details and vessel actions in dialogs
(end-product-inventory: Stock categories, Lists by substance, Inventory
forms).
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from inventory.bookings import correct_vessel, withdraw
from inventory.models import Vessel

from . import (
    PASSWORD,
    Element,
    berlin,
    field_value,
    frozen,
    make_batch,
    make_class,
    make_group,
    make_item,
    make_substance,
    make_task,
    make_vessel,
    page,
    past,
    substance_for,
    table,
    ticking,
)
from .collection_support import accept
from .inventory_support import (
    LIST,
    NEW_BATCH,
    SUBSTANCE_PAGE,
    TODAY,
    FormCase,
    InventoryCase,
    batch_url,
    fresh,
    has_amount,
    has_number,
    snapshot,
    vessel_url,
)
from .journal_support import entry_of, make_notebook
from .main_lists_support import (LOT_TABLE, has_ancestor_class, lot_keys,
                                 lot_marked, lot_pane, lot_rows, marked,
                                 must_outer_split, pane_head, pane_widgets,
                                 path_of, query_of, replaced, split_panes,
                                 strong_columns)
from .test_inventory_detail import pane_of
from .widget_support import grid
from .test_inventory_dialogs import (
    HTMX,
    LOGIN,
    RESTORE,
    controls_of,
    current,
    errors_at,
    heading_of,
    region,
    vary_of,
)
from .test_inventory_table import body_rows

INTERMEDIATES = "/lab/inventory/intermediates/"
CHEMICALS = "/lab/inventory/chemicals/"
BULK = "/lab/inventory/end-products/bulk/"
INTERMEDIATE_COOKIE = "intermediate-list-view"
CHEMICAL_COOKIE = "chemical-list-view"
VIEWS = (None, "table", "details")
VESSEL_ACTIONS = ("Entnahme", "Umfüllen", "Korrigieren", "Bearbeiten")
DETAIL_COLS_INT_DE = [
    "Gefäß", "Charge", "Menge", "Ort", "Herkunft", "Datum"]
DETAIL_COLS_INT_EN = [
    "Vessel", "Batch", "Amount", "Location", "Source", "Date"]
DETAIL_COLS_CHEM_DE = [
    "Gefäß", "Charge", "Menge", "Ort", "Herkunft", "Datum",
    "Angebrochen am"]
DETAIL_COLS_CHEM_EN = [
    "Vessel", "Batch", "Amount", "Location", "Source", "Date",
    "Opened on"]


def detail_url(base: str, key: str, query: str = "") -> str:
    return f"{base}{key}/{query}"


def opened(vessel: Vessel, day: date | None) -> Vessel:
    """Set ``opened_on`` on a bought vessel for fixture setup."""
    Vessel.objects.filter(pk=vessel.pk).update(opened_on=day)
    return fresh(vessel)


def row_map(root: Element) -> dict[str, dict[str, Element]]:
    """Rows of the list table keyed by substance key (``data-item``)."""
    header, rows = table(root)
    mapped: dict[str, dict[str, Element]] = {}
    for row in rows:
        tr = row[header[0]].closest("tr")
        key = tr.get("data-item") or ""
        mapped[key] = row
    return mapped


def detail_table(pane: Element) -> tuple[list[str], list[dict[str, Element]]]:
    """The lot table inside ``#item-detail``, a table of vessels."""
    found = pane.find("table", id=LOT_TABLE)
    assert found is not None, "the pane has no lot table"
    return grid(found)


def lot_ids(root: Element) -> list[str]:
    """The vessel ids of the lot table's rows, in order."""
    return lot_keys(root)


def outer_marked(root: Element) -> list[str]:
    """The ``data-item`` of the marked rows of the list's own table,
    leaving out the lot table's."""
    return marked(root)


class StockCategoryTests(InventoryCase):

    def test_categories_of_vessels(self) -> None:
        """Scenario: Categories of vessels."""
        self.item("CH-0012")
        made_end = make_batch(self.kl, "CH-0012", number="END-1")
        end_stored = make_vessel(
            self.kl, made_end, unit="g", amount="2", location="Regal 1")
        end_flask_batch = make_batch(self.kl, "CH-0012", number="END-2")
        end_flask = make_vessel(
            self.kl, end_flask_batch, unit="g", amount="1", flask=True)

        acetophenone = make_substance("acetophenone", "Acetophenone")
        int_flask_batch = make_batch(
            self.kl, substance=acetophenone, number="INT-1")
        make_vessel(
            self.kl, int_flask_batch, unit="g", amount="3", flask=True)
        int_stored_batch = make_batch(
            self.kl, substance=acetophenone, number="INT-2")
        make_vessel(
            self.kl, int_stored_batch, unit="g", amount="4",
            location="Regal 2")
        bought_batch = make_batch(
            self.kl, substance=acetophenone, source="bought",
            supplier="Sigma", supplier_batch="SUP-1")
        make_vessel(
            self.kl, bought_batch, unit="g", amount="5", location="Regal 3")

        bulk_text = page(self.client.get(BULK)).text()
        self.assertIn(f"#{end_stored.pk}", bulk_text)
        self.assertIn(f"#{end_flask.pk}", bulk_text)
        self.assertNotIn("Acetophenone", bulk_text)

        int_rows = row_map(page(self.client.get(INTERMEDIATES)))
        self.assertEqual(set(int_rows), {"acetophenone"})
        self.assertTrue(
            has_amount(int_rows["acetophenone"]["Menge"].text(), "7", "g"))
        self.assertIn("1 Kolben", int_rows["acetophenone"]["Gefäße"].text())

        chem_rows = row_map(page(self.client.get(CHEMICALS)))
        self.assertEqual(set(chem_rows), {"acetophenone"})
        self.assertTrue(
            has_amount(chem_rows["acetophenone"]["Menge"].text(), "5", "g"))

    def test_giving_a_substance_an_article_moves_vessels_to_end_products(
            self) -> None:
        """Requirement: Stock categories ("A substance can have vessels in
        more than one category; giving it an article moves all its vessels
        to `Endprodukte`.")."""
        sub = make_substance("acetophenone", "Acetophenone")
        v1 = make_vessel(self.kl, substance=sub, unit="g", amount="2",
                         flask=True)
        v2 = make_vessel(self.kl, substance=sub, unit="g", amount="3",
                         source="bought", supplier="Sigma")
        self.assertIn("acetophenone", row_map(
            page(self.client.get(INTERMEDIATES))))
        self.assertIn("acetophenone", row_map(
            page(self.client.get(CHEMICALS))))

        make_item(self.kl, article="CH-0099", substance=sub)
        self.assertEqual(
            row_map(page(self.client.get(INTERMEDIATES))), {})
        self.assertEqual(row_map(page(self.client.get(CHEMICALS))), {})
        bulk_text = page(self.client.get(BULK)).text()
        self.assertIn(f"#{v1.pk}", bulk_text)
        self.assertIn(f"#{v2.pk}", bulk_text)

    def test_used_up_vessels_are_not_listed(self) -> None:
        sub = make_substance("acetophenone", "Acetophenone")
        make_vessel(self.kl, substance=sub, unit="mg", amount="0")
        make_vessel(self.kl, substance=sub, unit="mg", amount="0",
                    source="bought", supplier="Sigma")
        self.assertEqual(
            row_map(page(self.client.get(INTERMEDIATES))), {})
        self.assertEqual(row_map(page(self.client.get(CHEMICALS))), {})


class IntermediateListTests(InventoryCase):

    def listing(self, query: str = "", view: str | None = None) -> Element:
        if view is None:
            self.client.cookies.pop(INTERMEDIATE_COOKIE, None)
        else:
            self.client.cookies[INTERMEDIATE_COOKIE] = view
        response = self.client.get(INTERMEDIATES + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_intermediates_by_substance(self) -> None:
        """Scenario: Intermediates by substance."""
        sub = make_substance("acetophenone", "Acetophenone")
        t21 = make_task(self.kl, sub, steps=1, started=past(1),
                        number="T-021")
        t8 = make_task(self.kl, sub, steps=1, started=past(1),
                       number="T-008")
        b21 = make_batch(self.kl, substance=sub, number="B-21",
                         task_step=t21.steps.get())
        b8 = make_batch(self.kl, substance=sub, number="B-8",
                        task_step=t8.steps.get())
        make_vessel(self.kl, b21, unit="g", amount="1", flask=True)
        make_vessel(self.kl, b21, unit="g", amount="1.5",
                    location="Chemikalienschrank 3")
        make_vessel(self.kl, b8, unit="g", amount="12",
                    location="Chemikalienschrank 3")
        make_vessel(self.kl, substance=sub, unit="g", amount="5",
                    source="bought", supplier="Sigma")

        rows = row_map(self.listing())
        self.assertEqual(list(rows), ["acetophenone"])
        row = rows["acetophenone"]
        self.assertIn("+gekauft", row["Substanz"].text())
        self.assertTrue(has_amount(row["Menge"].text(), "14,5", "g"),
                        row["Menge"].text())
        vessels_text = row["Gefäße"].text()
        self.assertTrue(has_number(vessels_text, "3"), vessels_text)
        self.assertIn("1 Kolben", vessels_text)
        loc_text = row["Ort"].text()
        self.assertIn("Chemikalienschrank 3", loc_text)
        self.assertIn("im Kolben", loc_text)
        source_text = row["Herkunft"].text()
        self.assertIn("T-008", source_text)
        self.assertIn("T-021", source_text)
        self.assertLess(source_text.index("T-008"),
                        source_text.index("T-021"))

    def test_the_substance_and_the_amount_are_strong(self) -> None:
        sub = make_substance("acetophenone", "Acetophenone")
        make_vessel(self.kl, substance=sub, unit="g", amount="5")
        root = self.listing()
        self.assertEqual(strong_columns(root),
                         (["Substanz", "Menge"], ["Substanz", "Menge"]))
        cell = row_map(root)["acetophenone"]["Substanz"]
        self.assertIn("Acetophenone", " ".join(
            (cell.get("title") or "").split()))

    def test_heading_counts_and_substance_order(self) -> None:
        """Requirement: Lists by substance ("under the headings
        `Zwischenprodukte` (`Intermediates`) ..., each followed by the number
        of substances and of vessels listed, and ordered by the substance's
        name regardless of case.")."""
        beta = make_substance("beta", "beta-Ketone")
        alpha = make_substance("alpha", "Alpha-Ketone")
        gamma = make_substance("gamma", "Gamma-Ketone", name_de="Ceta-Keton")
        make_vessel(self.kl, substance=beta, unit="mg", amount="10")
        make_vessel(self.kl, substance=beta, unit="mg", amount="20")
        make_vessel(self.kl, substance=alpha, unit="mg", amount="30")
        make_vessel(self.kl, substance=gamma, unit="mg", amount="40")

        root = self.listing()
        heading = root.find(cls="lab-heading")
        self.assertEqual(heading.find("h1").text(), "Zwischenprodukte")
        self.assertRegex(heading.text(), r"\b3\s+Substanzen\b")
        self.assertRegex(heading.text(), r"\b4\s+Gefäße\b")
        self.assertEqual(list(row_map(root)), ["alpha", "beta", "gamma"])

        filtered = self.listing("?q=beta")
        fhead = filtered.find(cls="lab-heading")
        self.assertRegex(fhead.text(), r"\b1\s+Substanz\b")
        self.assertRegex(fhead.text(), r"\b2\s+Gefäße\b")

        accept(language="en")
        en_root = self.listing()
        en_head = en_root.find(cls="lab-heading")
        self.assertEqual(en_head.find("h1").text(), "Intermediates")
        self.assertRegex(en_head.text(), r"\b3\s+substances\b")
        self.assertRegex(en_head.text(), r"\b4\s+vessels\b")
        self.assertEqual(list(row_map(en_root)), ["alpha", "beta", "gamma"])

    def test_heading_new_batch_link_for_signed_in_user_only(self) -> None:
        """Requirement: Lists by substance ("A signed-in user sees a link
        `Neue Charge` (`New batch`) to `/lab/inventory/batches/new/` on the
        intermediate list")."""
        make_vessel(self.kl, substance=make_substance("s1", "S1"))
        self.assertIsNone(self.listing().find("a", href=NEW_BATCH))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["Neue Charge"])
        accept(language="en")
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["New batch"])

    def test_substance_cell_classes_and_bought_mark(self) -> None:
        """Requirement: Lists by substance ("linking to its page, followed on
        the intermediate list by its chemical classes, by label, ... and the
        mark `+gekauft` (`+bought`) on the intermediate list ... when the
        substance has an open vessel of the other of the two categories,
        whatever the filters")."""
        ketones = make_class("ketones", "Ketones", label_de="Ketone")
        acids = make_class("acids", "Acids", label_de="Carbonsäuren")
        sub = make_substance("sub-1", "Sub 1", classes=[ketones, acids])
        make_vessel(self.kl, substance=sub, flask=True)
        bought = make_vessel(self.kl, substance=sub, source="bought",
                             amount="10")

        row = row_map(self.listing("?flask=1"))["sub-1"]
        cell = row["Substanz"]
        self.assertEqual([a.get("href") for a in cell.find_all("a")],
                         ["/lab/registry/substances/sub-1/"])
        text = cell.text()
        self.assertIn("Carbonsäuren", text)
        self.assertIn("Ketone", text)
        self.assertLess(text.index("Carbonsäuren"), text.index("Ketone"))
        self.assertIn("+gekauft", text)

        accept(language="en")
        en_text = row_map(self.listing("?flask=1"))["sub-1"]["Substance"].text()
        self.assertIn("Acids", en_text)
        self.assertIn("Ketones", en_text)
        self.assertLess(en_text.index("Acids"), en_text.index("Ketones"))
        self.assertIn("+bought", en_text)

        Vessel.objects.filter(pk=bought.pk).update(amount=0)
        accept(language="de")
        self.assertNotIn(
            "+gekauft", row_map(self.listing())["sub-1"]["Substanz"].text())

    def test_amount_cell_units_order(self) -> None:
        """Requirement: Lists by substance ("`Menge` (`Amount`): the amount
        in its vessels summed per unit, the units in the order `mg`, `g`,
        `µmol`, `mmol`")."""
        sub = make_substance("multi-unit", "Multi unit")
        make_vessel(self.kl, substance=sub, unit="mmol", amount="2")
        make_vessel(self.kl, substance=sub, unit="g", amount="1.5")
        make_vessel(self.kl, substance=sub, unit="mg", amount="7.4085")
        make_vessel(self.kl, substance=sub, unit="umol", amount="10")
        make_vessel(self.kl, substance=sub, unit="g", amount="0.5")

        text = row_map(self.listing())["multi-unit"]["Menge"].text()
        for num_str, unit in (("7,409", "mg"), ("2", "g"),
                              ("10", "µmol"), ("2", "mmol")):
            self.assertTrue(has_amount(text, num_str, unit), text)
        places = [text.index(u) for u in ("mg", "g", "µmol", "mmol")]
        self.assertEqual(places, sorted(places), text)

    def test_vessels_cell_flask_count(self) -> None:
        """Requirement: Lists by substance ("`Gefäße` (`Vessels`): their
        number, followed on the intermediate list by `<n> Kolben` (`<n> in
        flask`) when flasks are among them")."""
        both = make_substance("both", "Both")
        make_vessel(self.kl, substance=both, flask=True)
        make_vessel(self.kl, substance=both, location="Regal")
        stored_only = make_substance("stored-only", "Stored only")
        make_vessel(self.kl, substance=stored_only, location="Regal")

        rows = row_map(self.listing())
        self.assertIn("2", rows["both"]["Gefäße"].text())
        self.assertIn("1 Kolben", rows["both"]["Gefäße"].text())
        self.assertEqual(rows["stored-only"]["Gefäße"].text(), "1")

        accept(language="en")
        en_rows = row_map(self.listing())
        self.assertIn("1 in flask", en_rows["both"]["Vessels"].text())

    def test_locations_cell_order_not_recorded_and_flask(self) -> None:
        """Requirement: Lists by substance (`Ort`: natural order, `+<n>`,
        `nicht hinterlegt` last, `im Kolben` alone when all are flasks, a
        flask's own location is not shown)."""
        shared = make_substance("a-shared", "A Shared")
        make_vessel(self.kl, substance=shared, location="Regal 2")
        make_vessel(self.kl, substance=shared, location="Regal 2")

        multi = make_substance("b-multi", "B Multi")
        make_vessel(self.kl, substance=multi, location="Regal 10")
        make_vessel(self.kl, substance=multi, location="Regal 2")
        make_vessel(self.kl, substance=multi, location="")

        none_loc = make_substance("c-none", "C None")
        make_vessel(self.kl, substance=none_loc, location="")

        flask_loc = make_substance("d-flask", "D Flask")
        make_vessel(self.kl, substance=flask_loc, flask=True,
                    location="Geheim")

        rows = row_map(self.listing())
        self.assertEqual(rows["a-shared"]["Ort"].text(), "Regal 2")
        self.assertEqual(rows["b-multi"]["Ort"].text(), "Regal 2 +2")
        self.assertEqual(rows["c-none"]["Ort"].text(), "nicht hinterlegt")
        self.assertEqual(rows["d-flask"]["Ort"].text(), "im Kolben")
        self.assertNotIn("Geheim", rows["d-flask"]["Ort"].text())

        accept(language="en")
        en_rows = row_map(self.listing())
        self.assertEqual(en_rows["c-none"]["Location"].text(),
                         "not recorded")
        self.assertEqual(en_rows["d-flask"]["Location"].text(), "in flask")

    def test_source_cell_task_value_order_and_no_task(self) -> None:
        """Requirement: Lists by substance ("`Herkunft` (`Source`): the
        numbers of the tasks whose steps made the batches, linking to the
        tasks' pages, in the order of the tasks' numbers by value, at most two
        followed by `+<n>`, then `ohne Auftrag` (`no task`) when a batch was
        made by no step, alone when none was")."""
        sub_many = make_substance("a-many", "A Many")
        t1000 = make_task(self.kl, sub_many, steps=1, started=past(1),
                          number="T-1000")
        t21 = make_task(self.kl, sub_many, steps=1, started=past(1),
                        number="T-021")
        t8 = make_task(self.kl, sub_many, steps=1, started=past(1),
                       number="T-008")
        for task in (t1000, t21, t8):
            make_vessel(self.kl, substance=sub_many,
                        task_step=task.steps.get())
        make_vessel(self.kl, substance=sub_many)

        sub_none = make_substance("b-none", "B None")
        make_vessel(self.kl, substance=sub_none)

        rows = row_map(self.listing())
        cell = rows["a-many"]["Herkunft"]
        links = cell.find_all("a")
        self.assertEqual([(a.text(), a.get("href")) for a in links], [
            ("T-008", "/lab/tasks/T-008/"),
            ("T-021", "/lab/tasks/T-021/"),
        ])
        self.assertNotIn("T-1000", cell.text())
        self.assertIn("+1", cell.text())
        self.assertIn("ohne Auftrag", cell.text())
        self.assertEqual(rows["b-none"]["Herkunft"].text(), "ohne Auftrag")

        accept(language="en")
        en_rows = row_map(self.listing())
        self.assertIn("no task", en_rows["a-many"]["Source"].text())
        self.assertEqual(en_rows["b-none"]["Source"].text(), "no task")

    def test_ages(self) -> None:
        """Scenario: Ages."""
        s1 = make_substance("a-young", "A Young")
        make_vessel(self.kl, substance=s1, date=date(2026, 11, 20))
        make_vessel(self.kl, substance=s1, date=date(2026, 4, 6))
        s2 = make_substance("b-older", "B Older")
        make_vessel(self.kl, substance=s2, date=date(2025, 5, 1))
        s3 = make_substance("c-year", "C Year")
        make_vessel(self.kl, substance=s3, date=date(2025, 11, 24))

        with frozen(berlin(2026, 11, 24, 9)):
            rows = row_map(self.listing())
            self.assertEqual(rows["a-young"]["Alter"].text(),
                             "4 Tage – 7 Mon.")
            self.assertIsNone(rows["a-young"]["Alter"].find("span", "age-old"))

            for key, label in (("b-older", "1 J 6 Mon."), ("c-year", "1 J")):
                span = rows[key]["Alter"].find("span", "age-old")
                self.assertIsNotNone(span, key)
                self.assertEqual(span.text(), label)

            old_rows = row_map(self.listing("?old=1"))
            self.assertEqual(list(old_rows), ["b-older", "c-year"])

    def test_month_ends(self) -> None:
        """Scenario: Month ends."""
        sub = make_substance("month-end", "Month end")
        make_vessel(self.kl, substance=sub, date=date(2026, 1, 31))

        with frozen(berlin(2026, 2, 28, 9)):
            self.assertEqual(
                row_map(self.listing())["month-end"]["Alter"].text(),
                "1 Mon.")
        with frozen(berlin(2026, 2, 27, 9)):
            self.assertEqual(
                row_map(self.listing())["month-end"]["Alter"].text(),
                "27 Tage")

    def test_age_cell_same_label_and_undated(self) -> None:
        """Requirement: Lists by substance ("joined by ` – `, or one when the
        two read alike, `–` when no batch has a date")."""
        alike = make_substance("a-alike", "A Alike")
        make_vessel(self.kl, substance=alike, date=date(2026, 10, 1))
        make_vessel(self.kl, substance=alike, date=date(2026, 10, 2))
        undated = make_substance("b-undated", "B Undated")
        make_vessel(self.kl, substance=undated)

        with frozen(berlin(2026, 11, 24, 9)):
            rows = row_map(self.listing())
            self.assertEqual(rows["a-alike"]["Alter"].text(), "1 Mon.")
            self.assertEqual(rows["b-undated"]["Alter"].text(), "–")

    def test_filters_and_kept_values_on_intermediate_list(self) -> None:
        """Requirement: Lists by substance (`q` incl. task number, `location`
        never admitting flasks, `flask=1`, `old=1`, values kept)."""
        sub = make_substance(
            "acetophenone", "Acetophenone", name_de="Acetophenon",
            short_name="AP", cas="98-86-2")
        t8 = make_task(self.kl, sub, steps=1, started=past(1), number="T-008")
        t21 = make_task(self.kl, sub, steps=1, started=past(1), number="T-021")
        make_vessel(
            self.kl, substance=sub, number="KL0412", unit="g", amount="2",
            task_step=t8.steps.get(), location="Regal 1",
            date=date(2025, 1, 1))
        make_vessel(
            self.kl, substance=sub, number="KL0413", unit="g", amount="3",
            task_step=t21.steps.get(), flask=True, location="Regal 1",
            date=date(2026, 10, 1))

        for q, want in (
                ("acetophenone", "5"),
                ("acetophenon", "5"),
                ("AP", "5"),
                ("98-86", "5"),
                ("kl0412", "2"),
                ("t-008", "2"),
        ):
            with self.subTest(q=q):
                rows = row_map(self.listing(f"?q={quote(q)}"))
                self.assertEqual(list(rows), ["acetophenone"])
                self.assertTrue(
                    has_amount(rows["acetophenone"]["Menge"].text(), want,
                               "g"))

        loc_rows = row_map(self.listing(f"?location={quote('Regal 1')}"))
        self.assertTrue(
            has_amount(loc_rows["acetophenone"]["Menge"].text(), "2", "g"))
        self.assertNotIn("Kolben", loc_rows["acetophenone"]["Gefäße"].text())

        flask_rows = row_map(self.listing("?flask=1"))
        self.assertTrue(
            has_amount(flask_rows["acetophenone"]["Menge"].text(), "3", "g"))

        kept = self.listing(
            f"?q=t-008&location={quote('Regal 1')}&flask=1&old=1")
        self.assertEqual(field_value(kept, "q"), "t-008")
        self.assertEqual(field_value(kept, "location"), "Regal 1")
        self.assertEqual(field_value(kept, "flask"), "on")
        self.assertEqual(field_value(kept, "old"), "on")

    def test_classes_below_a_class(self) -> None:
        """Scenario: Classes below a class."""
        ketones = make_class("ketones", "Ketones", label_de="Ketone")
        aryl = make_class("aryl-ketones", "Aryl ketones", parent=ketones,
                          label_de="Arylketone")
        sub = make_substance("acetophenone", "Acetophenone", classes=[aryl])
        make_vessel(self.kl, substance=sub)

        self.assertEqual(
            list(row_map(self.listing("?class=ketones"))), ["acetophenone"])
        self.assertEqual(
            list(row_map(self.listing("?class=nothing"))), [])

    def test_class_hierarchy_depth_and_offered_terms_order(self) -> None:
        """Requirement: Lists by substance ("substances filed under the
        chemical class of that key or under a class filed below it, at any
        depth" and "each term of the chemical classes ... in the order of the
        vocabulary's page")."""
        top = make_class("carbonyl-compounds", "Carbonyl compounds",
                         label_de="Carbonylverbindungen")
        acids = make_class("carboxylic-acids", "Carboxylic acids", parent=top,
                           label_de="Carbonsäuren")
        ketones = make_class("ketones", "Ketones", parent=top,
                             label_de="Ketone")
        aryl = make_class("aryl-ketones", "Aryl ketones", parent=ketones,
                          label_de="Arylketone")
        sub = make_substance("acetophenone", "Acetophenone", classes=[aryl])
        make_vessel(self.kl, substance=sub)

        self.assertEqual(
            list(row_map(self.listing("?class=carbonyl-compounds"))),
            ["acetophenone"])
        self.assertEqual(
            list(row_map(self.listing("?class=carboxylic-acids"))), [])

        root = self.listing("?class=ketones")
        self.assertEqual(field_value(root, "class"), "ketones")
        values = [o.get("value") for o in
                  root.find("select", name="class").find_all("option")
                  if o.get("value")]
        self.assertEqual(values, [
            "carbonyl-compounds", "carboxylic-acids", "ketones",
            "aryl-ketones"])
        self.assertEqual(acids.key, "carboxylic-acids")

    def test_offered_locations_and_value_in_force(self) -> None:
        """Requirement: Lists by substance ("The page offers each location of
        the category's open stored vessels ...; the value in force is offered
        even when no vessel has it any more.")."""
        sub = make_substance("sub", "Sub")
        make_vessel(self.kl, substance=sub, location="Schrank A")
        make_vessel(self.kl, substance=sub, location="Verbraucht", amount="0")
        make_vessel(self.kl, substance=sub, flask=True, location="Kolbenort")
        make_vessel(self.kl, substance=sub, source="bought",
                    location="Kaufregal")
        self.item("CH-0012")
        make_vessel(self.kl, article="CH-0012", location="Endlager")

        root = self.listing("?location=Verschwunden")
        offered = [o.get("value") for o in
                   root.find("select", name="location").find_all("option")
                   if o.get("value")]
        self.assertEqual(offered, ["Schrank A", "Verschwunden"])
        self.assertEqual(field_value(root, "location"), "Verschwunden")


class CommercialListTests(InventoryCase):

    def listing(self, query: str = "", view: str | None = None) -> Element:
        if view is None:
            self.client.cookies.pop(CHEMICAL_COOKIE, None)
        else:
            self.client.cookies[CHEMICAL_COOKIE] = view
        response = self.client.get(CHEMICALS + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_commercial_chemicals_by_substance(self) -> None:
        """Scenario: Commercial chemicals by substance."""
        sub = make_substance("benzaldehyde", "Benzaldehyde")
        b1 = make_batch(self.kl, substance=sub, source="bought",
                        supplier="Sigma-Aldrich", supplier_batch="S-1")
        v1 = make_vessel(self.kl, b1, unit="g", amount="41",
                         location="Kühlschrank 1")
        opened(v1, date(2026, 3, 5))
        b2 = make_batch(self.kl, substance=sub, source="bought",
                        supplier="TCI", supplier_batch="T-1")
        make_vessel(self.kl, b2, unit="g", amount="100",
                    location="Kühlschrank 2")

        rows = row_map(self.listing())
        self.assertEqual(list(rows), ["benzaldehyde"])
        row = rows["benzaldehyde"]
        self.assertTrue(has_amount(row["Menge"].text(), "141", "g"),
                        row["Menge"].text())
        vessels_text = row["Gefäße"].text()
        self.assertTrue(has_number(vessels_text, "2"), vessels_text)
        self.assertIn("(1 versiegelt)", vessels_text)
        self.assertEqual(row["Ort"].text(), "Kühlschrank 1 +1")
        self.assertEqual(row["Lieferanten"].text(), "Sigma-Aldrich +1")
        self.assertEqual(row["Angebrochen"].text(), "05.03.2026")

    def test_the_substance_and_the_amount_are_strong(self) -> None:
        sub = make_substance("benzaldehyde", "Benzaldehyde")
        make_vessel(self.kl, substance=sub, unit="g", amount="5",
                    source="bought", supplier="Sigma-Aldrich")
        root = self.listing()
        self.assertEqual(strong_columns(root),
                         (["Substanz", "Menge"], ["Substanz", "Menge"]))
        cell = row_map(root)["benzaldehyde"]["Substanz"]
        self.assertIn("Benzaldehyd", " ".join(
            (cell.get("title") or "").split()))

    def test_filters_narrow_the_sums(self) -> None:
        """Scenario: Filters narrow the sums."""
        sub = make_substance("benzaldehyde", "Benzaldehyde")
        b1 = make_batch(self.kl, substance=sub, source="bought",
                        supplier="Sigma-Aldrich", supplier_batch="S-1")
        v1 = make_vessel(self.kl, b1, unit="g", amount="41",
                         location="Kühlschrank 1")
        opened(v1, date(2026, 3, 5))
        b2 = make_batch(self.kl, substance=sub, source="bought",
                        supplier="TCI", supplier_batch="T-1")
        v2 = make_vessel(self.kl, b2, unit="g", amount="100",
                         location="Kühlschrank 2")

        for query in ("?supplier=TCI", "?sealed=1"):
            with self.subTest(query=query):
                root = self.listing(query, view="details")
                rows = row_map(root)
                self.assertEqual(list(rows), ["benzaldehyde"])
                row = rows["benzaldehyde"]
                self.assertTrue(has_amount(row["Menge"].text(), "100", "g"))
                self.assertEqual(row["Gefäße"].text(), "1 (1 versiegelt)")
                self.assertEqual(row["Ort"].text(), "Kühlschrank 2")
                self.assertEqual(row["Lieferanten"].text(), "TCI")
                self.assertEqual(row["Angebrochen"].text(), "versiegelt")

                _, detail_rows = detail_table(pane_of(root))
                self.assertEqual(
                    [r["Gefäß"].text() for r in detail_rows], [f"#{v2.pk}"])

    def test_locations_not_recorded(self) -> None:
        """Scenario: Locations not recorded."""
        sub_bought = make_substance("sub-bought", "Sub Bought")
        make_vessel(self.kl, substance=sub_bought, source="bought",
                    location="Regal 10", supplier_batch="B-1")
        v_missing = make_vessel(
            self.kl, substance=sub_bought, source="bought", location="",
            supplier_batch="B-2")

        sub_flask = make_substance("sub-flask", "Sub Flask")
        make_vessel(self.kl, substance=sub_flask, flask=True)

        chem_root = self.listing(view="details")
        chem_rows = row_map(chem_root)
        self.assertEqual(chem_rows["sub-bought"]["Ort"].text(), "Regal 10 +1")
        _, d_rows = detail_table(pane_of(chem_root))
        by_id = {r["Gefäß"].text(): r for r in d_rows}
        self.assertEqual(
            by_id[f"#{v_missing.pk}"]["Ort"].text(), "nicht hinterlegt")

        int_rows = row_map(page(self.client.get(INTERMEDIATES)))
        self.assertEqual(int_rows["sub-flask"]["Ort"].text(), "im Kolben")

    def test_heading_counts_and_substance_order(self) -> None:
        """Requirement: Lists by substance ("`Handelschemikalien`
        (`Commercial chemicals`), each followed by the number of substances
        and of vessels listed, and ordered by the substance's name regardless
        of case.")."""
        b = make_substance("b", "beta")
        a = make_substance("a", "Alpha")
        make_vessel(self.kl, substance=b, source="bought")
        make_vessel(self.kl, substance=b, source="bought")
        make_vessel(self.kl, substance=a, source="bought")

        root = self.listing()
        heading = root.find(cls="lab-heading")
        self.assertEqual(heading.find("h1").text(), "Handelschemikalien")
        self.assertRegex(heading.text(), r"\b2\s+Substanzen\b")
        self.assertRegex(heading.text(), r"\b3\s+Gefäße\b")
        self.assertEqual(list(row_map(root)), ["a", "b"])

        accept(language="en")
        en_root = self.listing()
        en_head = en_root.find(cls="lab-heading")
        self.assertEqual(en_head.find("h1").text(), "Commercial chemicals")
        self.assertRegex(en_head.text(), r"\b2\s+substances\b")
        self.assertRegex(en_head.text(), r"\b3\s+vessels\b")

    def test_heading_goods_receipt_link_for_signed_in_user_only(self) -> None:
        """Requirement: Lists by substance ("`Wareneingang` (`Goods receipt`)
        to `/lab/inventory/batches/new/?source=bought` on the commercial
        chemical list")."""
        make_vessel(self.kl, substance=make_substance("s1", "S1"),
                    source="bought")
        href = f"{NEW_BATCH}?source=bought"
        self.assertIsNone(self.listing().find("a", href=href))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=href)
        self.assertEqual([a.text() for a in links], ["Wareneingang"])
        accept(language="en")
        links = self.listing().find_all("a", href=href)
        self.assertEqual([a.text() for a in links], ["Goods receipt"])

    def test_substance_cell_short_name_cas_and_made_mark(self) -> None:
        """Requirement: Lists by substance ("followed on the commercial
        chemical list by its short name and CAS number where it has them;
        and the mark ... `+hergestellt` (`+made`) on the commercial chemical
        list, when the substance has an open vessel of the other of the two
        categories, whatever the filters")."""
        sub = make_substance(
            "benzaldehyde", "Benzaldehyde", short_name="BZA", cas="100-52-7")
        make_vessel(self.kl, substance=sub, source="bought")
        made = make_vessel(self.kl, substance=sub, source="made", amount="5")

        row = row_map(self.listing("?sealed=1"))["benzaldehyde"]
        cell = row["Substanz"]
        self.assertEqual([a.get("href") for a in cell.find_all("a")],
                         ["/lab/registry/substances/benzaldehyde/"])
        text = cell.text()
        self.assertIn("BZA", text)
        self.assertIn("100-52-7", text)
        self.assertIn("+hergestellt", text)

        accept(language="en")
        self.assertIn(
            "+made",
            row_map(self.listing("?sealed=1"))["benzaldehyde"]["Substance"]
            .text())

        Vessel.objects.filter(pk=made.pk).update(amount=0)
        accept(language="de")
        self.assertNotIn(
            "+hergestellt",
            row_map(self.listing())["benzaldehyde"]["Substanz"].text())

    def test_vessels_group_suppliers_and_opened_cells(self) -> None:
        """Requirement: Lists by substance (`Gruppe`, `Gefäße` sealed count,
        `Lieferanten` with `unbekannt` and `+<n>`, `Angebrochen` earliest or
        `versiegelt`)."""
        reagents = make_group("reagents", "Reagents", label_de="Reagenzien")
        s1 = make_substance("a-mixed", "A Mixed", group=reagents)
        v_late = make_vessel(self.kl, substance=s1, source="bought",
                             supplier="TCI")
        opened(v_late, date(2026, 5, 10))
        v_early = make_vessel(self.kl, substance=s1, source="bought",
                              supplier="Alfa")
        opened(v_early, date(2026, 2, 1))
        make_vessel(self.kl, substance=s1, source="bought", supplier="")

        s2 = make_substance("b-sealed", "B Sealed", group=reagents)
        make_vessel(self.kl, substance=s2, source="bought", supplier="")

        rows = row_map(self.listing())
        r1 = rows["a-mixed"]
        self.assertEqual(r1["Gruppe"].text(), "Reagenzien")
        self.assertEqual(r1["Gefäße"].text(), "3 (1 versiegelt)")
        self.assertEqual(r1["Lieferanten"].text(), "Alfa +2")
        self.assertEqual(r1["Angebrochen"].text(), "01.02.2026")

        r2 = rows["b-sealed"]
        self.assertEqual(r2["Gefäße"].text(), "1 (1 versiegelt)")
        self.assertEqual(r2["Lieferanten"].text(), "unbekannt")
        self.assertEqual(r2["Angebrochen"].text(), "versiegelt")

        accept(language="en")
        en_rows = row_map(self.listing())
        self.assertEqual(en_rows["a-mixed"]["Group"].text(), "Reagents")
        self.assertEqual(en_rows["a-mixed"]["Vessels"].text(), "3 (1 sealed)")
        self.assertEqual(en_rows["b-sealed"]["Suppliers"].text(), "unknown")
        self.assertEqual(en_rows["b-sealed"]["Opened"].text(), "sealed")

    def test_filters_and_offered_values_on_commercial_list(self) -> None:
        """Requirement: Lists by substance (`q`, `location`, `group` tree and
        unknown key, `supplier`, `sealed=1`, offered locations, suppliers,
        groups, kept values)."""
        purchased = make_group("purchased", "Purchased", label_de="Zugekauft")
        solvents = make_group("solvents", "Solvents", parent=purchased,
                              label_de="Lösungsmittel")
        reagents = make_group("reagents", "Reagents", parent=purchased,
                              label_de="Reagenzien")
        sub = make_substance(
            "acetone", "Acetone", name_de="Aceton", short_name="AC",
            cas="67-64-1", group=solvents)
        make_vessel(self.kl, substance=sub, source="bought", supplier="Merck",
                    supplier_batch="MK-11", location="Abzug 1", amount="10")
        v_opened = make_vessel(
            self.kl, substance=sub, source="bought", supplier="TCI",
            supplier_batch="TC-22", location="Abzug 2", amount="20")
        opened(v_opened, date(2026, 4, 1))
        make_vessel(self.kl, substance=sub, source="bought",
                    supplier="Verbraucht", location="Leer", amount="0")
        make_vessel(self.kl, substance=sub, source="made",
                    location="Zwischenlager", amount="5")

        for q, want in (
                ("acetone", "30"),
                ("aceton", "30"),
                ("AC", "30"),
                ("67-64", "30"),
                ("mk-11", "10"),
                ("merck", "10"),
        ):
            with self.subTest(q=q):
                rows = row_map(self.listing(f"?q={quote(q)}"))
                self.assertEqual(list(rows), ["acetone"])
                self.assertTrue(
                    has_amount(rows["acetone"]["Menge"].text(), want, "mg"))

        self.assertEqual(
            list(row_map(self.listing("?group=purchased"))), ["acetone"])
        self.assertEqual(
            list(row_map(self.listing("?group=reagents"))), [])
        self.assertEqual(
            list(row_map(self.listing("?group=nothing"))), [])

        self.assertTrue(has_amount(
            row_map(self.listing(f"?location={quote('Abzug 2')}"))["acetone"]
            ["Menge"].text(), "20", "mg"))

        root = self.listing(
            "?q=ac&location=Fort&group=solvents&supplier=Alt&sealed=1")
        self.assertEqual(field_value(root, "q"), "ac")
        self.assertEqual(field_value(root, "location"), "Fort")
        self.assertEqual(field_value(root, "group"), "solvents")
        self.assertEqual(field_value(root, "supplier"), "Alt")
        self.assertEqual(field_value(root, "sealed"), "on")

        locs = [o.get("value") for o in
                root.find("select", name="location").find_all("option")
                if o.get("value")]
        self.assertEqual(locs, ["Abzug 1", "Abzug 2", "Fort"])

        sups = [o.get("value") for o in
                root.find("select", name="supplier").find_all("option")
                if o.get("value")]
        self.assertEqual(sups, ["Alt", "Merck", "TCI"])

        groups = [o.get("value") for o in
                  root.find("select", name="group").find_all("option")
                  if o.get("value")]
        self.assertEqual(groups, ["purchased", "reagents", "solvents"])
        self.assertEqual(reagents.key, "reagents")


class CategoryViewAndDetailsTests(InventoryCase):

    def test_view_cookies_and_selected_key(self) -> None:
        """Requirement: Lists by substance ("The list shows its substances in
        the views `Tabelle` and `Details`, remembered in the cookies
        `intermediate-list-view` and `chemical-list-view`, with one substance
        selected by `selected=<key>`, as the item list does with its
        items.")."""
        alpha = make_substance("alpha", "Alpha")
        beta = make_substance("beta", "Beta")
        make_vessel(self.kl, substance=alpha, source="made")
        make_vessel(self.kl, substance=beta, source="made")
        make_vessel(self.kl, substance=alpha, source="bought")
        make_vessel(self.kl, substance=beta, source="bought")

        for path, cookie in ((INTERMEDIATES, INTERMEDIATE_COOKIE),
                             (CHEMICALS, CHEMICAL_COOKIE)):
            for val, want in ((None, "table"), ("table", "table"),
                              ("details", "details"), ("other", "table"),
                              ("", "table")):
                with self.subTest(path=path, cookie=val):
                    if val is None:
                        self.client.cookies.pop(cookie, None)
                    else:
                        self.client.cookies[cookie] = val
                    root = page(self.client.get(path))
                    layout = must_outer_split(root)
                    self.assertEqual(layout.get("data-view"), want)
                    radios = {r.get("id"): r for r in root.find_all(
                        "input", type="radio", name="view")}
                    self.assertEqual(
                        [n for n, r in radios.items()
                         if "checked" in r.attrs], [f"view-{want}"])
                    for r in radios.values():
                        self.assertIsNone(r.closest("form"))
                        self.assertIsNone(r.get("form"))

            for view in VIEWS:
                if view is None:
                    self.client.cookies.pop(cookie, None)
                else:
                    self.client.cookies[cookie] = view
                for query, want_key in (
                        ("", "alpha"),
                        ("?selected=beta", "beta"),
                        ("?selected=unknown", "alpha"),
                        ("?q=beta&selected=alpha", "beta")):
                    with self.subTest(path=path, view=view, query=query):
                        root = page(self.client.get(path + query))
                        self.assertEqual(outer_marked(root), [want_key])
                        pane = pane_of(root)
                        self.assertEqual(pane.get("data-item"), want_key)
                        self.assertEqual(
                            field_value(root, "selected"), want_key)

                empty_root = page(self.client.get(
                    f"{path}?q=no-such&selected=alpha"))
                self.assertEqual(outer_marked(empty_root), [])
                self.assertIsNone(pane_of(empty_root).get("data-item"))
                self.assertIsNone(field_value(empty_root, "selected"))

    def test_containers_of_the_selected_substance(self) -> None:
        """Scenario: Containers of the selected substance."""
        sub = make_substance("acetophenone", "Acetophenone")
        t21 = make_task(self.kl, sub, steps=1, started=past(1),
                        number="T-021")
        t8 = make_task(self.kl, sub, steps=1, started=past(1),
                       number="T-008")
        b21 = make_batch(self.kl, substance=sub, number="B-21",
                         task_step=t21.steps.get())
        b8 = make_batch(self.kl, substance=sub, number="B-8",
                        task_step=t8.steps.get())
        flask = make_vessel(self.kl, b21, unit="g", amount="1", flask=True)
        make_vessel(self.kl, b21, unit="g", amount="1.5",
                    location="Chemikalienschrank 3")
        make_vessel(self.kl, b8, unit="g", amount="12",
                    location="Chemikalienschrank 3")

        self.client.force_login(self.kl)
        self.client.cookies[INTERMEDIATE_COOKIE] = "details"
        root = page(self.client.get(f"{INTERMEDIATES}?selected=acetophenone"))
        pane = pane_of(root)
        self.assertEqual(pane.get("data-item"), "acetophenone")
        header, rows = detail_table(pane)
        self.assertEqual(header, DETAIL_COLS_INT_DE)
        self.assertEqual(len(rows), 3)
        by_id = {r["Gefäß"].text(): r for r in rows}
        flask_row = by_id[f"#{flask.pk}"]
        self.assertEqual(flask_row["Ort"].text(), "Kolben")
        self.assertIn("T-021", flask_row["Herkunft"].text())

        # The first vessel of the table is the selected lot, and its
        # details, not its row, offer the actions.
        self.assertEqual(lot_marked(root), [lot_ids(root)[0]])
        self.assertEqual(lot_pane(root).get("data-item"), lot_ids(root)[0])
        for row in lot_rows(root):
            self.assertEqual(
                [a for a in row.find_all("a") if "data-dialog" in a.attrs],
                [])
        actions = {a.text(): a for a in lot_pane(root).find_all("a")
                   if a.text() in VESSEL_ACTIONS}
        self.assertEqual(set(actions), set(VESSEL_ACTIONS))
        for link in actions.values():
            self.assertIn("data-dialog", link.attrs)

        new_batch = pane.find(
            "a", href=f"{NEW_BATCH}?substance=acetophenone")
        self.assertIsNotNone(new_batch)
        self.assertEqual(new_batch.text(), "Neue Charge")

    def test_one_bottle_with_its_movements(self) -> None:
        """Scenario: One bottle with its movements."""
        sub = make_substance("benzaldehyde", "Benzaldehyde")
        vessel = make_vessel(self.kl, substance=sub, source="bought",
                             unit="g", amount="100", supplier="Sigma",
                             supplier_batch="B-1")
        task = make_task(self.kl, sub, steps=1, started=past(1))
        step = task.steps.get()
        withdraw(self.kl, vessel, task_step=step, amount=Decimal("10"),
                 date=date(2026, 10, 1))
        withdraw(self.kl, vessel, task_step=step, amount=Decimal("15"),
                 date=date(2026, 10, 2))

        self.client.cookies[CHEMICAL_COOKIE] = "details"
        root = page(self.client.get(
            f"{CHEMICALS}?selected=benzaldehyde"))
        self.assertEqual(lot_ids(root), [str(vessel.pk)])
        self.assertEqual(lot_marked(root), [str(vessel.pk)])
        details = lot_pane(root)
        self.assertEqual(details.get("data-item"), str(vessel.pk))
        text = details.text()
        self.assertIn("Anfangsmenge", text)
        self.assertIn("Entnahme", text)
        self.assertLess(text.index("75"), text.index("90"))
        self.assertLess(text.index("90"), text.index("100"))
        self.assertIsNotNone(details.find("a", href=vessel_url(vessel)))
        self.assertIsNone(root.find(id="category-detail-movements"))
        self.assertEqual(root.find_all(cls="split-movements-head"), [])

    def test_details_fragment_behavior_and_filter_propagation(self) -> None:
        """Requirement: Lists by substance (details endpoint HTMX fragment,
        Vary on HX-Request, redirect without HTMX, 404 without open vessel of
        category, `Keine Gefäße` when filters hide all, `hx-get` carries
        filters)."""
        sub = make_substance("acetophenone", "Acetophenone")
        v = make_vessel(self.kl, substance=sub, source="made",
                        location="Regal 1")
        bought = make_substance("bought-only", "Bought only")
        make_vessel(self.kl, substance=bought, source="bought",
                    location="Regal 1")
        used = make_substance("used-only", "Used only")
        make_vessel(self.kl, substance=used, source="made", amount="0")
        end_sub = make_substance("cinnamic-acid", "Cinnamic acid")
        make_item(self.kl, "CH-0012", substance=end_sub)
        make_vessel(self.kl, substance=end_sub, source="made")

        list_root = page(self.client.get(
            f"{INTERMEDIATES}?location={quote('Regal 1')}"))
        row = body_rows(list_root)[0]
        hx_get = row.get("hx-get")
        parts = urlsplit(hx_get)
        self.assertEqual(parts.path, detail_url(INTERMEDIATES, "acetophenone"))
        self.assertEqual(parse_qs(parts.query), {"location": ["Regal 1"]})

        frag = self.client.get(hx_get, **HTMX)
        self.assertEqual(frag.status_code, 200)
        frag_root = page(frag)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(frag_root.find_all(tag), [], tag)
        self.assertEqual(frag_root.find(id="item-detail").get("data-item"),
                         "acetophenone")
        self.assertIn(f"#{v.pk}", frag_root.text())
        self.assertIn("hx-request", vary_of(frag))
        self.assertEqual(lot_ids(frag_root), [str(v.pk)])
        self.assertEqual(lot_pane(frag_root).get("data-item"), str(v.pk))

        plain = self.client.get(detail_url(INTERMEDIATES, "acetophenone"))
        self.assertIn(plain.status_code, (302, 303))
        target = urlsplit(plain["Location"])
        self.assertEqual(target.path, INTERMEDIATES)
        self.assertEqual(
            parse_qs(target.query), {"selected": ["acetophenone"]})
        self.assertIn("hx-request", vary_of(plain))

        for missing in ("unknown", "bought-only", "used-only",
                        "cinnamic-acid"):
            with self.subTest(missing=missing):
                self.assertEqual(
                    self.client.get(
                        detail_url(INTERMEDIATES, missing),
                        **HTMX).status_code,
                    404)

        hidden = self.client.get(
            detail_url(INTERMEDIATES, "acetophenone", "?flask=1"), **HTMX)
        self.assertEqual(hidden.status_code, 200)
        self.assertIn("Keine Gefäße", page(hidden).text())
        accept(language="en")
        hidden_en = self.client.get(
            detail_url(INTERMEDIATES, "acetophenone", "?flask=1"), **HTMX)
        self.assertIn("No vessels", page(hidden_en).text())

    def test_details_table_columns_cells_and_actions(self) -> None:
        """Requirement: Lists by substance (details heading, columns, vessel
        order, origin with task/step/journal, no task with journal, supplier
        and article no., opened on commercial only, signed-in actions)."""
        make_notebook("AE-1", self.kl)
        entry = entry_of("AE-1/9")
        sub = make_substance("acetophenone", "Acetophenone")
        task = make_task(self.kl, sub, steps=2, started=past(1),
                         number="T-007")
        step = task.steps.get(position=2)
        b_old = make_batch(
            self.kl, substance=sub, number="B-OLD", date=date(2026, 1, 5),
            task_step=step, journal_entry=entry)
        b_none = make_batch(
            self.kl, substance=sub, number="B-NODATE", date=None,
            journal_entry=entry)
        v_none = make_vessel(self.kl, b_none, location="", note="ohne Datum")
        v_old = make_vessel(self.kl, b_old, location="Regal 1", note="alt")

        b_chem = make_batch(
            self.kl, substance=sub, source="bought", supplier="Sigma",
            supplier_article_number="S-999", supplier_batch="SB-1",
            date=date(2026, 2, 1))
        v_chem = make_vessel(self.kl, b_chem, location="Kühlraum",
                             note="kühl")

        # Anonymous sees no actions and no heading batch link.
        anon_root = page(self.client.get(INTERMEDIATES))
        anon_int = pane_of(anon_root)
        self.assertIsNone(
            anon_int.find("a", href=f"{NEW_BATCH}?substance=acetophenone"))
        for action in VESSEL_ACTIONS:
            self.assertNotIn(action, anon_int.text())
        self.assertEqual(
            [a for a in anon_int.find_all("a") if "data-dialog" in a.attrs],
            [])

        self.client.force_login(self.kl)
        int_root = page(self.client.get(INTERMEDIATES))
        int_pane = pane_of(int_root)
        self.assertIsNotNone(int_pane.find(
            "a", href="/lab/registry/substances/acetophenone/"))
        int_head, int_rows = detail_table(int_pane)
        self.assertEqual(int_head, DETAIL_COLS_INT_DE)
        self.assertEqual(
            [r["Gefäß"].text() for r in int_rows],
            [f"#{v_old.pk}", f"#{v_none.pk}"])

        r_old, r_none = int_rows
        self.assertEqual(
            r_old["Gefäß"].find("a").get("href"), vessel_url(v_old))
        self.assertEqual(
            r_old["Charge"].find("a").get("href"), batch_url(b_old))
        self.assertIn("T-007", r_old["Herkunft"].text())
        self.assertIn("Stufe 2", r_old["Herkunft"].text())
        self.assertIn("AE-1/9", r_old["Herkunft"].text())
        self.assertEqual(
            [a.get("href") for a in r_old["Herkunft"].find_all("a")],
            ["/lab/tasks/T-007/", "/lab/journal/AE-1/"])
        self.assertEqual(r_old["Datum"].text(), "05.01.2026")
        self.assertNotIn("Bemerkung", int_head)
        self.assertNotIn("alt", [cell.text() for cell in r_old.values()])
        # The note is in the details of the lot, which is the first one.
        self.assertEqual(lot_pane(int_root).get("data-item"), str(v_old.pk))
        self.assertIn("alt", lot_pane(int_root).text())
        for row in lot_rows(int_root):
            self.assertEqual([a for a in row.find_all("a")
                              if "data-dialog" in a.attrs], [])

        self.assertIn("ohne Auftrag", r_none["Herkunft"].text())
        self.assertIn("AE-1/9", r_none["Herkunft"].text())
        self.assertEqual(
            [a.get("href") for a in r_none["Herkunft"].find_all("a")],
            ["/lab/journal/AE-1/"])

        chem_root = page(self.client.get(CHEMICALS))
        chem_pane = pane_of(chem_root)
        self.assertIsNotNone(chem_pane.find(
            "a", href=f"{NEW_BATCH}?substance=acetophenone&source=bought"))
        chem_head, chem_rows = detail_table(chem_pane)
        self.assertEqual(chem_head, DETAIL_COLS_CHEM_DE)
        self.assertEqual(len(chem_rows), 1)
        rc = chem_rows[0]
        self.assertIn("Sigma", rc["Herkunft"].text())
        self.assertIn("S-999", rc["Herkunft"].text())
        self.assertEqual(rc["Angebrochen am"].text(), "versiegelt")
        self.assertIn("kühl", lot_pane(chem_root).text())
        self.assertIsNotNone(rc["Gefäß"].find("a", href=vessel_url(v_chem)))

        accept(language="en")
        self.assertEqual(
            detail_table(pane_of(page(self.client.get(INTERMEDIATES))))[0],
            DETAIL_COLS_INT_EN)
        self.assertEqual(
            detail_table(pane_of(page(self.client.get(CHEMICALS))))[0],
            DETAIL_COLS_CHEM_EN)

    def test_the_lot_shows_its_five_newest_movements(self) -> None:
        """Requirement: Lists by substance (the lot's details show "its
        five newest movements"), whether the substance has one vessel or
        several, and no block of movements stands apart from the lot's
        details."""
        sub = make_substance("acetophenone", "Acetophenone")
        v1 = make_vessel(self.kl, substance=sub, unit="mg", amount="100")
        for n in range(1, 7):
            correct_vessel(self.kl, v1, amount=Decimal(str(100 - n)),
                           note=f"Bew-{n}")

        for second in (False, True):
            with self.subTest(second_vessel=second):
                if second:
                    make_vessel(self.kl, substance=sub, unit="mg",
                                amount="50")
                root = page(self.client.get(INTERMEDIATES))
                self.assertEqual(lot_marked(root), [str(v1.pk)])
                text = lot_pane(root).text()
                self.assertIn("KL", text)
                for n in range(2, 7):
                    self.assertIn(f"Bew-{n}", text)
                self.assertNotIn("Bew-1", text)
                self.assertNotIn("Anfangsmenge", text)
                for newer, older in zip(("Bew-6", "Bew-5", "Bew-4",
                                         "Bew-3"),
                                        ("Bew-5", "Bew-4", "Bew-3",
                                         "Bew-2")):
                    self.assertLess(text.index(newer), text.index(older))
                self.assertIsNone(root.find(id="category-detail-movements"))
                self.assertEqual(root.find_all(cls="split-movements-head"),
                                 [])

class VesselDialogTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.sub = make_substance("acetophenone", "Acetophenone")
        self.task = make_task(self.kl, self.sub, steps=1, started=past(1))
        self.step = self.task.steps.get()
        self.vessel = make_vessel(
            self.kl, substance=self.sub, unit="g", amount="12",
            location="Regal 1")

    def urls(self) -> dict[str, str]:
        return {
            "withdraw": vessel_url(self.vessel, "withdraw"),
            "transfer": vessel_url(self.vessel, "transfer"),
            "correct": vessel_url(self.vessel, "correct"),
            "edit": vessel_url(self.vessel, "edit"),
        }

    def valid_posts(self) -> dict[str, dict[str, str]]:
        return {
            "withdraw": {"step": str(self.step.pk), "amount": "2",
                         "date": TODAY.isoformat()},
            "transfer": {"amount": "1", "target": "", "location": "Regal 2",
                         "date": TODAY.isoformat(), "note": "umgefüllt"},
            "correct": {"amount": "10", "date": TODAY.isoformat(),
                        "note": "nachgewogen"},
            "edit": {"location": "Regal 3", "note": "neu"},
        }

    def test_vessel_forms_as_dialog_answer_form_alone(self) -> None:
        for name, url in self.urls().items():
            with self.subTest(form=name):
                whole = page(self.client.get(url))
                title = whole.find("main").find("h1").text()
                response = self.client.get(url, **HTMX)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                for tag in ("html", "head", "body", "nav", "main",
                            "script", "dialog"):
                    self.assertIsNone(root.find(tag), tag)
                self.assertEqual(heading_of(root), title)
                form = root.find("form")
                self.assertEqual(form.get("hx-post"), url)
                self.assertEqual(form.get("action"), url)
                self.assertEqual(form.get("method"), "post")
                self.assertIn("hx-target", form.attrs)
                self.assertIn("hx-disabled-elt", form.attrs)
                self.assertEqual(
                    controls_of(form), controls_of(whole.find("main")))
                self.assertLessEqual(
                    {"hx-request", "hx-history-restore-request"},
                    vary_of(response))

    def test_vessel_forms_page_and_history_restore(self) -> None:
        for name, url in self.urls().items():
            for extra in ({}, RESTORE):
                with self.subTest(form=name, restore=bool(extra)):
                    root = page(self.client.get(url, **extra))
                    self.assertIsNotNone(root.find("html"))
                    form = root.find("main").find("form")
                    self.assertEqual(
                        [n for n in form.attrs if n.startswith("hx-")], [])

    def test_vessel_dialog_errors_and_saves(self) -> None:
        bad = {
            "withdraw": ("amount", {"step": str(self.step.pk), "amount": "x",
                                    "date": TODAY.isoformat()}),
            "transfer": ("amount", {"amount": "x", "target": "",
                                    "location": "Regal 2",
                                    "date": TODAY.isoformat(), "note": ""}),
            "correct": ("note", {"amount": "10", "date": TODAY.isoformat(),
                                 "note": ""}),
            "edit": ("location", {"location": "x" * 101, "note": ""}),
        }
        before = snapshot()
        for name, (field, data) in bad.items():
            url = self.urls()[name]
            with self.subTest(form=name):
                res = self.client.post(url, data, **HTMX)
                self.assertEqual(res.status_code, 200)
                root = page(res)
                self.assertIsNone(root.find("html"))
                self.assertTrue(errors_at(root, field))
        self.assertEqual(snapshot(), before)

        for name, data in self.valid_posts().items():
            url = self.urls()[name]
            with self.subTest(save=name):
                done = self.client.post(url, data, **HTMX)
                self.assertEqual(done.status_code, 204)
                self.assertEqual(done.content, b"")
                payload = json.loads(done["HX-Trigger"])
                self.assertIn("lab-saved", payload)
                self.assertLessEqual(
                    {"hx-request", "hx-history-restore-request"},
                    vary_of(done))

    def test_signed_out_vessel_dialog_redirects_to_login(self) -> None:
        self.client.logout()
        origin = f"{INTERMEDIATES}?selected=acetophenone"
        before = snapshot()
        for name, url in self.urls().items():
            for method, res in (
                    ("GET", self.client.get(url, **current(origin))),
                    ("POST", self.client.post(
                        url, self.valid_posts()[name], **current(origin)))):
                with self.subTest(form=name, method=method):
                    self.assertEqual(res.status_code, 204)
                    target = urlsplit(res["HX-Redirect"])
                    self.assertEqual(target.path, LOGIN)
                    self.assertEqual(
                        parse_qs(target.query), {"next": [origin]})
        self.assertEqual(snapshot(), before)

    def test_category_lists_mark_refreshed_parts(self) -> None:
        """Design: the heading's counts, the rows, the offered locations and
        suppliers, and the details with its vessel table carry `data-refresh`
        with an `id`."""
        make_vessel(self.kl, substance=self.sub, source="bought",
                    supplier="Sigma", location="Kühlraum")
        for path, selects in ((INTERMEDIATES, ("location",)),
                              (CHEMICALS, ("location", "supplier"))):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                for node in [
                        root.find(cls="lab-heading").find(cls="lab-count"),
                             root.find("tbody"),
                             pane_of(root),
                             *(root.find("select", name=s) for s in selects)]:
                    self.assertIsNotNone(node)
                    marked = region(node)
                    self.assertIsNotNone(marked)
                    self.assertTrue(marked.get("id"))

    def test_booking_in_a_dialog(self) -> None:
        """Scenario: Booking in a dialog."""
        self.client.cookies[INTERMEDIATE_COOKIE] = "details"
        withdraw_url = vessel_url(self.vessel, "withdraw")
        self.assertEqual(
            self.client.get(withdraw_url, **HTMX).status_code, 200)
        done = self.client.post(withdraw_url, {
            "step": str(self.step.pk), "amount": "2",
            "date": TODAY.isoformat()}, **HTMX)
        self.assertEqual(done.status_code, 204)
        self.assertIn("lab-saved", json.loads(done["HX-Trigger"]))

        root = page(self.client.get(
            f"{INTERMEDIATES}?selected=acetophenone&lot={self.vessel.pk}"))
        self.assertEqual(must_outer_split(root).get("data-view"), "details")
        rows = row_map(root)
        self.assertTrue(
            has_amount(rows["acetophenone"]["Menge"].text(), "10", "g"))
        pane = pane_of(root)
        self.assertEqual(pane.get("data-item"), "acetophenone")
        _, vrows = detail_table(pane)
        self.assertTrue(has_amount(vrows[0]["Menge"].text(), "10", "g"))
        self.assertEqual(lot_marked(root), [str(self.vessel.pk)])
        self.assertEqual(lot_pane(root).get("data-item"),
                         str(self.vessel.pk))
        self.assertTrue(has_amount(lot_pane(root).text(), "10", "g"))

    def test_the_last_admitted_bottle_opened(self) -> None:
        """Scenario: The last admitted bottle opened."""
        benz = make_substance("benzaldehyde", "Benzaldehyde")
        tol = make_substance("toluene", "Toluene")
        v_benz = make_vessel(self.kl, substance=benz, source="bought",
                             unit="g", amount="50", supplier="Sigma")
        v_tol = make_vessel(self.kl, substance=tol, source="bought",
                            unit="g", amount="50", supplier="Sigma")

        self.client.cookies[CHEMICAL_COOKIE] = "details"
        first_root = page(self.client.get(
            f"{CHEMICALS}?sealed=1&selected=benzaldehyde"))
        self.assertEqual(
            list(row_map(first_root)), ["benzaldehyde", "toluene"])
        self.assertEqual(
            pane_of(first_root).get("data-item"), "benzaldehyde")

        done1 = self.client.post(vessel_url(v_benz, "withdraw"), {
            "step": str(self.step.pk), "amount": "1",
            "date": TODAY.isoformat()}, **HTMX)
        self.assertEqual(done1.status_code, 204)

        second_root = page(self.client.get(
            f"{CHEMICALS}?sealed=1&selected=benzaldehyde"))
        self.assertEqual(list(row_map(second_root)), ["toluene"])
        self.assertEqual(outer_marked(second_root), ["toluene"])
        self.assertEqual(pane_of(second_root).get("data-item"), "toluene")
        self.assertEqual(field_value(second_root, "selected"), "toluene")

        done2 = self.client.post(vessel_url(v_tol, "withdraw"), {
            "step": str(self.step.pk), "amount": "1",
            "date": TODAY.isoformat()}, **HTMX)
        self.assertEqual(done2.status_code, 204)

        third_root = page(self.client.get(
            f"{CHEMICALS}?sealed=1&selected=toluene"))
        self.assertEqual(row_map(third_root), {})
        self.assertEqual(outer_marked(third_root), [])
        self.assertIsNone(pane_of(third_root).get("data-item"))


# ---------------------------------------------------------------------------
# The lots of a substance (end-product-inventory: Lists by substance)

LOT_VALUES = {
    "data-master-detail-level-value": "inner",
    "data-master-detail-rows-value": "lot-rows",
    "data-master-detail-pane-value": "lot-detail",
    "data-master-detail-param-value": "lot",
}


def lot_url(base: str, key: str, vessel: Vessel) -> str:
    return f"{base}{key}/lots/{vessel.pk}/"


def single(root: Element) -> Element:
    """The one element that a fragment holds."""
    found = [c for c in root.children if isinstance(c, Element)]
    assert len(found) == 1, f"{len(found)} elements"
    return found[0]


def ids_of(root: Element) -> list[str]:
    return [e.get("id") for e in root.walk() if e.get("id")]


class LotCase(InventoryCase):
    """``acetophenone`` with three stored intermediate vessels in
    ``Regal 1``, in the order of their ids, and ``benzaldehyde`` with two
    sealed bottles."""

    def setUp(self) -> None:
        super().setUp()
        self.aceto = make_substance("acetophenone", "Acetophenone")
        self.lots = [
            make_vessel(self.kl, substance=self.aceto, unit="g",
                        amount=str(n), location="Regal 1")
            for n in (1, 2, 3)]
        self.benz = make_substance("benzaldehyde", "Benzaldehyde")
        self.bottles = [
            make_vessel(self.kl, substance=self.benz, source="bought",
                        unit="g", amount=str(n), supplier="Sigma")
            for n in (10, 20)]

    def listing(self, base: str = INTERMEDIATES, query: str = "",
                signed_in: bool = False, **extra: Any) -> Element:
        if signed_in:
            self.client.force_login(self.kl)
        self.client.cookies[INTERMEDIATE_COOKIE] = "details"
        self.client.cookies[CHEMICAL_COOKIE] = "details"
        response = self.client.get(base + query, **extra)
        self.assertEqual(response.status_code, 200)
        return page(response)


class LotSplitTests(LotCase):
    """The pane of a substance with vessels is a second split."""

    def test_the_pane_holds_a_columns_split_of_the_lots(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        pane = pane_of(root)
        splits = pane.find_all("div", cls="split")
        self.assertEqual(len(splits), 1)
        inner = splits[0]
        self.assertIn("split--columns", inner.classes)
        self.assertNotIn("split--outer", inner.classes)
        self.assertEqual(inner.get("data-major"), "first")
        self.assertEqual(inner.get("data-controller"), "master-detail")
        for name, value in LOT_VALUES.items():
            self.assertEqual(inner.get(name), value, name)
        first, second = split_panes(inner)
        grid_ = first.find("table", id=LOT_TABLE)
        self.assertIsNotNone(grid_)
        self.assertIsNotNone(second.find("aside", id="lot-detail"))

    def test_the_lot_table_is_a_main_table_that_sorts(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        found = root.find_all("table", id=LOT_TABLE)
        self.assertEqual(len(found), 1)
        found = found[0]
        self.assertIn("main-table", found.classes)
        self.assertNotIn("aux-table", found.classes)
        self.assertIn("data-sortable", found.attrs)
        self.assertIn("sortable-table",
                      (found.get("data-controller") or "").split())

    def test_the_rows_ask_for_their_lot_and_the_body_takes_it(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        body = root.find("tbody", id="lot-rows")
        self.assertIsNotNone(body)
        self.assertEqual(
            {name: body.get(name) for name in (
                "hx-target", "hx-swap", "hx-sync", "hx-indicator")},
            {"hx-target": "#lot-detail", "hx-swap": "outerHTML",
             "hx-sync": "#main:replace", "hx-indicator": "#lot-detail"})
        self.assertEqual(lot_ids(root), [str(v.pk) for v in self.lots])
        for row, vessel in zip(lot_rows(root), self.lots):
            self.assertEqual(
                path_of(row.get("hx-get")),
                lot_url(INTERMEDIATES, "acetophenone", vessel))
            self.assertEqual(row.get("hx-trigger"), "item-select")

    def test_one_lot_is_selected_and_its_details_are_shown(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        first = self.lots[0]
        self.assertEqual(lot_marked(root), [str(first.pk)])
        details = lot_pane(root)
        self.assertEqual(details.tag, "aside")
        self.assertEqual(details.get("data-item"), str(first.pk))

    def test_the_lot_details_are_a_head_and_widgets(self) -> None:
        self.client.force_login(self.kl)
        root = self.listing(query="?selected=acetophenone")
        details = lot_pane(root)
        head = pane_head(details)
        self.assertIsNotNone(head)
        title = head.find("h2", id="lot-detail-title")
        self.assertIsNotNone(title)
        self.assertEqual(title.find("a").get("href"),
                         vessel_url(self.lots[0]))
        found = pane_widgets(details)
        self.assertTrue(found)
        for each in found:
            self.assertIsNotNone(each.find(cls="widget__head").find("h3"))
            self.assertIsNotNone(has_ancestor_class(each, "widget-grid"))

    def test_the_lot_actions_are_in_a_popover_for_a_signed_in_user(
            self) -> None:
        root = self.listing(query="?selected=acetophenone", signed_in=True)
        details = lot_pane(root)
        menu = details.find(id="lot-actions")
        self.assertIsNotNone(menu)
        self.assertIn("popover", menu.attrs)
        opener = details.find("button",
                              attrs={"popovertarget": "lot-actions"})
        self.assertIsNotNone(opener)
        self.assertIn(opener, list(pane_head(details).walk()))
        links = {a.text(): a for a in details.find_all("a")
                 if "data-dialog" in a.attrs}
        self.assertLessEqual(set(VESSEL_ACTIONS), set(links))
        self.assertIn(vessel_url(self.lots[0], "edit"),
                      [a.get("href") for a in menu.find_all("a")])

    def test_no_id_repeats_on_the_page(self) -> None:
        for signed_in in (False, True):
            for base, key in ((INTERMEDIATES, "acetophenone"),
                              (CHEMICALS, "benzaldehyde")):
                with self.subTest(base=base, signed_in=signed_in):
                    root = self.listing(base, f"?selected={key}",
                                        signed_in=signed_in)
                    found = ids_of(root)
                    self.assertEqual(
                        sorted(i for i in set(found)
                               if found.count(i) > 1), [])
                    self.assertIn("lot-detail-title", found)
                    self.assertIn("item-detail-title", found)
                    if signed_in:
                        self.assertIn("lot-actions", found)

    def test_nothing_in_the_pane_but_the_pane_is_refreshed(self) -> None:
        for signed_in in (False, True):
            for base, key in ((INTERMEDIATES, "acetophenone"),
                              (CHEMICALS, "benzaldehyde")):
                with self.subTest(base=base, signed_in=signed_in):
                    pane = pane_of(self.listing(base, f"?selected={key}",
                                                signed_in=signed_in))
                    self.assertIn("data-refresh", pane.attrs)
                    self.assertEqual(
                        [e.get("id") for e in pane.walk()
                         if "data-refresh" in e.attrs], [])

    def test_the_movements_block_of_a_single_vessel_is_gone(self) -> None:
        root = self.listing(CHEMICALS, "?selected=benzaldehyde")
        self.assertIsNone(root.find(id="category-detail-movements"))
        self.assertEqual(root.find_all(cls="split-movements-head"), [])
        self.assertEqual(root.find_all(cls="split-vessel-table"), [])
        self.assertIsNone(root.find(id="category-detail-vessels"))

    def test_the_old_pane_of_vessels_is_gone(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        for name in ("split-detail-head", "split-detail-actions",
                     "item-detail--split", "split-vessel-actions",
                     "split-vessel-note"):
            self.assertEqual(root.find_all(cls=name), [], name)

    def test_a_pane_without_vessels_has_no_second_split(self) -> None:
        root = self.listing(INTERMEDIATES, "?selected=acetophenone&flask=1")
        # No vessel of the substance is a flask: the list is empty.
        self.assertEqual(pane_of(root).find_all("div", cls="split"), [])
        details = self.client.get(
            f"{INTERMEDIATES}acetophenone/?flask=1", **HTMX)
        found = page(details)
        self.assertIn("Keine Gefäße", found.text())
        self.assertIsNone(found.find(id=LOT_TABLE))
        self.assertIsNone(found.find(id="lot-detail"))

    def test_the_lot_columns_in_german_and_english(self) -> None:
        for base, key, german, english in (
                (INTERMEDIATES, "acetophenone", DETAIL_COLS_INT_DE,
                 DETAIL_COLS_INT_EN),
                (CHEMICALS, "benzaldehyde", DETAIL_COLS_CHEM_DE,
                 DETAIL_COLS_CHEM_EN)):
            with self.subTest(base=base):
                accept(language="de")
                header, _ = detail_table(
                    pane_of(self.listing(base, f"?selected={key}")))
                self.assertEqual(header, german)
                accept(language="en")
                header, _ = detail_table(
                    pane_of(self.listing(base, f"?selected={key}")))
                self.assertEqual(header, english)


class SelectingALotTests(LotCase):
    """Scenario: Selecting a lot."""

    def test_a_lot_names_the_marked_row_and_its_details(self) -> None:
        second = self.lots[1]
        root = self.listing(
            query=f"?selected=acetophenone&lot={second.pk}")
        self.assertEqual(lot_marked(root), [str(second.pk)])
        self.assertEqual(lot_pane(root).get("data-item"), str(second.pk))

    def test_a_lot_that_is_none_of_the_lots_is_the_first(self) -> None:
        other = self.bottles[0]
        for value in (str(other.pk), "", "abc", "-1", "99999999",
                      str(self.lots[0].pk + 1000), "1.5"):
            with self.subTest(lot=value):
                root = self.listing(
                    query=f"?selected=acetophenone&lot={value}")
                self.assertEqual(lot_marked(root),
                                 [str(self.lots[0].pk)])
                self.assertEqual(lot_pane(root).get("data-item"),
                                 str(self.lots[0].pk))

    def test_a_lot_the_filters_hide_is_not_selected(self) -> None:
        make_vessel(self.kl, substance=self.aceto, unit="g", amount="4",
                    location="Regal 2")
        hidden = self.lots[0]
        root = self.listing(
            query=f"?selected=acetophenone&location=Regal+2"
                  f"&lot={hidden.pk}")
        self.assertEqual(len(lot_ids(root)), 1)
        self.assertNotIn(str(hidden.pk), lot_ids(root))
        self.assertEqual(lot_marked(root), lot_ids(root))

    def test_a_lot_is_read_where_the_substance_is_selected(self) -> None:
        second = self.bottles[1]
        root = self.listing(
            CHEMICALS, f"?selected=benzaldehyde&lot={second.pk}")
        self.assertEqual(lot_marked(root), [str(second.pk)])

    def test_the_filter_bar_and_the_headers_name_the_lot(self) -> None:
        second = self.lots[1]
        root = self.listing(
            query=f"?selected=acetophenone&lot={second.pk}")
        fields = {c.get("name"): c.get("value") for c in
                  root.find(id="filter-selected").find_all(
                      "input", type="hidden")}
        self.assertEqual(fields, {"selected": "acetophenone",
                                  "lot": str(second.pk)})
        links = root.find(id="item-head").find_all("a")
        self.assertTrue(links)
        for link in links:
            found = query_of(link.get("href"))
            self.assertEqual(found.get("selected"), ["acetophenone"])
            self.assertEqual(found.get("lot"), [str(second.pk)])
            self.assertEqual(query_of(link.get("hx-get")), found)

    def test_the_resolved_first_lot_is_named_too(self) -> None:
        root = self.listing(query="?selected=acetophenone")
        fields = {c.get("name"): c.get("value") for c in
                  root.find(id="filter-selected").find_all(
                      "input", type="hidden")}
        self.assertEqual(fields.get("lot"), str(self.lots[0].pk))
        for link in root.find(id="item-head").find_all("a"):
            self.assertEqual(query_of(link.get("href")).get("lot"),
                             [str(self.lots[0].pk)])

    def test_a_list_without_vessels_names_no_lot(self) -> None:
        root = self.listing(query="?q=no-such-thing")
        self.assertEqual(
            root.find(id="filter-selected").find_all("input", name="lot"),
            [])
        for link in root.find(id="item-head").find_all("a"):
            self.assertNotIn("lot", query_of(link.get("href")))

    def test_the_lot_details_endpoint(self) -> None:
        """The lot's details alone, its address, and the redirect."""
        second = self.lots[1]
        path = lot_url(INTERMEDIATES, "acetophenone", second)
        response = self.client.get(path, **current(
            f"{INTERMEDIATES}?location=Regal+1&selected=acetophenone"))
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = single(root)
        self.assertEqual(found.get("id"), "lot-detail")
        self.assertEqual(found.get("data-item"), str(second.pk))
        self.assertEqual(root.find_all(id="item-detail"), [])
        self.assertLessEqual({"hx-request", "hx-current-url"},
                             vary_of(response))
        self.assertEqual(
            response["HX-Replace-Url"],
            f"{INTERMEDIATES}?location=Regal+1&selected=acetophenone"
            f"&lot={second.pk}")
        plain = self.client.get(path)
        self.assertIn(plain.status_code, (302, 303))
        target = urlsplit(plain["Location"])
        self.assertEqual(target.path, INTERMEDIATES)
        self.assertEqual(
            parse_qs(target.query),
            {"selected": ["acetophenone"], "lot": [str(second.pk)]})
        self.assertLessEqual({"hx-request", "hx-current-url"},
                             vary_of(plain))

    def test_the_lot_endpoint_ignores_a_foreign_current_url(self) -> None:
        path = lot_url(INTERMEDIATES, "acetophenone", self.lots[2])
        response = self.client.get(path, **current(
            f"{INTERMEDIATES}?location=Nowhere&selected=x",
            host="evil.example"))
        self.assertEqual(
            response["HX-Replace-Url"],
            f"{INTERMEDIATES}?selected=acetophenone&lot={self.lots[2].pk}")

    def test_the_lot_endpoint_of_the_commercial_chemicals(self) -> None:
        path = lot_url(CHEMICALS, "benzaldehyde", self.bottles[1])
        response = self.client.get(path, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(single(page(response)).get("data-item"),
                         str(self.bottles[1].pk))
        self.assertEqual(
            response["HX-Replace-Url"],
            f"{CHEMICALS}?selected=benzaldehyde&lot={self.bottles[1].pk}")

    def test_the_rows_of_the_substance_list_name_no_lot(self) -> None:
        root = self.listing(query=f"?lot={self.lots[1].pk}")
        for row in root.find("tbody", id="item-rows").find_all("tr"):
            self.assertNotIn("lot", query_of(row.get("hx-get")))


class LotNotFoundTests(LotCase):
    """Scenarios: A lot of another substance; A lot the filters hide."""

    def test_a_lot_of_another_substance_or_category(self) -> None:
        # The lot of its own substance and category is found.
        self.assertEqual(self.client.get(
            lot_url(INTERMEDIATES, "acetophenone", self.lots[0]),
            **HTMX).status_code, 200)
        self.assertEqual(self.client.get(
            lot_url(CHEMICALS, "benzaldehyde", self.bottles[0]),
            **HTMX).status_code, 200)
        for path in (
                lot_url(INTERMEDIATES, "acetophenone", self.bottles[0]),
                lot_url(CHEMICALS, "acetophenone", self.lots[0]),
                lot_url(INTERMEDIATES, "benzaldehyde", self.lots[0]),
                lot_url(INTERMEDIATES, "benzaldehyde", self.bottles[0])):
            for extra in (HTMX, {}):
                with self.subTest(path=path, htmx=bool(extra)):
                    self.assertEqual(
                        self.client.get(path, **extra).status_code, 404)

    def test_an_unknown_key_or_id_or_a_used_up_vessel(self) -> None:
        used = make_vessel(self.kl, substance=self.aceto, unit="g",
                           amount="0")
        self.assertEqual(self.client.get(
            lot_url(INTERMEDIATES, "acetophenone", self.lots[1]),
            **HTMX).status_code, 200)
        for path in (
                lot_url(INTERMEDIATES, "no-such-substance", self.lots[0]),
                f"{INTERMEDIATES}acetophenone/lots/{used.pk + 999}/",
                lot_url(INTERMEDIATES, "acetophenone", used)):
            for extra in (HTMX, {}):
                with self.subTest(path=path, htmx=bool(extra)):
                    self.assertEqual(
                        self.client.get(path, **extra).status_code, 404)

    def test_a_lot_the_filters_hide(self) -> None:
        """Scenario: A lot the filters hide."""
        opened = self.bottles[0]
        Vessel.objects.filter(pk=opened.pk).update(
            opened_on=date(2026, 3, 5))
        path = lot_url(CHEMICALS, "benzaldehyde", opened)
        self.assertEqual(self.client.get(path, **current(
            f"{CHEMICALS}?sealed=1&selected=benzaldehyde")).status_code, 404)
        self.assertEqual(self.client.get(path, **current(
            f"{CHEMICALS}?selected=benzaldehyde")).status_code, 200)

    def test_the_request_query_filters_without_a_current_url(self) -> None:
        opened = self.bottles[0]
        Vessel.objects.filter(pk=opened.pk).update(
            opened_on=date(2026, 3, 5))
        path = lot_url(CHEMICALS, "benzaldehyde", opened)
        self.assertEqual(
            self.client.get(path + "?sealed=1", **HTMX).status_code, 404)
        self.assertEqual(self.client.get(path, **HTMX).status_code, 200)
        foreign = self.client.get(path + "?sealed=1", **current(
            f"{CHEMICALS}?selected=benzaldehyde", host="evil.example"))
        self.assertEqual(foreign.status_code, 404)


class NewSubstanceTests(LotCase):
    """Scenario: A new substance brings its first lot."""

    def test_the_substance_endpoint_names_its_first_lot(self) -> None:
        other = make_substance("other-int", "Other")
        earlier = make_vessel(self.kl, substance=other, unit="g",
                              amount="5")
        response = self.client.get(
            f"{INTERMEDIATES}acetophenone/",
            **current(f"{INTERMEDIATES}?selected=other-int"
                      f"&lot={earlier.pk}"))
        address = replaced(self, response)
        self.assertEqual(urlsplit(address).path, INTERMEDIATES)
        self.assertEqual(query_of(address), {
            "selected": ["acetophenone"], "lot": [str(self.lots[0].pk)]})

    def test_an_earlier_lot_is_ignored_even_when_it_is_the_same_substance(
            self) -> None:
        response = self.client.get(
            f"{INTERMEDIATES}acetophenone/?lot={self.lots[2].pk}",
            **current(f"{INTERMEDIATES}?selected=acetophenone"
                      f"&lot={self.lots[2].pk}"))
        self.assertEqual(
            query_of(replaced(self, response)).get("lot"),
            [str(self.lots[0].pk)])
        found = single(page(response))
        self.assertEqual(found.get("id"), "item-detail")
        self.assertEqual(lot_pane(found).get("data-item"),
                         str(self.lots[0].pk))
        self.assertEqual(lot_marked(found), [str(self.lots[0].pk)])

    def test_the_first_lot_is_the_oldest_batch(self) -> None:
        old = make_vessel(
            self.kl, substance=self.aceto, unit="g", amount="9",
            date=date(2020, 1, 1))
        make_vessel(self.kl, substance=self.aceto, unit="g", amount="9",
                    date=date(2021, 1, 1))
        response = self.client.get(f"{INTERMEDIATES}acetophenone/", **HTMX)
        self.assertEqual(query_of(replaced(self, response)).get("lot"),
                         [str(old.pk)])
        root = self.listing(query="?selected=acetophenone")
        self.assertEqual(lot_ids(root)[0], str(old.pk))
        self.assertEqual(lot_ids(root)[-1], str(self.lots[-1].pk))

    def test_no_lot_is_named_when_the_filters_admit_no_vessel(self) -> None:
        response = self.client.get(
            f"{INTERMEDIATES}acetophenone/?flask=1", **HTMX)
        address = replaced(self, response)
        self.assertEqual(query_of(address).get("selected"),
                         ["acetophenone"])
        self.assertNotIn("lot", query_of(address))

    def test_the_lists_push_address_names_the_resolved_lot(self) -> None:
        for query, wanted in (
                ("", self.lots[0]),
                (f"?lot={self.lots[1].pk}", self.lots[1]),
                (f"?selected=acetophenone&lot={self.lots[2].pk}",
                 self.lots[2]),
                (f"?selected=acetophenone&lot={self.bottles[0].pk}",
                 self.lots[0])):
            with self.subTest(query=query):
                response = self.client.get(INTERMEDIATES + query, **HTMX)
                pushed = response["HX-Push-Url"]
                self.assertEqual(query_of(pushed).get("lot"),
                                 [str(wanted.pk)])
                self.assertEqual(query_of(pushed).get("selected"),
                                 ["acetophenone"])


class LotDialogTests(FormCase):
    """Scenario: The selected lot opened."""

    def setUp(self) -> None:
        super().setUp()
        self.sub = make_substance("benzaldehyde", "Benzaldehyde")
        self.task = make_task(self.kl, self.sub, steps=1, started=past(1))
        self.step = self.task.steps.get()
        self.first, self.second = [
            make_vessel(self.kl, substance=self.sub, source="bought",
                        unit="g", amount="50", supplier="Sigma")
            for _ in range(2)]

    def test_the_selected_lot_opened(self) -> None:
        self.client.cookies[CHEMICAL_COOKIE] = "details"
        before = page(self.client.get(
            f"{CHEMICALS}?sealed=1&selected=benzaldehyde"
            f"&lot={self.second.pk}"))
        self.assertEqual(lot_ids(before),
                         [str(self.first.pk), str(self.second.pk)])
        self.assertEqual(lot_marked(before), [str(self.second.pk)])

        done = self.client.post(vessel_url(self.second, "withdraw"), {
            "step": str(self.step.pk), "amount": "1",
            "date": TODAY.isoformat()}, **HTMX)
        self.assertEqual(done.status_code, 204)

        # The page is fetched from the address that still names the
        # second bottle, which no longer is a lot.
        stale = f"{CHEMICALS}?sealed=1&selected=benzaldehyde" \
                f"&lot={self.second.pk}"
        after = page(self.client.get(stale))
        self.assertEqual(outer_marked(after), ["benzaldehyde"])
        self.assertEqual(lot_ids(after), [str(self.first.pk)])
        self.assertEqual(lot_marked(after), [str(self.first.pk)])
        self.assertEqual(lot_pane(after).get("data-item"),
                         str(self.first.pk))
        live = self.client.get(stale, **HTMX)
        self.assertEqual(query_of(live["HX-Push-Url"]).get("lot"),
                         [str(self.first.pk)])
        fields = {c.get("name"): c.get("value") for c in
                  after.find(id="filter-selected").find_all(
                      "input", type="hidden")}
        self.assertEqual(fields.get("lot"), str(self.first.pk))
