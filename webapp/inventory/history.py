"""The change history of an item, a lot or a delivery note as its page
shows it."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import models
from django.utils import formats
from django.utils.translation import gettext as _

from inventory.models import plain

FIELDS = {
    "item": ["name", "category", "note"],
    "lot": ["batch", "location", "made_on", "note"],
    "deliverynote": ["number", "recipient", "note", "reversed",
                     "reversal_note"],
}


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
    whether it created the record, and the changes it made otherwise."""

    time: Any
    user: Any
    created: bool
    changes: list[Change]


def shown(value: Any) -> str:
    """Return VALUE as the history shows it, in the active language."""
    if value is None or value == "":
        return "–"
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if isinstance(value, date):
        return formats.date_format(value)
    if isinstance(value, Decimal):
        return formats.number_format(plain(value))
    return str(value)


def history_entries(record: models.Model) -> list[Entry]:
    """Return the history of RECORD, an item, a lot or a delivery note,
    newest record first.

    The record that created it has no changes; each later record lists
    the fields, of those its page shows, whose values differ from the
    record before it.
    """
    records = list(record.history.select_related("history_user"))
    fields = [type(record)._meta.get_field(name)
              for name in FIELDS[type(record)._meta.model_name]]
    entries = []
    for position, current in enumerate(records):
        before = records[position + 1] if position + 1 < len(records) \
            else None
        changes = []
        if before is not None:
            for field in fields:
                old = getattr(before, field.attname)
                new = getattr(current, field.attname)
                if old != new:
                    changes.append(Change(label=str(field.verbose_name),
                                          old=shown(old), new=shown(new)))
        entries.append(Entry(time=current.history_date,
                             user=current.history_user,
                             created=current.history_type == "+",
                             changes=changes))
    return entries
