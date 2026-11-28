"""Intermediate and commercial chemical list and detail views."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.http import Http404, HttpRequest, HttpResponse, QueryDict
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory.models import Source, StockCategory, Vessel
from inventory.summaries import (AgeSummary, LocationSummary, SourceSummary,
                                 SupplierSummary, age_summary,
                                 amounts_by_unit, earliest_opened, is_old,
                                 location_summary, natural, source_summary,
                                 supplier_summary)
from inventory.views.common import (CHEMICAL_COOKIE, CHEMICAL_SPLIT_COOKIE,
                                    CHEMICALS, INTERMEDIATE_COOKIE,
                                    INTERMEDIATE_SPLIT_COOKIE, INTERMEDIATES,
                                    oldest_vessel_order, tabs)
from inventory.views.vessels import vessel_ledger
from orgsyndb_web.lists import (Order, SortColumn, detail_query,
                                htmx_detail_or_redirect,
                                htmx_list_push_url, list_view, pairs_sort_key,
                                pick_selected, sort_value, split_major)
from vocabulary.models import ChemicalClass, Group, Term, descendants, tree_order


@dataclass(frozen=True)
class CategoryConfig:
    """Static configuration differentiating the intermediates and
    commercial chemical lists."""

    category: str
    is_intermediate: bool
    source: str
    other_source: str
    base_url: str
    cookie: str
    split_cookie: str
    heading: Any


CONFIGS: dict[str, CategoryConfig] = {
    StockCategory.INTERMEDIATES: CategoryConfig(
        category=StockCategory.INTERMEDIATES,
        is_intermediate=True,
        source=Source.MADE,
        other_source=Source.BOUGHT,
        base_url=INTERMEDIATES,
        cookie=INTERMEDIATE_COOKIE,
        split_cookie=INTERMEDIATE_SPLIT_COOKIE,
        heading=gettext_lazy("Intermediates"),
    ),
    StockCategory.COMMERCIAL: CategoryConfig(
        category=StockCategory.COMMERCIAL,
        is_intermediate=False,
        source=Source.BOUGHT,
        other_source=Source.MADE,
        base_url=CHEMICALS,
        cookie=CHEMICAL_COOKIE,
        split_cookie=CHEMICAL_SPLIT_COOKIE,
        heading=gettext_lazy("Commercial chemicals"),
    ),
}


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
    config = CONFIGS[category]
    vessels = Vessel.objects.open().filter(
        batch__substance__article__isnull=True,
        batch__source=config.source,
    )
    if config.is_intermediate:
        return vessels.select_related(
            "batch__substance__group",
            "batch__task_step__task",
            "batch__task_step__entry__procedure",
            "batch__journal_entry__notebook",
        ).prefetch_related("batch__substance__chemical_classes")
    return vessels.select_related("batch__substance__group")


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
    def from_query(cls, query: QueryDict,
                   category: str) -> "CategoryFilters":
        """Read the parameters applicable to CATEGORY from QUERY."""
        q = query.get("q", "").strip()
        location = query.get("location", "").strip()
        if CONFIGS[category].is_intermediate:
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

    def filter_pairs(self, category: str) -> list[tuple[str, str]]:
        """Return the active filter parameters for CATEGORY."""
        pairs: list[tuple[str, str]] = []
        if self.q:
            pairs.append(("q", self.q))
        if self.location:
            pairs.append(("location", self.location))
        if CONFIGS[category].is_intermediate:
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
        return pairs

    def query_string(self, category: str, selected: str = "",
                     extra: list[tuple[str, str]] | None = None,
                     lot: str = "") -> str:
        """Return the active filter parameters, EXTRA pairs, SELECTED,
        and LOT when given, encoded with a leading ``?``, or empty when
        none are set."""
        pairs = self.filter_pairs(category)
        if extra:
            pairs.extend(extra)
        if selected:
            pairs.append(("selected", selected))
        if lot:
            pairs.append(("lot", lot))
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


def _admits_intermediate(vessel: Vessel, filters: CategoryFilters,
                         admitted_classes: set[Any] | None,
                         today: date) -> bool:
    batch = vessel.batch
    if admitted_classes is not None and not any(
            term.pk in admitted_classes
            for term in batch.substance.chemical_classes.all()):
        return False
    if filters.flask and not vessel.flask:
        return False
    if filters.old and (batch.date is None or not is_old(batch.date, today)):
        return False
    return True


def _admits_commercial(vessel: Vessel, filters: CategoryFilters,
                       admitted_groups: set[Any] | None) -> bool:
    batch = vessel.batch
    if admitted_groups is not None \
            and batch.substance.group_id not in admitted_groups:
        return False
    if filters.supplier and batch.supplier != filters.supplier:
        return False
    if filters.sealed and vessel.opened_on is not None:
        return False
    return True


def filter_category_vessels(vessels: list[Vessel], filters: CategoryFilters,
                            category: str, today: date) -> list[Vessel]:
    """Return the vessels of VESSELS admitted by FILTERS for CATEGORY as
    of TODAY."""
    is_int = CONFIGS[category].is_intermediate
    words = filters.q.casefold()
    admitted_terms = (
        filed_under(ChemicalClass, filters.chemical_class)
        if is_int and filters.chemical_class
        else filed_under(Group, filters.group)
        if not is_int and filters.group else None
    )
    result: list[Vessel] = []
    for vessel in vessels:
        if words and words not in vessel_searched(vessel, is_int):
            continue
        if filters.location and (vessel.flask
                                 or vessel.location != filters.location):
            continue
        admitted = (_admits_intermediate(vessel, filters, admitted_terms,
                                         today)
                    if is_int
                    else _admits_commercial(vessel, filters, admitted_terms))
        if admitted:
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
    ordered = sorted(vessels, key=oldest_vessel_order)
    is_int = CONFIGS[category].is_intermediate
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


def stale_key(key: str, terms: list[tuple[Any, int]]) -> str:
    """Return KEY, a vocabulary filter's value, when it names none of
    TERMS, so that the filter can still offer it as the value in force;
    else the empty string."""
    return key if key and all(term.key != key for term, _ in terms) \
        else ""


def _offered_options(all_vessels: list[Vessel], filters: CategoryFilters,
                     is_int: bool) -> tuple[list[str], list[str]]:
    locations = {vessel.location for vessel in all_vessels
                 if not vessel.flask and vessel.location}
    if filters.location:
        locations.add(filters.location)
    suppliers: list[str] = []
    if not is_int:
        found = {vessel.batch.supplier for vessel in all_vessels
                 if vessel.batch.supplier}
        if filters.supplier:
            found.add(filters.supplier)
        suppliers = sorted(found, key=str.casefold)
    return sorted(locations, key=natural), suppliers


def _oldest_age_days(row: CategoryRow, today: date) -> Any:
    dates = [vessel.batch.date for vessel in row.vessels
             if vessel.batch.date is not None]
    if not dates:
        return None
    return sort_value(max(0, (today - min(dates)).days))


def _location_sort(row: CategoryRow) -> Any:
    if row.locations.first:
        return sort_value(row.locations.first)
    if row.locations.in_flask:
        return sort_value(_("in flask"))
    return None


def _source_sort(row: CategoryRow) -> Any:
    if not row.sources:
        return None
    if row.sources.task_numbers:
        return sort_value(row.sources.task_numbers[0])
    if row.sources.no_task:
        return sort_value(_("no task"))
    return None


def _category_columns(is_int: bool, today: date) -> tuple[SortColumn, ...]:
    if is_int:
        return (
            SortColumn("substance", gettext_lazy("Substance"),
                       lambda row: sort_value(row.substance.shown_name)),
            SortColumn("amount", gettext_lazy("Amount"),
                       lambda row: pairs_sort_key(row.amounts)),
            SortColumn("vessels", gettext_lazy("Vessels"),
                       lambda row: sort_value(row.vessel_count)),
            SortColumn("location", gettext_lazy("Location"), _location_sort),
            SortColumn("source", gettext_lazy("Source"), _source_sort),
            SortColumn("age", gettext_lazy("Age"),
                       lambda row: _oldest_age_days(row, today)),
        )
    return (
        SortColumn("substance", gettext_lazy("Substance"),
                   lambda row: sort_value(row.substance.shown_name)),
        SortColumn("group", gettext_lazy("Group"),
                   lambda row: sort_value(
                       row.substance.group.shown_label
                       if row.substance.group else "")),
        SortColumn("amount", gettext_lazy("Amount"),
                   lambda row: pairs_sort_key(row.amounts)),
        SortColumn("vessels", gettext_lazy("Vessels"),
                   lambda row: sort_value(row.vessel_count)),
        SortColumn("location", gettext_lazy("Location"), _location_sort),
        SortColumn("suppliers", gettext_lazy("Suppliers"),
                   lambda row: sort_value(
                       row.suppliers.first if row.suppliers else "")),
        SortColumn("opened", gettext_lazy("Opened"),
                   lambda row: sort_value(
                       row.opened_on if row.opened_on else _("sealed"))),
    )


def category_list_response(request: HttpRequest, category: str
                           ) -> HttpResponse:
    """Render the intermediate or commercial chemical list for CATEGORY."""
    config = CONFIGS[category]
    today = timezone.localdate()
    filters = CategoryFilters.from_query(request.GET, category)
    order = Order.from_query(
        request.GET, _category_columns(config.is_intermediate, today),
        "substance")
    all_vessels = list(category_vessels(category))
    admitted = filter_category_vessels(all_vessels, filters, category, today)
    other_substances = set(Vessel.objects.open().filter(
        batch__substance__article__isnull=True,
        batch__source=config.other_source,
    ).values_list("batch__substance_id", flat=True))
    rows = order.ordered(
        category_rows(admitted, category, today, other_substances))

    offered_locations, offered_suppliers = _offered_options(
        all_vessels, filters, config.is_intermediate)
    chosen, selected = pick_selected(
        rows, request.GET.get("selected", ""), lambda row: row.substance.key)
    detail_vessels = chosen.vessels if chosen else []
    chosen_lot, lot = pick_selected(
        detail_vessels, request.GET.get("lot", ""), lambda vessel: vessel.pk)
    classes = (tree_order(ChemicalClass.objects.select_related("parent"))
               if config.is_intermediate else [])
    groups = ([] if config.is_intermediate
              else tree_order(Group.objects.select_related("parent")))
    filter_pairs = filters.filter_pairs(category)
    lot_extra = [("lot", lot)] if lot else ()
    response = render(request, "inventory/category_list.html", {
        "is_intermediate": config.is_intermediate,
        "base_url": config.base_url,
        "cookie": config.cookie,
        "split_cookie": config.split_cookie,
        "heading": str(config.heading),
        "rows": rows,
        "vessel_total": sum(row.vessel_count for row in rows),
        "chosen": chosen,
        "detail_substance": chosen.substance if chosen else None,
        "detail_vessels": detail_vessels,
        "chosen_lot": chosen_lot,
        "lot": lot,
        "lot_ledger": vessel_ledger(chosen_lot, 5) if chosen_lot else [],
        "selected": selected,
        "order": order,
        "headers": order.headers(
            config.base_url, filter_pairs, selected,
            {"substance": "col-strong col-name",
             "amount": "number col-strong"},
            extra=lot_extra),
        "view": list_view(request, config.cookie),
        "major": split_major(request, config.split_cookie, "first"),
        "filters": filters,
        "filter_query": filters.query_string(category),
        "locations": offered_locations,
        "suppliers": offered_suppliers,
        "classes": classes,
        "groups": groups,
        "stale_class": stale_key(filters.chemical_class, classes),
        "stale_group": stale_key(filters.group, groups),
        "tabs": tabs(config.base_url),
    })
    return htmx_list_push_url(
        request, response,
        config.base_url + filters.query_string(
            category, selected, extra=order.pairs(), lot=lot))


def category_detail_response(request: HttpRequest, category: str, key: str
                             ) -> HttpResponse:
    """Answer an htmx request with the details pane of substance KEY in
    CATEGORY under the active filters, naming its first admitted lot, or
    redirect non-htmx requests to the list. Answer 404 when KEY has no
    open vessel of CATEGORY."""
    config = CONFIGS[category]
    all_for_sub = list(category_vessels(category).filter(
        batch__substance__key=key))
    if not all_for_sub:
        raise Http404

    admitted = []
    if request.htmx:
        today = timezone.localdate()
        filters = CategoryFilters.from_query(
            detail_query(request, keep_query=True), category)
        admitted = sorted(
            filter_category_vessels(all_for_sub, filters, category, today),
            key=oldest_vessel_order)
    chosen_lot = admitted[0] if admitted else None

    return htmx_detail_or_redirect(
        request, config.base_url, key, "inventory/category_list.html#detail",
        lambda: {
            "is_intermediate": config.is_intermediate,
            "base_url": config.base_url,
            "detail_substance": all_for_sub[0].batch.substance,
            "detail_vessels": admitted,
            "chosen_lot": chosen_lot,
            "lot_ledger": vessel_ledger(chosen_lot, 5) if chosen_lot else [],
        },
        keep_query=True, extra=[("lot", str(chosen_lot.pk)
                                 if chosen_lot else None)])


def category_lot_detail_response(request: HttpRequest, category: str,
                                 key: str, pk: int) -> HttpResponse:
    """Answer an htmx request with the lot details pane of vessel PK of
    substance KEY in CATEGORY, or redirect non-htmx requests to the list.
    Answer 404 when KEY or PK names no open vessel of CATEGORY admitted
    by the active filters."""
    config = CONFIGS[category]
    candidates = list(category_vessels(category).filter(
        pk=pk, batch__substance__key=key))
    filters = CategoryFilters.from_query(
        detail_query(request, keep_query=True), category)
    admitted = filter_category_vessels(
        candidates, filters, category, timezone.localdate())
    if not admitted:
        raise Http404
    vessel = admitted[0]

    return htmx_detail_or_redirect(
        request, config.base_url, key, "inventory/category_list.html#lot",
        lambda: {
            "chosen_lot": vessel,
            "lot_ledger": vessel_ledger(vessel, 5),
        },
        keep_query=True, extra=[("lot", str(vessel.pk))])


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def intermediate_list(request: HttpRequest) -> HttpResponse:
    """List the substances with an open intermediate vessel, one row per
    substance, with filters, summaries and the details view."""
    return category_list_response(request, StockCategory.INTERMEDIATES)


@vary_on_headers("HX-Request", "HX-Current-URL")
def intermediate_detail(request: HttpRequest, key: str) -> HttpResponse:
    """Answer an htmx request with the details pane of the intermediate
    substance KEY under the active filters, or redirect to the list."""
    return category_detail_response(request, StockCategory.INTERMEDIATES, key)


@vary_on_headers("HX-Request", "HX-Current-URL")
def intermediate_lot_detail(request: HttpRequest, key: str, pk: int
                            ) -> HttpResponse:
    """Answer an htmx request with the lot details pane of intermediate
    vessel PK of substance KEY, or redirect to the list."""
    return category_lot_detail_response(
        request, StockCategory.INTERMEDIATES, key, pk)


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def chemical_list(request: HttpRequest) -> HttpResponse:
    """List the substances with an open commercial chemical vessel, one
    row per substance, with filters, summaries and the details view."""
    return category_list_response(request, StockCategory.COMMERCIAL)


@vary_on_headers("HX-Request", "HX-Current-URL")
def chemical_detail(request: HttpRequest, key: str) -> HttpResponse:
    """Answer an htmx request with the details pane of the commercial
    chemical KEY under the active filters, or redirect to the list."""
    return category_detail_response(request, StockCategory.COMMERCIAL, key)


@vary_on_headers("HX-Request", "HX-Current-URL")
def chemical_lot_detail(request: HttpRequest, key: str, pk: int
                        ) -> HttpResponse:
    """Answer an htmx request with the lot details pane of commercial
    chemical vessel PK of substance KEY, or redirect to the list."""
    return category_lot_detail_response(
        request, StockCategory.COMMERCIAL, key, pk)
