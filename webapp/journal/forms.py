"""The forms that register and change the lab's notebooks."""

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from journal.models import Notebook
from tasks.forms import AssigneeField


class NotebookForm(forms.ModelForm):
    """A new notebook: its code, its owner, a choice of every account
    shown as initials and display name, and its note."""

    user = AssigneeField(
        queryset=get_user_model().objects.order_by("initials"),
        label=_("Owner"), empty_label="–")

    class Meta:
        model = Notebook
        fields = ["code", "user", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}


class NotebookEditForm(NotebookForm):
    """An existing notebook's owner and note; its code is fixed, and a
    code posted with the form is ignored."""

    class Meta(NotebookForm.Meta):
        fields = ["user", "note"]
