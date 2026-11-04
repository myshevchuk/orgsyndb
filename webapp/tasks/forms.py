"""The forms that create and change tasks."""

from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orgsyndb_web import index
from tasks.models import Task

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class AssigneeField(forms.ModelChoiceField):
    """A choice among every account, each shown as its initials and
    display name."""

    def label_from_instance(self, obj: Any) -> str:
        return f"{obj.initials} – {obj.display_name}"


class TaskForm(forms.ModelForm):
    """The fields of a new task.

    A sequence that the form sets or changes must be one the collection
    index lists; its steps are copied onto the task and their number
    replaces the steps total. A sequence left as it was reads nothing
    from the index, and a cleared one clears the steps. Steps done left
    empty count as zero.
    """

    assignee = AssigneeField(
        queryset=get_user_model().objects.order_by("initials"),
        required=False, label=_("Assignee"), empty_label="–")
    steps_done = forms.IntegerField(label=_("Steps done"), required=False,
                                    min_value=0)

    class Meta:
        model = Task
        fields = ["product", "priority", "assignee", "started", "ended",
                  "sequence", "steps_total", "steps_done", "batch",
                  "report", "qc_list", "note"]
        widgets = {
            "product": forms.TextInput(attrs={"list": "compound-ids",
                                              "autocomplete": "off"}),
            "sequence": forms.TextInput(attrs={"list": "sequence-ids",
                                               "autocomplete": "off"}),
            "started": DATE,
            "ended": DATE,
            "note": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "product": _("A compound of the collection, by its key or "
                         "item number, or a name."),
            "sequence": _("A synthesis sequence of the collection; its "
                          "steps set the steps total."),
        }

    def clean_steps_done(self) -> int:
        """Return the steps done, zero when left empty."""
        return self.cleaned_data.get("steps_done") or 0

    def clean(self) -> dict[str, Any]:
        """Resolve the sequence and copy its steps onto the task."""
        cleaned = super().clean()
        sequence = (cleaned.get("sequence") or "").strip()
        cleaned["sequence"] = sequence
        if sequence == self.instance.sequence:
            steps = list(self.instance.sequence_steps or [])
        elif not sequence:
            steps = []
        else:
            found = index.sequence_for(sequence)
            if found is None:
                self.add_error("sequence", _(
                    "The collection has no sequence %(id)s.")
                    % {"id": sequence})
                return cleaned
            steps = list(found.steps)
        self.instance.sequence_steps = steps
        if sequence:
            cleaned["steps_total"] = len(steps) or None
        return cleaned


class TaskEditForm(TaskForm):
    """The fields of an existing task, among them its cancelled flag."""

    class Meta(TaskForm.Meta):
        fields = [*TaskForm.Meta.fields[:-1], "cancelled", "note"]
