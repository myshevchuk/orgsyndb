"""The inventory's lists, pages and forms."""

import bisect
import itertools
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import localize_input
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.utils.translation import gettext_lazy

from inventory import bookings
from inventory.bookings import Refused
from inventory.chart import chart, quarters_shown
from inventory.figures import (Bulk, Consumption, bulk, consumption,
                               containers_from, molar_mass, proposed_amount)
from inventory.forms import (ROWS, ConsumptionForm, CorrectionForm,
                             FillForm, ItemEditForm, ItemForm,
                             LotCorrectionForm, LotEditForm, LotForm,
                             NoteEditForm, NoteForm, ReversalForm,
                             show_refusal)
from inventory.history import history_entries
from inventory.models import (FACTOR, LEVEL_ORDER, Article, DeliveryNote,
                              Item, Level, Lot, Movement, plain)
from inventory.statistics import Statistics, statistics
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
    """An item of the item list with its consumption, its bulk and the
    figures of its statistics popup.
    HEAT_MEAN and HEAT_YEAR are the classes of the heat of its mean per
    year and of its current year's consumption, empty without one;
    CATEGORY_START tells whether it is the first row of its category
    after another category's."""

    item: Item
    figures: Consumption
    bulk: Bulk
    statistics: Statistics
    heat_mean: str = ""
    heat_year: str = ""
    category_start: bool = False

    def searched(self) -> str:
        """The text the list's search looks in, folded for a comparison
        regardless of case: the article number, category and note, and
        the substance's key, names and short name."""
        item = self.item
        substance = item.substance
        return "\n".join([item.article_number or "", item.category,
                          item.note, substance.key, substance.name,
                          substance.name_de,
                          substance.short_name]).casefold()


def container_code(item: Item) -> str:
    """The value that names ITEM's container size in the list's filter:
    the size without trailing zeros and the unit's code, as ``2.5 mg``
    or ``10 umol``."""
    return f"{plain(item.size)} {item.unit}"


def folded(text: str) -> str | None:
    """TEXT regardless of case, or None when it is empty."""
    return text.casefold() or None


def located(text: str) -> tuple[Any, ...] | None:
    """The natural order of the location TEXT, or None when it is
    empty."""
    return natural(text) if text else None


# The value each sort key orders a row by, None for a row without one,
# in the order of the list's columns.
SORT_VALUES: dict[str, Callable[[Row], Any]] = {
    "number": lambda row: row.item.article_number,
    "name": lambda row: row.item.name.casefold(),
    "category": lambda row: folded(row.item.category),
    "container": lambda row: row.item.container_order(),
    "stock": lambda row: (LEVEL_ORDER[row.figures.level],
                          row.figures.coverage is None,
                          row.figures.coverage or 0),
    "mean_year": lambda row: row.figures.mean_year,
    "this_year": lambda row: row.figures.this_year,
    "coverage": lambda row: row.figures.coverage,
    "compartment": lambda row: located(row.item.compartment),
    "box": lambda row: located(row.item.box),
    "bulk": lambda row: row.bulk.containers if row.bulk.lots else None,
    "note": lambda row: folded(row.item.note),
}
SORTS = tuple(SORT_VALUES)
DEFAULT_SORT = "category"
# The parameters of the filters; the last three sit under "More
# filters".
FILTERS = ("q", "category", "stock", "container", "compartment", "box")
MORE_FILTERS = ("container", "compartment", "box")
# The columns that break ties in the default order.
TIES = ("number", "container")
# The columns that right-align their numbers; those the view controls
# cannot hide; and those hidden until the user shows them.
NUMERIC = ("container", "stock", "mean_year", "this_year", "coverage")
FIXED_COLUMNS = ("number", "name", "stock")
HIDDEN_COLUMNS = ("compartment", "box", "note")


@dataclass(frozen=True)
class ItemFilters:
    """The item list's filters and order as the query gives them, each
    unknown value replaced by its default: Q, the searched text;
    CATEGORY, CONTAINER as ``container_code`` gives it, COMPARTMENT and
    BOX, admitting the items with that value; STOCK, any level or
    empty, admitting that level alone; SORT, one of ``SORTS``,
    ``category`` by default; and DESCENDING, whether ``dir=desc``
    reverses the order."""

    q: str = ""
    category: str = ""
    stock: str = ""
    container: str = ""
    compartment: str = ""
    box: str = ""
    sort: str = DEFAULT_SORT
    descending: bool = False

    @classmethod
    def from_query(cls, query: Any) -> "ItemFilters":
        """Return the filters of QUERY, a mapping of GET parameters."""
        given = {name: query.get(name, "").strip() for name in FILTERS}
        if given["stock"] not in Level.values:
            given["stock"] = ""
        sort = query.get("sort", "")
        return cls(**given, sort=sort if sort in SORTS else DEFAULT_SORT,
                   descending=query.get("dir") == "desc")

    @property
    def active(self) -> bool:
        """Whether any filter is in force."""
        return any(getattr(self, name) for name in FILTERS)

    @property
    def more(self) -> int:
        """The number of the filters under "More filters" in force."""
        return sum(1 for name in MORE_FILTERS if getattr(self, name))

    def admits(self, row: Row) -> bool:
        """Whether ROW passes every filter."""
        item = row.item
        return ((not self.category or item.category == self.category)
                and (not self.container
                     or container_code(item) == self.container)
                and (not self.compartment
                     or item.compartment == self.compartment)
                and (not self.box or item.box == self.box)
                and (not self.stock or row.figures.level == self.stock)
                and (not self.q or self.q.casefold() in row.searched()))

    def link(self, sort: str, descending: bool = False,
             filtered: bool = True) -> str:
        """The list's address in the order of SORT, reversed when
        DESCENDING, with the filters in force when FILTERED."""
        pairs = [(name, getattr(self, name)) for name in FILTERS
                 if filtered and getattr(self, name)]
        pairs.append(("sort", sort))
        if descending:
            pairs.append(("dir", "desc"))
        return "?" + urlencode(pairs)

    def ordered(self, rows: list[Row]) -> list[Row]:
        """ROWS, given in the default order, in the order in force: by
        the sort key's value, reversed when descending, rows without one
        after the others; ties keep their order."""
        value = SORT_VALUES[self.sort]
        present = [row for row in rows if value(row) is not None]
        present.sort(key=value, reverse=self.descending)
        return present + [row for row in rows if value(row) is None]


@dataclass(frozen=True)
class Column:
    """A column of the item list: its sort KEY, or ``location``, its
    LABEL, the UNIT shown beneath it, the HREF its header links to,
    empty for a column that does not sort, and ARIA_SORT,
    ``ascending`` or ``descending`` for the column in force, else
    empty."""

    key: str
    label: str
    unit: str
    href: str
    aria_sort: str

    @property
    def numeric(self) -> bool:
        """Whether the column right-aligns its numbers."""
        return self.key in NUMERIC


def column_labels(year: int) -> list[tuple[str, str, str]]:
    """The item list's columns in the active language, in their order,
    each as its key, its label and the unit beneath it, with YEAR the
    current year."""
    return [
        ("number", _("Article no."), ""), ("name", _("Name"), ""),
        ("category", _("Category"), ""), ("container", _("Container"), ""),
        ("stock", _("Stock"), _("containers")),
        ("mean_year", _("Mean per year"), _("containers / year")),
        ("this_year", pgettext("item list", "Delivered"),
         _("%(year)s · containers") % {"year": year}),
        ("coverage", _("Coverage"), _("quarters")),
        ("location", pgettext("item", "Location"), ""),
        ("compartment", _("Compartment"), ""), ("box", _("Box"), ""),
        ("bulk", _("Bulk available"), ""),
        ("note", pgettext("inventory", "Note"), "")]


def columns(filters: ItemFilters, year: int) -> list[Column]:
    """The columns of the list FILTERS shows in YEAR, each header but
    the location's linking to the list sorted by it, reversed when it
    is in force and not reversed."""
    found = []
    for key, label, unit in column_labels(year):
        current = key == filters.sort
        found.append(Column(
            key=key, label=label, unit=unit,
            href="" if key not in SORTS
            else filters.link(key, current and not filters.descending),
            aria_sort=("descending" if filters.descending else "ascending")
            if current else ""))
    return found


def order_text(filters: ItemFilters, year: int) -> str:
    """The order FILTERS put the list in, in words: the sorting column
    and the columns that break its ties, each ascending or
    descending."""
    labels = {key: label for key, label, _unit in column_labels(year)}
    rest = ", ".join(labels[key] for key in TIES if key != filters.sort)
    if filters.descending:
        return _("%(column)s descending, %(rest)s ascending") % {
            "column": labels[filters.sort], "rest": rest}
    return _("%(columns)s ascending") % {
        "columns": ", ".join([labels[filters.sort], rest])}


def heat(value: Any, positives: list[Any]) -> str:
    """The heat class of VALUE among POSITIVES, the values above zero of
    its kind across the inventory in ascending order: ``heat-<n>`` with
    n = 1 + 5B // N, B the values below it and N their number; empty
    for a value of zero or none."""
    if value is None or value <= 0:
        return ""
    below = bisect.bisect_left(positives, value)
    return f"heat-{1 + 5 * below // len(positives)}"


def heated(rows: list[Row]) -> list[Row]:
    """ROWS with the heats of their means per year and of their current
    year's consumption, each counted over ROWS."""
    means = sorted(row.figures.mean_year for row in rows
                   if row.figures.mean_year is not None
                   and row.figures.mean_year > 0)
    years = sorted(row.figures.this_year for row in rows
                   if row.figures.this_year > 0)
    return [replace(row, heat_mean=heat(row.figures.mean_year, means),
                    heat_year=heat(row.figures.this_year, years))
            for row in rows]


def by_category(rows: list[Row]) -> list[Row]:
    """ROWS, each whose category differs from that of the row before
    marked as starting a category."""
    return [replace(row, category_start=bool(
        index and folded(row.item.category)
        != folded(rows[index - 1].item.category)))
        for index, row in enumerate(rows)]


@dataclass(frozen=True)
class StockEntry:
    """An entry of the stock menu: its LEVEL, empty for every level, its
    LABEL and MEANING, the COUNT of items it lists, the HREF of the list
    it chooses, and whether it is CURRENT."""

    level: str
    label: str
    meaning: str
    count: int
    href: str
    current: bool


MEANINGS = {
    Level.OUT: gettext_lazy("no container left"),
    Level.CRITICAL: gettext_lazy("below half the mean per quarter"),
    Level.LOW: gettext_lazy("below the mean per quarter"),
    Level.WATCH: gettext_lazy("below twice the mean per quarter"),
    Level.OK: gettext_lazy("at least twice the mean per quarter"),
    Level.UNDELIVERED: gettext_lazy("no consumption yet"),
    Level.DORMANT: gettext_lazy(
        "set aside, or nothing delivered this year or last"),
}


def stock_menu(rows: list[Row], filters: ItemFilters) -> list[StockEntry]:
    """The stock menu's entries: every level, then each level in urgency
    order, each counting the items of ROWS that every filter of FILTERS
    but the level admits, and linking to the list with those filters,
    the order in force and its level."""
    others = replace(filters, stock="")
    counts = Counter(row.figures.level for row in rows
                     if others.admits(row))

    def entry(level: str, label: str, meaning: str, count: int
              ) -> StockEntry:
        return StockEntry(
            level=level, label=label, meaning=meaning, count=count,
            href=LIST + replace(filters, stock=level).link(
                filters.sort, filters.descending),
            current=filters.stock == level)

    return [entry("", _("All stock statuses"), "", counts.total()),
            *(entry(level, capfirst(str(level.label)), str(MEANINGS[level]),
                    counts[level]) for level in Level)]


def item_list(request: HttpRequest) -> HttpResponse:
    """List the items the query's filters select, with their figures,
    heats, bulk and statistics, in the order the query names."""
    today = timezone.localdate()
    filters = ItemFilters.from_query(request.GET)
    items = sorted(Item.objects.select_related("article__substance"),
                   key=Item.sort_key)
    lots = list(Lot.objects.filter(amount__gt=0).order_by("made_on", "id"))
    rows = []
    for item in items:
        figures = consumption(item, today)
        rows.append(Row(item=item, figures=figures, bulk=bulk(item, lots),
                        statistics=statistics(figures, today)))
    rows = heated(rows)
    shown = filters.ordered([row for row in rows if filters.admits(row)])
    if filters.sort == "category":
        shown = by_category(shown)
    containers = {container_code(item): item.container for item in
                  sorted(items, key=Item.container_order)}
    menu = stock_menu(rows, filters)
    shown_columns = columns(filters, today.year)
    return render(request, "inventory/item_list.html", {
        "rows": shown,
        "total": len(rows),
        "filters": filters,
        "columns": shown_columns,
        "view_columns": [(column, column.key not in HIDDEN_COLUMNS)
                         for column in shown_columns
                         if column.key not in FIXED_COLUMNS],
        "order": order_text(filters, today.year),
        "reset": filters.link(filters.sort, filters.descending,
                              filtered=False),
        "categories": sorted({item.category for item in items
                              if item.category}),
        "containers": list(containers.items()),
        "compartments": in_use("compartment"),
        "boxes": in_use("box"),
        "stock_menu": menu,
        "stock_choice": next(entry for entry in menu if entry.current),
        "heats": [f"heat-{n}" for n in range(1, 6)],
        "today": today,
        "tabs": tabs(LIST),
    })


def lot_list(request: HttpRequest) -> HttpResponse:
    """List the open lots of every substance, and the used-up ones too
    with ``empty=1``, by the substance's name regardless of case, then
    by date, oldest first and lots without one last."""
    empty = request.GET.get("empty") == "1"
    lots = Lot.objects.select_related("substance__article")
    if not empty:
        lots = lots.filter(amount__gt=0)
    shown = sorted(lots, key=lambda lot: (
        lot.substance.shown_name.casefold(), lot.made_on is None,
        lot.made_on or date.min, lot.pk))
    return render(request, "inventory/lot_list.html", {
        "lots": shown,
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
        "items": sorted(Item.objects.filter(
            article__article_number__isnull=False).select_related(
                "article__substance"), key=Item.sort_key),
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
    item = get_object_or_404(Item.objects.select_related(
        "article__substance"), pk=pk)
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
    found = plan.article(item.article_number, today) \
        if item.article_number is not None else None
    lots = Lot.objects.filter(substance_id=item.article_id,
                              amount__gt=0).order_by("made_on", "id")
    return render(request, "inventory/item_page.html", {
        "item": item,
        "today": today,
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
    lot = get_object_or_404(Lot.objects.select_related(
        "substance__article"), pk=pk)
    movements = lot.movements.select_related(
        "user", "item_movement__item__article").order_by("-id")
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
                  for line in note.lines.select_related(
                      "item__article__substance")],
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
    """The categories of the articles, for the category's
    ``datalist``."""
    return Article.objects.exclude(category="").order_by("category") \
        .values_list("category", flat=True).distinct()


def in_use(field: str) -> list[str]:
    """The values of the items' FIELD, ``compartment`` or ``box``, each
    once, in natural order."""
    return sorted(set(Item.objects.exclude(**{field: ""}).values_list(
        field, flat=True)), key=natural)


def natural(text: str) -> tuple[Any, ...]:
    """The order of TEXT among locations: its runs of the digits 0 to 9
    by their value, so that ``2`` comes before ``10``, the rest, digits
    of other scripts included, as text regardless of case."""
    return tuple(int(part) if odd else part.casefold()
                 for odd, part in zip(itertools.cycle((False, True)),
                                      re.split(r"([0-9]+)", text)))


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
        {"title": _("New item"), "cancel": LIST, "substances": True,
         "categories": categories(), "compartments": in_use("compartment"),
         "boxes": in_use("box")})


@login_required
def item_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the state, stock entry, location and note of the item PK
    and its article's category, and give its article the article number
    entered while it has none."""
    item = get_object_or_404(Item.objects.select_related(
        "article__substance"), pk=pk)
    title = _("Edit %(item)s") % {"item": item}

    def book(data: dict[str, Any]) -> HttpResponse:
        with transaction.atomic():
            if data.get("article_number"):
                bookings.assign_article_number(request.user, item.article,
                                               data["article_number"])
            form.instance._history_user = request.user
            form.save()
        stored = Item.objects.select_related("article__substance").get(
            pk=item.pk)
        return saved(request, _("Item %(item)s saved.") % {"item": stored},
                     item_url(stored))

    form = ItemEditForm(request.POST or None, instance=item)
    return form_page(
        request, form, book,
        {"title": title, "cancel": item_url(item),
         "categories": categories(), "compartments": in_use("compartment"),
         "boxes": in_use("box")})


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
            "Without a molar mass of the substance, enter the amount "
            "taken."))
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


def locations() -> Any:
    """The locations of the lots, for the location's ``datalist``."""
    return Lot.objects.exclude(location="").order_by("location") \
        .values_list("location", flat=True).distinct()


@login_required
def lot_new(request: HttpRequest) -> HttpResponse:
    """Create a bulk lot with its opening amount, booked by the
    signed-in user; ``substance``, ``batch`` and ``made_on`` in the
    query fill in the substance's key, the batch and the date."""

    def book(data: dict[str, Any]) -> HttpResponse:
        lot = bookings.create_lot(request.user, **data)
        return saved(request, _("Bulk lot %(lot)s created.") % {"lot": lot},
                     lot_url(lot))

    form = LotForm(request.POST or None, initial={
        "substance": request.GET.get("substance", ""),
        "batch": request.GET.get("batch", ""),
        "made_on": request.GET.get("made_on", "")})
    return form_page(request, form, book,
                     {"title": _("New bulk lot"), "cancel": BULK,
                      "substances": True, "locations": locations()})


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

