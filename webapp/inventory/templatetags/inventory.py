"""Template filters of the inventory's pages."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from django import template
from django.utils.formats import number_format

from inventory.models import Batch, Item, Level, Vessel, plain, shown
from orgsyndb_web.lists import (amount_data_sort, format_decimal_key,
                                pairs_data_sort)

register = template.Library()


@register.filter
def decimal(value: Decimal | None) -> str:
    """Return VALUE as a number of the active language without trailing
    zeros, or nothing for None."""
    return "" if value is None else number_format(plain(Decimal(value)))


@register.filter
def in_vessel_unit(amount: Decimal, vessel: Vessel) -> str:
    """Return AMOUNT, kept in the base unit of VESSEL, in the vessel's
    unit, rounded half up to three places, with the unit."""
    return f"{number_format(shown(amount, vessel.unit))} {vessel.unit_label}"


@register.filter
def in_yield_unit(batch: Batch) -> str:
    """Return the yield of BATCH in its unit, rounded half up to three
    places, with the unit; empty for a batch without a yield."""
    if batch.yield_amount is None:
        return ""
    return f"{number_format(batch.shown_yield)} {batch.yield_unit_label}"


@register.filter
def level_label(value: str | None) -> str:
    """Return the label of the level VALUE in the active language, or
    nothing for no level."""
    return str(Level(value).label) if value else ""


@register.filter
def new_on(item: Item, today: date) -> bool:
    """Whether ITEM entered stock in the calendar year of TODAY."""
    return item.is_new(today)


@register.filter
def base_sort(amount: Decimal | None) -> str:
    """Return AMOUNT (in mg or µmol) as a plain decimal sort key."""
    return "" if amount is None else format_decimal_key(Decimal(amount))


@register.filter
def amounts_sort(pairs: Sequence[tuple[Decimal, str]]) -> str:
    """Return the client ``data-sort`` key for ``(amount, unit)`` PAIRS."""
    return pairs_data_sort(pairs)


@register.filter
def container_sort(item: Item) -> str:
    """Return the client ``data-sort`` key for ITEM's container size."""
    return amount_data_sort(item.size, item.unit)
