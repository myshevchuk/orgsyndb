"""Fixtures and helpers shared by the tests of the demo data (lab-demo).

Nothing here imports the ``demo`` package at module level, so that the
tests fail on their assertions while the package is missing.
"""

import io
import re
from datetime import date, datetime, timedelta
from typing import Any

from django.core.management import call_command
from django.test import TestCase, override_settings

from . import BERLIN, frozen, parse

# The days the data set is seeded as of in the tests that check its
# outcomes: the start, middle and end of quarters, a day whose order
# window holds six quarters, and a leap day.
SEEDING_DAYS = [date(2026, 1, 1), date(2026, 2, 14), date(2026, 3, 31),
                date(2026, 11, 7), date(2028, 2, 29)]
DAY = date(2026, 11, 7)
OPENING_DAYS = 400
DEMO_PASSWORD = "demo"
ACCOUNTS = {
    "klehmann": ("Katrin Lehmann", "KL"),
    "tbauer": ("Tobias Bauer", "TB"),
    "aschmidt": ("Anna Schmidt", "AS"),
    "jkoch": ("Jonas Koch", "JK"),
    "mwolf": ("Miriam Wolf", "MW"),
}
SIGNING_IN = ["klehmann", "tbauer", "aschmidt", "jkoch"]
ARTICLES = ["CH-0001", "CH-0002", "CH-0010", "CH-0012", "CH-0013",
            "CH-0016", "NV-0007"]
# The demo's position without an article number, named as its compound.
NUMBERLESS = ("1-Phenylethanol", "1-phenylethanol")
LEVELS = ["out", "critical", "low", "watch", "ok", "undelivered",
          "dormant"]
NOTE_NUMBER = re.compile(r"^LS-(\d{4})-(\d{3})$")
PLAN = "/lab/planning/"
ITEMS = "/lab/inventory/end-products/"
DELIVERIES = "/lab/inventory/deliveries/"
TASKS = "/lab/tasks/"
LOGIN = "/lab/accounts/login/"


def opening(day: date) -> date:
    """The opening day of the inventory seeded as of DAY."""
    return day - timedelta(days=OPENING_DAYS)


def noon(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, tzinfo=BERLIN)


def run(*args: str, demo: bool = True) -> tuple[str, str]:
    """Run ``demo_data`` with ARGS, with ``ORGSYNDB_DEMO`` set to DEMO;
    return its output and its errors. CommandError and every other
    exception propagate."""
    out, err = io.StringIO(), io.StringIO()
    with override_settings(ORGSYNDB_DEMO=demo):
        call_command("demo_data", *args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


def seed(day: date) -> tuple[str, str]:
    """Write the data set as of DAY, with the clock at noon of DAY."""
    with frozen(noon(day)):
        return run()


def lab_records() -> dict[str, int]:
    """The number of each kind of lab record the database holds."""
    from django.contrib.auth import get_user_model
    from inventory.models import (Article, DeliveryNote, EnteredConsumption,
                                  Item, Lot, Movement)
    from planning.models import Parameters
    from registry.models import Substance
    from tasks.models import Task
    from vocabulary.models import (ChemicalClass, Group, Project,
                                   ReactionType)
    return {
        "accounts": get_user_model().objects.count(),
        "substances": Substance.objects.count(),
        "terms": sum(model.objects.count() for model in (
            ChemicalClass, Group, Project, ReactionType)),
        "articles": Article.objects.count(),
        "tasks": Task.objects.count(),
        "items": Item.objects.count(),
        "movements": Movement.objects.count(),
        "notes": DeliveryNote.objects.count(),
        "lots": Lot.objects.count(),
        "consumption": EnteredConsumption.objects.count(),
        "parameters": Parameters.objects.count(),
    }


def task_counter() -> int:
    from tasks.models import Counter
    found = Counter.objects.filter(name="task").values_list("value",
                                                           flat=True)
    return found.first() or 0


class SeededCase(TestCase):
    """A test case whose database holds the data set written as of DAY,
    with the clock at the afternoon of DAY in every test."""

    DAY = DAY

    @classmethod
    def setUpTestData(cls) -> None:
        cls.output = seed(cls.DAY)

    def setUp(self) -> None:
        self.enterContext(frozen(datetime(
            self.DAY.year, self.DAY.month, self.DAY.day, 19,
            tzinfo=BERLIN)))

    def get(self, path: str) -> Any:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return parse(response.content.decode("utf-8"))

    def account(self, username: str) -> Any:
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(username=username)

    def items(self, article: str | None) -> list[Any]:
        from inventory.models import Item
        if article is None:
            return list(Item.objects.filter(
                article__article_number__isnull=True))
        return list(Item.objects.filter(
            article__article_number=article))
