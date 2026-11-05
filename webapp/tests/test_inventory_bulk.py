"""Tests of the bulk lots and the filling from them (end-product-inventory:
Bulk lots, Filling from bulk)."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from inventory.bookings import (Refused, correct_lot, create_lot, fill,
                                reverse)
from inventory.figures import convert
from inventory.models import END_PRODUCTS, Lot, LotMovement

from . import build_index, compound, page, table
from .inventory_support import (LIST, MICRO, TODAY, InventoryCase, fresh,
                                has_amount, has_number, item_url, lot_url,
                                newest_movement, snapshot)

MW = Decimal("148.16")


class ConvertTests(SimpleTestCase):

    def test_units_of_one_kind_convert_by_their_factors(self) -> None:
        cases = [("1", "g", "mg", "1000"), ("2500", "mg", "g", "2.5"),
                 ("1", "mmol", "umol", "1000"),
                 ("500", "umol", "mmol", "0.5"),
                 ("3.5", "mg", "mg", "3.5"), ("2", "g", "g", "2"),
                 ("7", "umol", "umol", "7"), ("2", "mmol", "mmol", "2")]
        for amount, unit, to, want in cases:
            with self.subTest(unit=unit, to=to):
                self.assertEqual(
                    convert(Decimal(amount), unit, to, None), Decimal(want))

    def test_mass_and_amount_of_substance_convert_through_the_mass(
            self) -> None:
        cases = [("10", "umol", "mg", "1.4816"),
                 ("1", "mmol", "g", "0.14816"),
                 ("1", "mmol", "mg", "148.16"),
                 ("1000", "umol", "g", "0.14816"),
                 ("148.16", "mg", "mmol", "1"),
                 ("148.16", "mg", "umol", "1000"),
                 ("0.14816", "g", "mmol", "1")]
        for amount, unit, to, want in cases:
            with self.subTest(unit=unit, to=to):
                self.assertEqual(
                    convert(Decimal(amount), unit, to, MW), Decimal(want))

    def test_the_result_is_not_rounded(self) -> None:
        shown = convert(Decimal("1"), "mg", "umol", MW)
        self.assertAlmostEqual(float(shown), 1000 / 148.16, places=9)
        self.assertGreater(len(shown.as_tuple().digits), 6)

    def test_a_float_molar_mass_is_accepted(self) -> None:
        shown = convert(Decimal("10"), "umol", "mg", 148.16)
        self.assertAlmostEqual(float(shown), 1.4816, places=9)

    def test_without_a_molar_mass_the_kinds_do_not_convert(self) -> None:
        for unit, to in (("mg", "umol"), ("umol", "g"), ("g", "mmol"),
                         ("mmol", "mg")):
            for mass in (None, Decimal("0")):
                with self.subTest(unit=unit, to=to, mass=mass):
                    self.assertIsNone(convert(Decimal("5"), unit, to, mass))

    def test_the_mass_does_not_matter_within_a_kind(self) -> None:
        self.assertEqual(convert(Decimal("1"), "g", "mg", MW),
                         Decimal("1000"))


class LotTests(InventoryCase):

    def test_a_lot_keeps_its_fields(self) -> None:
        made = create_lot(
            self.kl, article_number="CH-0012", unit="mg",
            amount=Decimal("50"), batch="B-1", location="Kühlraum",
            made_on=date(2026, 10, 1), note="Rest")
        lot = Lot.objects.get(pk=made.pk)
        self.assertEqual(lot.inventory, END_PRODUCTS)
        self.assertEqual(
            (lot.article_number, lot.unit, lot.batch, lot.location,
             lot.made_on, lot.note),
            ("CH-0012", "mg", "B-1", "Kühlraum", date(2026, 10, 1), "Rest"))
        self.assertEqual(lot.amount, Decimal("50"))

    def test_batch_location_date_and_note_are_optional(self) -> None:
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("5"))
        lot = fresh(lot)
        self.assertEqual((lot.batch, lot.location, lot.note), ("", "", ""))
        self.assertIsNone(lot.made_on)

    def test_the_opening_amount_is_the_first_movement(self) -> None:
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("50"))
        movement = lot.movements.get()
        self.assertEqual(movement.kind, LotMovement.Kind.OPENING)
        self.assertEqual(movement.kind, "opening")
        self.assertEqual((movement.amount, movement.amount_after),
                         (Decimal("50"), Decimal("50")))
        self.assertEqual(movement.user, self.kl)
        self.assertEqual(movement.date, TODAY)
        self.assertIsNotNone(movement.booked_at)

    def test_the_opening_date_may_be_given(self) -> None:
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("50"), date=date(2026, 10, 1))
        self.assertEqual(lot.movements.get().date, date(2026, 10, 1))

    def test_the_four_units(self) -> None:
        units = {value for value, _ in Lot._meta.get_field("unit").choices}
        self.assertEqual(units, {"mg", "g", "umol", "mmol"})

    def test_amounts_are_kept_in_the_base_unit(self) -> None:
        cases = [("mg", "5", "5"), ("g", "1", "1000"), ("umol", "5", "5"),
                 ("mmol", "2", "2000"), ("g", "0.0015", "1.5")]
        for number, (unit, amount, base) in enumerate(cases):
            with self.subTest(unit=unit, amount=amount):
                lot = create_lot(
                    self.kl, article_number=f"L-{number}", unit=unit,
                    amount=Decimal(amount))
                lot = fresh(lot)
                self.assertEqual(lot.unit, unit)
                self.assertEqual(lot.amount, Decimal(base))
                self.assertEqual(lot.movements.get().amount_after,
                                 Decimal(base))

    def test_amounts_have_six_places(self) -> None:
        self.assertEqual(Lot._meta.get_field("amount").decimal_places, 6)
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("0.000001"))
        self.assertEqual(fresh(lot).amount, Decimal("0.000001"))

    def test_a_lot_of_zero_is_used_up_from_the_start(self) -> None:
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("0"))
        self.assertEqual(fresh(lot).amount, 0)

    def test_a_negative_amount_is_refused(self) -> None:
        before = snapshot()
        with self.assertRaises(Refused):
            create_lot(self.kl, article_number="CH-0012", unit="mg",
                       amount=Decimal("-1"))
        self.assertEqual(snapshot(), before)

    def test_a_lot_keeps_a_history(self) -> None:
        lot = create_lot(self.kl, article_number="CH-0012", unit="mg",
                         amount=Decimal("50"))
        self.assertEqual(lot.history.get().history_user, self.kl)


class LotCorrectionTests(InventoryCase):

    def test_correction_of_a_lot(self) -> None:
        """Scenario: Correction of a lot."""
        lot = self.lot(amount="50")
        movement = correct_lot(self.kl, lot, amount=Decimal("47.5"),
                               note="nachgewogen")
        self.assertEqual(fresh(lot).amount, Decimal("47.5"))
        newest = lot.movements.order_by("-pk").first()
        self.assertEqual(newest.pk, movement.pk)
        self.assertEqual(newest.kind, LotMovement.Kind.CORRECTION)
        self.assertEqual((newest.amount, newest.amount_after),
                         (Decimal("47.5"), Decimal("47.5")))
        self.assertEqual((newest.user, newest.note),
                         (self.kl, "nachgewogen"))
        self.assertEqual(newest.date, TODAY)

    def test_the_amount_is_in_the_unit_of_the_lot(self) -> None:
        lot = self.lot(unit="g", amount="1")
        correct_lot(self.kl, lot, amount=Decimal("0.5"), note="gewogen")
        self.assertEqual(fresh(lot).amount, Decimal("500"))

    def test_a_note_is_required(self) -> None:
        lot = self.lot()
        before = snapshot()
        with self.assertRaises(Refused):
            correct_lot(self.kl, lot, amount=Decimal("40"), note="")
        self.assertEqual(snapshot(), before)

    def test_a_negative_amount_is_refused(self) -> None:
        lot = self.lot()
        before = snapshot()
        with self.assertRaises(Refused):
            correct_lot(self.kl, lot, amount=Decimal("-1"), note="x")
        self.assertEqual(snapshot(), before)

    def test_a_lot_corrected_to_zero_is_used_up(self) -> None:
        lot = self.lot()
        correct_lot(self.kl, lot, amount=Decimal("0"), note="leer")
        self.assertEqual(fresh(lot).amount, 0)

    def test_the_date_may_be_given(self) -> None:
        lot = self.lot()
        movement = correct_lot(self.kl, lot, amount=Decimal("40"),
                               note="x", date=date(2026, 11, 1))
        self.assertEqual(movement.date, date(2026, 11, 1))


class FillingFromBulkTests(InventoryCase):

    def test_filling_with_conversion(self) -> None:
        """Scenario: Filling with conversion (the booking)."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=2)
        lot = self.lot("CH-0012", "mg", "50")
        movement = fill(self.kl, item, count=5, lot=lot)
        self.assertEqual(fresh(item).quantity, 7)
        self.assertEqual(fresh(lot).amount, Decimal("42.592"))
        taken = lot.movements.order_by("-pk").first()
        self.assertEqual(taken.kind, LotMovement.Kind.FILLING)
        self.assertEqual((taken.amount, taken.amount_after),
                         (Decimal("7.408"), Decimal("42.592")))
        self.assertEqual(taken.user, self.kl)
        movement = type(movement).objects.get(pk=movement.pk)
        self.assertEqual(movement.bulk_movement, taken)
        self.assertEqual((movement.kind, movement.count), ("filling", 5))

    def test_the_amount_may_be_named(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        movement = fill(self.kl, item, count=5, lot=lot,
                        amount=Decimal("7.4"))
        self.assertEqual(fresh(lot).amount, Decimal("42.6"))
        self.assertEqual(movement.bulk_movement.amount, Decimal("7.4"))

    def test_small_filling_from_a_lot_in_grams(self) -> None:
        """Scenario: Small filling from a lot in grams."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        lot = self.lot("CH-0012", "g", "1")
        fill(self.kl, item, count=1, lot=lot)
        self.assertEqual(fresh(lot).amount, Decimal("998.5184"))
        root = page(self.client.get(lot_url(lot)))
        self.assertTrue(has_amount(root.text(), "0,999", "g"), root.text())

    def test_a_named_amount_is_in_the_unit_of_the_lot(self) -> None:
        item = self.item("X-1", size="10", unit="mg", quantity=0)
        lot = self.lot("X-1", "g", "1")
        fill(self.kl, item, count=1, lot=lot, amount=Decimal("0.05"))
        self.assertEqual(fresh(lot).amount, Decimal("950"))

    def test_units_of_one_kind_need_no_molar_mass(self) -> None:
        item = self.item("X-1", size="10", unit="mg", quantity=0)
        lot = self.lot("X-1", "g", "1")
        fill(self.kl, item, count=5, lot=lot)
        self.assertEqual(fresh(lot).amount, Decimal("950"))
        item = self.item("X-2", size="2", unit="mmol", quantity=0)
        lot = self.lot("X-2", "umol", "10000")
        fill(self.kl, item, count=3, lot=lot)
        self.assertEqual(fresh(lot).amount, Decimal("4000"))

    def test_the_count_is_multiplied_by_the_size(self) -> None:
        item = self.item("CH-0012", size="2.5", unit="umol", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        fill(self.kl, item, count=3, lot=lot)
        self.assertEqual(fresh(lot).amount, Decimal("48.8888"))

    def test_the_proposal_rounds_half_up_to_six_places(self) -> None:
        self.use_index(build_index("de", [compound(
            "tie", name="Tie", mw=2.5, item_number="T-1")]))
        item = self.item("T-1", size="0.001", unit="umol", quantity=0)
        lot = self.lot("T-1", "mg", "1")
        movement = fill(self.kl, item, count=1, lot=lot)
        self.assertEqual(movement.bulk_movement.amount, Decimal("0.000003"))
        self.assertEqual(fresh(lot).amount, Decimal("0.999997"))

    def test_without_a_molar_mass_the_amount_is_required(self) -> None:
        item = self.item("X-1", size="10", unit="umol", quantity=0)
        lot = self.lot("X-1", "mg", "50")
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=2, lot=lot)
        self.assertEqual(snapshot(), before)
        fill(self.kl, item, count=2, lot=lot, amount=Decimal("3"))
        self.assertEqual(fresh(lot).amount, Decimal("47"))
        self.assertEqual(fresh(item).quantity, 2)

    def test_an_amount_above_the_lot_refuses_both(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "5")
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=5, lot=lot)
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, lot=lot, amount=Decimal("5.000001"))
        self.assertEqual(snapshot(), before)

    def test_the_whole_lot_may_be_taken(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "5")
        fill(self.kl, item, count=1, lot=lot, amount=Decimal("5"))
        self.assertEqual(fresh(lot).amount, 0)
        self.assertEqual(fresh(item).quantity, 1)

    def test_an_amount_that_rounds_to_zero_refuses_both(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "5")
        before = snapshot()
        for amount in ("0", "0.0000004", "-1"):
            with self.subTest(amount=amount), self.assertRaises(Refused):
                fill(self.kl, item, count=1, lot=lot,
                     amount=Decimal(amount))
        self.assertEqual(snapshot(), before)

    def test_a_proposal_that_rounds_to_zero_refuses_both(self) -> None:
        self.use_index(build_index("de", [compound(
            "light", name="Light", mw=0.001, item_number="T-2")]))
        item = self.item("T-2", size="0.001", unit="umol", quantity=0)
        lot = self.lot("T-2", "mg", "5")
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, lot=lot)
        self.assertEqual(snapshot(), before)

    def test_a_used_up_lot_is_refused(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "0")
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, lot=lot, amount=Decimal("1"))
        self.assertEqual(snapshot(), before)

    def test_a_lot_of_another_article_is_refused(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0013", "mg", "50")
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, lot=lot, amount=Decimal("1"))
        self.assertEqual(snapshot(), before)

    def test_the_amount_of_a_stale_lot_is_not_trusted(self) -> None:
        item = self.item("CH-0012", quantity=0)
        stale = self.lot("CH-0012", "mg", "50")
        fill(self.kl, item, count=1, lot=fresh(stale), amount=Decimal("45"))
        self.assertEqual(stale.amount, Decimal("50"))
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, lot=stale, amount=Decimal("20"))
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(stale).amount, Decimal("5"))

    def test_a_filling_without_a_lot_touches_no_lot(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        fill(self.kl, item, count=3)
        self.assertEqual(fresh(lot).amount, Decimal("50"))
        self.assertEqual(lot.movements.count(), 1)

    def test_reversing_a_filling_returns_the_amount(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        filling = fill(self.kl, item, count=5, lot=lot)
        reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(lot).amount, Decimal("50"))
        returned = lot.movements.order_by("-pk").first()
        self.assertEqual(returned.kind, LotMovement.Kind.REVERSAL)
        self.assertEqual((returned.amount, returned.amount_after),
                         (Decimal("7.408"), Decimal("50")))
        self.assertEqual(returned.user, self.kl)
        self.assertEqual(fresh(item).quantity, 0)

    def test_a_refused_reversal_leaves_the_lot(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        filling = fill(self.kl, item, count=5, lot=lot)
        self.deliver(item, 4)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse(self.kl, filling, note="doppelt")
        self.assertEqual(snapshot(), before)

    def test_the_item_movement_names_the_lot_movement(self) -> None:
        item = self.item("CH-0012", quantity=0)
        lot = self.lot("CH-0012", "mg", "50")
        fill(self.kl, item, count=5, lot=lot)
        movement = newest_movement(item)
        self.assertEqual(movement.bulk_movement.lot, lot)


class BulkOfAnItemTests(InventoryCase):
    """Wherever an item shows its bulk (here the list's column)."""

    def bulk_cells(self) -> dict[str, object]:
        header, rows = table(page(self.client.get(LIST)))
        return {f"{row[header[0]].text()} "
                f"{row['Gebinde'].text().replace(' ', '')}": row["Bulk"]
                for row in rows}

    def test_containers_from_bulk(self) -> None:
        """Scenario: Containers from bulk."""
        self.item("CH-0012", size="10", unit="umol")
        self.lot("CH-0012", "mg", "50")
        cell = self.bulk_cells()[f"CH-0012 10{MICRO}mol"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertTrue(has_number(cell.text(), "33"), cell.text())

    def test_lots_are_not_pooled(self) -> None:
        """Scenario: Lots are not pooled."""
        self.item("X-1", size="10", unit="mg")
        self.lot("X-1", "mg", "6")
        self.lot("X-1", "mg", "6")
        cell = self.bulk_cells()["X-1 10mg"]
        self.assertTrue(has_amount(cell.text(), "12", "mg"), cell.text())
        self.assertTrue(has_number(cell.text(), "0"), cell.text())

    def test_the_containers_are_counted_lot_by_lot(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.lot("X-1", "mg", "25")
        self.lot("X-1", "mg", "25")
        cell = self.bulk_cells()["X-1 10mg"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertTrue(has_number(cell.text(), "4"), cell.text())

    def test_the_division_is_exact(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.lot("CH-0012", "mg", "148.16")
        cell = self.bulk_cells()[f"CH-0012 10{MICRO}mol"]
        self.assertTrue(has_number(cell.text(), "100"), cell.text())

    def test_each_size_counts_its_own_containers(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0012", size="50", unit="umol")
        self.lot("CH-0012", "mg", "50")
        cells = self.bulk_cells()
        self.assertTrue(has_number(cells[f"CH-0012 10{MICRO}mol"].text(),
                                   "33"))
        self.assertTrue(has_number(cells[f"CH-0012 50{MICRO}mol"].text(),
                                   "6"))

    def test_the_amount_is_shown_by_unit(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.lot("X-1", "mg", "50")
        self.lot("X-1", "g", "1")
        text = self.bulk_cells()["X-1 10mg"].text()
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertTrue(has_amount(text, "1", "g"), text)
        self.assertTrue(has_number(text, "105"), text)

    def test_a_lot_in_grams_fills_milligram_containers(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.lot("X-1", "g", "1")
        self.assertTrue(has_number(self.bulk_cells()["X-1 10mg"].text(),
                                   "100"))

    def test_a_lot_that_does_not_convert_is_left_out(self) -> None:
        self.item("X-9", size="10", unit="umol")
        self.lot("X-9", "umol", "35")
        self.lot("X-9", "mg", "500")
        text = self.bulk_cells()[f"X-9 10{MICRO}mol"].text()
        self.assertTrue(has_amount(text, "35", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "500", "mg"), text)
        self.assertTrue(has_number(text, "3"), text)

    def test_used_up_lots_and_other_articles_are_left_out(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.lot("X-1", "mg", "0")
        self.lot("X-2", "mg", "90")
        text = self.bulk_cells()["X-1 10mg"].text()
        self.assertNotIn("90", text)
        self.assertNotIn("mg", text)

    def test_an_item_without_lots_shows_no_bulk(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.assertNotIn("mg", self.bulk_cells()["X-1 10mg"].text())

    def test_the_item_page_shows_the_open_lots(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.lot("CH-0012", "mg", "50", batch="B-7")
        self.lot("CH-0012", "mg", "0", batch="B-USED")
        self.lot("CH-0013", "mg", "20", batch="B-OTHER")
        text = page(self.client.get(item_url(item))).text()
        self.assertIn("B-7", text)
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertTrue(has_number(text, "33"), text)
        self.assertNotIn("B-USED", text)
        self.assertNotIn("B-OTHER", text)
