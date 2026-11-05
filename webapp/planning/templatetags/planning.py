"""Template filters of the forecast's figures."""

import math
from decimal import ROUND_FLOOR, Decimal

from django import template
from django.utils.formats import number_format
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from inventory.models import plain

register = template.Library()


@register.filter
def days(value: float | None) -> str:
    """Return VALUE as whole days, rounded down, such as ``60 days`` in
    the active language; nothing for None."""
    if value is None:
        return ""
    count = math.floor(value)
    return ngettext("%(count)s day", "%(count)s days", count) % {
        "count": count}


@register.filter
def percent(value: float) -> str:
    """Return the probability VALUE as a percentage of at most two
    places, without trailing zeros, such as ``97,5 %`` in German."""
    shown = Decimal(str(round(value * 100, 2)))
    return f"{number_format(plain(shown))} %"


@register.filter
def amount(value: Decimal | None) -> str:
    """Return the amount VALUE rounded down to three places, without
    trailing zeros, in the number format of the active language; nothing
    for None."""
    if value is None:
        return ""
    return number_format(plain(Decimal(value).quantize(
        Decimal("0.001"), ROUND_FLOOR)))


@register.filter
def figure(value: float | int, places: int = 2) -> str:
    """Return VALUE rounded to at most PLACES places, two by default,
    without trailing zeros, in the number format of the active
    language."""
    return number_format(plain(Decimal(str(round(float(value),
                                                 int(places))))))


@register.filter
def rough(flag: bool) -> SafeString:
    """Return the mark of a rough figure, preceded by a space, when FLAG
    is true; nothing otherwise."""
    if not flag:
        return mark_safe("")
    return format_html(' <span class="lab-mark">({})</span>', _("rough"))
