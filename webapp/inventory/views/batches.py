"""Batch list, page, and batch form views."""

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _

from inventory import bookings
from inventory.bookings import Refused
from inventory.figures import newest_first, open_amounts
from inventory.forms import BatchEditForm, BatchForm
from inventory.history import history_entries
from inventory.models import (Batch, DeliveryLine, Item, Movement, Source,
                              VesselMovement)
from inventory.views.common import (BATCHES, batch_url, form_page, locations,
                                    saved, tabs)
from journal.entries import entry_for
from tasks.models import Task, TaskStep


@dataclass(frozen=True)
class FillingRow:
    """A filling from a batch's vessel as the batch's page shows it: the
    vessel's MOVEMENT, the ITEM it filled, and whether the filling is
    REVERSED."""

    movement: VesselMovement
    item: Item
    reversed: bool


@dataclass(frozen=True)
class LineRow:
    """A delivery line of a batch as the batch's page shows it: the LINE,
    whether its note is HISTORICAL, and whether the line is REVERSED."""

    line: DeliveryLine
    historical: bool
    reversed: bool


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


def batch_page(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the batch PK with its vessels, fillings, container shares,
    deliveries and history; answer 404 for an unknown ID."""
    batch = get_object_or_404(Batch.objects.select_related(
        "substance__article", "journal_entry__notebook",
        "task_step__task", "task_step__entry__procedure"), pk=pk)
    vessels = sorted(batch.vessels.with_substance(),
                     key=lambda vessel: (not vessel.amount > 0, vessel.pk))
    fillings = VesselMovement.objects.filter(
        vessel__batch=batch, kind=VesselMovement.Kind.FILLING
        ).select_related("vessel", "item_movement__item__article",
                         "item_movement__reversal").order_by("-id")
    undone = set(Movement.objects.reversed_deliveries().filter(
        batch=batch).values_list("delivery_note_id", "item_id"))
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
