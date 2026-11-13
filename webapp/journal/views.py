"""The journal's pages and forms: the notebooks and their entries."""

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from collection.models import Procedure
from journal.forms import NotebookEditForm, NotebookForm
from journal.models import Notebook
from tasks.models import TaskStep

JOURNAL = "/lab/journal/"


def notebook_url(notebook: Notebook, action: str = "") -> str:
    """Return the path of NOTEBOOK's page, or of its form ACTION."""
    return f"{JOURNAL}{notebook.code}/" + (f"{action}/" if action else "")


def notebook_list(request: HttpRequest) -> HttpResponse:
    """List the notebooks by code, each with its owner and the number of
    its entries."""
    return render(request, "journal/list.html", {
        "notebooks": Notebook.objects.select_related("user").annotate(
            entry_count=Count("entries")).order_by("code")})


def notebook_page(request: HttpRequest, code: str) -> HttpResponse:
    """Show the notebook CODE with its owner, its note and its entries by
    number, each with the procedures and the task steps that name it;
    answer 404 for an unknown code."""
    notebook = get_object_or_404(Notebook.objects.select_related("user"),
                                 code=code)
    entries = notebook.entries.order_by("number").prefetch_related(
        Prefetch("procedures", queryset=Procedure.objects.order_by("key")),
        Prefetch("task_steps", queryset=TaskStep.objects.select_related(
            "task").order_by("task__number", "position")))
    return render(request, "journal/notebook.html", {
        "notebook": notebook, "entries": entries})


def form_page(request: HttpRequest, form: Any, title: str,
              cancel: str) -> HttpResponse:
    """Show FORM, or save the posted, valid FORM and lead to the saved
    notebook's page with a message; a form with errors shows again."""
    if request.method == "POST" and form.is_valid():
        notebook = form.save()
        messages.success(request, _("Lab notebook %(code)s saved.")
                         % {"code": notebook.code})
        return redirect(notebook_url(notebook))
    return render(request, "registry/form.html", {
        "form": form, "title": title, "cancel": cancel})


@login_required
def notebook_new(request: HttpRequest) -> HttpResponse:
    """Register a notebook, owned by the signed-in user unless the form
    names another account."""
    return form_page(
        request, NotebookForm(request.POST or None,
                              initial={"user": request.user.pk}),
        _("New lab notebook"), JOURNAL)


@login_required
def notebook_edit(request: HttpRequest, code: str) -> HttpResponse:
    """Change the owner and the note of the notebook CODE; answer 404 for
    an unknown code."""
    notebook = get_object_or_404(Notebook, code=code)
    return form_page(
        request, NotebookEditForm(request.POST or None, instance=notebook),
        _("Edit %(record)s") % {"record": notebook.code},
        notebook_url(notebook))

