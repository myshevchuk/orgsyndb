"""The steps a save gives a task: from its sequence, or plain steps as
many as a total, the first of them done (task-tracker "Task record",
"Task forms")."""

from datetime import date
from typing import Any

from django.utils.translation import gettext as _

from collection.models import Sequence, latest_accepted
from tasks.models import Task, TaskStep


class StepChange:
    """A save's change of the steps of TASK: its sequence becoming
    SEQUENCE, a sequence or None, the plain steps TOTAL, a number or
    None, and the first DONE steps done.

    The change compares SEQUENCE with the sequence the database holds
    for TASK, none for a task not saved yet, so it is made before the
    task is saved with SEQUENCE. A sequence set, changed or cleared
    replaces the steps; a sequence kept keeps them and ignores TOTAL;
    without a sequence before or after, TOTAL adds plain steps at the
    end or removes the last ones.
    """

    def __init__(self, task: Task, sequence: Sequence | None,
                 total: int | None, done: int) -> None:
        self.task = task
        self.sequence = sequence
        self.total = total
        self.done = done
        self.stored_sequence: Any = None
        self.stored: list[TaskStep] = []
        if task.pk:
            self.stored_sequence = Task.objects.values_list(
                "sequence_id", flat=True).get(pk=task.pk)
            self.stored = list(task.steps.order_by("position"))

    @property
    def replaces(self) -> bool:
        """Whether the save sets, changes or clears the sequence."""
        return (None if self.sequence is None
                else self.sequence.pk) != self.stored_sequence

    def planned(self) -> list[tuple[Any, Any]]:
        """Return the entry and the planned import of each step the task
        has after the save, in order."""
        if self.sequence is not None and not self.replaces:
            return [(step.entry_id, step.planned_import_id)
                    for step in self.stored]
        if self.sequence is not None:
            latest = latest_accepted()
            return [(step.entry_id, None if latest is None else latest.pk)
                    for step in self.sequence.steps.order_by("position")]
        return [(None, None)] * (self.total or 0)

    def errors(self) -> dict[str, str]:
        """Return the errors that refuse the change, by form field.

        A sequence set or changed may not be withdrawn; the sequence may
        not be set, changed or cleared while a stored step is done; the
        steps done may not exceed the steps the task has after the save;
        without a sequence, the total may not fall below the stored
        steps done; and a step that made a lot or took a withdrawal may
        not be removed.
        """
        errors = {}
        done_before = sum(step.done_on is not None for step in self.stored)
        booked = any(step.lots.exists() or step.lot_movements.exists()
                     for step in self.stored)
        if self.replaces and done_before:
            errors["sequence"] = _(
                "The sequence cannot be set, changed or cleared while a "
                "step is done.")
        elif self.replaces and booked:
            errors["sequence"] = _(
                "The sequence cannot be set, changed or cleared while a "
                "step has made a lot or taken a withdrawal.")
        elif self.replaces and self.sequence is not None \
                and self.sequence.withdrawn:
            errors["sequence"] = _(
                "The sequence %(key)s is no longer in the collection.") % {
                    "key": self.sequence.key}
        elif self.sequence is None and (self.total or 0) < done_before:
            errors["steps_total"] = _(
                "The steps total may not be below the %(done)s steps "
                "done.") % {"done": done_before}
        count = len(self.planned())
        if "sequence" not in errors and "steps_total" not in errors and any(
                step.lots.exists() or step.lot_movements.exists()
                for step in self.stored[count:]):
            errors["sequence" if self.replaces else "steps_total"] = _(
                "A step that made a lot or took a withdrawal cannot be "
                "removed.")
        if self.done > count:
            errors["steps_done"] = (
                _("Steps done may not exceed the %(count)s steps of the "
                  "task.") % {"count": count} if count
                else _("Steps done need steps."))
        return errors

    def apply(self, today: date, user: Any = None) -> None:
        """Give the saved task its steps, marking the first DONE of them
        done, those done before keeping their days and the others taking
        TODAY, and the rest not done; record each step created, changed
        or removed in its history as made by USER, or by the request's
        user when USER is None.

        The change must be free of errors (``errors``), and the caller
        provides the transaction.
        """
        held = {step.position: step for step in self.stored}
        for position, (entry, planned) in enumerate(self.planned(),
                                                    start=1):
            step = held.pop(position, None) or TaskStep(
                task=self.task, position=position)
            done_on = (step.done_on or today) if position <= self.done \
                else None
            if step.pk is None or (step.entry_id, step.planned_import_id,
                                   step.done_on) != (entry, planned,
                                                     done_on):
                step.entry_id = entry
                step.planned_import_id = planned
                step.done_on = done_on
                if user is not None:
                    step._history_user = user
                step.save()
        for gone in held.values():
            if user is not None:
                gone._history_user = user
            gone.delete()


def finish(task: Task, today: date, first_only: bool) -> None:
    """Mark the first step of TASK not done, or every such step unless
    FIRST_ONLY, done on TODAY. The caller provides the transaction."""
    for step in task.steps.filter(done_on=None).order_by("position"):
        step.done_on = today
        step.save(update_fields=["done_on"])
        if first_only:
            break
