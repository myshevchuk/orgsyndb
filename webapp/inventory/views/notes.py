"""Delivery note list, detail, page, and form views."""

from typing import Any
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory import bookings
from inventory.forms import ROWS, NoteEditForm, NoteForm, ReversalForm
from inventory.history import history_entries
from inventory.models import DeliveryLine, DeliveryNote, Item, Movement
from inventory.views.common import (DELIVERIES, LIST, NOTE_COOKIE, form_page,
                                    htmx_detail_or_redirect, layers,
                                    list_view, note_url, pick_selected, saved,
                                    tabs)
from orgsyndb_web.lists import (Order, SortColumn, htmx_list_push_url,
                                sort_value)

NOTE_COLUMNS: tuple[SortColumn, ...] = (
    SortColumn("number", gettext_lazy("Number"),
               lambda note: sort_value(str(note))),
    SortColumn("date", gettext_lazy("Date"),
               lambda note: sort_value(note.date)),
    SortColumn("recipient", gettext_lazy("Recipient"),
               lambda note: sort_value(note.recipient)),
    SortColumn("lines", gettext_lazy("Lines"),
               lambda note: sort_value(note.line_count)),
)
NOTE_CLASSES = {
    "number": "col-strong",
    "recipient": "col-strong",
    "lines": "number",
}


def note_states(notes: list[DeliveryNote]) -> dict[int, str]:
    """Return the reversal state of each of NOTES by its ID: ``reversed``
    for a reversed historical note and a current note whose lines are all
    reversed, ``partly`` for a current note with some reversed, and the
    empty string otherwise."""
    reversed_lines = dict(
        Movement.objects.reversed_deliveries().filter(
            delivery_note__in=notes).values("delivery_note")
        .annotate(count=Count("id")).values_list("delivery_note", "count"))
    states = {}
    for note in notes:
        done = reversed_lines.get(note.pk, 0)
        if note.historical:
            states[note.pk] = "reversed" if note.reversed else ""
        elif done and done >= note.line_count:
            states[note.pk] = "reversed"
        else:
            states[note.pk] = "partly" if done else ""
    return states


def note_context(note: DeliveryNote, *, state: str | None = None,
                 lines: list[DeliveryLine] | None = None
                 ) -> dict[str, Any]:
    """Return the context NOTE is shown with, on its page and in the
    delivery list's details: the note, its state and its lines, each
    with its delivery movement, found by item and batch, and whether
    that is reversed; the assignments the note booked are left out."""
    movements = {(movement.item_id, movement.batch_id): movement
                 for movement in note.movements.filter(
                     kind=Movement.Kind.DELIVERY).select_related(
                         "user", "reversal")}
    if lines is None:
        lines = list(note.lines.select_related(
            "item__article__substance", "batch"))
    shown = [(line, movements.get((line.item_id, line.batch_id)))
             for line in lines]
    return {"note": note,
            "state": note_states([note])[note.pk] if state is None else state,
            "lines": [(line, movement, hasattr(movement, "reversal"))
                      for line, movement in shown]}


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def note_list(request: HttpRequest) -> HttpResponse:
    """List the delivery notes, newest date first by default, then newest
    booking first; ``q`` selects those whose number or recipient holds
    the text regardless of case, and ``item`` those with a line of the
    item of that ID. The note ``selected`` names among those listed, else
    the first, is selected, in the view the cookie ``delivery-list-view``
    remembers."""
    q = request.GET.get("q", "").strip()
    chosen = request.GET.get("item", "").strip()
    order = Order.from_query(request.GET, NOTE_COLUMNS, "date",
                             default_descending=True)
    notes = DeliveryNote.objects.annotate(line_count=Count("lines")) \
        .order_by(*DeliveryNote._meta.ordering)
    if chosen.isdigit():
        notes = notes.filter(pk__in=DeliveryNote.objects.filter(
            lines__item_id=int(chosen)).values("pk"))
    else:
        chosen = ""
    words = q.casefold()
    shown = [note for note in notes
             if not words or words in "\n".join(
                 [note.number or "", note.recipient]).casefold()]
    shown = order.ordered(shown)
    states = note_states(shown)
    selected_note, selected = pick_selected(
        shown, request.GET.get("selected", ""), lambda note: note.pk)
    filter_pairs: list[tuple[str, str]] = []
    if q:
        filter_pairs.append(("q", q))
    if chosen:
        filter_pairs.append(("item", chosen))
    response = render(request, "inventory/note_list.html", {
        "notes": [(note, states[note.pk]) for note in shown],
        "selected_note": selected_note,
        "selected": selected,
        "order": order,
        "headers": order.headers(DELIVERIES, filter_pairs, selected,
                                 NOTE_CLASSES),
        **(note_context(selected_note, state=states[selected_note.pk],
                        lines=list(selected_note.lines.select_related(
                            "item__article__substance", "batch")))
           if selected_note else {}),
        "view": list_view(request, NOTE_COOKIE),
        "layers": layers(DELIVERIES),
        "q": q,
        "chosen": chosen,
        "items": sorted(Item.objects.numbered().with_substance(),
                        key=Item.sort_key),
        "tabs": tabs(LIST),
    })
    pairs = [*filter_pairs, *order.pairs()]
    if selected:
        pairs.append(("selected", selected))
    return htmx_list_push_url(
        request, response,
        f"{DELIVERIES}?{urlencode(pairs)}" if pairs else DELIVERIES)


def note_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the delivery note PK with its lines, their movements and its
    history; answer 404 for an unknown ID."""
    note = get_object_or_404(
        DeliveryNote.objects.annotate(line_count=Count("lines")), pk=pk)
    return render(request, "inventory/note_page.html", {
        **note_context(note), "history": history_entries(note)})


@vary_on_headers("HX-Request", "HX-Current-URL")
def note_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the delivery note PK alone, as the delivery list shows them beside
    its table, and any other request with a redirect to the list with
    ``selected`` naming the note. Answer 404 for an unknown ID."""
    note = get_object_or_404(
        DeliveryNote.objects.annotate(line_count=Count("lines")), pk=pk)
    return htmx_detail_or_redirect(
        request, DELIVERIES, note.pk, "inventory/note_list.html#detail",
        lambda: note_context(note))


@login_required
def note_new(request: HttpRequest) -> HttpResponse:
    """Book a delivery note made by the signed-in user; each ``item`` in
    the query puts that item in the next row, in the order given, up to
    the form's rows, leaving out items the form does not offer and
    repeats."""
    form = NoteForm(request.POST or None)
    offered = set(form.fields["item_0"].queryset.values_list(
        "pk", flat=True))
    chosen: list[int] = []
    for value in request.GET.getlist("item"):
        if value.isdigit() and int(value) in offered \
                and int(value) not in chosen:
            chosen.append(int(value))
    if not form.is_bound:
        for row, pk in enumerate(chosen[:ROWS]):
            form.initial[f"item_{row}"] = pk

    def book(data: dict[str, Any]) -> HttpResponse:
        note = bookings.book_note(
            request.user, date=data["date"], lines=data["lines"],
            number=data["number"], recipient=data["recipient"],
            note=data["note"], historical=data["historical"])
        return saved(request, _("Delivery note %(note)s booked.")
                     % {"note": note}, note_url(note))

    return form_page(request, form, book,
                     {"title": _("New delivery note"), "cancel": DELIVERIES},
                     "inventory/note_form.html")


@login_required
def note_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the number, recipient and note of the delivery note PK."""
    note = get_object_or_404(DeliveryNote, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        form.save()
        return saved(request, _("Delivery note %(note)s saved.")
                     % {"note": note}, note_url(note))

    form = NoteEditForm(request.POST or None, instance=note)
    return form_page(request, form, book,
                     {"title": _("Edit %(item)s") % {"item": note},
                      "cancel": note_url(note)})


@login_required
def note_reverse(request: HttpRequest, pk: int) -> HttpResponse:
    """Mark the historical delivery note PK reversed."""
    note = get_object_or_404(DeliveryNote, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.reverse_historical(request.user, note, note=data["note"])
        return saved(request, _("Delivery note %(note)s reversed.")
                     % {"note": note}, note_url(note))

    return form_page(request, ReversalForm(request.POST or None), book,
                     {"title": _("Reverse delivery note %(note)s")
                      % {"note": note}, "cancel": note_url(note)})
