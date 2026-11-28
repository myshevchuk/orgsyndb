"""The planning list and article details pane."""

import math
from typing import Any
from urllib.parse import urlencode

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from orgsyndb_web.lists import (Order, SortColumn, clean_choice,
                                htmx_detail_or_redirect, htmx_list_push_url,
                                list_view, pick_selected, sort_value,
                                split_major)
from planning.plan import Plan, Row

PLAN = "/lab/planning/"
PLANNING_COOKIE = "planning-list-view"
PLANNING_SPLIT_COOKIE = "planning-list-split"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SHOW_CHOICES = (
    ("", gettext_lazy("All")),
    ("high", gettext_lazy("High priority")),
    ("action", gettext_lazy("With action")),
    ("late", gettext_lazy("Late")),
)
SHOW_VALUES = {"high", "action", "late"}


def _whole_days(value: float | None) -> int | None:
    """Return VALUE in whole days rounded down, as the list shows it;
    None for None."""
    return None if value is None else math.floor(value)

PLANNING_COLUMNS: tuple[SortColumn, ...] = (
    SortColumn("article", gettext_lazy("Article"),
               lambda row: sort_value(row.forecast.substance.shown_name)),
    SortColumn("runway", gettext_lazy("Runway"),
               lambda row: _whole_days(row.forecast.runway)),
    SortColumn("synthesis", gettext_lazy("Synthesis time"),
               lambda row: _whole_days(row.forecast.synthesis_days)),
    SortColumn("start", gettext_lazy("Latest start"),
               lambda row: sort_value(row.forecast.latest_start)),
    SortColumn("priority", gettext_lazy("Priority"),
               lambda row: PRIORITY_ORDER.get(row.forecast.priority, 3)),
    SortColumn("tasks", gettext_lazy("Tasks"),
               lambda row: sort_value(row.tasks[0].task.number)
               if row.tasks else None),
    SortColumn("actions", pgettext_lazy("planning", "Actions"),
               sortable=False),
)
PLANNING_CLASSES = {
    "article": "col-strong col-name",
    "runway": "num",
    "synthesis": "num",
    "start": "col-strong",
}


def _matches_show(row: Row, show: str) -> bool:
    if show == "high":
        return row.forecast.priority == "high"
    if show == "action":
        return bool(row.fill or row.check_bulk or row.plan_synthesis)
    if show == "late":
        return any(line.late for line in row.tasks)
    return True


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def planning_list(request: HttpRequest) -> HttpResponse:
    """List the articles with a forecast whose priority is high or medium
    or for which an action is due, every one with ``all=1``, filtered by
    ``show`` and ordered by slack (latest start) by default."""
    every = request.GET.get("all") == "1"
    show = clean_choice(request.GET.get("show", ""), SHOW_VALUES)
    order = Order.from_query(request.GET, PLANNING_COLUMNS, "start")
    plan = Plan(timezone.localdate())
    base_rows = sorted(
        (row for row in (plan.row(found) for found in plan.forecasts())
         if every or row.listed),
        key=lambda row: (row.forecast.slack, row.forecast.article_number))
    has_unfiltered = bool(base_rows)
    rows = order.ordered(
        [row for row in base_rows if _matches_show(row, show)])
    chosen, selected = pick_selected(
        rows, request.GET.get("selected", ""),
        lambda row: row.forecast.article_number)
    filter_pairs: list[tuple[str, str]] = []
    if every:
        filter_pairs.append(("all", "1"))
    if show:
        filter_pairs.append(("show", show))
    row_query = f"?{urlencode(filter_pairs)}" if filter_pairs else ""
    response = render(request, "planning/list.html", {
        "rows": rows,
        "detail_row": chosen,
        "selected": selected,
        "all": every,
        "show": show,
        "show_choices": SHOW_CHOICES,
        "has_unfiltered": has_unfiltered,
        "row_query": row_query,
        "order": order,
        "headers": order.headers(PLAN, filter_pairs, selected,
                                 PLANNING_CLASSES),
        "view": list_view(request, PLANNING_COOKIE, default="details"),
        "major": split_major(request, PLANNING_SPLIT_COOKIE, "first"),
        "parameters": plan.parameters,
    })
    pairs = [*filter_pairs, *order.pairs()]
    if selected:
        pairs.append(("selected", selected))
    return htmx_list_push_url(
        request, response, f"{PLAN}?{urlencode(pairs)}" if pairs else PLAN)


@vary_on_headers("HX-Request", "HX-Current-URL")
def planning_detail(request: HttpRequest, number: str) -> HttpResponse:
    """Answer an htmx request with the details pane of article NUMBER,
    or redirect non-htmx requests to the planning list keeping ``all``
    and ``show`` with ``selected`` naming NUMBER. Answer 404 when NUMBER
    names no article with a forecast."""
    plan = Plan(timezone.localdate())
    found = next((f for f in plan.forecasts() if f.article_number == number),
                 None)
    if found is None:
        raise Http404
    return htmx_detail_or_redirect(
        request, PLAN, found.article_number, "planning/list.html#detail",
        lambda: {"detail_row": plan.row(found)},
        keep_query=True)
