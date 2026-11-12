"""A test case shared by the tests of the task record, its forms, its
page and its actions (task-tracker): accounts, the demo registry, and
an accepted import of the demo collection, so that the sequences
``SEQ-0001`` and ``SEQ-0002`` exist.

Nothing here imports the ``tasks`` or ``collection`` package at module
level.
"""

from typing import Any

from django.test import TestCase

from . import (edit_data, load_demo_registry, make_demo_accounts, make_user,
               substance_for, task_form_data, task_url)
from .collection_support import import_collection

NEW = "/lab/tasks/new/"


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
