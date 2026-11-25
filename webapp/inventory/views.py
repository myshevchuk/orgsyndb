"""The inventory's lists, pages and forms."""

import bisect
import itertools
import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from functools import wraps
from typing import Any
from urllib.parse import urlencode, urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.formats import localize_input
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory import bookings
from inventory.bookings import Refused
from inventory.chart import chart, quarters_shown
from inventory.figures import (Bulk, Consumption, bulk, consumption,
                               containers_from, molar_mass, newest_first,
                               open_amounts, proposed_amount)
from inventory.forms import (ROWS, BatchEditForm, BatchForm,
                             ConsumptionForm, CorrectionForm, FillForm,
                             ItemEditForm, ItemForm, NewVesselForm,
                             NoteEditForm, NoteForm, ReversalForm,
                             TransferForm, VesselCorrectionForm,
                             VesselEditForm, WithdrawalForm, show_refusal)
from inventory.history import history_entries
from inventory.models import (FACTOR, LEVEL_ORDER, Article, Batch,
                              DeliveryLine, DeliveryNote, Item, Level,
                              Movement, Source, StockCategory, Vessel,
                              VesselKind, VesselMovement, plain)
from inventory.statistics import Statistics, statistics
from inventory.summaries import (AgeSummary, LocationSummary, SourceSummary,
                                 SupplierSummary, age_summary,
                                 amounts_by_unit, earliest_opened, is_old,
                                 location_summary, natural, source_summary,
                                 supplier_summary)
from journal.entries import entry_for
from planning import plan
from tasks.models import Task, TaskStep
from vocabulary.models import ChemicalClass, Group, Term, descendants, tree_order

LIST = "/lab/inventory/end-products/"
INTERMEDIATES = "/lab/inventory/intermediates/"
CHEMICALS = "/lab/inventory/chemicals/"
BATCHES = "/lab/inventory/batches/"
VESSELS = "/lab/inventory/vessels/"
DELIVERIES = "/lab/inventory/deliveries/"
BULK = "/lab/inventory/end-products/bulk/"


def tabs(current: str) -> list[dict[str, Any]]:
    """Return the section tabs of the inventory, marking CURRENT, the
    path of the tab's list; the end products' layers are under
    ``LIST``."""
    return [{"url": url, "label": label, "current": url == current}
            for url, label in ((LIST, _("End products")),
                               (INTERMEDIATES, _("Intermediates")),
                               (CHEMICALS, _("Commercial chemicals")),
                               (BATCHES, _("Batches")),
                               (VESSELS, _("All vessels")))]


def layers(current: str) -> list[dict[str, Any]]:
    """Return the layers of the end products, the item list, the bulk
    list and the delivery list, each with its count, marking CURRENT,
    the path of the layer shown."""
    return [{"url": url, "label": label, "count": count,
             "current": url == current}
            for url, label, count in (
                (LIST, pgettext_lazy("layer", "Containers"),
                 Item.objects.count()),
                (BULK, pgettext_lazy("layer", "Bulk"),
                 bulk_vessels().count()),
                (DELIVERIES, pgettext_lazy("layer", "Deliveries"),
                 DeliveryNote.objects.count()))]


def bulk_vessels() -> Any:
    """Return the open vessels of the substances that have an article,
    with their batch, its step's task, the substance and its article
    read."""
    return Vessel.objects.filter(
        amount__gt=0, batch__substance__article__isnull=False
    ).select_related("batch__substance__article", "batch__task_step__task")


def open_vessels(item: Item | None = None) -> list[Vessel]:
    """Return the open vessels, those holding an amount above zero, of
    ITEM's substance, or of every substance when ITEM is None, by their
    batch's date, oldest first and undated ones last, then by ID, each
    with its batch, substance and the substance's article read."""
    vessels = Vessel.objects.filter(amount__gt=0).select_related(
        "batch__substance__article")
    if item is not None:
        vessels = vessels.filter(batch__substance_id=item.article_id)
    return sorted(vessels, key=lambda vessel: (
        vessel.batch.date is None, vessel.batch.date or date.min,
        vessel.pk))


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


# The item list's columns in the order they appear, those of the base
# group first.
COLUMN_MODEL: tuple[ColumnSpec, ...] = (
    ColumnSpec("number", gettext_lazy("Article no."), "", False,
               lambda row: row.item.article_number, "base"),
    ColumnSpec("name", gettext_lazy("Name"), "", False,
               lambda row: row.item.name.casefold(), "base"),
    ColumnSpec("category", gettext_lazy("Category"), "", False,
               lambda row: folded(row.item.category), "base"),
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
               lambda row: located(row.item.compartment), "table"),
    ColumnSpec("box", gettext_lazy("Box"), "", False,
               lambda row: located(row.item.box), "table"),
    ColumnSpec("bulk", gettext_lazy("Bulk available"), "", False,
               lambda row: row.bulk.containers if row.bulk.vessels else None,
               "table"),
    ColumnSpec("note", pgettext_lazy("inventory", "Note"), "", False,
               lambda row: folded(row.item.note), "table", shown=False),
)
SORTS = tuple(spec.key for spec in COLUMN_MODEL)
DEFAULT_SORT = "category"
# The parameters of the filters; the last three sit under "More
# filters".
FILTERS = ("q", "category", "stock", "container", "compartment", "box")
MORE_FILTERS = ("container", "compartment", "box")
# The columns that break ties in the default order.
TIES = ("number", "container")
# The cookie that remembers the view of the item list.
VIEW_COOKIE = "item-list-view"
BULK_COOKIE = "bulk-list-view"
NOTE_COOKIE = "delivery-list-view"
INTERMEDIATE_COOKIE = "intermediate-list-view"
CHEMICAL_COOKIE = "chemical-list-view"


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
             filtered: bool = True, selected: str = "") -> str:
        """The list's address in the order of SORT, reversed when
        DESCENDING, with the filters in force when FILTERED, and
        naming the item SELECTED, an id, unless that is empty."""
        pairs = [(name, getattr(self, name)) for name in FILTERS
                 if filtered and getattr(self, name)]
        pairs.append(("sort", sort))
        if descending:
            pairs.append(("dir", "desc"))
        if selected:
            pairs.append(("selected", selected))
        return "?" + urlencode(pairs)

    def ordered(self, rows: list[Row]) -> list[Row]:
        """ROWS, given in the default order, in the order in force: by
        the sort key's value, reversed when descending, rows without one
        after the others; ties keep their order."""
        value = next(spec.value for spec in COLUMN_MODEL
                     if spec.key == self.sort)
        present = [row for row in rows if value(row) is not None]
        present.sort(key=value, reverse=self.descending)
        return present + [row for row in rows if value(row) is None]


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
    return [Column(
        spec=spec, label=str(spec.label),
        unit=str(spec.unit) % {"year": year},
        href=filters.link(spec.key, spec.key == filters.sort
                          and not filters.descending, selected=selected),
        aria_sort=("descending" if filters.descending else "ascending")
        if spec.key == filters.sort else "") for spec in COLUMN_MODEL]


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
            href=LIST + replace(filters, stock=level).link(
                filters.sort, filters.descending, selected=selected),
            current=filters.stock == level)

    return [entry("", _("All stock statuses"), "", counts.total()),
            *(entry(level, capfirst(str(level.label)), str(MEANINGS[level]),
                    counts[level]) for level in Level)]


def row_of(item: Item, today: date, vessels: list[Vessel]) -> Row:
    """The row of ITEM as of TODAY, with its bulk among VESSELS, the
    open vessels, and without heats."""
    figures = consumption(item, today)
    return Row(item=item, figures=figures, bulk=bulk(item, vessels),
               statistics=statistics(figures, today))


def chosen_row(rows: list[Row], selected: str) -> Row | None:
    """The row of ROWS whose item's id is the number SELECTED, else the
    first row, else None for no rows. A SELECTED that is not a whole
    number, or names no item of ROWS, chooses the first row."""
    for row in rows:
        if str(row.item.pk) == selected:
            return row
    return rows[0] if rows else None


@vary_on_cookie
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
    items = sorted(Item.objects.select_related("article__substance"),
                   key=Item.sort_key)
    vessels = open_vessels()
    rows = heated([row_of(item, today, vessels) for item in items])
    shown = filters.ordered([row for row in rows if filters.admits(row)])
    if filters.sort == "category":
        shown = by_category(shown)
    containers = {container_code(item): item.container for item in
                  sorted(items, key=Item.container_order)}
    chosen = chosen_row(shown, request.GET.get("selected", ""))
    selected = str(chosen.item.pk) if chosen else ""
    menu = stock_menu(rows, filters, selected)
    shown_columns = columns(filters, today.year, selected)
    return render(request, "inventory/item_list.html", {
        "rows": shown,
        "chosen": chosen,
        "selected": selected,
        "view": ("details" if request.COOKIES.get(VIEW_COOKIE) == "details"
                 else "table"),
        "total": len(rows),
        "filters": filters,
        "columns": shown_columns,
        "table_columns": [column for column in shown_columns
                          if column.table_only],
        "order": order_text(filters),
        "reset": filters.link(filters.sort, filters.descending,
                              filtered=False, selected=selected),
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
        "layers": layers(LIST),
    })


@vary_on_headers("HX-Request")
def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the item PK alone, as the item list shows them beside its table,
    and any other request with a redirect to the list with ``selected``
    naming the item. Answer 404 for an unknown ID. The answer varies
    with the ``HX-Request`` header."""
    item = get_object_or_404(Item.objects.select_related(
        "article__substance"), pk=pk)
    if request.headers.get("HX-Request") != "true":
        return redirect(f"{LIST}?{urlencode({'selected': item.pk})}")
    today = timezone.localdate()
    return render(request, "inventory/item_list.html#detail", {
        "chosen": row_of(item, today, open_vessels(item)),
        "today": today,
    })


def batch_list(request: HttpRequest) -> HttpResponse:
    """List the batches of every substance, newest date first and
    undated ones last, then newest recorded first, each with the amount
    in its open vessels; ``q`` selects those in whose number, supplier's
    batch number or supplier, or in whose substance's key or names, the
    text is found regardless of case."""
    q = request.GET.get("q", "").strip()
    words = q.casefold()
    found = []
    for batch in Batch.objects.select_related(
            "substance__article", "task_step__task",
            "journal_entry__notebook"):
        substance = batch.substance
        text = "\n".join([batch.number, batch.supplier_batch,
                          batch.supplier, substance.key, substance.name,
                          substance.name_de]).casefold()
        if not words or words in text:
            found.append(batch)
    found = newest_first(found)
    stock = open_amounts(found)
    return render(request, "inventory/batch_list.html", {
        "rows": [(batch, stock[batch.pk]) for batch in found],
        "q": q,
        "tabs": tabs(BATCHES),
    })


def vessel_list(request: HttpRequest) -> HttpResponse:
    """List the open vessels of every substance, and the used-up ones
    too with ``empty=1``, by the substance's name regardless of case,
    then by their batch's date, oldest first and vessels without one
    last, then by ID. ``kind`` names one of ``VesselKind`` and lists the
    vessels of that kind; another value lists every kind."""
    empty = request.GET.get("empty") == "1"
    kind = request.GET.get("kind", "")
    if kind not in VesselKind.values:
        kind = ""
    vessels = Vessel.objects.select_related("batch__substance__article",
                                            "batch__task_step__task")
    if not empty:
        vessels = vessels.filter(amount__gt=0)
    found = sorted((vessel for vessel in vessels
                    if not kind or vessel.kind == kind),
                   key=lambda vessel: (
                       vessel.batch.substance.shown_name.casefold(),
                       vessel.batch.date is None,
                       vessel.batch.date or date.min, vessel.pk))
    return render(request, "inventory/vessel_list.html", {
        "vessels": found,
        "empty": empty,
        "kind": kind,
        "kinds": VesselKind.choices,
        "tabs": tabs(VESSELS),
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


@vary_on_cookie
def note_list(request: HttpRequest) -> HttpResponse:
    """List the delivery notes, newest date first, then newest booking
    first; ``q`` selects those whose number or recipient holds the text
    regardless of case, and ``item`` those with a line of the item of
    that ID. The note ``selected`` names among those listed, else the
    first, is selected, in the view the cookie ``delivery-list-view``
    remembers."""
    q = request.GET.get("q", "").strip()
    chosen = request.GET.get("item", "").strip()
    notes = DeliveryNote.objects.annotate(line_count=Count("lines")) \
        .prefetch_related("lines__item", "lines__batch").order_by(
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
    wanted = request.GET.get("selected", "")
    selected = next((note for note in shown if str(note.pk) == wanted),
                    shown[0] if shown else None)
    return render(request, "inventory/note_list.html", {
        "notes": [(note, states[note.pk]) for note in shown],
        "selected_note": selected,
        "selected": str(selected.pk) if selected else "",
        **(note_context(selected) if selected else {}),
        "view": list_view(request, NOTE_COOKIE),
        "layers": layers(DELIVERIES),
        "q": q,
        "chosen": chosen,
        "items": sorted(Item.objects.filter(
            article__article_number__isnull=False).select_related(
                "article__substance"), key=Item.sort_key),
        "tabs": tabs(LIST),
    })


@dataclass(frozen=True)
class Fills:
    """The containers of ITEM a vessel would fill: COUNT, or None when
    the vessel does not convert into the item's unit."""

    item: Item
    count: int | None


@dataclass(frozen=True)
class BulkRow:
    """A vessel of the bulk list with the containers it would fill of
    each item of its substance's article, by size."""

    vessel: Vessel
    fills: list[Fills]

    def searched(self) -> str:
        """The text the list's search looks in, folded for a comparison
        regardless of case: the article number, the substance's key and
        names, and the batch's number and supplier's batch."""
        batch = self.vessel.batch
        substance = batch.substance
        return "\n".join([substance.article.article_number or "",
                          substance.key, substance.name,
                          substance.name_de, batch.number,
                          batch.supplier_batch]).casefold()


def bulk_rows(vessels: list[Vessel]) -> list[BulkRow]:
    """Return VESSELS as rows of the bulk list, with the containers each
    would fill of every item of its substance's article, by size."""
    items: dict[int, list[Item]] = {}
    for item in sorted(Item.objects.filter(
            article_id__in={vessel.batch.substance_id
                            for vessel in vessels}
            ).select_related("article__substance"),
            key=Item.container_order):
        items.setdefault(item.article_id, []).append(item)
    return [BulkRow(vessel=vessel, fills=[
        Fills(item=item, count=containers_from(vessel, item,
                                               molar_mass(item)))
        for item in items.get(vessel.batch.substance_id, [])])
        for vessel in vessels]


def bulk_order(vessel: Vessel) -> tuple[Any, ...]:
    """The bulk list's order: by article number, articles without one
    last and by name regardless of case, then by the batch's date,
    oldest first and undated ones last, then by ID."""
    substance = vessel.batch.substance
    number = substance.article.article_number
    return (number is None, number or "",
            substance.shown_name.casefold(), vessel.batch.date is None,
            vessel.batch.date or date.min, vessel.pk)


def list_view(request: HttpRequest, cookie: str) -> str:
    """Return the view of a list with two views that the cookie COOKIE
    remembers, ``details`` or else ``table``."""
    return "details" if request.COOKIES.get(cookie) == "details" \
        else "table"


@vary_on_cookie
def bulk_list(request: HttpRequest) -> HttpResponse:
    """List the open vessels of the substances that have an article, in
    the bulk list's order, with the containers each would fill; ``q``,
    ``location``, ``source`` and ``flask=1`` select among them. The
    vessel ``selected`` names among those listed, else the first, is
    selected, in the view the cookie ``bulk-list-view`` remembers."""
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    source = request.GET.get("source", "")
    if source not in Source.values:
        source = ""
    flask = request.GET.get("flask") == "1"
    vessels = list(bulk_vessels())
    locations = sorted({vessel.location for vessel in vessels
                        if vessel.location}, key=natural)
    words = q.casefold()
    rows = [row for row in bulk_rows(sorted(vessels, key=bulk_order))
            if (not words or words in row.searched())
            and (not location or row.vessel.location == location)
            and (not source or row.vessel.batch.source == source)
            and (not flask or row.vessel.flask)]
    wanted = request.GET.get("selected", "")
    chosen = next((row for row in rows if str(row.vessel.pk) == wanted),
                  rows[0] if rows else None)
    return render(request, "inventory/bulk_list.html", {
        "rows": rows,
        "chosen": chosen,
        "ledger": vessel_ledger(chosen.vessel, 5) if chosen else [],
        "selected": str(chosen.vessel.pk) if chosen else "",
        "view": list_view(request, BULK_COOKIE),
        "q": q,
        "location": location,
        "source": source,
        "sources": Source.choices,
        "flask": flask,
        "locations": locations,
        "tabs": tabs(LIST),
        "layers": layers(BULK),
    })


@vary_on_headers("HX-Request")
def bulk_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the vessel PK alone, as the bulk list shows them beside its table,
    and any other request with a redirect to the list with ``selected``
    naming the vessel. Answer 404 for a vessel the bulk list does not
    hold."""
    vessel = get_object_or_404(bulk_vessels(), pk=pk)
    if request.headers.get("HX-Request") != "true":
        return redirect(f"{BULK}?{urlencode({'selected': vessel.pk})}")
    return render(request, "inventory/bulk_list.html#detail", {
        "chosen": bulk_rows([vessel])[0],
        "ledger": vessel_ledger(vessel, 5),
    })


def filed_under(model: type[Term], key: str) -> set[Any]:
    """Return the IDs of the term of MODEL whose key is KEY and of all
    terms filed below it; empty when no term has KEY."""
    term = model.objects.filter(key=key).first()
    return set() if term is None else {
        term.pk, *(below.pk for below in descendants(term))}


def category_vessels(category: str) -> Any:
    """Return the open vessels of the stock category CATEGORY
    (``StockCategory.INTERMEDIATES`` or ``StockCategory.COMMERCIAL``)
    with the related records their list and details need."""
    source = (Source.MADE if category == StockCategory.INTERMEDIATES
              else Source.BOUGHT)
    vessels = Vessel.objects.filter(
        amount__gt=0,
        batch__substance__article__isnull=True,
        batch__source=source,
    )
    if category == StockCategory.INTERMEDIATES:
        return vessels.select_related(
            "batch__substance__group",
            "batch__task_step__task",
            "batch__task_step__entry__procedure",
            "batch__journal_entry__notebook",
        ).prefetch_related("batch__substance__chemical_classes")
    return vessels.select_related("batch__substance__group")


def vessel_detail_order(vessel: Vessel) -> tuple[Any, ...]:
    """Order vessels in the details table: by batch date oldest first,
    undated vessels last, then by ID."""
    return (vessel.batch.date is None, vessel.batch.date or date.min,
            vessel.pk)


@dataclass(frozen=True)
class CategoryFilters:
    """The GET filter parameters of an intermediate or commercial
    chemical list."""

    q: str = ""
    location: str = ""
    chemical_class: str = ""
    flask: bool = False
    old: bool = False
    group: str = ""
    supplier: str = ""
    sealed: bool = False

    @classmethod
    def from_query(cls, query: Any, category: str) -> "CategoryFilters":
        """Read the parameters applicable to CATEGORY from QUERY."""
        q = query.get("q", "").strip()
        location = query.get("location", "").strip()
        if category == StockCategory.INTERMEDIATES:
            return cls(
                q=q,
                location=location,
                chemical_class=query.get("class", "").strip(),
                flask=query.get("flask") == "1",
                old=query.get("old") == "1",
            )
        return cls(
            q=q,
            location=location,
            group=query.get("group", "").strip(),
            supplier=query.get("supplier", "").strip(),
            sealed=query.get("sealed") == "1",
        )

    def query_string(self, category: str) -> str:
        """Return the active filter parameters encoded with a leading
        ``?``, or empty when no filter is set."""
        pairs: list[tuple[str, str]] = []
        if self.q:
            pairs.append(("q", self.q))
        if self.location:
            pairs.append(("location", self.location))
        if category == StockCategory.INTERMEDIATES:
            if self.chemical_class:
                pairs.append(("class", self.chemical_class))
            if self.flask:
                pairs.append(("flask", "1"))
            if self.old:
                pairs.append(("old", "1"))
        else:
            if self.group:
                pairs.append(("group", self.group))
            if self.supplier:
                pairs.append(("supplier", self.supplier))
            if self.sealed:
                pairs.append(("sealed", "1"))
        return "?" + urlencode(pairs) if pairs else ""


def vessel_searched(vessel: Vessel, include_task: bool) -> str:
    """Return the casefolded text searched by ``q`` for VESSEL."""
    batch = vessel.batch
    substance = batch.substance
    parts = [
        substance.key, substance.name, substance.name_de,
        substance.short_name, substance.cas,
        batch.number, batch.supplier_batch, batch.supplier,
    ]
    if include_task and batch.task_step_id is not None:
        parts.append(batch.task_step.task.number)
    return "\n".join(parts).casefold()


def filter_category_vessels(vessels: list[Vessel], filters: CategoryFilters,
                            category: str, today: date) -> list[Vessel]:
    """Return the vessels of VESSELS admitted by FILTERS for CATEGORY as
    of TODAY."""
    is_int = category == StockCategory.INTERMEDIATES
    words = filters.q.casefold()
    admitted_classes = (filed_under(ChemicalClass, filters.chemical_class)
                        if is_int and filters.chemical_class else None)
    admitted_groups = (filed_under(Group, filters.group)
                       if not is_int and filters.group else None)
    result: list[Vessel] = []
    for vessel in vessels:
        batch = vessel.batch
        substance = batch.substance
        if words and words not in vessel_searched(vessel, is_int):
            continue
        if filters.location and (vessel.flask
                                 or vessel.location != filters.location):
            continue
        if is_int:
            if admitted_classes is not None and not any(
                    term.pk in admitted_classes
                    for term in substance.chemical_classes.all()):
                continue
            if filters.flask and not vessel.flask:
                continue
            if filters.old and (batch.date is None
                                or not is_old(batch.date, today)):
                continue
        else:
            if admitted_groups is not None \
                    and substance.group_id not in admitted_groups:
                continue
            if filters.supplier and batch.supplier != filters.supplier:
                continue
            if filters.sealed and vessel.opened_on is not None:
                continue
        result.append(vessel)
    return result


@dataclass(frozen=True)
class CategoryRow:
    """A substance row in the intermediate or commercial chemical list,
    summarising its admitted vessels of that category."""

    substance: Any
    vessels: list[Vessel]
    amounts: list[tuple[Any, str]]
    vessel_count: int
    flask_count: int
    sealed_count: int
    locations: LocationSummary
    sources: SourceSummary | None
    age: AgeSummary | None
    suppliers: SupplierSummary | None
    opened_on: date | None
    classes: list[str]
    in_other_category: bool


def category_row(substance: Any, vessels: list[Vessel], category: str,
                 today: date, in_other: bool) -> CategoryRow:
    """Build the ``CategoryRow`` of SUBSTANCE from its admitted VESSELS
    in CATEGORY as of TODAY."""
    ordered = sorted(vessels, key=vessel_detail_order)
    is_int = category == StockCategory.INTERMEDIATES
    return CategoryRow(
        substance=substance,
        vessels=ordered,
        amounts=amounts_by_unit(ordered),
        vessel_count=len(ordered),
        flask_count=sum(1 for vessel in ordered if vessel.flask),
        sealed_count=sum(1 for vessel in ordered if vessel.opened_on is None),
        locations=location_summary(ordered, show_flask=is_int),
        sources=source_summary(ordered) if is_int else None,
        age=age_summary(ordered, today) if is_int else None,
        suppliers=None if is_int else supplier_summary(ordered),
        opened_on=None if is_int else earliest_opened(ordered),
        classes=sorted(
            (term.shown_label for term in substance.chemical_classes.all()),
            key=str.casefold) if is_int else [],
        in_other_category=in_other,
    )


def category_rows(vessels: list[Vessel], category: str, today: date,
                  other_substances: set[int]) -> list[CategoryRow]:
    """Group VESSELS by substance and return their ``CategoryRow``s
    ordered by substance name regardless of case."""
    grouped: dict[int, tuple[Any, list[Vessel]]] = {}
    for vessel in vessels:
        substance = vessel.batch.substance
        entry = grouped.setdefault(substance.pk, (substance, []))
        entry[1].append(vessel)
    rows = [
        category_row(substance, group, category, today,
                     substance.pk in other_substances)
        for substance, group in grouped.values()
    ]
    rows.sort(key=lambda row: (row.substance.shown_name.casefold(),
                               row.substance.key))
    return rows


def category_list_response(request: HttpRequest, category: str
                           ) -> HttpResponse:
    """Render the intermediate or commercial chemical list for CATEGORY."""
    is_int = category == StockCategory.INTERMEDIATES
    base_url = INTERMEDIATES if is_int else CHEMICALS
    cookie = INTERMEDIATE_COOKIE if is_int else CHEMICAL_COOKIE
    today = timezone.localdate()
    filters = CategoryFilters.from_query(request.GET, category)
    all_vessels = list(category_vessels(category))
    admitted = filter_category_vessels(all_vessels, filters, category, today)
    other_source = Source.BOUGHT if is_int else Source.MADE
    other_substances = set(Vessel.objects.filter(
        amount__gt=0,
        batch__substance__article__isnull=True,
        batch__source=other_source,
    ).values_list("batch__substance_id", flat=True))
    rows = category_rows(admitted, category, today, other_substances)

    offered_locations = {vessel.location for vessel in all_vessels
                         if not vessel.flask and vessel.location}
    if filters.location:
        offered_locations.add(filters.location)
    offered_suppliers: list[str] = []
    if not is_int:
        suppliers_set = {vessel.batch.supplier for vessel in all_vessels
                         if vessel.batch.supplier}
        if filters.supplier:
            suppliers_set.add(filters.supplier)
        offered_suppliers = sorted(suppliers_set, key=str.casefold)

    wanted = request.GET.get("selected", "")
    chosen = next((row for row in rows if row.substance.key == wanted),
                  rows[0] if rows else None)
    selected = chosen.substance.key if chosen else ""
    detail_vessels = chosen.vessels if chosen else []
    single_vessel = detail_vessels[0] if len(detail_vessels) == 1 else None
    classes = (tree_order(ChemicalClass.objects.select_related("parent"))
               if is_int else [])
    groups = ([] if is_int
              else tree_order(Group.objects.select_related("parent")))
    return render(request, "inventory/category_list.html", {
        "category": category,
        "is_intermediate": is_int,
        "base_url": base_url,
        "cookie": cookie,
        "heading": _("Intermediates") if is_int else _("Commercial chemicals"),
        "rows": rows,
        "vessel_total": sum(row.vessel_count for row in rows),
        "chosen": chosen,
        "detail_substance": chosen.substance if chosen else None,
        "detail_vessels": detail_vessels,
        "single_vessel": single_vessel,
        "ledger": vessel_ledger(single_vessel, 5) if single_vessel else [],
        "selected": selected,
        "view": list_view(request, cookie),
        "filters": filters,
        "filter_query": filters.query_string(category),
        "locations": sorted(offered_locations, key=natural),
        "suppliers": offered_suppliers,
        "classes": classes,
        "groups": groups,
        "stale_class": stale_key(filters.chemical_class, classes),
        "stale_group": stale_key(filters.group, groups),
        "tabs": tabs(base_url),
    })


def stale_key(key: str, terms: list[tuple[Any, int]]) -> str:
    """Return KEY, a vocabulary filter's value, when it names none of
    TERMS, so that the filter can still offer it as the value in force;
    else the empty string."""
    return key if key and all(term.key != key for term, _ in terms) \
        else ""


def category_detail_response(request: HttpRequest, category: str, key: str
                             ) -> HttpResponse:
    """Answer an htmx request with the details pane of substance KEY in
    CATEGORY under the request's filters, or redirect non-htmx requests
    to the list. Answer 404 when KEY has no open vessel of CATEGORY."""
    is_int = category == StockCategory.INTERMEDIATES
    base_url = INTERMEDIATES if is_int else CHEMICALS
    all_for_sub = list(category_vessels(category).filter(
        batch__substance__key=key))
    if not all_for_sub:
        raise Http404
    if request.headers.get("HX-Request") != "true":
        params = request.GET.copy()
        params["selected"] = key
        return redirect(f"{base_url}?{params.urlencode()}")
    today = timezone.localdate()
    filters = CategoryFilters.from_query(request.GET, category)
    admitted = sorted(
        filter_category_vessels(all_for_sub, filters, category, today),
        key=vessel_detail_order)
    substance = all_for_sub[0].batch.substance
    single_vessel = admitted[0] if len(admitted) == 1 else None
    return render(request, "inventory/category_list.html#detail", {
        "category": category,
        "is_intermediate": is_int,
        "detail_substance": substance,
        "detail_vessels": admitted,
        "single_vessel": single_vessel,
        "ledger": vessel_ledger(single_vessel, 5) if single_vessel else [],
    })


@vary_on_cookie
def intermediate_list(request: HttpRequest) -> HttpResponse:
    """List the substances with an open intermediate vessel, one row per
    substance, with filters, summaries and the details view."""
    return category_list_response(request, StockCategory.INTERMEDIATES)


@vary_on_headers("HX-Request")
def intermediate_detail(request: HttpRequest, key: str) -> HttpResponse:
    """Answer an htmx request with the details pane of the intermediate
    substance KEY under the query's filters, or redirect to the list."""
    return category_detail_response(request, StockCategory.INTERMEDIATES, key)


@vary_on_cookie
def chemical_list(request: HttpRequest) -> HttpResponse:
    """List the substances with an open commercial chemical vessel, one
    row per substance, with filters, summaries and the details view."""
    return category_list_response(request, StockCategory.COMMERCIAL)


@vary_on_headers("HX-Request")
def chemical_detail(request: HttpRequest, key: str) -> HttpResponse:
    """Answer an htmx request with the details pane of the commercial
    chemical KEY under the query's filters, or redirect to the list."""
    return category_detail_response(request, StockCategory.COMMERCIAL, key)


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


def consumption_section(item: Item, today: date, links: bool
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
    item = get_object_or_404(Item.objects.select_related(
        "article__substance"), pk=pk)
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
    vessels = open_vessels(item)
    held = [stock for stock in item.stocks.select_related("batch")
            if stock.quantity]
    return render(request, "inventory/item_page.html", {
        "item": item,
        "today": today,
        "stocks": [stock for stock in held if stock.batch_id is not None],
        "unknown": sum(stock.quantity for stock in held
                       if stock.batch_id is None),
        **consumption_section(item, today, request.user.is_authenticated),
        "ledger": ledger,
        "vessels": [(vessel, containers_from(vessel, item, mass))
                    for vessel in vessels],
        "bulk": bulk(item, vessels),
        "forecast": found,
        "entry": found.entry(item) if found else None,
        "history": history_entries(item),
    })


@dataclass(frozen=True)
class VesselLedgerRow:
    """A movement of a vessel as its page shows it: the ITEM a filling
    filled, or None; the OTHER vessel of a transfer, or None; and
    whether a withdrawal may still be REVERSIBLE."""

    movement: VesselMovement
    item: Item | None
    other: Vessel | None
    reversible: bool


def vessel_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the vessel PK with its batch, its movements and its history;
    answer 404 for an unknown ID."""
    vessel = get_object_or_404(Vessel.objects.select_related(
        "batch__substance__article"), pk=pk)
    return render(request, "inventory/vessel_page.html", {
        "vessel": vessel,
        "ledger": vessel_ledger(vessel),
        "history": history_entries(vessel),
    })


def vessel_ledger(vessel: Vessel, limit: int | None = None
                  ) -> list["VesselLedgerRow"]:
    """Return the movements of VESSEL, newest first, the LIMIT newest
    alone when it is given, each with the item it filled, the other
    vessel of a transfer and whether it can be reversed."""
    movements = vessel.movements.select_related(
        "user", "item_movement__item__article", "task_step__task",
        "task_step__entry__procedure", "reverses", "reversal",
        "transfer__vessel", "transferred__vessel").order_by("-id")
    if limit is not None:
        movements = movements[:limit]
    rows = []
    for movement in movements:
        other = None
        if movement.kind == VesselMovement.Kind.TRANSFER_IN:
            other = movement.transfer.vessel
        elif movement.kind == VesselMovement.Kind.TRANSFER_OUT \
                and hasattr(movement, "transferred"):
            other = movement.transferred.vessel
        rows.append(VesselLedgerRow(
            movement=movement,
            item=movement.item_movement.item
            if hasattr(movement, "item_movement") else None,
            other=other,
            reversible=movement.kind == VesselMovement.Kind.WITHDRAWAL
            and not hasattr(movement, "reversal")))
    return rows


@dataclass(frozen=True)
class FillingRow:
    """A filling from a vessel of a batch as the batch's page shows it:
    the MOVEMENT of the vessel, the ITEM filled, and whether the
    filling is REVERSED."""

    movement: VesselMovement
    item: Item
    reversed: bool


@dataclass(frozen=True)
class LineRow:
    """A delivery line as the page of its batch shows it: the LINE, and
    whether it is of a HISTORICAL note and whether its delivery or its
    historical note is REVERSED."""

    line: DeliveryLine
    historical: bool
    reversed: bool


def batch_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the batch PK with its vessels, the fillings from them, the
    items holding containers of it, the delivery lines that name it and
    its history; answer 404 for an unknown ID.

    The lines are those of current and of historical notes, newest note
    first.
    """
    batch = get_object_or_404(Batch.objects.select_related(
        "substance__article", "journal_entry__notebook",
        "task_step__task", "task_step__entry__procedure"), pk=pk)
    vessels = sorted(batch.vessels.select_related(
        "batch__substance__article"), key=lambda vessel: (
            not vessel.amount > 0, vessel.pk))
    fillings = VesselMovement.objects.filter(
        vessel__batch=batch, kind=VesselMovement.Kind.FILLING
        ).select_related("vessel", "item_movement__item__article",
                         "item_movement__reversal").order_by("-id")
    undone = set(Movement.objects.filter(
        kind=Movement.Kind.DELIVERY, batch=batch, reversal__isnull=False
        ).values_list("delivery_note_id", "item_id"))
    lines = batch.delivery_lines.select_related(
        "delivery_note", "item__article__substance").order_by(
            "-delivery_note__date", "-delivery_note__created_at",
            "-delivery_note_id", "-id")
    return render(request, "inventory/batch_page.html", {
        "batch": batch,
        "vessels": vessels,
        "fillings": [FillingRow(
            movement=movement, item=movement.item_movement.item,
            reversed=hasattr(movement.item_movement, "reversal"))
            for movement in fillings if hasattr(movement, "item_movement")],
        "stocks": batch.stocks.filter(quantity__gt=0).select_related(
            "item__article__substance"),
        "lines": [LineRow(
            line=line, historical=line.delivery_note.historical,
            reversed=line.delivery_note.reversed
            if line.delivery_note.historical
            else (line.delivery_note_id, line.item_id) in undone)
            for line in lines],
        "history": history_entries(batch),
    })


def note_context(note: DeliveryNote) -> dict[str, Any]:
    """Return the context NOTE is shown with, on its page and in the
    delivery list's details: the note, its state and its lines, each
    with its delivery movement, found by item and batch, and whether
    that is reversed; the assignments the note booked are left out."""
    movements = {(movement.item_id, movement.batch_id): movement
                 for movement in note.movements.filter(
                     kind=Movement.Kind.DELIVERY).select_related(
                         "user", "reversal")}
    shown = [(line, movements.get((line.item_id, line.batch_id)))
             for line in note.lines.select_related(
                 "item__article__substance", "batch")]
    return {"note": note, "state": note_states([note])[note.pk],
            "lines": [(line, movement, hasattr(movement, "reversal"))
                      for line, movement in shown]}


def note_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the delivery note PK with its lines, their movements and the
    history; answer 404 for an unknown ID."""
    note = get_object_or_404(
        DeliveryNote.objects.annotate(line_count=Count("lines")), pk=pk)
    return render(request, "inventory/note_page.html", {
        **note_context(note), "history": history_entries(note)})


@vary_on_headers("HX-Request")
def note_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the delivery note PK alone, as the delivery list shows them beside
    its table, and any other request with a redirect to the list with
    ``selected`` naming the note. Answer 404 for an unknown ID."""
    note = get_object_or_404(
        DeliveryNote.objects.annotate(line_count=Count("lines")), pk=pk)
    if request.headers.get("HX-Request") != "true":
        return redirect(f"{DELIVERIES}?{urlencode({'selected': note.pk})}")
    return render(request, "inventory/note_list.html#detail",
                  note_context(note))


def for_dialog(request: HttpRequest) -> bool:
    """Tell whether REQUEST asks for a form to show in the lab's dialog.

    That is an htmx request that is not htmx's reload of a page from its
    history, which needs the complete page.
    """
    return (request.headers.get("HX-Request") == "true"
            and request.headers.get("HX-History-Restore-Request") != "true")


def sign_in_next(request: HttpRequest) -> str:
    """Return the address to which signing in leads back after REQUEST.

    That is the path and query of the page that made the htmx request
    REQUEST, named by its ``HX-Current-URL`` header, when the page is on
    the host of REQUEST; otherwise the path of REQUEST.
    """
    current = request.headers.get("HX-Current-URL", "")
    if current and url_has_allowed_host_and_scheme(
            current, {request.get_host()}, request.is_secure()):
        parts = urlsplit(current)
        return (parts.path or "/") + (f"?{parts.query}" if parts.query
                                      else "")
    return request.path


def item_form(view: Callable[..., HttpResponse]
              ) -> Callable[..., HttpResponse]:
    """Decorate the item form VIEW to need a signed-in user and to answer
    a request for a dialog (see ``for_dialog``).

    A request without a signed-in user is redirected to the sign-in page
    with ``next`` the path of the request. Where the request is for a
    dialog, the answer is instead ``204 No Content`` with ``HX-Redirect``
    to the sign-in page, whose ``next`` is the address of the page that
    made the request (see ``sign_in_next``), which htmx makes the page
    follow. Every answer varies with the headers ``HX-Request`` and
    ``HX-History-Restore-Request``.
    """
    signed_in = login_required(view)

    @wraps(view)
    @vary_on_headers("HX-Request", "HX-History-Restore-Request")
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any
                ) -> HttpResponse:
        if for_dialog(request) and not request.user.is_authenticated:
            return HttpResponse(status=204, headers={
                "HX-Redirect": redirect_to_login(sign_in_next(request)).url})
        return signed_in(request, *args, **kwargs)

    return wrapper


def render_form(request: HttpRequest, form: BaseForm,
                context: dict[str, Any], dialog: bool = False,
                template: str = "inventory/form.html") -> HttpResponse:
    """Render TEMPLATE with FORM and CONTEXT.

    When DIALOG is true and REQUEST is for a dialog (see ``for_dialog``),
    only the form's partial is rendered, to post from the dialog;
    otherwise the complete page is.
    """
    if dialog and for_dialog(request):
        return render(request, f"{template}#form",
                      {"form": form, "dialog": True, **context})
    return render(request, template, {"form": form, **context})


def form_page(request: HttpRequest, form: BaseForm,
              book: Callable[[dict[str, Any]], HttpResponse],
              context: dict[str, Any],
              template: str = "inventory/form.html",
              dialog: bool = False) -> HttpResponse:
    """Show FORM, or pass the cleaned data of the posted FORM to BOOK and
    return its response.

    A form with errors, and one whose booking is refused, shows again
    with the errors at their fields. CONTEXT goes to TEMPLATE beside the
    form. A true DIALOG lets a request for a dialog show the form alone
    (see ``render_form``).
    """
    if request.method == "POST" and form.is_valid():
        try:
            return book(form.cleaned_data)
        except Refused as refused:
            show_refusal(form, refused, form.cleaned_data.get("rows"))
    return render_form(request, form, context, dialog, template)


def saved(request: HttpRequest, text: str, target: str,
          record: Any = None) -> HttpResponse:
    """Leave the message TEXT and redirect to TARGET.

    When RECORD is given and REQUEST is for a dialog (see ``for_dialog``),
    the answer is instead ``204 No Content`` with an ``HX-Trigger``
    header that fires the event ``lab-saved`` naming RECORD's ID.
    """
    messages.success(request, text)
    if record is not None and for_dialog(request):
        key = "vessel" if isinstance(record, Vessel) else "item"
        return HttpResponse(status=204, headers={
            "HX-Trigger": json.dumps({"lab-saved": {key: record.pk}})})
    return redirect(target)


def item_url(item: Item, action: str = "") -> str:
    """Return the path of ITEM's page, or of its form ACTION."""
    return f"/lab/inventory/items/{item.pk}/" + (f"{action}/" if action
                                                 else "")


def consumption_url(item: Item, year: int, quarter: int) -> str:
    """Return the path of ITEM's consumption form for the QUARTER of
    YEAR."""
    query = urlencode({"year": year, "quarter": quarter})
    return f"{item_url(item, 'consumption')}?{query}"


def batch_url(batch: Batch, action: str = "") -> str:
    """Return the path of BATCH's page, or of its form ACTION."""
    return f"/lab/inventory/batches/{batch.pk}/" + (
        f"{action}/" if action else "")


def vessel_url(vessel: Vessel, action: str = "") -> str:
    """Return the path of VESSEL's page, or of its form ACTION."""
    return f"/lab/inventory/vessels/{vessel.pk}/" + (
        f"{action}/" if action else "")


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
                     item_url(stored), stored)

    form = ItemEditForm(request.POST or None, instance=item)
    return form_page(
        request, form, book,
        {"title": title, "cancel": item_url(item),
         "categories": categories(), "compartments": in_use("compartment"),
         "boxes": in_use("box")}, dialog=True)


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
    """The locations of the vessels, for the location's ``datalist``."""
    return Vessel.objects.exclude(location="").order_by("location") \
        .values_list("location", flat=True).distinct()


def chosen_step(request: HttpRequest) -> TaskStep | None:
    """Return the task step whose ID the query's ``step`` names, or, when
    the query has none, the posted ``step``; None when neither names one.
    Answer 404 for an unknown or malformed ID."""
    value = request.GET.get("step", "") or request.POST.get("step", "")
    if not value:
        return None
    if not value.isdigit():
        raise Http404
    return get_object_or_404(TaskStep.objects.select_related(
        "task__substance", "entry__procedure", "journal_entry__notebook"),
        pk=int(value))


def step_initial(step: TaskStep) -> dict[str, Any]:
    """Return the values the new-batch form takes from STEP: the first
    substance the step makes, made in the lab, today."""
    products = step.products()
    return {"substance": products[0].key if products else "",
            "source": Source.MADE, "date": timezone.localdate()}


@login_required
def batch_new(request: HttpRequest) -> HttpResponse:
    """Record a batch, booked by the signed-in user; ``substance`` in the
    query fills in the substance's key.

    ``step`` in the query, or posted, makes the batch one made by that
    task step and fills in the form from it (``step_initial``); the
    amount is then its yield. An unknown step answers 404.
    """
    step = chosen_step(request)

    def book(data: dict[str, Any]) -> HttpResponse:
        amount = data["amount"]
        with transaction.atomic():
            if step is not None:
                Task.objects.select_for_update().get(pk=step.task_id)
            text = data["journal_entry"]
            batch = bookings.record_batch(
                request.user, substance=data["substance"],
                source=data["source"], number=data["number"],
                journal_entry=entry_for(text) if text else None,
                task_step=step, date=data["date"],
                supplier=data["supplier"],
                supplier_article_number=data["supplier_article_number"],
                supplier_batch=data["supplier_batch"], note=data["note"],
                amount=amount, unit=data["unit"] if amount is not None
                else "", location=data["location"])
        return saved(request, _("Batch %(batch)s recorded.")
                     % {"batch": batch}, batch_url(batch))

    if step is not None:
        initial = step_initial(step)
    else:
        initial = {"substance": request.GET.get("substance", "")}
        if request.GET.get("source") == Source.BOUGHT:
            initial["source"] = Source.BOUGHT
    title = _("New batch") if step is None else _(
        "New batch of %(task)s, %(step)s") % {
            "task": step.task.number, "step": step.label}
    return form_page(
        request, BatchForm(request.POST or None, initial=initial,
                           step=step), book,
        {"title": title, "cancel": BATCHES, "substances": True,
         "locations": locations()})


@login_required
def batch_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the batch PK: its number, journal entry and yield when
    made, its supplier's fields when bought, and its date and note;
    answer 404 for an unknown batch."""
    batch = get_object_or_404(Batch.objects.select_related(
        "journal_entry__notebook"), pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        try:
            with transaction.atomic():
                form.instance._history_user = request.user
                form.save()
        except IntegrityError as error:
            raise Refused({"number": _(
                "Another made batch has this number.")}) from error
        return saved(request, _("Batch %(batch)s saved.")
                     % {"batch": form.instance}, batch_url(batch))

    form = BatchEditForm(request.POST or None, instance=batch)
    return form_page(request, form, book,
                     {"title": _("Edit %(item)s") % {"item": batch},
                      "cancel": batch_url(batch)})


@login_required
def vessel_new(request: HttpRequest, pk: int) -> HttpResponse:
    """Open a stored vessel of the batch PK with its opening amount,
    booked by the signed-in user; answer 404 for an unknown batch."""
    batch = get_object_or_404(Batch, pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        vessel = bookings.open_vessel(request.user, batch, **data)
        return saved(request, _("Vessel %(vessel)s opened.")
                     % {"vessel": vessel}, batch_url(batch))

    return form_page(
        request, NewVesselForm(request.POST or None), book,
        {"title": _("New vessel of %(batch)s") % {"batch": batch},
         "cancel": batch_url(batch), "locations": locations()})


@item_form
def vessel_withdraw(request: HttpRequest, pk: int) -> HttpResponse:
    """Book a withdrawal from the vessel PK into a task step, chosen in
    the form or filled in from ``step`` in the query; answer 404 for an
    unknown vessel."""
    vessel = get_object_or_404(Vessel.objects.select_related("batch"),
                               pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.withdraw(request.user, vessel, task_step=data["step"],
                          amount=data["amount"], date=data["date"])
        return saved(request, _("Withdrawal from %(vessel)s booked.")
                     % {"vessel": vessel}, vessel_url(vessel), vessel)

    return form_page(
        request, WithdrawalForm(request.POST or None, initial={
            "step": request.GET.get("step", "")}), book,
        {"title": _("Withdraw from %(vessel)s") % {"vessel": vessel},
         "cancel": vessel_url(vessel), "unit": vessel.unit_label},
        dialog=True)


@login_required
@require_POST
def vessel_movement_reverse(request: HttpRequest, pk: int
                            ) -> HttpResponse:
    """Reverse the withdrawal PK and return to its vessel's page with a
    message; a refusal leaves an error message. Answer 404 for an
    unknown movement and 405 for a request other than POST."""
    movement = get_object_or_404(
        VesselMovement.objects.select_related("vessel__batch"), pk=pk)
    vessel = movement.vessel
    try:
        bookings.reverse_withdrawal(request.user, movement)
    except Refused as refused:
        messages.error(request, " ".join(refused.messages))
        return redirect(vessel_url(vessel))
    return saved(request, _("Withdrawal from %(vessel)s reversed.")
                 % {"vessel": vessel}, vessel_url(vessel))


@item_form
def vessel_transfer(request: HttpRequest, pk: int) -> HttpResponse:
    """Transfer an amount from the vessel PK into another stored vessel
    of its batch or into a new one; answer 404 for an unknown vessel."""
    vessel = get_object_or_404(Vessel.objects.select_related(
        "batch__substance"), pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.transfer(request.user, vessel, **data)
        return saved(request, _("Transfer from %(vessel)s booked.")
                     % {"vessel": vessel}, vessel_url(vessel), vessel)

    return form_page(
        request, TransferForm(request.POST or None, source=vessel), book,
        {"title": _("Transfer from %(vessel)s") % {"vessel": vessel},
         "cancel": vessel_url(vessel), "unit": vessel.unit_label,
         "locations": locations()}, dialog=True)


@item_form
def vessel_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Change the location and note of the vessel PK; answer 404 for an
    unknown vessel."""
    vessel = get_object_or_404(Vessel.objects.select_related("batch"),
                               pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        form.instance._history_user = request.user
        form.save()
        return saved(request, _("Vessel %(vessel)s saved.")
                     % {"vessel": vessel}, vessel_url(vessel), vessel)

    form = VesselEditForm(request.POST or None, instance=vessel)
    return form_page(request, form, book,
                     {"title": _("Edit %(item)s") % {"item": vessel},
                      "cancel": vessel_url(vessel),
                      "locations": locations()}, dialog=True)


@item_form
def vessel_correct(request: HttpRequest, pk: int) -> HttpResponse:
    """Set the amount of the vessel PK after weighing; answer 404 for an
    unknown vessel."""
    vessel = get_object_or_404(Vessel.objects.select_related("batch"),
                               pk=pk)

    def book(data: dict[str, Any]) -> HttpResponse:
        bookings.correct_vessel(request.user, vessel, **data)
        return saved(request, _("Amount of %(vessel)s corrected.")
                     % {"vessel": vessel}, vessel_url(vessel), vessel)

    return form_page(
        request, VesselCorrectionForm(request.POST or None, initial={
            "amount": vessel.shown_amount}), book,
        {"title": _("Correct the amount of %(vessel)s") % {
            "vessel": vessel},
         "cancel": vessel_url(vessel), "unit": vessel.unit_label},
        dialog=True)
