"""Bulk vessel list and detail views."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory.figures import containers_from, molar_mass
from inventory.models import Item, Source, Vessel
from inventory.summaries import natural
from inventory.views.common import (BULK, BULK_COOKIE, LIST, bulk_vessels,
                                    htmx_detail_or_redirect, layers, list_view,
                                    pick_selected, tabs)
from inventory.views.vessels import vessel_ledger


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
    chosen, selected = pick_selected(
        rows, request.GET.get("selected", ""), lambda row: row.vessel.pk)
    return render(request, "inventory/bulk_list.html", {
        "rows": rows,
        "chosen": chosen,
        "ledger": vessel_ledger(chosen.vessel, 5) if chosen else [],
        "selected": selected,
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
    return htmx_detail_or_redirect(
        request, BULK, vessel.pk, "inventory/bulk_list.html#detail",
        lambda: {
            "chosen": bulk_rows([vessel])[0],
            "ledger": vessel_ledger(vessel, 5),
        })
