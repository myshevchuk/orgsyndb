"""Tests of the forms that name a batch: the new item, the delivery note
and the correction (end-product-inventory: Inventory forms, Stock by
batch)."""

import re
from typing import Any

from inventory.models import Batch, DeliveryNote, Item, Movement

from . import (Element, context_form, field_value, make_batch,
               make_substance, page)
from .collection_support import accept
from .inventory_support import (NEW_ITEM, NEW_NOTE, TODAY, FormCase,
                                expected, fresh, item_data, item_url,
                                note_data, set_shares, shares,
                                stock_snapshot)

type Groups = dict[str, tuple[str, list[tuple[str, str]]]]


def groups_of(select: Element) -> Groups:
    """The ``optgroup`` of a ``select`` by its ``data-substance``, each
    as its label and its options' values and texts."""
    return {group.get("data-substance"): (
        group.get("label"),
        [(option.get("value"), option.text())
         for option in group.find_all("option")])
        for group in select.find_all("optgroup")}


def offered(select: Element) -> set[str]:
    """The values of the batches a ``select`` offers in its groups."""
    return {value for _, options in groups_of(select).values()
            for value, _ in options}


def count_in(text: str, name: str) -> int | None:
    """The first whole number of ``text`` outside ``name``, None when
    there is none."""
    found = re.search(r"(?<![\w.,])\d+(?![\w.,])", text.replace(name, ""))
    return int(found.group()) if found else None


class BatchFormCase(FormCase):
    """Batches of ``cinnamic-acid`` and ``acetophenone``, a bought one
    among them."""

    def setUp(self) -> None:
        super().setUp()
        self.a = make_batch(self.kl, "CH-0012", number="KL0412")
        self.b = make_batch(self.kl, "CH-0012", source="bought",
                            supplier="Sigma", supplier_batch="MK99")
        self.other = make_batch(self.kl, "acetophenone", number="AP1")

    def name_of(self, key: str) -> str:
        from registry.models import Substance
        return Substance.objects.get(key=key).shown_name


class NewItemBatchTests(BatchFormCase):

    def select(self) -> Element:
        root = page(self.client.get(NEW_ITEM))
        found = root.find("select", name="batch")
        self.assertIsNotNone(found, "the form has no choice of a batch")
        return found

    def test_the_form_offers_the_batches_of_every_substance(self) -> None:
        loose = make_batch(self.kl, substance=make_substance(
            "no-article", "No article"), number="NA1")
        found = groups_of(self.select())
        self.assertEqual(set(found), {"cinnamic-acid", "acetophenone",
                                      "no-article"})
        self.assertEqual(
            found["cinnamic-acid"][1],
            [(str(self.a.pk), "KL0412"), (str(self.b.pk), "MK99")])
        self.assertEqual(found["acetophenone"][1],
                         [(str(self.other.pk), "AP1")])
        self.assertEqual(found["no-article"][1], [(str(loose.pk), "NA1")])

    def test_the_groups_are_named_for_their_substance(self) -> None:
        found = groups_of(self.select())
        for key in ("cinnamic-acid", "acetophenone"):
            with self.subTest(key=key):
                self.assertEqual(found[key][0], self.name_of(key))

    def test_the_choice_is_for_the_script_to_narrow(self) -> None:
        self.assertEqual(self.select().get("data-batch-for"), "substance")

    def test_the_choice_is_optional_and_empty_by_default(self) -> None:
        select = self.select()
        self.assertIn("", [o.get("value") for o in select.find_all("option")])
        self.assertNotIn("required", select.attrs)
        self.assertIn(field_value(page(self.client.get(NEW_ITEM)), "batch"),
                      ("", None))

    def test_an_opening_count_of_a_batch(self) -> None:
        """Scenario: Opening count of a batch."""
        done = self.client.post(NEW_ITEM, item_data(
            quantity="4", batch=str(self.a.pk)))
        item = Item.objects.get()
        self.assertRedirects(done, item_url(item),
                             fetch_redirect_response=False)
        self.assertEqual(shares(item), expected((self.a, 4)))
        self.assertEqual(item.quantity, 4)
        opening = item.movements.get()
        self.assertEqual((opening.kind, opening.count, opening.batch),
                         ("opening", 4, self.a))

    def test_a_batch_of_another_substance_is_refused(self) -> None:
        """Scenario: Opening count of a batch (the second form)."""
        self.client.post(NEW_ITEM, item_data(quantity="4",
                                             batch=str(self.a.pk)))
        before = stock_snapshot()
        done = self.client.post(NEW_ITEM, item_data(
            size="50", quantity="4", batch=str(self.other.pk)))
        self.refused(done, "batch")
        self.assertEqual(Item.objects.count(), 1)
        self.assertEqual(stock_snapshot(), before)

    def test_an_unknown_batch_is_refused(self) -> None:
        done = self.client.post(NEW_ITEM, item_data(batch="999999"))
        self.refused(done, "batch")
        self.assertEqual(Item.objects.count(), 0)

    def test_an_opening_count_without_a_batch_is_of_unknown_batch(
            self) -> None:
        """Scenario: Opening count of unknown batch (the form)."""
        self.client.post(NEW_ITEM, item_data(quantity="4"))
        item = Item.objects.get()
        self.assertEqual(shares(item), {None: 4})
        self.assertIsNone(item.movements.get().batch)

    def test_the_form_keeps_the_batch_that_was_chosen(self) -> None:
        done = self.client.post(NEW_ITEM, item_data(
            batch=str(self.a.pk), size="0"))
        self.refused(done, "size")
        self.assertEqual(field_value(page(done), "batch"), str(self.a.pk))


class NoteBatchTests(BatchFormCase):

    def setUp(self) -> None:
        super().setUp()
        self.c = make_batch(self.kl, "CH-0001", number="KL0001")
        self.item_a = self.item("CH-0012", quantity=0)
        self.item_c = self.item("CH-0001", quantity=0)
        make_batch(self.kl, "CH-0002", number="KL0002")

    def holding(self, item: Item, *pairs: tuple[Batch | None, int]) -> Item:
        set_shares(item, *pairs)
        return item

    def rows(self, *lines: tuple[Item, Batch | None, Any], **over: str
             ) -> dict[str, str]:
        """The note form with the lines ``(item, batch, count)`` in its
        first rows, which books nothing beforehand."""
        data = note_data(**over)
        for index, (item, batch, count) in enumerate(lines):
            data[f"item_{index}"] = str(item.pk)
            data[f"batch_{index}"] = "" if batch is None else str(batch.pk)
            data[f"count_{index}"] = str(count)
        return data

    def test_each_row_offers_the_batches_of_the_substances_of_its_items(
            self) -> None:
        from .test_inventory_numbers import numberless
        bare = numberless(self.kl)
        make_batch(self.kl, substance=bare.article.substance, number="NV9")
        root = page(self.client.get(NEW_NOTE))
        for row in range(10):
            select = root.find("select", name=f"batch_{row}")
            with self.subTest(row=row):
                self.assertIsNotNone(select)
                self.assertEqual(select.get("data-batch-for"),
                                 f"item_{row}")
                found = groups_of(select)
                self.assertEqual(set(found), {"cinnamic-acid",
                                              "1-4-bromophenyl-ethanol"})
                self.assertEqual(
                    found["cinnamic-acid"][1],
                    [(str(self.a.pk), "KL0412"), (str(self.b.pk), "MK99")])
                self.assertEqual(found["1-4-bromophenyl-ethanol"][1],
                                 [(str(self.c.pk), "KL0001")])
                self.assertEqual(found["cinnamic-acid"][0],
                                 self.name_of("cinnamic-acid"))

    def test_the_batches_of_the_other_substances_are_not_offered(
            self) -> None:
        root = page(self.client.get(NEW_NOTE))
        self.assertNotIn(str(self.other.pk),
                         offered(root.find("select", name="batch_0")))

    def test_a_row_may_be_left_without_a_batch(self) -> None:
        root = page(self.client.get(NEW_NOTE))
        select = root.find("select", name="batch_0")
        self.assertIn("", [o.get("value") for o in select.find_all("option")])
        self.assertIn(field_value(root, "batch_0"), ("", None))

    def test_the_items_carry_their_substances(self) -> None:
        root = page(self.client.get(NEW_NOTE))
        options = {o.get("value"): o.get("data-substance")
                   for o in root.find("select", name="item_0"
                                      ).find_all("option")
                   if o.get("value")}
        self.assertEqual(options, {str(self.item_a.pk): "cinnamic-acid",
                                   str(self.item_c.pk):
                                   "1-4-bromophenyl-ethanol"})

    def test_an_item_in_the_url_leaves_the_batch_to_choose(self) -> None:
        root = page(self.client.get(f"{NEW_NOTE}?item={self.item_a.pk}"))
        self.assertEqual(field_value(root, "item_0"), str(self.item_a.pk))
        self.assertIn(field_value(root, "batch_0"), ("", None))

    def test_booking_a_note_with_batches(self) -> None:
        """Scenario: Note with several lines (the form)."""
        self.holding(self.item_a, (self.a, 5))
        self.holding(self.item_c, (self.c, 3))
        done = self.client.post(NEW_NOTE, self.rows(
            (self.item_a, self.a, 2), (self.item_c, self.c, 3),
            number="LS-1"))
        note = DeliveryNote.objects.get()
        self.assertRedirects(done, f"/lab/inventory/deliveries/{note.pk}/",
                             fetch_redirect_response=False)
        self.assertEqual(
            sorted((line.item_id, line.batch_id, line.count)
                   for line in note.lines.all()),
            sorted([(self.item_a.pk, self.a.pk, 2),
                    (self.item_c.pk, self.c.pk, 3)]))
        self.assertEqual(shares(self.item_a), expected((self.a, 3)))
        self.assertEqual(shares(self.item_c), {})
        self.assertEqual(
            self.item_a.movements.get(kind="delivery").batch, self.a)

    def test_a_delivery_from_containers_of_unknown_batch(self) -> None:
        item = self.holding(self.item_a, (self.a, 1), (None, 5))
        self.client.post(NEW_NOTE, self.rows((item, self.a, 3)))
        self.assertEqual(shares(item), {None: 3})
        kinds = [m.kind for m in item.movements.order_by("-pk")][:2]
        self.assertEqual(kinds, ["delivery", "assignment"])

    def test_too_few_even_with_unknown_batch(self) -> None:
        """Scenario: Too few even with unknown batch (the form)."""
        item = self.holding(self.item_a, (self.a, 1), (None, 1))
        before = stock_snapshot()
        done = self.client.post(NEW_NOTE, self.rows((item, self.a, 3)))
        self.refused(done, "count_0")
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertEqual(stock_snapshot(), before)
        self.assertFalse(Movement.objects.filter(kind="assignment").exists())

    def test_a_row_needs_its_batch(self) -> None:
        """Scenario: A row needs its batch."""
        self.holding(self.item_a, (self.a, 5))
        before = stock_snapshot()
        done = self.client.post(NEW_NOTE, self.rows(
            (self.item_a, None, 2)))
        self.refused(done, "batch_0")
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertEqual(stock_snapshot(), before)

    def test_the_row_with_the_missing_field_is_the_one_marked(self) -> None:
        self.holding(self.item_a, (self.a, 5))
        done = self.client.post(NEW_NOTE, self.rows(
            (self.item_a, self.a, 1), (self.item_a, None, 1)))
        self.refused(done, "batch_1")
        self.assertNotIn("batch_0", context_form(done).errors)

    def test_a_row_without_its_item_or_its_count_is_refused(self) -> None:
        self.holding(self.item_a, (self.a, 5))
        data = self.rows((self.item_a, self.a, 1))
        for field, name in (("item_0", "item_0"), ("count_0", "count_0")):
            with self.subTest(field=field):
                self.refused(self.client.post(
                    NEW_NOTE, {**data, field: ""}), name)
        self.assertEqual(DeliveryNote.objects.count(), 0)

    def test_rows_left_empty_are_ignored(self) -> None:
        self.holding(self.item_a, (self.a, 5))
        self.client.post(NEW_NOTE, self.rows((self.item_a, self.a, 1)))
        self.assertEqual(DeliveryNote.objects.get().lines.count(), 1)

    def test_a_batch_of_another_substance_is_refused(self) -> None:
        """Scenario: A batch of another substance (the form)."""
        self.holding(self.item_a, (self.a, 5))
        before = stock_snapshot()
        for batch in (self.c, self.other):
            for historical in ({}, {"historical": "on",
                                    "date": "2025-03-12"}):
                with self.subTest(batch=batch.number,
                                  historical=bool(historical)):
                    done = self.client.post(NEW_NOTE, self.rows(
                        (self.item_a, batch, 1), **historical))
                    self.refused(done, "batch_0")
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertEqual(stock_snapshot(), before)

    def test_a_batch_that_is_not_offered_is_refused(self) -> None:
        done = self.client.post(NEW_NOTE, {
            **self.rows((self.item_a, self.a, 1)), "batch_0": "999999"})
        self.refused(done, "batch_0")

    def test_two_batches_of_one_item(self) -> None:
        """Scenario: Two batches of one item."""
        item = self.holding(self.item_a, (self.a, 3), (self.b, 1))
        self.client.post(NEW_NOTE, self.rows(
            (item, self.a, 2), (item, self.b, 1)))
        note = DeliveryNote.objects.get()
        self.assertEqual(note.lines.count(), 2)
        done = self.client.post(NEW_NOTE, self.rows(
            (item, self.a, 1), (item, self.a, 1)))
        self.refused(done, "batch_1")
        self.assertNotIn("batch_0", context_form(done).errors)
        self.assertEqual(DeliveryNote.objects.count(), 1)
        self.assertEqual(shares(item), expected((self.a, 1)))

    def test_the_second_line_of_an_item_may_name_another_batch(self) -> None:
        item = self.holding(self.item_a, (None, 5))
        self.client.post(NEW_NOTE, self.rows(
            (item, self.a, 2), (item, self.b, 1)))
        self.assertEqual(shares(item), {None: 2})

    def test_a_historical_note_names_its_batches_and_moves_nothing(
            self) -> None:
        item = self.holding(self.item_a, (self.a, 1))
        before = stock_snapshot()
        done = self.client.post(NEW_NOTE, self.rows(
            (item, self.a, 4), (item, self.b, 2), date="2025-03-12",
            historical="on"))
        note = DeliveryNote.objects.get()
        self.assertRedirects(done, f"/lab/inventory/deliveries/{note.pk}/",
                             fetch_redirect_response=False)
        self.assertEqual(
            sorted((line.batch_id, line.count) for line in note.lines.all()),
            sorted([(self.a.pk, 4), (self.b.pk, 2)]))
        self.assertEqual(stock_snapshot(), before)

    def test_a_historical_row_needs_its_batch_too(self) -> None:
        done = self.client.post(NEW_NOTE, self.rows(
            (self.item_a, None, 4), date="2025-03-12", historical="on"))
        self.refused(done, "batch_0")

    def test_the_form_keeps_the_batch_that_was_chosen(self) -> None:
        item = self.holding(self.item_a, (self.a, 1))
        done = self.client.post(NEW_NOTE, self.rows((item, self.a, 4)))
        self.refused(done, "count_0")
        root = page(done)
        self.assertEqual(field_value(root, "item_0"), str(item.pk))
        self.assertEqual(field_value(root, "batch_0"), str(self.a.pk))
        self.assertEqual(field_value(root, "count_0"), "4")


class CorrectionShareFormTests(BatchFormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", quantity=0)
        set_shares(self.target, (self.a, 3), (None, 2))
        self.url = item_url(self.target, "correct")

    def data(self, **over: str) -> dict[str, str]:
        data = {"count": "5", "date": TODAY.isoformat(), "note": "gezählt",
                "batch": ""}
        data.update(over)
        return data

    def options(self) -> dict[str, str]:
        root = page(self.client.get(self.url))
        select = root.find("select", name="batch")
        self.assertIsNotNone(select, "the form has no choice of a share")
        return {o.get("value"): o.text() for o in select.find_all("option")}

    def test_the_shares_offered(self) -> None:
        """Scenario: Shares offered for a correction."""
        found = self.options()
        self.assertEqual(set(found), {"", str(self.a.pk), str(self.b.pk)})
        for value, name, held in (("", "unbekannt", 2),
                                  (str(self.a.pk), "KL0412", 3),
                                  (str(self.b.pk), "MK99", 0)):
            with self.subTest(share=name):
                self.assertIn(name, found[value])
                self.assertEqual(count_in(found[value], name), held)

    def test_the_share_of_unknown_batch_is_chosen(self) -> None:
        root = page(self.client.get(self.url))
        self.assertEqual(field_value(root, "batch"), "")

    def test_the_batches_of_other_substances_are_not_offered(self) -> None:
        self.assertNotIn(str(self.other.pk), self.options())

    def test_the_choice_in_english(self) -> None:
        accept(language="en")
        found = self.options()
        self.assertIn("unknown", found[""])
        self.assertNotIn("unbekannt", found[""])

    def test_correcting_the_share_of_unknown_batch(self) -> None:
        """Scenario: Correction of one share (the form)."""
        done = self.client.post(self.url, self.data(count="0"))
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(shares(self.target), expected((self.a, 3)))
        movement = self.target.movements.order_by("-pk").first()
        self.assertEqual(
            (movement.kind, movement.batch, movement.count,
             movement.quantity_after),
            ("correction", None, 0, 3))

    def test_correcting_the_share_of_a_batch(self) -> None:
        self.client.post(self.url, self.data(batch=str(self.a.pk)))
        self.assertEqual(shares(self.target),
                         expected((self.a, 5), (None, 2)))
        movement = self.target.movements.order_by("-pk").first()
        self.assertEqual(
            (movement.batch, movement.count, movement.quantity_after),
            (self.a, 5, 7))

    def test_correcting_a_batch_the_item_never_held(self) -> None:
        self.client.post(self.url, self.data(batch=str(self.b.pk),
                                             count="4"))
        self.assertEqual(shares(self.target), expected(
            (self.a, 3), (self.b, 4), (None, 2)))

    def test_a_post_without_the_choice_corrects_the_unknown_share(
            self) -> None:
        data = self.data(count="1")
        del data["batch"]
        self.client.post(self.url, data)
        self.assertEqual(shares(self.target),
                         expected((self.a, 3), (None, 1)))

    def test_a_batch_of_another_substance_is_refused(self) -> None:
        before = stock_snapshot()
        done = self.client.post(self.url, self.data(
            batch=str(self.other.pk)))
        self.refused(done, "batch")
        self.assertEqual(stock_snapshot(), before)

    def test_the_note_is_still_required(self) -> None:
        before = stock_snapshot()
        done = self.client.post(self.url, self.data(
            batch=str(self.a.pk), note=""))
        self.refused(done, "note")
        self.assertEqual(stock_snapshot(), before)
        self.assertEqual(fresh(self.target).quantity, 5)

    def test_the_counts_follow_the_item(self) -> None:
        set_shares(self.target, (self.a, 7), (self.b, 1), (None, 0))
        found = self.options()
        self.assertEqual(count_in(found[str(self.a.pk)], "KL0412"), 7)
        self.assertEqual(count_in(found[str(self.b.pk)], "MK99"), 1)
        self.assertEqual(count_in(found[""], "unbekannt"), 0)
