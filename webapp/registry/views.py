"""The registry's pages and forms: the substances, the vocabularies and
the snapshot."""

from collections import Counter
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.vary import vary_on_headers

from collection import routes
from collection.models import EntrySubstance, Procedure, Role, Sequence
from inventory.figures import newest_first, open_amounts
from inventory.models import Batch, Item
from orgsyndb_web.lists import htmx_list_push_url
from registry import snapshot
from registry.forms import SubstanceForm
from registry.models import Substance, SubstanceClass
from tasks.models import Task
from vocabulary.forms import term_form
from vocabulary.models import (ChemicalClass, Group, Project, ReactionType,
                               Term, descendants, is_tree, tree_order)

REGISTRY = "/lab/registry/"
# The vocabularies by the names of their pages, each with its model and
# its heading.
VOCABULARIES: dict[str, tuple[type[Term], Any]] = {
    "chemical-classes": (ChemicalClass, gettext_lazy("Chemical classes")),
    "groups": (Group, gettext_lazy("Inventory groups")),
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


def filed_under(model: type[Term], key: str) -> list[Any]:
    """Return the IDs of the term of MODEL whose key is KEY and of the
    terms filed below it, at any depth; none for a key no term has."""
    term = model.objects.filter(key=key).first()
    return [] if term is None else [
        term.pk, *(below.pk for below in descendants(term))]


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def substance_list(request: HttpRequest) -> HttpResponse:
    """List the substances, by name regardless of case: those whose key,
    names, short name or CAS number hold the query's ``q`` regardless of
    case, filed under the inventory group ``group`` or a group below it,
    and of the chemical class ``class`` or a class below it, each
    condition left out when its parameter is empty."""
    query = request.GET.get("q", "").strip()
    group = request.GET.get("group", "").strip()
    chemical_class = request.GET.get("class", "").strip()
    words = query.casefold()
    every = Substance.objects.select_related("group", "article") \
        .prefetch_related("chemical_classes").defer("structure_svg")
    if group:
        every = every.filter(group__in=filed_under(Group, group))
    if chemical_class:
        every = every.filter(chemical_classes__in=filed_under(
            ChemicalClass, chemical_class)).distinct()
    shown = sorted((substance for substance in every
                    if not words or words in searched(substance)),
                   key=lambda substance: (substance.shown_name.casefold(),
                                          substance.key))
    groups = tree_order(Group.objects.all())
    classes = tree_order(ChemicalClass.objects.all())
    response = render(request, "registry/list.html", {
        "substances": shown, "q": query, "group": group,
        "chemical_class": chemical_class,
        "groups": groups,
        "classes": classes,
        "group_unknown": bool(group) and all(
            term.key != group for term, _ in groups),
        "class_unknown": bool(chemical_class) and all(
            term.key != chemical_class for term, _ in classes),
    })
    pairs: list[tuple[str, str]] = []
    if query:
        pairs.append(("q", query))
    if group:
        pairs.append(("group", group))
    if chemical_class:
        pairs.append(("class", chemical_class))
    return htmx_list_push_url(
        request, response,
        f"{REGISTRY}?{urlencode(pairs)}" if pairs else REGISTRY)


def shown_yield(value: float | None) -> Decimal | None:
    """Return VALUE, a yield kept as a float, as the decimal it was
    written as, or None."""
    return None if value is None else Decimal(repr(value))


def kept_rows(substance: Substance, role: Role) -> Any:
    """Return the rows of SUBSTANCE in ROLE among the entries that are
    not withdrawn, of procedures that are not withdrawn."""
    return EntrySubstance.objects.filter(
        substance=substance, role=role, entry__withdrawn=False,
        entry__procedure__withdrawn=False)


def made_by(substance: Substance) -> list[dict[str, Any]]:
    """Return what makes SUBSTANCE, by procedure ID and then entry
    position: per specific procedure or entry of a general one, a table
    of ``procedure``, its row; ``entry``, the entry's position for a
    general procedure, else None; and ``yield_percent``, a decimal or
    None."""
    rows = kept_rows(substance, Role.PRODUCT).select_related(
        "entry__procedure").order_by("entry__procedure__key",
                                     "entry__position")
    return [{"procedure": row.entry.procedure,
             "entry": row.entry.position
             if row.entry.procedure.general else None,
             "yield_percent": shown_yield(row.yield_percent)}
            for row in rows]


def used_in(substance: Substance) -> list[Procedure]:
    """Return the procedures that start from SUBSTANCE, by ID."""
    named = kept_rows(substance, Role.SUBSTRATE).values("entry__procedure")
    return list(Procedure.objects.filter(pk__in=named).order_by("key"))


def route(substance: Substance) -> list[dict[str, Any]]:
    """Return SUBSTANCE's route tree (``routes.route_tree``), its steps
    holding the procedure's row under ``procedure`` and the yield as a
    decimal, and their substrates the substance's row under
    ``substance``; an empty list when it has none."""
    tree = routes.route_tree(substance.key, routes.steps())
    procedures: set[str] = set()
    compounds: set[str] = set()

    def collect(steps: list[dict[str, Any]]) -> None:
        for step in steps:
            procedures.add(step["procedure"])
            for item in step["substrates"]:
                compounds.add(item["compound"])
                collect(item["steps"])

    collect(tree)
    rows = {row.key: row for row in
            Procedure.objects.filter(key__in=procedures)}
    found = {row.key: row for row in
             Substance.objects.filter(key__in=compounds)}

    def resolve(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"procedure": rows[step["procedure"]],
                 "entry": step.get("entry"),
                 "yield_percent": shown_yield(step["yield_percent"]),
                 "substrates": [{"substance": found[item["compound"]],
                                 "steps": resolve(item["steps"]),
                                 "more": item["more"]}
                                for item in step["substrates"]]}
                for step in steps]

    return resolve(tree)


def substance_page(request: HttpRequest, key: str) -> HttpResponse:
    """Show the substance KEY with its fields, the procedures that make
    it and that start from it, the sequences whose target it is, its
    route tree, its article's items, its batches and its tasks;
    answer 404 for an unknown key."""
    substance = get_object_or_404(
        Substance.objects.select_related("group").defer("structure_svg"),
        key=key)
    items = sorted(Item.objects.filter(article_id=substance.pk)
                   .select_related("article__substance"),
                   key=Item.sort_key)
    batches = newest_first(Batch.objects.filter(substance=substance))
    stock = open_amounts(batches)
    return render(request, "registry/substance.html", {
        "substance": substance,
        "classes": [term for term, _depth in tree_order(
            substance.chemical_classes.all())],
        "made_by": made_by(substance),
        "used_in": used_in(substance),
        "sequences": Sequence.objects.filter(
            target=substance, withdrawn=False).order_by("key"),
        "route": route(substance),
        "items": items,
        "batches": [(batch, stock[batch.pk]) for batch in batches],
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


# The headers of a structure image: it runs no script and loads nothing
# from elsewhere, and is taken for nothing but SVG.
IMAGE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src "
                               "'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}


def structure_image(request: HttpRequest, key: str) -> HttpResponse:
    """Answer the kept drawing of the substance KEY's structure as
    ``image/svg+xml`` with ``IMAGE_HEADERS``, without drawing it; answer
    404 for an unknown key or a substance without a molfile."""
    found = Substance.objects.filter(key=key).exclude(molfile="") \
        .values_list("structure_svg", flat=True).first()
    if found is None:
        raise Http404
    return HttpResponse(found, content_type="image/svg+xml",
                        headers=IMAGE_HEADERS)


@login_required
def substance_new(request: HttpRequest) -> HttpResponse:
    """Create a substance with its chemical classes."""
    return form_page(
        request, SubstanceForm(request.POST or None, request.FILES or None),
        _("New substance"), REGISTRY, substance_url)


@login_required
def substance_edit(request: HttpRequest, key: str) -> HttpResponse:
    """Change the substance KEY, its key excepted; answer 404 for an
    unknown key."""
    substance = get_object_or_404(Substance, key=key)
    return form_page(
        request, SubstanceForm(request.POST or None, request.FILES or None,
                               instance=substance),
        _("Edit %(record)s") % {"record": substance.shown_name},
        substance_url(substance), substance_url)


def vocabulary_of(name: str) -> tuple[type[Term], Any]:
    """Return the model and the heading of the vocabulary whose page is
    NAME; raise Http404 for any other name."""
    if name not in VOCABULARIES:
        raise Http404
    return VOCABULARIES[name]


# The rows that name a term of each vocabulary, by model: a manager and
# the field that names the term.
NAMED_BY: dict[type[Term], tuple[Any, str]] = {
    ChemicalClass: (SubstanceClass.objects, "chemical_class"),
    Group: (Substance.objects, "group"),
    Project: (Procedure.objects, "project"),
    ReactionType: (Procedure.objects, "reaction_type"),
}


def uses(model: type[Term]) -> Counter[int]:
    """Return how many records name each term of MODEL, by the term's
    ID: substances for the chemical classes and the inventory groups,
    procedures of the collection, withdrawn ones included, for the
    projects and the reaction types."""
    rows, field = NAMED_BY[model]
    return Counter(dict(rows.filter(**{f"{field}__isnull": False})
                        .values(field).annotate(count=Count("pk"))
                        .values_list(field, "count")))


def vocabulary_page(request: HttpRequest, vocabulary: str) -> HttpResponse:
    """List the terms of VOCABULARY in tree order, each with its depth
    and the number of records that name it (``uses``); answer 404 for
    an unknown vocabulary."""
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
