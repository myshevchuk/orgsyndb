"""Tasks: the syntheses of end products the lab follows."""

from datetime import date
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _

from orgsyndb_web.history import RecordedHistory


class Counter(models.Model):
    """A named counter that only counts up."""

    name = models.CharField(max_length=30, primary_key=True)
    value = models.PositiveBigIntegerField(default=0)

    @classmethod
    def next(cls, name: str) -> int:
        """Add one to the counter NAME and return its new value.

        A counter that does not exist yet starts at zero. The increment
        is one atomic ``UPDATE``, read back in the same transaction, so
        concurrent callers get different values and no value is given
        twice.
        """
        with transaction.atomic():
            counter = cls.objects.filter(name=name)
            if not counter.update(value=F("value") + 1):
                cls.objects.get_or_create(name=name)
                counter.update(value=F("value") + 1)
            return counter.values_list("value", flat=True).get()


class Priority(models.TextChoices):
    HIGH = "high", _("high")
    MEDIUM = "medium", _("medium")
    LOW = "low", _("low")


class State(models.TextChoices):
    PLANNED = "planned", _("Planned")
    RUNNING = "running", _("Running")
    ENDED = "ended", pgettext_lazy("state", "Ended")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
STATE_ORDER = {State.RUNNING: 0, State.PLANNED: 1, State.ENDED: 2,
               State.FAILED: 3, State.CANCELLED: 4}


class Task(models.Model):
    """The synthesis of a substance, from planning to its report and the
    QC list.

    A task's number, ``T-`` and at least three digits, is assigned when
    it is first saved and never given again. Its state follows from its
    dates and its cancelled and failed flags; see ``state``. A task
    that is ended and has not failed has a batch and a product lot; see
    ``has_product_lot`` and ``clean``. Its steps are the
    ``TaskStep`` rows of ``steps``, which ``tasks.steps`` gives it from
    its ``sequence``, an imported sequence, or as plain steps.
    """

    number = models.CharField(_("No."), max_length=20, unique=True,
                              editable=False)
    substance = models.ForeignKey(
        "registry.Substance", verbose_name=_("Substance"),
        on_delete=models.PROTECT, related_name="tasks")
    priority = models.CharField(_("Priority"), max_length=6,
                                choices=Priority.choices,
                                default=Priority.MEDIUM)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Assignee"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="assigned_tasks")
    started = models.DateField(_("Started"), null=True, blank=True)
    ended = models.DateField(pgettext_lazy("date", "Ended"), null=True,
                             blank=True)
    sequence = models.ForeignKey(
        "collection.Sequence", verbose_name=_("Sequence"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="tasks")
    batch = models.CharField(_("Batch"), max_length=30, blank=True)
    report = models.BooleanField(_("Report"), default=False)
    qc_list = models.BooleanField(_("QC list"), default=False)
    cancelled = models.BooleanField(_("Cancelled"), default=False)
    failed = models.BooleanField(_("Failed"), default=False)
    note = models.TextField(_("Note"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Created by"),
        on_delete=models.PROTECT, related_name="created_tasks")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["id"]
        verbose_name = _("task")
        verbose_name_plural = _("tasks")

    def __str__(self) -> str:
        return f"{self.number} {self.substance.shown_name}"

    @property
    def state(self) -> str:
        """``cancelled`` when that flag is on, else ``failed`` when that
        flag is on, else ``ended`` with an end date, ``running`` with a
        start date, and ``planned`` without either."""
        if self.cancelled:
            return State.CANCELLED
        if self.failed:
            return State.FAILED
        if self.ended:
            return State.ENDED
        if self.started:
            return State.RUNNING
        return State.PLANNED

    @property
    def state_label(self) -> str:
        """The state as the active language names it."""
        return State(self.state).label

    @property
    def needs_follow_up(self) -> bool:
        """Whether the task is ended, neither cancelled nor failed, while
        its report or QC-list flag is off."""
        return self.state == State.ENDED and not (self.report
                                                  and self.qc_list)

    @property
    def step_counts(self) -> tuple[int, int]:
        """The number of the task's steps done and the number of its
        steps, read from its step rows."""
        steps = list(self.steps.all()) if self.pk else []
        return (sum(step.done_on is not None for step in steps),
                len(steps))

    @property
    def progress(self) -> int | None:
        """The steps done as a whole percentage of the steps, rounded
        down; None without steps."""
        done, total = self.step_counts
        return done * 100 // total if total else None

    @property
    def active(self) -> bool:
        """Whether the task is planned, running, or ended and needing
        follow-up."""
        return (self.state in (State.PLANNED, State.RUNNING)
                or self.needs_follow_up)

    @property
    def has_product_lot(self) -> bool:
        """Whether the task has a batch and a product lot: a lot of its
        substance, made in the lab, whose batch is the task's."""
        return bool(self.batch) and self.substance.lots.filter(
            source="made", batch=self.batch).exists()

    def clean(self) -> None:
        """Check the rules that tie the dates, the batch and the product
        lot together.

        Neither date may lie after today, and an end needs a start and
        may not precede it. A failed task has no batch. A task that is
        ended, neither cancelled nor failed, has a batch and a product
        lot (``has_product_lot``). Raise ValidationError with the errors
        by field. The rules of the steps are
        ``tasks.steps.StepChange``'s.
        """
        errors: dict[str, str] = {}
        today = timezone.localdate()
        if self.started and self.started > today:
            errors["started"] = _("The start may not lie in the future.")
        if self.ended:
            if self.ended > today:
                errors["ended"] = _("The end may not lie in the future.")
            elif not self.started:
                errors["ended"] = _("An end needs a start.")
            elif self.ended < self.started:
                errors["ended"] = _("The end may not precede the start.")
        if self.failed and self.batch:
            errors["batch"] = _("A failed task has no batch.")
        elif self.state == State.ENDED and "ended" not in errors \
                and self.substance_id is not None:
            if not self.batch:
                errors["batch"] = _(
                    "An ended task needs the batch of its product lot.")
            elif not self.has_product_lot:
                errors["ended"] = _(
                    "Record a lot of the product, made in the lab, with "
                    "the batch %(batch)s before ending the task.") % {
                        "batch": self.batch}
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the task, giving a new task the next number.

        The number comes from the ``task`` counter, incremented in the
        transaction that inserts the task.
        """
        with transaction.atomic():
            if self._state.adding and not self.number:
                self.number = f"T-{Counter.next('task'):03d}"
            super().save(*args, **kwargs)

    def sort_key(self, priority: str, slack: float | None
                 ) -> tuple[Any, ...]:
        """The task's place in the list, given the PRIORITY it is listed
        with and its SLACK in days or None: by priority, high first, then
        by slack, smallest first and tasks without one last, then by
        state, running, planned, ended, cancelled, then by start date,
        earliest first and tasks without one last, then by number."""
        return (PRIORITY_ORDER.get(priority, len(PRIORITY_ORDER)),
                slack is None, slack or 0, STATE_ORDER[self.state],
                self.started is None, self.started or date.min,
                self.serial)

    @property
    def serial(self) -> int:
        """The counter value of the task's number; 0 before the number is
        assigned."""
        digits = self.number.removeprefix("T-")
        return int(digits) if digits.isdigit() else 0


class TaskStep(models.Model):
    """A step of a task, at its ``position`` from 1.

    ``entry`` is the scope entry the step carries out, or None for a
    step not written down as one; ``planned_import`` is the accepted
    import that was the latest when the step was planned, or None; and
    ``done_on`` is the day it was done, or None while it is not.
    """

    task = models.ForeignKey(Task, verbose_name=_("task"),
                             on_delete=models.CASCADE, related_name="steps")
    position = models.PositiveIntegerField(
        _("Position"), validators=[MinValueValidator(1)])
    entry = models.ForeignKey(
        "collection.ScopeEntry", verbose_name=_("scope entry"),
        on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    planned_import = models.ForeignKey(
        "collection.Import", verbose_name=_("Planned with import"),
        on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    done_on = models.DateField(_("Done on"), null=True, blank=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["task", "position"]
        verbose_name = _("task step")
        verbose_name_plural = _("task steps")
        constraints = [
            models.UniqueConstraint(fields=["task", "position"],
                                    name="tasks_taskstep_once"),
            models.CheckConstraint(condition=models.Q(position__gte=1),
                                   name="tasks_taskstep_position"),
        ]

    def __str__(self) -> str:
        return f"{self.task.number} {self.position}"

    @property
    def label(self) -> str:
        """The step in the active language as ``Step <n>``, its position,
        followed for a step with an entry by its procedure's ID."""
        shown = gettext("Step %(position)s") % {"position": self.position}
        if self.entry_id is None:
            return shown
        return f"{shown} · {self.entry.procedure.key}"

    @property
    def open(self) -> bool:
        """Whether the step's task is planned or running."""
        return self.task.state in (State.PLANNED, State.RUNNING)

    def products(self) -> list[Any]:
        """Return the substances the step makes: its entry's products in
        their order, or, for a step without an entry, its task's
        substance."""
        if self.entry_id is None:
            return [self.task.substance]
        return [row.substance for row in self.entry.substances.filter(
            role="product").select_related("substance").order_by(
                "position")]

    def substrates(self) -> list[Any] | None:
        """Return the substances the step takes: its entry's substrates
        in their order, or None for a step without an entry, which may
        take any."""
        if self.entry_id is None:
            return None
        return [row.substance for row in self.entry.substances.filter(
            role="substrate").select_related("substance").order_by(
                "position")]
