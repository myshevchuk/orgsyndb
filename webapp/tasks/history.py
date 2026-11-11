"""A task's change history as its page shows it."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import formats
from django.utils.translation import gettext as _

from registry.models import Substance
from tasks.models import Priority, Task

FIELDS = ["substance", "priority", "assignee", "started", "ended",
          "sequence", "sequence_steps", "steps_total", "steps_done",
          "batch", "report", "qc_list", "cancelled", "note"]


@dataclass(frozen=True)
class Change:
    """A field's change: its label and its old and new values as
    text."""

    label: str
    old: str
    new: str


@dataclass(frozen=True)
class Entry:
    """A record of the history: its time, the user who made it, or None,
    whether it created the task, and the changes it made otherwise."""

    time: Any
    user: Any
    created: bool
    changes: list[Change]


def shown(name: str, value: Any, users: dict[Any, Any],
          keys: dict[Any, str]) -> str:
    """Return VALUE of the task field NAME as the history shows it, in
    the active language; USERS maps account IDs to accounts and KEYS
    substance IDs to the substances' keys."""
    if value is None or value == "" or value == []:
        return "–"
    if name == "substance":
        return keys.get(value, str(value))
    if name == "priority":
        return str(Priority(value).label) if value in Priority.values \
            else str(value)
    if name == "assignee":
        user = users.get(value)
        return user.initials if user else str(value)
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if isinstance(value, date):
        return formats.date_format(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def history_entries(task: Task) -> list[Entry]:
    """Return the history of TASK, newest record first.

    The record that created the task has no changes; each later record
    lists the fields whose values differ from the record before it.
    """
    records = list(task.history.select_related("history_user"))
    fields = [Task._meta.get_field(name) for name in FIELDS]
    user_ids = {getattr(record, "assignee_id") for record in records}
    users = get_user_model().objects.in_bulk(
        [pk for pk in user_ids if pk is not None])
    keys = dict(Substance.objects.filter(
        pk__in={record.substance_id for record in records}).values_list(
            "pk", "key"))
    entries = []
    for position, record in enumerate(records):
        before = records[position + 1] if position + 1 < len(records) \
            else None
        changes = []
        if before is not None:
            for field in fields:
                old = getattr(before, field.attname)
                new = getattr(record, field.attname)
                if old != new:
                    changes.append(Change(
                        label=str(field.verbose_name),
                        old=shown(field.name, old, users, keys),
                        new=shown(field.name, new, users, keys)))
        entries.append(Entry(time=record.history_date,
                             user=record.history_user,
                             created=record.history_type == "+",
                             changes=changes))
    return entries
