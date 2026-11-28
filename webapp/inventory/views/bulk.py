"""Bulk vessel list and detail views."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory.figures import containers_from, molar_mass
from inventory.models import Item, Source, Vessel
from inventory.summaries import natural
from inventory.views.common import (BULK, BULK_COOKIE, LIST,
                                    batch_source_text, bulk_vessels,
                                    htmx_detail_or_redirect, layers,
                                    list_view, pick_selected, tabs)
from inventory.views.vessels import vessel_ledger
from orgsyndb_web.lists import (Order, SortColumn, amount_sort_key,
                                clean_choice, htmx_list_push_url, sort_value)


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


def _article_sort(row: BulkRow) -> tuple[Any, ...]:
    substance = row.vessel.batch.substance
    number = substance.article.article_number
    return (number is None, sort_value(number) or (),
            sort_value(substance.shown_name))


def _vessel_amount_sort(vessel: Vessel) -> Any:
    base_unit = "mg" if vessel.unit in ("mg", "g", "kg", "ug") else "umol"
    return amount_sort_key(vessel.amount, base_unit)


BULK_COLUMNS: tuple[SortColumn, ...] = (
    SortColumn("article", gettext_lazy("Article"), _article_sort),
    SortColumn("vessel", gettext_lazy("Vessel"),
               lambda row: sort_value(f"#{row.vessel.pk}")),
    SortColumn("batch", gettext_lazy("Batch"),
               lambda row: sort_value(str(row.vessel.batch))),
    SortColumn("source", gettext_lazy("Source"),
               lambda row: sort_value(batch_source_text(row.vessel.batch))),
    SortColumn("amount", gettext_lazy("Amount"),
               lambda row: _vessel_amount_sort(row.vessel)),
    SortColumn("location", gettext_lazy("Location"),
               lambda row: sort_value(
                   _("Flask") if row.vessel.flask else row.vessel.location)),
    SortColumn("date", gettext_lazy("Date"),
               lambda row: sort_value(row.vessel.batch.date)),
    SortColumn("fills", pgettext_lazy("bulk", "Fills"), sortable=False),
)
BULK_CLASSES = {"amount": "number"}


def bulk_rows(vessels: list[Vessel]) -> list[BulkRow]:
    """Return VESSELS as rows of the bulk list, with the containers each
    would fill of every item of its substance's article, by size."""
    items: dict[int, list[Item]] = {}
    for item in sorted(Item.objects.filter(
            article_id__in={vessel.batch.substance_id
                            for vessel in vessels}
            ).with_substance(),
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


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bulk_list(request: HttpRequest) -> HttpResponse:
    """List the open vessels of the substances that have an article, in
    the requested or default order, with the containers each would fill;
    ``q``, ``location``, ``source`` and ``flask=1`` select among them.
    The vessel ``selected`` names among those listed, else the first, is
    selected, in the view the cookie ``bulk-list-view`` remembers."""
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    source = clean_choice(request.GET.get("source", ""), Source.values)
    flask = request.GET.get("flask") == "1"
    order = Order.from_query(request.GET, BULK_COLUMNS, "article")
    vessels = list(bulk_vessels())
    locations = sorted({vessel.location for vessel in vessels
                        if vessel.location}, key=natural)
    words = q.casefold()
    rows = [row for row in bulk_rows(sorted(vessels, key=bulk_order))
            if (not words or words in row.searched())
            and (not location or row.vessel.location == location)
            and (not source or row.vessel.batch.source == source)
            and (not flask or row.vessel.flask)]
    rows = order.ordered(rows)
    chosen, selected = pick_selected(
        rows, request.GET.get("selected", ""), lambda row: row.vessel.pk)
    filter_pairs: list[tuple[str, str]] = []
    if q:
        filter_pairs.append(("q", q))
    if location:
        filter_pairs.append(("location", location))
    if source:
        filter_pairs.append(("source", source))
    if flask:
        filter_pairs.append(("flask", "1"))
    response = render(request, "inventory/bulk_list.html", {
        "rows": rows,
        "chosen": chosen,
        "ledger": vessel_ledger(chosen.vessel, 5) if chosen else [],
        "selected": selected,
        "order": order,
        "headers": order.headers(BULK, filter_pairs, selected, BULK_CLASSES),
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
    pairs = [*filter_pairs, *order.pairs()]
    if selected:
        pairs.append(("selected", selected))
    return htmx_list_push_url(
        request, response, f"{BULK}?{urlencode(pairs)}" if pairs else BULK)


@vary_on_headers("HX-Request", "HX-Current-URL")
def bulk_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request (``HX-Request: true``) with the details of
    the vessel PK alone, as the bulk list shows them beside its table,
    and any other request with a redirect to the list with ``selected``
    naming the vessel. Answer 404 for a vessel the bulk list does not
    hold."""
    vessel = get_object_or_404(bulk_vessels(), pk=pk)
    return htmx_detail_or_redirect(
        request, BULK, vessel.pk, "inventory/bulk_list.html#detail",
        lambda: {
            "chosen": bulk_rows([vessel])[0],
            "ledger": vessel_ledger(vessel, 5),
        })
