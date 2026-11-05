"""Tasks: the syntheses of end products the lab follows."""

from datetime import date
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

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
    CANCELLED = "cancelled", _("Cancelled")


PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
STATE_ORDER = {State.RUNNING: 0, State.PLANNED: 1, State.ENDED: 2,
               State.CANCELLED: 3}


class Task(models.Model):
    """The synthesis of a product, from planning to its report and the
    QC list.

    A task's number, ``T-`` and at least three digits, is assigned when
    it is first saved and never given again. Its state follows from its
    dates and its cancelled flag; see ``state``.
    """

    number = models.CharField(_("No."), max_length=20, unique=True,
                              editable=False)
    product = models.CharField(_("Product"), max_length=100)
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
    sequence = models.CharField(_("Sequence"), max_length=30, blank=True)
    sequence_steps = models.JSONField(_("Steps of the sequence"),
                                      default=list, blank=True)
    steps_total = models.PositiveIntegerField(
        _("Steps total"), null=True, blank=True,
        validators=[MinValueValidator(1)])
    steps_done = models.PositiveIntegerField(_("Steps done"), default=0)
    batch = models.CharField(_("Batch"), max_length=30, blank=True)
    report = models.BooleanField(_("Report"), default=False)
    qc_list = models.BooleanField(_("QC list"), default=False)
    cancelled = models.BooleanField(_("Cancelled"), default=False)
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
        return f"{self.number} {self.product}"

    @property
    def state(self) -> str:
        """``cancelled`` when the flag is on, else ``ended`` with an end
        date, ``running`` with a start date, and ``planned`` without
        either."""
        if self.cancelled:
            return State.CANCELLED
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
        """Whether the task is ended, and not cancelled, while its report
        or QC-list flag is off."""
        return self.state == State.ENDED and not (self.report
                                                  and self.qc_list)

    @property
    def progress(self) -> int | None:
        """The steps done as a whole percentage of the steps total,
        rounded down; None without a total."""
        if not self.steps_total:
            return None
        return (self.steps_done or 0) * 100 // self.steps_total

    @property
    def active(self) -> bool:
        """Whether the task is planned, running, or ended and needing
        follow-up."""
        return (self.state in (State.PLANNED, State.RUNNING)
                or self.needs_follow_up)

    def clean(self) -> None:
        """Check the rules that tie the fields together.

        Neither date may lie after today; an end needs a start and may
        not precede it; steps done need a total and may not exceed it;
        and with a sequence, the total is the number of its steps.
        Raise ValidationError with the errors by field.
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
        done = self.steps_done or 0
        if self.steps_total is None:
            if done:
                errors["steps_done"] = _("Steps done need a steps total.")
        elif done > self.steps_total:
            errors["steps_done"] = _(
                "Steps done may not exceed the steps total.")
        if self.sequence and self.steps_total != len(self.sequence_steps):
            errors["steps_total"] = _(
                "With a sequence, the total is the number of its steps.")
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

    def sort_key(self) -> tuple[Any, ...]:
        """The task's place in the list: by priority, high first, then by
        state, running, planned, ended, cancelled, then by start date,
        earliest first and tasks without one last, then by number."""
        return (PRIORITY_ORDER.get(self.priority, len(PRIORITY_ORDER)),
                STATE_ORDER[self.state], self.started is None,
                self.started or date.min,
                self.serial)

    @property
    def serial(self) -> int:
        """The counter value of the task's number; 0 before the number is
        assigned."""
        digits = self.number.removeprefix("T-")
        return int(digits) if digits.isdigit() else 0
