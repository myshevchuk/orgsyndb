"""Writing the demo data set into the database, and the questions the
``demo_data`` command asks of it first.

Every change of ``demo.data.changes`` is made through the application's
own write paths: counts and amounts through ``inventory.bookings``,
tasks and planning parameters through their models' saves after their
own validation. Each change is made with ``django.utils.timezone.now``
standing at its moment, so that the times the write paths stamp, the
history records' among them, and the day they take as today are the
change's.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model

from demo import data
from demo.models import DemoMark
from inventory import bookings
from inventory.models import (DeliveryLine, DeliveryNote, EnteredConsumption,
                              Item, Lot, LotMovement, Movement)
from orgsyndb_web import index
from planning.models import Parameters
from tasks.models import Counter, Task


@dataclass(frozen=True)
class Summary:
    """What a seed wrote: the number of each kind of record."""

    accounts: int
    items: int
    notes: int
    tasks: int


def histories() -> list[type]:
    """Return the historical models of every record that keeps a change
    history."""
    return [model for model in apps.get_models()
            if model.__name__.startswith("Historical")]


def holds_records() -> bool:
    """Whether the database holds lab records: an account, task, item,
    delivery note, bulk lot, entered consumption value, stored planning
    parameters, change-history record or the demo mark."""
    return any(model.objects.exists() for model in (
        get_user_model(), Task, Item, DeliveryNote, Lot,
        EnteredConsumption, Parameters, DemoMark, *histories()))


def is_demo() -> bool:
    """Whether the database holds the demo mark."""
    return DemoMark.objects.exists()


def missing_compounds() -> int:
    """Return how many of the compounds of ``examples/demo`` the data set
    names the collection index lacks."""
    return sum(index.compound_for(number) is None
               for number in data.compounds())


def clear() -> None:
    """Delete every lab record, with its movements, lines and change
    history, and set the task counter to zero.

    Reversals go before the movements they reverse and movements before
    the notes and lots they name, which protect them otherwise.
    """
    Movement.objects.exclude(reverses=None).delete()
    Movement.objects.all().delete()
    DeliveryLine.objects.all().delete()
    DeliveryNote.objects.all().delete()
    LotMovement.objects.all().delete()
    Lot.objects.all().delete()
    EnteredConsumption.objects.all().delete()
    Item.objects.all().delete()
    Task.objects.all().delete()
    Parameters.objects.all().delete()
    DemoMark.objects.all().delete()
    for model in histories():
        model.objects.all().delete()
    get_user_model().objects.all().delete()
    Counter.objects.filter(name="task").update(value=0)


@contextmanager
def clock(moment: datetime) -> Iterator[None]:
    """Make ``django.utils.timezone.now`` return MOMENT for the length of
    the block."""
    with mock.patch("django.utils.timezone.now", return_value=moment):
        yield


def write(today: date, language: str) -> Summary:
    """Write the data set as of TODAY, its texts in LANGUAGE, into a
    database without lab records, and mark the database as a demo
    database seeded on TODAY.

    The caller provides the transaction. Raise ``bookings.Refused`` or
    ValidationError when a change is refused.
    """
    writer = _Writer()
    for change in data.changes(today, language):
        with clock(change.moment):
            writer.make(change)
    DemoMark.objects.create(seeded_on=today)
    return Summary(accounts=len(writer.users), items=len(writer.items),
                   notes=len(writer.notes), tasks=len(writer.tasks))


class _Writer:
    """The records the changes made so far, by their keys."""

    def __init__(self) -> None:
        self.users: dict[str, Any] = {}
        self.items: dict[str, Item] = {}
        self.lots: dict[str, Lot] = {}
        self.notes: dict[str, DeliveryNote] = {}
        self.tasks: dict[str, Task] = {}
        self.parameters: Parameters | None = None

    def make(self, change: data.Change) -> None:
        """Make CHANGE through the write path of its kind."""
        user = self.users.get(change.user)
        day = change.moment.date()
        match change:
            case data.CreateAccount(account=account):
                self.users[account.username] = self.account(change)
            case data.SaveParameters(fields=fields):
                self.save_parameters(user, fields)
            case data.OpenItem():
                self.items[change.key] = bookings.create_item(
                    user, article_number=change.article_number,
                    name=change.name, size=change.size, unit=change.unit,
                    quantity=change.quantity, category=change.category,
                    date=day)
            case data.EnterConsumption():
                bookings.enter_consumption(
                    user, self.items[change.item], year=change.year,
                    quarter=change.quarter, count=change.count)
            case data.BookNote():
                self.notes[change.number] = bookings.book_note(
                    user, date=change.day,
                    lines=[(self.items[key], count)
                           for key, count in change.lines],
                    number=change.number, recipient=change.recipient,
                    historical=change.historical)
            case data.ReverseNote():
                self.notes[change.number] = bookings.reverse_historical(
                    user, self.notes[change.number], note=change.note)
            case data.ReverseDelivery():
                movement = Movement.objects.get(
                    delivery_note=self.notes[change.number],
                    item=self.items[change.item],
                    kind=Movement.Kind.DELIVERY)
                bookings.reverse(user, movement, note=change.note)
            case data.OpenLot():
                self.lots[change.key] = bookings.create_lot(
                    user, article_number=change.article_number,
                    unit=change.unit, amount=change.amount,
                    batch=change.batch, location=change.location,
                    made_on=change.made_on, date=day)
            case data.Fill():
                bookings.fill(user, self.items[change.item],
                              count=change.count, date=day,
                              lot=self.lots[change.lot],
                              amount=change.amount)
            case data.Correct():
                bookings.correct(user, self.items[change.item],
                                 count=change.count, note=change.note,
                                 date=day)
            case data.CorrectLot():
                bookings.correct_lot(user, self.lots[change.lot],
                                     amount=change.amount, note=change.note,
                                     date=day)
            case data.SaveTask():
                self.save_task(user, change.key, change.fields)
            case _:
                raise TypeError(f"unknown change: {change!r}")

    def account(self, change: data.CreateAccount) -> Any:
        """Create the account of CHANGE, with the password
        ``data.PASSWORD`` or none usable, joined at the change's
        moment."""
        account = change.account
        return get_user_model().objects.create_user(
            username=account.username,
            password=data.PASSWORD if account.signs_in else None,
            first_name=account.first_name, last_name=account.last_name,
            initials=account.initials, is_staff=account.superuser,
            is_superuser=account.superuser, date_joined=change.moment)

    def save_parameters(self, user: Any, fields: dict[str, Any]) -> None:
        """Store the planning parameters with FIELDS, or change the
        stored ones, as USER, after their own validation."""
        record = self.parameters or Parameters()
        for name, value in fields.items():
            setattr(record, name, value)
        record.full_clean()
        record._history_user = user
        record.save()
        self.parameters = record

    def save_task(self, user: Any, key: str, fields: dict[str, Any]
                  ) -> None:
        """Create the task KEY, made by USER, or change it, after the
        validation the task form applies; its number is assigned on
        creation."""
        task = self.tasks.get(key) or Task(created_by=user)
        for name, value in fields.items():
            if name == "assignee":
                value = self.users[value] if value else None
            setattr(task, name, value)
        task.full_clean(exclude=["number"])
        task._history_user = user
        task.save()
        self.tasks[key] = task
