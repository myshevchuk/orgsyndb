"""The registry's pages and forms: the substances, the vocabularies and
the snapshot."""

from collections import Counter
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from collection.models import latest_accepted
from inventory.models import Item, Lot
from registry import snapshot
from registry.forms import SubstanceForm
from registry.models import Substance, SubstanceClass
from tasks.models import Task
from vocabulary.forms import term_form
from vocabulary.models import (ChemicalClass, Group, Project, ReactionType,
                               Term, is_tree, tree_order)

REGISTRY = "/lab/registry/"
# The vocabularies by the names of their pages, each with its model and
# its heading.
VOCABULARIES: dict[str, tuple[type[Term], Any]] = {
    "chemical-classes": (ChemicalClass, gettext_lazy("Chemical classes")),
    "groups": (Group, gettext_lazy("Groups")),
    "projects": (Project, gettext_lazy("Projects")),
    "reaction-types": (ReactionType, gettext_lazy("Reaction types")),
}


def substance_url(substance: Substance, action: str = "") -> str:
    """Return the path of SUBSTANCE's page, or of its form ACTION."""
    return f"{REGISTRY}substances/{substance.key}/" + (
        f"{action}/" if action else "")


def searched(substance: Substance) -> str:
    """The text the list's search looks in, folded for a comparison
    regardless of case: the key, the names, the short name and the CAS
    number."""
    return "\n".join([substance.key, substance.name, substance.name_de,
                      substance.short_name, substance.cas]).casefold()


def substance_list(request: HttpRequest) -> HttpResponse:
    """List the substances whose key, names, short name or CAS number
    hold the query's ``q`` regardless of case, every one without it, by
    name regardless of case."""
    query = request.GET.get("q", "").strip()
    words = query.casefold()
    every = Substance.objects.select_related("group", "article") \
        .prefetch_related("chemical_classes")
    shown = sorted((substance for substance in every
                    if not words or words in searched(substance)),
                   key=lambda substance: (substance.shown_name.casefold(),
                                          substance.key))
    return render(request, "registry/list.html", {
        "substances": shown,
        "q": query,
        "vocabularies": [(name, heading) for name, (_model, heading)
                         in VOCABULARIES.items()],
    })


def in_collection(substance: Substance) -> bool:
    """Whether the latest accepted import of the collection was received
    no earlier than SUBSTANCE was created, the time of the first record
    of its history: the build of that import had the substance's page.
    False while no import was accepted, or for a substance without a
    history."""
    latest = latest_accepted()
    created = substance.history.order_by("history_id").first()
    return (latest is not None and created is not None
            and latest.received_at >= created.history_date)


def substance_page(request: HttpRequest, key: str) -> HttpResponse:
    """Show the substance KEY with its fields, its link to the site's
    compound page (``in_collection``), its article's items, its open
    lots and its tasks; answer 404 for an unknown key."""
    substance = get_object_or_404(
        Substance.objects.select_related("group"), key=key)
    items = sorted(Item.objects.filter(article_id=substance.pk)
                   .select_related("article__substance"),
                   key=Item.sort_key)
    return render(request, "registry/substance.html", {
        "substance": substance,
        "classes": [term for term, _depth in tree_order(
            substance.chemical_classes.all())],
        "in_collection": in_collection(substance),
        "items": items,
        "lots": Lot.objects.filter(substance=substance, amount__gt=0)
        .order_by("made_on", "id"),
        "tasks": sorted(Task.objects.filter(substance=substance),
                        key=lambda task: task.serial),
    })


def form_page(request: HttpRequest, form: Any, title: str, cancel: str,
              done: Any) -> HttpResponse:
    """Show FORM, or save the posted, valid FORM and redirect to the
    path DONE gives for the saved record, with a message; a form with
    errors shows again."""
    if request.method == "POST" and form.is_valid():
        record = form.save()
        messages.success(request, _("%(record)s saved.")
                         % {"record": record})
        return redirect(done(record))
    return render(request, "registry/form.html", {
        "form": form, "title": title, "cancel": cancel})


@login_required
def substance_new(request: HttpRequest) -> HttpResponse:
    """Create a substance with its chemical classes."""
    return form_page(request, SubstanceForm(request.POST or None),
                     _("New substance"), REGISTRY, substance_url)


@login_required
def substance_edit(request: HttpRequest, key: str) -> HttpResponse:
    """Change the substance KEY, its key excepted; answer 404 for an
    unknown key."""
    substance = get_object_or_404(Substance, key=key)
    return form_page(
        request, SubstanceForm(request.POST or None, instance=substance),
        _("Edit %(record)s") % {"record": substance.shown_name},
        substance_url(substance), substance_url)


def vocabulary_of(name: str) -> tuple[type[Term], Any]:
    """Return the model and the heading of the vocabulary whose page is
    NAME; raise Http404 for any other name."""
    if name not in VOCABULARIES:
        raise Http404
    return VOCABULARIES[name]


def uses(model: type[Term]) -> Counter[int]:
    """Return how many substances name each term of MODEL, by the
    term's ID."""
    if model is Group:
        pairs = Substance.objects.values("group").annotate(
            count=Count("pk")).values_list("group", "count")
    elif model is ChemicalClass:
        pairs = SubstanceClass.objects.values("chemical_class").annotate(
            count=Count("pk")).values_list("chemical_class", "count")
    else:
        pairs = []
    return Counter(dict(pairs))


def vocabulary_page(request: HttpRequest, vocabulary: str) -> HttpResponse:
    """List the terms of VOCABULARY in tree order, each with its depth
    and the number of substances that name it; answer 404 for an
    unknown vocabulary."""
    model, heading = vocabulary_of(vocabulary)
    counts = uses(model)
    terms = model.objects.select_related("parent") if is_tree(model) \
        else model.objects.all()
    return render(request, "registry/vocabulary.html", {
        "name": vocabulary,
        "heading": heading,
        "tree": is_tree(model),
        "terms": [(term, depth, counts[term.pk])
                  for term, depth in tree_order(terms)],
    })


@login_required
def term_new(request: HttpRequest, vocabulary: str) -> HttpResponse:
    """Create a term of VOCABULARY; answer 404 for an unknown
    vocabulary."""
    model, heading = vocabulary_of(vocabulary)
    page = f"{REGISTRY}{vocabulary}/"
    return form_page(request, term_form(model, data=request.POST or None),
                     _("New term: %(vocabulary)s") % {"vocabulary": heading},
                     page, lambda term: page)


@login_required
def term_edit(request: HttpRequest, vocabulary: str, key: str
              ) -> HttpResponse:
    """Change the term KEY of VOCABULARY, its key excepted; answer 404
    for an unknown vocabulary or key."""
    model, heading = vocabulary_of(vocabulary)
    term = get_object_or_404(model, key=key)
    page = f"{REGISTRY}{vocabulary}/"
    return form_page(
        request, term_form(model, term, data=request.POST or None),
        _("Edit %(record)s") % {"record": term.key}, page,
        lambda saved: page)


def snapshot_json(request: HttpRequest) -> JsonResponse:
    """Answer the registry's snapshot as JSON."""
    return JsonResponse(snapshot.build())
