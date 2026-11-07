"""The inventory's lists, pages and forms."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import localize_input
from django.utils.translation import gettext as _

from inventory import bookings
from inventory.bookings import Refused
from inventory.chart import chart, quarters_shown
from inventory.figures import (Bulk, Consumption, bulk, consumption,
                               containers_from, molar_mass, proposed_amount)
from inventory.forms import (ConsumptionForm, CorrectionForm, FillForm,
                             ItemEditForm, ItemForm, LotCorrectionForm,
                             LotEditForm, LotForm, NoteEditForm, NoteForm,
                             ReversalForm, show_refusal)
from inventory.history import history_entries
from inventory.models import (END_PRODUCTS, FACTOR, LEVEL_ORDER,
                              DeliveryNote, Item, Level, Lot, Movement,
                              plain)
from orgsyndb_web import index
from planning import plan

LIST = "/lab/inventory/end-products/"
BULK = "/lab/inventory/end-products/bulk/"
DELIVERIES = "/lab/inventory/deliveries/"


def tabs(current: str) -> list[dict[str, Any]]:
    """Return the section tabs of the three lists, marking CURRENT, the
    path of the list shown."""
    return [{"url": url, "label": label, "current": url == current}
            for url, label in ((LIST, _("Items")), (BULK, _("Bulk")),
                               (DELIVERIES, _("Deliveries")))]


@dataclass(frozen=True)
class Row:
    """An item of the item list with its consumption, its bulk and its
    compound, or None."""

    item: Item
    figures: Consumption
    bulk: Bulk
    compound: Any

    @property
    def urgency(self) -> tuple[Any, ...]:
        """The row's place with ``sort=urgency``: by level, out first
        and items without one last, then by coverage, smallest first and
        items without one last, then in the list's order."""
        coverage = self.figures.coverage
        return (LEVEL_ORDER.get(self.figures.level, len(LEVEL_ORDER)),
                coverage is None, coverage or 0, self.item.sort_key())

    def searched(self) -> str:
        """The text the list's search looks in, folded for a comparison
        regardless of case."""
        item = self.item
        return "\n".join([item.article_number or "", item.name,
                          item.category,
                          item.note, self.compound.name if self.compound
                          else ""]).casefold()


@dataclass(frozen=True)
class ItemFilters:
    """The item list's filters as the query gives them, each unknown
    value replaced by its default: CATEGORY; LEVEL, a level or empty; Q,
    the searched text; and SORT, ``urgency`` or empty."""

    category: str = ""
    level: str = ""
    q: str = ""
    sort: str = ""

    @classmethod
    def from_query(cls, query: Any) -> "ItemFilters":
        """Return the filters of QUERY, a mapping of GET parameters."""
        level = query.get("level", "")
        return cls(category=query.get("category", "").strip(),
                   level=level if level in Level.values else "",
                   q=query.get("q", "").strip(),
                   sort="urgency" if query.get("sort") == "urgency"
                   else "")

    def admits(self, row: Row) -> bool:
        """Whether ROW passes every filter."""
        shown = row.figures.level
        return ((not self.category or row.item.category == self.category)
                and (not self.level or shown is not None
                     and LEVEL_ORDER[shown] <= LEVEL_ORDER[self.level])
                and (not self.q or self.q.casefold() in row.searched()))


def item_list(request: HttpRequest) -> HttpResponse:
    """List the items of ``end-products`` the query's filters select,
    with their figures and bulk, ordered by article number, unit and
    size, or by urgency with ``sort=urgency``."""
    today = timezone.localdate()
    filters = ItemFilters.from_query(request.GET)
    items = sorted(Item.objects.filter(inventory=END_PRODUCTS),
                   key=Item.sort_key)
    lots = list(Lot.objects.filter(inventory=END_PRODUCTS, amount__gt=0))
    rows = [Row(item=item, figures=consumption(item, today),
                bulk=bulk(item, lots),
                compound=index.compound_for(item.article_number)
                if item.article_number else None)
            for item in items]
    shown = [row for row in rows if filters.admits(row)]
    if filters.sort:
        shown.sort(key=lambda row: row.urgency)
    return render(request, "inventory/item_list.html", {
        "rows": shown,
        "filters": filters,
        "categories": sorted({item.category for item in items
                              if item.category}),
        "levels": Level.choices,
        "tabs": tabs(LIST),
    })


def lot_list(request: HttpRequest) -> HttpResponse:
    """List the open lots of ``end-products``, and the used-up ones too
    with ``empty=1``, by article number, then by date, oldest first and
    lots without one last."""
    empty = request.GET.get("empty") == "1"
    lots = Lot.objects.filter(inventory=END_PRODUCTS)
    if not empty:
        lots = lots.filter(amount__gt=0)
    names: dict[str, str] = {}
    for item in sorted(Item.objects.filter(inventory=END_PRODUCTS),
                       key=Item.sort_key):
        names.setdefault(item.article_number, item.name)
    shown = sorted(lots, key=lambda lot: (
        lot.article_number, lot.made_on is None, lot.made_on or date.min,
        lot.pk))
    return render(request, "inventory/lot_list.html", {
        "rows": [(lot, names.get(lot.article_number, "")) for lot in shown],
        "empty": empty,
        "tabs": tabs(BULK),
    })


def note_states(notes: list[DeliveryNote]) -> dict[int, str]:
    """Return the reversal state of each of NOTES by its ID: ``reversed``
    for a reversed historical note and a current note whose lines are all
    reversed, ``partly`` for a current note with some reversed, and the
    empty string otherwise."""
    reversed_lines = dict(
        Movement.objects.filter(
            delivery_note__in=notes, kind=Movement.Kind.DELIVERY,
            reversal__isnull=False).values("delivery_note")
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


def note_list(request: HttpRequest) -> HttpResponse:
    """List the delivery notes, newest date first, then newest booking
    first; ``q`` selects those whose number or recipient holds the text
    regardless of case, and ``item`` those with a line of the item of
    that ID."""
    q = request.GET.get("q", "").strip()
    chosen = request.GET.get("item", "").strip()
    notes = DeliveryNote.objects.annotate(line_count=Count("lines")) \
        .prefetch_related("lines__item").order_by(
            *DeliveryNote._meta.ordering)
    if chosen.isdigit():
        notes = notes.filter(pk__in=DeliveryNote.objects.filter(
            lines__item_id=int(chosen)).values("pk"))
    else:
        chosen = ""
    words = q.casefold()
    shown = [note for note in notes
             if not words or words in "\n".join(
                 [note.number or "", note.recipient]).casefold()]
    states = note_states(shown)
    return render(request, "inventory/note_list.html", {
        "notes": [(note, states[note.pk]) for note in shown],
        "q": q,
        "chosen": chosen,
        "items": sorted(Item.objects.filter(inventory=END_PRODUCTS,
                                            article_number__isnull=False),
                        key=Item.sort_key),
        "tabs": tabs(DELIVERIES),
    })


@dataclass(frozen=True)
class LedgerRow:
    """A movement as a ledger shows it: whether it is reversed, and
    whether it may still be reversed."""

    movement: Movement
    reversed: bool
    reversible: bool


@dataclass(frozen=True)
class QuarterRow:
    """A quarter of the chart's table: its entered value, its deliveries
    and their sum."""

    year: int
    quarter: int
    entered: int
    delivered: int
    total: int


def item_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the item PK with its figures, chart, movements, bulk,
    forecast and history; answer 404 for an unknown ID."""
    item = get_object_or_404(Item, pk=pk)
    today = timezone.localdate()
    figures = consumption(item, today)
    movements = item.movements.select_related(
        "user", "delivery_note", "reversal").order_by("-id")
    ledger = []
    for movement in movements:
        done = hasattr(movement, "reversal")
        ledger.append(LedgerRow(movement=movement, reversed=done,
                                reversible=movement.reversible
                                and not done))
    mass = molar_mass(item)
    numbered = item.article_number is not None
    found = plan.article(item.article_number, today) \
        if numbered and item.inventory == END_PRODUCTS else None
    lots = Lot.objects.filter(inventory=item.inventory,
                              article_number=item.article_number,
                              amount__gt=0).order_by("made_on", "id") \
        if numbered else Lot.objects.none()
    return render(request, "inventory/item_page.html", {
        "item": item,
        "figures": figures,
        "chart": chart(figures, today.year),
        "quarters": [QuarterRow(year=year, quarter=quarter,
                                entered=figures.entered.get((year, quarter),
                                                            0),
                                delivered=figures.delivered.get(
                                    (year, quarter), 0),
                                total=figures.total((year, quarter)))
                     for year, quarter in quarters_shown(today.year)],
        "ledger": ledger,
        "lots": [(lot, containers_from(lot, item, mass)) for lot in lots],
        "bulk": bulk(item, lots),
        "forecast": found,
        "entry": found.entry(item) if found else None,
        "history": history_entries(item),
    })


def lot_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the lot PK with its movements, the tasks of its batch and its
    history; answer 404 for an unknown ID."""
    lot = get_object_or_404(Lot, pk=pk)
    movements = lot.movements.select_related(
        "user", "item_movement__item").order_by("-id")
    return render(request, "inventory/lot_page.html", {
        "lot": lot,
        "ledger": [(movement, movement.item_movement.item
                    if hasattr(movement, "item_movement") else None)
                   for movement in movements],
        "tasks": plan.batch_tasks(lot),
        "history": history_entries(lot),
    })


def note_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the delivery note PK with its lines, their movements and the
    history; answer 404 for an unknown ID."""
    note = get_object_or_404(
        DeliveryNote.objects.annotate(line_count=Count("lines")), pk=pk)
    movements = {movement.item_id: movement for movement in
                 note.movements.select_related("user", "reversal")}
    return render(request, "inventory/note_page.html", {
        "note": note,
        "state": note_states([note])[note.pk],
        "lines": [(line, movements.get(line.item_id),
                   hasattr(movements.get(line.item_id), "reversal"))
                  for line in note.lines.select_related("item")],
        "history": history_entries(note),
    })


def form_page(request: HttpRequest, form: BaseForm,
              book: Callable[[dict[str, Any]], HttpResponse],
              context: dict[str, Any],
              template: str = "inventory/form.html") -> HttpResponse:
    """Show FORM, or pass the cleaned data of the posted FORM to BOOK and
    return its response.

    A form with errors, and one whose booking is refused, shows again
    with the errors at their fields. CONTEXT goes to TEMPLATE beside the
    form.
    """
    if request.method == "POST" and form.is_valid():
        try:
            return book(form.cleaned_data)
        except Refused as refused:
            show_refusal(form, refused, form.cleaned_data.get("rows"))
    return render(request, template, {"form": form, **context})


def saved(request: HttpRequest, text: str, target: str) -> HttpResponse:
    """Leave the message TEXT and redirect to TARGET."""
    messages.success(request, text)
    return redirect(target)


def item_url(item: Item, action: str = "") -> str:
    """Return the path of ITEM's page, or of its form ACTION."""
    return f"/lab/inventory/items/{item.pk}/" + (f"{action}/" if action
                                                 else "")


def lot_url(lot: Lot, action: str = "") -> str:
    """Return the path of LOT's page, or of its form ACTION."""
    return f"/lab/inventory/bulk/{lot.pk}/" + (f"{action}/" if action
                                               else "")


def note_url(note: DeliveryNote, action: str = "") -> str:
    """Return the path of NOTE's page, or of its form ACTION."""
    return f"/lab/inventory/deliveries/{note.pk}/" + (
        f"{action}/" if action else "")


def categories() -> Any:
    """The categories of the items, for the category's ``datalist``."""
    return Item.objects.exclude(category="").order_by("category") \
        .values_list("category", flat=True).distinct()


def article_numbers() -> list[tuple[str, str]]:
    """The values of the unique text fields of the compounds of the
    collection index, each with its compound's name, for the article
    numbers' ``datalist``; no compound key is among them."""
    return [(number, compound.name)
            for compound in index.current().compounds.values()
            for number in compound.identifiers if number != compound.key]


@login_required
def item_new(request: HttpRequest) -> HttpResponse:
    """Create an item with its opening count, booked by the signed-in
    user."""

    def book(data: dict[str, Any]) -> HttpResponse:
        item = bookings.create_item(request.user, **data)
        return saved(request, _("Item %(item)s created.") % {"item": item},
                     item_url(item))

    return form_page(
        request, ItemForm(request.POST or None), book,
        {"title": _("New item"), "cancel": LIST,
         "article_numbers": article_numbers(), "categories": categories()})


@login_required
def item_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the name, category and note of the item PK, and give it
    the article number entered while it has none."""
    item = get_object_or_404(Item, pk=pk)
    title = _("Edit %(item)s") % {"item": item}

    def book(data: dict[str, Any]) -> HttpResponse:
        with transaction.atomic():
            if data.get("article_number"):
                form.instance.article_number = \
                    bookings.assign_article_number(
                        request.user, item,
                        data["article_number"]).article_number
            form.save()
        stored = Item.objects.get(pk=item.pk)
        return saved(request, _("Item %(item)s saved.") % {"item": stored},
                     item_url(stored))

    form = ItemEditForm(request.POST or None, instance=item)
    return form_page(
        request, form, book,
        {"title": title, "cancel": item_url(item),
         "article_numbers": article_numbers(),
         "categories": categories()})


@login_required
def item_fill(request: HttpRequest, pk: int) -> HttpResponse:
    """Book a filling of the item PK, from a lot or none.

    The button ``propose`` books nothing: it shows the form again with
    the amount set to the proposal for the count and lot entered, or an
    error at the amount when there is no molar mass to convert with.
    """
    item = get_object_or_404(Item, pk=pk)
    form = FillForm(request.POST or None, item=item)
    if request.method == "POST" and "propose" in request.POST:
        if form.is_valid():
            form = proposed(request, form, item)
        return render(request, "inventory/form.html",
                      {"form": form, **fill_context(item)})

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.fill(request.user, item, **data)
        return saved(request, _("Filling of %(item)s booked.")
                     % {"item": item}, item_url(item))

    return form_page(request, form, book, fill_context(item))


def proposed(request: HttpRequest, form: FillForm, item: Item) -> FillForm:
    """Return the valid FORM of ITEM again with the amount set to the
    proposal, or FORM with an error where none can be made."""
    lot = form.cleaned_data["lot"]
    if lot is None:
        form.add_error("lot", _("Choose a lot to propose an amount."))
        return form
    base = proposed_amount(item, form.cleaned_data["count"], lot)
    if base is None:
        form.add_error("amount", _(
            "Without a molar mass of the compound, enter the amount taken."))
        return form
    data = request.POST.copy()
    data["amount"] = localize_input(plain(base / FACTOR[lot.unit]))
    again = FillForm(data, item=item)
    again.is_valid()
    return again


def fill_context(item: Item) -> dict[str, Any]:
    """Return the context of the filling form of ITEM."""
    return {"title": _("Fill %(item)s") % {"item": item},
            "cancel": item_url(item), "item": item, "propose": True}


@login_required
def item_correct(request: HttpRequest, pk: int) -> HttpResponse:
    """Set the count of the item PK after counting."""
    item = get_object_or_404(Item, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.correct(request.user, item, **data)
        return saved(request, _("Count of %(item)s corrected.")
                     % {"item": item}, item_url(item))

    return form_page(
        request, CorrectionForm(request.POST or None, initial={
            "count": item.quantity}), book,
        {"title": _("Correct the count of %(item)s") % {"item": item},
         "cancel": item_url(item)})


@login_required
def movement_reverse(request: HttpRequest, pk: int, movement: int
                     ) -> HttpResponse:
    """Reverse the delivery or filling MOVEMENT of the item PK."""
    item = get_object_or_404(Item, pk=pk)
    chosen = get_object_or_404(Movement, pk=movement, item=item)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.reverse(request.user, chosen, note=data["note"])
        return saved(request, _("%(kind)s of %(item)s reversed.")
                     % {"kind": chosen.get_kind_display(), "item": item},
                     item_url(item))

    return form_page(
        request, ReversalForm(request.POST or None), book,
        {"title": _("Reverse: %(kind)s of %(count)s, %(date)s") % {
            "kind": chosen.get_kind_display(), "count": chosen.count,
            "date": localize_input(chosen.date)},
         "cancel": item_url(item)})


@login_required
def item_consumption(request: HttpRequest, pk: int) -> HttpResponse:
    """Enter the consumption of a quarter of the item PK, or remove it
    with an empty count."""
    item = get_object_or_404(Item, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.enter_consumption(request.user, item, **data)
        return saved(request, _("Consumption of %(item)s saved.")
                     % {"item": item}, item_url(item))

    return form_page(
        request, ConsumptionForm(request.POST or None), book,
        {"title": _("Enter consumption of %(item)s") % {"item": item},
         "cancel": item_url(item)})


@login_required
def note_new(request: HttpRequest) -> HttpResponse:
    """Book a delivery note made by the signed-in user; ``item`` in the
    query puts that item in the first row."""
    initial = {}
    chosen = request.GET.get("item", "")
    if chosen.isdigit():
        initial["item_0"] = int(chosen)
    form = NoteForm(request.POST or None, initial=initial)

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


def locations() -> Any:
    """The locations of the lots, for the location's ``datalist``."""
    return Lot.objects.exclude(location="").order_by("location") \
        .values_list("location", flat=True).distinct()


@login_required
def lot_new(request: HttpRequest) -> HttpResponse:
    """Create a bulk lot with its opening amount, booked by the
    signed-in user; ``article``, ``batch`` and ``made_on`` in the query
    fill in the article number, the batch and the date."""

    def book(data: dict[str, Any]) -> HttpResponse:
        lot = bookings.create_lot(request.user, **data)
        return saved(request, _("Bulk lot %(lot)s created.") % {"lot": lot},
                     lot_url(lot))

    form = LotForm(request.POST or None, initial={
        "article_number": request.GET.get("article", ""),
        "batch": request.GET.get("batch", ""),
        "made_on": request.GET.get("made_on", "")})
    return form_page(request, form, book,
                     {"title": _("New bulk lot"), "cancel": BULK,
                      "article_numbers": article_numbers(),
                      "locations": locations()})


@login_required
def lot_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the batch, location, date and note of the lot PK."""
    lot = get_object_or_404(Lot, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        form.save()
        return saved(request, _("Bulk lot %(lot)s saved.") % {"lot": lot},
                     lot_url(lot))

    form = LotEditForm(request.POST or None, instance=lot)
    return form_page(request, form, book,
                     {"title": _("Edit %(item)s") % {"item": lot},
                      "cancel": lot_url(lot), "locations": locations()})


@login_required
def lot_correct(request: HttpRequest, pk: int) -> HttpResponse:
    """Set the amount of the lot PK after weighing."""
    lot = get_object_or_404(Lot, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.correct_lot(request.user, lot, **data)
        return saved(request, _("Amount of %(lot)s corrected.")
                     % {"lot": lot}, lot_url(lot))

    return form_page(
        request, LotCorrectionForm(request.POST or None, initial={
            "amount": lot.shown_amount}), book,
        {"title": _("Correct the amount of %(lot)s") % {"lot": lot},
         "cancel": lot_url(lot), "unit": lot.unit_label})

