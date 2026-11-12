"""Tests of the batches between tasks and bulk lots (production-planning:
Batches between tasks and bulk; task-tracker: Task page;
end-product-inventory: Bulk lot page, Inventory forms)."""

from datetime import date
from urllib.parse import parse_qs, urlsplit

from inventory.models import Lot

from . import field_value, make_substance, make_task, task_url
from .collection_support import accept
from .inventory_support import NEW_LOT, lot_data, lot_url
from .planning_support import PlanningCase

RECORD_DE = "Als Bulk erfassen"
RECORD_EN = "Record as bulk"
BATCH = "B-2026-031"
ENDED = date(2026, 10, 30)


def hrefs(root) -> list[str]:
    return [a.get("href") for a in root.find_all("a")]


class BatchCase(PlanningCase):

    def setUp(self) -> None:
        super().setUp()
        self.item("CH-0012", size="10", unit="umol", quantity=3)

    def ended(self, substance: str = "CH-0012", batch: str = BATCH, **over):
        return make_task(self.kl, substance=substance, batch=batch,
                         started=date(2026, 10, 1), ended=ENDED,
                         report=True, qc_list=True, **over)

    def task_page(self, task, signed_in: bool = False):
        return self.get(task_url(task), signed_in)

    def lot_page(self, lot):
        return self.get(lot_url(lot))

    def record_link(self, task, signed_in: bool = True):
        root = self.task_page(task, signed_in)
        found = [a for a in root.find_all("a")
                 if a.text() in (RECORD_DE, RECORD_EN)]
        return found[0] if found else None


class LinkTests(BatchCase):

    def test_task_and_lot_of_one_batch_link_each_other(self) -> None:
        task = self.ended()
        lot = self.lot("CH-0012", batch=BATCH)
        self.assertIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_same_batch_other_substance(self) -> None:
        """Scenario: Same batch, other substance."""
        lot = self.lot("new-compound-7", batch="B-001")
        task = make_task(self.kl, substance="CH-0012", batch="B-001")
        self.assertNotIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_a_task_of_the_substance_without_its_article_number(
            self) -> None:
        task = self.ended(substance="cinnamic-acid")
        lot = self.lot("CH-0012", batch=BATCH)
        self.assertIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_a_lot_of_a_substance_without_an_article_belongs_too(
            self) -> None:
        task = self.ended(substance="acetophenone")
        lot = self.lot("acetophenone", batch=BATCH, source="made")
        self.assertIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_other_batches_do_not_link(self) -> None:
        task = self.ended()
        lot = self.lot("CH-0012", batch="B-2026-032")
        self.assertNotIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_empty_batches_do_not_link(self) -> None:
        task = make_task(self.kl, substance="CH-0012", batch="")
        lot = self.lot("CH-0012", batch="")
        self.assertNotIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_a_task_without_a_batch_does_not_link_to_a_lot_with_one(
            self) -> None:
        task = make_task(self.kl, substance="CH-0012")
        lot = self.lot("CH-0012", batch=BATCH)
        self.assertNotIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.lot_page(lot)))

    def test_every_task_and_lot_of_the_batch_is_linked(self) -> None:
        first = self.ended()
        second = make_task(self.kl, substance="CH-0012", batch=BATCH)
        other = self.ended(batch="B-2")
        lots = [self.lot("CH-0012", batch=BATCH),
                self.lot("CH-0012", batch=BATCH)]
        lot_hrefs = hrefs(self.lot_page(lots[0]))
        self.assertIn(task_url(first), lot_hrefs)
        self.assertIn(task_url(second), lot_hrefs)
        self.assertNotIn(task_url(other), lot_hrefs)
        for task in (first, second):
            with self.subTest(task=task.number):
                found = hrefs(self.task_page(task))
                for lot in lots:
                    self.assertIn(lot_url(lot), found)

    def test_a_cancelled_task_belongs_to_its_batch_all_the_same(
            self) -> None:
        task = make_task(self.kl, substance="CH-0012", batch=BATCH,
                         cancelled=True)
        lot = self.lot("CH-0012", batch=BATCH)
        self.assertIn(lot_url(lot), hrefs(self.task_page(task)))


class RecordAsBulkTests(BatchCase):

    def test_the_link_of_an_ended_task(self) -> None:
        task = self.ended()
        link = self.record_link(task)
        self.assertIsNotNone(link)
        self.assertEqual(link.text(), RECORD_DE)
        parts = urlsplit(link.get("href"))
        self.assertEqual(parts.path, NEW_LOT)
        self.assertEqual(parse_qs(parts.query),
                         {"substance": ["cinnamic-acid"], "batch": [BATCH],
                          "made_on": ["2026-10-30"]})

    def test_the_english_label(self) -> None:
        accept(language="en")
        link = self.record_link(self.ended())
        self.assertEqual(link.text(), RECORD_EN)

    def test_the_link_needs_a_signed_in_user(self) -> None:
        self.assertIsNone(self.record_link(self.ended(), signed_in=False))

    def test_the_link_needs_an_ended_task(self) -> None:
        for fields in ({}, {"started": date(2026, 10, 1)}):
            with self.subTest(**fields):
                task = make_task(self.kl, substance="CH-0012", batch=BATCH,
                                 **fields)
                self.assertIsNone(self.record_link(task))

    def test_a_cancelled_task_does_not_offer_it(self) -> None:
        task = make_task(self.kl, substance="CH-0012", batch=BATCH,
                         started=date(2026, 10, 1), ended=ENDED,
                         cancelled=True)
        self.assertIsNone(self.record_link(task))

    def test_the_link_needs_a_batch(self) -> None:
        self.assertIsNone(self.record_link(self.ended(batch="")))

    def test_the_link_needs_no_article(self) -> None:
        """An intermediate has lots though it is no article."""
        link = self.record_link(self.ended(substance="acetophenone"))
        self.assertIsNotNone(link)
        parts = urlsplit(link.get("href"))
        self.assertEqual(parse_qs(parts.query)["substance"],
                         ["acetophenone"])

    def test_the_link_is_offered_though_the_batch_has_a_lot(self) -> None:
        self.lot("CH-0012", batch=BATCH)
        self.assertIsNotNone(self.record_link(self.ended()))

    def test_bulk_from_an_ended_task(self) -> None:
        """Scenario: Bulk from an ended task."""
        task = self.ended()
        link = self.record_link(task)
        form = self.get(link.get("href"), True)
        done = self.client.post(NEW_LOT, lot_data(
            substance=field_value(form, "substance"),
            batch=field_value(form, "batch"),
            made_on=field_value(form, "made_on"), amount="50"))
        self.assertEqual(done.status_code, 302)
        lot = Lot.objects.get(batch=BATCH)
        self.assertEqual(lot.substance.key, "cinnamic-acid")
        self.assertEqual(lot.source, "made")
        self.assertEqual(lot.made_on, ENDED)
        self.assertIn(lot_url(lot), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.lot_page(lot)))


class NewLotFormTests(BatchCase):

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.kl)

    def form(self, query: str):
        return self.get(NEW_LOT + query)

    def test_new_lot_from_the_query(self) -> None:
        """Scenario: New lot from the query."""
        root = self.form(
            "?substance=cinnamic-acid&batch=B-2026-031&made_on=2026-10-30")
        self.assertEqual(field_value(root, "substance"), "cinnamic-acid")
        self.assertEqual(field_value(root, "source"), "made")
        self.assertEqual(field_value(root, "batch"), BATCH)
        self.assertEqual(field_value(root, "made_on"), "2026-10-30")

    def test_each_parameter_fills_its_own_field(self) -> None:
        root = self.form("?batch=B-7")
        self.assertEqual(field_value(root, "batch"), "B-7")
        self.assertIn(field_value(root, "substance"), (None, ""))
        self.assertIn(field_value(root, "made_on"), (None, ""))
        root = self.form("?made_on=2026-10-30")
        self.assertEqual(field_value(root, "made_on"), "2026-10-30")
        self.assertIn(field_value(root, "batch"), (None, ""))

    def test_the_substance_alone_still_fills_in(self) -> None:
        root = self.form("?substance=cinnamic-acid")
        self.assertEqual(field_value(root, "substance"), "cinnamic-acid")
        self.assertIn(field_value(root, "batch"), (None, ""))

    def test_without_a_query_the_fields_are_empty(self) -> None:
        root = self.form("")
        for name in ("substance", "batch", "made_on"):
            with self.subTest(name=name):
                self.assertIn(field_value(root, name), (None, ""))

    def test_special_characters_survive(self) -> None:
        root = self.form("?substance=A%26B&batch=%22x%22+y")
        self.assertEqual(field_value(root, "substance"), "A&B")
        self.assertEqual(field_value(root, "batch"), '"x" y')

    def test_the_posted_values_win(self) -> None:
        make_substance("nv-7")
        done = self.client.post(
            NEW_LOT + "?substance=cinnamic-acid&batch=B-1",
            lot_data(substance="nv-7", batch="B-2", amount="5"))
        self.assertEqual(done.status_code, 302)
        lot = Lot.objects.get()
        self.assertEqual((lot.substance.key, lot.batch), ("nv-7", "B-2"))
