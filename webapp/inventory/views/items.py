"""End-product item list, detail, page, consumption, and item form views."""

import bisect
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.formats import localize_input
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory import bookings
from inventory.chart import chart, quarters_shown
from inventory.figures import (Bulk, Consumption, ConsumptionBatch, bulk,
                               consumption, containers_from, molar_mass,
                               proposed_amount, vessels_by_substance)
from inventory.forms import (ConsumptionForm, CorrectionForm, FillForm,
                             ItemEditForm, ItemForm, ReversalForm)
from inventory.history import history_entries
from inventory.models import (FACTOR, LEVEL_ORDER, Item, Level, Movement,
                              Vessel, plain)
from inventory.statistics import Statistics, statistics
from inventory.summaries import natural
from inventory.views.common import (LIST, VIEW_COOKIE, categories,
                                    consumption_url, form_page,
                                    htmx_detail_or_redirect, in_use, item_form,
                                    item_url, layers, list_view, open_vessels,
                                    pick_selected, render_form, saved, tabs)
from orgsyndb_web.lists import (Order, SortColumn, clean_choice,
                                htmx_list_push_url, sort_value)
from planning import plan


@dataclass(frozen=True)
class Row:
    """An item of the item list with its consumption, its bulk and the
    statistics of its details.
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


@dataclass(frozen=True)
class ColumnSpec:
    """A column of the item list as the model defines it. KEY is its
    sort key, LABEL its heading and UNIT the text beneath it, both lazy
    strings of the active language, UNIT possibly holding ``%(year)s``
    for the current year. NUMERIC tells whether it right-aligns its
    numbers. VALUE gives the value that orders a row when the list is
    sorted by the column, None for a row without one. GROUP is ``base``
    for a column both views show and ``table`` for one the table view
    adds; SHOWN tells whether it shows at first."""

    key: str
    label: Any
    unit: Any
    numeric: bool
    value: Callable[[Row], Any]
    group: str
    shown: bool = True


COLUMN_MODEL: tuple[ColumnSpec, ...] = (
    ColumnSpec("number", gettext_lazy("Article no."), "", False,
               lambda row: sort_value(row.item.article_number), "base"),
    ColumnSpec("name", gettext_lazy("Name"), "", False,
               lambda row: sort_value(row.item.name), "base"),
    ColumnSpec("category", gettext_lazy("Category"), "", False,
               lambda row: sort_value(row.item.category), "base"),
    ColumnSpec("container", gettext_lazy("Container"), "", True,
               lambda row: row.item.container_order(), "base"),
    ColumnSpec("stock", gettext_lazy("Stock"), gettext_lazy("containers"),
               True,
               lambda row: (LEVEL_ORDER[row.figures.level],
                            row.figures.coverage is None,
                            row.figures.coverage or 0), "base"),
    ColumnSpec("mean_year", gettext_lazy("Mean per year"),
               gettext_lazy("containers / year"), True,
               lambda row: row.figures.mean_year, "table"),
    ColumnSpec("this_year", pgettext_lazy("item list", "Delivered"),
               gettext_lazy("%(year)s · containers"), True,
               lambda row: row.figures.this_year, "table"),
    ColumnSpec("coverage", gettext_lazy("Coverage"),
               gettext_lazy("quarters"), True,
               lambda row: row.figures.coverage, "table"),
    ColumnSpec("compartment", gettext_lazy("Compartment"), "", False,
               lambda row: sort_value(row.item.compartment), "table"),
    ColumnSpec("box", gettext_lazy("Box"), "", False,
               lambda row: sort_value(row.item.box), "table"),
    ColumnSpec("bulk", gettext_lazy("Bulk available"), "", False,
               lambda row: row.bulk.containers if row.bulk.vessels else None,
               "table"),
    ColumnSpec("note", pgettext_lazy("inventory", "Note"), "", False,
               lambda row: sort_value(row.item.note), "table", shown=False),
)
SORT_COLUMNS: tuple[SortColumn, ...] = tuple(
    SortColumn(spec.key, spec.label, spec.value) for spec in COLUMN_MODEL
)
SORTS = tuple(spec.key for spec in COLUMN_MODEL)
DEFAULT_SORT = "category"
FILTERS = ("q", "category", "stock", "container", "compartment", "box")
MORE_FILTERS = ("container", "compartment", "box")
TIES = ("number", "container")


@dataclass(frozen=True)
class ItemFilters:
    """The item list's filters and order as the query gives them, each
    unknown value replaced by its default: Q, the searched text;
    CATEGORY, CONTAINER as ``container_code`` gives it, COMPARTMENT and
    BOX, admitting the items with that value; STOCK, any level or
    empty, admitting that level alone; and ORDER, the resolved sort
    order."""

    q: str = ""
    category: str = ""
    stock: str = ""
    container: str = ""
    compartment: str = ""
    box: str = ""
    order: Order = Order(SORT_COLUMNS, DEFAULT_SORT, False,
                         DEFAULT_SORT, False)

    @property
    def sort(self) -> str:
        """The active sort column key."""
        return self.order.key

    @property
    def descending(self) -> bool:
        """Whether the active sort order is descending."""
        return self.order.descending

    @classmethod
    def from_query(cls, query: Any) -> "ItemFilters":
        """Return the filters of QUERY, a mapping of GET parameters."""
        given = {name: query.get(name, "").strip() for name in FILTERS}
        given["stock"] = clean_choice(given["stock"], Level.values)
        return cls(
            **given,
            order=Order.from_query(query, SORT_COLUMNS, DEFAULT_SORT),
        )

    @property
    def active(self) -> bool:
        """Whether any filter is in force."""
        return any(getattr(self, name) for name in FILTERS)

    @property
    def more(self) -> int:
        """The number of the filters under "More filters" in force."""
        return sum(1 for name in MORE_FILTERS if getattr(self, name))

    def filter_pairs(self) -> list[tuple[str, str]]:
        """Return the active filter query pairs in canonical order."""
        return [(name, getattr(self, name)) for name in FILTERS
                if getattr(self, name)]

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

    def canonical_query(self, filtered: bool = True,
                        selected: str = "") -> str:
        """Return the canonical query string with active filters when
        FILTERED, non-default order, and SELECTED when given."""
        pairs = self.filter_pairs() if filtered else []
        pairs.extend(self.order.pairs())
        if selected:
            pairs.append(("selected", selected))
        return f"?{urlencode(pairs)}" if pairs else ""

    def ordered(self, rows: list[Row]) -> list[Row]:
        """ROWS, given in the default order, in the order in force: by
        the sort key's value, reversed when descending, rows without one
        after the others; ties keep their order."""
        return self.order.ordered(rows)


@dataclass(frozen=True)
class Column:
    """A column of the item list as a page shows it: the SPEC that
    defines it, its LABEL and UNIT in the active language, the HREF its
    header links to, and ARIA_SORT, ``ascending`` or ``descending`` for
    the column in force, else empty."""

    spec: ColumnSpec
    label: str
    unit: str
    href: str
    aria_sort: str

    @property
    def key(self) -> str:
        """The column's sort key."""
        return self.spec.key

    @property
    def numeric(self) -> bool:
        """Whether the column right-aligns its numbers."""
        return self.spec.numeric

    @property
    def table_only(self) -> bool:
        """Whether the table view alone shows the column."""
        return self.spec.group == "table"

    @property
    def shown(self) -> bool:
        """Whether the column shows at first."""
        return self.spec.shown

    @property
    def classes(self) -> str:
        """The classes of the column's header and cells: ``col-`` and
        its key, ``number`` for a numeric column and ``table-only`` for
        one that only the table view shows."""
        return " ".join([f"col-{self.key}",
                         *(["number"] if self.numeric else []),
                         *(["table-only"] if self.table_only else [])])


def columns(filters: ItemFilters, year: int, selected: str = ""
            ) -> list[Column]:
    """The columns of the list FILTERS shows in YEAR, in the model's
    order, each header linking to the list sorted by it, reversed when
    it is in force and not reversed, and naming the item SELECTED, an
    id, unless that is empty."""
    filter_pairs = filters.filter_pairs()
    return [Column(
        spec=spec, label=str(spec.label),
        unit=str(spec.unit) % {"year": year},
        href=LIST + filters.order.link(spec.key, filter_pairs, selected),
        aria_sort=filters.order.aria_sort(spec.key),
    ) for spec in COLUMN_MODEL]


def order_text(filters: ItemFilters) -> str:
    """The order FILTERS put the list in, in words: the sorting column
    and the columns that break its ties, each ascending or
    descending."""
    labels = {spec.key: str(spec.label) for spec in COLUMN_MODEL}
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


def stock_menu(rows: list[Row], filters: ItemFilters, selected: str = ""
               ) -> list[StockEntry]:
    """The stock menu's entries: every level, then each level in urgency
    order, each counting the items of ROWS that every filter of FILTERS
    but the level admits, and linking to the list with those filters,
    the order in force, its level and the item SELECTED, an id, unless
    that is empty."""
    others = replace(filters, stock="")
    counts = Counter(row.figures.level for row in rows
                     if others.admits(row))

    def entry(level: str, label: str, meaning: str, count: int
              ) -> StockEntry:
        return StockEntry(
            level=level, label=label, meaning=meaning, count=count,
            href=LIST + replace(filters, stock=level).canonical_query(
                selected=selected),
            current=filters.stock == level)

    return [entry("", _("All stock statuses"), "", counts.total()),
            *(entry(level, capfirst(str(level.label)), str(MEANINGS[level]),
                    counts[level]) for level in Level)]


def row_of(item: Item, today: date, vessels: list[Vessel],
           figures: Consumption | None = None) -> Row:
    """The row of ITEM as of TODAY, with its bulk among VESSELS, the
    open vessels, and without heats."""
    if figures is None:
        figures = consumption(item, today)
    return Row(item=item, figures=figures, bulk=bulk(item, vessels),
               statistics=statistics(figures, today))


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def item_list(request: HttpRequest) -> HttpResponse:
    """List the items the query's filters select, with their figures,
    heats and bulk, in the order the query names, in the view the cookie
    ``item-list-view`` remembers, ``details`` or else ``table``. The
    item that ``selected`` names among those listed, else the first one
    listed, is the selected one: its row is marked and its details
    shown, and the list's own links and its filter form name it. The
    answer varies with the cookies."""
    today = timezone.localdate()
    filters = ItemFilters.from_query(request.GET)
    items = sorted(Item.objects.with_substance(), key=Item.sort_key)
    by_substance = vessels_by_substance(open_vessels())
    batch = ConsumptionBatch.load(items)
    rows = heated([
        row_of(item, today, by_substance.get(item.article_id, []),
               batch.consumption(item, today))
        for item in items])
    shown = filters.ordered([row for row in rows if filters.admits(row)])
    if filters.sort == "category":
        shown = by_category(shown)
    containers = {container_code(item): item.container for item in
                  sorted(items, key=Item.container_order)}
    chosen, selected = pick_selected(
        shown, request.GET.get("selected", ""), lambda row: row.item.pk)
    menu = stock_menu(rows, filters, selected)
    shown_columns = columns(filters, today.year, selected)
    response = render(request, "inventory/item_list.html", {
        "rows": shown,
        "chosen": chosen,
        "selected": selected,
        "view": list_view(request, VIEW_COOKIE),
        "total": len(rows),
        "filters": filters,
        "columns": shown_columns,
        "table_columns": [column for column in shown_columns
                          if column.table_only],
        "order": order_text(filters),
        "sort_order": filters.order,
        "reset": LIST + filters.canonical_query(filtered=False,
                                                selected=selected),
        "categories": sorted({item.category for item in items
                              if item.category}),
        "containers": list(containers.items()),
        "compartments": sorted({item.compartment for item in items
                                if item.compartment}, key=natural),
        "boxes": sorted({item.box for item in items if item.box},
                        key=natural),
        "stock_menu": menu,
        "stock_choice": next(entry for entry in menu if entry.current),
        "heats": [f"heat-{n}" for n in range(1, 6)],
        "today": today,
        "tabs": tabs(LIST),
        "layers": layers(LIST),
    })
    return htmx_list_push_url(
        request, response,
        LIST + filters.canonical_query(selected=selected))


@vary_on_headers("HX-Request", "HX-Current-URL")
def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the item PK alone, as the item list shows them beside its table,
    and any other request with a redirect to the list with ``selected``
    naming the item. Answer 404 for an unknown ID. The answer varies
    with the ``HX-Request`` header."""
    item = get_object_or_404(Item.objects.with_substance(), pk=pk)

    def detail_context() -> dict[str, Any]:
        today = timezone.localdate()
        return {
            "chosen": row_of(item, today, open_vessels(item)),
            "today": today,
        }

    return htmx_detail_or_redirect(
        request, LIST, item.pk, "inventory/item_list.html#detail",
        detail_context)


@dataclass(frozen=True)
class LedgerRow:
    """A movement as a ledger shows it: whether it is reversed, and
    whether it may still be reversed."""

    movement: Movement
    reversed: bool
    reversible: bool


@dataclass(frozen=True)
class QuarterRow:
    """A quarter of the chart's table: its entered value, ``stored``
    telling whether there is one, its deliveries and their sum, and the
    path of the consumption form for the quarter, None where the table
    offers none."""

    year: int
    quarter: int
    entered: int
    delivered: int
    total: int
    stored: bool = False
    href: str | None = None


def consumption_section(item: Item, today: date, links: bool,
                        figures: Consumption | None = None
                        ) -> dict[str, Any]:
    """Return the context of the template ``inventory/consumption.html``
    for ITEM as of TODAY: ``figures``, its consumption (see
    ``inventory.figures.consumption``), ``chart``, and ``quarters``, a
    ``QuarterRow`` for each quarter the chart draws, with ``links``
    telling whether any row has a link.

    A row has the path of the consumption form for its quarter when
    LINKS is true, the item has an article number, the quarter has begun
    and the item has no line of a historical delivery note in it that is
    not reversed; the quarter then takes an entered value (see
    ``bookings.enter_consumption``).
    """
    if figures is None:
        figures = consumption(item, today)
    open_for_links = links and item.article_number is not None
    held = bookings.held_quarters(item) if open_for_links else set()
    rows = []
    for year, quarter in quarters_shown(today.year):
        key = (year, quarter)
        takes = (open_for_links and bookings.has_begun(year, quarter, today)
                 and key not in held)
        rows.append(QuarterRow(
            year=year, quarter=quarter,
            entered=figures.entered.get(key, 0),
            delivered=figures.delivered.get(key, 0),
            total=figures.total(key), stored=key in figures.entered,
            href=consumption_url(item, year, quarter) if takes else None))
    return {"figures": figures, "chart": chart(figures, today.year),
            "quarters": rows, "links": any(row.href for row in rows)}


def item_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the item PK with its figures, containers by batch, chart,
    movements, bulk, forecast and history; answer 404 for an unknown
    ID.

    The containers by batch are the shares above zero: ``stocks`` those
    of a batch, and ``unknown`` the containers of unknown batch.
    """
    item = get_object_or_404(Item.objects.with_substance(), pk=pk)
    today = timezone.localdate()
    movements = item.movements.select_related(
        "user", "delivery_note", "reversal", "batch").order_by("-id")
    ledger = []
    for movement in movements:
        done = hasattr(movement, "reversal")
        ledger.append(LedgerRow(movement=movement, reversed=done,
                                reversible=movement.reversible
                                and not done))
    mass = molar_mass(item)
    found = plan.article(item.article_number, today) \
        if item.article_number is not None else None
    entry = found.entry(item) if found else None
    vessels = open_vessels(item)
    held = [stock for stock in item.stocks.select_related("batch")
            if stock.quantity]
    return render(request, "inventory/item_page.html", {
        "item": item,
        "today": today,
        "stocks": [stock for stock in held if stock.batch_id is not None],
        "unknown": sum(stock.quantity for stock in held
                       if stock.batch_id is None),
        **consumption_section(item, today, request.user.is_authenticated,
                              figures=entry.figures if entry else None),
        "ledger": ledger,
        "vessels": [(vessel, containers_from(vessel, item, mass))
                    for vessel in vessels],
        "bulk": bulk(item, vessels),
        "forecast": found,
        "entry": entry,
        "history": history_entries(item),
    })


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


@item_form
def item_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the state, stock entry, location and note of the item PK
    and its article's category, and give its article the article number
    entered while it has none."""
    item = get_object_or_404(Item.objects.with_substance(), pk=pk)
    title = _("Edit %(item)s") % {"item": item}

    def book(data: dict[str, Any]) -> HttpResponse:
        with transaction.atomic():
            if data.get("article_number"):
                bookings.assign_article_number(request.user, item.article,
                                               data["article_number"])
            form.instance._history_user = request.user
            form.save()
        stored = Item.objects.with_substance().get(pk=item.pk)
        return saved(request, _("Item %(item)s saved.") % {"item": stored},
                     item_url(stored), stored)

    form = ItemEditForm(request.POST or None, instance=item)
    return form_page(
        request, form, book,
        {"title": title, "cancel": item_url(item),
         "categories": categories(), "compartments": in_use("compartment"),
         "boxes": in_use("box")}, dialog=True)


def proposed(request: HttpRequest, form: FillForm, item: Item) -> FillForm:
    """Return the valid FORM of ITEM again with the amount set to the
    proposal, or FORM with an error where none can be made."""
    vessel = form.cleaned_data["vessel"]
    base = proposed_amount(item, form.cleaned_data["count"], vessel)
    if base is None:
        form.add_error("amount", _(
            "Without a molar mass of the substance, enter the amount "
            "taken."))
        return form
    data = request.POST.copy()
    data["amount"] = localize_input(plain(base / FACTOR[vessel.unit]))
    again = FillForm(data, item=item)
    again.is_valid()
    return again


def fill_context(item: Item) -> dict[str, Any]:
    """Return the context of the filling form of ITEM."""
    return {"title": _("Fill %(item)s") % {"item": item},
            "cancel": item_url(item), "item": item, "propose": True}


@item_form
def item_fill(request: HttpRequest, pk: int) -> HttpResponse:
    """Book a filling of the item PK from a vessel of its substance;
    ``vessel`` in the query chooses that vessel when the form offers it.

    The button ``propose`` books nothing: it shows the form again with
    the amount set to the proposal for the count and vessel entered, or
    an error at the amount when there is no molar mass to convert with.
    """
    item = get_object_or_404(Item, pk=pk)
    form = FillForm(request.POST or None, item=item)
    wanted = request.GET.get("vessel", "")
    if not form.is_bound and wanted.isdigit() and form.fields[
            "vessel"].queryset.filter(pk=int(wanted)).exists():
        form.initial["vessel"] = int(wanted)
    if request.method == "POST" and "propose" in request.POST:
        if form.is_valid():
            form = proposed(request, form, item)
        return render_form(request, form, fill_context(item), dialog=True)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.fill(request.user, item, **data)
        return saved(request, _("Filling of %(item)s booked.")
                     % {"item": item}, item_url(item), item)

    return form_page(request, form, book, fill_context(item),
                     dialog=True)


@item_form
def item_correct(request: HttpRequest, pk: int) -> HttpResponse:
    """Set the count of one share of the item PK after counting: the
    share of the batch chosen, or of unknown batch."""
    item = get_object_or_404(Item, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.correct(request.user, item, **data)
        return saved(request, _("Count of %(item)s corrected.")
                     % {"item": item}, item_url(item), item)

    return form_page(
        request, CorrectionForm(request.POST or None, item=item), book,
        {"title": _("Correct the count of %(item)s") % {"item": item},
         "cancel": item_url(item)}, dialog=True)


@item_form
def movement_reverse(request: HttpRequest, pk: int, movement: int
                     ) -> HttpResponse:
    """Reverse the delivery or filling MOVEMENT of the item PK."""
    item = get_object_or_404(Item, pk=pk)
    chosen = get_object_or_404(Movement, pk=movement, item=item)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.reverse(request.user, chosen, note=data["note"])
        return saved(request, _("%(kind)s of %(item)s reversed.")
                     % {"kind": chosen.get_kind_display(), "item": item},
                     item_url(item), item)

    return form_page(
        request, ReversalForm(request.POST or None), book,
        {"title": _("Reverse: %(kind)s of %(count)s, %(date)s") % {
            "kind": chosen.get_kind_display(), "count": chosen.count,
            "date": localize_input(chosen.date)},
         "cancel": item_url(item)}, dialog=True)


def fixed_quarter(request: HttpRequest, today: date
                  ) -> tuple[int, int] | None:
    """Return the year and quarter that the query of REQUEST, ``year``
    and ``quarter``, names as a quarter that has begun by TODAY; None
    when either is missing, not a whole number, outside 1 to 9999 and 1
    to 4, or when the quarter has not begun."""
    values = [request.GET.get(name, "") for name in ("year", "quarter")]
    if not all(value.isascii() and value.isdigit() and len(value) <= 4
               for value in values):
        return None
    year, quarter = map(int, values)
    if not (1 <= year <= 9999 and 1 <= quarter <= 4
            and bookings.has_begun(year, quarter, today)):
        return None
    return year, quarter


@item_form
def item_consumption(request: HttpRequest, pk: int) -> HttpResponse:
    """Enter the consumption of a quarter of the item PK, or remove it
    with an empty count.

    A query ``year=<year>&quarter=<quarter>`` naming a quarter that has
    begun fixes the form to that quarter (see ``fixed_quarter``), which
    shows the quarter's stored count, if any, as the value a save
    replaces; any other query leaves the year and quarter to choose.
    The form shows the item's consumption beside its fields
    (``consumption_section``).
    """
    item = get_object_or_404(Item, pk=pk)
    today = timezone.localdate()
    fixed = fixed_quarter(request, today)
    stored = None if fixed is None else item.entered_consumption.filter(
        year=fixed[0], quarter=fixed[1]).values_list(
            "count", flat=True).first()

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.enter_consumption(request.user, item, **data)
        return saved(request, _("Consumption of %(item)s saved.")
                     % {"item": item}, item_url(item), item)

    return form_page(
        request,
        ConsumptionForm(request.POST or None, fixed=fixed, stored=stored),
        book,
        {"title": _("Enter consumption of %(item)s") % {"item": item},
         "cancel": item_url(item), "fixed": fixed, "stored": stored,
         **consumption_section(item, today, True)},
        template="inventory/consumption_form.html", dialog=True)
