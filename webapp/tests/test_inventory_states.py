"""Tests of the item's state, its stock entry date, the projected means
and the item list's levels and legend (end-product-inventory: Items,
Consumption, Stock levels, Item list, Item page and Inventory forms;
production-planning: Demand models, Runway and Item forecast)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import Refused, correct, create_item, fill
from inventory.models import EnteredConsumption, Item

from . import Element, field_value, page, table
from .inventory_support import (LEVELS, LIST, NEW_ITEM, TODAY, FormCase,
                                InventoryCase, fresh, item_url)
from .planning_support import PlanningCase

PROJECTED = "hochgerechnet aus dem laufenden Jahr"


def edit_data(item: Item, **over: str) -> dict[str, str]:
    data = {"name": item.name, "category": item.category,
            "note": item.note, "status": item.status,
            "stocked_on": item.stocked_on.isoformat()
            if item.stocked_on else ""}
    data.update(over)
    return data


class ProjectionTests(InventoryCase):

    def test_projected_means(self) -> None:
        """Scenario: Projected means."""
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        found = self.consumption(item)
        self.assertTrue(found.projected)
        self.assertEqual(round(found.mean_quarter, 1), Decimal("2.5"))
        self.assertEqual(round(found.mean_year, 1), Decimal("10.1"))
        self.assertEqual(round(found.coverage, 1), Decimal("1.2"))
        self.assertEqual(found.level, "watch")

    def test_one_early_delivery(self) -> None:
        """Scenario: One early delivery."""
        item = self.item("P-2", quantity=5)
        self.deliver(item, 3, date(2026, 10, 15))
        found = self.consumption(item)
        self.assertTrue(found.projected)
        self.assertEqual(found.mean_quarter, Decimal(3))
        self.assertEqual(round(found.coverage, 1), Decimal("0.7"))
        self.assertEqual(found.level, "low")

    def test_years_counted(self) -> None:
        """Scenario: Years counted."""
        first = self.item("P-3", quantity=5)
        self.enter(first, 2024, 3, 0)
        self.enter_year(first, 2025, 8)
        second = self.item("P-4", quantity=5)
        self.enter(second, 2026, 1, 4)
        self.assertEqual(self.consumption(first).mean_year, 16)
        self.assertFalse(self.consumption(first).projected)
        self.assertTrue(self.consumption(second).projected)

    def test_earlier_zeros_do_not_stop_the_projection(self) -> None:
        item = self.item("P-5", quantity=5)
        self.enter_year(item, 2025, 0)
        self.enter(item, 2026, 3, 4)
        self.assertTrue(self.consumption(item).projected)

    def test_the_next_year_counts_complete_years(self) -> None:
        item = self.item("P-6", quantity=3)
        self.enter(item, 2026, 2, 6)
        found = self.consumption(item, date(2027, 2, 1))
        self.assertFalse(found.projected)
        self.assertEqual(found.mean_year, 6)

    def test_no_coverage_for_a_dormant_item(self) -> None:
        """Scenario: No coverage for a dormant item."""
        item = self.item("P-7", quantity=6)
        self.enter_year(item, 2024, 8)
        found = self.consumption(item)
        self.assertEqual(found.mean_year, 16)
        self.assertIsNone(found.coverage)
        self.assertEqual(found.level, "dormant")


class QuarterToComeTests(FormCase):

    def test_no_value_for_a_quarter_to_come(self) -> None:
        """Scenario: No value for a quarter to come."""
        item = self.item("Q-1")
        with self.assertRaises(Refused):
            self.enter(item, 2027, 1, 3)
        response = self.client.post(item_url(item, "consumption"), {
            "year": "2027", "quarter": "1", "count": "3"})
        self.refused(response)
        self.client.post(item_url(item, "consumption"), {
            "year": "2026", "quarter": "4", "count": "3"})
        self.assertEqual(list(EnteredConsumption.objects.filter(
            item=item).values_list("year", "quarter", "count")),
            [(2026, 4, 3)])


class StockEntryTests(FormCase):

    def test_by_the_first_filling(self) -> None:
        """Scenario: Stock entry by the first filling."""
        item = create_item(self.kl, article_number="S-1", name="Probe",
                           size=Decimal("10"), unit="mg", quantity=0)
        self.assertIsNone(fresh(item).stocked_on)
        fill(self.kl, item, count=3, date=date(2026, 10, 20))
        fill(self.kl, item, count=2, date=date(2026, 11, 2))
        stored = fresh(item)
        self.assertEqual(stored.stocked_on, date(2026, 10, 20))
        self.assertTrue(stored.is_new(TODAY))
        last = stored.history.order_by("-history_id").first()
        self.assertEqual(last.history_user, self.kl)

    def test_by_a_correction(self) -> None:
        item = create_item(self.kl, article_number="S-2", name="Probe",
                           size=Decimal("10"), unit="mg", quantity=0)
        correct(self.kl, item, count=2, note="gefunden",
                date=date(2026, 9, 1))
        self.assertEqual(fresh(item).stocked_on, date(2026, 9, 1))

    def test_by_the_opening_count(self) -> None:
        """Scenario: Stock entry by the opening count."""
        item = create_item(self.kl, article_number="S-3", name="Probe",
                           size=Decimal("10"), unit="mg", quantity=5)
        self.assertEqual(fresh(item).stocked_on, TODAY)
        response = self.client.post(item_url(item, "edit"), edit_data(
            fresh(item), stocked_on="2019-05-02"))
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        stored = fresh(item)
        self.assertEqual(stored.stocked_on, date(2019, 5, 2))
        self.assertFalse(stored.is_new(TODAY))
        changed = [record.diff_against(record.prev_record).changed_fields
                   for record in stored.history.all()
                   if record.prev_record is not None]
        self.assertIn(["stocked_on"], changed)

    def test_a_later_movement_keeps_the_date(self) -> None:
        item = create_item(self.kl, article_number="S-4", name="Probe",
                           size=Decimal("10"), unit="mg", quantity=5,
                           stocked_on=date(2020, 1, 1))
        fill(self.kl, item, count=1)
        self.assertEqual(fresh(item).stocked_on, date(2020, 1, 1))

    def test_stock_entry_in_the_future(self) -> None:
        """Scenario: Stock entry in the future."""
        item = self.item("S-5")
        before = fresh(item).stocked_on
        response = self.client.post(item_url(item, "edit"), edit_data(
            fresh(item), stocked_on="2026-11-05"))
        self.refused(response, "stocked_on")
        self.assertEqual(fresh(item).stocked_on, before)

    def test_the_page_history_shows_state_and_date(self) -> None:
        item = self.item("S-7")
        self.client.post(item_url(item, "edit"), edit_data(
            fresh(item), status="discontinued", stocked_on="2024-03-01"))
        history = page(self.client.get(item_url(item))).find(
            "ul", "lab-history").text()
        for shown in ("Status", "auslaufend", "aktiv", "Im Bestand seit",
                      "01.03.2024", "02.01.2019"):
            with self.subTest(shown=shown):
                self.assertIn(shown, history)

    def test_new_item_form_takes_a_date(self) -> None:
        response = self.client.post(NEW_ITEM, {
            "article_number": "", "name": "Altbestand", "category": "",
            "size": "10", "unit": "mg", "quantity": "3",
            "stocked_on": "2021-06-01", "note": ""})
        item = Item.objects.get(name="Altbestand")
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        self.assertEqual(item.stocked_on, date(2021, 6, 1))

    def test_setting_a_size_aside(self) -> None:
        """Scenario: Setting a size aside."""
        item = self.with_mean_quarter(self.item("S-6", quantity=5), 4)
        self.client.post(item_url(item, "edit"), edit_data(
            fresh(item), status="not_needed"))
        stored = fresh(item)
        self.assertEqual(stored.status, "not_needed")
        changed = [record.diff_against(record.prev_record).changed_fields
                   for record in stored.history.all()
                   if record.prev_record is not None]
        self.assertIn(["status"], changed)
        self.assertEqual(self.consumption(item).level, "dormant")
        self.assertEqual(field_value(page(self.client.get(
            item_url(item, "edit"))), "status"), "not_needed")


class ListTests(InventoryCase):

    def rows(self, query: str = "") -> tuple[list[str], list[dict]]:
        return table(page(self.client.get(LIST + query)))

    def leveled(self) -> dict[str, Item]:
        """Items at the levels ok (two), low and dormant."""
        made = {
            "OK-1": self.with_mean_quarter(self.item("OK-1", quantity=9), 4),
            "OK-2": self.with_mean_quarter(self.item("OK-2", quantity=9), 4),
            "LO-1": self.with_mean_quarter(self.item("LO-1", quantity=3), 4),
            "DO-1": self.with_mean_quarter(self.item("DO-1", quantity=3), 4),
        }
        Item.objects.filter(pk=made["DO-1"].pk).update(
            status="discontinued")
        return made

    def test_legend_with_counts(self) -> None:
        """Scenario: Legend with counts."""
        self.leveled()
        root = page(self.client.get(LIST + "?q=xyz"))
        legend = root.find("dl", "level-legend")
        parts = [child for child in legend.children
                 if isinstance(child, Element)]
        counts = {}
        for term, definition in zip(parts[::2], parts[1::2]):
            level = next(c[6:] for c in term.classes
                         if c.startswith("level-"))
            counts[level] = int(definition.find("span", "count")
                                .text().strip("()"))
            self.assertEqual(term.find("a").get("href"),
                             f"{LIST}?stock={level}")
            self.assertEqual(term.text(), LEVELS[level])
        self.assertEqual(counts, {"out": 0, "critical": 0, "low": 1,
                                  "watch": 0, "ok": 2, "undelivered": 0,
                                  "dormant": 1})
        self.assertEqual([next(c[6:] for c in term.classes
                               if c.startswith("level-"))
                          for term in legend.find_all("dt")],
                         list(counts))

    def test_one_level_exactly(self) -> None:
        """Scenario: One level exactly."""
        for article, quantity in (("A-0", 0), ("A-1", 1), ("A-2", 3)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        header, rows = self.rows("?stock=critical")
        self.assertEqual([row[header[0]].text() for row in rows], ["A-1"])
        header, rows = self.rows("?stock=bogus")
        self.assertEqual(len(rows), 3)
        root = page(self.client.get(LIST + "?stock=critical"))
        form = root.find("form", "lab-filters")
        self.assertEqual(form.find("input", name="stock").get("value"),
                         "critical")

    def test_urgent_items_first(self) -> None:
        """Scenario: Urgent items first."""
        made = self.leveled()
        self.with_mean_quarter(self.item("WA-1", quantity=5), 4)
        self.with_mean_quarter(self.item("OU-1", quantity=0), 4)
        self.item("UN-1", quantity=2)
        header, rows = self.rows("?sort=urgency")
        stock = [next(c[6:] for c in row["Bestand"].classes
                      if c.startswith("level-")) for row in rows]
        self.assertEqual(stock, ["out", "low", "watch", "ok", "ok",
                                 "undelivered", "dormant"])
        self.assertTrue(made)

    def test_the_level_filter_keeps_its_urgent_choices(self) -> None:
        root = page(self.client.get(LIST))
        options = [option.get("value") for option in root.find(
            "select", name="level").find_all("option")]
        self.assertEqual(options, ["", "out", "critical", "low", "watch"])

    def test_new_items_marked(self) -> None:
        """Scenario: New items marked."""
        self.item("N-1", stocked_on=date(2026, 2, 1))
        self.item("N-2", stocked_on=date(2025, 12, 31))
        self.item("N-3", quantity=0, stocked_on=None)
        header, rows = self.rows()
        marks = {row[header[0]].text(): row[header[1]].find(
            "sup", "mark-new") for row in rows}
        self.assertEqual(marks["N-1"].text(), "neu")
        self.assertIsNone(marks["N-2"])
        self.assertIsNone(marks["N-3"])

    def test_projected_cells(self) -> None:
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        self.with_mean_quarter(self.item("P-2", quantity=3), 4)
        header, rows = self.rows()
        by_article = {row[header[0]].text(): row for row in rows}
        for column in ("Ø Quartal", "Ø Jahr", "Reichweite"):
            with self.subTest(column=column):
                cell = by_article["P-1"][column]
                self.assertIn("projected", cell.classes)
                self.assertEqual(cell.get("title"), PROJECTED)
                self.assertNotIn("projected", by_article["P-2"][column]
                                 .classes)


class PageTests(InventoryCase):

    def test_a_discontinued_size(self) -> None:
        """Scenario: A discontinued size."""
        item = self.item("D-1", quantity=4, stocked_on=date(2024, 3, 1))
        Item.objects.filter(pk=item.pk).update(status="discontinued")
        root = page(self.client.get(item_url(item)))
        text = root.find("dl", "metadata").text()
        self.assertIn("auslaufend", text)
        self.assertIn("01.03.2024", text)
        stock = root.find(cls="level-dormant")
        self.assertIn("ruhend", stock.text())
        self.assertIn("4", stock.text())
        self.assertIn("Ruhend, keine Prognose.", root.text())

    def test_the_heading_marks_a_new_item(self) -> None:
        item = self.item("N-1", stocked_on=date(2026, 3, 1))
        self.assertEqual(page(self.client.get(item_url(item))).find(
            "h1").find("sup", "mark-new").text(), "neu")

    def test_an_active_item_shows_no_status(self) -> None:
        item = self.item("A-1")
        self.assertNotIn("Status", page(self.client.get(
            item_url(item))).find("dl", "metadata").text())


class PlanningTests(PlanningCase):

    def test_a_dormant_size_plans_nothing(self) -> None:
        """Scenario: A dormant size plans nothing."""
        self.planned_item("NV-1", "1", "mg", 10)
        gone = self.planned_item("NV-1", "5", "mg", 0)
        Item.objects.filter(pk=gone.pk).update(status="discontinued")
        found = self.forecast("NV-1")
        self.assertEqual(int(found.runway), 60)
        self.assertEqual(int(found.slack), 11)
        entry = found.entry(fresh(gone))
        self.assertIsNone(entry.runway_on_hand)
        self.assertIsNone(entry.model)

    def test_a_dormant_size_does_not_choose_the_bulk_unit(self) -> None:
        """Scenario: A dormant size does not choose the bulk unit."""
        alone = self.planned_item("NV-2", "1", "umol", 10)
        self.lot("NV-2", "umol", "100")
        without = self.forecast("NV-2")
        gone = self.planned_item("NV-2", "1", "mg", 0)
        Item.objects.filter(pk=gone.pk).update(status="discontinued")
        found = self.forecast("NV-2")
        self.assertEqual(found.bulk_unit, "umol")
        self.assertFalse(found.unconvertible)
        self.assertAlmostEqual(found.runway, without.runway, places=3)
        self.assertTrue(alone)

    def test_an_article_of_dormant_sizes_has_no_forecast(self) -> None:
        gone = self.planned_item("NV-3", "1", "mg", 10)
        Item.objects.filter(pk=gone.pk).update(status="not_needed")
        self.assertIsNone(self.forecast("NV-3"))
