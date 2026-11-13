"""A task's change history as its page shows it: the task's records and
its steps', newest first."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import formats
from django.utils.translation import gettext as _

from collection.models import Import, ScopeEntry, Sequence
from journal.models import Entry as JournalEntry
from registry.models import Substance
from tasks.models import Priority, Task, TaskStep

FIELDS = ["substance", "priority", "assignee", "started", "ended",
          "sequence", "start_step", "batch", "report", "qc_list",
          "cancelled", "failed", "note"]
STEP_FIELDS = ["position", "entry", "planned_import", "done_on",
               "journal_entry"]


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
    the HEADING of a step's record, ``Step <n>`` or ``Step <n>
    removed`` in the active language, empty for the task's, whether it
    CREATED the task or the step, and the CHANGES it made otherwise."""

    time: Any
    user: Any
    heading: str
    created: bool
    changes: list[Change]


def shown(name: str, value: Any, names: dict[str, dict[Any, str]]) -> str:
    """Return VALUE of the field NAME of a task or a step as the history
    shows it, in the active language. NAMES maps the IDs of the
    accounts, substances, sequences, scope entries, imports and journal
    entries the records name, under ``assignee``, ``substance``,
    ``sequence``, ``entry``, ``planned_import`` and ``journal_entry``,
    to the text that shows each."""
    if value is None or value == "":
        return "–"
    if name in names:
        return names[name].get(value, str(value))
    if name == "priority":
        return str(Priority(value).label) if value in Priority.values \
            else str(value)
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if isinstance(value, date):
        return formats.date_format(value)
    return str(value)


def _names(records: list[Any], steps: list[Any]) -> dict[str, dict]:
    """Return the texts that show the records the task's RECORDS and
    its STEPS' records name, as ``shown`` takes them."""

    def ids(rows: list[Any], attname: str) -> set[Any]:
        return {getattr(row, attname) for row in rows} - {None}

    users = get_user_model().objects.in_bulk(ids(records, "assignee_id"))
    entries = ScopeEntry.objects.select_related("procedure").in_bulk(
        ids(steps, "entry_id"))
    return {
        "assignee": {pk: user.initials for pk, user in users.items()},
        "substance": dict(Substance.objects.filter(
            pk__in=ids(records, "substance_id")).values_list("pk", "key")),
        "sequence": dict(Sequence.objects.filter(
            pk__in=ids(records, "sequence_id")).values_list("pk", "key")),
        "entry": {pk: str(entry) for pk, entry in entries.items()},
        "planned_import": {pk: str(found) for pk, found in
                           Import.objects.in_bulk(
                               ids(steps, "planned_import_id")).items()},
        "journal_entry": {pk: str(found) for pk, found in
                          JournalEntry.objects.select_related(
                              "notebook").in_bulk(
                                  ids(steps, "journal_entry_id")).items()},
    }


def _changes(record: Any, before: Any, fields: list[Any],
             names: dict[str, dict]) -> list[Change]:
    """Return the changes of the history RECORD from the record BEFORE
    it in the FIELDS given."""
    return [Change(label=str(field.verbose_name),
                   old=shown(field.name, getattr(before, field.attname),
                             names),
                   new=shown(field.name, getattr(record, field.attname),
                             names))
            for field in fields
            if getattr(before, field.attname)
            != getattr(record, field.attname)]


def history_entries(task: Task) -> list[Entry]:
    """Return the history of TASK and of its steps, removed ones among
    them, newest record first.

    A record that created the task or a step has no changes. A later
    record of the task lists the fields whose values differ from its
    record before, and a later record of a step likewise, under the
    heading ``Step <n>`` in the active language; a record that changes
    no field is left out. A step's removal is headed ``Step <n>
    removed``. Of records made at one moment, the steps' count as the
    newer.
    """
    records = list(task.history.select_related("history_user")
                   .order_by("history_id"))
    steps = list(TaskStep.history.filter(task_id=task.pk)
                 .select_related("history_user").order_by("history_id"))
    names = _names(records, steps)
    fields = [Task._meta.get_field(name) for name in FIELDS]
    step_fields = [TaskStep._meta.get_field(name) for name in STEP_FIELDS]
    found: list[tuple[tuple[Any, ...], Entry]] = []
    for number, record in enumerate(records):
        changes = [] if not number else _changes(
            record, records[number - 1], fields, names)
        if number and not changes:
            continue
        found.append(((record.history_date, 0, record.history_id), Entry(
            time=record.history_date, user=record.history_user,
            heading="", created=record.history_type == "+",
            changes=changes)))
    last: dict[Any, Any] = {}
    for record in steps:
        before = last.get(record.id)
        last[record.id] = record
        if record.history_type == "-":
            heading = _("Step %(position)s removed") % {
                "position": record.position}
            changes = []
        else:
            heading = _("Step %(position)s") % {"position": record.position}
            changes = [] if before is None else _changes(
                record, before, step_fields, names)
            if before is not None and record.history_type == "~" \
                    and not changes:
                continue
        found.append(((record.history_date, 1, record.history_id), Entry(
            time=record.history_date, user=record.history_user,
            heading=heading, created=record.history_type == "+",
            changes=changes)))
    return [entry for _key, entry in sorted(found, key=lambda pair: pair[0],
                                            reverse=True)]
