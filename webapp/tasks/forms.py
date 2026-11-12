"""The forms that create and change tasks."""

from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from collection.models import Sequence
from registry.forms import SubstanceKeyField
from tasks.models import Task
from tasks.steps import StepChange

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class AssigneeField(forms.ModelChoiceField):
    """A choice among every account, each shown as its initials and
    display name."""

    def label_from_instance(self, obj: Any) -> str:
        return f"{obj.initials} – {obj.display_name}"


class SequenceField(forms.ModelChoiceField):
    """A choice of a sequence by its key, each shown as its ID and its
    title in the active language."""

    def label_from_instance(self, obj: Any) -> str:
        title = obj.title_de if get_language() == "de" and obj.title_de \
            else obj.title
        return f"{obj.key} – {title}"


class TaskForm(forms.ModelForm):
    """The fields of a new task, and the steps it has.

    The substance is named by its key. The sequence is one of the
    collection's sequences that are not withdrawn, or the one the task
    already has. ``steps_total`` sets the number of plain steps of a
    task without a sequence, and ``steps_done`` marks the first that
    many steps done; both are left empty as none. The rules of the
    steps are those of ``tasks.steps.StepChange``, whose errors the
    form shows at their fields.
    """

    substance = SubstanceKeyField()
    assignee = AssigneeField(
        queryset=get_user_model().objects.order_by("initials"),
        required=False, label=_("Assignee"), empty_label="–")
    sequence = SequenceField(
        queryset=Sequence.objects.none(), to_field_name="key",
        required=False, label=_("Sequence"), empty_label="–",
        help_text=_("A synthesis sequence of the collection; its steps "
                    "become the task's steps."))
    steps_total = forms.IntegerField(
        label=_("Steps total"), required=False, min_value=1,
        help_text=_("The number of steps of a task without a sequence."))
    steps_done = forms.IntegerField(label=_("Steps done"), required=False,
                                    min_value=0)

    class Meta:
        model = Task
        fields = ["substance", "priority", "assignee", "started", "ended",
                  "sequence", "steps_total", "steps_done", "batch",
                  "report", "qc_list", "note"]
        widgets = {
            "started": DATE,
            "ended": DATE,
            "note": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "priority": _("Applies while no forecast computes the "
                          "priority."),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        task = self.instance
        self.fields["sequence"].queryset = Sequence.objects.filter(
            Q(withdrawn=False) | Q(pk=task.sequence_id)).order_by("key")
        if task.sequence_id is not None:
            self.initial["sequence"] = task.sequence.key
        if task.pk:
            done, total = task.step_counts
            self.initial.setdefault("steps_total", total or None)
            self.initial.setdefault("steps_done", done)
        self.steps: StepChange | None = None

    def clean(self) -> dict[str, Any]:
        """Check the change of the steps the form makes, adding its
        errors at their fields."""
        cleaned = super().clean()
        if any(name in self.errors
               for name in ("sequence", "steps_total", "steps_done")):
            return cleaned
        self.steps = StepChange(self.instance, cleaned.get("sequence"),
                                cleaned.get("steps_total"),
                                cleaned.get("steps_done") or 0)
        for field, error in self.steps.errors().items():
            self.add_error(field, error)
        return cleaned

    def save(self, commit: bool = True) -> Task:
        """Save the task and, when COMMIT, give it its steps, both in one
        transaction; the steps done the form marks newly take today."""
        if not commit:
            return super().save(commit=False)
        with transaction.atomic():
            task = super().save()
            self.steps.apply(timezone.localdate())
        return task


class TaskEditForm(TaskForm):
    """The fields of an existing task, among them its cancelled flag."""

    class Meta(TaskForm.Meta):
        fields = [*TaskForm.Meta.fields[:-1], "cancelled", "note"]
