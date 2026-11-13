"""Fixtures and helpers shared by the tests of the lab journal
(lab-journal) and of the journal entries of procedures and task steps.

Nothing here imports the ``journal`` package at module level, so a test
that uses these helpers fails on its own assertions while the package is
missing.
"""

from typing import Any

from django.test import TestCase

from . import make_user, parse

JOURNAL = "/lab/journal/"
NEW_NOTEBOOK = JOURNAL + "new/"
ADMIN = "/lab/admin/journal/"
NOTEBOOKS = ADMIN + "notebook/"
ENTRIES = ADMIN + "entry/"


def notebook_url(code: str, action: str = "") -> str:
    """The page of the notebook ``code``, or its form ``action``
    (``edit``)."""
    return f"{JOURNAL}{code}/" + (f"{action}/" if action else "")


def step_journal_url(step: Any) -> str:
    """The path that sets the journal entry of the task step ``step``."""
    return f"/lab/tasks/steps/{step.pk}/journal/"


def make_notebook(code: str = "AE-1", user: Any = None, note: str = "",
                  by: Any = None) -> Any:
    """The notebook ``code`` of the account ``user``, saved with the
    history user ``by`` when that is given."""
    from journal.models import Notebook
    found = Notebook(code=code, user=user, note=note)
    if by is not None:
        found._history_user = by
    found.save()
    return found


def entry_of(text: str) -> Any:
    """The entry ``text``, such as ``AE-1/2``, as ``journal.entries``
    gives it, created when it is new."""
    from journal.entries import entry_for
    return entry_for(text)


def entries_named(text: str) -> int:
    """How many entries are written ``text``, such as ``AE-1/2``."""
    from journal.models import Entry
    code, _slash, number = text.partition("/")
    return Entry.objects.filter(notebook__code=code,
                                number=int(number)).count()


def control_names(form: Any) -> set[str]:
    """The names of the controls of ``form`` that submit a value."""
    return {e.get("name") for e in
            form.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in ("submit", "button")
            and e.get("name") != "csrfmiddlewaretoken"}


class JournalCase(TestCase):
    """A test case with the accounts ``kl`` (initials ``KL``, signed in
    by the tests that need it), ``ae`` and the staff account ``boss``,
    and the notebooks ``AE-1`` of ``kl`` and ``AE-2`` of ``ae``."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.first = make_notebook("AE-1", cls.kl)
        cls.second = make_notebook("AE-2", cls.ae, "Zweites Buch")

    def get(self, path: str, signed_in: bool = False) -> Any:
        """The parsed page ``path``, which answers 200."""
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return parse(response.content.decode("utf-8"))
