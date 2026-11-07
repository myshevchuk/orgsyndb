"""The overview at /lab/ and its summary at /lab/summary/."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from overview import figures
from overview.chart import chart
from planning.plan import Plan


def overview(request: HttpRequest) -> HttpResponse:
    """Show the overview: the summary, the next syntheses, the
    deliveries per month and the lists of the current year."""
    today = timezone.localdate()
    plan = Plan(today)
    items = figures.end_products()
    deliveries = figures.delivered()
    months = figures.months_ending(today)
    return render(request, "overview/overview.html", {
        "summary": figures.summary(today, plan, items, deliveries),
        "next": figures.next_syntheses(plan),
        "chart": chart(
            months, figures.per_month(deliveries, months),
            figures.per_month(deliveries, [(year - 1, month)
                                           for year, month in months])),
        "requested": figures.most_requested(deliveries, today.year, items),
        "recipients": figures.recipients(deliveries, today.year),
        "latest": figures.latest_notes(),
        "year": today.year,
    })


@xframe_options_sameorigin
def summary(request: HttpRequest) -> HttpResponse:
    """Show the overview's summary alone, as a page that a page of the
    same host may frame."""
    today = timezone.localdate()
    return render(request, "overview/summary.html", {
        "summary": figures.summary(today, Plan(today),
                                   figures.end_products(),
                                   figures.delivered()),
    })
