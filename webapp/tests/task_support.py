"""A test case shared by the tests of the task record, its forms, its
page and its actions (task-tracker): accounts, the demo registry, and
an accepted import of the demo collection, so that the sequences
``SEQ-0001`` and ``SEQ-0002`` exist.

Nothing here imports the ``tasks`` or ``collection`` package at module
level.
"""

from typing import Any

from django.test import TestCase

from . import (berlin, edit_data, load_demo_registry, make_demo_accounts,
               make_demo_notebooks, make_lot, make_user, substance_for,
               task_form_data, task_url, ticking)
from .collection_support import import_collection

NEW = "/lab/tasks/new/"
NEW_LOT = "/lab/inventory/bulk/new/"
NOW = berlin(2026, 11, 4, 8)
TODAY_ISO = "2026-11-04"


class TaskCase(TestCase):
    """A database with the accounts ``kl`` and ``ae``, the demo
    registry, the demo accounts, the substance ``aspirin`` and the demo
    collection imported once, which ``cls.first`` names. ``kl`` is signed
    in."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")
        load_demo_registry()
        make_demo_accounts()
        make_demo_notebooks()
        substance_for("Aspirin")
        cls.first = import_collection()

    def setUp(self) -> None:
        self.client.force_login(self.kl)

    def create(self, **fields: str) -> Any:
        """Post the new-task form with ``fields`` over the defaults of
        ``task_form_data``; return the response."""
        return self.client.post(NEW, task_form_data(**fields))

    def change(self, task: Any, **fields: str) -> Any:
        """Post the edit form of ``task`` as it stands with ``fields``
        replacing values; return the response."""
        return self.client.post(task_url(task, "edit"),
                                edit_data(task, **fields))

    def only_task(self) -> Any:
        from tasks.models import Task
        return Task.objects.get()


def history_text(root) -> str:
    """The text of the page below the heading of the change history."""
    text = root.text()
    for heading in ("Änderungen", "History"):
        if heading in text:
            return text.split(heading, 1)[1]
    raise AssertionError("the page shows no history")


def make_product_lot(task: Any, amount: str = "5", unit: str = "g",
                     **extra: Any) -> Any:
    """A made lot of ``task``'s substance with ``task``'s batch, which
    is the task's product lot (task-tracker "Task record"), booked by
    the task's creator; ``extra`` replaces what ``make_lot`` takes."""
    return make_lot(task.created_by, **{
        "substance": task.substance, "batch": task.batch, "unit": unit,
        "amount": amount, "source": "made", **extra})


def steps_of(task: Any) -> list[Any]:
    """The steps of ``task``, in order."""
    return list(task.steps.order_by("position"))


class StepCase(TaskCase):
    """The task case with a clock that stands at 2026-11-04 and ticks,
    for the tests of lots made by a step and of withdrawals into one;
    ``cls.first`` is the demo collection's import, whose sequence
    ``SEQ-0002`` has the steps ``OSDB-0004``, making
    ``4-acetylbiphenyl``, and entry 1 of ``OSDB-0009``, which takes it
    and makes ``1-biphenyl-4-yl-ethanol``."""

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(ticking(NOW))

    def follow(self, sequence: str = "SEQ-0002", **fields: str) -> Any:
        """The only task, made through the form for a task of
        ``sequence`` that started on 2025-03-01 (``fields`` replace the
        form's values), with the sequence's product as its substance."""
        from collection.models import Sequence
        from tasks.models import Task
        target = Sequence.objects.get(key=sequence).target.key
        self.create(**{"substance": target, "sequence": sequence,
                       "started": "2025-03-01", **fields})
        return Task.objects.get()
