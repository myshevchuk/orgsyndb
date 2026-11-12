"""Writing the demo data set into the database, and the questions the
``demo_data`` command asks of it first.

Every change of ``demo.data.changes`` is made through the application's
own write paths: the registry through ``registry.snapshot.load``, the
data set's import of the collection through ``collection.importing``,
as the manifest view receives one, counts and amounts through
``inventory.bookings``, tasks and their steps through their saves after
the validation the task form applies, and planning parameters through
their model's save after its own validation.
Each change is made with ``django.utils.timezone.now`` standing at its
moment, so that the times the write paths stamp, the
history records' among them, and the day they take as today are the
change's.
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from collection import importing
from collection.models import (EntrySubstance, Import, Outcome, Procedure,
                               ScopeEntry, Sequence, Step, Trigger,
                               latest_accepted)
from demo import data
from demo.models import DemoMark
from inventory import bookings
from inventory.models import (Article, DeliveryLine, DeliveryNote,
                              EnteredConsumption, Item, Lot, LotMovement,
                              Movement)
from orgsyndb_web import lock
from planning.models import Parameters
from registry import snapshot
from registry.models import Substance, SubstanceClass
from tasks.models import Counter, Task, TaskStep
from tasks.steps import StepChange
from vocabulary.models import ChemicalClass, Group, Project, ReactionType

# The demo registry: the snapshot of the demo collection's registry and
# the substance new-compound-7.
REGISTRY = Path(__file__).resolve().parent / "registry.json"
# The collection half of the demo collection's manifest, as
# ``tools/orgsyndb manifest`` prints it.
MANIFEST = Path(__file__).resolve().parent / "manifest.json"
# The commit the data set's import names, which no collection has.
DEMO_COMMIT = "0" * 40
DEMO_RELEASE = "demo"
DEFAULT_LANGUAGE = "de"
TERMS = (ChemicalClass, Group, Project, ReactionType)


@dataclass(frozen=True)
class Summary:
    """What a seed wrote: the number of each kind of record."""

    accounts: int
    substances: int
    items: int
    notes: int
    tasks: int


def histories() -> list[type]:
    """Return the historical models of every record that keeps a change
    history."""
    return [model for model in apps.get_models()
            if model.__name__.startswith("Historical")]


def holds_records() -> bool:
    """Whether the database holds lab records: an account, substance,
    vocabulary term, article, task, item, delivery note, bulk lot,
    entered consumption value, stored planning parameters, import of
    the collection, imported procedure or sequence, change-history
    record or the demo mark."""
    return any(model.objects.exists() for model in (
        get_user_model(), Substance, *TERMS, Article, Task, Item,
        DeliveryNote, Lot, EnteredConsumption, Parameters, Import,
        Procedure, Sequence, DemoMark, *histories()))


def language() -> str:
    """Return the language of the latest accepted import the database
    holds, or ``de`` when it holds none."""
    latest = latest_accepted()
    return latest.language if latest is not None else DEFAULT_LANGUAGE


def is_demo() -> bool:
    """Whether the database holds the demo mark."""
    return DemoMark.objects.exists()


def clear() -> None:
    """Delete every lab record, with its movements, lines and change
    history, and set the task counter to zero. The caller provides the
    transaction, in which the lock (``orgsyndb_web.lock``) is taken
    first.

    Reversals go before the movements they reverse, movements before
    the notes, lots and task steps they name, lots before the task steps
    that made them, records before the substances and terms they name,
    tasks and their steps before the sequences, entries and imports they
    name, sequence steps before the entries they name, and terms and
    imports are taken out of their trees and chains before they are
    deleted, as each protects the other otherwise.
    """
    lock.hold()
    Movement.objects.exclude(reverses=None).delete()
    Movement.objects.all().delete()
    DeliveryLine.objects.all().delete()
    DeliveryNote.objects.all().delete()
    LotMovement.objects.exclude(reverses=None).delete()
    LotMovement.objects.all().delete()
    Lot.objects.all().delete()
    TaskStep.objects.all().delete()
    Task.objects.all().delete()
    Step.objects.all().delete()
    Sequence.objects.all().delete()
    EntrySubstance.objects.all().delete()
    ScopeEntry.objects.all().delete()
    Procedure.objects.all().delete()
    Import.objects.update(base=None)
    Import.objects.all().delete()
    EnteredConsumption.objects.all().delete()
    Item.objects.all().delete()
    Article.objects.all().delete()
    SubstanceClass.objects.all().delete()
    Substance.objects.all().delete()
    for model in TERMS:
        if model is not ReactionType:
            model.objects.update(parent=None)
        model.objects.all().delete()
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
    """Write the data set as of TODAY, its texts and its own import of
    the demo collection in LANGUAGE, into a database without lab
    records, and mark the database as a demo database seeded on
    TODAY.

    The caller provides the transaction. Raise ``bookings.Refused`` or
    ValidationError when a change is refused.
    """
    writer = _Writer()
    for change in data.changes(today, language):
        with clock(change.moment):
            writer.make(change)
    DemoMark.objects.create(seeded_on=today)
    return Summary(accounts=len(writer.users),
                   substances=Substance.objects.count(),
                   items=len(writer.items), notes=len(writer.notes),
                   tasks=len(writer.tasks))


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
            case data.LoadRegistry():
                snapshot.load(json.loads(REGISTRY.read_text(
                    encoding="utf-8")), user)
            case data.RecordImport(language=language):
                record_import(change.moment, language)
            case data.SaveParameters(fields=fields):
                self.save_parameters(user, fields)
            case data.OpenItem():
                self.items[change.key] = bookings.create_item(
                    user, substance=Substance.objects.get(
                        key=change.substance),
                    article_number=change.article_number,
                    size=change.size, unit=change.unit,
                    quantity=change.quantity, category=change.category,
                    compartment=change.compartment, box=change.box,
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
                    user, substance=Substance.objects.get(
                        key=change.substance),
                    source=change.source, supplier=change.supplier,
                    unit=change.unit, amount=change.amount,
                    batch=change.batch, location=change.location,
                    made_on=change.made_on, date=day,
                    task_step=self.step(*change.step) if change.step
                    else None)
            case data.Withdraw():
                bookings.withdraw(user, self.lots[change.lot],
                                  task_step=self.step(change.task,
                                                      change.position),
                                  amount=change.amount, date=day)
            case data.Fill():
                bookings.fill(user, self.items[change.item],
                              count=change.count, date=day,
                              lot=self.lots[change.lot] if change.lot
                              else None, amount=change.amount)
            case data.SetStatus():
                item = Item.objects.get(pk=self.items[change.item].pk)
                item.status = change.status
                item._history_user = user
                item.save(update_fields=["status"])
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

    def step(self, task: str, position: int) -> TaskStep:
        """Return the step at POSITION of the task TASK."""
        return self.tasks[task].steps.get(position=position)

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
        validation the task form applies, and give it its steps; its
        number is assigned on creation. Raise ValidationError when the
        task or its steps are refused."""
        task = self.tasks.get(key) or Task(created_by=user)
        done, total = task.step_counts
        sequence = task.sequence
        for name, value in fields.items():
            if name == "assignee":
                setattr(task, name, self.users[value] if value else None)
            elif name == "substance":
                task.substance = Substance.objects.get(key=value)
            elif name == "sequence":
                sequence = Sequence.objects.get(key=value) if value \
                    else None
            elif name == "steps_total":
                total = value
            elif name == "steps_done":
                done = value
            else:
                setattr(task, name, value)
        task.full_clean(exclude=["number", "sequence"])
        steps = StepChange(task, sequence, total, done)
        errors = steps.errors()
        if errors:
            raise ValidationError(errors)
        task.sequence = sequence
        task._history_user = user
        task.save()
        steps.apply(timezone.localdate(), user)
        self.tasks[key] = task


def record_import(moment: datetime, language: str) -> Import:
    """Record the data set's own accepted import of the demo collection,
    ``MANIFEST``, committed and received at MOMENT, with the commit and
    tooling of forty zeros, the release ``demo``, the trigger
    ``catch-up``, no base, the current snapshot's digest and LANGUAGE,
    through ``collection.importing`` as the manifest view receives a
    manifest; return it. The database must hold the registry the
    manifest names and no accepted import. Raise ValidationError when
    the import is not accepted."""
    collection = json.loads(MANIFEST.read_text(encoding="utf-8"))
    body = {**collection, "format": importing.FORMAT,
            "build": str(uuid.uuid4()), "commit": DEMO_COMMIT,
            "committed_at": moment.isoformat(), "base": None,
            "snapshot": snapshot.build()["digest"], "tooling": DEMO_COMMIT,
            "trigger": Trigger.CATCH_UP.value, "outcome": "built",
            "release": DEMO_RELEASE, "language": language}
    _status, answer = importing.receive(importing.read(body))
    if answer["outcome"] != Outcome.ACCEPTED:
        raise ValidationError(
            f"the demo collection was not accepted: {answer}")
    return Import.objects.get(pk=answer["import"])
