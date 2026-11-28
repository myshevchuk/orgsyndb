"""Vessel list, page, ledger, and vessel form views."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from inventory import bookings
from inventory.bookings import Refused
from inventory.forms import (NewVesselForm, TransferForm,
                             VesselCorrectionForm, VesselEditForm,
                             WithdrawalForm)
from inventory.history import history_entries
from inventory.models import Batch, Item, Vessel, VesselKind, VesselMovement
from inventory.views.common import (VESSEL_COOKIE, VESSELS, batch_source_text,
                                    batch_url, form_page,
                                    htmx_detail_or_redirect, item_form,
                                    list_view, locations, pick_selected, saved,
                                    tabs, vessel_url)
from orgsyndb_web.lists import (Order, SortColumn, amount_sort_key,
                                clean_choice, htmx_list_push_url, sort_value)


def _vessel_amount_sort(vessel: Vessel) -> Any:
    base_unit = "mg" if vessel.unit in ("mg", "g", "kg", "ug") else "umol"
    return amount_sort_key(vessel.amount, base_unit)


def _vessel_opened_sort(vessel: Vessel) -> Any:
    if vessel.batch.source != "bought":
        return None
    return sort_value(vessel.opened_on if vessel.opened_on else _("sealed"))


VESSEL_COLUMNS: tuple[SortColumn, ...] = (
    SortColumn("vessel", gettext_lazy("Vessel"),
               lambda v: sort_value(f"#{v.pk}")),
    SortColumn("name", gettext_lazy("Name"),
               lambda v: sort_value(v.batch.substance.shown_name)),
    SortColumn("article", gettext_lazy("Article no."),
               lambda v: sort_value(v.article_number)),
    SortColumn("kind", gettext_lazy("Kind"),
               lambda v: sort_value(v.kind_label)),
    SortColumn("batch", gettext_lazy("Batch"),
               lambda v: sort_value(str(v.batch))),
    SortColumn("source", gettext_lazy("Source"),
               lambda v: sort_value(batch_source_text(v.batch))),
    SortColumn("amount", gettext_lazy("Amount"), _vessel_amount_sort),
    SortColumn("location", gettext_lazy("Location"),
               lambda v: sort_value(v.location)),
    SortColumn("date", gettext_lazy("Date"),
               lambda v: sort_value(v.batch.date)),
    SortColumn("opened", gettext_lazy("Opened"), _vessel_opened_sort),
    SortColumn("note", pgettext_lazy("inventory", "Note"),
               lambda v: sort_value(v.note)),
)
VESSEL_CLASSES = {"amount": "number"}


@dataclass(frozen=True)
class VesselLedgerRow:
    """A movement of a vessel as its page shows it: the ITEM a filling
    filled, or None; the OTHER vessel of a transfer, or None; and
    whether a withdrawal may still be REVERSIBLE."""

    movement: VesselMovement
    item: Item | None
    other: Vessel | None
    reversible: bool


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def vessel_list(request: HttpRequest) -> HttpResponse:
    """List the open vessels of every substance, and the used-up ones
    too with ``empty=1``, by the substance's name regardless of case by
    default, then by their batch's date, oldest first and vessels
    without one last, then by ID. ``kind`` names one of ``VesselKind``
    and lists the vessels of that kind; another value lists every
    kind."""
    empty = request.GET.get("empty") == "1"
    kind = clean_choice(request.GET.get("kind", ""), VesselKind.values)
    order = Order.from_query(request.GET, VESSEL_COLUMNS, "name")
    vessels = Vessel.objects.with_substance().select_related(
        "batch__task_step__task")
    if not empty:
        vessels = vessels.open()
    found = sorted((vessel for vessel in vessels
                    if not kind or vessel.kind == kind),
                   key=lambda vessel: (
                       vessel.batch.substance.shown_name.casefold(),
                       vessel.batch.date is None,
                       vessel.batch.date or date.min, vessel.pk))
    found = order.ordered(found)
    chosen, selected = pick_selected(
        found, request.GET.get("selected", ""), lambda vessel: vessel.pk)
    filter_pairs: list[tuple[str, str]] = []
    if kind:
        filter_pairs.append(("kind", kind))
    if empty:
        filter_pairs.append(("empty", "1"))
    response = render(request, "inventory/vessel_list.html", {
        "vessels": found,
        "detail_vessel": chosen,
        "ledger": vessel_ledger(chosen, 5) if chosen else [],
        "selected": selected,
        "order": order,
        "headers": order.headers(VESSELS, filter_pairs, selected,
                                 VESSEL_CLASSES),
        "view": list_view(request, VESSEL_COOKIE),
        "empty": empty,
        "kind": kind,
        "kinds": VesselKind.choices,
        "tabs": tabs(VESSELS),
    })
    pairs = [*filter_pairs, *order.pairs()]
    if selected:
        pairs.append(("selected", selected))
    return htmx_list_push_url(
        request, response,
        f"{VESSELS}?{urlencode(pairs)}" if pairs else VESSELS)


@vary_on_headers("HX-Request", "HX-Current-URL")
def vessel_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Answer an htmx request with the details pane of vessel PK alone,
    or redirect non-htmx requests to the vessel list with ``selected``
    naming the vessel. Answer 404 for an unknown ID."""
    vessel = get_object_or_404(
        Vessel.objects.with_substance().select_related(
            "batch__task_step__task"), pk=pk)
    return htmx_detail_or_redirect(
        request, VESSELS, vessel.pk, "inventory/vessel_list.html#detail",
        lambda: {"detail_vessel": vessel, "ledger": vessel_ledger(vessel, 5)})


def vessel_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the vessel PK with its batch, its movements and its history;
    answer 404 for an unknown ID."""
    vessel = get_object_or_404(Vessel.objects.with_substance(), pk=pk)
    return render(request, "inventory/vessel_page.html", {
        "vessel": vessel,
        "ledger": vessel_ledger(vessel),
        "history": history_entries(vessel),
    })


def vessel_ledger(vessel: Vessel, limit: int | None = None
                  ) -> list[VesselLedgerRow]:
    """Return the movements of VESSEL, newest first, the LIMIT newest
    alone when it is given, each with the item it filled, the other
    vessel of a transfer and whether it can be reversed."""
    movements = vessel.movements.select_related(
        "user", "item_movement__item__article", "task_step__task",
        "task_step__entry__procedure", "reverses", "reversal",
        "transfer__vessel__batch",
        "transferred__vessel__batch").order_by("-id")
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
