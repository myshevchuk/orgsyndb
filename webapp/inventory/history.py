"""The change history of an item, a batch, a vessel or a delivery note as
its page shows it; an item's includes that of its entered
consumption."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import models
from django.utils import formats
from django.utils.translation import gettext as _

from inventory.models import EnteredConsumption, Item, Unit, plain
from inventory.models import shown as in_unit
from journal.models import Entry as JournalEntry

FIELDS = {
    "item": ["status", "stocked_on", "compartment", "box", "note"],
    "batch": ["number", "journal_entry", "yield_amount", "supplier",
              "supplier_article_number", "supplier_batch", "date", "note"],
    "vessel": ["location", "note"],
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
    """A record of the history: its TIME, the USER who made it, or None,
    its HEADING, ``Consumption Q<n> <year>`` in the active language for
    a record of entered consumption and empty for the others, whether it
    CREATED the record, and the CHANGES it made otherwise."""

    time: Any
    user: Any
    heading: str
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


def shown_field(field: models.Field, value: Any) -> str:
    """Return VALUE of FIELD as the history shows it: a choice by its
    label, any other value as ``shown`` writes it."""
    labels = dict(field.flatchoices) if field.choices else {}
    return str(labels[value]) if value in labels else shown(value)


def _raw(row: Any, field: models.Field) -> Any:
    """Return the value of FIELD in the history record ROW that a change
    compares: the yield with its unit, any other field as stored."""
    if field.name == "yield_amount":
        return (row.yield_amount, row.yield_unit)
    return getattr(row, field.attname)


def _text(field: models.Field, value: Any, entries: dict[int, str]) -> str:
    """Return VALUE, as ``_raw`` gives it, of FIELD as the history shows
    it: a journal entry as ``<code>/<number>``, a yield in its unit, any
    other value as ``shown_field`` writes it."""
    if field.name == "journal_entry":
        return entries.get(value, "–") if value else "–"
    if field.name == "yield_amount":
        amount, unit = value
        if amount is None:
            return "–"
        return f"{shown(in_unit(amount, unit))} {Unit(unit).label}"
    return shown_field(field, value)


def _own(record: models.Model) -> list[tuple[Any, Entry]]:
    """Return the history records of RECORD, each with its entry, newest
    record first.

    The record that created it has no changes; each later record lists
    the fields, of those its page shows, whose values differ from the
    record before it.
    """
    records = list(record.history.select_related("history_user"))
    fields = [type(record)._meta.get_field(name)
              for name in FIELDS[type(record)._meta.model_name]]
    ids = {row.journal_entry_id for row in records
           if hasattr(row, "journal_entry_id")} - {None}
    entries = {entry.pk: str(entry) for entry in
               JournalEntry.objects.select_related("notebook").filter(
                   pk__in=ids)}
    found = []
    for position, current in enumerate(records):
        before = records[position + 1] if position + 1 < len(records) \
            else None
        changes = []
        if before is not None:
            for field in fields:
                old = _raw(before, field)
                new = _raw(current, field)
                if old != new:
                    changes.append(Change(
                        label=str(field.verbose_name),
                        old=_text(field, old, entries),
                        new=_text(field, new, entries)))
        found.append((current, Entry(
            time=current.history_date, user=current.history_user,
            heading="", created=current.history_type == "+",
            changes=changes)))
    return found


def _consumption(item: Item) -> list[tuple[Any, Entry]]:
    """Return the history records of the entered consumption of ITEM,
    each with its entry, in the order they were recorded.

    A record lists the quarter's count as a change from the count of the
    record before it for the same year and quarter, removals included,
    from none (``–``) when there is none, to none for a removal.
    """
    label = str(EnteredConsumption._meta.get_field("count").verbose_name)
    counts: dict[tuple[int, int], int | None] = {}
    found = []
    for record in EnteredConsumption.history.filter(
            item_id=item.pk).select_related("history_user").order_by(
                "history_id"):
        key = (record.year, record.quarter)
        new = None if record.history_type == "-" else record.count
        found.append((record, Entry(
            time=record.history_date, user=record.history_user,
            heading=_("Consumption Q%(quarter)s %(year)s") % {
                "quarter": record.quarter, "year": record.year},
            created=False,
            changes=[Change(label=label, old=shown(counts.get(key)),
                            new=shown(new))])))
        counts[key] = new
    return found


def history_entries(record: models.Model) -> list[Entry]:
    """Return the history of RECORD, an item, a lot or a delivery note,
    newest record first.

    The record that created it has no changes; each later record lists
    the fields, of those its page shows, whose values differ from the
    record before it. An item's history also holds the entries of its
    entered consumption, headed ``Consumption Q<quarter> <year>`` in the
    active language, each listing the change of that quarter's count
    (``Entry`` and ``_consumption``); the entries then follow one
    another by time, and of those made at one moment the consumption's
    come first.
    """
    own = _own(record)
    if not isinstance(record, Item):
        return [entry for _record, entry in own]
    found = [((each.history_date, 0, each.history_id), entry)
             for each, entry in own]
    found += [((each.history_date, 1, each.history_id), entry)
              for each, entry in _consumption(record)]
    return [entry for _key, entry in sorted(found, key=lambda pair: pair[0],
                                            reverse=True)]
