"""The steps a save gives a task: from its sequence, from the step it
starts at, or plain steps as many as a total, the first of them done
(task-tracker "Task record", "Task forms")."""

from datetime import date
from typing import Any

from django.utils.translation import gettext as _

from collection.models import Sequence, latest_accepted
from tasks.models import Task, TaskStep


class StepChange:
    """A save's change of the steps of TASK: its sequence becoming
    SEQUENCE, a sequence or None, from its step START on, its substance
    becoming SUBSTANCE, the plain steps TOTAL, a number or None, and
    the first DONE steps done.

    The change compares SEQUENCE and START with the sequence and the
    start step the database holds for TASK, none and 1 for a task not
    saved yet, so it is made before the task is saved with them. A
    sequence set, changed or cleared, or a start step changed with a
    sequence, plans the steps anew; a sequence and start step kept keep
    the steps and ignore TOTAL; without a sequence before or after,
    TOTAL adds plain steps at the end or removes the last ones, and
    START is taken as 1.
    """

    def __init__(self, task: Task, sequence: Sequence | None,
                 total: int | None, done: int, start: int = 1,
                 substance: Any = None) -> None:
        self.task = task
        self.sequence = sequence
        self.start = start if sequence is not None else 1
        self.substance = substance
        self.total = total
        self.done = done
        self.stored_sequence: Any = None
        self.stored_start = 1
        self.stored: list[TaskStep] = []
        if task.pk:
            self.stored_sequence, self.stored_start = (
                Task.objects.values_list("sequence_id", "start_step")
                .get(pk=task.pk))
            self.stored = list(task.steps.order_by("position"))

    @property
    def changes_sequence(self) -> bool:
        """Whether the save sets, changes or clears the sequence."""
        return (None if self.sequence is None
                else self.sequence.pk) != self.stored_sequence

    @property
    def replaces(self) -> bool:
        """Whether the save plans the steps anew: it sets, changes or
        clears the sequence, or changes the start step of a task that
        keeps one."""
        return self.changes_sequence or (
            self.sequence is not None and self.start != self.stored_start)

    def planned(self) -> list[tuple[Any, Any]]:
        """Return the entry and the planned import of each step the task
        has after the save, in order."""
        if self.sequence is not None and not self.replaces:
            return [(step.entry_id, step.planned_import_id)
                    for step in self.stored]
        if self.sequence is not None:
            latest = latest_accepted()
            return [(step.entry_id, None if latest is None else latest.pk)
                    for step in self.sequence.steps.filter(
                        position__gte=self.start).order_by("position")]
        return [(None, None)] * (self.total or 0)

    def _plan_errors(self) -> dict[str, str]:
        """Return the errors that refuse planning the steps anew, at the
        field the save changes: ``sequence`` when it sets, changes or
        clears the sequence, else ``start_step``; an error of the
        sequence's target is always at ``sequence``."""
        by_sequence = self.changes_sequence
        field = "sequence" if by_sequence else "start_step"
        if any(step.done_on is not None for step in self.stored):
            return {field: _(
                "The sequence cannot be set, changed or cleared while a "
                "step is done.") if by_sequence else _(
                "The start step cannot be changed while a step is done.")}
        if any(step.lots.exists() or step.lot_movements.exists()
               for step in self.stored):
            return {field: _(
                "The sequence cannot be set, changed or cleared while a "
                "step has made a lot or taken a withdrawal.")
                if by_sequence else _(
                "The start step cannot be changed while a step has made "
                "a lot or taken a withdrawal.")}
        if any(step.journal_entry_id is not None for step in self.stored):
            return {field: _(
                "The sequence cannot be set, changed or cleared while a "
                "step names a lab notebook entry.") if by_sequence else _(
                "The start step cannot be changed while a step names a "
                "lab notebook entry.")}
        sequence = self.sequence
        if sequence is None:
            return {}
        if sequence.withdrawn:
            return {field: _(
                "The sequence %(key)s is no longer in the collection.") % {
                    "key": sequence.key}}
        if self.substance is not None \
                and sequence.target_id != self.substance.pk:
            return {"sequence": _(
                "The sequence %(key)s makes %(name)s, not the task's "
                "substance.") % {"key": sequence.key,
                                 "name": sequence.target.shown_name}}
        count = sequence.steps.count()
        if self.start > count:
            return {"start_step": _(
                "The start step may not exceed the %(count)s steps of the "
                "sequence %(key)s.") % {"key": sequence.key,
                                        "count": count}}
        return {}

    def errors(self) -> dict[str, str]:
        """Return the errors that refuse the change, by form field.

        A save that plans the steps anew may not do so while a stored
        step is done, has made a lot or taken a withdrawal, or names a
        journal entry; the sequence it plans from may not be withdrawn,
        its target must be SUBSTANCE, when given, and START may not
        exceed its steps. The steps done may not exceed the steps the
        task has after the save; without a sequence, the total may not
        fall below the stored steps done; and a step that made a lot,
        took a withdrawal or names a journal entry may not be removed.
        """
        errors = self._plan_errors() if self.replaces else {}
        done_before = sum(step.done_on is not None for step in self.stored)
        if not errors and self.sequence is None \
                and (self.total or 0) < done_before:
            errors["steps_total"] = _(
                "The steps total may not be below the %(done)s steps "
                "done.") % {"done": done_before}
        count = len(self.planned())
        removed = self.stored[count:]
        if not errors:
            field = "sequence" if self.changes_sequence else (
                "start_step" if self.replaces else "steps_total")
            if any(step.lots.exists() or step.lot_movements.exists()
                   for step in removed):
                errors[field] = _(
                    "A step that made a lot or took a withdrawal cannot "
                    "be removed.")
            elif any(step.journal_entry_id is not None for step in removed):
                errors[field] = _(
                    "A step that names a lab notebook entry cannot be "
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
