"""The planning list."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from planning.plan import Plan


def planning_list(request: HttpRequest) -> HttpResponse:
    """List the articles with a forecast whose priority is high or medium
    or for which an action is due, every one with ``all=1``, by slack,
    smallest first, then by article number."""
    every = request.GET.get("all") == "1"
    plan = Plan(timezone.localdate())
    rows = [plan.row(found) for found in plan.forecasts()]
    return render(request, "planning/list.html", {
        "rows": sorted((row for row in rows if every or row.listed),
                       key=lambda row: (row.forecast.slack,
                                        row.forecast.article_number)),
        "all": every,
        "parameters": plan.parameters,
    })
