"""Tests of the batches of tasks (production-planning: Batches of
tasks; task-tracker: Task page; end-product-inventory: Batch page,
Inventory forms)."""

from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from inventory.models import Batch

from . import (field_value, make_batch, make_task, make_vessel, past,
               task_url)
from .collection_support import accept
from .inventory_support import NEW_BATCH, batch_data, batch_url
from .planning_support import PlanningCase

RECORD_DE = "Charge erfassen"
RECORD_EN = "Record batch"
OLD_DE = ("Los erfassen", "Als Bulk erfassen")
OLD_EN = ("Record a lot", "Record as bulk")


def hrefs(root) -> list[str]:
    return [a.get("href") for a in root.find_all("a")]


class BatchCase(PlanningCase):

    def setUp(self) -> None:
        super().setUp()
        self.item("CH-0012", size="10", unit="umol", quantity=3)

    def running(self, substance: str = "CH-0012", steps: int = 2, **over):
        return make_task(self.kl, substance=substance,
                         started=date(2026, 10, 1), steps=steps, **over)

    def task_page(self, task, signed_in: bool = False):
        return self.get(task_url(task), signed_in)

    def batch_page(self, batch):
        return self.get(batch_url(batch))

    def record_links(self, task, signed_in: bool = True):
        root = self.task_page(task, signed_in)
        return [a for a in root.find_all("a")
                if a.text() in (RECORD_DE, RECORD_EN)]


class LinkTests(BatchCase):
    """Requirement: Batches of tasks (a batch made by a step belongs to
    that task, and to no other)."""

    def test_a_task_and_its_batch_link_each_other(self) -> None:
        task = self.running()
        batch = make_batch(self.kl, "CH-0012", number="KL0412",
                           task_step=task.steps.get(position=2))
        self.assertIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.batch_page(batch)))

    def test_a_batch_without_a_step_links_no_task(self) -> None:
        """Scenario: A batch without a step."""
        task = self.running()
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.assertNotIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.batch_page(batch)))

    def test_a_batch_without_a_step_stays_unlinked_beside_one_with(
            self) -> None:
        """The link is the step: a batch of the same substance recorded
        without one stays unlinked while the task has a batch of its
        own."""
        task = self.running()
        make_batch(self.kl, "CH-0012", number="KL1",
                   task_step=task.steps.get(position=2))
        loose = make_batch(self.kl, "CH-0012", number="KL2")
        self.assertNotIn(batch_url(loose), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.batch_page(loose)))

    def test_a_batch_belongs_to_the_task_of_its_step_alone(self) -> None:
        task = self.running()
        other = self.running()
        batch = make_batch(self.kl, "CH-0012", number="KL1",
                           task_step=other.steps.get(position=1))
        self.assertNotIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertNotIn(task_url(task), hrefs(self.batch_page(batch)))
        self.assertIn(task_url(other), hrefs(self.batch_page(batch)))
        self.assertIn(batch_url(batch), hrefs(self.task_page(other)))

    def test_an_intermediate_batch_belongs_to_the_task_too(self) -> None:
        task = self.running()
        batch = make_batch(self.kl, "acetophenone", number="KL1",
                           task_step=task.steps.get(position=1))
        self.assertIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.batch_page(batch)))

    def test_several_batches_of_one_step_are_all_linked(self) -> None:
        task = self.running()
        step = task.steps.get(position=2)
        batches = [make_batch(self.kl, "CH-0012", number=f"KL{n}",
                              task_step=step) for n in range(3)]
        found = hrefs(self.task_page(task))
        for batch in batches:
            with self.subTest(batch=batch.number):
                self.assertIn(batch_url(batch), found)

    def test_a_cancelled_tasks_batch_stays_linked(self) -> None:
        task = self.running(cancelled=True)
        batch = make_batch(self.kl, "CH-0012", number="KL1",
                           task_step=task.steps.get(position=1))
        self.assertIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.batch_page(batch)))

    def test_the_batch_is_listed_under_the_step_that_made_it(self) -> None:
        task = self.running()
        batch = make_batch(self.kl, "CH-0012", number="KL1",
                           task_step=task.steps.get(position=2))
        make_vessel(self.kl, batch, unit="g", amount="2", flask=True)
        items = self.task_page(task).find("ol").find_all("li")
        self.assertNotIn(batch_url(batch), hrefs(items[0]))
        self.assertIn(batch_url(batch), hrefs(items[1]))


class RecordLinkTests(BatchCase):
    """Requirement: Task page (`Charge erfassen` while the task is
    planned or running)."""

    def test_the_link_of_each_step_of_a_running_task(self) -> None:
        task = self.running()
        links = self.record_links(task)
        self.assertEqual(
            sorted(a.get("href") for a in links),
            sorted(f"{NEW_BATCH}?step={step.pk}"
                   for step in task.steps.all()))
        self.assertEqual({a.text() for a in links}, {RECORD_DE})

    def test_a_planned_task_offers_it_too(self) -> None:
        task = make_task(self.kl, substance="CH-0012", steps=1)
        self.assertEqual(len(self.record_links(task)), 1)

    def test_the_english_label(self) -> None:
        accept(language="en")
        links = self.record_links(self.running())
        self.assertEqual({a.text() for a in links}, {RECORD_EN})

    def test_the_link_needs_a_signed_in_user(self) -> None:
        self.assertEqual(self.record_links(self.running(),
                                           signed_in=False), [])

    def test_a_task_that_is_not_planned_or_running_offers_none(self) -> None:
        for fields in ({"ended": date(2026, 10, 30), "report": True,
                        "qc_list": True},
                       {"cancelled": True},
                       {"ended": date(2026, 10, 30), "failed": True}):
            with self.subTest(**fields):
                task = self.running(**fields)
                self.assertEqual(self.record_links(task), [])

    def test_a_task_without_steps_offers_none(self) -> None:
        task = make_task(self.kl, substance="CH-0012",
                         started=date(2026, 10, 1))
        self.assertEqual(self.record_links(task), [])

    def test_the_old_links_are_gone(self) -> None:
        for fields in ({}, {"ended": date(2026, 10, 30), "report": True,
                            "qc_list": True}):
            with self.subTest(**fields):
                task = self.running(**fields)
                texts = {a.text() for a in self.task_page(
                    task, True).find_all("a")}
                self.assertFalse(texts & set(OLD_DE + OLD_EN), texts)


class BatchFromAStepTests(BatchCase):

    def test_a_batch_from_a_tasks_step(self) -> None:
        """Scenario: A batch from a task's step."""
        task = self.running("CH-0012", steps=2)
        last = task.steps.get(position=2)
        root = self.task_page(task, signed_in=True)
        items = root.find("ol").find_all("li")
        links = [a for a in items[-1].find_all("a")
                 if a.text() == RECORD_DE]
        self.assertEqual([a.get("href") for a in links],
                         [f"{NEW_BATCH}?step={last.pk}"])
        href = links[0].get("href")
        form = self.get(href)
        self.assertEqual(field_value(form, "substance"), "cinnamic-acid")
        done = self.client.post(href, batch_data(
            substance=field_value(form, "substance"), number="KL0412",
            step=field_value(form, "step"), amount="2", unit="g"))
        self.assertEqual(done.status_code, 302)
        batch = Batch.objects.get()
        self.assertEqual(
            (batch.number, batch.substance.key, batch.source,
             batch.task_step), ("KL0412", "cinnamic-acid", "made", last))
        flask = batch.vessels.get()
        self.assertEqual((flask.flask, flask.amount),
                         (True, Decimal("2000")))
        self.assertIn(batch_url(batch), hrefs(self.task_page(task)))
        self.assertIn(task_url(task), hrefs(self.batch_page(batch)))

    def test_the_query_of_the_link_fills_the_form(self) -> None:
        task = self.running("CH-0012", steps=1)
        step = task.steps.get()
        parts = urlsplit(self.record_links(task)[0].get("href"))
        self.assertEqual(parts.path, NEW_BATCH)
        self.assertEqual(parse_qs(parts.query), {"step": [str(step.pk)]})

    def test_a_batch_from_a_step_of_a_planned_task(self) -> None:
        task = make_task(self.kl, substance="CH-0012", steps=1)
        step = task.steps.get()
        self.client.force_login(self.kl)
        done = self.client.post(
            f"{NEW_BATCH}?step={step.pk}", batch_data(
                step=str(step.pk), amount="1", unit="g", number="KL1"))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Batch.objects.get().task_step, step)

    def test_the_form_of_an_ended_tasks_step_is_refused(self) -> None:
        task = make_task(self.kl, substance="CH-0012", steps=1,
                         started=past(2), ended=past(1))
        step = task.steps.get()
        self.client.force_login(self.kl)
        done = self.client.post(
            f"{NEW_BATCH}?step={step.pk}", batch_data(
                step=str(step.pk), amount="1", unit="g", number="KL1"))
        self.assertEqual(done.status_code, 200)
        self.assertEqual(Batch.objects.count(), 0)
