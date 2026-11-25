"""Tests of the item, batch, vessel and delivery note pages (end-product-
inventory: Item page, Batch page, Vessel page, Delivery list)."""

from collections import Counter
from datetime import date
from decimal import Decimal

from inventory.bookings import (book_note, correct, correct_vessel, reverse,
                                reverse_historical, transfer, withdraw)

from . import make_batch, make_task, make_vessel, page, past
from .collection_support import accept
from .inventory_support import (MICRO, InventoryCase, batch_url, cells,
                                delivery_line, has_amount, has_number,
                                historical_line, item_url, ledger,
                                movement_url, note_url, num, vessel_ledger,
                                vessel_url)
from .journal_support import entry_of, make_notebook

QUARTERS = [(year, quarter) for year in (2024, 2025, 2026)
            for quarter in (1, 2, 3, 4)]


class PageCase(InventoryCase):

    def show(self, path: str):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response)


class ItemHeadTests(PageCase):

    def test_the_heading_and_the_record(self) -> None:
        item = self.item("CH-0012", name="Zimtsäure", size="2.5",
                         unit="mg", quantity=7, category="Endprodukt",
                         note="Zeile eins")
        root = self.show(item_url(item))
        heading = root.find("h1").text()
        self.assertIn("CH-0012", heading)
        self.assertIn("Zimtsäure", heading)
        text = root.text()
        for expected in ("Endprodukt", "Zeile eins"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "2,5", "mg"), text)
        hrefs = [a.get("href") for a in root.find_all("a")]
        self.assertIn("/lab/registry/substances/cinnamic-acid/", hrefs)
        self.assertNotIn("/compounds/cinnamic-acid/", hrefs)

    def test_the_substance_is_named_by_language(self) -> None:
        item = self.item("CH-0012")
        self.assertIn("(E)-Zimtsäure", self.show(item_url(item)).text())
        accept(language="en")
        self.assertIn("(E)-Cinnamic acid",
                      self.show(item_url(item)).text())

    def test_the_figures(self) -> None:
        item = self.means_item("CH-0012", name="Zimtsäure")
        text = self.show(item_url(item)).text()
        self.assertTrue(has_number(text, "4,5"), text)
        self.assertTrue(has_number(text, "0,7"), text)
        self.assertRegex(text, r"(?<![\d,.])18(,0)?(?![\d,])")
        self.assertTrue(has_number(text, "13"), text)

    def test_the_english_page(self) -> None:
        accept(language="en")
        item = self.means_item("CH-0012")
        text = self.show(item_url(item)).text()
        self.assertIn("4.5", text)
        self.assertIn("0.7", text)

    def test_an_unknown_item_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/items/9999/").status_code, 404)

    def test_an_item_keeps_a_history(self) -> None:
        item = self.item("CH-0012")
        text = self.show(item_url(item)).text()
        self.assertIn("Angelegt", text)
        self.assertIn("KL", text)


class ChartTests(PageCase):

    def chart_item(self, article: str = "CH-0012"):
        item = self.item(article, name="Zimtsäure", quantity=40)
        self.enter(item, 2025, 1, 11)
        self.enter(item, 2025, 2, 13)
        self.enter(item, 2025, 3, 17)
        self.deliver(item, 7, date(2026, 2, 10), number="LS-1")
        self.deliver(item, 9, date(2026, 8, 20), number="LS-2")
        return item

    EXPECTED = {(2024, 1): 0, (2024, 2): 0, (2024, 3): 0, (2024, 4): 0,
                (2025, 1): 11, (2025, 2): 13, (2025, 3): 17, (2025, 4): 0,
                (2026, 1): 7, (2026, 2): 0, (2026, 3): 9, (2026, 4): 0}

    def bars(self, root) -> list[str]:
        svg = root.find("svg")
        self.assertIsNotNone(svg, "the page draws no chart")
        return [t.text() for t in svg.find_all("title")
                if t.parent is not svg]

    def test_chart_and_ledger(self) -> None:
        """Scenario: Chart and ledger."""
        root = self.show(item_url(self.chart_item()))
        titles = self.bars(root)
        self.assertEqual(len(titles), 12)
        for (year, _), total in sorted(self.EXPECTED.items()):
            matching = [t for t in titles
                        if str(year) in t and has_number(t, str(total))]
            self.assertTrue(matching, f"no bar for {year}: {total}")
            titles.remove(matching[0])
        self.assertEqual(titles, [])
        kinds = [kind for kind, _ in ledger(root)]
        self.assertEqual(kinds, ["delivery", "delivery", "opening"])

    def test_the_bars_have_distinct_titles(self) -> None:
        titles = self.bars(self.show(item_url(self.chart_item())))
        self.assertEqual(len(set(titles)), 12)

    def test_the_table_lists_the_same_values(self) -> None:
        root = self.show(item_url(self.chart_item()))
        grids = [t for t in root.find_all("table")
                 if len([r for r in t.find_all("tr") if r.find("td")]) == 12]
        self.assertEqual(len(grids), 1)
        triples = []
        for row in grids[0].find_all("tr"):
            if not row.find("td"):
                continue
            last = [num(c) or Decimal(0) for c in cells(row)[-3:]]
            triples.append(tuple(int(v) for v in last))
        expected = [(0, 0, 0)] * 4 + [(11, 0, 11), (13, 0, 13), (17, 0, 17),
                                      (0, 0, 0), (0, 7, 7), (0, 0, 0),
                                      (0, 9, 9), (0, 0, 0)]
        self.assertEqual(Counter(triples), Counter(expected))

    def test_the_mean_is_drawn_as_a_line(self) -> None:
        with_mean = self.show(item_url(self.chart_item("CH-0012")))
        item = self.item("CH-0013", quantity=40)
        self.enter_year(item, 2026, 0)
        without = self.show(item_url(item))
        tags = ("line", "polyline", "path")
        self.assertGreater(len(with_mean.find("svg").find_all(tags)),
                           len(without.find("svg").find_all(tags)))
        self.assertEqual(len(self.bars(without)), 12)

    def test_an_item_without_data_still_has_twelve_bars(self) -> None:
        root = self.show(item_url(self.item("CH-0014")))
        self.assertEqual(len(self.bars(root)), 12)


class LedgerTests(PageCase):

    def booked(self):
        item = self.item("CH-0012", quantity=10)
        filling = self.filling(item, 4, note="Charge 7")
        delivery = self.deliver_movement(item, 2)
        correction = correct(self.kl, item, count=9, note="gezählt")
        return item, filling, delivery, correction

    def test_the_movements_come_newest_first(self) -> None:
        item, *_ = self.booked()
        kinds = [kind for kind, _ in ledger(self.show(item_url(item)))]
        self.assertEqual(kinds, ["correction", "delivery", "filling",
                                 "opening"])

    def test_booking_order_decides_not_the_date(self) -> None:
        item = self.item("CH-0012", quantity=10)
        self.deliver(item, 1, date(2026, 10, 15), number="LS-LATE")
        self.deliver(item, 2, date(2026, 8, 1), number="LS-EARLY")
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["delivery", "delivery", "opening"])
        self.assertIn("LS-EARLY", rows[0][1].text())
        self.assertIn("LS-LATE", rows[1][1].text())

    def test_a_row_shows_the_booking(self) -> None:
        item = self.item("CH-0012", quantity=10)
        self.deliver(item, 2, date(2026, 10, 15), number="LS-9",
                     recipient="Produktion", note="Eilig", user=self.ae)
        _, row = ledger(self.show(item_url(item)))[0]
        text = row.text()
        for expected in ("15.10.2026", "AE", "LS-9", "Produktion", "Eilig"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_number(text, "2"), text)
        self.assertTrue(has_number(text, "8"), text)

    def test_notes_and_counts_of_the_other_kinds(self) -> None:
        item, *_ = self.booked()
        rows = dict(ledger(self.show(item_url(item))))
        self.assertIn("gezählt", rows["correction"].text())
        self.assertTrue(has_number(rows["correction"].text(), "9"))
        self.assertIn("Charge 7", rows["filling"].text())
        self.assertTrue(has_number(rows["filling"].text(), "14"))
        self.assertTrue(has_number(rows["opening"].text(), "10"))
        self.assertIn("KL", rows["opening"].text())

    def test_a_reversed_movement_is_marked(self) -> None:
        item, filling, delivery, _ = self.booked()
        reverse(self.kl, delivery, note="falsch gebucht")
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "correction", "delivery", "filling",
                          "opening"])
        by_kind = {kind: row for kind, row in rows}
        self.assertIn("storniert", by_kind["delivery"].text())
        self.assertNotIn("storniert", by_kind["filling"].text())
        self.assertIn("falsch gebucht", by_kind["reversal"].text())

    def test_the_actions_of_a_signed_in_user(self) -> None:
        item, filling, delivery, correction = self.booked()
        self.assertFalse(self.actions(item))
        self.client.force_login(self.kl)
        links = self.actions(item)
        self.assertEqual(links, {
            "Abgabe buchen": f"/lab/inventory/deliveries/new/?item={item.pk}",
            "Abfüllen": item_url(item, "fill"),
            "Bestand korrigieren": item_url(item, "correct"),
            "Verbrauch nachtragen": item_url(item, "consumption"),
            "Bearbeiten": item_url(item, "edit")})
        reversals = self.reversals(item)
        self.assertEqual(
            sorted(reversals), sorted([movement_url(filling),
                                       movement_url(delivery)]))

    def test_a_reversed_movement_offers_no_reversal(self) -> None:
        item, filling, delivery, _ = self.booked()
        reverse(self.kl, delivery, note="falsch")
        self.client.force_login(self.kl)
        self.assertEqual(self.reversals(item), [movement_url(filling)])

    def test_english_links(self) -> None:
        accept(language="en")
        item, *_ = self.booked()
        self.client.force_login(self.kl)
        self.assertEqual(
            set(self.actions(item)),
            {"Book delivery", "Fill", "Correct count", "Enter consumption",
             "Edit"})

    def actions(self, item) -> dict[str, str]:
        wanted = {"Abgabe buchen", "Abfüllen", "Bestand korrigieren",
                  "Verbrauch nachtragen", "Bearbeiten", "Book delivery",
                  "Fill", "Correct count", "Enter consumption", "Edit"}
        root = self.show(item_url(item))
        return {a.text(): a.get("href") for a in root.find_all("a")
                if a.text() in wanted}

    def reversals(self, item) -> list[str]:
        root = self.show(item_url(item))
        return [a.get("href") for a in root.find_all("a")
                if a.get("href", "").endswith("/reverse/")
                and "/movements/" in a.get("href", "")]


class ItemHistoryTests(PageCase):

    def test_a_change_is_in_the_history(self) -> None:
        item = self.item("CH-0012", note="alt")
        self.client.force_login(self.ae)
        self.client.post(item_url(item, "edit"), {
            "category": "", "note": "neu", "status": "active",
            "stocked_on": "2019-01-02"})
        text = self.show(item_url(item)).text()
        for expected in ("alt", "neu", "AE", "KL", "Angelegt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertLess(text.find("neu"), text.rfind("Angelegt"))


class VesselPageTests(PageCase):

    def filled(self):
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50", number="B-1",
                             location="Kühlraum", date=date(2026, 10, 1),
                             note="Rest")
        from inventory.bookings import fill
        fill(self.kl, item, count=5, vessel=vessel)
        return item, vessel

    def test_the_record(self) -> None:
        _, vessel = self.filled()
        root = self.show(vessel_url(vessel))
        self.assertIn(f"B-1 #{vessel.pk}", root.find("h1").text())
        text = root.text()
        for expected in ("CH-0012", "B-1", "Kühlraum", "Rest", "Endprodukt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "42,592", "mg"), text)
        self.assertNotIn("aufgebraucht", text)
        hrefs = [a.get("href") for a in root.find_all("a")]
        self.assertIn(batch_url(vessel.batch), hrefs)
        self.assertIn("/lab/registry/substances/cinnamic-acid/", hrefs)

    def test_the_kind_of_a_flask(self) -> None:
        flask = self.vessel("CH-0012", "g", "2", flask=True)
        self.assertIn("Kolben", self.show(vessel_url(flask)).text())

    def test_the_substance_the_source_and_the_kind(self) -> None:
        self.item("CH-0012")
        commercial = self.vessel("acetophenone", "mg", "5", source="bought",
                                 supplier="Sigma")
        root = self.show(vessel_url(commercial))
        self.assertIn("/lab/registry/substances/acetophenone/",
                      [a.get("href") for a in root.find_all("a")])
        self.assertIn("Handelschemikalie", root.text())
        self.assertNotRegex(root.text(), r"[A-Z]{2}-\d{4}")

    def test_an_intermediate(self) -> None:
        vessel = self.vessel("acetophenone", "mg", "5", source="made")
        self.assertIn("Zwischenprodukt", self.show(vessel_url(vessel)).text())

    def test_vessel_page_after_a_filling(self) -> None:
        """Scenario: Vessel page after a filling."""
        item, vessel = self.filled()
        rows = vessel_ledger(self.show(vessel_url(vessel)))
        self.assertEqual([kind for kind, _ in rows], ["filling", "opening"])
        newest = rows[0][1]
        self.assertIn(item_url(item),
                      [a.get("href") for a in newest.find_all("a")])
        text = newest.text()
        self.assertTrue(has_number(text, "7,408"), text)
        self.assertTrue(has_number(text, "42,592"), text)
        self.assertIn("KL", text)
        opening = rows[1][1].text()
        self.assertTrue(has_number(opening, "50"), opening)

    def test_vessel_page_after_a_transfer(self) -> None:
        """Scenario: Vessel page after a transfer."""
        flask = self.vessel("CH-0012", "g", "2", number="KL0412",
                            flask=True)
        out, into = transfer(self.kl, flask, amount=Decimal("1.5"),
                             location="Kühlschrank 2")
        rows = vessel_ledger(self.show(vessel_url(flask)))
        self.assertEqual([kind for kind, _ in rows],
                         ["transfer_out", "opening"])
        self.assertIn(vessel_url(into.vessel),
                      [a.get("href") for a in rows[0][1].find_all("a")])
        back = vessel_ledger(self.show(vessel_url(into.vessel)))
        self.assertEqual([kind for kind, _ in back], ["transfer_in"])
        self.assertIn(vessel_url(flask),
                      [a.get("href") for a in back[0][1].find_all("a")])
        self.assertEqual(out.transferred, into)

    def test_a_withdrawal_names_its_task_and_step(self) -> None:
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1))
        vessel = self.vessel("CH-0012", "g", "2")
        withdraw(self.kl, vessel, task_step=plain.steps.get(position=2),
                 amount=Decimal("0.5"))
        (row,) = [row for kind, row in vessel_ledger(
            self.show(vessel_url(vessel))) if kind == "withdrawal"]
        self.assertIn(f"/lab/tasks/{plain.number}/",
                      [a.get("href") for a in row.find_all("a")])
        self.assertIn(plain.number, row.text())
        self.assertIn("Stufe 2", row.text())

    def test_a_reversal_names_the_movement_it_reverses(self) -> None:
        from inventory.bookings import reverse_withdrawal
        plain = make_task(self.kl, "Aspirin", steps=1, started=past(1))
        vessel = self.vessel("CH-0012", "g", "2")
        taken = withdraw(self.kl, vessel, task_step=plain.steps.get(),
                         amount=Decimal("0.5"))
        reverse_withdrawal(self.kl, taken)
        rows = vessel_ledger(self.show(vessel_url(vessel)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "withdrawal", "opening"])
        self.assertIn("Entnahme", rows[0][1].text())

    def test_a_remainder_is_listed(self) -> None:
        from inventory.bookings import write_off_flasks
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        from .task_support import make_product_batch
        flask = make_product_batch(task, "2", "g", flask=True
                                   ).vessels.get()
        write_off_flasks(self.kl, task)
        rows = vessel_ledger(self.show(vessel_url(flask)))
        self.assertEqual([kind for kind, _ in rows],
                         ["remainder", "opening"])
        self.assertIn("aufgebraucht", self.show(vessel_url(flask)).text())

    def test_a_used_up_vessel_is_marked(self) -> None:
        vessel = self.vessel("CH-0012", "mg", "5")
        correct_vessel(self.kl, vessel, amount=Decimal("0"), note="leer")
        text = self.show(vessel_url(vessel)).text()
        self.assertIn("aufgebraucht", text)

    def test_the_amount_shows_in_the_unit_of_the_vessel(self) -> None:
        vessel = self.vessel("X-1", "mmol", "2.5")
        self.assertTrue(has_amount(self.show(vessel_url(vessel)).text(),
                                   "2,5", "mmol"))

    def test_corrections_and_reversals_are_listed(self) -> None:
        item, vessel = self.filled()
        correct_vessel(self.kl, vessel, amount=Decimal("40"),
                       note="nachgewogen")
        reverse(self.kl, item.movements.get(kind="filling"), note="doppelt")
        rows = vessel_ledger(self.show(vessel_url(vessel)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "correction", "filling", "opening"])
        self.assertIn("nachgewogen", rows[1][1].text())

    def test_the_actions_of_a_signed_in_user(self) -> None:
        vessel = self.vessel()
        root = self.show(vessel_url(vessel))
        self.assertIsNone(root.find("a", href=vessel_url(vessel, "correct")))
        self.assertIsNone(root.find("a", href=vessel_url(vessel, "edit")))
        self.client.force_login(self.kl)
        root = self.show(vessel_url(vessel))
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=vessel_url(vessel, "correct"))], ["Korrigieren"])
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=vessel_url(vessel, "edit"))], ["Bearbeiten"])

    def test_the_vessel_keeps_a_history(self) -> None:
        vessel = self.vessel()
        self.assertIn("Angelegt", self.show(vessel_url(vessel)).text())

    def test_an_unknown_vessel_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/vessels/9999/").status_code,
            404)


class BatchPageTests(PageCase):

    def test_a_made_batch(self) -> None:
        make_notebook("AE-1", self.kl)
        self.item("CH-0012", name="Zimtsäure")
        task = make_task(self.kl, "CH-0012", steps=2, started=past(1))
        step = task.steps.get(position=2)
        batch = make_batch(
            self.kl, "CH-0012", number="KL0412", date=date(2026, 10, 30),
            note="Rest", task_step=step, journal_entry=entry_of("AE-1/9"),
            yield_amount="2", yield_unit="g")
        root = self.show(batch_url(batch))
        self.assertIn("KL0412", root.find("h1").text())
        text = root.text()
        for expected in ("CH-0012", "Zimtsäure", "hergestellt", "AE-1/9",
                         "30.10.2026", "Rest"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertRegex(text, rf"{task.number}\W+Stufe 2")
        self.assertTrue(has_amount(text, "2", "g"), text)
        hrefs = [a.get("href") for a in root.find_all("a")]
        for href in ("/lab/registry/substances/cinnamic-acid/",
                     "/lab/journal/AE-1/", f"/lab/tasks/{task.number}/"):
            with self.subTest(href=href):
                self.assertIn(href, hrefs)

    def test_a_bought_batch(self) -> None:
        batch = make_batch(
            self.kl, "acetophenone", source="bought", supplier="Sigma",
            supplier_article_number="C80857", supplier_batch="MKCK1234",
            date=date(2026, 11, 2))
        root = self.show(batch_url(batch))
        self.assertIn("MKCK1234", root.find("h1").text())
        text = root.text()
        for expected in ("gekauft", "Sigma", "C80857", "MKCK1234",
                         "02.11.2026"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotRegex(text, r"[A-Z]{2}-\d{4}")

    def test_a_field_without_a_value_shows_a_dash(self) -> None:
        batch = make_batch(self.kl, "acetophenone", number="KL1")
        self.assertIn("–", self.show(batch_url(batch)).text())

    def test_a_batch_without_a_number_shows_its_id(self) -> None:
        batch = make_batch(self.kl, "acetophenone", source="bought")
        self.assertIn(f"#{batch.pk}", self.show(batch_url(batch)).find(
            "h1").text())

    def test_the_vessels_open_ones_first_then_by_id(self) -> None:
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        used = make_vessel(self.kl, batch, unit="mg", amount="0",
                           location="A")
        first = make_vessel(self.kl, batch, unit="g", amount="1",
                            location="B")
        second = make_vessel(self.kl, batch, unit="mg", amount="30",
                             flask=True)
        root = self.show(batch_url(batch))
        order = [a.get("href") for a in root.find("main").find_all("a")
                 if a.get("href", "").startswith("/lab/inventory/vessels/")
                 and a.get("href").rstrip("/").split("/")[-1].isdigit()]
        self.assertEqual(order, [vessel_url(first), vessel_url(second),
                                 vessel_url(used)])
        rows = {a.text(): a.closest("tr") for a in root.find_all("a")
                if a.get("href") in order}
        self.assertEqual(sorted(rows), sorted(
            f"#{v.pk}" for v in (used, first, second)))
        self.assertIn("aufgebraucht", rows[f"#{used.pk}"].text())
        self.assertNotIn("aufgebraucht", rows[f"#{first.pk}"].text())
        self.assertIn("Kolben", rows[f"#{second.pk}"].text())
        self.assertIn("B", rows[f"#{first.pk}"].text())
        self.assertTrue(has_amount(rows[f"#{first.pk}"].text(), "1", "g"))

    def test_where_a_batch_went(self) -> None:
        """Scenario: Where a batch went."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        flask = make_vessel(self.kl, batch, unit="mg", amount="2000",
                            flask=True)
        from inventory.bookings import fill
        fill(self.kl, item, count=5, vessel=flask)
        _out, into = transfer(self.kl, flask, amount=Decimal("1992.592"),
                              location="Kühlschrank 2")
        root = self.show(batch_url(batch))
        order = [a.get("href") for a in root.find("main").find_all("a")
                 if a.get("href") in (vessel_url(flask),
                                      vessel_url(into.vessel))]
        self.assertEqual(order[:2], [vessel_url(into.vessel),
                                     vessel_url(flask)])
        flask_row = next(a for a in root.find_all("a")
                         if a.get("href") == vessel_url(flask)
                         ).closest("tr")
        self.assertIn("aufgebraucht", flask_row.text())
        rows = [a.closest("tr") for a in root.find_all("a")
                if a.get("href") == item_url(item)]
        filling = next(row for row in rows if row is not None
                       and f"#{flask.pk}" in row.text())
        self.assertTrue(has_number(filling.text(), "5"), filling.text())
        self.assertIn(f"#{flask.pk}", filling.text())

    def test_fillings_newest_first_and_a_reversed_one_marked(self) -> None:
        first = self.item("CH-0012", size="10", unit="umol", quantity=0)
        second = self.item("CH-0012", size="50", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "g", "2")
        from inventory.bookings import fill
        one = fill(self.kl, first, count=1, vessel=vessel,
                   date=date(2026, 10, 1))
        fill(self.kl, second, count=1, vessel=vessel,
             date=date(2026, 10, 20))
        reverse(self.kl, one, note="doppelt")
        root = self.show(batch_url(vessel.batch))
        rows = [a.closest("tr") for a in root.find("main").find_all("a")
                if a.get("href") in (item_url(first), item_url(second))]
        rows = [r for r in rows
                if r is not None and f"#{vessel.pk}" in r.text()]
        hrefs = [[a.get("href") for a in r.find_all("a")
                  if a.get("href") in (item_url(first), item_url(second))][0]
                 for r in rows]
        self.assertEqual(hrefs, [item_url(second), item_url(first)])
        self.assertNotIn("storniert", rows[0].text())
        self.assertIn("storniert", rows[1].text())

    def test_the_actions_of_a_signed_in_user(self) -> None:
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        root = self.show(batch_url(batch))
        self.assertIsNone(root.find("a", href=batch_url(batch, "edit")))
        self.assertIsNone(root.find(
            "a", href=batch_url(batch, "vessels/new")))
        self.client.force_login(self.kl)
        root = self.show(batch_url(batch))
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=batch_url(batch, "edit"))], ["Bearbeiten"])
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=batch_url(batch, "vessels/new"))], ["Neues Gefäß"])

    def test_the_batch_keeps_a_history(self) -> None:
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.assertIn("Angelegt", self.show(batch_url(batch)).text())

    def test_the_task_and_the_batch_link_each_other(self) -> None:
        """production-planning, Batches of tasks (a batch from a step)."""
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = make_batch(self.kl, "CH-0012", number="KL0412",
                           task_step=task.steps.get())
        self.assertIn(f"/lab/tasks/{task.number}/", [
            a.get("href") for a in self.show(batch_url(batch)).find_all("a")])
        self.assertIn(batch_url(batch), [
            a.get("href") for a in self.show(
                f"/lab/tasks/{task.number}/").find_all("a")])

    def test_a_batch_without_a_step_links_no_task(self) -> None:
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.assertNotIn(f"/lab/tasks/{task.number}/", [
            a.get("href") for a in self.show(batch_url(batch)).find_all("a")])
        self.assertNotIn(batch_url(batch), [
            a.get("href") for a in self.show(
                f"/lab/tasks/{task.number}/").find_all("a")])

    def test_an_unknown_batch_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/batches/9999/").status_code,
            404)


class ItemPageVesselTests(PageCase):
    """Requirement: Item page (its bulk: the open vessels of its
    substance, each with its batch and amount and linking to its
    page)."""

    def test_the_open_vessels_with_their_batches(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        open_one = self.vessel("CH-0012", "mg", "50", number="B-7")
        flask = self.vessel("CH-0012", "g", "2", number="B-8", flask=True)
        used = self.vessel("CH-0012", "mg", "0", number="B-USED")
        other = self.vessel("CH-0013", "mg", "20", number="B-OTHER")
        root = self.show(item_url(item))
        hrefs = [a.get("href") for a in root.find_all("a")]
        for vessel in (open_one, flask):
            with self.subTest(vessel=vessel.pk):
                self.assertIn(vessel_url(vessel), hrefs)
        for vessel in (used, other):
            with self.subTest(vessel=vessel.pk):
                self.assertNotIn(vessel_url(vessel), hrefs)
        text = root.text()
        self.assertIn("B-7", text)
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertTrue(has_amount(text, "2", "g"), text)


class NotePageTests(PageCase):

    def test_a_current_note(self) -> None:
        first = self.item("CH-0012", name="Zimtsäure", quantity=9)
        second = self.item("X-1", name="Anderes", size="2.5", unit="mg",
                           quantity=9)
        note = book_note(self.kl, date=date(2026, 10, 15), number="LS-9",
                         recipient="Produktion", note="Eilig",
                         lines=[delivery_line(first, 2),
                                delivery_line(second, 3)])
        root = self.show(note_url(note))
        self.assertIn("LS-9", root.find("h1").text())
        text = root.text()
        for expected in ("15.10.2026", "Produktion", "Eilig", "CH-0012",
                         "Zimtsäure", "X-1", "Anderes", "Abgabe", "KL",
                         "Angelegt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "10", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "2,5", "mg"), text)
        self.assertNotIn("nachgetragen", text)

    def test_a_note_without_a_number_is_shown_by_its_id(self) -> None:
        item = self.item(quantity=9)
        note = self.deliver(item, 1)
        self.assertIn(f"#{note.pk}", self.show(note_url(note)).find(
            "h1").text())

    def test_a_historical_note(self) -> None:
        item = self.item(quantity=9)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         number="ALT-1", lines=[historical_line(item, 4)])
        text = self.show(note_url(note)).text()
        self.assertIn("nachgetragen", text)
        self.assertIn("12.03.2025", text)
        self.assertNotIn("Abgabe", text)
        reverse_historical(self.kl, note, note="doppelt erfasst")
        text = self.show(note_url(note)).text()
        self.assertIn("storniert", text)

    def test_an_unknown_note_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/deliveries/9999/").status_code,
            404)
